import argparse
import pandas as pd
import sys
import os
from typing import Iterable, List, Optional, Tuple


def normalize_value(val) -> str:
    if pd.isna(val):
        return ""
    return " ".join(str(val).strip().lower().split())


def parse_path_and_col(spec: str) -> Tuple[str, Optional[str]]:
    if ":" in spec:
        path, col = spec.split(":", 1)
        return path, col
    return spec, None


def load_exclusions_from_file(spec: str) -> List[str]:
    path, col = parse_path_and_col(spec)
    if not os.path.exists(path):
        sys.exit(f"Exclusion file not found: {path}")

    _, ext = os.path.splitext(path.lower())
    if ext == ".csv":
        try:
            df = pd.read_csv(path, encoding="utf-8-sig")
        except Exception as e:
            sys.exit(f"Error reading CSV exclusions '{path}': {e}")
        if col is None:
            if df.shape[1] != 1:
                sys.exit(
                    f"CSV exclusions '{path}' has multiple columns; specify one like 'file.csv:Column'"
                )
            col = df.columns[0]
        if col not in df.columns:
            sys.exit(
                f"Column '{col}' not found in exclusions file '{path}'. Available: {list(df.columns)}"
            )
        values = [normalize_value(v) for v in df[col].astype(str).tolist() if normalize_value(v)]
        return values
    else:
        try:
            with open(path, "r", encoding="utf-8-sig") as f:
                lines = [line.strip() for line in f]
        except Exception as e:
            sys.exit(f"Error reading text exclusions '{path}': {e}")
        values = [normalize_value(x) for x in lines if x and not x.lstrip().startswith(("#", "//"))]
        return values


def filter_by_list(df: pd.DataFrame, cols: Iterable[str], banned: Iterable[str], mode: str) -> pd.Series:
    banned = [normalize_value(x) for x in banned]
    mask = pd.Series(False, index=df.index)
    for col in cols:
        if col not in df.columns:
            sys.exit(f"Filter column '{col}' not found in data. Available: {list(df.columns)}")
        colnorm = df[col].map(normalize_value)
        for ban in banned:
            if mode == "exact":
                mask |= (colnorm == ban)
            elif mode == "substring":
                mask |= colnorm.str.contains(ban, na=False, regex=False)
            else:
                sys.exit(f"Unknown neigh-match mode: {mode}")
    return mask
# --- Patch: write accepted and rejected files ---
 

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--input", required=True, help="Input CSV")
    parser.add_argument("-o", "--output", required=True, help="Output CSV")

    parser.add_argument("--price-col", help="Column name containing price. Rows with null/non-numeric price are dropped.")

    parser.add_argument("--exclude-neighborhoods-files", required=True, help="Path to neighborhoods exclusion file (.txt or CSV[:Column])")
    parser.add_argument("--neigh-col", default="neighborhood", help="Column to compare neighborhoods against (default: neighborhood)")
    parser.add_argument("--neigh-match", choices=["exact", "substring"], default="exact", help="Neighborhood match mode")

    parser.add_argument("--exclude-types-files", help="Path to types exclusion file (.txt or CSV[:Column])")
    parser.add_argument("--type-col", default="property_type", help="Column containing property type (default: property_type)")
    parser.add_argument("--rejected", help="Path to write rejected/excluded rows (CSV)")


    args = parser.parse_args()

    try:
        df = pd.read_csv(args.input, encoding="utf-8-sig")
    except Exception as e:
        sys.exit(f"Error reading input: {e}")

    initial_rows = len(df)
    original=df.copy()
   
    if args.price_col:
        if args.price_col not in df.columns:
            sys.exit(f"--price-col '{args.price_col}' not found. Available: {list(df.columns)}")
        #df["price"] = df["price"].str.replace(",", "").astype(float)
        df["price"] = (
        df["price"]
        .astype(str)                     # convert everything to string
        .str.replace(",", "", regex=False)
        .str.replace(" ", "", regex=False)
        .replace("nan", None)            # clean 'nan' text back to None
        .astype(float)
        )


        prices_num = pd.to_numeric(df[args.price_col], errors="coerce")
        non_null_mask = prices_num.notna()
        dropped_price = (~non_null_mask).sum()
        df = df.loc[non_null_mask].copy()
    else:
        dropped_price = 0

    if args.exclude_types_files:
        excluded_types = load_exclusions_from_file(args.exclude_types_files)
        type_mask = filter_by_list(df, [args.type_col], excluded_types, mode="exact")
        dropped_types = type_mask.sum()
        df = df.loc[~type_mask].copy()
    else:
        dropped_types = 0

    excluded_neigh = load_exclusions_from_file(args.exclude_neighborhoods_files)
    neigh_mask = filter_by_list(df, [args.neigh_col], excluded_neigh, mode="exact")
    dropped_neigh = neigh_mask.sum()
    df = df.loc[~neigh_mask].copy()
   
    ####

    #final_rows = len(df)

    #Differential = original.merge(df,on="Listing_uid",indicator = True, how='left').loc[lambda x : x['_merge']!='both']
    #Differential.to_csv(args.rejected, index=False, encoding="utf-8-sig")
#####
 
    final_rows = len(df)

    # Build rejected rows (present in original but not in final df)
    Differential = (
        original.merge(df, on="Listing_uid", indicator=True, how="left")
        .loc[lambda x: x["_merge"] != "both"]
        .copy()
    )

    # Add rejection cause column
    Differential["rejection_cause"] = ""
  
    # Price rejection: price was null or non-numeric in the ORIGINAL data
    if args.price_col:
        orig_price_num = pd.to_numeric(
            original[args.price_col]
            .astype(str)
            .str.replace(",", "", regex=False)
            .str.replace(" ", "", regex=False),
            errors="coerce",
        )
        price_reject_mask = orig_price_num.isna()
        Differential.loc[price_reject_mask, "rejection_cause"] += "price_null_or_non_numeric;"

    # Property type rejection
    if args.exclude_types_files:
        excluded_types = load_exclusions_from_file(args.exclude_types_files)
        type_reject_mask = filter_by_list(original, [args.type_col], excluded_types, mode="exact")
        Differential.loc[type_reject_mask, "rejection_cause"] += "excluded_property_type;"

    # Neighborhood rejection
    neigh_reject_mask = filter_by_list(original, [args.neigh_col], excluded_neigh, mode="exact")
    Differential.loc[neigh_reject_mask, "rejection_cause"] += "excluded_neighborhood;"
    print(f"Differential columns: {Differential.columns.tolist()}")
    #CLEAN REJECTED
    # Keep only left-side columns + decision metadata
    keep_cols = [
    c for c in Differential.columns
    if c.endswith("_x") or c in ["Listing_uid", "_merge", "rejection_cause"]
    ]

    Differential_clean = Differential[keep_cols].copy()
    Differential_clean.columns = [
    c[:-2] if c.endswith("_x") else c
    for c in Differential_clean.columns
    ]

    # Drop all right-side (_y) columns that are entirely empty
    y_cols = [c for c in Differential.columns if c.endswith("_y")]
    Differential = Differential.drop(columns=y_cols)

    Differential.columns = [
    c[:-2] if c.endswith("_x") else c
    for c in Differential.columns
]


    # Write rejected file

    Differential.to_csv(args.rejected, index=False, encoding="utf-8-sig")



    try:
        df.to_csv(args.output, index=False, encoding="utf-8-sig")
    except Exception as e:
        sys.exit(f"Error writing output: {e}")

    print("\nSummary:")
    print(f"  Initial rows: {initial_rows}")
    if args.price_col:
        print(f"  Dropped due to null/non-numeric {args.price_col}: {dropped_price}")
    if args.exclude_types_files:
        print(f"  Dropped due to property_type exclusions: {dropped_types}")
    print(f"  Dropped due to neighborhood exclusions: {dropped_neigh}")
    print(f"  Final rows: {final_rows}")


if __name__ == "__main__":
    main()



