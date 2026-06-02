#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
StdPrice_v6.py

FX price standardization with configurable FX methodology.

Supports:
- Multiple dates per listings file
- Strict YYYY-MM-DD validation
- Daily FX OR monthly-average FX
- USD identity conversion
- HNL -> USD conversion

Expected FX file examples:

DAILY:
date,base,quote,rate
2015-01-28,HNL,USD,0.0472

MONTHLY_AVG:
year_month,base,quote,rate
2015-01,HNL,USD,0.0468
"""

import argparse
import pandas as pd
import re
from pathlib import Path

SUPPORTED_CURRENCIES = {"USD", "HNL"}

ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
YEAR_MONTH_RE = re.compile(r"^\d{4}-\d{2}$")


# =========================================================
# ARGUMENTS
# =========================================================

def parse_args():

    ap = argparse.ArgumentParser()

    ap.add_argument(
        "--input",
        required=True,
        help="Input listings CSV"
    )

    ap.add_argument(
        "--fx",
        required=True,
        help="FX CSV"
    )
    
    ap.add_argument(
        "--output",
        required=True,
        help="Output CSV"
    )

    ap.add_argument(
        "--fx-mode",
        choices=["daily", "monthly_avg"],
        default="monthly_avg",
        help="FX methodology"
    )

    ap.add_argument(
        "--on-missing-rate",
        choices=["error", "null"],
        default="error"
    )

    return ap.parse_args()


# =========================================================
# MAIN
# =========================================================

def main():

    args = parse_args()

    # --------------------------------------------------
    # LOAD LISTINGS
    # --------------------------------------------------

    df = pd.read_csv(
        args.input,
        dtype=str,
        encoding="utf-8-sig"
    )
    
    required_cols = {
        "price",
        "currency",
        "date"
    }

    if not required_cols.issubset(df.columns):

        raise RuntimeError(
            f"Input file must contain columns: {required_cols}"
        )

    # --------------------------------------------------
    # STRICT DATE VALIDATION
    # --------------------------------------------------

    bad_date = ~df["date"].astype(str).str.match(
        ISO_DATE_RE
    )

    if bad_date.any():

        raise RuntimeError(
            "Invalid date format in listings "
            "(expected YYYY-MM-DD). "
            f"Examples: "
            f"{df.loc[bad_date, 'date'].head(5).tolist()}"
        )

    df["date"] = pd.to_datetime(
        df["date"],
        format="%Y-%m-%d",
        errors="raise"
    )
    
    # --------------------------------------------------
    # NORMALIZE PRICE & CURRENCY
    # --------------------------------------------------

    df["currency"] = (
        df["currency"]
        .str.upper()
        .str.strip()
    )

    df["price"] = pd.to_numeric(
        df["price"],
        errors="coerce"
    )

    bad_cur = df.loc[
        ~df["currency"].isin(SUPPORTED_CURRENCIES),
        "currency"
    ].unique()

    if len(bad_cur) > 0:

        raise RuntimeError(
            f"Unsupported currencies found: {bad_cur}"
        )

    # --------------------------------------------------
    # LOAD FX
    # --------------------------------------------------

    fx = pd.read_csv(
        args.fx,
        dtype=str,
        encoding="utf-8-sig"
    )

    fx_required = {
        "base",
        "quote",
        "rate"
    }

    if args.fx_mode == "daily":
        fx_required.add("date")

    elif args.fx_mode == "monthly_avg":
        fx_required.add("year_month")

    if not fx_required.issubset(fx.columns):

        raise RuntimeError(
            f"FX file must contain columns: {fx_required}"
        )

    fx["base"] = (
        fx["base"]
        .str.upper()
        .str.strip()
    )

    fx["quote"] = (
        fx["quote"]
        .str.upper()
        .str.strip()
    )

    fx["rate"] = pd.to_numeric(
        fx["rate"],
        errors="coerce"
    )

    # Keep only HNL -> USD
    fx = fx[
        (fx["base"] == "HNL")
        & (fx["quote"] == "USD")
    ]

    # --------------------------------------------------
    # DAILY FX MODE
    # --------------------------------------------------

    if args.fx_mode == "daily":

        bad_fx_date = ~fx["date"].astype(str).str.match(
            ISO_DATE_RE
        )

        if bad_fx_date.any():

            raise RuntimeError(
                "Invalid FX date format "
                "(expected YYYY-MM-DD). "
                f"Examples: "
                f"{fx.loc[bad_fx_date, 'date'].head(5).tolist()}"
            )

        fx["date"] = pd.to_datetime(
            fx["date"],
            format="%Y-%m-%d",
            errors="raise"
        )

        df = df.merge(
            fx[["date", "rate"]],
            how="left",
            on="date",
            validate="many_to_one"
        )

    # --------------------------------------------------
    # MONTHLY AVG FX MODE
    # --------------------------------------------------

    elif args.fx_mode == "monthly_avg":

        bad_ym = ~fx["year_month"].astype(str).str.match(
            YEAR_MONTH_RE
        )

        if bad_ym.any():

            raise RuntimeError(
                "Invalid year_month format "
                "(expected YYYY-MM). "
                f"Examples: "
                f"{fx.loc[bad_ym, 'year_month'].head(5).tolist()}"
            )

        df["year_month"] = (
            df["date"]
            .dt.strftime("%Y-%m")
        )






        df = df.merge(
            fx[["year_month", "rate"]],
            how="left",
            on="year_month",
            validate="many_to_one"
        )

    # --------------------------------------------------
    # COMPUTE PRICE_USD
    # --------------------------------------------------

    df["price_usd"] = None
    df["fx_rate_used"] = None
    df["fx_method"] = None

    # USD identity
    usd = df["currency"] == "USD"

    df.loc[usd, "price_usd"] = (
        df.loc[usd, "price"]
    )

    df.loc[usd, "fx_rate_used"] = 1.0

    df.loc[usd, "fx_method"] = "identity"

    # HNL conversion
    hnl = df["currency"] == "HNL"

    missing_fx = (
        hnl
        & df["rate"].isna()
    )

    if (
        missing_fx.any()
        and args.on_missing_rate == "error"
    ):

        bad_dates = (
            df.loc[missing_fx, "date"]
            .dt.strftime("%Y-%m-%d")
            .unique()
        )

        raise RuntimeError(
            f"Missing FX rate for dates: {bad_dates}"
        )

    valid_hnl = (
        hnl
        & df["rate"].notna()
    )

    df.loc[valid_hnl, "price_usd"] = (
        df.loc[valid_hnl, "price"]
        * df.loc[valid_hnl, "rate"]
    )

    df.loc[hnl, "fx_rate_used"] = (
        df.loc[hnl, "rate"]
    )

    df.loc[hnl, "fx_method"] = (
        args.fx_mode
    )

    df["price_usd"] = pd.to_numeric(
        df["price_usd"],
        errors="coerce"
    )

    df["price_usd"] = (
        df["price_usd"]
        .round(2)
    )

    # --------------------------------------------------
    # WRITE OUTPUT
    # --------------------------------------------------

    Path(args.output).parent.mkdir(
        parents=True,
        exist_ok=True
    )

    df.to_csv(
        args.output,
        index=False,
        encoding="utf-8-sig"
    )

    # --------------------------------------------------
    # SUMMARY
    # --------------------------------------------------

    print("[OK] FX standardization completed")
    print("FX mode:", args.fx_mode)

    print("Currency counts:")
    print(df["currency"].value_counts())

    print("[OUT]", args.output)

    print("Rows written:", len(df))


if __name__ == "__main__":
    main()