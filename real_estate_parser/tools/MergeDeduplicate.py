#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
MergeDeduplicate_v4.py

Purpose:
Conservative deduplication of SDG-11 real-estate listings.

Key principles:
- Listing ID is preserved but NOT used for uniqueness
- Deduplication only within the same month
- Cross-month relistings preserved
- Canonical = first seen (earliest date)
- Duplicates exported separately (full transparency)
"""

import argparse
import pandas as pd
from pathlib import Path
import hashlib


def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, help="Input CSV file")
    ap.add_argument("--out-canonical", required=True, help="Output canonical CSV")
    ap.add_argument("--out-duplicates", required=True, help="Output duplicates CSV")
    return ap.parse_args()


def normalize_text(x):
    if pd.isna(x):
        return ""
    return (
        str(x)
        .lower()
        .strip()
        .replace("á", "a")
        .replace("é", "e")
        .replace("í", "i")
        .replace("ó", "o")
        .replace("ú", "u")
    )


def build_dedup_key(row):
    """
    Build a SAFE deduplication key.
    Every component is explicitly cast to string.
    """
    parts = [
        normalize_text(row.get("title")),
        normalize_text(row.get("neighborhood")),
        str(row.get("bedrooms") or ""),
        str(row.get("bathrooms") or ""),
        str(row.get("area_m2") or ""),
        str(row.get("AT") or ""),
        str(row.get("price") or ""),
        normalize_text(row.get("transaction")),
        str(row.get("year_month") or ""),
    ]

    raw = "|".join(parts)
    return hashlib.md5(raw.encode("utf-8")).hexdigest()


def main():
    args = parse_args()

    # ---- read input ----
    df = pd.read_csv(args.input, dtype=str)

    # ---- normalize date → year-month ----
    df["date"] = pd.to_datetime(df.get("date"), errors="coerce")
    df["year_month"] = df["date"].dt.strftime("%Y-%m")
    df["year_month"] = df["year_month"].fillna("")

    # ---- build dedup key (Listing ID intentionally excluded) ----
    df["dedup_key"] = df.apply(build_dedup_key, axis=1)

    # ---- assign dedup groups ----
    df["dedup_group_id"] = df.groupby("dedup_key").ngroup()
    df["dedup_role"] = "DUPLICATE"

    # ---- canonical = earliest date (first seen) ----
    canonical_idx = (
        df.sort_values("date", na_position="last")
        .groupby("dedup_key", as_index=False)
        .head(1)
        .index
    )

    df.loc[canonical_idx, "dedup_role"] = "CANONICAL"

    # ---- remove exact ingestion artifacts ONLY ----
    df = df.drop_duplicates(
        subset=[
            "dedup_key",
            "source_file",
            "ingestion_id",
        ]
    )

    # ---- split outputs ----
    df_canonical = df[df["dedup_role"] == "CANONICAL"].copy()
    df_duplicates = df[df["dedup_role"] == "DUPLICATE"].copy()

    # ---- write outputs ----
    Path(args.out_canonical).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out_duplicates).parent.mkdir(parents=True, exist_ok=True)

    df_canonical.to_csv(args.out_canonical, index=False)
    df_duplicates.to_csv(args.out_duplicates, index=False)

    # ---- report ----
    print("[OK] Deduplication completed")
    print(f"  Canonical records : {len(df_canonical)}")
    print(f"  Duplicate records : {len(df_duplicates)}")
    print(f"[OUT] {args.out_canonical}")
    print(f"[OUT] {args.out_duplicates}")

    missing_dates = (df["year_month"] == "").sum()
    if missing_dates > 0:
        print(f"[WARN] {missing_dates} records have missing or invalid dates")


if __name__ == "__main__":
    main()
