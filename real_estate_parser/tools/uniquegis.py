
#!/usr/bin/env python3
"""
Preprocess GIS zones:
- One row per GISID
- Concatenate unique zones (deduped, trimmed, newline-safe) with a chosen separator
- Generate UID as: DC-<ALPHANUMERIC>-<SEQUENTIAL>

Usage:
  python preprocess_gis_zones.py input.csv output.csv \
    --id-col GISID --zone-col ZONE --sep ":" --alpha-len 6 --seq-digits 4 --seed 0
"""

import argparse
import csv
import random
import string
import sys
from collections import defaultdict, OrderedDict
from pathlib import Path

def parse_args():
    p = argparse.ArgumentParser(description="Preprocess GIS zones CSV.")
    p.add_argument("input", help="Path to input CSV")
    p.add_argument("output", help="Path to write processed CSV")
    p.add_argument("--id-col", default="GISID", help="Name of the ID column (default: GISID)")
    p.add_argument("--zone-col", default="ZONE", help="Name of the Zone column (default: ZONE)")
    p.add_argument("--sep", default=":", help="Separator to use when joining zones (default: :)")
    p.add_argument("--alpha-len", type=int, default=6, help="Length of the alphanumeric middle part (default: 6)")
    p.add_argument("--seq-digits", type=int, default=4, help="Digits for zero-padded sequential number (default: 4)")
    p.add_argument("--keep-input-order", action="store_true",
                   help="Keep the first-seen order of GISIDs (default sorts by GISID ascending).")
    p.add_argument("--seed", type=int, default=None,
                   help="Random seed for reproducible alphanumeric codes (optional).")
    return p.parse_args()

def clean_zone(z: str) -> str:
    if z is None:
        return ""
    z = str(z).strip()
    # replace any line breaks inside zones to keep output one-line per record
    z = z.replace("\r", " ").replace("\n", " ")
    return z

def random_alphanumeric(n: int) -> str:
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=n))

def main():
    args = parse_args()
    if args.seed is not None:
        random.seed(args.seed)

    in_path = Path(args.input)
    out_path = Path(args.output)

    if not in_path.exists():
        print(f"ERROR: Input file not found: {in_path}", file=sys.stderr)
        sys.exit(1)

    # Read CSV with utf-8-sig to handle BOM if present
    with in_path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        # Validate columns
        if args.id_col not in reader.fieldnames or args.zone_col not in reader.fieldnames:
            print(f"ERROR: CSV must contain columns '{args.id_col}' and '{args.zone_col}'. "
                  f"Found: {reader.fieldnames}", file=sys.stderr)
            sys.exit(1)

        # Preserve first-seen order of GISIDs if requested
        seen_order = OrderedDict()
        zones_by_id = defaultdict(list)

        for row in reader:
            gid_raw = row[args.id_col]
            if gid_raw is None or str(gid_raw).strip() == "":
                # skip rows missing the id
                continue
            gid = str(gid_raw).strip()
            z = clean_zone(row.get(args.zone_col))
            if z != "":
                zones_by_id[gid].append(z)
            if args.keep_input_order and gid not in seen_order:
                seen_order[gid] = None

    # Build output rows
    # Deduplicate zones per GISID, sort A→Z for consistency (or keep insertion order if desired)
    def unique_sorted(iterable):
        # de-dup then sort for stable output
        return sorted(set(iterable), key=lambda s: (s.upper(), s))

    if args.keep_input_order:
        ordered_ids = list(seen_order.keys()) or list(zones_by_id.keys())
        # include GISIDs that had no zones if any (rare)
        for gid in zones_by_id.keys():
            if gid not in seen_order:
                ordered_ids.append(gid)
    else:
        # numeric sort when possible, else lexical
        def sort_key(x):
            try:
                return (0, int(x))
            except ValueError:
                return (1, x)
        ordered_ids = sorted(zones_by_id.keys(), key=sort_key)

    output_rows = []
    for gid in ordered_ids:
        zlist = zones_by_id.get(gid, [])
        zuniq = unique_sorted(zlist)
        zones_joined = args.sep.join(zuniq)
        output_rows.append({
            args.id_col: gid,
            "ZONES": zones_joined
        })

    # Generate UIDs: DC-<ALPHANUMERIC>-<SEQUENTIAL>
    for idx, row in enumerate(output_rows, start=1):
        alpha = random_alphanumeric(args.alpha_len)
        seq = str(idx).zfill(args.seq_digits)
        row["UID"] = f"DC-{alpha}-{seq}"

    # Write output CSV
    with out_path.open("w", encoding="utf-8", newline="") as f:
        fieldnames = [args.id_col, "ZONES", "UID"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(output_rows)

    print(f"✅ Wrote {len(output_rows)} records to: {out_path}")

if __name__ == "__main__":
    main()
