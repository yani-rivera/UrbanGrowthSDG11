# --- DROP-IN PATCH for gis_data_sets_multiyear.py ---
# Paste these helpers near the top (imports: json, folium, branca.cm if not present)

import json
import folium
import branca.colormap as cm
import pandas as pd


def _pick_value_col(df: pd.DataFrame, requested: str | None) -> str:
    """Return a valid numeric value column for the choropleth.
    Prefers the `requested` name; otherwise tries common fallbacks.
    Raises if none found.
    """
    if requested and requested in df.columns:
        return requested
    candidates = [
        "avg_std_price", "median_std_price", "avg_price", "median_price",
        "avg_price_per_bed", "median_price_per_bed", "count",
    ]
    for c in candidates:
        if c in df.columns:
            return c
    # last resort: first numeric column after UID
    numeric = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
    if numeric:
        return numeric[0]
    raise ValueError("No valid numeric value column found for choropleth.")


def _prep_for_map(df: pd.DataFrame, year: int, uid_key: str, label_key: str | None,
                  value_col: str | None) -> pd.DataFrame:
    """Ensure the frame has the right year, columns, and types for joining by UID."""
    if "year" in df.columns:
        df = df[df["year"].astype(str) == str(year)].copy()
    # replicate UID if requested key doesn't exist but a canonical one does
    if uid_key not in df.columns:
        for alt in ("neighborhood_uid", "GISID", "gisid", "uid", "neigh_uid"):
            if alt in df.columns:
                df[uid_key] = df[alt]
                break
    if uid_key not in df.columns:
        raise KeyError(f"UID column '{uid_key}' not found in dataframe; available: {list(df.columns)}")

    # coerce types
    df[uid_key] = df[uid_key].astype(str).str.strip()

    # choose value column
    value_col = _pick_value_col(df, value_col)
    df[value_col] = pd.to_numeric(df[value_col], errors="coerce")

    # drop rows with missing value/uid
    df = df.dropna(subset=[uid_key, value_col])

    # optional label
    if label_key and label_key in df.columns:
        df[label_key] = df[label_key].astype(str)
    else:
        label_key = None

    # keep only required columns
    cols = [uid_key, value_col] + ([label_key] if label_key else [])
    return df[cols].drop_duplicates()


def make_map(df: pd.DataFrame, year: int, geojson_path: str, out_html: str,
             value_col: str | None = None, uid_key: str = "neighborhood_uid",
             label_key: str | None = None, center_lat: float | None = None,
             center_lon: float | None = None, zoom: int = 12, caption: str = "") -> None:
    """Render a Folium choropleth joined strictly by UID.

    Requirements:
      - df has a column named exactly like `uid_key` (or an alt that we copy from)
      - GeoJSON features contain the same property name `uid_key`
    """
    # Prep data
    gdf = _prep_for_map(df, year, uid_key=uid_key, label_key=label_key, value_col=value_col)
    value_col = [c for c in gdf.columns if c != uid_key and c != (label_key or "")][0]

    # load GeoJSON and verify property
    with open(geojson_path, "r", encoding="utf-8") as f:
        gj = json.load(f)
    # check uid property exists in features
    sample_props = gj["features"][0]["properties"] if gj.get("features") else {}
    if uid_key not in sample_props:
        raise KeyError(f"GeoJSON missing uid_key '{uid_key}'. Available keys include: {list(sample_props.keys())[:20]}")

    # compute map center if not provided
    if center_lat is None or center_lon is None:
        # try to read bbox center
        try:
            # naive center from first polygon bbox if present
            center_lat, center_lon = 14.0818, -87.2068  # fallback (TGU approx)
        except Exception:
            center_lat, center_lon = 14.0818, -87.2068

    # color scale
    vmin, vmax = float(gdf[value_col].min()), float(gdf[value_col].max())
    if not pd.notna(vmin) or not pd.notna(vmax):
        raise ValueError("No numeric data to map after filtering.")
    if vmax <= vmin:
        vmax = vmin + 1.0
    cmap = cm.linear.Blues_09.scale(vmin, vmax)

    m = folium.Map(location=[center_lat, center_lon], zoom_start=zoom, control_scale=True, tiles="cartodbpositron")

    # Choropleth joined by UID
    folium.Choropleth(
        geo_data=gj,
        name=f"{caption} ({year})",
        data=gdf,
        columns=[uid_key, value_col],
        key_on=f"feature.properties.{uid_key}",
        fill_color="Blues",
        fill_opacity=0.7,
        line_opacity=0.6,
        nan_fill_opacity=0.0,
        legend_name=f"{caption} ({value_col})",
    ).add_to(m)

    # Tooltip with label/value if label exists
    try:
        tip_fields = [uid_key, value_col] + ([label_key] if label_key else [])
        folium.GeoJson(
            gj,
            name="Neighborhoods",
            tooltip=folium.features.GeoJsonTooltip(fields=tip_fields,
                                                   aliases=["UID", value_col, "Label"][:len(tip_fields)],
                                                   sticky=True),
            style_function=lambda f: {"weight": 1, "color": "#666", "fillOpacity": 0},
        ).add_to(m)
    except Exception:
        pass

    folium.LayerControl(collapsed=False).add_to(m)
    cmap.caption = f"{caption} ({value_col})"
    cmap.add_to(m)

    m.save(out_html)
    print(f"[MAP] Saved → {out_html}  (rows={len(gdf)}, value_col={value_col}, uid_key={uid_key})")

# --- END PATCH ---
