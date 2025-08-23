# Version 2.1
import re



def normalize_ocr_text(text):
    return (
        text.replace("√±", "ñ")
            .replace("ƒ±", "ñ")
            .replace("√≥", "ó")
            .replace("√", "")
            .replace("ƒ", "")
            .replace("Ã", "í")
            .replace("â", "")
            .strip()
            .lower()
    )

def extract_price(text, config):
    text = normalize_ocr_text(text)
    aliases = config.get("currency_aliases", {})
    norm_aliases = {k.upper(): v for k, v in aliases.items()}

    patterns = [
        r'(?P<symbol>\$)\s?(?P<amount>[\d.,]+)',
        r'(?P<symbol>Lps?\.?)\s?(?P<amount>[\d.,]+)',
        r'(?P<symbol>L\.?)\s?(?P<amount>[\d.,]+)'
    ]

    best_amount, best_currency = None, ""
    for pat in patterns:
        for m in re.finditer(pat, text, re.IGNORECASE):
            start, end = m.start(), m.end()
            window = text[start:end+16] if end+16 <= len(text) else text[start:]
            # Skip per‑unit: "$ 4.00 vrs²", "$10.00 vrs2", etc.
            if re.search(r'\b(vrs|vrs2|vrs²|vr²|vr2|vara|varas)\b', window):
                continue
            raw_symbol = m.group("symbol").strip().upper()
            amount_str = m.group("amount").replace(",", "")
            try:
                amt = float(amount_str)
            except ValueError:
                continue
            curr = norm_aliases.get(raw_symbol, raw_symbol)
            if best_amount is None or amt > best_amount:
                best_amount, best_currency = amt, curr
    return (best_amount if best_amount is not None else ""), (best_currency if best_amount is not None else "")



def extract_area(text, config):
    text = normalize_ocr_text(text)
    area_m2, area_v2 = "", ""
    aliases = config.get("area_aliases", {})

    for unit in aliases.get("ac", []):
        m = re.search(rf'(\d+(?:[.,]\d+)?)\s*{re.escape(unit)}\b', text)
        if m:
            try: area_m2 = float(m.group(1).replace(',', '.')); break
            except: pass

    for unit in aliases.get("at", []):
        m = re.search(rf'(\d+(?:[.,]\d+)?)\s*{re.escape(unit)}\b', text)
        if m:
            try: area_v2 = float(m.group(1).replace(',', '.')); break
            except: pass

    if area_v2 == "":
        m_mz = re.search(r'(\d+(?:[.,]\d+)?)\s*manzanas?\b', text)
        if m_mz:
            try:
                mz = float(m_mz.group(1).replace(',', '.'))
                area_v2 = mz * 10000.0  # 1 manzana = 10,000 v²
            except:
                pass
    return area_m2, area_v2


def extract_property_type(text, config):
    text = normalize_ocr_text(text)
    for prop_type, keywords in config.get("type_keywords", {}).items():
        if any(kw in text for kw in keywords):
            return prop_type
    return "other"

def detect_transaction(text, config):
    text = normalize_ocr_text(text)
    for keyword, tx_type in config.get("transaction_keywords", {}).items():
        if keyword in text:
            return tx_type
    return ""

def clean_listing_line(line):
    return re.sub(r'\s+', ' ', line).strip()

NUM_WORDS = {"uno":1,"una":1,"dos":2,"tres":3,"cuatro":4,"cinco":5,"seis":6,"siete":7,"ocho":8,"nueve":9,"diez":10}
def _word_to_int(s): return NUM_WORDS.get(s.strip().lower(), None)

def extract_bedrooms(text, config):
    text = normalize_ocr_text(text)
    for kw in config.get("bedroom_keywords", []):
        m = re.search(rf'(\d+)\s*{re.escape(kw)}\b', text)
        if m: return int(m.group(1))
    for kw in config.get("bedroom_keywords", []):
        m = re.search(rf'\b({ "|".join(NUM_WORDS.keys()) })\s*{re.escape(kw)}\b', text)
        if m:
            v = _word_to_int(m.group(1))
            if v: return v
    return ""

def extract_bathrooms(text, config):
    text = normalize_ocr_text(text)
    m = re.search(r'(\d+)\s*(?:1/2|½)\s*bañ', text)
    if m: return float(m.group(1)) + 0.5
    m = re.search(r'(\d+)\s*y\s*medio\s*bañ', text)
    if m: return float(m.group(1)) + 0.5
    for kw in config.get("bathroom_keywords", []):
        m = re.search(rf'(\d+)\s*{re.escape(kw)}\b', text)
        if m: return int(m.group(1))
    for kw in config.get("bathroom_keywords", []):
        m = re.search(rf'\b({ "|".join(NUM_WORDS.keys()) })\s*{re.escape(kw)}\b', text)
        if m:
            v = _word_to_int(m.group(1))
            if v: return v
    return ""
