import re
import os
import json
import argparse
from neighborhood_utils import match_neighborhood

def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def parse_serpecal_lines(lines, config, neighborhoods, transaction_type):
    rows = []
    listing = ""
    listing_id = 1

    for line in lines:
        line = line.strip()
        if not line:
            continue

        if line.startswith("COL.") and listing:
            row = parse_listing(listing, config, neighborhoods, listing_id, transaction_type)
            rows.append(row)
            listing_id += 1
            listing = line
        else:
            listing += " " + line

    if listing:
        row = parse_listing(listing, config, neighborhoods, listing_id, transaction_type)
        rows.append(row)

    return rows

def parse_listing(text, config, neighborhoods, listing_id, transaction):
    neighborhood = match_neighborhood(text, neighborhoods, strategy=config.get("neighborhood_strategy"))

    price_match = re.search(r"Lps\.?\s?([\d,.]+)", text)
    price = price_match.group(1).replace(",", "") if price_match else ""
    currency = "HNL" if price else ""

    area_match = re.search(r"(\d+(\.\d+)?)\s*Mts", text)
    area = area_match.group(1) if area_match else ""

    bathrooms = "1" if any(term in text.lower() for term in config.get("bathroom_terms", [])) else ""

    property_type = "Commercial" if any(keyword in text.lower() for keyword in config.get("property_keywords", {}).get("Commercial", [])) else ""

    return {
        "Listing ID": listing_id,
        "Title": "",
        "Neighborhood": neighborhood,
        "Bedrooms": "",
        "Bathrooms": bathrooms,
        "Area": area,
        "Price": price,
        "Currency": currency,
        "Transaction": transaction,
        "Type": property_type,
        "Agency": config.get("agency", "SERPECAL"),
        "Date": "",
        "Notes": text,
        "Data Completeness": "✅" if price and neighborhood else "⚠️ Incomplete"
    }

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", required=True)
    parser.add_argument("--config", required=True)
    parser.add_argument("--neighborhoods", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()

    lines = open(args.file, encoding="utf-8").readlines()
    config = load_json(args.config)
    neighborhoods = load_json(args.neighborhoods)

    transaction_type = ""
    if lines and lines[0].strip().startswith("#"):
        header = lines.pop(0).strip().lstrip("#").upper()
        transaction_type = config.get("transaction_headers", {}).get(header, "")

    rows = parse_serpecal_lines(lines, config, neighborhoods, transaction_type)

    os.makedirs(args.output_dir, exist_ok=True)
    filename = os.path.splitext(os.path.basename(args.file))[0].lower()
    outpath = os.path.join(args.output_dir, f"serpecal_{filename}.csv")

    import csv
    with open(outpath, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    print(f"✅ Output written to: {outpath}")

if __name__ == "__main__":
    main()