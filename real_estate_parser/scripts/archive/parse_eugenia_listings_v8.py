import os
import re
import json
import argparse
import datetime
import pandas as pd
from parser_utils import normalize_price, detect_transaction, detect_neighborhood, clean_listing_line


def parse_eugenia_listings(file_path, config, neighborhoods):
    with open(file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    date_match = re.search(r"(\\d{4})(\\d{2})(\\d{2})", os.path.basename(file_path))
    listing_date = ""
    if date_match:
        listing_date = f"{date_match.group(1)}-{date_match.group(2)}-{date_match.group(3)}"

    listings = []
    current_transaction = None

    for line in lines:
        line = line.strip()
        if not line:
            continue

        if line.startswith("#"):
            current_transaction = detect_transaction(line, config.get("transaction_headers", {}))
            continue

        if line.startswith(config["listing_marker"]):
            text = clean_listing_line(line)
            price = normalize_price(text)
            neighborhood = detect_neighborhood(text, neighborhoods)

            listings.append({
                "Listing ID": len(listings)+1,
                "Title": "",
                "Neighborhood": neighborhood or "",
                "Bedrooms": "",
                "Bathrooms": "",
                "Area": "",
                "Price": price,
                "Currency": "USD" if "$" in line else "HNL" if "L" in line else "",
                "Transaction": current_transaction or "",
                "Type": "",
                "Agency": "Eugenia",
                "Date": listing_date,
                "Notes": text,
                "Observaciones": ""
            })

    return listings


def save_to_excel(listings, agency, date):
    df = pd.DataFrame(listings)
    output_dir = f"data/output/{agency}"
    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, f"{agency}_listings_{date}.xlsx")
    df.to_excel(output_file, index=False)
    print(f"✅ Listings saved to {output_file}")


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", required=True)
    parser.add_argument("--config", required=True)
    parser.add_argument("--neighborhoods", required=True)
    args = parser.parse_args()

    config = load_json(args.config)
    neighborhoods = load_json(args.neighborhoods)
    neighborhoods = load_json(args.neighborhoods)
    if isinstance(neighborhoods, dict) and "neighborhoods" in neighborhoods:
        neighborhoods = neighborhoods["neighborhoods"]


    listings = parse_eugenia_listings(args.file, config, neighborhoods)
    listing_date = re.search(r"(\d{4})(\d{2})(\d{2})", os.path.basename(args.file)).group(0)
    save_to_excel(listings, "Eugenia", listing_date)
