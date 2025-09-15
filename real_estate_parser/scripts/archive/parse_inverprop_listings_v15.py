# parse_inverprop_listings_v15.py
import os
import re
import json
import argparse
import datetime
import pandas as pd
from pathlib import Path

def load_json(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def sanitize_price(price_str):
    price_str = re.sub(r'[^\d.,]', '', price_str)
    price_str = price_str.replace(',', '')
    try:
        return float(price_str)
    except:
        return None

def detect_transaction(header, transaction_map):
    for key, val in transaction_map.items():
        if key.lower() in header.lower():
            return val
    return "Unknown"

def extract_listings(lines, marker, transaction_map):
    listings = []
    current_transaction = ""
    current_category = ""
    buffer = []

    for line in lines:
        line = line.strip()
        if not line:
            continue

        if line.startswith('#'):
            current_category = line[1:].strip()
            current_transaction = detect_transaction(current_category, transaction_map)
            continue

        if line.startswith(marker):
            if buffer:
                listings.append((current_transaction, current_category, " ".join(buffer)))
                buffer = []
            buffer.append(line.lstrip(marker).strip())
        else:
            buffer.append(line.strip())

    if buffer:
        listings.append((current_transaction, current_category, " ".join(buffer)))

    return listings

def find_neighborhood(text, neighborhoods):
    for entry in neighborhoods:
        name = entry['Neighborhood'].upper()
        if name in text.upper():
            return name
    return None

def parse_listing(entry, currency_aliases, neighborhoods, agency):
    transaction, category, text = entry
    price_match = re.findall(r'([\$L]\.?\s?[\d,\.]+)', text)
    price = sanitize_price(price_match[0]) if price_match else None
    currency = None
    for symbol, code in currency_aliases.items():
        if any(symbol in p for p in price_match):
            currency = code
            break

    neighborhood = find_neighborhood(text, neighborhoods)

    return {
        "Listing ID": None,
        "Title": text.split(',')[0].strip(),
        "Neighborhood": neighborhood,
        "Bedrooms": None,
        "Bathrooms": None,
        "Area": None,
        "Price": price,
        "Currency": currency,
        "Transaction": transaction,
        "Type": category,
        "Agency": agency,
        "Date": None,
        "Notes": text
    }

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--file', required=True, help="Path to the raw .txt listings file")
    parser.add_argument('--config', required=True, help="Path to the agency config JSON file")
    parser.add_argument('--neighborhoods', required=True, help="Path to the known neighborhoods JSON file")
    args = parser.parse_args()

    config = load_json(args.config)
    agency = config['agency']
    listing_marker = config.get('listing_marker', '*')
    currency_aliases = config.get('currency_aliases', {})
    transaction_map = config.get('transaction_headers', {})
    neighborhoods = load_json(args.neighborhoods)

    with open(args.file, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    listings = extract_listings(lines, listing_marker, transaction_map)
    parsed = [parse_listing(l, currency_aliases, neighborhoods, agency) for l in listings]

    df = pd.DataFrame(parsed)
    df['Listing ID'] = [f"{agency[:3].upper()}-{i+1}" for i in range(len(df))]
    df['Date'] = Path(args.file).stem.split('_')[-1]

    year = df['Date'].iloc[0][:4]
    output_dir = f"data/output/{agency}/{year}"
    os.makedirs(output_dir, exist_ok=True)

    filename = Path(args.file).stem + "_parsed.csv"
    output_path = os.path.join(output_dir, filename)
    df.to_csv(output_path, index=False)
    print(f"Saved parsed listings to: {output_path}")

if __name__ == '__main__':
    main()
