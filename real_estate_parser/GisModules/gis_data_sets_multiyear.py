#!/usr/bin/env python3
"""
GisDataSetsMultiyear.py

Build QGIS/Folium-ready datasets across multiple years from a per-listing universe.
Creates neighborhood aggregates for:
  A) Avg price by neighborhood (Rent/Sale × House/Apartment/Room)
  B) Avg price per bedroom by neighborhood (requires bedrooms >= 1)

Optionally exports Folium choropleth maps for A and B.

Inputs
------
• --universe: a CSV file OR a directory containing multiple universe CSVs
    Universe must contain (case-sensitive):
      listing_id (recommended), neighborhood_uid, neighborhood_label,
      transaction, property_type, date (YYYY-MM-DD), std_price,
      bedrooms (for B)

• --geojson: neighborhood polygons (for maps and enriched outputs)

Outputs (in --outdir)
---------------------
• CSVs per year:
    A_price_by_neigh_<YEAR>.csv
    B_price_bed_by_neigh_<YEAR>.csv
• Combined multi-year CSVs:
    A_price_by_neigh_ALL.csv
    B_price_bed_by_neigh_ALL.csv
• Optional Folium maps per year:
    map_A_<YEAR>.html  (value = avg_std_price by default)
    map_B_<YEAR>.html  (value = avg_price_per_bed)

Usage
-----
python GisDataSetsMultiyear.py \
  --universe output/universe/ \
  --outdir output/gis \
  --geojson data/neighborhoods.geojson \
  --years 2010 2015 \
  --types House Apartment Room \
  --min-count 3 \
  --make-maps
"""
from __future__ import annotations
import argparse
import os
import json
from typing import List, Optional
import pandas as pd

try:
    import folium
    from folium.features import GeoJson, GeoJsonTooltip
    from branca.colormap import LinearColormap
except Exception:
    folium = None

# -------------------- IO helpers --------------------

def read_universe(path: str) -> pd.DataFrame:
    if os.path.isdir(path):
        frames = []
        for fn in sorted(os.listdir(path)):
            if fn.lower().endswith('.csv'):
                frames.append(pd.read_csv(os.path.join(path, fn)))
        if not frames:
            raise RuntimeError(f"No CSV files found in directory: {path}")
        return pd.concat(frames, ignore_index=True)
    else:
        return pd.read_csv(path)

# -------------------- Cleaning & typing --------------------

def coerce_types(df: pd.DataFrame) -> pd.DataFrame:
    # date → year, year_month
    if 'year' not in df.columns:
        df['year'] = pd.to_datetime(df['date'], errors='coerce').dt.year
    if 'year_month' not in df.columns:
        dt = pd.to_datetime(df['date'], errors='coerce')
        df['year_month'] = dt.dt.to_period('M').astype(str)
    # numerics
    df['std_price'] = pd.to_numeric(df['std_price'], errors='coerce')
    if 'bedrooms' in df.columns:
        df['bedrooms'] = pd.to_numeric(df['bedrooms'], errors='coerce')
    return df

# -------------------- Filters / subsets --------------------

def filter_in_scope(df: pd.DataFrame, types: List[str]) -> pd.DataFrame:
    keep = df['std_price'].notna() & (df['std_price'] > 0)
    keep &= df['neigh_uid'].notna() & (df['neigh_uid'] != 'UNMATCHED')
    keep &= df['transaction'].isin(['Rent','Sale'])
    keep &= df['property_type'].isin(types)
    return df[keep].copy()

# -------------------- Aggregations --------------------

def agg_A(df: pd.DataFrame, min_count: int) -> pd.DataFrame:
    g = df.groupby(['neigh_uid','neighborhood_label','property_type','transaction','year'])['std_price']
    out = g.agg(avg_std_price='mean', median_std_price='median', min_std_price='min', max_std_price='max', count_listings='count').reset_index()
    return out[out['count_listings'] >= min_count]

def agg_B(df: pd.DataFrame, min_count: int) -> pd.DataFrame:
    dfb = df[df['bedrooms'].notna() & (df['bedrooms'] >= 1)].copy()
    dfb['price_per_bed'] = dfb['std_price'] / dfb['bedrooms']
    g = dfb.groupby(['neigh_uid','neighborhood_label','property_type','transaction','year'])['price_per_bed']
    out = g.agg(avg_price_per_bed='mean', median_price_per_bed='median', min_price_per_bed='min', max_price_per_bed='max', count_listings='count').reset_index()
    return out[out['count_listings'] >= min_count]

# -------------------- Folium maps --------------------

def colormap(vmin: float, vmax: float) -> LinearColormap:
    return LinearColormap(['#f7fbff','#deebf7','#c6dbef','#9ecae1','#6baed6','#3182bd','#08519c'], vmin=vmin, vmax=vmax)


def add_layer(m, gjson: dict, df_year: pd.DataFrame, value_col: str, uid_key: str, label_key: str, layer_caption: str):
    combos = sorted(df_year[['transaction','property_type']].drop_duplicates().itertuples(index=False, name=None))
    for trn, ptype in combos:
        sub = df_year[(df_year['transaction']==trn) & (df_year['property_type']==ptype)]
        if sub.empty:
            continue
        vmin, vmax = float(sub[value_col].min()), float(sub[value_col].max())
        if vmax == vmin:
            vmax = vmin + 1e-6
        cmap = colormap(vmin, vmax)
        values = dict(zip(sub['neigh_uid'], sub[value_col]))
        labels = dict(zip(sub['neigh_uid'], sub['neighborhood_label']))
        def style_fn(feat):
            uid = feat['properties'].get(uid_key)
            val = values.get(uid)
            if val is None:
                return {'fillOpacity': 0.0, 'weight': 0.4, 'color': '#888888'}
            return {'fillColor': cmap(val), 'fillOpacity': 0.85, 'weight': 0.4, 'color': '#666666'}
        gj = GeoJson(
            data=gjson,
            name=f"{trn} – {ptype} {layer_caption}",
            style_function=style_fn,
            tooltip=GeoJsonTooltip(fields=[uid_key], aliases=['UID:'], sticky=True)
        )
        # enrich tooltips
        for feat in gj.data['features']:
            uid = feat['properties'].get(uid_key)
            lbl = labels.get(uid, feat['properties'].get(label_key, uid))
            val = values.get(uid)
            feat['properties']['_popup'] = f"{lbl}<br>{trn} – {ptype}: {val:,.2f}" if val is not None else f"{lbl}<br>No data"
        gj.add_to(m)
        cmap.caption = f"{trn} – {ptype} {layer_caption} ({value_col})"
        cmap.add_to(m)


def make_map(df: pd.DataFrame, year: int, geojson_path: str, out_html: str, value_col: str, uid_key: str, label_key: str, center_lat: float, center_lon: float, zoom: int, caption: str):
    if folium is None:
        print('[warn] folium/branca not installed; skipping maps')
        return
    with open(geojson_path, 'r', encoding='utf-8') as f:
        gjson = json.load(f)
    m = folium.Map(location=[center_lat, center_lon], zoom_start=zoom, tiles='cartodbpositron')
    df_y = df[df['year']==year]
    add_layer(m, gjson, df_y, value_col=value_col, uid_key=uid_key, label_key=label_key, layer_caption=f'({year}) {caption}')
    folium.LayerControl(collapsed=False).add_to(m)
    m.save(out_html)
    print(f"Saved map → {out_html}")

# -------------------- CLI --------------------

def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description='Build multi-year GIS datasets (A: price, B: price per bed) and optional Folium maps.')
    ap.add_argument('--universe', required=True, help='Universe CSV or directory of CSVs')
    ap.add_argument('--outdir', required=True, help='Output directory')
    ap.add_argument('--geojson', default=None, help='Neighborhood GeoJSON (required for maps)')
    ap.add_argument('--years', nargs='*', type=int, default=None, help='Subset of years to process')
    ap.add_argument('--types', nargs='*', default=['House','Apartment','Room'], help='Property types to include')
    ap.add_argument('--min-count', type=int, default=3, help='Minimum listings per group')
    ap.add_argument('--uid-key', default='neigh_uid', help='GeoJSON & CSV join key')
    ap.add_argument('--label-key', default='neighborhood_label', help='Display label column')
    ap.add_argument('--center-lat', type=float, default=14.072, help='Map center lat')
    ap.add_argument('--center-lon', type=float, default=-87.206, help='Map center lon')
    ap.add_argument('--zoom', type=int, default=12, help='Map zoom')
    ap.add_argument('--make-maps', action='store_true', help='Generate Folium maps for A and B')
    ap.add_argument('--map-A', action='store_true', help='Map Dataset A (avg_std_price)')
    ap.add_argument('--map-B', action='store_true', help='Map Dataset B (avg_price_per_bed)')
    return ap.parse_args()

# -------------------- Main --------------------

def main():
    args = parse_args()
    os.makedirs(args.outdir, exist_ok=True)

    df = read_universe(args.universe)
    df = coerce_types(df)
    df = filter_in_scope(df, args.types)

    if args.years:
        df = df[df['year'].isin(set(args.years))]
        if df.empty:
            raise RuntimeError('No rows after year filter')

    dfA = agg_A(df, args.min_count)
    dfB = agg_B(df, args.min_count)

    # write per-year
    for y, sub in dfA.groupby('year'):
        sub.sort_values(['neigh_uid','transaction','property_type'], inplace=True)
        sub.to_csv(os.path.join(args.outdir, f'A_price_by_neigh_{int(y)}.csv'), index=False)
    for y, sub in dfB.groupby('year'):
        sub.sort_values(['neigh_uid','transaction','property_type'], inplace=True)
        sub.to_csv(os.path.join(args.outdir, f'B_price_bed_by_neigh_{int(y)}.csv'), index=False)

    # write ALL
    dfA.sort_values(['year','neigh_uid','transaction','property_type'], inplace=True)
    dfA.to_csv(os.path.join(args.outdir, 'A_price_by_neigh_ALL.csv'), index=False)
    dfB.sort_values(['year','neigh_uid','transaction','property_type'], inplace=True)
    dfB.to_csv(os.path.join(args.outdir, 'B_price_bed_by_neigh_ALL.csv'), index=False)

    print(f"Saved: A({len(dfA)}) rows, B({len(dfB)}) rows")

    if args.make_maps:
        if not args.geojson:
            raise RuntimeError('--geojson is required to make maps')
        years = sorted(dfA['year'].unique())
        if args.map_A or (not args.map_A and not args.map_B):
            # default: map A
            for y in years:
                make_map(dfA, int(y), args.geojson, os.path.join(args.outdir, f'map_A_{int(y)}.html'),
                         value_col='avg_std_price', uid_key=args.uid_key, label_key=args.label_key,
                         center_lat=args.center_lat, center_lon=args.center_lon, zoom=args.zoom,
                         caption='Avg price')
        if args.map_B:
            yearsB = sorted(dfB['year'].unique())
            for y in yearsB:
                make_map(dfB, int(y), args.geojson, os.path.join(args.outdir, f'map_B_{int(y)}.html'),
                         value_col='avg_price_per_bed', uid_key=args.uid_key, label_key=args.label_key,
                         center_lat=args.center_lat, center_lon=args.center_lon, zoom=args.zoom,
                         caption='Avg price per bed')

if __name__ == '__main__':
    main()
