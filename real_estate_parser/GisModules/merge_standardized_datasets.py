#!/usr/bin/env python3
"""
Merge standardized final datasets (2010, 2015, 2020) into a single "universe" CSV
and per-year consolidated files. Designed to work with your project folder layout:

output/
  consolidated/
    2010/
    2015/
    2020/

The script will:
1) Discover CSVs in each year folder (glob pattern can be customized).
2) Normalize columns → target schema:
   listing_id, neighborhood_uid, neighborhood_label, transaction,
   property_type, date, std_price, bedrooms, rent_basis
3) Concatenate rows across all discovered files, ensure types, drop exact dupes.
4) Write:
   - output/consolidated/universe_2010_2015_2020.csv
   - output/consolidated/2010/consolidated_2010.csv (and for 2015, 2020)

Usage
-----
python merge_standardized_datasets.py \
  --root output/consolidated \
  --years 2010 2015 2020 \
  --pattern "*.csv" \
  --outfile output/consolidated/universe_2010_2015_2020.csv

Notes
-----
- If your files already have normalized monthly rents, `rent_basis` can simply be
  "monthly". If some entries were converted from daily, pass that column through
  (recognized synonyms below) so it isn’t lost.
- Synonym mapping is included for common column name variations.
"""
from __future__ import annotations
import argparse
import sys
from pathlib import Path
from typing import Dict, List

import pandas as pd

TARGET_COLUMNS = [
    "listing_id",
    "neighborhood_uid",
    "neighborhood_label",
    "transaction",       # Rent | Sale
    "property_type",     # Apartment | House | Room | etc.
    "date",              # YYYY-MM-DD or YYYY-MM
    "std_price",         # numeric (monthly for rents)
    "bedrooms",          # may be NaN for sales/land
    "rent_basis",        # monthly | daily_converted | weekly_converted | unknown
]

# Common synonyms → target field
SYNONYMS: Dict[str, str] = {
    # IDs / neighborhood
    "id": "listing_id",
    "listingid": "listing_id",
    "listing_id": "listing_id",
    "neigh_uid": "neighborhood_uid",
    "neigh_id": "neighborhood_uid",
    "neighborhood_id": "neighborhood_uid",
    "neigh_final": "neighborhood_label",
    "neighborhood": "neighborhood_label",
    "neighborhood_name": "neighborhood_label",
    "neigh": "neighborhood_label",

    # transaction / type
    "deal_type": "transaction",
    "transaction_type": "transaction",
    "operation": "transaction",
    "type": "property_type",
    "prop_type": "property_type",
    "property": "property_type",

    # time
    "posted_date": "date",
    "created_at": "date",
    "year_month": "date",

    # price
    "price": "std_price",
    "stdprice": "std_price",
    "amount": "std_price",
    "monthly_price": "std_price",

    # bedrooms
    "beds": "bedrooms",
    "br": "bedrooms",

    # rent basis
    "price_basis": "rent_basis",
    "rent_unit": "rent_basis",
    "rentbasis": "rent_basis",
}


def coerce_columns(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    # Ensure all target columns exist
    for col in TARGET_COLUMNS:
        if col not in out.columns:
            out[col] = pd.NA

    # Types
    out["listing_id"] = out["listing_id"].astype(str).str.strip()
    out["neighborhood_uid"] = out["neighborhood_uid"].astype(str).str.strip()
    out["neighborhood_label"] = out["neighborhood_label"].astype(str).str.strip()
    out["transaction"] = out["transaction"].astype(str).str.strip().str.title()  # Rent/Sale
    out["property_type"] = out["property_type"].astype(str).str.strip().str.title()

    # date: keep as string; optionally normalize to YYYY-MM-DD where possible
    out["date"] = out["date"].astype(str).str.strip()

    # price numeric
    out["std_price"] = pd.to_numeric(out["std_price"], errors="coerce")

    # bedrooms numeric
    out["bedrooms"] = pd.to_numeric(out["bedrooms"], errors="coerce")

    # rent_basis fallback
    out["rent_basis"] = out["rent_basis"].fillna("monthly")

    return out[TARGET_COLUMNS]


def standardize_columns(df: pd.DataFrame) -> pd.DataFrame:
    # Lowercase all columns for mapping
    mapper = {c: SYNONYMS.get(c.lower(), c) for c in df.columns}
    std = df.rename(columns=mapper)
    # If both neighborhood_uid and label missing, try to split a composite field
    if "neighborhood_uid" not in std.columns and "uid" in std.columns:
        std = std.rename(columns={"uid": "neighborhood_uid"})
    if "neighborhood_label" not in std.columns and "label" in std.columns:
        std = std.rename(columns={"label": "neighborhood_label"})
    return std


def load_and_standardize(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    df = standardize_columns(df)
    df = coerce_columns(df)
    return df


def discover_files(year_dir: Path, pattern: str) -> List[Path]:
    return sorted(list(year_dir.rglob(pattern)))


def consolidate_year(year: int, base: Path, pattern: str) -> pd.DataFrame:
    ydir = base / str(year)
    if not ydir.exists():
        print(f"[WARN] Missing directory for {year}: {ydir}")
        return pd.DataFrame(columns=TARGET_COLUMNS)

    files = discover_files(ydir, pattern)
    if not files:
        print(f"[WARN] No files matched pattern in {ydir}: {pattern}")
        return pd.DataFrame(columns=TARGET_COLUMNS)

    frames = []
    for fp in files:
        try:
            df = load_and_standardize(fp)
            frames.append(df)
            print(f"[OK] Loaded {fp} → {len(df):,} rows")
        except Exception as e:
            print(f"[ERR] Failed to load {fp}: {e}")

    if not frames:
        return pd.DataFrame(columns=TARGET_COLUMNS)

    year_df = pd.concat(frames, ignore_index=True)

    # Add year column if not derivable from date easily
    if "year" not in year_df.columns:
        year_df.insert(0, "year", year)

    # Drop exact duplicates
    year_df = year_df.drop_duplicates()

    return year_df


def main():
    ap = argparse.ArgumentParser(description="Merge standardized final datasets (2010, 2015, 2020)")
    ap.add_argument("--root", default="output/consolidated", help="Root directory that contains year subfolders")
    ap.add_argument("--years", nargs="+", type=int, default=[2010, 2015, 2020], help="Years to include")
    ap.add_argument("--pattern", default="*.csv", help="Glob pattern to discover input CSVs inside each year folder")
    ap.add_argument("--outfile", default="output/consolidated/universe_2010_2015_2020.csv", help="Output CSV path for the merged universe")
    ap.add_argument("--write-per-year", action="store_true", help="Also write consolidated_<year>.csv in each year folder")

    args = ap.parse_args()

    root = Path(args.root)
    root.mkdir(parents=True, exist_ok=True)

    all_frames: List[pd.DataFrame] = []
    for y in args.years:
        dfy = consolidate_year(y, root, args.pattern)
        if len(dfy):
            all_frames.append(dfy)
            if args.write_per_year:
                outy = root / str(y) / f"consolidated_{y}.csv"
                outy.parent.mkdir(parents=True, exist_ok=True)
                dfy.to_csv(outy, index=False)
                print(f"[SAVE] {outy} → {len(dfy):,} rows")

    if not all_frames:
        print("[EXIT] No input data found. Check --root/--pattern.")
        sys.exit(1)

    universe = pd.concat(all_frames, ignore_index=True)

    # Consistency tweaks
    # Normalize transaction values
    universe["transaction"] = universe["transaction"].str.strip().str.title()
    universe["property_type"] = universe["property_type"].str.strip().str.title()

    # Optional: ensure rents are monthly; if flagged as daily_converted/weekly_converted that’s fine
    # (Assumes upstream normalization done already.)

    outpath = Path(args.outfile)
    outpath.parent.mkdir(parents=True, exist_ok=True)
    universe.to_csv(outpath, index=False)
    print(f"[SAVE] {outpath} → {len(universe):,} rows (columns: {', '.join(universe.columns)})")


if __name__ == "__main__":
    main()
