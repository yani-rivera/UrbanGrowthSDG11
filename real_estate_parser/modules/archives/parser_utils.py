
import re

def normalize_price(text):
    # More flexible price matcher for OCR-like $.700, $2,600.00, $325/$425
    price_patterns = [
        r'\$\.\d{1,3}(?:,\d{3})*(?:\.\d+)?',  # $.700.00, $.2,600.00
        r'\$\s?\d{1,3}(?:,\d{3})*(?:\.\d+)?', # $2,600.00
        r'\$\d+/\$\d+',                         # $325/$425
        r'L\.\s?\d{1,3}(?:,\d{3})*(?:\.\d+)?',# L. 1,700,000
        r'Lps?\.\s?\d{1,3}(?:,\d{3})*(?:\.\d+)?' # Lps. 8500
    ]

    found = []
    for pattern in price_patterns:
        matches = re.findall(pattern, text)
        found.extend(matches)

    cleaned = []
    for p in found:
        nums = re.findall(r'[\d,]+(?:\.\d+)?', p)
        for n in nums:
            try:
                cleaned.append(float(n.replace(',', '')))
            except:
                continue

    return max(cleaned) if cleaned else None


def extract_price(text):
    # More flexible price matcher for OCR-like $.700, $2,600.00, $325/$425
    price_patterns = [
        r'\$\.\d{1,3}(?:,\d{3})*(?:\.\d+)?',       # $.700.00, $.2,600.00
        r'\$\s?\d{1,3}(?:,\d{3})*(?:\.\d+)?',      # $2,600.00
        r'\$\d+/\$\d+',                            # $325/$425
        r'L\.\s?\d{1,3}(?:,\d{3})*(?:\.\d+)?',     # L. 1,700,000
        r'Lps?\.\s?\d{1,3}(?:,\d{3})*(?:\.\d+)?'   # Lps. 8500
    ]

    found = []
    for pattern in price_patterns:
        matches = re.findall(pattern, text)
        found.extend(matches)

    return found  # Now returns the matched raw strings




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

def detect_transaction(header, transaction_keywords):
    header_upper = header.upper()
    for tx_type, keywords in transaction_keywords.items():
        for kw in keywords:
            if kw in header_upper:
                return tx_type
    return None

def clean_listing_line(line):
    return line.strip().lstrip("*-").strip()

def extract_property_type(text, config):
    text_lower = text.lower()
    for prop_type, keywords in config.get("type_keywords", {}).items():
        if any(keyword in text_lower for keyword in keywords):
            return prop_type
    return "other"
