#!/usr/bin/env python3
"""
headers_to_json.py — Extract section headers from a raw listings TXT file
and generate a JSON stub you can merge into your agency config.

It looks for lines that start with a header marker (default '#').
Examples it will detect (spaces optional):
  #ALQUILER DE CASAS
  # ALQUILER DE APARTAMENTOS
  ## VENTA DE CASAS
  ＃VENTA DE TERRENOS   (full‑width hash, common in some OCR/PDF exports)

For each unique header it emits an object with:
  { "pattern": <text>, "transaction": <Rent|Sale|...>, "type": <House|Apartment|Land|...>, "category": <text> }

Usage
-----
python tools/headers_to_json.py \
  --input data/raw_listings.txt \
  --out configs/sections_stub.json \
  [--marker '#'] [--no-infer] [--debug]

- --marker: change if your headers use another symbol (e.g., '*', '##').
- --no-infer: disable simple heuristics; leave transaction/type blank.
- --debug: print the first few non‑matches to help diagnose markers/encoding.
"""

from __future__ import annotations
import argparse, json, os, re, sys

TRANSACTION_MAP = {
    "ALQUILER": "Rent",
    "RENTA": "Rent",
    "VENTA": "Sale",
    "SE VENDEN": "Sale",
}

TYPE_MAP = {
    "CASA": "House",
    "CASAS": "House",
    "APART": "Apartment",   # matches APARTAMENTO/APARTAMENTOS/APARTMENT
    "DEPTO": "Apartment",
    "DEPARTAMENTO": "Apartment",
    "TERRENO": "Land",
    "TERRENOS": "Land",
    "LOTE": "Land",
    "LOTES": "Land",
    "BODEGA": "Commercial",
    "LOCAL": "Commercial",
    "OFICINA": "Commercial",
}


def guess_fields(header: str, enable_infer: bool = True) -> dict:
    text = (header or "").upper().strip()
    if not enable_infer:
        return {"pattern": header.strip(), "transaction": "", "type": "", "category": header.strip()}

    # Transaction inference
    transaction = ""
    for key, val in TRANSACTION_MAP.items():
        if key in text:
            transaction = val
            break

    # Type inference
    ptype = ""
    for key, val in TYPE_MAP.items():
        if key in text:
            ptype = val
            break

    return {
        "pattern": header.strip(),
        "transaction": transaction,
        "type": ptype,
        "category": header.strip(),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, help="Path to raw TXT file (listings with headers)")
    ap.add_argument("--out", required=True, help="Path to save JSON config stub")
    ap.add_argument("--marker", default="#", help="Header marker prefix to detect (default '#')")
    ap.add_argument("--no-infer", action="store_true", help="Disable transaction/type inference")
    ap.add_argument("--debug", action="store_true", help="Print diagnostic info about header detection")
    args = ap.parse_args()

    marker = str(args.marker)
    # Accept ASCII '#' or full‑width '＃' by default; if a custom marker is provided, honor it.
    if marker == "#":
        marker_rx = re.compile(r"^\s*[#＃]+\s*(.+?)\s*$")
    else:
        marker_rx = re.compile(rf"^\s*{re.escape(marker)}+\s*(.+?)\s*$")

    headers = []
    with open(args.input, "r", encoding="utf-8-sig", errors="ignore") as f:
        for i, line in enumerate(f, 1):
            m = marker_rx.match(line)
            if m:
                headers.append(m.group(1))
            elif args.debug and i <= 10:
                # Show a few early lines that didn't match to help debug markers
                print(f"[debug] no‑match L{i}: {line!r}")

    if not headers:
        print(
            f"⚠️ No headers found using marker '{marker}'. "
            "Try --marker '##' or check the file. If it uses full‑width '＃', rerun without --marker or with --debug."
        )
        sys.exit(0)

    # Deduplicate while keeping order of first appearance
    seen = set()
    uniq = []
    for h in headers:
        key = h.strip().upper()
        if key not in seen:
            seen.add(key)
            uniq.append(h.strip())

    section_headers = [guess_fields(h, enable_infer=(not args.no_infer)) for h in uniq]
    out_data = {"section_headers": section_headers}

    os.makedirs(os.path.dirname(os.path.abspath(args.out)) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fo:
        json.dump(out_data, fo, indent=2, ensure_ascii=False)

    print(f"✅ Extracted {len(section_headers)} headers → {args.out}")


if __name__ == "__main__":
    main()
