# parse_eugenia_listings_fixed.py
# Updated version to fix Neighborhood and Price extraction issues

import re
import csv
import json
import argparse
import os
from datetime import datetime

import sys


sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))



from neighborhood_utils import load_neighborhoods, match_neighborhood
from modules.parser_utils import normalize_price, extract_bedrooms, extract_bathrooms, extract_area



# === User Guide Notes ===
# Script name: parse_eugenia_listings_v9.py (formerly fixed.py)
#
# Directory structure:
# - raw OCR text input: data/raw/Eugenia/eugenia_20151228.txt
# - output CSV:         data/output/Eugenia/eugenia_20151228_fixed.csv
# - config JSONs:
#     - config/agency_eugenia.json            (general agency config)
#     - config/config_known_neighborhoods.json (neighborhoods with optional aliases)
# - modular support libraries:
#     - parser_utils.py
#     - neighborhood_utils.py
#
# How to run:
# python scripts/parse_eugenia_listings_v9.py \
#   --file data/raw/Eugenia/eugenia_20151228.txt \
#   --config config/agency_eugenia.json \
#   --neighborhoods config/config_known_neighborhoods.json
#
# What it does:
# - Combines input lines into a single text block
# - Splits listings based on '-' prefix
# - Uses modular regex helpers to extract price, beds, baths, area
# - Matches neighborhood via config and fallback patterns (e.g. Col., Loma, San)
# - Outputs cleaned and structured CSV with full Notes for verification

import json

def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

from neighborhood_utils import match_neighborhood

def parse_lines_to_rows(lines, agency_name, neighborhoods_path, config):
    import json
    import re

    # Load neighborhoods
    with open(neighborhoods_path, "r", encoding="utf-8") as f:
        neighborhoods = json.load(f)

    strategy = config.get("neighborhood_strategy", "")
    rows = []
    listing_id = 1

    for line in lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue

        # 🏘 Neighborhood: before first comma
        parts = re.split(r'[,:]', line, maxsplit=1)
        fallback_nhood = parts[0].replace("-", "").strip()
        neighborhood = match_neighborhood(line, neighborhoods, strategy=strategy) or fallback_nhood.upper()

        # 🛏 Bedrooms
        bedroom_match = re.search(r"(\d+)\s*hab", line, re.IGNORECASE)
        bedrooms = bedroom_match.group(1) if bedroom_match else ""

        # 🛁 Bathrooms (optional, not in sample)
        bathroom_match = re.search(r"(\d+)\s*(ba[ñn]o|bafios?)", line, re.IGNORECASE)
        bathrooms = bathroom_match.group(1) if bathroom_match else ""

        # 💲 Price
        price_match = re.search(r"[$L]\.?\s?(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)", line)
        currency = ""
        price = ""
        if price_match:
            price = price_match.group(1).replace(",", "")
            currency_symbol = re.search(r"([$L])", line)
            if currency_symbol:
                currency = config.get("currency_aliases", {}).get(currency_symbol.group(1), currency_symbol.group(1))

        row = {
            "Listing ID": listing_id,
            "Title": "",
            "Neighborhood": neighborhood,
            "Bedrooms": bedrooms,
            "Bathrooms": bathrooms,
            "Area": "",
            "Price": price,
            "Currency": currency,
            "Transaction": "",
            "Type": "",
            "Agency": agency_name,
            "Date": "",
            "Notes": line,
            "Data Completeness": "✅" if price and neighborhood else "⚠️ Incomplete",
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
    config = load_json(args.config)
    rows = parse_lines_to_rows(lines, "Eugenia", args.neighborhoods,config)
    output_file = "data/output/Eugenia/eugenia_20151228_fixed.csv"
    write_to_csv(rows, output_file)
    print(f"✅ Output saved to: {output_file}")
