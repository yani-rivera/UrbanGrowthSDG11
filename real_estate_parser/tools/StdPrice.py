#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
StdPrice_v5.py

Monthly FX price standardization (BCH).

- Allows MULTIPLE dates per listings file
- Strict YYYY-MM-DD validation per row
- Row-level FX join on exact date
- USD rows bypass FX
- HNL rows require FX
"""

import argparse
import pandas as pd
import re
from pathlib import Path

SUPPORTED_CURRENCIES = {"USD", "HNL"}
ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, help="Input listings CSV")
    ap.add_argument("--fx", required=True, help="Monthly FX CSV (BCH)")
    ap.add_argument("--output", required=True, help="Output CSV with price_usd")
    ap.add_argument("--on-missing-rate", choices=["error", "null"], default="error")
    return ap.parse_args()


def main():
    args = parse_args()

    # --------------------------------------------------
    # Load listings
    # --------------------------------------------------
    df = pd.read_csv(args.input, dtype=str, encoding="utf-8-sig")

    required_cols = {"price", "currency", "date"}
    if not required_cols.issubset(df.columns):
        raise RuntimeError(f"Input file must contain columns: {required_cols}")

    # --------------------------------------------------
    # STRICT date validation (row-level)
    # --------------------------------------------------
    bad_date = ~df["date"].astype(str).str.match(ISO_DATE_RE)
    if bad_date.any():
        raise RuntimeError(
            "Invalid date format in listings (expected YYYY-MM-DD). "
            f"Examples: {df.loc[bad_date, 'date'].head(5).tolist()}"
        )

    df["date"] = pd.to_datetime(df["date"], format="%Y-%m-%d", errors="raise")

    # --------------------------------------------------
    # Normalize price & currency
    # --------------------------------------------------
    df["currency"] = df["currency"].str.upper().str.strip()
    df["price"] = pd.to_numeric(df["price"], errors="coerce")

    bad_cur = df.loc[~df["currency"].isin(SUPPORTED_CURRENCIES), "currency"].unique()
    if len(bad_cur) > 0:
        raise RuntimeError(f"Unsupported currencies found: {bad_cur}")

    # --------------------------------------------------
    # Load FX (monthly BCH)
    # --------------------------------------------------
    fx = pd.read_csv(args.fx, dtype=str, encoding="utf-8-sig")

    fx_required = {"date", "base", "quote", "rate"}
    if not fx_required.issubset(fx.columns):
        raise RuntimeError(f"FX file must contain columns: {fx_required}")

    bad_fx_date = ~fx["date"].astype(str).str.match(ISO_DATE_RE)
    if bad_fx_date.any():
        raise RuntimeError(
            "Invalid date format in FX file. "
            f"Examples: {fx.loc[bad_fx_date, 'date'].head(5).tolist()}"
        )

    fx["date"] = pd.to_datetime(fx["date"], format="%Y-%m-%d", errors="raise")
    fx["base"] = fx["base"].str.upper().str.strip()
    fx["quote"] = fx["quote"].str.upper().str.strip()
    fx["rate"] = pd.to_numeric(fx["rate"], errors="coerce")

    # Keep only HNL -> USD
    fx = fx[(fx["base"] == "HNL") & (fx["quote"] == "USD")]

    # --------------------------------------------------
    # Merge FX (ROW-LEVEL, MULTI-DATE SAFE)
    # --------------------------------------------------
    df = df.merge(
        fx[["date", "rate"]],
        how="left",
        on="date",
        validate="many_to_one"
    )

    # --------------------------------------------------
    # Compute price_usd
    # --------------------------------------------------
    df["price_usd"] = None
    df["fx_rate_used"] = None
    df["fx_method"] = None

    # USD rows
    usd = df["currency"] == "USD"
    df.loc[usd, "price_usd"] = df.loc[usd, "price"]
    df.loc[usd, "fx_rate_used"] = 1.0
    df.loc[usd, "fx_method"] = "identity"

    # HNL rows
    hnl = df["currency"] == "HNL"
    missing_fx = hnl & df["rate"].isna()

    if missing_fx.any() and args.on_missing_rate == "error":
        bad_dates = df.loc[missing_fx, "date"].dt.strftime("%Y-%m-%d").unique()
        raise RuntimeError(f"Missing FX rate for dates: {bad_dates}")

    df.loc[hnl & df["rate"].notna(), "price_usd"] = (
        df.loc[hnl & df["rate"].notna(), "price"]
        * df.loc[hnl & df["rate"].notna(), "rate"]
    )

    df.loc[hnl, "fx_rate_used"] = df.loc[hnl, "rate"]
    df.loc[hnl, "fx_method"] = "monthly_bch"

    df["price_usd"] = pd.to_numeric(df["price_usd"], errors="coerce")
    df["price_usd"] = df["price_usd"].round(2)


    # --------------------------------------------------
    # Write output
    # --------------------------------------------------
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(args.output, index=False, encoding="utf-8-sig")

    # --------------------------------------------------
    # Summary
    # --------------------------------------------------
    print("[OK] Monthly FX standardization completed")
    print("Currency counts:")
    print(df["currency"].value_counts())
    print("[OUT]", args.output)
    print("Rows written:", len(df))


if __name__ == "__main__":
    main()
