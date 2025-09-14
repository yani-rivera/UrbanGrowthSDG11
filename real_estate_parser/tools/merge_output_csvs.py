
#!/usr/bin/env python3
# tools/merge_output_csvs.py
"""
Merge per-agency CSVs from: output/<Agency>/<YEAR>/*.csv
Filters: --year (required), optional --month, --day, optional --agency
Auto output path (if --out omitted):
  output/consolidated/<YEAR>/
    merged_<YYYY>.csv | merged_<YYYYMM>.csv | merged_<YYYYMMDD>.csv
    <Agency>_<YYYY>.csv | <Agency>_<YYYYMM>.csv | <Agency>_<YYYYMMDD>.csv
"""

import argparse
import csv
import os
import re
import sys
from glob import glob
from typing import List, Tuple, Dict

DATE_RE = re.compile(r"_(\d{8})\.csv$", re.IGNORECASE)

def auto_out_path(output_root: str, year: str, month: str | None, day: str | None, agency: str | None) -> str:
    outdir = os.path.join(output_root, "consolidated", year)
    os.makedirs(outdir, exist_ok=True)
    suffix = year + (month or "") + (day or "")
    fname = (f"{agency}_{suffix}.csv" if agency else f"merged_{suffix}.csv")
    return os.path.join(outdir, fname)

def find_csvs(root_out: str, year: str, month: str | None, day: str | None, agency: str | None) -> List[str]:
    """
    Find CSVs matching year/month/day (based on filename suffix _YYYYMMDD.csv).
    Searches: output/*/<YEAR>/*.csv  or  output/<Agency>/<YEAR>/*.csv
    """
    patterns = [os.path.join(root_out, (agency or "*"), year, "*.csv")]
    files: List[str] = []
    for pat in patterns:
        files.extend(glob(pat))
    matched = []
    for fp in files:
        m = DATE_RE.search(fp)
        if not m:
            continue
        yyyymmdd = m.group(1)
        f_year, f_month, f_day = yyyymmdd[:4], yyyymmdd[4:6], yyyymmdd[6:8]
        if f_year != year:
            continue
        if month and f_month != month:
            continue
        if day and f_day != day:
            continue
        matched.append(fp)
    # stable order: by agency folder then filename
    return sorted(matched, key=lambda p: (p.replace("\\", "/").split("/")[-3].lower(), os.path.basename(p).lower()))

def sniff_agency_from_path(path: str) -> str:
    # output/<Agency>/<Year>/file.csv
    try:
        return path.replace("\\", "/").split("/")[-3]
    except Exception:
        return ""

def read_rows(path: str) -> Tuple[List[str], List[Dict[str, str]]]:
    # tolerant reader
    for enc in ("utf-8-sig", "utf-8"):
        try:
            with open(path, "r", encoding=enc, newline="") as f:
                reader = csv.DictReader(f)
                return (reader.fieldnames or []), [dict(r) for r in reader]
        except UnicodeDecodeError:
            continue
    with open(path, "r", encoding="latin-1", newline="") as f:
        reader = csv.DictReader(f)
        return (reader.fieldnames or []), [dict(r) for r in reader]

def union_headers(files: List[str]) -> List[str]:
    seen: List[str] = []
    for fp in files:
        hdr, _ = read_rows(fp)
        for h in hdr:
            if h not in seen:
                seen.append(h)
    preferred = [
        "Listing ID","title","neighborhood","bedrooms","bathrooms",
        "area","area_unit","area_m2","AT","AT_unit",
        "price","currency","transaction","property_type",
        "agency","date","notes","source_type","ingestion_id","pipeline_version"
    ]
    ordered = [h for h in preferred if h in seen]
    ordered += [h for h in seen if h not in ordered]
    # provenance helpers
    if "source_file" not in ordered: ordered.append("source_file")
    if "source_agency" not in ordered: ordered.append("source_agency")
    return ordered

def make_dedupe_key(row: Dict[str, str], keys: List[str]) -> tuple:
    return tuple((row.get(k, "") or "").strip() for k in keys)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--year", required=True, help="Year (YYYY)")
    ap.add_argument("--month", help="Month (MM)")
    ap.add_argument("--day", help="Day (DD)")
    ap.add_argument("--agency", help="Filter by agency folder name (e.g., Casabianca)")
    ap.add_argument("--output-root", default="output", help="Root output dir (default: output)")
    ap.add_argument("--out", help="Override output CSV path (otherwise auto to output/consolidated/<YEAR>/...)")
    ap.add_argument("--no-dedupe", action="store_true", help="Disable de-duplication")
    ap.add_argument("--dedupe-key", nargs="+",
                    default=["agency","ingestion_id","Listing ID"],
                    help="Columns forming the dedupe key (default: agency ingestion_id 'Listing ID')")
    args = ap.parse_args()

    # Validate date parts
    if args.month and (len(args.month) != 2 or not args.month.isdigit()):
        ap.error("--month must be MM (e.g., 03)")
    if args.day and (len(args.day) != 2 or not args.day.isdigit()):
        ap.error("--day must be DD (e.g., 09)")

    files = find_csvs(args.output_root, args.year, args.month, args.day, args.agency)
    if not files:
        print(f"⚠️ No CSVs found under {args.output_root}/<Agency>/{args.year}/ matching filters.", file=sys.stderr)
        sys.exit(2)

    header = union_headers(files)
    out_rows: List[Dict[str, str]] = []
    seen_keys: set[tuple] = set()
    dedupe = not args.no_dedupe
    total_in = 0

    for fp in files:
        agency_name = sniff_agency_from_path(fp)
        hdr, rows = read_rows(fp)
        total_in += len(rows)
        for r in rows:
            r = dict(r)  # copy
            # provenance
            r.setdefault("source_file", os.path.basename(fp))
            r.setdefault("source_agency", agency_name or r.get("agency",""))
            # align to union header
            merged = {h: r.get(h, "") for h in header}
            if dedupe:
                key = make_dedupe_key(merged, args.dedupe_key)
                if key in seen_keys:
                    continue
                seen_keys.add(key)
            out_rows.append(merged)

    out_path = args.out or auto_out_path(args.output_root, args.year, args.month, args.day, args.agency)
    os.makedirs(os.path.dirname(os.path.abspath(out_path)) or ".", exist_ok=True)
    with open(out_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=header)
        writer.writeheader()
        writer.writerows(out_rows)

    uniq = len(out_rows)
    suffix = args.year + (args.month or "") + (args.day or "")
    target = args.agency or "ALL"
    print(f"✅ Merged {len(files)} file(s) for [{target}] @ [{suffix}] → {uniq} rows into {out_path}")
    if dedupe:
        print(f"   Dedupe key: {args.dedupe_key}")

if __name__ == "__main__":
    main()
