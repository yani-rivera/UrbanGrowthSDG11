import re
from scripts.parser_utils import extract_price

def extract_number(text, keywords):
    for kw in keywords:
        pattern = r"(\d{1,2})\s*%s" % re.escape(kw)
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return int(match.group(1))
    return None

def extract_area(text, area_aliases):
    ac = at = None
    for unit in area_aliases.get("ac", []):
        pattern = r"\b(\d{1,5})\s*%s\b" % re.escape(unit)
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            ac = int(match.group(1))
            break
    for unit in area_aliases.get("at", []):
        pattern = r"\b(\d{1,5})\s*%s\b" % re.escape(unit)
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            at = int(match.group(1))
            break
    return ac, at

def extract_property_type(text, type_keywords):
    for k, variants in type_keywords.items():
        if any(v in text.lower() for v in variants):
            return k
    return None



def parse_record(text, config, agency=None, date=None, listing_no=None):
    row = {
        "agency": agency or "",
        "date": date or "",
        "listing_no": listing_no or "",
        "description": text.strip(),
        "property_type": "",
        "bedrooms": "",
        "bathrooms": "",
        "area_construction": "",
        "area_terrain": "",
        "price": "",
        "currency": ""
    }

    # Bedrooms
    m_bed = re.search(r'(\d+)\s*(?:hab\.|habitaciones?)\b', text, re.IGNORECASE)
    if m_bed:
        row["bedrooms"] = int(m_bed.group(1))

    # Bathrooms
    m_bath = re.search(r'(\d+)\s*(?:baños?|bañ\.)\b', text, re.IGNORECASE)
    if m_bath:
        row["bathrooms"] = int(m_bath.group(1))

    # Areas
    ac, at = extract_area(text, config.get("area_aliases", {}))
    row["area_construction"] = ac or ""
    row["area_terrain"] = at or ""

    # Property type
    ptype = extract_property_type(text, config.get("type_keywords", {}))
    row["property_type"] = ptype or ""

    # Price & Currency
    price, curr = extract_price(text, config.get("currency_aliases", {}))
    row["price"] = price or ""
    row["currency"] = curr or ""

    return row

