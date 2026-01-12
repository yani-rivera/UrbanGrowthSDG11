#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
set_date_from_filename.py

Purpose:
Assign a dataset-level date to each CSV file based on the
date encoded at the end of the filename.

Example:
qs_20201025.csv  -->  date = 2020-10-25

Encoding:
- Reads and writes using utf-8-sig (Excel-safe)
"""

import argparse
import pandas as pd
from pathlib import Path
import re


DATE_RE = re.compile(r"(20\d{2})(\d{2})(\d{2})")


def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--input-dir",
        required=True,
        help="Directory containing CSV files"
    )
    ap.add_argument(
        "--output-dir",
        required=False,
        help="Optional output directory (defaults to in-place overwrite)"
    )
    return ap.parse_args()


def extract_date_from_filename(filename: str):
    """
    Extract YYYY-MM-DD from filename ending like *_YYYYMMDD.csv
    """
    m = DATE_RE.search(filename)
    if not m:
        return None
    return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"


def main():
    args = parse_args()

    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir) if args.output_dir else input_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    csv_files = sorted(input_dir.glob("*.csv"))

    if not csv_files:
        print("[WARN] No CSV files found")
        return

    for csv_path in csv_files:
        date_str = extract_date_from_filename(csv_path.name)

        if not date_str:
            print(f"[SKIP] No date found in filename: {csv_path.name}")
            continue

        # read with utf-8-sig
        df = pd.read_csv(csv_path, dtype=str, encoding="utf-8-sig")

        # overwrite / set date column
        df["date"] = date_str

        out_path = output_dir / csv_path.name

        # write with utf-8-sig
        df.to_csv(out_path, index=False, encoding="utf-8-sig")

        print(f"[OK] {csv_path.name} -> date = {date_str}")

    print("[DONE] Date assignment complete")


if __name__ == "__main__":
    main()
