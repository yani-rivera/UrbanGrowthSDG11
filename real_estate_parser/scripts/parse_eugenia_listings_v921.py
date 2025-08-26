#!/usr/bin/env python3
import argparse
import csv
import os
import sys
import json
import re
from datetime import datetime

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from modules.record_parser import parse_record, preprocess_listings


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def infer_agency(config_path: str, default: str = "") -> str:
    if not config_path:
        return default
    base = os.path.basename(config_path)
    m = re.search(r"agency[_\- ]?([A-Za-z0-9]+)", base, re.IGNORECASE)
    if m:
        return m.group(1).capitalize()
    parent = os.path.basename(os.path.dirname(config_path))
    return parent.capitalize() if parent else (default or "Agency")


def infer_date(file_path: str, default: str = "") -> str:
    base = os.path.basename(file_path)
    m = re.search(r'(20\d{6}|\d{8})', base)
    if m:
        d = m.group(1)
        yyyy, mm, dd = d[0:4], d[4:6], d[6:8]
        try:
            return datetime(int(yyyy), int(mm), int(dd)).strftime("%Y-%m-%d")
        except Exception:
            pass
    return default or datetime.now().strftime("%Y-%m-%d")


def detect_section_context(line: str, config: dict):
    t = (line or "").strip().upper()
    for entry in (config or {}).get("section_headers", []):
        pat = (entry.get("pattern") or "").strip().upper()
        if pat and pat in t:
            return (
                entry.get("transaction") or None,
                entry.get("type") or None,
                entry.get("category") or pat
            )
    return (None, None, None)


def format_listing_row(parsed, raw_line, listing_no):
    return {
        "Listing ID": listing_no,
        "Title": (raw_line[:60] + "...") if len(raw_line) > 60 else raw_line,
        "Neighborhood": parsed.get("neighborhood", ""),
        "Bedrooms": parsed.get("bedrooms", ""),
        "Bathrooms": parsed.get("bathrooms", ""),
        "AT": parsed.get("area_terrain", ""),  # keep as separate column if you want
        "Area": parsed.get("area_construction") or parsed.get("area_terrain") or "",
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
    ap.add_argument("--agency", required=False, help="Agency name (optional, inferred from config)")
    ap.add_argument("--date", required=False, help="Listing date YYYY-MM-DD (optional, inferred from --file)")
    ap.add_argument("--neighborhoods", required=False, help="Known neighborhoods JSON (optional)")
    args = ap.parse_args()

    config = load_json(args.config)

    if args.neighborhoods and os.path.exists(args.neighborhoods):
        try:
            known_neigh = load_json(args.neighborhoods)
            # config["known_neighborhoods"] = known_neigh  # optional hook
        except Exception:
            pass

    agency = args.agency or infer_agency(args.config, default="Eugenia")
    date   = args.date   or infer_date(args.file)

    with open(args.file, "r", encoding="utf-8") as f:
        raw_lines = [ln.rstrip("\n") for ln in f]
    listings = preprocess_listings(raw_lines, marker=config.get("listing_marker", "-"))

    rows = []
    listing_no = 0
    current_tx, current_type, current_cat = None, None, None

    for ln in listings:
        tx, ty, cat = detect_section_context(ln, config)
        if tx or ty or cat:
            current_tx   = tx  or current_tx
            current_type = ty  or current_type
            current_cat  = cat or current_cat
            continue

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
            continue

        if not parsed.get("property_type") or str(parsed.get("property_type")).lower() == "other":
            parsed["property_type"] = current_type or "other"
        if not parsed.get("transaction"):
            parsed["transaction"] = current_tx or ""
        if not parsed.get("category"):
            parsed["category"] = current_cat or ""

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
