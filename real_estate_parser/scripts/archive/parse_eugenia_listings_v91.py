import os
import csv
import argparse
import json
from datetime import datetime

import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from modules.agency_preprocess import preprocess_listings
from modules.record_parser import parse_record
from modules.output_utils import format_listing_row, OUTPUT_FIELDS
from modules.parser_utils import detect_section_context




def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", required=True)
    parser.add_argument("--config", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--agency", required=True)
    parser.add_argument("--date", required=True)
    args = parser.parse_args()

    with open(args.config, "r", encoding="utf-8") as f:
        config = json.load(f)

    with open(args.file, "r", encoding="utf-8") as f:
        listings_raw = f.read().splitlines()

    listings = preprocess_listings(listings_raw, marker=config.get("listing_marker", "-"))
    current_tx = None
    current_type = None
    current_cat = None
    listing_no = 0
    rows = []

    for ln in listings:
      
      tx, ty, cat = detect_section_context(ln,config)
    
      if tx not in [None, "", "not found"] or ty not in [None, "", "not found"] or cat not in [None, "", "not found"]:
         current_tx   = tx if tx not in [None, "", "not found"] else current_tx
         current_type = ty if ty not in [None, "", "not found"] else current_type
         current_cat  = cat if cat not in [None, "", "not found"] else current_cat
         continue
      #continue

        # Regular listing
      listing_no += 1
       
      parsed = parse_record(ln,
            config,
            agency="Eugenia",
            date=args.date,
            listing_no=listing_no,
            # these kwargs must exist in parse_record; if not, remove them
            default_transaction=current_tx,
            default_type=current_type,
            default_category=current_cat,
        )

      if not isinstance(parsed, dict):
        print(f"[SKIP] #{listing_no} parsed as {type(parsed)} — skipping.")
        continue   

      print(f"[DEBUG] Parsed type: {type(parsed)} | Value: {parsed}")

    formatted = format_listing_row(parsed, ln, listing_no)
    rows.append(formatted)
      ######=========


    os.makedirs(args.output_dir, exist_ok=True)
    output_file = os.path.join(args.output_dir,f"{os.path.basename(args.file).replace('.txt', '')}.csv")

    output_fields = [
        "Listing ID", "Title", "Neighborhood", "Bedrooms", "Bathrooms",
        "AT", "Area", "Price", "Currency", "Transaction", "Type",
        "Agency", "Date", "Notes"
    ]

    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        #DEBUG
        for i, r in enumerate(rows[:3], 1):
            print(f"[DEBUG] Row {i} non-empty:", {k:v for k,v in r.items() if v not in ("", None)})
        missing_tx = [(r["Listing ID"], r["Notes"][:80]) for r in rows if not (r.get("Transaction") or "").strip()]
        print(f"[QC] Transaction empty in {len(missing_tx)} rows (context-inherit ON)")
        #debug
        writer = csv.DictWriter(f, fieldnames=output_fields)
        writer.writeheader()
        writer.writerows(rows)
        print(f"\n✅ Parsed {len(rows)} listings into {output_file}")


if __name__ == "__main__":
     main()



     
