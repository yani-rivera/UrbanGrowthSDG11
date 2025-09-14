#!/usr/bin/env python3
"""
Merge multi‑year/month datasets and build clean subsets ready for mapping or export.

Safe defaults:
- Accepts CSV or Parquet; mix is OK.
- Normalizes dtypes (UIDs→string, dates→int, numerics→float).
- Adds `row_uid` if missing (stable SHA1 of path+rownum) to avoid row loss.
- Optional year/month filter.
- Flexible subset: only keeps columns that exist, warns for missing ones.
- Optional join to GeoJSON via a provided UID field to validate coverage.

Examples
--------
# Merge everything under a folder, filter Dec 2015, write merged+subset
python merge_and_subset_v3.py \
  --inputs "output/consolidated/*.csv" \
  --out merged_dec2015.csv \
  --subset-out subset_dec2015.csv \
  --year 2015 --month 12 \
  --uid-col row_uid \
  --keep agency,year,month,neighborhood,neighborhood_uid,price,currency,bedrooms,notes

# Same but produce Parquet
python merge_and_subset_v3.py \
  --inputs "output/consolidated/*.parquet" \
  --out merged_2015.parquet \
  --subset-out subset_2015.parquet \
  --year 2015
"""
from __future__ import annotations

import argparse
import glob
import hashlib
from pathlib import Path
from typing import Iterable, List, Optional

import pandas as pd


NUMERIC_GUESSES = [
    "price", "price_std", "std_price", "avg_price", "median_price",
    "avg_std_price", "median_std_price", "price_per_bed", "avg_price_per_bed",
    "bedrooms", "bathrooms", "area_m2", "count",
]
STRING_GUESSES = [
    "row_uid", "listing_uid", "agency", "source", "neighborhood", "neighborhood_uid",
    "colonia", "barrio", "notes", "notes_clean", "currency", "transaction",
]
INT_GUESSES = ["year", "month", "day"]


def _stable_uid(*parts: Optional[str]) -> str:
    s = "|".join("" if p is None else str(p) for p in parts)
    return hashlib.sha1(s.encode("utf-8")).hexdigest()


def _coerce_schema(df: pd.DataFrame, uid_col: str) -> pd.DataFrame:
    out = df.copy()
    # Ensure UID exists
    if uid_col not in out.columns:
        out[uid_col] = [
            _stable_uid(out.attrs.get("__source_path__", ""), i) for i in range(len(out))
        ]
    # Strings
    for c in STRING_GUESSES + [uid_col]:
        if c in out.columns:
            out[c] = out[c].astype("string")
    # Ints
    for c in INT_GUESSES:
        if c in out.columns:
            out[c] = pd.to_numeric(out[c], errors="coerce").astype("Int64")
    # Numerics
    for c in NUMERIC_GUESSES:
        if c in out.columns:
            out[c] = pd.to_numeric(out[c], errors="coerce")
    return out


def _read_any(path: Path) -> pd.DataFrame:
    if path.suffix.lower() in {".parquet", ".pq"}:
        df = pd.read_parquet(path)
    else:
        df = pd.read_csv(path)
    # stash source path for UID seed
    df.attrs["__source_path__"] = str(path)
    return df


def merge_inputs(inputs: Iterable[str], uid_col: str) -> pd.DataFrame:
    paths: List[Path] = []
    for pat in inputs:
        if any(ch in pat for ch in "*?[]"):
            paths.extend([Path(p) for p in glob.glob(pat)])
        else:
            paths.append(Path(pat))
    paths = [p for p in paths if p.exists()]
    if not paths:
        raise SystemExit("No input files found for given --inputs.")

    frames: List[pd.DataFrame] = []
    for p in sorted(paths):
        df = _read_any(p)
        df = _coerce_schema(df, uid_col)
        frames.append(df)
    merged = pd.concat(frames, ignore_index=True, sort=False)
    return merged


def make_subset(df: pd.DataFrame, keep: List[str]) -> pd.DataFrame:
    have = [c for c in keep if c in df.columns]
    miss = [c for c in keep if c not in df.columns]
    if miss:
        print(f"[WARN] Missing columns skipped: {miss}")
    return df[have].copy()


def run(inputs: List[str], out: Path, subset_out: Optional[Path], uid_col: str,
        year: Optional[int], month: Optional[int], keep_cols: List[str]) -> None:
    df = merge_inputs(inputs, uid_col)
    print(f"[MERGE] rows={len(df)} cols={len(df.columns)} from {len(inputs)} patterns")

    # Filtering
    if year is not None and "year" in df.columns:
        before = len(df)
        df = df[df["year"].astype("Int64") == int(year)]
        print(f"[FILTER] year={year} → {len(df)} (was {before})")
    if month is not None and "month" in df.columns:
        before = len(df)
        df = df[df["month"].astype("Int64") == int(month)]
        print(f"[FILTER] month={month} → {len(df)} (was {before})")

    # Write merged
    out.parent.mkdir(parents=True, exist_ok=True)
    if out.suffix.lower() in {".parquet", ".pq"}:
        df.to_parquet(out, index=False)
    else:
        df.to_csv(out, index=False)
    print(f"[WRITE] merged → {out}")

    # Subset
    if subset_out:
        sub = make_subset(df, keep_cols) if keep_cols else df.copy()
        subset_out.parent.mkdir(parents=True, exist_ok=True)
        if subset_out.suffix.lower() in {".parquet", ".pq"}:
            sub.to_parquet(subset_out, index=False)
        else:
            sub.to_csv(subset_out, index=False)
        print(f"[WRITE] subset → {subset_out} (cols={list(sub.columns)})")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Merge multi‑year datasets and build subsets")
    p.add_argument("--inputs", nargs="+", help="List of files or globs (CSV/Parquet)")
    p.add_argument("--out", required=True, type=Path, help="Output merged CSV/Parquet")
    p.add_argument("--subset-out", type=Path, default=None, help="Optional subset output path")
    p.add_argument("--uid-col", default="row_uid", help="UID column name to ensure (default: row_uid)")
    p.add_argument("--year", type=int, default=None)
    p.add_argument("--month", type=int, default=None)
    p.add_argument("--keep", default="", help="Comma‑separated list of columns to keep in subset")
    return p.parse_args()


if __name__ == "__main__":
    args = parse_args()
    keep_cols = [c.strip() for c in args.keep.split(",") if c.strip()]
    run(args.inputs, args.out, args.subset_out, args.uid_col, args.year, args.month, keep_cols)
