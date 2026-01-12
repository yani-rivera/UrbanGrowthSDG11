#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
preparse_to_sdg11.py

Purpose:
Convert pre-parse / semi-manual real estate listings
into the standardized SDG-11 pipeline format.

Key rule:
- `notes` is preserved verbatim for traceability
  (e.g. Facebook screenshots, manual verification).

Input:
--input   pre-parse Excel file
--output  standardized CSV

Example:
python preparse_to_sdg11.py \
  --input preparse_facebook_2020.xlsx \
  --output sdg11_2020_preparse.csv
"""

import argparse
import pandas as pd
import re
from pathlib import Path


# ----------------------------
# Helpers
# ----------------------------

def clean_number(val):
    """Remove commas and whitespace; return numeric or NA."""
    if pd.isna(val):
        return pd.NA
    s = str(val).strip()
    s = re.sub(r"[,\s]", "", s)
    return s if s != "" else pd.NA


def normalize_currency(val):
    if pd.isna(val):
        return pd.NA
    v = str(val).strip().upper()
    if v in ("L", "LPS", "HNL"):
        return "HNL"
    if v in ("USD", "$", "US$"):
        return "USD"
    return v


def parse_date(val):
    if pd.isna(val):
        return pd.NA
    try:
        return pd.to_datetime(val, errors="coerce").date()
    except Exception:
        return pd.NA


# ----------------------------
# Main
# ----------------------------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, help="Pre-parse Excel file")
    ap.add_argument("--output", required=True, help="Output SDG-11 CSV")
    ap.add_argument("--source_type", default="pre_parse_manual")
    ap.add_argument("--pipeline_version", default="v1.0")
    ap.add_argument("--ingestion_id", default=None)
    ap.add_argument("--source_agency", default=None)
    args = ap.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)

    df = pd.read_csv(input_path,encoding="utf-8-sig")

    # ----------------------------
    # Rename columns (authoritative mapping)
    # ----------------------------
    df = df.rename(columns={
        "No": "Listing ID",
        "Title": "title",
        "Neighborhood": "neighborhood",
        "Bedrooms": "bedrooms",
        "Bathrooms": "bathrooms",
        "Land area": "area",
        "built Area m2": "area_m2",
        "Price": "price",
        "Currency": "currency",
        "Transaction": "transaction",
        "Type": "property_type",
        "Agency": "agency",
        "Date": "date",
        "Notes": "notes",
    })

    # ----------------------------
    # Clean numeric fields
    # ----------------------------
    df["price"] = df["price"].apply(clean_number)
    df["area"] = df.get("area", pd.Series()).apply(clean_number)
    df["area_m2"] = df.get("area_m2", pd.Series()).apply(clean_number)

    # Area unit inference
    df["area_unit"] = df["area"].apply(lambda x: "m2" if pd.notna(x) else pd.NA)
    df["AT"] = pd.NA
    df["AT_unit"] = pd.NA

    # ----------------------------
    # Normalize fields
    # ----------------------------
    df["currency"] = df["currency"].apply(normalize_currency)
    df["date"] = df["date"].apply(parse_date)

    # ----------------------------
    # Preserve notes verbatim
    # ----------------------------
    df["notes"] = df["notes"].astype(str)

    # ----------------------------
    # Add pipeline metadata
    # ----------------------------
    df["source_type"] = args.source_type
    df["pipeline_version"] = args.pipeline_version
    df["source_file"] = input_path.name
    df["ingestion_id"] = (
        args.ingestion_id
        if args.ingestion_id
        else input_path.stem
    )
    df["source_agency"] = (
        args.source_agency
        if args.source_agency
        else df["agency"]
    )

    # ----------------------------
    # Final column order (SDG-11)
    # ----------------------------
    final_cols = [
        "Listing ID",
        "title",
        "neighborhood",
        "bedrooms",
        "bathrooms",
        "area",
        "area_unit",
        "area_m2",
        "AT",
        "AT_unit",
        "price",
        "currency",
        "transaction",
        "property_type",
        "agency",
        "date",
        "notes",
        "source_type",
        "ingestion_id",
        "pipeline_version",
        "source_file",
        "source_agency",
    ]

    df = df[[c for c in final_cols if c in df.columns]]

    # ----------------------------
    # Write output
    # ----------------------------
    df.to_csv(output_path, index=False, encoding="utf-8-sig")
    print(f"[OK] Standardized file written: {output_path}")


if __name__ == "__main__":
    main()
