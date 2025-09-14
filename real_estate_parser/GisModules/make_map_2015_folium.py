
#!/usr/bin/env python3
"""
make_map_2015_folium.py — Build interactive Folium maps for 2015 averages

Creates 4 toggleable choropleth layers from your 2015 aggregates:
  • Rent – Apartment
  • Rent – House
  • Sale – Apartment
  • Sale – House

Inputs
------
• Neighborhood polygons as GeoJSON (must contain a key that joins to CSV, e.g., neighborhood_uid)
• 2015 CSVs already split (as produced earlier):
    Rent_Apartment_2015.csv
    Rent_House_2015.csv
    Sale_Apartment_2015.csv
    Sale_House_2015.csv

Each CSV must have columns:
  neighborhood_uid, neighborhood_label, transaction, property_type, Average of std_price

Usage
-----
python make_map_2015_folium.py \
  --geojson data/neighborhoods.geojson \
  --csv-dir data/2015 \
  --uid-key neighborhood_uid \
  --label-key neighborhood_label \
  --value-col "Average of std_price" \
  --out map_2015.html

Notes
-----
• If your GeoJSON uses a different property for the UID, pass it via --uid-key.
• If you only have labels to join, set --uid-key neighborhood_label (but UID is safest).
• The script makes separate color scales per layer (values differ for Rent vs Sale etc.).
"""
from __future__ import annotations
import argparse
import os
import pandas as pd
import folium
from folium.features import GeoJson, GeoJsonTooltip
import json
from branca.colormap import LinearColormap

LAYER_SPECS = [
    ("Rent – Apartment",   "Rent_Apartment_2015.csv"),
    ("Rent – House",       "Rent_House_2015.csv"),
    ("Sale – Apartment",   "Sale_Apartment_2015.csv"),
    ("Sale – House",       "Sale_House_2015.csv"),
]


def load_geojson(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def minmax(series):
    s = pd.to_numeric(series, errors="coerce").dropna()
    if s.empty:
        return 0.0, 1.0
    return float(s.min()), float(s.max())


def build_colormap(vmin: float, vmax: float) -> LinearColormap:
    # 7-step ramp; adjust colors to taste
    return LinearColormap(
        ["#f7fbff", "#deebf7", "#c6dbef", "#9ecae1", "#6baed6", "#3182bd", "#08519c"],
        vmin=vmin,
        vmax=vmax,
    )


def add_choropleth_layer(m: folium.Map, gjson: dict, df: pd.DataFrame, uid_key: str, label_key: str, value_col: str, layer_name: str):
    # Prepare a lookup from uid → value/label
    value_by_uid = dict(zip(df[uid_key], df[value_col]))
    label_by_uid = dict(zip(df[uid_key], df[label_key]))

    # Compute color scale from data actually present in this layer
    vmin, vmax = minmax(df[value_col])
    if vmax == vmin:
        vmax = vmin + 1e-6
    cmap = build_colormap(vmin, vmax)

    def style_fn(feature):
        uid = feature["properties"].get(uid_key)
        val = value_by_uid.get(uid)
        if val is None:
            # not in this layer → transparent fill
            return {
                "fillOpacity": 0.0,
                "weight": 0.5,
                "color": "#888888",
            }
        # choropleth color
        return {
            "fillColor": cmap(val),
            "fillOpacity": 0.8,
            "weight": 0.5,
            "color": "#666666",
        }

    def highlight_fn(feature):
        return {"weight": 2, "color": "#000000"}

    gj = GeoJson(
        gjson,
        name=layer_name,
        style_function=style_fn,
        highlight_function=highlight_fn,
        tooltip=GeoJsonTooltip(
            fields=[uid_key],
            aliases=["Neighborhood_uid:"],
            sticky=True,
        ),
    )

    # Enhance tooltip with label + value when present
    for feat in gj.data["features"]:
        uid = feat["properties"].get(uid_key)
        lbl = label_by_uid.get(uid, feat["properties"].get(label_key, ""))
        val = value_by_uid.get(uid)
        feat["properties"]["_popup"] = f"{lbl or uid}<br>{layer_name}: {val:,.2f}" if val is not None else f"{lbl or uid}<br>{layer_name}: n/a"

    gj.add_to(m)

    # Add a legend specific to this layer
    cmap.caption = f"{layer_name} — {value_col}"
    cmap.add_to(m)



def main():
    ap = argparse.ArgumentParser(description="Build a 2015 Folium map with 4 price layers.")
    ap.add_argument("--geojson", required=True, help="Neighborhood polygons GeoJSON path")
    ap.add_argument("--csv-dir", required=True, help="Directory containing the 4 split CSVs")
    ap.add_argument("--uid-key", default="neighborhood_uid", help="Join key present in both GeoJSON properties and CSV")
    ap.add_argument("--label-key", default="neighborhood_label", help="Label column in CSV (used in tooltip)")
    ap.add_argument("--value-col", default="Average of std_price", help="Numeric column to choropleth")
    ap.add_argument("--out", default="map_2015.html", help="Output HTML file")
    ap.add_argument("--center-lat", type=float, default=14.072, help="Initial map center latitude")
    ap.add_argument("--center-lon", type=float, default=-87.206, help="Initial map center longitude")
    ap.add_argument("--zoom", type=int, default=12, help="Initial zoom level")
    args = ap.parse_args()

    gjson = load_geojson(args.geojson)

    # Base map
    m = folium.Map(location=[args.center_lat, args.center_lon], zoom_start=args.zoom, tiles="cartodbpositron")

    # Load and add each layer
    for layer_name, fname in LAYER_SPECS:
        path = os.path.join(args.csv_dir, fname)
        if not os.path.exists(path):
            print(f"[warn] Missing CSV for layer '{layer_name}': {path}", flush=True)
            continue
        df = pd.read_csv(path)
        # Ensure join key exists in dataframe
        if args.uid_key not in df.columns:
            raise RuntimeError(f"CSV {fname} is missing join key column '{args.uid_key}'")
        if args.value_col not in df.columns:
            raise RuntimeError(f"CSV {fname} is missing value column '{args.value_col}'")
        # Add layer
        add_choropleth_layer(m, gjson, df, args.uid_key, args.label_key, args.value_col, layer_name)

    folium.LayerControl(collapsed=False).add_to(m)

    m.save(args.out)
    print(f"Saved map → {args.out}")


if __name__ == "__main__":
    main()
