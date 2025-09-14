#!/usr/bin/env python3
"""
Build A/B/C datasets from a per-listing "universe" CSV and (optionally) generate Folium maps
for multiple years and categories.

Inputs
------
• Universe CSV (Dataset D) OR a directory of CSVs to concatenate.
  Required per-listing columns (case-sensitive):
    - neighborhood_uid (stable key that matches GeoJSON properties)
    - neighborhood_label (display name)
    - transaction        (Rent|Sale)
    - property_type      (Apartment|House|Other|Room)
    - date               (YYYY-MM-DD)
    - std_price          (numeric, USD)
  Optional but recommended for indicators:
    - bedrooms           (int)
    - area_m2            (float)

Outputs
-------
• Dataset A (price by neighborhood): A_price_by_neigh_<YEAR>.csv
• Dataset B (price & bedrooms):     B_price_bed_by_neigh_<YEAR>.csv
• Dataset C (price & area):         C_price_area_by_neigh_<YEAR>.csv

Optional maps (Dataset A):
• map_A_<YEAR>.html — choropleth of avg_std_price with layer toggles by (transaction × property_type)

Usage
-----
python build_datasets_and_maps.py \
  --universe data/universe/2010_2015/ \
  --geojson data/neighborhoods.geojson \
  --outdir output/aggregates \
  --min-count 3 \
  --make-maps

Notes
-----
• Requires: pandas, folium, branca
• Binning defaults: bedrooms_bin in {0,1,2,3,4+}; area_bin (m²) in [0-49,50-79,80-119,120-159,160+]
• Rows with missing std_price are excluded from stats, but counts are reported per group.
"""
from __future__ import annotations
import argparse
import os
import sys
import json
from typing import List, Tuple, Optional, Dict

import pandas as pd

try:
    import folium
    from folium.features import GeoJson, GeoJsonTooltip
    from branca.colormap import LinearColormap
except Exception:
    folium = None  # maps will be disabled if folium/branca are missing

# --------------------------- Helpers ---------------------------

def read_universe(path: str) -> pd.DataFrame:
    if os.path.isdir(path):
        frames = []
        for fn in sorted(os.listdir(path)):
            if fn.lower().endswith(".csv"):
                frames.append(pd.read_csv(os.path.join(path, fn)))
        if not frames:
            raise RuntimeError(f"No CSV files found in directory: {path}")
        df = pd.concat(frames, ignore_index=True)
    else:
        df = pd.read_csv(path)
    return df


def ensure_columns(df: pd.DataFrame, cols: List[str]) -> None:
    missing = [c for c in cols if c not in df.columns]
    if missing:
        raise RuntimeError(f"Universe is missing required columns: {missing}")


def coerce_types(df: pd.DataFrame) -> pd.DataFrame:
    # Date → year
    if "year" not in df.columns:
        df["year"] = pd.to_datetime(df["date"], errors="coerce").dt.year
    # Numeric std_price
    df["std_price"] = pd.to_numeric(df["std_price"], errors="coerce")
    # Bedrooms & area
    if "bedrooms" in df.columns:
        df["bedrooms"] = pd.to_numeric(df["bedrooms"], errors="coerce")
    if "area_m2" in df.columns:
        df["area_m2"] = pd.to_numeric(df["area_m2"], errors="coerce")
    return df


def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    # price per bed: avoid division by 0; require bedrooms >= 1
    if "bedrooms" in df.columns:
        df["price_per_bed"] = df.apply(lambda r: r["std_price"] / r["bedrooms"] if pd.notnull(r.get("std_price")) and pd.notnull(r.get("bedrooms")) and r["bedrooms"] >= 1 else pd.NA, axis=1)
    else:
        df["price_per_bed"] = pd.NA
    # price per m2: require positive area
    if "area_m2" in df.columns:
        df["price_per_m2"] = df.apply(lambda r: r["std_price"] / r["area_m2"] if pd.notnull(r.get("std_price")) and pd.notnull(r.get("area_m2")) and r["area_m2"] > 0 else pd.NA, axis=1)
    else:
        df["price_per_m2"] = pd.NA
    return df


def bin_bedrooms(df: pd.DataFrame) -> pd.DataFrame:
    # Bins: 0,1,2,3,4+
    def _bin(x):
        if pd.isna(x):
            return pd.NA
        x = int(x)
        return str(x) if x < 4 else "4+"
    if "bedrooms" in df.columns:
        df["bedrooms_bin"] = df["bedrooms"].apply(_bin)
    else:
        df["bedrooms_bin"] = pd.NA
    return df


def bin_area(df: pd.DataFrame, edges: List[int]) -> pd.DataFrame:
    # Example edges: [0,50,80,120,160,10**9]
    if "area_m2" not in df.columns:
        df["area_bin"] = pd.NA
        return df
    labels = []
    for i in range(len(edges)-1):
        a, b = edges[i], edges[i+1]
        if b >= 10**9:
            labels.append(f">={a}")
        else:
            labels.append(f"{a}-{b-1}")
    df["area_bin"] = pd.cut(df["area_m2"], bins=edges, right=False, labels=labels, include_lowest=True)
    return df


def agg_stats(series: pd.Series) -> pd.Series:
    s = pd.to_numeric(series, errors="coerce")
    return pd.Series({
        "avg": s.mean(skipna=True),
        "median": s.median(skipna=True),
        "min": s.min(skipna=True),
        "max": s.max(skipna=True),
        "count": s.count(),
    })

# --------------------------- Aggregations A/B/C ---------------------------

def make_dataset_A(df: pd.DataFrame, min_count: int) -> pd.DataFrame:
    grp = df.dropna(subset=["std_price"]).groupby(["neighborhood_uid", "neighborhood_label", "property_type", "transaction", "year"], as_index=False)["std_price"].apply(agg_stats)
    out = grp.pivot_table(index=["neighborhood_uid", "neighborhood_label", "property_type", "transaction", "year"], values=["avg", "median", "min", "max", "count"]).reset_index()
    out = out.rename(columns={"avg": "avg_std_price", "median": "median_std_price", "min": "min_std_price", "max": "max_std_price", "count": "count_listings"})
    out = out[out["count_listings"] >= min_count]
    return out


def make_dataset_B(df: pd.DataFrame, min_count: int) -> pd.DataFrame:
    df_b = df.dropna(subset=["std_price", "bedrooms"]).copy()
    df_b = bin_bedrooms(df_b)
    df_b["price_per_bed"] = pd.to_numeric(df_b["price_per_bed"], errors="coerce")
    grp = df_b.groupby(["neighborhood_uid", "neighborhood_label", "property_type", "transaction", "bedrooms_bin", "year"], as_index=False)["price_per_bed"].apply(agg_stats)
    out = grp.pivot_table(index=["neighborhood_uid", "neighborhood_label", "property_type", "transaction", "bedrooms_bin", "year"], values=["avg", "median", "min", "max", "count"]).reset_index()
    out = out.rename(columns={"avg": "avg_price_per_bed", "median": "median_price_per_bed", "min": "min_price_per_bed", "max": "max_price_per_bed", "count": "count_listings"})
    out = out[out["count_listings"] >= min_count]
    return out


def make_dataset_C(df: pd.DataFrame, min_count: int, area_edges: List[int]) -> pd.DataFrame:
    df_c = df.dropna(subset=["std_price", "area_m2"]).copy()
    df_c = bin_area(df_c, area_edges)
    df_c["price_per_m2"] = pd.to_numeric(df_c["price_per_m2"], errors="coerce")
    grp = df_c.groupby(["neighborhood_uid", "neighborhood_label", "property_type", "transaction", "area_bin", "year"], as_index=False)["price_per_m2"].apply(agg_stats)
    out = grp.pivot_table(index=["neighborhood_uid", "neighborhood_label", "property_type", "transaction", "area_bin", "year"], values=["avg", "median", "min", "max", "count"]).reset_index()
    out = out.rename(columns={"avg": "avg_price_per_m2", "median": "median_price_per_m2", "min": "min_price_per_m2", "max": "max_price_per_m2", "count": "count_listings"})
    out = out[out["count_listings"] >= min_count]
    return out

# --------------------------- Maps (Dataset A) ---------------------------

def build_colormap(vmin: float, vmax: float) -> LinearColormap:
    return LinearColormap(["#f7fbff", "#deebf7", "#c6dbef", "#9ecae1", "#6baed6", "#3182bd", "#08519c"], vmin=vmin, vmax=vmax)


def add_layer_dataset_A(m, gjson: dict, dfA_year: pd.DataFrame, value_col: str, layer_suffix: str, uid_key: str, label_key: str):
    # Create one layer per (transaction × property_type) for the selected year
    combos = sorted(dfA_year[["transaction", "property_type"]].drop_duplicates().itertuples(index=False, name=None))
    for transaction, ptype in combos:
        sub = dfA_year[(dfA_year["transaction"] == transaction) & (dfA_year["property_type"] == ptype)]
        if sub.empty:
            continue
        vmin, vmax = float(sub[value_col].min()), float(sub[value_col].max())
        if vmax == vmin:
            vmax = vmin + 1e-6
        cmap = build_colormap(vmin, vmax)

        value_by_uid = dict(zip(sub["neighborhood_uid"], sub[value_col]))
        label_by_uid = dict(zip(sub["neighborhood_uid"], sub["neighborhood_label"]))

        def style_fn(feature):
            uid = feature["properties"].get(uid_key)
            val = value_by_uid.get(uid)
            if val is None:
                return {"fillOpacity": 0.0, "weight": 0.4, "color": "#888888"}
            return {"fillColor": cmap(val), "fillOpacity": 0.85, "weight": 0.4, "color": "#666666"}

        gj = GeoJson(
            data=gjson,
            name=f"{transaction} – {ptype} {layer_suffix}",
            style_function=style_fn,
            highlight_function=lambda f: {"weight": 1.5, "color": "#000"},
            tooltip=GeoJsonTooltip(fields=[uid_key], aliases=["UID:"], sticky=True),
        )
        # enrich tooltips
        for feat in gj.data["features"]:
            uid = feat["properties"].get(uid_key)
            lbl = label_by_uid.get(uid, feat["properties"].get(label_key, uid))
            val = value_by_uid.get(uid)
            feat["properties"]["_popup"] = f"{lbl}<br>{transaction} – {ptype}: {val:,.2f}" if val is not None else f"{lbl}<br>No data"
        gj.add_to(m)
        cmap.caption = f"{transaction} – {ptype} {layer_suffix} ({value_col})"
        cmap.add_to(m)


def make_map_for_year(dfA: pd.DataFrame, year: int, geojson_path: str, out_html: str, center_lat: float, center_lon: float, zoom: int, uid_key: str, label_key: str, value_col: str):
    if folium is None:
        print("[warn] folium/branca not installed; skipping map generation", file=sys.stderr)
        return
    with open(geojson_path, "r", encoding="utf-8") as f:
        gjson = json.load(f)
    m = folium.Map(location=[center_lat, center_lon], zoom_start=zoom, tiles="cartodbpositron")
    df_year = dfA[dfA["year"] == year]
    if df_year.empty:
        print(f"[warn] No Dataset A rows for year {year}", file=sys.stderr)
    add_layer_dataset_A(m, gjson, df_year, value_col=value_col, layer_suffix=f"({year})", uid_key=uid_key, label_key=label_key)
    folium.LayerControl(collapsed=False).add_to(m)
    m.save(out_html)
    print(f"Saved map → {out_html}")

# --------------------------- CLI ---------------------------

def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Build datasets A/B/C and optional Folium maps from a per-listing universe CSV (multi-year).")
    ap.add_argument("--universe", required=True, help="Universe CSV file or a directory of CSVs to concatenate")
    ap.add_argument("--outdir", required=True, help="Output directory for datasets and maps")
    ap.add_argument("--geojson", default=None, help="Neighborhood polygons GeoJSON path (required to make maps)")
    ap.add_argument("--uid-key", default="neighborhood_uid", help="Join key present in both GeoJSON properties and CSVs")
    ap.add_argument("--label-key", default="neighborhood_label", help="Display label in CSVs")
    ap.add_argument("--years", nargs="*", type=int, default=None, help="Optional subset of years to process (e.g., 2010 2015)")
    ap.add_argument("--min-count", type=int, default=3, help="Minimum listings per group to keep in outputs")
    ap.add_argument("--area-edges", nargs="*", type=int, default=[0,50,80,120,160,10**9], help="Bin edges for area_m2 (right-open)")
    ap.add_argument("--make-maps", action="store_true", help="Generate Folium maps for Dataset A per year")
    ap.add_argument("--merge-geojson", action="store_true", help="Also export enriched GeoJSON per year and per (transaction×property_type)")
    ap.add_argument("--center-lat", type=float, default=14.072, help="Map center latitude")
    ap.add_argument("--center-lon", type=float, default=-87.206, help="Map center longitude")
    ap.add_argument("--zoom", type=int, default=12, help="Map initial zoom")
    ap.add_argument("--value-col", default="avg_std_price", help="Dataset A value column for choropleth")
    ap.add_argument("--types", nargs="*", default=["House","Apartment","Room"], help="Property types to include (default: House Apartment Room)")
    return ap.parse_args()


def main():
    args = parse_args()
    os.makedirs(args.outdir, exist_ok=True)

    # Load & check universe
    df = read_universe(args.universe)
    required = ["neighborhood_uid", "neighborhood_label", "transaction", "property_type", "date", "std_price"]
    ensure_columns(df, required)
    df = coerce_types(df)
    df = add_indicators(df)

    # Optional filter by years
    if args.years:
        df = df[df["year"].isin(set(args.years))]
        if df.empty:
            raise RuntimeError("No rows remain after filtering by years")

    # Build datasets
    dfA = make_dataset_A(df, args.min_count)
    dfB = make_dataset_B(df, args.min_count)
    dfC = make_dataset_C(df, args.min_count, area_edges=list(map(int, args.area_edges)))

    # Write per-year CSVs
    for y, sub in dfA.groupby("year"):
        sub.sort_values(["neighborhood_uid", "transaction", "property_type"], inplace=True)
        sub.to_csv(os.path.join(args.outdir, f"A_price_by_neigh_{y}.csv"), index=False)
    for y, sub in dfB.groupby("year"):
        sub.sort_values(["neighborhood_uid", "transaction", "property_type", "bedrooms_bin"], inplace=True)
        sub.to_csv(os.path.join(args.outdir, f"B_price_bed_by_neigh_{y}.csv"), index=False)
    for y, sub in dfC.groupby("year"):
        sub.sort_values(["neighborhood_uid", "transaction", "property_type", "area_bin"], inplace=True)
        sub.to_csv(os.path.join(args.outdir, f"C_price_area_by_neigh_{y}.csv"), index=False)

    print(f"Saved Dataset A rows: {len(dfA)}  |def main():
    args = parse_args()
    os.makedirs(args.outdir, exist_ok=True)

    # Load & check universe
    df = read_universe(args.universe)
    required = ["neighborhood_uid", "neighborhood_label", "transaction", "property_type", "date", "std_price"]
    ensure_columns(df, required)
    df = coerce_types(df)
    df = add_indicators(df)

    # Filter property types if requested (default: House, Apartment, Room)
    if args.types:
        df = df[df["property_type"].isin(set(args.types))]

    # Exclude records without price
    df = df[df["std_price"].notna() & (df["std_price"] > 0)]

    # Optional filter by years
    if args.years:
        df = df[df["year"].isin(set(args.years))]
        if df.empty:
            raise RuntimeError("No rows remain after filtering by years")

    # Build datasets
    dfA = make_dataset_A(df, args.min_count)
    dfB = make_dataset_B(df, args.min_count)
    dfC = make_dataset_C(df, args.min_count, area_edges=list(map(int, args.area_edges)))

    # Write per-year CSVs
    for y, sub in dfA.groupby("year"):
        sub.sort_values(["neighborhood_uid", "transaction", "property_type"], inplace=True)
        sub.to_csv(os.path.join(args.outdir, f"A_price_by_neigh_{y}.csv"), index=False)
    for y, sub in dfB.groupby("year"):
        sub.sort_values(["neighborhood_uid", "transaction", "property_type", "bedrooms_bin"], inplace=True)
        sub.to_csv(os.path.join(args.outdir, f"B_price_bed_by_neigh_{y}.csv"), index=False)
    for y, sub in dfC.groupby("year"):
        sub.sort_values(["neighborhood_uid", "transaction", "property_type", "area_bin"], inplace=True)
        sub.to_csv(os.path.join(args.outdir, f"C_price_area_by_neigh_{y}.csv"), index=False)

    print(f"Saved Dataset A rows: {len(dfA)}  | B: {len(dfB)}  | C: {len(dfC)}")

    # Optional maps (Dataset A only)
    if args.make_maps or args.merge_geojson:
        if args.geojson is None:
            raise RuntimeError("--geojson is required when --make-maps or --merge-geojson is set")

    if args.make_maps:
        years = sorted(dfA["year"].unique())
        for y in years:
            out_html = os.path.join(args.outdir, f"map_A_{y}.html")
            make_map_for_year(dfA, int(y), args.geojson, out_html, args.center_lat, args.center_lon, args.zoom, args.uid_key, args.label_key, args.value_col)

    # Optional: export enriched GeoJSON per year and per (transaction × property_type)
    if args.merge_geojson:
        import json
        with open(args.geojson, "r", encoding="utf-8") as f:
            base_gj = json.load(f)
        years = sorted(dfA["year"].unique())
        for y in years:
            df_y = dfA[dfA["year"] == y]
            combos = sorted(df_y[["transaction", "property_type"]].drop_duplicates().itertuples(index=False, name=None))
            for transaction, ptype in combos:
                sub = df_y[(df_y["transaction"] == transaction) & (df_y["property_type"] == ptype)]
                # Build lookup per UID of all metrics we have in A
                cols = ["avg_std_price", "median_std_price", "min_std_price", "max_std_price", "count_listings"]
                lookup = sub.set_index("neighborhood_uid")[cols].to_dict(orient="index")
                # Clone base geojson and enrich properties
                gj = {"type": "FeatureCollection", "features": []}
                for feat in base_gj.get("features", []):
                    props = dict(feat.get("properties", {}))
                    uid = props.get(args.uid_key)
                    metrics = lookup.get(uid)
                    if metrics:
                        # add metrics with a clear namespace
                        for k, v in metrics.items():
                            props[f"{transaction}_{ptype}_{k}"] = v
                        props["year"] = int(y)
                        props["_layer"] = f"{transaction}_{ptype}"
                    new_feat = {"type": "Feature", "geometry": feat.get("geometry"), "properties": props}
                    gj["features"].append(new_feat)
                out_path = os.path.join(args.outdir, f"geoA_{y}_{transaction}_{ptype}.geojson")
                with open(out_path, "w", encoding="utf-8") as fo:
                    json.dump(gj, fo, ensure_ascii=False)
                print(f"Saved enriched GeoJSON → {out_path}")| C: {len(dfC)}")

    # Optional maps (Dataset A only)
    if args.make-maps:
        if args.geojson is None:
            raise RuntimeError("--geojson is required when --make-maps is set")
        years = sorted(dfA["year"].unique())
        for y in years:
            out_html = os.path.join(args.outdir, f"map_A_{y}.html")
            make_map_for_year(dfA, int(y), args.geojson, out_html, args.center_lat, args.center_lon, args.zoom, args.uid_key, args.label_key, args.value_col)


if __name__ == "__main__":
    main()
