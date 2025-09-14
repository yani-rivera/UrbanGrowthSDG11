#!/usr/bin/env python3
"""
Clean candidate neighborhood strings (light/heavy) and normalize (Ñ preserved)
-----------------------------------------------------------------------------
This script expects your merged listings CSV already has a *candidate* field for
neighborhood (e.g., first 25 chars or text before a colon). It produces:
  • neighborhood_clean        → human‑readable cleaned name
  • neighborhood_clean_norm   → uppercase, accents stripped but Ñ preserved
  • neigh_mode                → 'light' or 'heavy' depending on detected noise

Rules
-----
- Mojibake repair (fix common encoding artifacts like CASTA√ëOS → CASTAÑOS).
- Special boulevard rule: if raw text contains BLVD/BLV, keep "BLVD <NEXTWORD>".
  (If you don't have the raw column, this step is skipped.)
- Light mode (already name-like): remove leading admin prefixes (COLONIA/COL./
  BARRIO/RES./RESIDENCIAL/APARTAM/APT.), collapse whitespace.
- Heavy mode (numbers, price/area/bed/bath/etc. present): remove noise chunks
  (prices, areas, bedrooms/baths, phones, URLs, sale words, property types),
  then apply prefix removal and tidy whitespace.
- Normalization preserves Ñ as distinct from N (CAMPANA ≠ CAMPAÑA).

CLI
---
python clean_candidates.py \
  --input_csv merged.csv \
  --input_col neighborhood \
  --out_csv merged_clean.csv \
  --encoding utf-8 \
  [--raw_col description]
"""
from __future__ import annotations
import argparse
import re
import unicodedata
import pandas as pd
import csv


# ------------------ Mojibake repair ------------------

# --- mojibake repair ---



MOJIBAKE_FIXES = {
    "√±": "ñ", "√ë": "Ñ",
    "Ã±": "ñ", "Ã‘": "Ñ",
    "Ã¡": "á", "Ã©": "é", "Ãí": "í", "Ã³": "ó", "Ãº": "ú",
    "ÃÁ": "Á", "Ã‰": "É", "ÃÍ": "Í", "Ã“": "Ó", "Ãš": "Ú",
    "Â": "",
}
def fix_mojibake(s: str) -> str:
    t = "" if s is None else str(s)
    for bad, good in MOJIBAKE_FIXES.items():
        t = t.replace(bad, good)
    return t

# --- Ñ-preserving normalize ---
_WS_RE = re.compile(r"\s+")
_PUNCT = re.compile(r"[^A-ZÑ0-9\s/\-\.]")  # allow Ñ

def strip_accents_preserve_ene(s: str) -> str:
    s = "" if s is None else str(s)
    s = s.replace("Ñ","##ENE_UP##").replace("ñ","##ene_low##")
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = s.replace("##ENE_UP##","Ñ").replace("##ene_low##","ñ")
    return s.upper()

def normalize_key(s: str) -> str:
    s = strip_accents_preserve_ene(s)
    s = _PUNCT.sub(" ", s)
    s = _WS_RE.sub(" ", s).strip()
    return s

# --- month expansions + OCR tails ---
MONTH_MAP = [
    (r"\bENE\.?\b", "ENERO"),
    (r"\bFEB\.?\b", "FEBRERO"),
    (r"\bMAR\.?\b", "MARZO"),
    (r"\bABR\.?\b", "ABRIL"),
    (r"\bMAY\.?\b", "MAYO"),
    (r"\bJUN\.?\b", "JUNIO"),
    (r"\bJUL\.?\b", "JULIO"),
    (r"\bAGO\.?\b", "AGOSTO"),
    (r"\bSET\.?\b|\bSEP\.?T?\.?\b", "SEPTIEMBRE"),
    (r"\bOCT\.?\b", "OCTUBRE"),
    (r"\bNOV\.?\b", "NOVIEMBRE"),
    (r"\bDIC\.?\b", "DICIEMBRE"),
]
def expand_months(s: str) -> str:
    t = s
    for pat, repl in MONTH_MAP:
        t = re.sub(pat, repl, t, flags=re.IGNORECASE)
    return t

OCR_TAIL_RE = re.compile(r"\b(SEPTIEMBRE|SEPT|SEP|SET)\.[A-Z\*]+\b", re.IGNORECASE)
def strip_ocr_tails(s: str) -> str:
    return OCR_TAIL_RE.sub(lambda m: m.group(1), s)

def prep_key(s: str) -> str:
    """mojibake → month expand → strip OCR tails → Ñ-preserving normalize"""
    return normalize_key(strip_ocr_tails(expand_months(fix_mojibake(s))))






def fix_mojibake(s: str) -> str:
    if s is None:
        return ""
    t = str(s)
    for bad, good in MOJIBAKE_FIXES.items():
        t = t.replace(bad, good)
    return t

# ------------------ Normalization (Ñ preserved) ------------------
_WS_RE = re.compile(r"\s+")
_PUNCT_NORM_RE = re.compile(r"[^A-ZÑ0-9\s/\-\.]")  # allow Ñ

def strip_accents_preserve_ene(s: str) -> str:
    s = "" if s is None else str(s)
    s = s.replace("Ñ", "##ENE_UP##").replace("ñ", "##ene_low##")
    s = unicodedata.normalize("NFKD", s)
    s = ''.join(ch for ch in s if not unicodedata.combining(ch))
    s = s.replace("##ENE_UP##", "Ñ").replace("##ene_low##", "ñ")
    return s.upper()


def normalize_key(s: str) -> str:
    s = strip_accents_preserve_ene(s)
    s = _PUNCT_NORM_RE.sub(" ", s)
    s = _WS_RE.sub(" ", s).strip()
    return s

# ------------------ BLVD/BLV detector ------------------
BLVD_ANY_RE = re.compile(r"(?i)\b(BLVD\.?|BLV\.?)(?:\s+)([A-ZÁÉÍÓÚÜÑ0-9]+)")

def extract_blvd_anywhere(raw: str) -> str | None:
    m = BLVD_ANY_RE.search(raw)
    if m:
        blvd = m.group(1).upper().rstrip('.')
        nxt = m.group(2).upper().rstrip('.')
        return f"{blvd} {nxt}"
    return None

# ------------------ Prefixes & noise ------------------
PREFIX_RE = re.compile(
    r"^(?:COLONI|COLONIA|COL\.?|BARRIO|RESIDENCIAL|RES\.?|APARTAM|APARTAMENTO[S]?|APT\.?)\s+",
    re.IGNORECASE,
)

PRICE_RE = re.compile(r"(?i)(?:US\$|USD|\$|HNL|LPS?\.?|L\.)\s*[\d.,]+(?:\s*(?:K|MIL|M|MM))?")
AREA_RE  = re.compile(r"(?i)\b[\d.,]+\s*(?:M2|M\^2|M²|MT2|MTS2|MTS|METROS CUADRADOS|FT2|FT\^2|FT²|VARAS|VRS2|HA|HECTAREAS|HECTÁREAS)\b")
BED_RE   = re.compile(r"(?i)\b(?:DE\s*)?\d+(?:[.,]\d+)?\s*(?:HAB(?:IT(?:A\w*)?)?|HABS?|DORM(?:ITORIOS?)?|DORMS?|CUARTOS?)\b")
BATH_RE  = re.compile(r"(?i)\b(?:DE\s*)?\d+(?:[.,]\d+)?\s*(?:BAÑ?O(?:S)?|BANO(?:S)?)\b")
LEVEL_RE = re.compile(r"(?i)\b\d+\s*(?:PISOS?|NIVELES?)\b")
PROP_RE  = re.compile(r"(?i)\b(?:CASA|HOUSE|APARTAMENTOS?|APART\.?|APT\.?|CONDOMINIO|CONDO|DUPLEX|TRIPLEX|OFICINA|LOCAL|BODEGA|TERRENO|LOTES?)\b")
SALE_RE  = re.compile(r"(?i)\b(?:VENTA|ALQUILER|RENTA|RENT|SALE|PRECIO|PRICE)\b")
PHONE_RE = re.compile(r"\b\d{7,}\b")
EMAIL_RE = re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.I)
URL_RE   = re.compile(r"(?i)\bhttps?://\S+|www\.\S+\b")
PUNCT_CLEAN_RE = re.compile(r"[\*\|\u2022]+")

NON_LOCATION_PACK = [
    PRICE_RE, AREA_RE, BED_RE, BATH_RE, LEVEL_RE,
    PHONE_RE, EMAIL_RE, URL_RE, SALE_RE, PROP_RE, PUNCT_CLEAN_RE,
]

# ------------------ Mode classifier ------------------

def classify_mode(candidate: str) -> str:
    s = candidate or ""
    for rx in (PRICE_RE, AREA_RE, BED_RE, BATH_RE, PHONE_RE, URL_RE, EMAIL_RE, SALE_RE, PROP_RE):
        if rx.search(s):
            return "heavy"
    return "light"

# ------------------ Cleaning core ------------------

def clean_candidate(candidate: str, raw_full: str | None = None) -> tuple[str, str, str]:
    """Return (clean, norm, mode) from a candidate string.
    - If raw_full provided and contains BLVD/BLV, return 'BLVD <WORD>'.
    - Otherwise choose light/heavy based on candidate noise.
    """
    cand = fix_mojibake(candidate or "")

    # BLVD override from raw text if available
    if raw_full is not None and isinstance(raw_full, str):
        blvd = extract_blvd_anywhere(fix_mojibake(raw_full))
        if blvd:
            clean = blvd
            return clean, normalize_key(clean), "blvd"

    mode = classify_mode(cand)

    if mode == "light":
        s = PREFIX_RE.sub("", cand).strip()
        s = _WS_RE.sub(" ", s).strip()
        return s, normalize_key(s), mode

    # heavy: strip noise first, then prefixes
    s = cand
    for rx in NON_LOCATION_PACK:
        s = rx.sub(" ", s)
    s = PREFIX_RE.sub("", s)
    s = _WS_RE.sub(" ", s).strip()
    return s, normalize_key(s), mode

# ------------------ CLI ------------------

def main():
    ap = argparse.ArgumentParser(description="Clean candidate neighborhoods (light/heavy)")
    ap.add_argument("--input_csv", required=True)
    ap.add_argument("--input_col", default="neighborhood", help="Column with candidate neighborhood text")
    ap.add_argument("--out_csv", required=True)
    ap.add_argument("--encoding", default="utf-8")
    ap.add_argument("--raw_col", default=None, help="Optional column with full raw text to enable BLVD override")
    args = ap.parse_args()

    df = pd.read_csv(args.input_csv, encoding=args.encoding)
    if args.input_col not in df.columns:
        raise SystemExit(f"Column '{args.input_col}' not found. Available: {list(df.columns)}")

    use_raw = args.raw_col and (args.raw_col in df.columns)

    cleans, norms, modes = [], [], []
    for _, row in df.iterrows():
        raw_full = row[args.raw_col] if use_raw else None
        clean, norm, mode = clean_candidate(row[args.input_col], raw_full)
        cleans.append(clean)
        norms.append(norm)
        modes.append(mode)

    df["neighborhood_clean"] = cleans
    df["neighborhood_clean_norm"] = norms
    df["neigh_mode"] = modes

    df.to_csv(args.out_csv, index=False, encoding=args.encoding)
    print(f"✅ Cleaned {len(df)} rows → {args.out_csv}")

if __name__ == "__main__":
    main()
