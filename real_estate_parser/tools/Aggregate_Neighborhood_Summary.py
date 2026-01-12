#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Aggregate_2010_Neighborhood_Summary.py

Generate descriptive housing price summaries for 2010.

Output level:
(neighborhood_label, transaction, neighborhood_clean,
 neighborhood_uid, GISID, year_month, property_type_new)

Statistics:
min, max, mean, median, std, count
"""

import argparse
import pandas as pd
from pathlib import Path


def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, help="Input CSV (post-QC)")
    ap.add_argument("--output", required=True, help="Output CSV")
    ap.add_argument("--min-n", type=int, default=5,
                    help="Minimum listings per group")
    return ap.parse_args()


def main():
    args = parse_args()

    df = pd.read_csv(args.input, encoding="utf-8-sig")

    required_cols = {
        "neighborhood_label",
        "transaction",
        "neighborhood_clean",
        "neighborhood_uid",
        "GISID",
        "year_month",
        "property_type_new",
        "price_usd"
    }

    if not required_cols.issubset(df.columns):
        missing = required_cols - set(df.columns)
        raise RuntimeError(f"Missing required columns: {missing}")

    # Ensure numeric price
    df["price_usd"] = pd.to_numeric(df["price_usd"], errors="coerce")
    df = df[df["price_usd"].notna()]

    # Aggregate
    agg = (
        df.groupby([
            "neighborhood_label",
            "transaction",
            "neighborhood_clean",
            "neighborhood_uid",
            "GISID",
            "year_month",
            "property_type_new"
        ])
        .agg(
            price_min_usd=("price_usd", "min"),
            price_max_usd=("price_usd", "max"),
            price_avg_usd=("price_usd", "mean"),
            price_median_usd=("price_usd", "median"),
            price_std_usd=("price_usd", "std"),
            qty=("price_usd", "size")
        )
        .reset_index()
    )

    # Apply min-n rule
    agg = agg[agg["qty"] >= args.min_n]

    # Sort for readability
    agg = agg.sort_values([
        "year_month",
        "neighborhood_label",
        "transaction",
        "property_type_new"
    ])

    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    agg.to_csv(args.output, index=False, encoding="utf-8-sig")

    print("[OK] 2010 neighborhood summary generated")
    print("[OUT]", args.output)
    print("Rows:", len(agg))


if __name__ == "__main__":
    main()
