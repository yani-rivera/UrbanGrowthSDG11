#!/usr/bin/env python3
"""
Add a UID column as the first column of a CSV file.

UID format: <mnemonic>-<YYYYMMDD>-<sequential>
 - mnemonic: read from an agency config file (JSON or YAML) under key "mnemonic" (configurable)
 - date: read from a date column in the CSV (name configurable), normalized to YYYYMMDD
 - sequential: read from a numeric/text column in the CSV (name configurable)

Examples:
  python add_uid_column.py \
    --config agency_vinsa.json \
    --input listings.csv \
    --output listings_with_uid.csv \
    --date-col Fecha \
    --seq-col Nro

If --output is omitted, the script writes alongside input as <stem>_uid.csv.

Notes:
- Handles JSON or YAML config (PyYAML optional). If mnemonic is missing, derives from the
  agency name in config (key "agency") or the config filename stem.
- Always *adds* a UID column, even if one exists already (so you could have both).
- Accepts many common date formats; falls back conservatively with warnings.
"""

import argparse
import csv
import json
import os
import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple

try:
    import yaml  # type: ignore
except Exception:
    yaml = None


def load_config(path: str) -> Dict:
    if not os.path.exists(path):
        raise FileNotFoundError(f"Config file not found: {path}")
    _, ext = os.path.splitext(path.lower())
    with open(path, "r", encoding="utf-8") as fh:
        if ext in (".yml", ".yaml"):
            if yaml is None:
                raise RuntimeError("PyYAML is not installed but YAML config provided. Install pyyaml or use JSON.")
            data = yaml.safe_load(fh)
        else:
            data = json.load(fh)
    if not isinstance(data, dict):
        raise ValueError("Config root must be an object/dict.")
    return data


def derive_mnemonic_from_name(name: str, max_len: int = 6) -> str:
    base = re.sub(r"[^A-Za-z0-9]", "", name or "").upper()
    return (base[:max_len] or "AGENCY")


def extract_mnemonic(cfg: Dict, mnemonic_key: str) -> str:
    if mnemonic_key in cfg and isinstance(cfg[mnemonic_key], str) and cfg[mnemonic_key].strip():
        return cfg[mnemonic_key].strip().upper()
    for k in ("mnemonic", "mnem", "code", "shortcode"):
        if k in cfg and isinstance(cfg[k], str) and cfg[k].strip():
            return cfg[k].strip().upper()
    if isinstance(cfg.get("agency"), str) and cfg["agency"].strip():
        return derive_mnemonic_from_name(cfg["agency"].strip())
    filename = cfg.get("__config_filename__")
    if isinstance(filename, str):
        return derive_mnemonic_from_name(os.path.splitext(os.path.basename(filename))[0])
    return "AGENCY"

COMMON_DATE_FORMATS: Tuple[str, ...] = (
    "%Y-%m-%d",
    "%Y/%m/%d",
    "%d/%m/%Y",
    "%m/%d/%Y",
    "%d-%m-%Y",
    "%m-%d-%Y",
    "%Y%m%d",
    "%d.%m.%Y",
    "%m.%d.%Y",
)


def normalize_date(value: str, explicit_fmt: Optional[str] = None) -> str:
    s = (value or "").strip()
    if not s:
        raise ValueError("Empty date cell")
    fmts = [explicit_fmt] if explicit_fmt else []
    fmts.extend([f for f in COMMON_DATE_FORMATS if f not in fmts])
    if re.fullmatch(r"\d{8}", s):
        return s
    for fmt in fmts:
        if not fmt:
            continue
        try:
            dt = datetime.strptime(s, fmt)
            return dt.strftime("%Y%m%d")
        except Exception:
            pass
    digits = re.sub(r"[^0-9]", "", s)
    if len(digits) == 8:
        if digits[:4] in {str(y) for y in range(1900, 2101)}:
            return digits
    raise ValueError(f"Unrecognized date format: '{s}'")


def ensure_uid_first(header: List[str], uid_col: str) -> List[str]:
    # Always add UID as a new column at front
    return [uid_col] + header


def run(args: argparse.Namespace) -> None:
    cfg = load_config(args.config)
    cfg["__config_filename__"] = args.config
    mnemonic = extract_mnemonic(cfg, args.mnemonic_key)

    with open(args.input, newline="", encoding=args.encoding) as fh:
        reader = csv.DictReader(fh)
        if reader.fieldnames is None:
            raise ValueError("Input CSV has no header row.")
        header = list(reader.fieldnames)

        for col, label in ((args.date_col, "date"), (args.seq_col, "sequential")):
            if col not in header:
                raise KeyError(f"Missing {label} column '{col}' in input CSV. Present columns: {header}")

        uid_col = args.uid_col
        header_out = ensure_uid_first(header, uid_col)

        rows_out: List[Dict[str, str]] = []
        for i, row in enumerate(reader, start=1):
            date_raw = row.get(args.date_col, "")
            seq_raw = row.get(args.seq_col, "")

            try:
                date_yyyymmdd = normalize_date(date_raw, args.date_in_format)
                seq_str = str(seq_raw).strip()
                uid_val = f"{mnemonic}-{date_yyyymmdd}-{seq_str}" if seq_str else ""
            except Exception as e:
                if args.strict:
                    raise
                print(f"⚠️  Row {i+1} (after header): could not build UID: {e}. Leaving UID empty.")
                uid_val = ""

            new_row = {uid_col: uid_val}
            new_row.update(row)
            rows_out.append(new_row)

    out_path = args.output
    if not out_path:
        base, ext = os.path.splitext(args.input)
        out_path = f"{base}_uid{ext or '.csv'}"

    with open(out_path, "w", encoding=args.encoding, newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=header_out, extrasaction="ignore")
        writer.writeheader()
        for row in rows_out:
            writer.writerow(row)

    print(f"✅ Wrote {len(rows_out)} rows to {out_path}\n    Added UID column as first column: {uid_col}")


def build_argparser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Add UID column to CSV: <mnemonic>-<YYYYMMDD>-<sequential>.")
    p.add_argument("--config", required=True, help="Path to agency config file (JSON or YAML) that contains 'mnemonic'.")
    p.add_argument("--input", required=True, help="Input CSV path")
    p.add_argument("--output", help="Output CSV path (default: <input>_uid.csv)")
    p.add_argument("--date-col", required=True, help="Name of the date column in the CSV")
    p.add_argument("--seq-col", required=True, help="Name of the sequential column in the CSV")
    p.add_argument("--uid-col", default="UID", help="Name of the UID column to add (default: UID)")
    p.add_argument("--mnemonic-key", default="mnemonic", help="Key in the config that holds the mnemonic (default: mnemonic)")
    p.add_argument("--date-in-format", help="Explicit input date format (e.g., %d/%m/%Y). If omitted, auto-detect common formats.")
    p.add_argument("--encoding", default="utf-8-sig", help="CSV encoding for input/output (default: utf-8-sig)")
    p.add_argument("--strict", action="store_true", help="Fail on parse errors instead of warning and leaving blank UIDs")
    return p


if __name__ == "__main__":
    args = build_argparser().parse_args()
    run(args)
