# parse_serpecal_listings_v8.4.py
import os
import re
import json
import argparse
import csv
from datetime import datetime

VERSION = "v8.4"

def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def is_new_listing(line, start_exceptions):
    text = line.strip()
    if not text or text.startswith("#"):
        return False
    for exc in start_exceptions:
        if text.lower().startswith(exc.lower()):
            return False
    return bool(re.match(r"^[A-Z].*?,", text))

def preprocess_to_temp(lines, config, temp_path):
    start_excs = config.get("exceptions", {}).get("start_exceptions", [])
    with open(temp_path, "w", encoding="utf-8") as out:
        buffer = []
        for line in lines:
            line = line.strip()
            if is_new_listing(line, start_excs):
                if buffer:
                    out.write("* " + " ".join(buffer).strip() + "\n")
                buffer = [line]
            else:
                buffer.append(line)
        if buffer:
            out.write("* " + " ".join(buffer).strip() + "\n")
    return temp_path

def split_listings(lines, marker):
    content = "\n".join(line.strip() for line in lines)
    blocks = content.split(marker)
    return [blk.strip() for blk in blocks if blk.strip()]

def extract_price(text, curr_aliases):
    matches = re.findall(r"([$L]|Lps\.?)\s?([\d,]+(?:\.\d{1,2})?)", text)
    if not matches:
        return None, None
    symbol, amount = matches[-1]
    amt = float(amount.replace(",", ""))
    currency = curr_aliases.get(symbol, "")
    return amt, currency

def extract_areas(text, ac_aliases, at_aliases):
    area_ac = area_at = ""
    for val, unit in re.findall(r"(\d+[.,]?\d*)\s*(\w+)", text.lower()):
        try:
            num = float(val.replace(",", "."))
        except:
            continue
        if unit in [a.lower() for a in ac_aliases]:
            area_ac = num
        elif unit in [a.lower() for a in at_aliases]:
            area_at = num
    return area_ac, area_at

def parse_record(raw, config, agency, date_str, idx):
    title = raw[:60]
    neighborhood = raw.split(",", 1)[0].strip()
    price, currency = extract_price(raw, config.get("currency_aliases", {}))
    area_ac, area_at = extract_areas(raw,
                                     config.get("area_aliases", {}).get("ac", []),
                                     config.get("area_aliases", {}).get("at", []))
    transaction = next((k for k, vals in config.get("transaction_keywords", {}).items()
                        if any(v.lower() in raw.lower() for v in vals)), "")
    ptype = next((k for k, vals in config.get("type_keywords", {}).items()
                  if any(v.lower() in raw.lower() for v in vals)), "")

    return {
        "Listing ID": idx,
        "Title": title,
        "Neighborhood": neighborhood,
        "Bedrooms": "",
        "Bathrooms": "",
        "Area (AC)": area_ac,
        "Area (AT)": area_at,
        "Price": price if price is not None else "",
        "Currency": currency or "",
        "Transaction": transaction,
        "Type": ptype,
        "Agency": agency,
        "Date": date_str,
        "Notes": raw
    }

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", required=True)
    parser.add_argument("--config", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()

    config = load_json(args.config)
    agency = os.path.splitext(os.path.basename(args.config))[0].split("_")[1].upper()
    date_match = re.search(r"(\d{8})", os.path.basename(args.file))
    date_str = datetime.strptime(date_match.group(1), "%Y%m%d").strftime("%Y-%m-%d") if date_match else ""

    lines = open(args.file, "r", encoding="utf-8").readlines()

    if config.get("preprocessing_needed", False):
        temp_path = os.path.join("temp", f"{agency.lower()}_{date_match.group(1)}_temp.txt")
        os.makedirs(os.path.dirname(temp_path), exist_ok=True)
        preprocess_to_temp(lines, config, temp_path)
        lines = open(temp_path, "r", encoding="utf-8").readlines()

    listings_raw = split_listings(lines, config.get("listing_marker", "* "))
    rows = [parse_record(raw, config, agency, date_str, idx + 1)
            for idx, raw in enumerate(listings_raw)]

    os.makedirs(args.output_dir, exist_ok=True)
    output_name = f"{agency.lower()}_{date_str}_{VERSION}.csv"
    output_path = os.path.join(args.output_dir, output_name)
    with open(output_path, "w", newline="", encoding="utf-8") as out:
        writer = csv.DictWriter(out, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    print(f"✅ Output generated: {output_path}")

if __name__ == "__main__":
    main()
