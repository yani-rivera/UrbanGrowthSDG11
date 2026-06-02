# extract_currency_aliases.py
#
# Scan all agency config JSON files and extract/merge:
#   "currency_aliases": { ... }
#
# Output:
#   configs/price_currency_config.json
#
# Usage:
#   python extract_currency_aliases.py configs/agencies/

import json
import sys
from pathlib import Path
from collections import OrderedDict


def load_json(path):

    with open(path, "r", encoding="utf-8-sig") as f:
        return json.load(f)


def main(config_dir):

    config_dir = Path(config_dir)

    if not config_dir.exists():
        print(f"[ERROR] Directory not found: {config_dir}")
        return

    merged_aliases = OrderedDict()

    scanned = 0
    found = 0

    for json_file in sorted(config_dir.rglob("*.json")):

        scanned += 1

        try:
            cfg = load_json(json_file)
            if not isinstance(cfg, dict):
                print(f"[SKIP NON-DICT] {json_file.name}")
                continue
            
        except Exception as e:
            print(f"[SKIP] {json_file.name}: {e}")
            continue

        aliases = cfg.get("currency_aliases")

        if not aliases:
            continue

        found += 1

        print(f"[FOUND] {json_file.name}")

        for alias, canonical in aliases.items():

            alias_clean = str(alias).strip()

            canonical_clean = str(canonical).strip().upper()

            if not alias_clean:
                continue

            # preserve first occurrence
            if alias_clean not in merged_aliases:

                merged_aliases[alias_clean] = canonical_clean

    # --------------------------------------------------
    # Build final structure
    # --------------------------------------------------

    output = {

        "currency_aliases": dict(merged_aliases),

        "price_magnitude_aliases": {

            "k": 1000,
            "mil": 1000,

            "m": 1000000,
            "mm": 1000000,

            "millón": 1000000,
            "millon": 1000000,
            "millones": 1000000
        },

        "price_locale_rules": {

            "decimal_max_digits": 2,

            "allow_mixed_separators": True,

            "allow_suffix_currency": True,

            "allow_prefix_currency": True
        }
    }

    # --------------------------------------------------
    # Output file
    # --------------------------------------------------

    out_path = config_dir / "price_currency_config.json"

    with open(out_path, "w", encoding="utf-8-sig") as f:

        json.dump(
            output,
            f,
            indent=4,
            ensure_ascii=False
        )

    # --------------------------------------------------
    # Summary
    # --------------------------------------------------

    print()
    print("=" * 60)
    print("DONE")
    print("=" * 60)

    print(f"Configs scanned : {scanned}")
    print(f"Configs matched : {found}")
    print(f"Aliases extracted: {len(merged_aliases)}")

    print()
    print(f"Saved to:")
    print(out_path)


if __name__ == "__main__":

    if len(sys.argv) < 2:

        print("Usage:")
        print("python extract_currency_aliases.py <config_dir>")

        sys.exit(1)

    main(sys.argv[1])