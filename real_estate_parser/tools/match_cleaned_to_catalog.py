import argparse
import pandas as pd


def main():
    ap = argparse.ArgumentParser(
        description="Match cleaned neighborhood names to catalog aliases (alias-based)"
    )

    # ---- listings ----
    ap.add_argument("--listings_csv", required=True)
    ap.add_argument("--listings_col", required=True)

    # ---- catalog ----
    ap.add_argument("--catalog_csv", required=True)

    # ---- outputs ----
    ap.add_argument("--out_merged", required=True)
    ap.add_argument("--out_matched", required=True)
    ap.add_argument("--out_unmatched", required=True)

    args = ap.parse_args()

    # ------------------------------------------------------------------
    # Load data (UTF-8 safe)
    # ------------------------------------------------------------------
    listings = pd.read_csv(args.listings_csv, encoding="utf-8-sig")
    catalog = pd.read_csv(args.catalog_csv, encoding="utf-8-sig")

    # ------------------------------------------------------------------
    # Normalize catalog aliases
    # ------------------------------------------------------------------
    catalog["__alias_norm__"] = (
        catalog["alias"]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    # ------------------------------------------------------------------
    # Build lookup tables (EXPLICIT + CANONICAL)
    # ------------------------------------------------------------------
    alias_to_uid = dict(zip(catalog["__alias_norm__"], catalog["uid"]))
    alias_to_gisid = dict(zip(catalog["__alias_norm__"], catalog["GISID"]))
    alias_to_label = dict(zip(catalog["__alias_norm__"], catalog["NEIGHBORHOOD"]))

    # ------------------------------------------------------------------
    # Sanitize listings neighborhood input
    # ------------------------------------------------------------------
    listings[args.listings_col] = (
        listings[args.listings_col]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    listings.loc[
        listings[args.listings_col].isin(["", "NAN", "NONE"]),
        args.listings_col
    ] = pd.NA

    listings["neighborhood_input_valid"] = listings[args.listings_col].notna()

    # ------------------------------------------------------------------
    # Safe alias-based matching (NO leakage)
    # ------------------------------------------------------------------
    def safe_lookup(val, lookup):
        if pd.isna(val):
            return pd.NA
        return lookup.get(val, pd.NA)

    listings["neighborhood_uid"] = listings[args.listings_col].apply(
        lambda v: safe_lookup(v, alias_to_uid)
    )

    listings["GISID"] = listings[args.listings_col].apply(
        lambda v: safe_lookup(v, alias_to_gisid)
    )

    listings["neighborhood_label"] = listings[args.listings_col].apply(
        lambda v: safe_lookup(v, alias_to_label)
    )

    # ------------------------------------------------------------------
    # Match flag
    # ------------------------------------------------------------------
    listings["matched"] = listings["neighborhood_uid"].notna()

    # ------------------------------------------------------------------
    # Outputs
    # ------------------------------------------------------------------
    listings.to_csv(args.out_merged, index=False, encoding="utf-8-sig")
    listings[listings["matched"]].to_csv(args.out_matched, index=False, encoding="utf-8-sig")
    listings[~listings["matched"]].to_csv(args.out_unmatched, index=False, encoding="utf-8-sig")


if __name__ == "__main__":
    main()
