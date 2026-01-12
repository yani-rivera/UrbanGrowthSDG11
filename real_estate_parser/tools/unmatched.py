#!/usr/bin/env python3
"""
Split CSV records by matched flag.

- Input: CSV file (UTF-8-SIG safe)
- Output:
    <input>_matched.csv
    <input>_rejectedUnmatched.csv
- No deduplication
- Columns preserved exactly
"""

import argparse
from pathlib import Path
import csv


def is_false(value):
    if value is None:
        return False
    return str(value).strip().lower() in {"false", "0", "no", "n"}


def main():
    ap = argparse.ArgumentParser(
        description="Split CSV records by matched=True / matched=False (UTF-8-SIG safe)"
    )
    ap.add_argument("--input", required=True, help="Input CSV file")
    args = ap.parse_args()

    input_path = Path(args.input)

    out_matched = input_path.with_name(
        input_path.stem + "_valid" + input_path.suffix
    )
    out_unmatched = input_path.with_name(
        input_path.stem + "_rejectedUnmatched" + input_path.suffix
    )

    with input_path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames

        if "matched" not in fieldnames:
            raise ValueError("Column 'matched' not found in CSV")

        matched_rows = []
        unmatched_rows = []

        for row in reader:
            if is_false(row.get("matched")):
                unmatched_rows.append(row)
            else:
                matched_rows.append(row)

    with out_matched.open("w", encoding="utf-8-sig", newline="") as f_ok:
        writer = csv.DictWriter(f_ok, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(matched_rows)

    with out_unmatched.open("w", encoding="utf-8-sig", newline="") as f_rej:
        writer = csv.DictWriter(f_rej, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(unmatched_rows)

    print(f"[OK] Matched records written to   : {out_matched}")
    print(f"[OK] Unmatched records written to: {out_unmatched}")
    print(f"[OK] Counts → matched: {len(matched_rows)} | rejected: {len(unmatched_rows)}")


if __name__ == "__main__":
    main()
