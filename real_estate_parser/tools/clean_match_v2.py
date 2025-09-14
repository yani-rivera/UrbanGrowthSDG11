#!/usr/bin/env python3
"""
Level-1 universal neighborhood cleaner + matcher (token ⇒ subset ⇒ qualifier containment)
-------------------------------------------------------------------------------
Now updated to always treat input/output files with explicit encoding (default latin-1).
- Reads input & tokens CSV with configurable encoding (default = latin-1).
- Writes outputs with the same encoding.
- Keeps original display values (accents preserved).
- Normalization (uppercase, strip accents) is only used internally for matching keys.
- Adds a pre-cleaning step to strip out prices, areas, property types, phones, emails, etc. from the neighborhood field before matching.

CLI
---
Example:
  python clean_match_v1_token_subset.py \
      --input_csv data/agency_listings.csv \
      --input_col nombre \
      --tokens_csv configs/neighborhood_tokens.csv \
      --out_matched out/agency_matched.csv \
      --out_unmatched out/agency_unmatched.csv \
      --encoding latin-1
"""
from __future__ import annotations
import argparse
import csv
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from typing import Dict, List, Tuple, Set, Optional

# ------------------------------
# Normalization utilities (safe)
# ------------------------------

def strip_accents_upper(s: str) -> str:
    if s is None:
        return ""
    s = unicodedata.normalize('NFKD', s)
    s = ''.join(ch for ch in s if not unicodedata.combining(ch))
    s = s.upper()
    return s

_WS_RE = re.compile(r"\s+")
_PUNCT_RE = re.compile(r"[^A-Z0-9\s/\-\.]")


def basic_normalize(raw: str) -> str:
    s = strip_accents_upper(str(raw))
    s = _PUNCT_RE.sub(" ", s)
    s = _WS_RE.sub(" ", s).strip()
    return s

# ------------------------------
# Pre-cleaning utilities (remove prices, areas, contact/marketing clutter)
# ------------------------------
PRICE_RE = re.compile(r"(?i)(?:US\$|USD|\$|HNL|LPS?\.?|L\.)\s*[\d.,]+(?:\s*(?:K|MIL|M|MM))?")
AREA_RE = re.compile(r"(?i)\b[\d.,]+\s*(?:M2|M\^2|M²|MT2|MTS2|MTS|METROS CUADRADOS|FT2|FT\^2|FT²|VARAS|VRS2|HA|HECTAREAS|HECTÁREAS)\b")
BED_RE = re.compile(r"(?i)\b\d+\s*(?:HABITACIONES?|HABS?|CUARTOS?)\b")
BATH_RE = re.compile(r"(?i)\b\d+(?:[.,]\d+)?\s*BAÑ?OS?\b")
LEVEL_RE = re.compile(r"(?i)\b\d+\s*(?:PISOS?|NIVELES?)\b")
PROP_TYPE_RE = re.compile(r"(?i)\b(?:CASA|HOUSE|APARTAMENTOS?|APART\.?|APT\.?|CONDOMINIO|CONDO|DUPLEX|TRIPLEX|OFICINA|LOCAL|BODEGA|TERRENO|LOTES?)\b")
SALE_RE = re.compile(r"(?i)\b(?:VENTA|ALQUILER|RENTA|RENT|SALE|PRECIO|PRICE)\b")
PHONE_RE = re.compile(r"\b\d{7,}\b")
EMAIL_RE = re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.I)
URL_RE = re.compile(r"(?i)\bhttps?://\S+|www\.\S+\b")
PUNCT_CLEAN_RE = re.compile(r"[\*\|\u2022]+")

NON_LOCATION_PACK = [PRICE_RE, AREA_RE, BED_RE, BATH_RE, LEVEL_RE, PHONE_RE, EMAIL_RE, URL_RE, SALE_RE, PROP_TYPE_RE, PUNCT_CLEAN_RE]

def preclean_neighborhood_for_matching(display_str: str) -> str:
    s = str(display_str)
    for splitter in [" - ", " | ", " – ", " — ", " * "]:
        if splitter in s:
            left, right = s.split(splitter, 1)
            if sum(ch.isdigit() for ch in left) <= sum(ch.isdigit() for ch in right):
                s = left
                break
    for rx in NON_LOCATION_PACK:
        s = rx.sub(" ", s)
    s = _WS_RE.sub(" ", s).strip()
    return s

# ------------------------------
# I/O helpers with encoding
# ------------------------------

def sniff_dialect(path: str, encoding: str) -> csv.Dialect:
    with open(path, 'r', encoding=encoding, errors='replace') as f:
        sample = f.read(4096)
    sniffer = csv.Sniffer()
    try:
        dialect = sniffer.sniff(sample)
    except csv.Error:
        class Simple(csv.excel):
            delimiter = ','
        dialect = Simple()
    return dialect

def read_rows(path: str, encoding: str) -> Tuple[List[Dict[str, str]], List[str]]:
    dialect = sniff_dialect(path, encoding)
    with open(path, 'r', encoding=encoding, errors='replace', newline='') as f:
        reader = csv.DictReader(f, dialect=dialect)
        rows = list(reader)
        return rows, reader.fieldnames or []

def write_rows(path: str, fieldnames: List[str], rows: List[Dict[str, str]], encoding: str) -> None:
    with open(path, 'w', encoding=encoding, errors='replace', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in rows:
            writer.writerow(r)

# ------------------------------
# Main
# ------------------------------

def main():
    ap = argparse.ArgumentParser(description="L1 cleaner: token ⇒ subset ⇒ qualifier containment")
    ap.add_argument('--input_csv', required=True, help='Input agency CSV file')
    ap.add_argument('--input_col', default='neighborhood', help='Column name containing the neighborhood text (e.g., nombre)')
    ap.add_argument('--tokens_csv', required=True, help='Token CSV with NeighborhoodToken, neighborhood_uid, nombre')
    ap.add_argument('--out_matched', required=True, help='Output CSV with matched rows + annotations')
    ap.add_argument('--out_unmatched', required=True, help='Output CSV with unmatched candidates + frequency')
    ap.add_argument('--encoding', default='latin-1', help='Encoding for input and output files (default latin-1)')
    args = ap.parse_args()

    enc = args.encoding

    # Read input
    rows, in_fields = read_rows(args.input_csv, enc)

    # Pre-clean neighborhood field for matching
    for r in rows:
        if args.input_col in r:
            r[args.input_col + "_clean"] = preclean_neighborhood_for_matching(r[args.input_col])

    # Read tokens
    token_rows, _ = read_rows(args.tokens_csv, enc)

    # [.. matching logic from before stays the same, but should use r[input_col + "_clean"] instead of raw_display ..]

    # Write outputs
    write_rows(args.out_matched, out_fields, out_rows, enc)
    write_rows(args.out_unmatched, ["candidate", "frequency"], unmatched_rows, enc)

if __name__ == '__main__':
    main()
