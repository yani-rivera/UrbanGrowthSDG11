#!/usr/bin/env python3
import argparse
import csv
import os
import sys
import json
import re
from datetime import datetime

# Keep imports minimal and centralized
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from modules.record_parser import parse_record, preprocess_listings


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def infer_agency(config_path: str, default: str = "") -> str:
    """
    Infer agency from config filename or parent folder.
    e.g., config/agency_eugenia.json -> "Eugenia"
    """
    if not config_path:
        return default
    base = os.path.basename(config_path)
    m = re.search(r"agency[_\- ]?([A-Za-z0-9]+)", base, re.IGNORECASE)
    if m:
        return m.group(1).capitalize()
    parent = os.path.basename(os.path.dirname(config_path))
    return parent.capitalize() if parent else (default or "Agency")


def infer_date(file_path: str, default: str = "") -> str:
    """
    Infer date (YYYY-MM-DD) from raw file name like eugenia_20151128.txt
    Falls back to today's date if not found.
    """
    base = os.path.basename(file_path)
    m = re.search(r'(20\d{6}|\d{8})', base)
    if m:
        d = m.group(1)
        # Normalize to YYYY-MM-DD
        yyyy = d[0:4]
        mm   = d[4:6]
        dd   = d[6:8]
        try:
            return datetime(int(yyyy), int(mm), int(dd)).strftime("%Y-%m-%d")
        except Exception:
            pass
    return default or datetime.now().strftime("%Y-%m-%d")


def detect_section_context(line: str, config: dict):
    """
    Returns (transaction, type, category) if the line looks like a section header,
    else (None, None, None).
    Matching is simple (pat in line uppercased) to avoid extra modules.
    """
    t = (line or "").strip().upper()
    for entry in (config or {}).get("section_headers", []):
        pat = (entry.get("pattern") or "").strip().upper()
        if pat and pat in t:
            # Debug can be toggled by commenting next two lines
            print(f"[MATCH FOUND] Pattern: {pat} in line: {t}")
            print(f"Returning: transaction={entry.get('transaction')}, type={entry.get('type')}, category={entry.get('category')}")
            return (
                entry.get("transaction") or None,
                entry.get("type") or None,
                entry.get("category") or pat
            )
    return (None, None, None)


def format_listing_row(parsed, raw_line, listing_no):
    return {
        "Listing ID": listing_no,
        "Title": parsed.get("title", ""),
        "Neighborhood": parsed.get("neighborhood", ""),
        "Bedrooms": parsed.get("bedrooms", ""),
        "Bathrooms": parsed.get("bathrooms", ""),
        "Area": parsed.get("area", ""),
        "Price": parsed.get("price", ""),
        "Currency": parsed.get("currency", ""),
        "Transaction": parsed.get("transaction", ""),
        "Type": parsed.get("property_type", ""),
        "Agency": parsed.get("agency", ""),
        "Date": parsed.get("date", ""),
        "Notes": raw_line.strip(),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", required=True, help="Raw text file")
    ap.add_argument("--config", required=True, help="Agency config JSON")
    ap.add_argument("--output-dir", required=True, help="Output directory for CSV")
    # These are now OPTIONAL and inferred if omitted
    ap.add_argument("--agency", required=False, help="Agency name (optional, inferred from config)")
    ap.add_argument("--date", required=False, help="Listing date YYYY-MM-DD (optional, inferred from --file)")
    # Optional neighborhoods file; accepted but not required in this lean script
    ap.add_argument("--neighborhoods", required=False, help="Known neighborhoods JSON (optional)")
    args = ap.parse_args()

    config = load_json(args.config)

    # Optional neighborhoods hook (doesn't require extra modules)
    if args.neighborhoods and os.path.exists(args.neighborhoods):
        try:
            known_neigh = load_json(args.neighborhoods)
            # If your parse_record expects this, uncomment the next line:
            # config["known_neighborhoods"] = known_neigh
            print(f"[INFO] Loaded neighborhoods: {args.neighborhoods}")
        except Exception as e:
            print(f"[WARN] Could not load neighborhoods file: {e}")

    # Infer agency / date if not provided
    agency = args.agency or infer_agency(args.config, default="Eugenia")
    date   = args.date   or infer_date(args.file)

    # Read and fold multiline listings into single lines by marker
    with open(args.file, "r", encoding="utf-8") as f:
        raw_lines = [ln.rstrip("\n") for ln in f]
    listings = preprocess_listings(raw_lines, marker=config.get("listing_marker", "-"))
    print(f"[INFO] Listings after preprocess: {len(listings)}")

    rows = []
    listing_no = 0
    current_tx, current_type, current_cat = None, None, None

    for ln in listings:
        # Detect and update header context
        tx, ty, cat = detect_section_context(ln, config)
        if tx or ty or cat:
            prev = (current_tx, current_type, current_cat)
            current_tx   = tx  or current_tx
            current_type = ty  or current_type
            current_cat  = cat or current_cat
            print(f"[HEADER] {ln}")
            print(f"         context {prev} -> {(current_tx, current_type, current_cat)}")
            continue

        # Regular listing
        listing_no += 1
        parsed = parse_record(
            ln,
            config,
            agency=agency,
            date=date,
            listing_no=listing_no,
            default_transaction=current_tx,
            default_type=current_type,
            default_category=current_cat,
        )

        if not isinstance(parsed, dict):
            print(f"[SKIP] listing #{listing_no} → got {type(parsed)}")
            continue

        # Enforce header inheritance if extractor returns empty/other
        ptype = parsed.get("property_type")
        if not ptype or str(ptype).lower() == "other":
            parsed["property_type"] = current_type or "other"
        if not parsed.get("transaction"):
            parsed["transaction"] = current_tx or ""
        if not parsed.get("category"):
            parsed["category"] = current_cat or ""

        print(f"[OK]  #{listing_no} type={parsed['property_type']} tx={parsed['transaction']} cat={parsed.get('category','')}")
        rows.append(format_listing_row(parsed, ln, listing_no))

    os.makedirs(args.output_dir, exist_ok=True)
    outpath = os.path.join(args.output_dir, f"{agency}_{date.replace('-', '')}.csv")

    if rows:
        with open(outpath, "w", newline="", encoding="utf-8") as outcsv:
            writer = csv.DictWriter(outcsv, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)
        print(f"✅ Exported {len(rows)} listings to {outpath}")
    else:
        print(f"⚠️ No listings parsed. Check header detection and marker in {args.file}.")


if __name__ == "__main__":
    main()
