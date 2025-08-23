
# modules/qa_utils.py
import re

MULTI_PRICE = re.compile(r'(\$\s?\d[\d,\.]*)(?:\s*(?:/|y|e|,)\s*)(\$\s?\d[\d,\.]*)', re.IGNORECASE)
MULTI_BEDS  = re.compile(r'\b(\d+)\s*(?:hab\.?|habitaciones|cuartos|dorms?)\b[^$]*?(?:/|y|e|,)\s*(\d+)\s*(?:hab\.?|habitaciones|cuartos|dorms?)', re.IGNORECASE)
BEDS_ANY    = re.compile(r'\b(\d+)\s*(?:hab\.?|habitaciones|cuartos|dorms?)\b', re.IGNORECASE)
PRICES_ANY  = re.compile(r'(\$\s?\d[\d,\.]*)', re.IGNORECASE)

def is_multi_offer(raw_text: str) -> dict:
    """
    Detects multiple prices and/or multiple bedroom counts in one line.
    Returns a dict with flags and the extracted numbers (for your reference).
    """
    text = raw_text or ""
    prices = PRICES_ANY.findall(text)
    beds   = [int(b) for b in BEDS_ANY.findall(text)]
    has_multi_price = bool(MULTI_PRICE.search(text)) or (len(prices) >= 2)
    has_multi_beds  = bool(MULTI_BEDS.search(text)) or (len(beds)   >= 2)
    return {
        "multi_price": has_multi_price,
        "multi_bedrooms": has_multi_beds,
        "prices_found": [p.strip() for p in prices],
        "bedrooms_found": beds
    }

def missing_fields(formatted_row: dict) -> list:
    """
    Accepts the already formatted row (with final CSV headers).
    Returns the list of final headers that are empty and should be reviewed.
    """
    check = ["Price","Currency","Bedrooms","Bathrooms","AT","Area","Transaction","Type","Neighborhood"]
    return [k for k in check if not str(formatted_row.get(k, "")).strip()]
