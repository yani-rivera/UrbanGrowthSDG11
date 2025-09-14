
#!/usr/bin/env python3
"""
Neighborhood cleaner (no matching)
----------------------------------
- Preserves original neighborhood column.
- Adds:
  * neighborhood_clean        -> cleaned for human-readable use
  * neighborhood_clean_norm   -> (optional) normalized join key (UPPER, no accents/punct)
Usage:
  python clean_neighborhoods.py \
    --input_csv path/to/listings.csv \
    --input_col neighborhood \
    --out_csv path/to/listings_clean.csv \
    --encoding utf-8 \
    --add_norm
"""
import argparse, csv, re, unicodedata

# ---------- normalization helpers ----------
_WS_RE = re.compile(r"\s+")
_PUNCT_NORM_RE = re.compile(r"[^A-Z0-9\s/\-\.]")  # keep space, slash, hyphen, dot


# Keep BLVD/BLV + next word (robust to trailing dots)
BLVD_HEAD_RE = re.compile(r"(?i)^\s*(BLVD\.?|BLV\.?)\s+([A-ZÁÉÍÓÚÜÑ0-9]+)")

def extract_blvd_head(s: str) -> str | None:
    """
    If the string starts with BLVD/BLV, return 'BLVD <NEXTWORD>' in UPPERCASE,
    stripping any trailing periods (e.g., 'BLVD. SUYAPA.' -> 'BLVD SUYAPA').
    """
    m = BLVD_HEAD_RE.match(s)
    if not m:
        return None
    blvd = m.group(1).upper().rstrip(".")
    nxt  = m.group(2).upper().rstrip(".")
    return f"{blvd} {nxt}"



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
        # If decomposed base is 'n' but original was ñ, keep as ñ
        if ch in ("n", "N") and "̃" in s:  # combining tilde
            result_chars.append("Ñ" if ch.isupper() else "ñ")
        else:
            result_chars.append(ch)
    s = "".join(result_chars).upper()
    return s


# ---------- cleaning packs ----------
# Remove only LEADING admin prefixes
PREFIX_RE = re.compile(r"^(?:BARRIO|RESIDENCIAL|RES\.?|COLONIA)\s+", re.IGNORECASE)

PRICE_RE = re.compile(r"(?i)(?:US\$|USD|\$|HNL|LPS?\.?|L\.)\s*[\d.,]+(?:\s*(?:K|MIL|M|MM))?")
AREA_RE  = re.compile(r"(?i)\b[\d.,]+\s*(?:M2|M\^2|M²|MT2|MTS2|MTS|METROS CUADRADOS|FT2|FT\^2|FT²|VARAS|VRS2|HA|HECTAREAS|HECTÁREAS)\b")
BED_RE   = re.compile(r"(?i)\b\d+\s*(?:HABITACIONES?|HABS?|CUARTOS?|DORMITORIOS?)\b")
BATH_RE  = re.compile(r"(?i)\b\d+(?:[.,]\d+)?\s*BAÑ?OS?\b")
LEVEL_RE = re.compile(r"(?i)\b\d+\s*(?:PISOS?|NIVELES?)\b")
PROP_RE  = re.compile(r"(?i)\b(?:CASA|HOUSE|APARTAMENTOS?|APART\.?|APT\.?|CONDOMINIO|CONDO|DUPLEX|TRIPLEX|OFICINA|LOCAL|BODEGA|TERRENO|LOTES?)\b")
SALE_RE  = re.compile(r"(?i)\b(?:VENTA|ALQUILER|RENTA|RENT|SALE|PRECIO|PRICE)\b")
PHONE_RE = re.compile(r"\b\d{7,}\b")
EMAIL_RE = re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.I)
URL_RE   = re.compile(r"(?i)\bhttps?://\S+|www\.\S+\b")
PUNCT_CLEAN_RE = re.compile(r"[\*\|\u2022]+")
MOJIBAKE_FIXES = {
    "√±": "ñ", "√ë": "Ñ",
    "Ã±": "ñ", "Ã‘": "Ñ",
    "Ã¡": "á", "Ã©": "é", "Ãí": "í", "Ã³": "ó", "Ãú": "ú",
    "ÃÁ": "Á", "Ã‰": "É", "ÃÍ": "Í", "Ã“": "Ó", "Ãš": "Ú",
    "Â": "",
}






NON_LOCATION_PACK = [PRICE_RE, AREA_RE, BED_RE, BATH_RE, LEVEL_RE,
                     PHONE_RE, EMAIL_RE, URL_RE, SALE_RE, PROP_RE, PUNCT_CLEAN_RE]

SPLITTERS = [" - ", " | ", " – ", " — ", " * "]





def extract_blvd(s: str, keep_words=2) -> str:
    """
    If 'BLVD' is found, return 'BLVD' + the next N words.
    Defaults to BLVD + 2 words (e.g., 'BLVD LOS PROCERES').
    """
    parts = s.split()
    for i, p in enumerate(parts):
        if p.upper() == "BLVD":
            keep = parts[i : i + 1 + keep_words]  # BLVD + next N
            return " ".join(keep).upper()
    return None

def fix_mojibake(s: str) -> str:
    if s is None:
        return ""
    t = str(s)
    for bad, good in MOJIBAKE_FIXES.items():
        t = t.replace(bad, good)
    return t


def preclean_neighborhood(s: str) -> str:
    s = fix_mojibake(str(s))
    s = s.upper()

    head = extract_blvd_head(s)
    if head:
        return head

    # --- special case for BLVD ---
    blvd_candidate = extract_blvd(s, keep_words=2)  # BLVD + 2 words
    if blvd_candidate:
        return blvd_candidate

    # --- existing cleaning rules ---
    for splitter in SPLITTERS:
        if splitter in s:
            left, right = s.split(splitter, 1)
            if looks_like_description(right):
                s = left
                break
    for rx in NON_LOCATION_PACK:
        s = rx.sub(" ", s)
    s = PREFIX_RE.sub("", s)
    s = _WS_RE.sub(" ", s).strip()
    return s


def normalize_key(display_str: str) -> str:
    x = strip_accents_upper(display_str)
    x = _PUNCT_NORM_RE.sub(" ", x)
    x = _WS_RE.sub(" ", x).strip()
    return x

# ---------- csv helpers ----------
def sniff_dialect(path: str, encoding: str):
    with open(path, "r", encoding=encoding, errors="replace") as f:
        sample = f.read(4096)
    sniffer = csv.Sniffer()
    try:
        return sniffer.sniff(sample)
    except csv.Error:
        class Simple(csv.excel):
            delimiter = ","
        return Simple()

def main():
    ap = argparse.ArgumentParser(description="Clean neighborhood text (no matching)")
    ap.add_argument("--input_csv", required=True)
    ap.add_argument("--input_col", default="neighborhood", help="Column with neighborhood text")
    ap.add_argument("--out_csv", required=True)
    ap.add_argument("--encoding", default="utf-8", help="CSV read/write encoding (utf-8 or latin-1)")
    ap.add_argument("--add_norm", action="store_true", help="Also add neighborhood_clean_norm key")
    args = ap.parse_args()

    dia = sniff_dialect(args.input_csv, args.encoding)
    with open(args.input_csv, "r", encoding=args.encoding, errors="replace", newline="") as f:
        reader = csv.DictReader(f, dialect=dia)
        rows = list(reader)
        fields = reader.fieldnames or []

    if args.input_col not in fields:
        raise SystemExit(f"Column '{args.input_col}' not found. Available: {fields}")

    out_rows = []
    for r in rows:
        raw = r.get(args.input_col, "") or ""
        cleaned = preclean_neighborhood(str(raw))
        r2 = dict(r)
        r2["neighborhood_clean"] = cleaned
        if args.add_norm:
            r2["neighborhood_clean_norm"] = normalize_key(cleaned)
        out_rows.append(r2)

    out_fields = list(fields)
    for c in ["neighborhood_clean"] + (["neighborhood_clean_norm"] if args.add_norm else []):
        if c not in out_fields:
            out_fields.append(c)

    with open(args.out_csv, "w", encoding=args.encoding, errors="replace", newline="") as f:
        w = csv.DictWriter(f, fieldnames=out_fields)
        w.writeheader()
        for r in out_rows:
            w.writerow(r)

if __name__ == "__main__":
    main()
