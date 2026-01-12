#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
StdTerrainAreaToM2_v2.py

Standardize terrain (land) area to square meters.

Rules:
- Preserve original columns
- Create new column: area_m2_std
- Use Honduran vara² conversion
- Add area_std_method for auditability
"""

import argparse
import pandas as pd
from pathlib import Path

# Honduras official approximation
V2_TO_M2 = 0.6987

VARA_ALIASES = {
    "v2", "vrs2", "vrs²", "vara2", "varas2", "v²"
}


def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, help="Input CSV")
    ap.add_argument("--output", required=True, help="Output CSV with area_m2_std")
    return ap.parse_args()


def normalize_unit(u):
    if pd.isna(u):
        return None
    return str(u).lower().strip()


def main():
    args = parse_args()

    df = pd.read_csv(args.input, dtype=str, encoding="utf-8-sig")

    # Ensure numeric
    for col in ["area_m2", "AT"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    df["area_m2_std"] = None
    df["area_std_method"] = None

    # 1) Built area already in m2
    if "area_m2" in df.columns:
        built_mask = df["area_m2"].notna()
        df.loc[built_mask, "area_m2_std"] = df.loc[built_mask, "area_m2"]
        df.loc[built_mask, "area_std_method"] = "built_area_m2"

    # 2) Terrain area (AT)
    if {"AT", "AT_unit"}.issubset(df.columns):
        at_mask = df["area_m2_std"].isna() & df["AT"].notna()
        units = df.loc[at_mask, "AT_unit"].apply(normalize_unit)

        # Vara² → m²
        v2_mask = at_mask & units.isin(VARA_ALIASES)
        df.loc[v2_mask, "area_m2_std"] = df.loc[v2_mask, "AT"] * V2_TO_M2
        df.loc[v2_mask, "area_std_method"] = "terrain_v2"

        # Already m2
        m2_mask = at_mask & units.eq("m2")
        df.loc[m2_mask, "area_m2_std"] = df.loc[m2_mask, "AT"]
        df.loc[m2_mask, "area_std_method"] = "terrain_m2"

    df["area_m2_std"] = pd.to_numeric(df["area_m2_std"], errors="coerce")

    # Write output
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(args.output, index=False, encoding="utf-8-sig")

    # Summary
    print("[OK] Terrain area standardization completed")
    print(df["area_std_method"].value_counts(dropna=False))
    print("[OUT]", args.output)
    print("Rows written:", len(df))


if __name__ == "__main__":
    main()
