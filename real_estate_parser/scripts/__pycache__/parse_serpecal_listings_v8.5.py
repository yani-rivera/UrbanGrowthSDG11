import os
import re
import csv
import json
from datetime import datetime

VERSION = "v8.3"

def load_json(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)

def normalize_currency(text, currency_aliases):
    for symbol, currency in currency_aliases.items():
        if symbol in text:
            return currency
    return ""

def extract_price(text, currency_aliases):
    price_pattern = re.compile(r"(\$|Lps\.?|L\.?|L)\s?([\d.,]+)")
    matches = price_pattern.findall(text)
    if matches:
        last_match = matches[-1]
        amount = last_match[1].replace(",", "")
        try:
            return float(amount)
        except ValueError:
            return None
    return None

def extract_transaction(text, transaction_keywords):
    text = text.lower()
    for key, value in transaction_keywords.items():
        if key in text:
            return value
    return ""

def extract_type(text, type_keywords):
    text = text.lower()
    for type_key, keywords in type_keywords.items():
        if any(kw in text for kw in keywords):
            return type_key
    return "for review"

def extract_area(text, area_aliases):
    ac = at = None
    ac_pattern = re.compile(r"(\d+[.,]?\d*)\s*(mts|m2|metros|m²)", re.IGNORECASE)
    at_pattern = re.compile(r"(\d+[.,]?\d*)\s*(vrs|vr2|vrs2|v²|vr²|varas)", re.IGNORECASE)
    ac_match = ac_pattern.search(text)
    at_match = at_pattern.search(text)
    if ac_match:
        ac = float(ac_match.group(1).replace(",", "."))
    if at_match:
        at = float(at_match.group(1).replace(",", "."))
    return ac, at

def extract_bed_bath(text):
    bed = bath = None
    bed_match = re.search(r"(\d+)\s*hab", text.lower())
    bath_match = re.search(r"(\d+)\s*ba[ñn]o", text.lower())
    if bed_match:
        bed = int(bed_match.group(1))
    if bath_match:
        bath = int(bath_match.group(1))
    return bed, bath

def parse_listings(text, config, agency, date):
    listings = text.split("\n*\n")  # Assuming * is the injected delimiter from preprocessing
    rows = []
    for idx, listing in enumerate(listings):
        listing = listing.strip()
        if not listing or any(header in listing for header in config["exceptions"].get("ignore_lines", [])):
            continue

        row = {
            "Listing ID": idx + 1,
            "Title": listing[:60],
            "Neighborhood": listing.split(config["neighborhood_delimiter"])[0].strip() if config.get("neighborhood_delimiter") in listing else "",
            "Bedrooms": None,
            "Bathrooms": None,
            "Area (AC)": None,
            "Area (AT)": None,
            "Price": None,
            "Currency": "",
            "Transaction": extract_transaction(listing, config.get("transaction_keywords", {})),
            "Type": extract_type(listing, config.get("type_keywords", {})),
            "Agency": agency,
            "Date": date,
            "Notes": listing
        }
        row["Currency"] = normalize_currency(listing, config.get("currency_aliases", {}))
        row["Price"] = extract_price(listing, config.get("currency_aliases", {}))
        row["Bedrooms"], row["Bathrooms"] = extract_bed_bath(listing)
        row["Area (AC)"], row["Area (AT)"] = extract_area(listing, config.get("area_aliases", {}))

        rows.append(row)
    return rows

def save_to_csv(rows, output_path):
    if not rows:
        return
    fieldnames = list(rows[0].keys())
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", required=True)
    parser.add_argument("--config", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()

    config = load_json(args.config)
    with open(args.file, 'r', encoding='utf-8') as f:
        raw_text = f.read()

    agency = os.path.basename(args.file).split("_")[0]
    date_match = re.search(r"(\d{8})", args.file)
    date = datetime.strptime(date_match.group(1), "%Y%m%d").strftime("%Y-%m-%d") if date_match else "unknown"

    listings = parse_listings(raw_text, config, agency, date)
    output_file = os.path.join(args.output_dir, f"{agency}_{date}_{VERSION}.csv")
    save_to_csv(listings, output_file)
    print(f"✅ Output saved to {output_file}")

if __name__ == "__main__":
    main()
