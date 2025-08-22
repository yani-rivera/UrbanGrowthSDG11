import re
def extract_bedrooms(text):
    match = re.search(r'(\d+)\s*(hab\.|habitaciones|cuartos|dorm)', text, re.IGNORECASE)
    return match.group(1) if match else ""

def extract_bathrooms(text):
    match = re.search(r'(\d+)\s*(ba[ñn]os?)', text, re.IGNORECASE)
    return match.group(1) if match else ""

def extract_area(text):
    match = re.search(r'(\d+[\.,]?\d*)\s*(m2|mts2|v2|vrs2)', text, re.IGNORECASE)
    if match:
        area = match.group(1).replace(',', '.')
        return (area, 'm2' if 'm' in match.group(2).lower() else 'v2')
    return ("", "")


def normalize_price(text):
    """Extracts and normalizes price as float. Supports $, L, commas."""
    prices = re.findall(r"[$L]\s?([\d,.]+)", text)
    if not prices:
        return None
    
    def clean(p):
        return float(p.replace(",", "").replace(".00", ".0") if "." in p else p)

    # Choose highest price if multiple found
    try:
        return max(clean(p) for p in prices)
    except ValueError:
        return None

def detect_transaction(header, transaction_keywords):
    """Detects transaction type from a header line based on keywords."""
    header_upper = header.upper()
    for tx_type, keywords in transaction_keywords.items():
        for kw in keywords:
            if kw in header_upper:
                return tx_type
    return None

def detect_neighborhood(text, neighborhoods):
    # Clean to only include string-type neighborhoods
    clean_neighborhoods = [nb if isinstance(nb, str) else nb.get("name", "") for nb in neighborhoods]

    for nb in clean_neighborhoods:
        if nb and re.search(rf"\b{re.escape(nb)}\b", text, re.IGNORECASE):
            return nb
    return ""


def clean_listing_line(line):
    return line.strip().lstrip("*-").strip()
