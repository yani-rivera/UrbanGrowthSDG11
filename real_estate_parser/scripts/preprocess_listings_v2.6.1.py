#python scripts/preprocess_listings_v2.6.1.py \
#  --file temp/serpecal_20151228.txt \
#  --config config/agency_serpecal.json \
#  --agency SERPECAL \
#  --out temp/serpecal_20151228_temp.txt




#!/usr/bin/env python3
# scripts/preprocess_listings_v2.6.py

import re
import os
import sys
import json
import argparse
import unicodedata
from typing import List, Tuple

# --- OPTIONAL import if you already created agency_preprocess.py earlier ---
try:
    from modules.agency_preprocess import ocr_sanitize as _external_ocr_sanitize
except Exception:
    _external_ocr_sanitize = None


# -----------------------------
# OCR sanitation (standalone)
# -----------------------------
def ocr_sanitize(text: str) -> str:
    """
    Minimal, safe OCR sanitation so downstream regexes hit more reliably.
    Keeps semantics, does NOT translate fields. Notes/raw text should still keep originals later.
    """
    if not text:
        return ""
    s = str(text)

    # Normalize unicode / compatibility forms
    s = unicodedata.normalize("NFKC", s)

    # Common OCR garbage & fixes (extend as you discover new patterns)
    fixes = [
        (r'\$\.', '$ '),                       # "$.700,000" -> "$ 700,000"
        (r'(Lps?|L)\.(\d)', r'\1. \2'),        # "Lps.3000"  -> "Lps. 3000"
        (r'US\$(\d)', r'US$ \1'),

        # Known misreads for bathrooms/accents
        (r'\bbafios\b', 'baños'),
        (r'\bbanos\b', 'baños'),
        (r'\bbano\b', 'baño'),

        # Units standardization
        (r'\b(mts?2|mt2|m2)\b', 'm²'),
        (r'\b(vr2|vrs2|v2)\b', 'vrs²'),

        # Ensure a space after currency for price regex
        (r'(\$)(\d)', r'\1 \2'),
        (r'(Lps?\.?|US\$)(\s*)(\d)', r'\1 \3'),

        # Collapse bullets / soft hyphen / fancy quotes
        ('\u2022', '*'),
        ('\u00AD', ''),        # soft hyphen
        ('\u2018', "'"),
        ('\u2019', "'"),
        ('\u201C', '"'),
        ('\u201D', '"'),
    ]
    for pat, rep in fixes:
        s = re.sub(pat, rep, s, flags=re.IGNORECASE)

    # Fix hyphenation across line breaks (if multi-line OCR input)
    s = re.sub(r'-\s*\n\s*', '', s)

    # Collapse spaces
    s = re.sub(r'[ \t]+', ' ', s)
    # Normalize line endings
    s = s.replace('\r\n', '\n').replace('\r', '\n')
    return s.strip("\r\n")


# -----------------------------
# Listing boundary detection
# -----------------------------
HEADER_TOKENS = r'(col\.|res\.|barrio|urb\.|blvd\.|anillo periferico)'

def is_header_start(line: str) -> bool:
    """
    Heuristic: line begins with a location header like 'COL. PALMIRA:' or 'RES. MONSEÑOR ... :'
    """
    return bool(re.match(rf'^\s*{HEADER_TOKENS}\s*[^:]+:', line, flags=re.IGNORECASE))

def is_symbol_start(line: str, symbols: List[str]) -> bool:
    """
    True if line begins with one of the agency's known symbols (e.g., "*", ">", "•")
    """
    sym_class = ''.join(re.escape(s) for s in symbols if s)
    if not sym_class:
        return False
    return bool(re.match(rf'^\s*[{sym_class}]+\s*', line))

def should_start_new_listing(prev: str, curr: str, markers: dict) -> bool:
    """
    Decide if 'curr' is the start of a new listing, using (a) explicit symbols, (b) header tokens, (c) strong punctuation hints.
    """
    # 1) Explicit symbol markers
    if is_symbol_start(curr, markers.get("symbols", [])):
        return True

    # 2) Header tokens pattern: 'COL./RES./BARRIO/URB./BLVD./ANILLO ... :'
    if is_header_start(curr):
        return True

    # 3) Strong punctuation hint: line starts with ALL CAPS word(s) then colon
    #    e.g., "AMAPALA:" or "BULEVAR ..." (fallback if OCR lost the 'COL.' / 'RES.' token)
    if re.match(r'^[A-ZÁÉÍÓÚÑ0-9][A-ZÁÉÍÓÚÑ0-9\s\.\-]{2,30}:\s', curr):
        return True

    # 4) If previous line is very short (like a tail) and current looks long, consider start
    if prev and len(prev) < 20 and len(curr) > 30:
        return True

    return False


def segment_listings(sanitized_text: str, agency_markers: dict) -> List[str]:
    """
    Splits OCR text into listings. Returns a list of listing strings.
    """
    symbols = agency_markers.get("symbols", [])
    lines = [ln.strip("\r\n") for ln in sanitized_text.splitlines() if ln.strip("\r\n")]

    listings = []
    buf = []

    prev_line = ""
    for ln in lines:
        if should_start_new_listing(prev_line, ln, agency_markers):
            # flush buffer
            if buf:
                listings.append(' '.join(buf).strip())
                buf = []
        # remove the leading symbol if present
        if is_symbol_start(ln, symbols):
            if PHASE1_ACTIVE:
                ln = re.sub(r'^\s*[' + ''.join(re.escape(s) for s in symbols) + r']+\s*', '', ln)
            else:
                ln = re.sub(r'^([' + ''.join(re.escape(s) for s in symbols) + r'])\s+', r'\1 ', ln, count=1)

        buf.append(ln)
        prev_line = ln

    if buf:
        listings.append(' '.join(buf).rstrip())
    # Optional de-dup: remove tiny fragments (noise)
    listings = [x for x in listings if len(x) >= 12]
    return listings


# -----------------------------
# IO / CLI
# -----------------------------
def load_config(config_path: str) -> dict:
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)

def markers_for_agency(config: dict, agency: str) -> dict:
    """
    Returns a dict of markers for this agency, e.g.:
    { "symbols": ["*", "•", ">"] }
    """
    # allow both top-level or per-agency blocks
    ag = (agency or "").strip().upper()
    # try per-agency first
    per = (config.get("agencies", {}) or {}).get(ag, {})
    if per.get("listing_markers"):
        return per["listing_markers"]
    # legacy keys
    if per.get("symbols"):
        return {"symbols": per["symbols"]}

    # global defaults
    symbols = config.get("listing_symbols", []) or config.get("symbols", []) or []
    # fallback: known common markers if config is sparse
    if not symbols:
        symbols = ["*", "•", ">"]
    return {"symbols": symbols}

def main():
    ap = argparse.ArgumentParser(description="Pre-process OCR classifieds into 1 listing per line.")
    ap.add_argument("--file", required=True, help="OCR text input (.txt)")
    ap.add_argument("--config", required=True, help="Agency config JSON")
    ap.add_argument("--agency", required=True, help="Agency code (e.g., SERPECAL)")
    ap.add_argument("--out", required=False, help="Output temp file (.txt). If omitted, writes alongside input with _temp suffix.")
    args = ap.parse_args()

    with open(args.file, "r", encoding="utf-8") as f:
        raw = f.read()

    cfg = load_config(args.config)
    global PHASE1_ACTIVE
    preprocess_list = cfg.get("preprocess") or [2]
    emit_marker     = bool(cfg.get("emit_marker", False))
    PHASE1_ACTIVE   = (1 in preprocess_list) and emit_marker

    markers = markers_for_agency(cfg, args.agency)

    # Prefer external sanitizer if available; else use local
    sanitized = _external_ocr_sanitize(raw) if _external_ocr_sanitize else ocr_sanitize(raw)

    segments = segment_listings(sanitized, markers)

    # Decide output path
    if args.out:
        out_path = args.out
    else:
        root, ext = os.path.splitext(args.file)
        out_path = f"{root}_temp.txt"

    with open(out_path, "w", encoding="utf-8") as out:
        for seg in segments:
            out.write(seg.rstrip("\r\n") + "\n")

    print(f"✅ Preprocess complete for {args.agency}")
    print(f"   Input lines   : {len([ln for ln in raw.splitlines() if ln.strip()])}")
    print(f"   Listings found: {len(segments)}")
    print(f"   Output file   : {out_path}")

if __name__ == "__main__":
    sys.exit(main())
