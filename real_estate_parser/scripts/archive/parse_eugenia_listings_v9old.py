# parse_eugenia_listings_fixed.py
# Updated version to fix Neighborhood and Price extraction issues

import re
import csv
import json
import argparse
import os
from datetime import datetime
from neighborhood_utils import load_neighborhoods, match_neighborhood
from parser_utils import normalize_price, extract_bedrooms, extract_bathrooms, extract_area


def parse_lines_to_rows(lines, agency_name, neighborhood_path):
    neighborhoods = load_neighborhoods(neighborhood_path)
    rows = []
    listing_id = 1
    date_str = datetime.now().strftime("%Y-%m-%d")

    for line in lines:
        line = line.strip()
        if not line:
            continue

        neighborhood = match_neighborhood(line, neighborhoods)
        price = normalize_price(line)
        bedrooms = extract_bedrooms(line)
        bathrooms = extract_bathrooms(line)
        area, unit = extract_area(line)

        row = {
            "Listing ID": listing_id,
            "Title": "",
            "Neighborhood": neighborhood,
            "Bedrooms": bedrooms,
            "Bathrooms": bathrooms,
            "Area": area,
            "Price": price,
            "Currency": "USD" if "$" in line else ("HNL" if "L" in line.upper() else ""),
            "Transaction": "ALQUILERES",
            "Type": "",
            "Agency": agency_name,
            "Date": date_str,
            "Notes": line,
            "Observaciones": ""
        }
        rows.append(row)
        listing_id += 1

    return rows


def write_to_csv(rows, output_file):
    fieldnames = list(rows[0].keys()) if rows else []
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--file', required=True, help="Input .txt file from OCR")
    parser.add_argument('--config', required=True, help="Agency config (not used directly)")
    parser.add_argument('--neighborhoods', required=True, help="Path to neighborhoods JSON")
    args = parser.parse_args()

    with open(args.file, encoding='utf-8') as f:
        lines = f.readlines()

    rows = parse_lines_to_rows(lines, "Eugenia", args.neighborhoods)
    output_file = "data/output/Eugenia/eugenia_20151228_fixed.csv"
    write_to_csv(rows, output_file)
    print(f"✅ Output saved to: {output_file}")
