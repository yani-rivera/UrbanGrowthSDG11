# modules/agency_preprocess.py
import re
import unicodedata

# --- OCR sanitation ---
def ocr_sanitize(text: str) -> str:
    if not text:
        return ""

    s = str(text)

    # Unicode normalize (fixes many accent/spacing artifacts)
    # NFKC also resolves ligatures and compatibility forms
    s = unicodedata.normalize("NFKC", s)

    # Common OCR garbage & mis-encoded sequences seen in your scans
    # (extend this table as you encounter new patterns)
    FIXES = [
        # Broken currency spacing / stray dots
        (r'\$\.', '$ '),                  # "$.700,000" -> "$ 700,000"
        (r'(Lps?|L)\.(\d)', r'\1. \2'),   # "Lps.3000"  -> "Lps. 3000"
        (r'US\$(\d)', r'US$ \1'),

        # Smart quotes / bullets / weird punctuation
        ('\u2018', "'"), ('\u2019', "'"),
        ('\u201C', '"'), ('\u201D', '"'),
        ('\u2022', '*'),                  # bullet to "*"
        ('\u00AD', ''),                   # soft hyphen

        # Mis-decoded accent triplets often seen after OCR/export
        ('bafios', 'baños'),
        ('banos', 'baños'),
        ('baf̃os', 'baños'),
        ('bano', 'baño'),
        ('anos', 'años'),
        ('jard\\u221an', 'jardín'),       # "jard√≠n" etc → "jardín"
        ('jard\xbf\xaan', 'jardín'),

        # General accent repairs (broad strokes)
        ('Monse\\xF1or', 'Monseñor'),
        ('Monsenor', 'Monseñor'),
        ('An\\xEDllo', 'Anillo'),

        # Frequently mangled tokens
        ('Residencial', 'Res.'),
        ('Colonia', 'Col.'),
        ('Col ', 'Col. '),
        ('Urb ', 'Urb. '),
    ]

    for a, b in FIXES:
        s = re.sub(a, b, s, flags=re.IGNORECASE) if len(a) > 1 and a.startswith(r'\b') is False else s.replace(a, b)

    # Normalize area units (m2→m², mts2→m²; vr2/vrs2→vrs²)
    s = re.sub(r'\b(mts?2|mt2|m2)\b', 'm²', s, flags=re.IGNORECASE)
    s = re.sub(r'\b(vr2|vrs2|v2)\b', 'vrs²', s, flags=re.IGNORECASE)

    # Ensure a space after currency markers for price regex
    s = re.sub(r'(\$)(\d)', r'\1 \2', s)
    s = re.sub(r'(Lps?\.?|US\$)(\s*)(\d)', r'\1 \3', s, flags=re.IGNORECASE)

    # Hyphenation line‑break fix (if any multi-line text slips through)
    s = re.sub(r'-\s*\n\s*', '', s)

    # Collapse weird spacing
    s = re.sub(r'\s+', ' ', s).strip()

    
    return s

# --- Your existing basic normalizer; now calls ocr_sanitize first ---
def _basic_normalize(s: str) -> str:
    s = ocr_sanitize(s)

    # remove leading bullets/markers
    s = re.sub(r'^[\*\>]+\s*', '', s)

    # Unicode NFC (after edits)
    s = unicodedata.normalize("NFC", s)

    # Standardize tokens that help extractors
    s = re.sub(r'(Lps\.?|L\.|\$)(\d)', r'\1 \2', s, flags=re.IGNORECASE)  # backup space enforcement
    s = re.sub(r'\bcolonia\b', 'col.', s, flags=re.IGNORECASE)
    s = re.sub(r'\bcol\b', 'col.', s, flags=re.IGNORECASE)
    s = re.sub(r'\bresidencial\b', 'res.', s, flags=re.IGNORECASE)

    return s.strip()

def preprocess_generic(text: str) -> str:
    return _basic_normalize(text).lower()

def preprocess_serpecal(text: str) -> str:
    s = _basic_normalize(text)
    # SERPECAL quirks: Vr²/Vrs2 capitalization
    s = s.replace('Vr²','vrs²').replace('Vr2','vrs²').replace('Vrs2','vrs²').replace('Vrs','vrs')
    return s.lower()

def preprocess_perpi(text: str) -> str:
    return _basic_normalize(text).lower()

# def preprocess(text: str, agency: str) -> str:
#     ag = (agency or "").strip().upper()
#     if ag == "SERPECAL":
#         return preprocess_serpecal(text)
#     if ag == "PERPI":
#         return preprocess_perpi(text)
#     return preprocess_generic(text)

MULTI_PRICE = re.compile(
    r'(\$\s?\d[\d.,]*)(?:\s*(?:/|y|e|,)\s*)(\$\s?\d[\d.,]*)',
    re.IGNORECASE
)

def detect_multi_offer(text: str) -> dict:
    """
    Non-invasive detector: finds multiple prices and/or bedrooms in one line.
    Does NOT split; returns metadata you can store in parsed row.
    """
    prices = PRICES_ANY.findall(text)              # ['$ 450', '$ 500']
    beds   = [int(b) for b in BEDS_ANY.findall(text)]  # [2, 3]
    return {
        "is_multi": (len(prices) >= 2) or (len(beds) >= 2) or bool(MULTI_PRICE.search(text)),
        "prices_found": [p.strip() for p in prices],
        "bedrooms_found": beds
    }

#####

# modules/agency_preprocess.py

def normalize_ocr_text(s: str) -> str:
    if not s:
        return ""
    s = unicodedata.normalize("NFKC", s)
    s = re.sub(r'\$\.(\d)', r'$\1', s)           # "$.700,000" -> "$700,000"
    s = re.sub(r'(Lps?|L)\.(\d)', r'\1. \2', s)  # "Lps.3000" -> "Lps. 3000"
    s = re.sub(r'\s+', ' ', s).strip()
    return s


def preprocess(text: str, agency: str) -> str:
    """
    Generic OCR cleanup; you can branch on agency inside if needed.
    Keep this as the single function `record_parser` calls.
    """
    s = normalize_ocr_text(text)
    ag = (agency or "").upper()
    if ag == "SERPECAL":
        # Any extra SERPECAL-specific tweaks live here
        s = s.replace("Vr2", "vrs²").replace("Vrs2", "vrs²")
    return s

# --- Back‑compat shim (so old imports don't break) ---
def serpecal_preprocess(text: str) -> str:
    """Old callers used this name; delegate to the generic one."""
    return preprocess(text, "SERPECAL")
