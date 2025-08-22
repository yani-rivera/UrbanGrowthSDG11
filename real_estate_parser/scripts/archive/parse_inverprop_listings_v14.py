# Inverprop Listing Parser v1.3.3
import re
import pandas as pd
import os
import json
import argparse
import logging
from datetime import datetime
from difflib import get_close_matches

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Load lexicon and neighborhoods
def load_json(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)

LEXICON = load_json("config/lexicon_inverprop.json")
NEIGHBORHOODS = load_json("config/neighborhoods_inverprop.json")
SECTION_MAP = load_json("config/section_to_transaction_map.json")

# Normalize neighborhood names using best match
def normalize_neighborhood(text):
    text = text.strip().lower()
    matches = get_close_matches(text, NEIGHBORHOODS.keys(), n=1, cutoff=0.8)
    return NEIGHBORHOODS[matches[0]] if matches else text.title()

def detect_section_map_by_headers(text):
    section_lines = text.split("\n")
    section_context = {}
    current_section = ""
    for line in section_lines:
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("#"):
            label = stripped[1:].strip().lower()
            for keyword in SECTION_MAP:
                if keyword in label:
                    current_section = SECTION_MAP[keyword]
                    break
        elif stripped.startswith("*"):
            section_context[stripped] = current_section
    return section_context

def infer_transaction_from_text(entry_text, fallback):
    entry_text_lower = entry_text.lower()
    if "alquiler" in entry_text_lower or "renta" in entry_text_lower:
        return "Rent"
    if "venta" in entry_text_lower or "se vende" in entry_text_lower:
        return "Sale"
    return fallback

def preprocess_raw_text(raw_text):
    # Join wrapped lines into one block per listing
    lines = raw_text.splitlines()
    combined_lines = []
    buffer = ""
    for line in lines:
        if line.strip().startswith("#"):
            if buffer:
                combined_lines.append(buffer)
                buffer = ""
            combined_lines.append(line.strip())
        elif line.strip().startswith("*"):
            if buffer:
                combined_lines.append(buffer)
            buffer = line.strip()
        else:
            buffer += " " + line.strip()
    if buffer:
        combined_lines.append(buffer)
    return "\n".join(combined_lines)

def parse_inverprop_listings(raw_text, agency="Inverprop", date="2015-12-28"):
    cleaned_text = preprocess_raw_text(raw_text)
    section_context = detect_section_map_by_headers(cleaned_text)
    listings = [line.strip() for line in cleaned_text.split("\n") if line.strip().startswith("*")]

    records = []
    for entry in listings:
        original = entry
        entry_clean = re.sub(r'[^\w\s.,$/()º°VvMm]+', '', entry)

        # Match currencies even if stuck to words like "panoramica$"
        price_matches = re.findall(r'([A-Z]*\$|L)\s?([\d.,]+)', entry_clean)
        prices = [(LEXICON["currency_aliases"].get(s.strip(), s.strip()), p.replace(",", "")) for s, p in price_matches] if price_matches else [("", "")]

        bed_matches = re.findall(r'(\d+)\s?(%s)' % '|'.join(LEXICON["bedroom_terms"]), entry, re.IGNORECASE)
        bed_counts = [b[0] for b in bed_matches] if bed_matches else [""]

        bath_match = re.search(r'(\d+)\s?(%s)' % '|'.join(LEXICON["bathroom_terms"]), entry, re.IGNORECASE)
        bathrooms = bath_match.group(1) if bath_match else ""

        area_m2 = re.search(r'(\d+)\s?M2', entry, re.IGNORECASE)
        area_v2 = re.search(r'(\d+)\s?V2', entry, re.IGNORECASE)

        raw_neighborhood = re.split(r'\d|,', entry)[0].strip()[:50]
        neighborhood = normalize_neighborhood(raw_neighborhood)

        section_guess = section_context.get(entry, "Sale")
        transaction = infer_transaction_from_text(entry, section_guess)

        prop_type = "House"
        for ptype, keywords in LEXICON["property_keywords"].items():
            if any(kw in entry.lower() for kw in keywords):
                prop_type = ptype
                break

        for currency, price in prices:
            for bedrooms in bed_counts:
                observaciones = []
                if not price: observaciones.append("Missing price")
                if not bedrooms: observaciones.append("Missing bedrooms")
                if not currency: observaciones.append("Missing currency")

                try:
                    numeric_price = float(price.replace(",", "")) if price else ""
                except ValueError:
                    numeric_price = ""
                    observaciones.append("Invalid price")

                records.append({
                    "Listing ID": "",  # Placeholder, to be numbered later
                    "Neighborhood": neighborhood,
                    "Bedrooms": bedrooms,
                    "Bathrooms": bathrooms,
                    "Area_m2": area_m2.group(1) if area_m2 else "",
                    "Area_v2": area_v2.group(1) if area_v2 else "",
                    "Price": numeric_price,
                    "Currency": currency,
                    "Transaction": transaction,
                    "Type": prop_type,
                    "Agency": agency,
                    "Date": date,
                    "Notes": original,
                    "Observaciones": "; ".join(observaciones)
                })

    df_new = pd.DataFrame(records)

    year = datetime.strptime(date, "%Y-%m-%d").year
    output_dir = os.path.join("data", "output", agency, str(year))
    os.makedirs(output_dir, exist_ok=True)
    filename = f"{agency}_Listings_{date.replace('-', '')}.xlsx"
    filepath = os.path.join(output_dir, filename)

    if os.path.exists(filepath):
        df_existing = pd.read_excel(filepath)
        df_combined = pd.concat([df_existing, df_new], ignore_index=True)
        df_combined.drop_duplicates(subset="Notes", inplace=True)
        df_combined.reset_index(drop=True, inplace=True)
    else:
        df_combined = df_new

    df_combined["Listing ID"] = range(1, len(df_combined) + 1)
    df_combined.to_excel(filepath, index=False)
    logging.info(f"Saved: {filepath}")

    return df_combined

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Parse Inverprop listings from .txt file")
    parser.add_argument("--file", required=True, help="Path to raw text file (e.g., data/raw/inverprop/xxx.txt)")
    parser.add_argument("--agency", default="Inverprop", help="Agency name")
    parser.add_argument("--date", default="2015-12-28", help="Listing date (YYYY-MM-DD)")
    args = parser.parse_args()

    if not os.path.exists(args.file):
        logging.error(f"Input file not found: {args.file}")
        exit(1)

    with open(args.file, "r", encoding="utf-8") as f:
        raw_text = f.read()

    parse_inverprop_listings(raw_text, agency=args.agency, date=args.date)
