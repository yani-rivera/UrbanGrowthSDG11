import os
import csv
import argparse
import sys


sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from modules.record_parser import parse_record
from modules.output_utils import format_listing_row


import json 



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
        listings = f.read().splitlines()

    rows = []

    for idx, listing in enumerate(listings):
        parsed = parse_record(
            listing,
            config,
            agency=args.agency,
            date=args.date,
            listing_no=idx + 1
        )

        if not isinstance(parsed, dict):
            print(f"[SKIP] #{idx+1} parsed as {type(parsed)} — skipping.")
            continue


        print(f"[DEBUG] Parsed type: {type(parsed)} | Value: {parsed}")

        formatted= format_listing_row(parsed, listing, idx + 1)
        rows.append(formatted)

    os.makedirs(args.output_dir, exist_ok=True)
    output_file = os.path.join(
        args.output_dir,
        f"{os.path.basename(args.file).replace('.txt', '')}.csv"
    )

    output_fields = [
        "Listing ID", "Title", "Neighborhood", "Bedrooms", "Bathrooms",
        "AT", "Area", "Price", "Currency", "Transaction", "Type",
        "Agency", "Date", "Notes"
    ]

    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        #DEBUG
        for i, r in enumerate(rows[:3], 1):
            print(f"[DEBUG] Row {i} non-empty:", {k:v for k,v in r.items() if v not in ("", None)})
    
        #debug
        writer = csv.DictWriter(f, fieldnames=output_fields)
        writer.writeheader()
        writer.writerows(rows)



    print(f"\n✅ Parsed {len(rows)} listings into {output_file}")


if __name__ == "__main__":
    main()
