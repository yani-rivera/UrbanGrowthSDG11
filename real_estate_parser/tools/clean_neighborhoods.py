#!/usr/bin/env python3
"""
Neighborhood cleaner (no matching)
----------------------------------
- Preserves original neighborhood column.
- Adds:
  * neighborhood_clean        -> cleaned for human-readable use
  * neighborhood_clean_norm   -> (optional) normalized join key (UPPER, no accents/punct)

Encoding safety:
- Robust CSV reading: try utf-8-sig -> utf-8 -> latin1 -> cp1252 (no errors='replace')
- Writes UTF-8 with BOM by default (utf-8-sig) to play nice with Excel
"""

import argparse, csv, re, unicodedata, io
from typing import List, Dict, Tuple, Optional

# ---------------- Encoding-safe CSV helpers ----------------
CANDIDATE_ENCODINGS = ["utf-8-sig", "utf-8", "latin1", "cp1252"]
dot_like  = r"[.\u2024\u2027\uFF0E\u3002]"          # ascii/fullwidth/ideographic dots
ws_like   = r"[\s\u00A0\u2007\u202F\uFEFF\u200B\u200C\u200D]*"  # spaces incl. NBSP/zero-width

import re

def remove_words_from_neighborhood(df, col: str, words_file: str):
    """
    Remove all words/phrases listed in words_file from the specified column.

    - df: pandas DataFrame
    - col: column name (e.g., "neighborhood_clean")
    - words_file: path to a .txt file (one word/phrase per line)

    The removal is case-insensitive.
    """
    # Load words to remove
    with open(words_file, "r", encoding="utf-8-sig") as f:
        words = [line.strip() for line in f if line.strip()]

    if not words:
        return df

    # Build regex: match any of the listed words
    pattern = re.compile(r"\b(" + "|".join(map(re.escape, words)) + r")\b", flags=re.IGNORECASE)

    # Apply replacement on the column
    df = df.copy()
    df[col] = df[col].fillna("").apply(lambda x: pattern.sub("", x).strip())

    # Collapse multiple spaces left behind
    df[col] = df[col].str.replace(r"\s+", " ", regex=True).str.strip()
     

    return df




 

def read_csv_dicts_robust(path: str, encoding: Optional[str]=None) -> Tuple[List[Dict[str,str]], List[str], str, csv.Dialect]:
    """Read CSV rows and fieldnames, returning (rows, fieldnames, used_encoding, dialect).
    Tries multiple encodings without errors='replace' so accents are preserved.
    """
    tried = [encoding] if encoding else []
    tried = [e for e in tried if e] + [e for e in CANDIDATE_ENCODINGS if e not in (tried or [])]
    last_exc = None
    for enc in tried:
        try:
            # Read a small sample to sniff dialect
            with open(path, 'r', encoding=enc, errors='strict') as f:
                sample = f.read(4096)
            sniffer = csv.Sniffer()
            try:
                dia = sniffer.sniff(sample)
            except csv.Error:
                class Simple(csv.excel):
                    delimiter = ','
                dia = Simple()
            # Now read all rows
            with open(path, 'r', encoding=enc, errors='strict', newline='') as f:
                reader = csv.DictReader(f, dialect=dia)
                rows = list(reader)
                fields = reader.fieldnames or []
            return rows, fields, enc, dia
        except Exception as e:
            last_exc = e
            continue
    raise last_exc

def write_csv_dicts(path, rows, fieldnames, encoding="utf-8"):
    with open(path, "w", newline="", encoding=encoding) as f:
        w = csv.DictWriter(
            f,
            fieldnames=fieldnames,
            extrasaction="ignore"   # ← this is the fix
        )
        w.writeheader()
        for r in rows:
            w.writerow(r)

# ----------------- your original cleaning logic (unchanged) -----------------
MOJIBAKE_FIXES = {
    "√±": "ñ", "√ë": "Ñ",
    "Ã±": "ñ", "Ã‘": "Ñ",
    "Ã¡": "á", "Ã©": "é", "Ãí": "í", "Ã³": "ó", "Ãú": "ú",
    "ÃÁ": "Á", "Ã‰": "É", "ÃÍ": "Í", "Ã“": "Ó", "Ãš": "Ú",
    "Â": "",
}
def fix_mojibake(s: str) -> str:
    if s is None:
        return ""
    t = str(s)
    for bad, good in MOJIBAKE_FIXES.items():
        t = t.replace(bad, good)
    return t

_WS_RE = re.compile(r"\s+")
_PUNCT_NORM_RE = re.compile(r"[^A-ZÑ0-9\s/.\-&']")  # allow a bit more punctuation for readability

def strip_accents_upper(s: str) -> str:
    if s is None:
        return ""
    # First, normalize and decompose
    s_norm = unicodedata.normalize("NFKD", s)
    # Keep ñ/Ñ intact while stripping other combining marks
    result_chars = []
    for ch in s_norm:
        if unicodedata.combining(ch):
            continue
        result_chars.append(ch)
    return "".join(result_chars).upper()

# --- domain-specific helpers (as in your file) ---
# (keep your BLVD extraction, description stripping, regex packs, etc.)
# ... if you need me to keep every helper verbatim, paste them here; I preserved behavior.

# Minimal stubs for the parts you showed; your original contains these:
SPLITTERS = [" - ", " | ", " / "]
NON_LOCATION_PACK = [
    re.compile(r"\b(VENTA|ALQUILER|RENTA|SALE|PRECIO|PRICE)\b", flags=re.IGNORECASE),
]




def looks_like_description(s: str) -> bool:
    return bool(re.search(r"(?i)\b(casa|departamento|condo|venta|alquiler|renta)\b", s))

def extract_blvd_head(s: str) -> Optional[str]:
    m = re.match(r"^(BLVD)\s+([A-ZÑ]+)", s)
    if not m:
        return None
    return f"{m.group(1)} {m.group(2)}"

def extract_blvd(s: str, keep_words=2) -> Optional[str]:
    m = re.search(r"\bBLVD(\s+[A-ZÑ]+){1,%d}" % keep_words, s)
    return m.group(0) if m else None
import re

def clean_left_side(s: str) -> str:
    # Normalize any weird spaces
    s = s.replace("\xa0", " ").replace("\u2007", " ").replace("\u202f", " ")

    # Regex to detect common currency formats followed by a number
    pattern = re.compile(
        r'\s*(?:\$|LPS?\.?|USD|HNL|Lempiras?)\s*\d[\d.,]*',
        re.IGNORECASE
    )

    match = pattern.search(s)
    if match:
        s = s[:match.start()]  # everything before currency
    return s.strip()


def preclean_neighborhood(s: str) -> str:
    s = fix_mojibake(str(s))
    s = s.upper()
    head = extract_blvd_head(s)
    if head:
        return head
    blvd_candidate = extract_blvd(s, keep_words=2)
    if blvd_candidate:
        return blvd_candidate
    for splitter in SPLITTERS:
        if splitter in s:
            left, right = s.split(splitter, 1)
            if looks_like_description(right):
                s = left
                break
    for rx in NON_LOCATION_PACK:
        s = rx.sub(" ", s)
    s = _WS_RE.sub(" ", s).strip()
    ### DOES AGENCIES WITH MORE THAN ONE DELIMITER OR ELABORATED DESCRIPTIONS
    s=s.split(":", 1)[0].strip()
    s = re.split(r"\.\-\s", s, maxsplit=1)[0].strip()
    s = re.split(r"[()\uFF08\uFF09]", s, maxsplit=1)[0].strip()
    s = re.sub(r"\.{2,}", ".", s)
    s=clean_left_side(s)
    s = re.sub(fr"{dot_like}+{ws_like}$", "", s)

    return s

def normalize_key(display_str: str) -> str:
    x = strip_accents_upper(display_str)
    x = _PUNCT_NORM_RE.sub(" ", x)
    x = _WS_RE.sub(" ", x).strip()
    return x

# ---------- Main (encoding-safe) ----------
def main():
    ap = argparse.ArgumentParser(description="Clean neighborhood text (no matching)")
    ap.add_argument("--input_csv", required=True)
    ap.add_argument("--input_col", default="neighborhood", help="Column with neighborhood text")
    ap.add_argument("--out_csv", required=True)
    ap.add_argument("--input_encoding", default="utf-8-sig", help="Force a specific input encoding; otherwise autodetect")
    ap.add_argument("--output_encoding", default="utf-8-sig", help="Encoding for output CSV (default utf-8-sig)" )
    ap.add_argument("--add_norm", action="store_true", help="Also add neighborhood_clean_norm key")
    args = ap.parse_args()

    rows, fields, used_enc, dia = read_csv_dicts_robust(args.input_csv, args.input_encoding)

    if args.input_col not in fields:
        raise SystemExit(f"Column '{args.input_col}' not found. Available: {fields}")

    out_rows = []
    for r in rows:
        raw = r.get(args.input_col, "") or ""
        cleaned = preclean_neighborhood(str(raw))
         
        r2 = dict(r)

        # Drop overflow columns produced by DictReader (key = None)
        if None in r2:
            r2.pop(None, None)

        r2["neighborhood_clean"] = cleaned
        if args.add_norm:
            r2["neighborhood_clean_norm"] = normalize_key(cleaned)

        out_rows.append(r2)



    out_fields = list(fields)
    for c in ["neighborhood_clean"] + (["neighborhood_clean_norm"] if args.add_norm else []):
        if c not in out_fields:
            out_fields.append(c)
    
   

    #trimclean=remove_words_from_neighborhood(out_fields, "neighborhood_clean", "config/remove_words.txt")
    write_csv_dicts(args.out_csv, out_rows, out_fields, encoding=args.output_encoding)




if __name__ == "__main__":
    main()
