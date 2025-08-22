
import argparse
import json
import os
import re

def is_potential_listing_start(line, start_exceptions):
    stripped = line.strip()
    if not stripped:
        return False
    first_word = stripped.split()[0].lower().strip(".,:;")
    normalized_exceptions = {e.lower().strip(".,:;") for e in start_exceptions}
    return stripped[0].isupper() and first_word not in normalized_exceptions

def preprocess_listings(input_file, output_file, marker, agency, config):
    with open(input_file, 'r', encoding='utf-8') as infile:
        lines = infile.readlines()

    start_exceptions = config.get("start_exceptions", [])
    preprocessed = []
    buffer = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        if stripped.startswith("#"):
            if buffer:
                preprocessed.append(marker + " " + " ".join(buffer).strip())
                buffer = []
            preprocessed.append(stripped)
        elif is_potential_listing_start(stripped, start_exceptions):
            if buffer:
                preprocessed.append(marker + " " + " ".join(buffer).strip())
                buffer = []
            buffer.append(stripped)
        else:
            buffer.append(stripped)

    if buffer:
        preprocessed.append(marker + " " + " ".join(buffer).strip())

    with open(output_file, 'w', encoding='utf-8') as outfile:
        for item in preprocessed:
            outfile.write(item + "\n")

    print(f"✅ Preprocessed {len(preprocessed)} items to {output_file}")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="Input file path")
    parser.add_argument("--output", required=True, help="Output file path")
    parser.add_argument("--marker", default="*", help="Listing marker")
    parser.add_argument("--agency", required=True, help="Agency name")
    parser.add_argument("--config", required=True, help="Path to config JSON")
    args = parser.parse_args()

    with open(args.config, 'r', encoding='utf-8') as f:
        config = json.load(f)

    preprocess_listings(args.input, args.output, args.marker, args.agency, config)

if __name__ == "__main__":
    main()
