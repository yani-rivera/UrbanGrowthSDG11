#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Aggregate neighborhood housing prices by year.

Flexible version:
- Uses `area` column
- Keeps rows even if area / bedrooms are missing
- Adds price per area and beds per area (may be NULL)
"""

import argparse
import pandas as pd
from pathlib import Path


def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, help="Input CSV (post-QC)")
    ap.add_argument("--year", required=True, help="Year to extract (e.g. 2010)")
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
        "price_usd",
        "area",
        "bedrooms"
    }

    missing = required_cols - set(df.columns)
    if missing:
        raise RuntimeError(f"Missing required columns: {missing}")

    # ---- FILTER YEAR ----
    df = df[df["year_month"].astype(str).str.startswith(f"{args.year}-")].copy()
    if df.empty:
        raise RuntimeError(f"No data found for year {args.year}")

    # ---- NUMERIC COERCION ----
    df["price_usd"] = pd.to_numeric(df["price_usd"], errors="coerce")
    df["area_num"] = pd.to_numeric(df["area"], errors="coerce")
    df["bedrooms_num"] = pd.to_numeric(df["bedrooms"], errors="coerce")

    df = df[df["price_usd"].notna()]

    # ---- DERIVED METRICS (SAFE) ----
    df["price_per_m2_usd"] = None
    area_mask = df["area_num"] > 0
    df.loc[area_mask, "price_per_m2_usd"] = (
        df.loc[area_mask, "price_usd"] / df.loc[area_mask, "area_num"]
    )

    df["beds_per_area"] = None
    bed_area_mask = (df["area_num"] > 0) & (df["bedrooms_num"] > 0)
    df.loc[bed_area_mask, "beds_per_area"] = (
        df.loc[bed_area_mask, "bedrooms_num"] / df.loc[bed_area_mask, "area_num"]
    )

    # ---- AGGREGATION ----
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
            # PRICE
            price_min_usd=("price_usd", "min"),
            price_max_usd=("price_usd", "max"),
            price_avg_usd=("price_usd", "mean"),
            price_median_usd=("price_usd", "median"),
            price_std_usd=("price_usd", "std"),

            # PRICE / AREA
            price_per_m2_min=("price_per_m2_usd", "min"),
            price_per_m2_max=("price_per_m2_usd", "max"),
            price_per_m2_avg=("price_per_m2_usd", "mean"),
            price_per_m2_median=("price_per_m2_usd", "median"),
            price_per_m2_std=("price_per_m2_usd", "std"),

            # BEDS / AREA
            beds_per_area_min=("beds_per_area", "min"),
            beds_per_area_max=("beds_per_area", "max"),
            beds_per_area_avg=("beds_per_area", "mean"),
            beds_per_area_median=("beds_per_area", "median"),
            beds_per_area_std=("beds_per_area", "std"),

            qty=("price_usd", "size")
        )
        .reset_index()
    )

    # ---- MIN-N FILTER ----
    agg = agg[agg["qty"] >= args.min_n]

    # ---- SORT ----
    agg = agg.sort_values([
        "year_month",
        "neighborhood_label",
        "transaction",
        "property_type_new"
    ])

    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    agg.to_csv(args.output, index=False, encoding="utf-8-sig")

    print("[OK] Flexible aggregation completed")
    print("Year:", args.year)
    print("Rows:", len(agg))
    print("[OUT]", args.output)


if __name__ == "__main__":
    main()
