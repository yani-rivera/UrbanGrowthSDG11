
import os
import re
import json
import argparse
import csv
from datetime import datetime
from neighborhood_utils import load_neighborhoods, match_neighborhood

def extract_price(text):
    prices = re.findall(r"[$L]\s?([\d,]+\.\d{2})", text)
    if prices:
        return float(prices[0].replace(",", ""))
    return None

def parse_inverprop_file(filepath, config_path, neighborhoods_path, output_dir):
    config = load_json(config_path)
    neighborhoods = load_neighborhoods(neighborhoods_path)

    date_str = os.path.basename(filepath).split("_")[-1].split(".")[0]
    date = datetime.strptime(date_str, "%Y%m%d").strftime("%Y-%m-%d")

    agency = config["agency"]
    prefix = config.get("listing_prefix", "*")
    transaction_map = config.get("transaction_keywords", {})
    category = ""
    listings = []

    with open(filepath, "r", encoding="utf-8") as f:
        lines = f.readlines()

    current_listing = ""
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if line.startswith("#"):
            category = line[1:].strip().upper()
            continue
        if line.startswith(prefix):
            if current_listing:
                listings.append((category, current_listing))
            current_listing = line[len(prefix):].strip()
        else:
            current_listing += " " + line.strip()

    if current_listing:
        listings.append((category, current_listing))

    os.makedirs(output_dir, exist_ok=True)
    outpath = os.path.join(output_dir, f"{agency.lower()}_{date_str}.csv")

    with open(outpath, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=[
            "Listing ID", "Title", "Neighborhood", "Bedrooms", "Bathrooms", "Area",
            "Price", "Currency", "Transaction", "Type", "Agency", "Date", "Notes"
        ])
        writer.writeheader()

        for idx, (cat, raw_text) in enumerate(listings, start=1):
            price = extract_price(raw_text)
            currency = "USD" if "$" in raw_text else "Lempiras" if "L" in raw_text else ""

            transaction = "Rent" if any(k in cat for k in transaction_map.get("rent", [])) else (
                "Sale" if any(k in cat for k in transaction_map.get("sale", [])) else ""
            )
            prop_type = "House" if "CASA" in cat else "Apartment" if "APARTAMENTO" in cat else ""

            neighborhood = match_neighborhood(raw_text, neighborhoods)

            writer.writerow({
                "Listing ID": idx,
                "Title": raw_text[:60],
                "Neighborhood": neighborhood,
                "Bedrooms": "",
                "Bathrooms": "",
                "Area": "",
                "Price": price if price else "",
                "Currency": currency,
                "Transaction": transaction,
                "Type": prop_type,
                "Agency": agency,
                "Date": date,
                "Notes": raw_text
            })

    return outpath

def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
