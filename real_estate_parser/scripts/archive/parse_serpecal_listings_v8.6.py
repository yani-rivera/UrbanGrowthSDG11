# parse_serpecal_listings_v8.6.py
# Based on stable v8.4 with incremental, tested improvements

import os
import re
import argparse
import csv
import json
from datetime import datetime

VERSION = "v8.6"

def extract_date_from_filename(filename):
    match = re.search(r'(\\d{8})', filename)
    if match:
        try:
            return datetime.strptime(match.group(1), "%Y%m%d").strftime("%m/%d/%y")
        except ValueError:
            pass
    return "Unknown"

def normalize_currency_symbol(price_str, currency_aliases):
    for symbol, currency in currency_aliases.items():
        if symbol in price_str:
            return re.sub(re.escape(symbol), "" , price_str), currency
    return price_str, "Unknown"

def detect_transaction_type(text, transaction_keywords):
    for keyword, value in transaction_keywords.items():
        if keyword.lower() in text.lower():
            return value
    return "Unknown"

def detect_property_type(text, type_keywords):
    for property_type, keywords in type_keywords.items():
        for keyword in keywords:
            if keyword.lower() in text.lower():
                return property_type
    return "For Review"

def extract_area(text, area_aliases):
    ac_area = at_area = ""
    for alias in area_aliases.get("ac", []):
        match = re.search(r'(\\d+(?:[.,]\\d+)?)\\s*' + re.escape(alias), text, re.IGNORECASE)
        if match:
            ac_area = match.group(1)
            break
    for alias in area_aliases.get("at", []):
        match = re.search(r'(\\d+(?:[.,]\\d+)?)\\s*' + re.escape(alias), text, re.IGNORECASE)
        if match:
            at_area = match.group(1)
            break
    return ac_area, at_area

def extract_price(text):
    match = re.search(r'(\\d{1,3}(?:[.,]\\d{3})*(?:[.,]\\d+)?)', text)
    return match.group(1) if match else ""

def parse_listing(listing, config, agency, date):
    title = listing.split(" ", 1)[0] if listing else ""
    neighborhood = title.split(",")[0] if config.get("neighborhood_delimiter") in title else ""
    transaction = detect_transaction_type(listing, config.get("transaction_keywords", {}))
    property_type = detect_property_type(listing, config.get("type_keywords", {}))
    ac_area, at_area = extract_area(listing, config.get("area_aliases", {}))
    price_raw = extract_price(listing)
    price_cleaned, currency = normalize_currency_symbol(price_raw, config.get("currency_aliases", {}))

    return {
        "Title": title,
        "Neighborhood": neighborhood,
        "Bedrooms": "",
        "Bathrooms": "",
        "Area (AC)": ac_area,
        "Area (AT)": at_area,
        "Price": price_cleaned,
        "Currency": currency,
        "Transaction": transaction,
        "Type": property_type,
        "Agency": agency,
        "Date": date,
        "Notes": listing.strip()
    }

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", required=True)
    parser.add_argument("--config", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()

    with open(args.config, encoding="utf-8") as f:
        config = json.load(f)

    with open(args.file, encoding="utf-8") as f:
        lines = f.readlines()

    agency = config.get("agency_name", "SERPECAL")
    date = extract_date_from_filename(args.file)

    listings = []
    current_listing = ""
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        if stripped.startswith("#"):
            if current_listing:
                listings.append(current_listing)
                current_listing = ""
            listings.append(stripped)
            continue

        start_exceptions = config.get("exceptions", {}).get("start_exceptions", [])
        if any(stripped.startswith(exc) for exc in start_exceptions):
            if current_listing:
                listings.append(current_listing)
            current_listing = stripped
        else:
            current_listing += " " + stripped

    if current_listing:
        listings.append(current_listing)

    parsed = [parse_listing(listing, config, agency, date) for listing in listings]

    os.makedirs(args.output_dir, exist_ok=True)
    output_file = os.path.join(args.output_dir, f"{agency.lower()}_{date.replace('/', '-')}_{VERSION}.csv")
    with open(output_file, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=parsed[0].keys())
        writer.writeheader()
        writer.writerows(parsed)

    print(f"✅ Output written to: {output_file}")

if __name__ == "__main__":
    main()
