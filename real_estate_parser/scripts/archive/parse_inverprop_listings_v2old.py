#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
parse_inverprop_listings_v2.py
Minimal, clone-friendly agency parser runner for INVERPROP.

Behavior (per user request):
- ALWAYS call Phase 2 routine (preprocess_listings_v2.6.py) to produce a Phase-2 TXT.
- NO validations: do not gatekeep or filter; consume Phase-2 output as-is.
- Feed each non-header line to the parser with current section context from headers.
- Write final structured output to the path provided by --output (CSV or JSON by extension).

Versioning
---------
__version__   : 2.0.0
__released__  : 2025-08-29
__agency__    : INVERPROP
"""

import os
import re
import sys
import csv
import json
import argparse
import subprocess

# Import the parser orchestrator
# Assumes modules/record_parser.py is importable via PYTHONPATH. If not, add project root.
HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(HERE, os.pardir))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

try:
    from modules.record_parser import parse_record  # type: ignore
except Exception:
    # Fallback: try relative import if project layout differs during development
    sys.path.insert(0, os.path.join(PROJECT_ROOT, "modules"))
    from record_parser import parse_record  # type: ignore

try:
    from scripts.helpers import split_raw_and_parse_line, build_release_row
except ImportError:
    from helpers import split_raw_and_parse_line, build_release_row

__version__  = "2.0.0"
__released__ = "2025-08-29"
__agency__   = "INVERPROP"


def run_phase2_preprocess(raw_path: str, config_path: str, agency: str, out_path: str) -> str:
    """
    Call the existing Phase-2 script exactly as designed.
    No validations here; we trust its output and consume it as-is.
    CLI expected by preprocess_listings_v2.6.py:
      --file <raw> --config <cfg> --agency <AGENCY> [--out <phase2_out>]
    """
    args = [
        sys.executable,
        os.path.join("scripts", "preprocess_listings_v2.5.py"),
        "--input", raw_path,
        "--config", config_path,
        "--agency", agency,
        "--out", out_path,
    ]
    print("[phase2] calling:", " ".join(args))
    subprocess.run(args, check=True)
    return out_path


def infer_year_from_path_or_name(path: str) -> str:
    """
    Try to infer a 4-digit year from directory or filename.
    Falls back to 'unknown' if no match.
    """
    # Prefer directory segment .../<YEAR>/filename
    m = re.search(r"[\\/](\d{4})[\\/]", path)
    if m:
        return m.group(1)
    # Fallback: filename pattern ...YYYYMMDD...
    base = os.path.basename(path)
    m2 = re.search(r"(19|20)\d{2}\d{4}", base)
    if m2:
        return m2.group(0)[:4]
    return "unknown"


def load_json(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def each_line(path: str):
    
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            yield line.rstrip("\r\n")
            print("Linea====>>",line)

def parse_phase2_stream(phase2_path: str, cfg: dict, agency: str):
    """
    Iterate the Phase-2 TXT:
    - header lines (starting with cfg['header_marker']) update context via cfg['section_headers'] (if provided)
    - other lines are listings → feed to parse_record, unchanged (no filtering/validation)
    """
    header_marker = cfg.get("header_marker", "#")
    listing_marker = cfg.get("listing_marker", None)
    section_rules = cfg.get("section_headers", []) or []

    # precompile section patterns if any
    compiled_rules = []
    for rule in section_rules:
        pat = rule.get("pattern")
        compiled_rules.append((re.compile(pat, re.IGNORECASE) if pat else None, rule))

    ctx = {"transaction": None, "type": None, "category": None}
    listing_index = 0

    for raw in each_line(phase2_path):
        if not raw:
            yield raw

        # header line → update context; keep minimal and forgiving
        if header_marker and raw.startswith(header_marker):
            for rx, rule in compiled_rules:
                if rx and rx.search(raw):
                    ctx["transaction"] = rule.get("transaction") or ctx["transaction"]
                    ctx["type"]        = rule.get("type") or ctx["type"]
                    ctx["category"]    = rule.get("category") or ctx["category"]
                    break
            continue  # headers are not listings

        # listing line → do not strip or alter; pass text as-is
        listing_text = raw
        listing_index += 1

        fields = parse_record(
            listing_text,
            cfg,
            agency=agency,
            date=None,
            listing_no=listing_index,
            default_transaction=ctx["transaction"],
            default_type=ctx["type"],
            default_category=ctx["category"],
        )
        yield fields


def write_output(rows, out_path: str):
    ext = os.path.splitext(out_path)[1].lower()
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    if ext == ".json":
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(list(rows), f, ensure_ascii=False, indent=2)
        print(f"[write] JSON → {out_path}")
        return

    # default CSV
    rows = list(rows)
    # union of keys to keep columns stable
    keys = set()
    for r in rows:
        keys.update(r.keys())
    fieldnames = sorted(keys)

    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in rows:
            writer.writerow(r)
    print(f"[write] CSV  → {out_path}")


def main():
    ap = argparse.ArgumentParser(description="INVERPROP parser runner (v2): call Phase-2 then parse, no validations.")
    ap.add_argument("--input",  required=True, help="Raw agency TXT (will always run Phase-2).")
    ap.add_argument("--output", required=True, help="Final structured output path (.csv or .json).")
    ap.add_argument("--config", required=True, help="Agency config JSON path.")
    ap.add_argument("--agency", required=True, help="Agency name, e.g., INVERPROP.")
    ap.add_argument("--version", action="store_true", help="Print version and exit.")
    args = ap.parse_args()

    if args.version:
        print(f"{os.path.basename(__file__)} v{__version__}  released {__released__}")
        sys.exit(0)

    raw_path    = os.path.abspath(args.input)
    out_path    = os.path.abspath(args.output)
    config_path = os.path.abspath(args.config)
    agency      = args.agency

    cfg = load_json(config_path)

    # Build Phase-2 target path according to project layout: data/phase2/<AGENCY>/<YEAR>/<file>_phase2.txt
    year = infer_year_from_path_or_name(raw_path)
    phase2_dir = os.path.join(PROJECT_ROOT, "data", "phase2", agency, year)
    os.makedirs(phase2_dir, exist_ok=True)
    base_no_ext = os.path.splitext(os.path.basename(raw_path))[0]
    phase2_path = os.path.join(phase2_dir, f"{base_no_ext}_phase2.txt")

    # Always call Phase-2 routine and use its output as-is (no validations).
    run_phase2_preprocess(raw_path, config_path, agency, phase2_path)

    # Parse Phase-2 stream and write final output
    rows = list(parse_phase2_stream(phase2_path, cfg, agency))
    write_output(rows, out_path)


if __name__ == "__main__":
    main()
