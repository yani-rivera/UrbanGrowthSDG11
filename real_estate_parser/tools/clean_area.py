#!/usr/bin/env python3
# clean_AT_csv.py
import argparse, re, sys, os
import numpy as np
import pandas as pd

V2_TO_M2 = 0.698896  # 1 vara² ≈ 0.698896 m²

def clean_number(x):
    """Extract numeric value from messy strings like '1,200 vr2', '594 v2', '260 m¬¨¬©2'."""
    if pd.isna(x):
        return np.nan
    s = str(x).lower().strip()
    s = s.replace("m¬¨¬©2", "m2").replace("m²", "m2")
    m = re.search(r'[-+]?\d[\d.,\s]*', s)
    if not m:
        return np.nan
    num = m.group(0)
    num = num.replace(",", "").replace(" ", "")
    if num.count(".") > 1:  # handle multiple dots
        num = num.replace(".", "")
    try:
        return float(num)
    except ValueError:
        return np.nan

def clean_unit(u, default="vr2"):
    """Normalize units to 'm2' or 'vr2' (default vr2 if missing)."""
    if pd.isna(u):
        return default
    u = str(u).lower().strip()
    u = (u.replace("m¬¨¬©2", "m2")
           .replace("m²", "m2")
           .replace(".", ""))

    m2_aliases = {"m2","mt2","mts2","mts","metro2","metros2","metros cuadrados"}
    v2_aliases = {"vr2","v2","vrs2","vrs","vara2","varas2","varas cuadradas"}

    if u in m2_aliases: return "m2"
    if u in v2_aliases: return "vr2"
    return default

def main():
    ap = argparse.ArgumentParser(description="Clean 'AT' (lot size) + 'AT_unit' in a CSV and output standardized values.")
    ap.add_argument("--infile", required=True, help="Input CSV file")
    ap.add_argument("--outfile", required=True, help="Output CSV file")
    ap.add_argument("--AT_col", default="AT", help="Column name for AT values (default: AT)")
    ap.add_argument("--unit_col", default="AT_unit", help="Column name for AT unit (default: AT_unit)")
    args = ap.parse_args()

    # load CSV
    df = pd.read_csv(args.infile, dtype=str)

    if args.AT_col not in df.columns:
        sys.exit(f"Column '{args.AT_col}' not found. Available: {list(df.columns)}")
    if args.unit_col not in df.columns:
        sys.exit(f"Column '{args.unit_col}' not found. Available: {list(df.columns)}")

    # clean numbers
    df["AT_clean"] = df[args.AT_col].apply(clean_number)

    # clean units
    df["AT_unit_clean"] = df[args.unit_col].apply(lambda u: clean_unit(u, default="vr2"))

    # convert to m²
    df["AT_m2"] = np.where(
        df["AT_unit_clean"].eq("m2"), df["AT_clean"],
        np.where(df["AT_unit_clean"].eq("vr2"), df["AT_clean"] * V2_TO_M2, np.nan)
    )

    df.to_csv(args.outfile, index=False)
    print(f"Saved cleaned file to {args.outfile}")

if __name__ == "__main__":
    main()
