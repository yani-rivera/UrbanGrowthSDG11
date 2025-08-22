import os
import re
import json
import argparse
import csv
from neighborhood_utils import match_neighborhood

def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def parse_listing(text, neighborhood, config, date, category):
    bedrooms = bathrooms = area = price = currency = ""

    bed_match = re.search(r"(\d+)\s*(hab|habitaciones?)", text, re.IGNORECASE)
    bath_match = re.search(r"(\d+)\s*(ba[ñn]o?s?)", text, re.IGNORECASE)
    area_match = re.search(r"(\d{2,4}(?:\.\d+)?)(?:\s*(m2|mts|metros))?", text, re.IGNORECASE)
    price_match = re.search(r"(\$|Lps?\.?|USD|US\$)?\s*([\d,]+\.\d{2})", text, re.IGNORECASE)

    if bed_match:
        bedrooms = bed_match.group(1)
    if bath_match:
        bathrooms = bath_match.group(1)
    if area_match:
        area = area_match.group(1)
    if price_match:
        symbol = price_match.group(1) or ""
        price = price_match.group(2).replace(",", "")
        currency = config.get("currency_aliases", {}).get(symbol.strip().upper(), symbol.strip().upper())

    property_type = ""
    property_keywords = config.get("property_keywords", {})
    for p_type, keywords in property_keywords.items():
        if any(kw.lower() in text.lower() for kw in keywords):
            property_type = p_type
            break

    transaction = ""
    if category.upper().startswith("#ALQUILER"):
        transaction = "Rent"
    elif category.upper().startswith("#VENTA"):
        transaction = "Sale"

    return {
        "Listing ID": "",
        "Title": "",
        "Neighborhood": neighborhood,
        "Bedrooms": bedrooms,
        "Bathrooms": bathrooms,
        "Area": area,
        "Price": price,
        "Currency": currency,
        "Transaction": transaction,
        "Type": property_type,
        "Agency": "SERPECAL",
        "Date": date,
        "Notes": text.strip()
    }

def segment_listings(lines):
    listings = []
    current = []
    category = ""
    data = []

    for line in lines:
        line = line.strip()
        if not line:
            continue

        if line.startswith("#"):
            category = line
            continue

        if re.match(r"^[A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ\s\.]{2,},", line):
            if current:
                data.append((" ".join(current), category))
                current = []
        current.append(line)

    if current:
        data.append((" ".join(current), category))

    return data

def write_to_csv(rows, output_path):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", required=True)
    parser.add_argument("--config", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()

    with open(args.file, encoding="utf-8") as f:
        lines = f.readlines()

    config = load_json(args.config)
    delimiter = config.get("neighborhood_delimiter", ",")

    filename = os.path.splitext(os.path.basename(args.file))[0].lower()
    date = filename.split("_")[-1]

    segmented = segment_listings(lines)
    rows = []

   
    for i, (text, category) in enumerate(segmented, start=1):
        neighborhood = text.split(delimiter)[0].strip().upper() if delimiter in text else ""
        row = parse_listing(text, neighborhood, config, date, category)
        row["Listing ID"] = i
        rows.append(row)

    output_file = os.path.join(args.output_dir, f"serpecal_{date}.csv")
    write_to_csv(rows, output_file)
    print(f"✅ Output saved to: {output_file}")

if __name__ == "__main__":
    main()
