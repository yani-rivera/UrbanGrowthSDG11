#!/usr/bin/env python3
"""
Batch‑add UID to merged CSVs by looking up each row's agency in **per‑agency config files**.

UID format per row: <MNEMONIC>-<YYYYMMDD>-<SEQUENTIAL>
 - MNEMONIC: read on‑the‑fly from that agency's config file (JSON/YAML)
 - YYYYMMDD: parsed from a date column in the CSV
 - SEQUENTIAL: from a sequential column in the CSV

Key points:
 - We **read the agency from the CSV row**, normalize to lowercase, then locate its config file
   in `--configs` (config file names are all **lowercase**, per your setup).
 - Extract mnemonic from config using keys: `nemonic`, `mnemonic`, `mnem`, `code`, `shortcode`.
 - Adds the UID column as the **first column**; originals are untouched unless `--in-place`.
 - Optional path/agency consistency check.

Examples:
  python batch_add_uid.py \
    --root output \
    --configs config \
    --name-filter "*20151028.csv" \
    --agency-col agency \
    --date-col date \
    --seq-col ListingID \
    --out-suffix _uid \
    --skip-if-present
"""

import argparse
import csv
import fnmatch
import json
import os
import re
import unicodedata
from datetime import datetime
from typing import Dict, List, Optional, Tuple

try:
    import yaml  # type: ignore
except Exception:
    yaml = None

# ---------------------------- normalization ----------------------------

def norm_ag(s: str) -> str:
    """Normalize agency string: strip, collapse spaces, remove accents, lowercase."""
    if s is None:
        return ""
    s = unicodedata.normalize("NFKD", str(s))
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = re.sub(r"\s+", " ", s).strip().lower()
    return s

# ----------------------------- date parsing ----------------------------
COMMON_DATE_FORMATS: Tuple[str, ...] = (
    "%Y-%m-%d", "%Y/%m/%d", "%d/%m/%Y", "%m/%d/%Y",
    "%d-%m-%Y", "%m-%d-%Y", "%Y%m%d", "%d.%m.%Y", "%m.%d.%Y",
    "%d/%m/%y", "%m/%d/%y", "%d-%m-%y", "%m-%d-%y",
)

def normalize_date(value: str, explicit_fmt: Optional[str] = None) -> str:
    s = (value or "").strip()
    if not s:
        raise ValueError("empty date cell")
    fmts: List[Optional[str]] = [explicit_fmt] if explicit_fmt else []
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
    if len(digits) == 8 and digits[:4].isdigit():
        return digits
    raise ValueError(f"unrecognized date format: {s}")

# ------------------------------ config I/O -----------------------------

def load_any(path: str) -> Dict:
    _, ext = os.path.splitext(path.lower())
    with open(path, "r", encoding="utf-8") as fh:
        if ext in (".yml", ".yaml"):
            if yaml is None:
                raise RuntimeError("PyYAML not installed; cannot read YAML: " + path)
            data = yaml.safe_load(fh)
        else:
            data = json.load(fh)
    if not isinstance(data, dict):
        raise ValueError(f"Expected dict at root of {path}")
    return data

MNEMONIC_KEYS = ("nemonic", "mnemonic", "mnem", "code", "shortcode")

class AgencyConfigIndex:
    """Index config files in a directory and resolve agency -> config path.
       File names are assumed **lowercase**; we index stems both with and without common prefixes.
    """
    def __init__(self, cfg_dir: str):
        if not os.path.isdir(cfg_dir):
            raise FileNotFoundError(f"configs directory not found: {cfg_dir}")
        self.cfg_dir = cfg_dir
        self._by_key: Dict[str, str] = {}
        for fname in os.listdir(cfg_dir):
            low = fname.lower()
            if not low.endswith((".json", ".yml", ".yaml")):
                continue
            stem = os.path.splitext(low)[0]
            # tokens include raw stem and variants with/without common prefixes
            tokens = {stem}
            if stem.startswith("agency_"):
                tokens.add(stem[len("agency_"):])
            if stem.startswith("cfg_"):
                tokens.add(stem[len("cfg_"):])
            # also map any hyphen/space separated pieces
            tokens.add(stem.replace("-", " "))
            for t in tokens:
                key = norm_ag(t)
                self._by_key.setdefault(key, os.path.join(cfg_dir, fname))

    def find(self, agency_value: str) -> Optional[str]:
        key = norm_ag(agency_value)
        # direct match
        p = self._by_key.get(key)
        if p:
            return p
        # try stripping common words (e.g., "inmobiliaria", "agencia")
        for stop in ("inmobiliaria", "agencia", "agency"):  # extend if needed
            key2 = norm_ag(re.sub(rf"\b{stop}\b", "", key))
            if key2 and key2 in self._by_key:
                return self._by_key[key2]
        return None

    def mnemonic_for(self, agency_value: str) -> str:
        path = self.find(agency_value)
        if not path:
            raise KeyError(f"No config file found for agency '{agency_value}' in {self.cfg_dir}")
        data = load_any(path)
        for k in MNEMONIC_KEYS:
            v = data.get(k)
            if isinstance(v, str) and v.strip():
                return v.strip().upper()
        # last chance: some configs nest under a top-level object
        for k, v in data.items():
            if isinstance(v, dict):
                for kk in MNEMONIC_KEYS:
                    vv = v.get(kk)
                    if isinstance(vv, str) and vv.strip():
                        return vv.strip().upper()
        raise KeyError(f"Config {os.path.basename(path)} has no mnemonic/nemonic key for agency '{agency_value}'")

# ----------------------------- CSV helpers -----------------------------

def ensure_uid_first(header: List[str], uid_col: str) -> List[str]:
    return [uid_col] + [h for h in header if h != uid_col]

# ------------------------------ processing -----------------------------

def process_csv(input_path: str, output_path: str, uid_col: str,
                agency_col: str, date_col: str, seq_col: str,
                cfg_index: AgencyConfigIndex, date_in_format: Optional[str],
                encoding: str, skip_if_present: bool,
                expected_agency_from_path: Optional[str] = None,
                strict_agency_mismatch: bool = False,
                cache: Optional[Dict[str, str]] = None) -> int:
    cache = cache if cache is not None else {}

    with open(input_path, newline="", encoding=encoding) as fh:
        reader = csv.DictReader(fh)
        if not reader.fieldnames:
            raise ValueError(f"No header in {input_path}")
        header = list(reader.fieldnames)

        if skip_if_present and uid_col in header:
            rows = list(reader)
            header_out = header
        else:
            for col, label in ((agency_col, "agency"), (date_col, "date"), (seq_col, "sequential")):
                if col not in header:
                    raise KeyError(f"Missing {label} column '{col}' in {input_path}. Found: {header}")
            header_out = ensure_uid_first(header, uid_col)
            rows = []

            for i, row in enumerate(reader, start=2):
                # Optional consistency check with folder name
                if expected_agency_from_path:
                    ag_in_row = (row.get(agency_col) or "").strip()
                    if ag_in_row and norm_ag(ag_in_row) != norm_ag(expected_agency_from_path):
                        msg = (f"agency mismatch: path='{expected_agency_from_path}' vs row='{ag_in_row}'")
                        if strict_agency_mismatch:
                            raise ValueError(msg)
                        else:
                            print(f"[WARN] {os.path.basename(input_path)} row {i}: {msg}")

                ag_raw = row.get(agency_col, "")
                ag_key = norm_ag(ag_raw)
                if not ag_key:
                    raise ValueError(f"Empty agency at row {i} in {os.path.basename(input_path)}")

                # Resolve mnemonic with cache
                mn = cache.get(ag_key)
                if not mn:
                    mn = cfg_index.mnemonic_for(ag_raw)
                    cache[ag_key] = mn

                # Build UID
                d = normalize_date(row.get(date_col, ""), date_in_format)
                seq = str(row.get(seq_col, "")).strip()
                uid = f"{mn}-{d}-{seq}" if seq else ""

                new_row = {uid_col: uid}
                new_row.update(row)
                rows.append(new_row)

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w", encoding=encoding, newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=header_out, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    return len(rows)

# --------------------------------- CLI ---------------------------------

def run(args: argparse.Namespace) -> None:
    cfg_index = AgencyConfigIndex(args.configs)

    matched_files: List[str] = []
    for root, _, files in os.walk(args.root):
        for fname in files:
            if fnmatch.fnmatch(fname, args.name_filter) and fname.lower().endswith(".csv"):
                print("config files:",fname)
                matched_files.append(os.path.join(root, fname))

    if not matched_files:
        print("No CSV files matched.")
        return

    total_rows = 0
    total_files = 0
    cache: Dict[str, str] = {}

    for in_csv in matched_files:
        # derive expected agency from path (first component under --root)
        rel = os.path.relpath(in_csv, args.root)
        expected_agency = rel.split(os.sep)[0] if rel else None

        out_csv = in_csv if args.in_place else f"{os.path.splitext(in_csv)[0]}{args.out_suffix}.csv"

        try:
            n = process_csv(
                input_path=in_csv,
                output_path=out_csv,
                uid_col=args.uid_col,
                agency_col=args.agency_col,
                date_col=args.date_col,
                seq_col=args.seq_col,
                cfg_index=cfg_index,
                date_in_format=args.date_in_format,
                encoding=args.encoding,
                skip_if_present=args.skip_if_present,
                expected_agency_from_path=expected_agency if args.validate_agency_from_path else None,
                strict_agency_mismatch=args.strict_agency_mismatch,
                cache=cache,
            )
            total_rows += n
            total_files += 1
            print(f"[OK] {in_csv} -> {out_csv} ({n} rows)")
        except Exception as e:
            if args.continue_on_error:
                print(f"[ERR] {in_csv}: {e}")
                continue
            raise

    print(f"\nDone. Files processed: {total_files}, rows written: {total_rows}")


def build_argparser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Add UID column by reading per‑row agency and per‑agency configs.")
    p.add_argument("--root", required=True, help="Root folder to search for CSVs")
    p.add_argument("--configs", required=True, help="Directory containing per‑agency config files (filenames lowercase)")
    p.add_argument("--name-filter", default="*", help="Filename wildcard to match (default: *). Also filtered to .csv")

    p.add_argument("--uid-col", default="UID", help="Name of the UID column to add (default: UID)")
    p.add_argument("--agency-col", default="agency", help="Name of the agency column in the CSV (default: agency)")
    p.add_argument("--date-col", default="date", help="Name of the date column in the CSV (default: date)")
    p.add_argument("--seq-col", default="Listing ID", help="Name of the sequential column in the CSV (default: 'Listing ID')")
    p.add_argument("--date-in-format", help="Explicit input date format (e.g., %d/%m/%Y). If omitted, auto-detect common formats.")
    p.add_argument("--encoding", default="utf-8-sig", help="CSV encoding (default: utf-8-sig)")

    p.add_argument("--out-suffix", default="_uid", help="Suffix for output files (ignored with --in-place)")
    p.add_argument("--in-place", action="store_true", help="Overwrite input files instead of writing new ones")
    p.add_argument("--skip-if-present", action="store_true", help="Skip files that already contain the UID column")

    # Path-agency validation flags
    p.add_argument("--validate-agency-from-path", action="store_true", help="Compare CSV agency column against agency inferred from path output/<agency>/...")
    p.add_argument("--strict-agency-mismatch", action="store_true", help="Error out when agency in row differs from path-inferred agency")

    p.add_argument("--continue-on-error", action="store_true", help="Continue processing other files when an error occurs")
    return p


if __name__ == "__main__":
    args = build_argparser().parse_args()
    run(args)
