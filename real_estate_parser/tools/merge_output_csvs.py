
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
from pathlib import Path


DATE_RE = re.compile(r"_(\d{8})\.csv$", re.IGNORECASE)

def auto_out_path(output_root: str, year: str, month: str | None, day: str | None, agency: str | None) -> str:
    outdir = os.path.join(output_root, year)
    os.makedirs(outdir, exist_ok=True)
    suffix = year + (month or "") + (day or "")
    fname = (f"{agency}_{suffix}.csv" if agency else f"merged_{suffix}.csv")
    return os.path.join(outdir, fname)





def find_csvs(root_out: str, year: str, month: str | None, day: str | None, agency: str | None,
              debug: bool = False) -> List[str]:
    """
    Find CSVs matching year/month/day based on tokens in the filename:
      - YYYY
      - YYYYMM
      - YYYYMMDD

    Searches BOTH:
      1) output/<Agency>/<YEAR>/*.csv   (current pipeline)
      2) output/<Agency>/*.csv          (legacy / flat files like Agency_2015.csv)

    NOTE: This version does NOT auto-drop YYYY.csv when more granular files exist.
    (You can re-add that later once you confirm discovery works.)
    """

    # 1) Build patterns (cover both folder layouts)
    patterns = [
        os.path.join(root_out, (agency or "*"), year, "*.csv"),
        os.path.join(root_out, (agency or "*"), "*.csv"),
    ]

    files: List[str] = []
    for pat in patterns:
        hits = glob(pat)
        files.extend(hits)
        if debug:
            print(f"[DEBUG] glob: {pat} -> {len(hits)} hit(s)")

    # Deduplicate file paths (because same file might match patterns in odd layouts)
    files = sorted(set(files))

    if debug:
        print(f"[DEBUG] total candidate CSVs: {len(files)}")

    matched: List[str] = []

    # 2) Parse filename tokens robustly:
    # Look for a YEAR token optionally followed by MM and DD, but don’t require underscores.
    # Example matches:
    #   Casabianca_2015.csv
    #   Casabianca201503.csv
    #   Casabianca-20150312-clean.csv
    token_re = re.compile(rf"(?<!\d)({re.escape(year)})(\d{{2}})?(\d{{2}})?(?!\d)")

    for fp in files:
        fname = os.path.basename(fp)
        m = token_re.search(fname)

        if not m:
            if debug:
                print(f"[DEBUG] SKIP (no year token): {fname}")
            continue

        f_year = m.group(1)
        f_month = m.group(2)  # may be None
        f_day = m.group(3)    # may be None

        # Apply filters
        if month and f_month != month:
            if debug:
                print(f"[DEBUG] SKIP (month mismatch): {fname}  found MM={f_month} need MM={month}")
            continue
        if day and f_day != day:
            if debug:
                print(f"[DEBUG] SKIP (day mismatch): {fname}  found DD={f_day} need DD={day}")
            continue

        matched.append(fp)
        if debug:
            print(f"[DEBUG] KEEP: {fname}  token={f_year}{f_month or ''}{f_day or ''}")

    # 3) Stable sort: agency folder (best-effort) then filename
    def sort_key(p: str):
        path = Path(p)
        # try to infer agency folder name
        parts = [x.lower() for x in path.parts]
        # if structure is .../<Agency>/<YEAR>/<file>
        # agency is the parent of YEAR, else parent folder
        agency_name = ""
        if year in parts:
            idx = parts.index(year)
            if idx - 1 >= 0:
                agency_name = parts[idx - 1]
        if not agency_name:
            agency_name = path.parent.name.lower()
        return (agency_name, path.name.lower())

    return sorted(matched, key=sort_key)




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

    # INPUT: agency outputs (scanned)
    ap.add_argument(
        "--input",
        required=True,
        help="Directory containing per-agency output folders (input for merge)"
    )

    # OUTPUT: consolidated results (write-only)
    ap.add_argument(
        "--output",
        required=True,
        help="Directory for consolidated outputs (must NOT be inside --input)"
    )

    ap.add_argument(
        "--no-dedupe",
        action="store_true",
        help="Disable de-duplication"
    )

    ap.add_argument(
        "--dedupe-key",
        nargs="+",
        default=["agency", "ingestion_id", "Listing ID"],
        help="Columns forming the dedupe key"
    )

    ap.add_argument(
        "--out",
        help="Explicit output file path (optional)"
    )

    args = ap.parse_args()

    # ---- validate date parts ----
    if args.month and (len(args.month) != 2 or not args.month.isdigit()):
        ap.error("--month must be MM (e.g., 03)")
    if args.day and (len(args.day) != 2 or not args.day.isdigit()):
        ap.error("--day must be DD (e.g., 09)")

    # ---- resolve paths ----
    input_root = os.path.abspath(args.input)
    output_root = os.path.abspath(args.output)

    # safety: prevent self-ingestion
    if os.path.commonpath([output_root]).startswith(os.path.commonpath([input_root])):
        ap.error("--output must NOT be inside --input (prevents self-ingestion)")

    # ---- find input CSVs ----
    files = find_csvs(
        input_root,
        args.year,
        args.month,
        args.day,
        args.agency,
        debug=True
    )

    if not files:
        print(
            f"⚠️ No CSVs found under {input_root}/<Agency>/{args.year}/ matching filters.",
            file=sys.stderr
        )
        sys.exit(2)

    header = union_headers(files)
    out_rows = []
    seen_keys = set()
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
            r.setdefault("source_agency", agency_name or r.get("agency", ""))

            merged = {h: r.get(h, "") for h in header}

            if dedupe:
                key = make_dedupe_key(merged, args.dedupe_key)
                if key in seen_keys:
                    continue
                seen_keys.add(key)

            out_rows.append(merged)

    # ---- output path ----
    out_path = (
        args.out
        or auto_out_path(output_root, args.year, args.month, args.day, args.agency)
    )

    os.makedirs(os.path.dirname(os.path.abspath(out_path)) or ".", exist_ok=True)

    with open(out_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=header)
        writer.writeheader()
        writer.writerows(out_rows)

    suffix = args.year + (args.month or "") + (args.day or "")
    target = args.agency or "ALL"

    print(
        f"✅ Merged {len(files)} file(s) for [{target}] @ [{suffix}] "
        f"→ {len(out_rows)} rows into {out_path}"
    )

    if dedupe:
        print(f"   Dedupe key: {args.dedupe_key}")

if __name__ == "__main__":
    main()
