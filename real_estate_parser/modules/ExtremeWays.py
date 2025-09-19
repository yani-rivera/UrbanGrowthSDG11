#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ExtremeWays — parse agency free-text listings into structured rows.
- Marker optional (one physical line can be one listing, but we handle wrapped lines, too)
- Comma-delimited fields per listing
- Headers (# .. ######) tracked; bullets before headers are ignored
- Splits fused records at each price boundary
- Outputs CSV (default) or JSON
"""

import argparse
import csv
import json
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

# ------------------------- regexes & helpers -------------------------

BED_RX   = re.compile(r"\b(\d+)\s*(?:hab(?:itaciones)?|bed(?:rooms)?)\b", re.I)
BATH_RX  = re.compile(r"\b(\d+(?:\s*[.,]?\s*½)?)\s*(?:bañ(?:o|os)|bano|banos?|bath(?:rooms)?)\b", re.I)
PRICE_RX = re.compile(r"(?i)(?:\$\s*\.?|LPS?\.?|L\.)\s*[\d.,\s]+")

# Header: optional bullet, 1–6 #'s, optional trailing colon
HEADER_RX = re.compile(r"""^\s*
    (?:[-*+•–—·]\s+)?        # optional bullet
    (?P<hashes>\#{1,6})\s*   # markdown hashes
    (?P<title>.+?)\s*:?\s*$  # header text (trim optional colon)
""", re.X)

# Split when a price is followed by what looks like a NEW listing start (UPPER/NUM + comma)
FUSION_SPLIT_RX = re.compile(
    r"(?P<price>(?:\$\s*\.?|LPS?\.?|L\.)\s*[\d.,\s]+)\s+(?=(?:[A-ZÁÉÍÓÚÑ0-9][A-ZÁÉÍÓÚÑ0-9 .#/-]*,))",
    re.I
)

def _half_to_float(s: str) -> float:
    s = s.strip().replace("½", ".5")
    s = re.sub(r"(\d+)\s*[,\.]?\s*5$", r"\1.5", s)
    s = re.sub(r"[^\d\.]", "", s)
    try:
        return float(s)
    except ValueError:
        return 0.0

def _parse_price_from_text(s: str) -> Tuple[Optional[str], Optional[float], Optional[str], str]:
    """Return (currency, price_float, price_text, text_without_that_price)."""
    matches = list(PRICE_RX.finditer(s))
    if not matches:
        return (None, None, None, s)
    last = matches[-1]
    raw = last.group(0)
    cur = "USD" if "$" in raw else "HNL"
    num_str = re.sub(r"[^\d.]", "", raw.replace(",", ""))
    try:
        val = float(num_str)
    except ValueError:
        val = None
    start, end = last.span()
    rest = (s[:start] + s[end:]).strip().strip(", ")
    return (cur, val, raw.strip(), rest)

def _flatten_spaces(text: str) -> str:
    t = re.sub(r"\s+", " ", text or " ")
    return t.strip()

def _split_fused_block(text: str) -> List[str]:
    """Split a block that may contain multiple listings fused after prices."""
    flat = _flatten_spaces(text)
    parts: List[str] = []
    i = 0
    for m in FUSION_SPLIT_RX.finditer(flat):
        end = m.end("price")
        part = flat[i:end].strip(" ,")
        if part:
            parts.append(part)
        i = end
    tail = flat[i:].strip(" ,")
    if tail:
        parts.append(tail)
    return parts if parts else ([flat] if flat else [])

# ------------------------- per-listing parse -------------------------

def parse_listing_line(line: str) -> Optional[Dict[str, Any]]:
    s = (line or "").strip()
    if not s or s.startswith("#"):
        return None

    # Extract price (and remove it from the body for cleaner tokenization)
    currency, price, price_text, body_wo_price = _parse_price_from_text(s)

    # Tokenize by commas (agency convention)
    parts = [p.strip() for p in body_wo_price.split(",") if p.strip()] \
         or [p.strip() for p in s.split(",") if p.strip()]
    if not parts:
        return None

    neighborhood = parts[0]
    tail = ", ".join(parts[1:]) if len(parts) > 1 else ""

    beds = None
    mb = BED_RX.search(tail)
    if mb:
        beds = int(mb.group(1))

    baths = None
    mt = BATH_RX.search(tail)
    if mt:
        baths = _half_to_float(mt.group(1))

    # Keep descriptive tokens that aren’t bed/bath/price
    features = [
        p for p in parts[1:]
        if not (BED_RX.search(p) or BATH_RX.search(p) or PRICE_RX.search(p))
    ]

    return {
        "neighborhood": neighborhood,
        "beds": beds,
        "baths": baths,
        "currency": currency,
        "price": price,
        "price_text": price_text,
        "features": features,
        "raw": s,
    }

# ------------------------- full-text parse (headers aware) -------------------------

def parse_agency_text_with_headers(raw: str) -> List[Dict[str, Any]]:
    """
    Scan the raw text, track current header (# .. ######), accumulate lines until
    split by price boundaries, parse each listing, and tag with section info.
    """
    out: List[Dict[str, Any]] = []
    cur_header: Optional[str] = None
    cur_level: Optional[int] = None
    buf: List[str] = []

    def flush_buf():
        nonlocal buf, cur_header, cur_level, out
        if not buf:
            return
        block = _flatten_spaces(" ".join(buf))
        for piece in _split_fused_block(block):
            rec = parse_listing_line(piece)
            if rec:
                rec["section"] = cur_header
                rec["section_level"] = cur_level
                out.append(rec)
        buf = []

    for ln in (raw or "").splitlines():
        # remove a stray "* " right before a header
        ln = re.sub(r"^\s*\*\s+(?=#)", "", ln)

        mh = HEADER_RX.match(ln)
        if mh:
            flush_buf()
            cur_header = mh.group("title").strip()
            cur_level = len(mh.group("hashes"))
            continue

        if ln.strip():
            buf.append(ln)

    flush_buf()
    return out

# ------------------------- output helpers -------------------------

CSV_FIELDS = [
    "section", "neighborhood", "beds", "baths",
    "currency", "price", "price_text", "features", "raw"
]

def rows_to_csv(rows: List[Dict[str, Any]], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        w.writeheader()
        for r in rows:
            w.writerow({
                "section": r.get("section"),
                "neighborhood": r.get("neighborhood"),
                "beds": r.get("beds"),
                "baths": r.get("baths"),
                "currency": r.get("currency"),
                "price": r.get("price"),
                "price_text": r.get("price_text"),
                "features": "; ".join(r.get("features", [])),
                "raw": r.get("raw"),
            })

def rows_to_json(rows: List[Dict[str, Any]], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)

# ------------------------- CLI -------------------------

def main():
    ap = argparse.ArgumentParser(
        prog="ExtremeWays",
        description="Parse agency free-text listings into CSV/JSON (marker optional; headers supported).",
    )
    ap.add_argument("input", nargs="?", help="Path to input .txt (if omitted, read from STDIN)")
    ap.add_argument("-o", "--output", default="listings.csv", help="Output path (default: listings.csv)")
    ap.add_argument("--format", choices=["csv", "json"], default="csv", help="Output format")
    ap.add_argument("--encoding", default="utf-8", help="Input encoding (default: utf-8)")
    ap.add_argument("--summary", action="store_true", help="Print a short parse summary to stdout")
    args = ap.parse_args()

    # Read input
    if args.input:
        raw = Path(args.input).read_text(encoding=args.encoding, errors="replace")
    else:
        import sys
        raw = sys.stdin.read()

    rows = parse_agency_text_with_headers(raw)

    out_path = Path(args.output)
    if args.format == "csv":
        rows_to_csv(rows, out_path)
    else:
        rows_to_json(rows, out_path)

    if args.summary:
        print(f"ExtremeWays → {len(rows)} listings → {out_path}")

if __name__ == "__main__":
    main()
