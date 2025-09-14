#!/usr/bin/env python3
"""
std_price_csv_enricher — Standalone FX normalizer for listings CSVs

Purpose
-------
- Reads a listings CSV with at least (price, currency, date) fields.
- Looks up FX rates from a rates CSV.
- Converts prices into a chosen standard currency (default USD).
- Appends 7 new columns and writes an enriched CSV.

Added columns
-------------
- std_price
- std_currency
- fx_rate_used
- fx_base_date
- fx_pair
- fx_method
- fx_source

Usage
-----
python std_price_csv_enricher.py \
  --in listings.csv \
  --out enriched.csv \
  --rates fx_rates.csv \
  --std-currency USD
"""

import argparse
import csv
import os
import bisect
import sys
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List, Tuple, Optional

# ----------------------------
# Helpers
# ----------------------------

# Number of decimal places (minor units) per currency
# Keep minimal set, extend as needed
MINOR_UNITS = {
    "USD": 2,
    "EUR": 2,
    "HNL": 2,
    # Example extensions:
    # "JPY": 0,   # Japanese Yen, no decimals
    # "GBP": 2,   # British Pound
    # "MXN": 2,   # Mexican Peso
}

def normalize_currency(code: str) -> str:
    synonyms = {"US$": "USD", "$": "USD", "EURO": "EUR", "UK£": "GBP", "£": "GBP", "¥": "JPY"}
    c = (code or "").strip().upper()
    return synonyms.get(c, c)


def round_money(amount: Decimal, currency: str) -> Decimal:
    cur = currency.upper()
    if cur not in MINOR_UNITS:
        print(f"[WARN] Currency {cur} not in MINOR_UNITS, defaulting to 2 decimals.", file=sys.stderr)
    units = MINOR_UNITS.get(cur, 2)
    q = Decimal(10) ** -units
    return amount.quantize(q, rounding=ROUND_HALF_UP)

# ----------------------------
# FX Index
# ----------------------------

class FXIndex:
    def __init__(self):
        # key: (base, quote) -> sorted list of (date, rate, source)
        self.series: Dict[Tuple[str, str], List[Tuple[str, Decimal, str]]] = {}

    def add(self, date: str, base: str, quote: str, rate: str, source: str):
        key = (base.upper(), quote.upper())
        self.series.setdefault(key, []).append((date, Decimal(rate), source))

    def finalize(self):
        for k in self.series:
            self.series[k].sort(key=lambda t: t[0])

    def find_latest(self, base: str, quote: str, on: str) -> Optional[Tuple[str, Decimal, str]]:
        arr = self.series.get((base.upper(), quote.upper()))
        if not arr:
            return None
        idx = bisect.bisect_right([d for d, _, _ in arr], on) - 1
        if idx >= 0:
            return arr[idx]
        return None

# ----------------------------
# Conversion
# ----------------------------

def resolve_rate(fx: FXIndex, date: str, from_cur: str, to_cur: str, pivots=("USD",)):
    f, t = from_cur.upper(), to_cur.upper()
    if f == t:
        return Decimal("1"), date, "parity", ""

    # direct
    row = fx.find_latest(f, t, date)
    if row:
        d, r, s = row
        return r, d, "direct", s

    # inverse
    row = fx.find_latest(t, f, date)
    if row:
        d, r, s = row
        if r != 0:
            return (Decimal("1")/r), d, "inverse", s

    # pivot
    for p in pivots:
        if p in (f, t):
            continue
        row1 = fx.find_latest(f, p, date)
        row2 = fx.find_latest(p, t, date)
        if row1 and row2:
            d1, r1, s1 = row1
            d2, r2, s2 = row2
            return (r1*r2), max(d1,d2), "pivot", f"{s1}|{s2}"

    return None

# ----------------------------
# Main enrichment
# ----------------------------

def enrich_csv(input_csv, output_csv, fx_path, std_currency="USD", amount_col="price", currency_col="currency", date_col="date", pivots=("USD",), on_missing="error"):
    # load rates
    fx = FXIndex()
    with open(fx_path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                print("read row==>", row)
                fx.add(row["date"].strip(), row["base"].strip(), row["quote"].strip(), row["rate"].strip(), row.get("source",""))
            except Exception:
                continue
    fx.finalize()

    with open(input_csv, newline="", encoding="utf-8-sig") as fin, open(output_csv, "w", newline="", encoding="utf-8") as fout:
        reader = csv.DictReader(fin)
        fieldnames = reader.fieldnames or []
        new_fields = ["std_price","std_currency","fx_rate_used","fx_base_date","fx_pair","fx_method","fx_source"]
        writer = csv.DictWriter(fout, fieldnames=fieldnames+new_fields)
        writer.writeheader()

        for row in reader:
            price = row.get(amount_col)
            print("read price==>", price)
            cur = normalize_currency(row.get(currency_col))
            d = row.get(date_col)
            
            std_price, rate_used, base_date, pair, method, src = "","","","","",""
            if price and cur and d:
                res = resolve_rate(fx, d, cur, std_currency, pivots=pivots)
                if res:
                    r, bd, m, s = res
                    amount = Decimal(price) * r
                    std_amt = round_money(amount, std_currency)
                    std_price = str(std_amt)
                    rate_used = str(r)
                    base_date = bd
                    pair = f"{cur}/{std_currency}"
                    method = m
                    src = s
                else:
                    if on_missing == "error":
                        raise RuntimeError(f"No FX rate for {cur}->{std_currency} on {d}")

            row.update({
                "std_price": std_price,
                "std_currency": std_currency,
                "fx_rate_used": rate_used,
                "fx_base_date": base_date,
                "fx_pair": pair,
                "fx_method": method,
                "fx_source": src
            })
            writer.writerow(row)

# ----------------------------
# CLI
# ----------------------------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="input_csv", required=True)
    ap.add_argument("--out", dest="output_csv", required=True)
    ap.add_argument("--rates", dest="fx_path", required=True)
    ap.add_argument("--std-currency", default="USD")
    ap.add_argument("--amount-col", default="price")
    ap.add_argument("--currency-col", default="currency")
    ap.add_argument("--date-col", default="date")
    ap.add_argument("--pivot", nargs="*", default=["USD"])
    ap.add_argument("--on-missing-rate", choices=["error","skip","nulls"], default="error")
    args = ap.parse_args()

    os.makedirs(os.path.dirname(args.output_csv), exist_ok=True)
    enrich_csv(args.input_csv, args.output_csv, args.fx_path, std_currency=args.std_currency, amount_col=args.amount_col, currency_col=args.currency_col, date_col=args.date_col, pivots=tuple(args.pivot), on_missing=args.on_missing_rate)

if __name__ == "__main__":
    main()
