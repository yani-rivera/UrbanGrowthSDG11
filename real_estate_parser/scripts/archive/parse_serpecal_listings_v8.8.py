import argparse
import os
import json
import csv
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from modules.record_parser import parse_record



def parse_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument('--file', required=True, help='Input file with listings')
    parser.add_argument('--config', required=True, help='Path to config JSON')
    parser.add_argument('--output-dir', required=True, help='Directory to save parsed CSV')
    parser.add_argument('--agency', required=False, default='UNKNOWN', help='Agency name')
    parser.add_argument('--date', required=False, default=None, help='Date of the listing file')
    return parser.parse_args()


def read_config(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def load_listings(path, marker="*"):
    listings = []
    current_listing = []

    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            print(f"[DEBUG] Line: {repr(line)}")  # ✅ DEBUG LINE

            stripped = line.strip()
            if not stripped:
                continue
            if stripped.startswith(marker):
                if current_listing:
                    listings.append(" ".join(current_listing))
                    current_listing = []
                current_listing.append(stripped.lstrip(marker).strip())
            else:
                current_listing.append(stripped)

    if current_listing:
        listings.append(" ".join(current_listing))

    # ✅ Final count debug
    print(f"\n✅ Total listings parsed: {len(listings)}")
    for i, l in enumerate(listings[:5]):
        print(f"{i+1}: {l[:120]}...\n")

    return listings


def main():
    args = parse_arguments()
    filename = os.path.basename(args.file)
    date_str = filename.split("_")[1].split(".")[0]  # "20151228"
    date = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}"  # "2015-12-28"

    config = read_config(args.config)
    marker = config.get("listing_marker", "*")

    listings = load_listings(args.file, marker)

    rows = []
    for idx, listing in enumerate(listings):
        row = parse_record(
              listing,
              config,
              agency=args.agency,
              date=args.date,
              listing_no=idx + 1
           )

        if not row:
           print(f"[SKIP] Listing {idx + 1} returned None:\n{listing[:300]}\n")
        else:
           rows.append(row)



    os.makedirs(args.output_dir, exist_ok=True)
    output_file = os.path.join(args.output_dir, f"{os.path.basename(args.file).replace('.txt', '')}.csv")

    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    print(f"✅ Parsed {len(rows)} listings into {output_file}")

if __name__ == "__main__":
    main()
