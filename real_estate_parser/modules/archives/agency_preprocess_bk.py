# modules/agency_preprocess.py
import re
import unicodedata

MULTI_PRICE = re.compile(
    r'(\$\s?\d[\d.,]*)(?:\s*(?:/|y|e|,)\s*)(\$\s?\d[\d.,]*)',
    re.IGNORECASE
)
BEDS_ANY = re.compile(
    r'\b(\d+)\s*(?:hab\.?|habitaciones|cuartos|dorms?)\b',
    re.IGNORECASE
)
PRICES_ANY = re.compile(
    r'(\$\s?\d[\d.,]*)',
    re.IGNORECASE
)

def _basic_normalize(s: str) -> str:
    s = s.strip()
    s = re.sub(r'^[\*\>\u2022]+\s*', '', s)           # bullets
    s = re.sub(r'\s+', ' ', s)                        # collapse spaces
    s = unicodedata.normalize("NFC", s)
    s = re.sub(r'(Lps\.?|L\.|\$)(\d)', r'\1 \2', s, flags=re.IGNORECASE)  # ensure space after currency
    s = re.sub(r'\b(mts?2|mt2|m2)\b', 'm²', s, flags=re.IGNORECASE)
    s = re.sub(r'\b(vr2|vrs2|v2)\b', 'vrs²', s, flags=re.IGNORECASE)
    s = re.sub(r'\bcolonia\b', 'col.', s, flags=re.IGNORECASE)
    s = re.sub(r'\bcol\b', 'col.', s, flags=re.IGNORECASE)
    s = re.sub(r'\bresidencial\b', 'res.', s, flags=re.IGNORECASE)
    return s

def preprocess_generic(text: str) -> str:
    return _basic_normalize(text).lower()

def preprocess_serpecal(text: str) -> str:
    s = _basic_normalize(text)
    s = s.replace('Vr²','vrs²').replace('Vr2','vrs²').replace('Vrs2','vrs²').replace('Vrs','vrs')
    return s.lower()

def preprocess_perpi(text: str) -> str:
    return _basic_normalize(text).lower()

def preprocess(text: str, agency: str) -> str:
    ag = (agency or "").strip().upper()
    if ag == "SERPECAL":
        return preprocess_serpecal(text)
    if ag == "PERPI":
        return preprocess_perpi(text)
    return preprocess_generic(text)

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
