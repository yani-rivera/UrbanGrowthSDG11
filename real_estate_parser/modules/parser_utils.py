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

    # Fix cases like "$.1000", "$ . 1000" to "$ 1000"
    text = re.sub(r'(\$\s*\.\s*)(\d)', r'$ \2', text)
    text = re.sub(r'(\$\s*\.\s*)(\d)', r'$ \2', text)  # repeat for extra safety

    aliases = config.get("currency_aliases", {})
    norm_aliases = {k.upper(): v for k, v in aliases.items()}

    patterns = [
        r'(?P<symbol>\$)\s*(?P<amount>[\d.,]+)',
        r'(?P<symbol>Lps?\.?)\s*(?P<amount>[\d.,]+)',
        r'(?P<symbol>L\.?)\s*(?P<amount>[\d.,]+)'
    ]

    best_amount, best_currency = None, ""
    for pat in patterns:
        for m in re.finditer(pat, text, re.IGNORECASE):
            start, end = m.start(), m.end()
            window = text[start:end+16] if end+16 <= len(text) else text[start:]
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

    # sensible defaults on top of config
    ac_units = set([u.lower() for u in aliases.get("ac", [])] + ["m²","m2","mt2","mts2","mts²","metros","metros2","metros²"])
    at_units = set([u.lower() for u in aliases.get("at", [])] + ["vrs²","vrs2","vr2","vr²","vrs","vara","varas","v²","vr"])
    mz_units = set([u.lower() for u in aliases.get("mz", [])] + ["manzana","manzanas","mz"])

    # helper: avoid matching prices (look back for $ or L)
    def looks_like_price(s, start):
        return start >= 1 and s[start-1] in "$L"

    # m² / construction
    for unit in ac_units:
        m = re.search(rf'(\d+(?:[.,]\d+)?)\s*{re.escape(unit)}\b', text, flags=re.IGNORECASE)
        if m and not looks_like_price(text, m.start(1)):
            try:
                area_m2 = float(m.group(1).replace(',', '.')); break
            except: pass

    # vrs² / terrain
    for unit in at_units:
        m = re.search(rf'(\d+(?:[.,]\d+)?)\s*{re.escape(unit)}\b', text, flags=re.IGNORECASE)
        if m and not looks_like_price(text, m.start(1)):
            try:
                area_v2 = float(m.group(1).replace(',', '.')); break
            except: pass

    # manzanas → vrs² (1 mz = 10,000 v²)
    if area_v2 == "":
        for unit in mz_units:
            m = re.search(rf'(\d+(?:[.,]\d+)?)\s*{re.escape(unit)}\b', text, flags=re.IGNORECASE)
            if m and not looks_like_price(text, m.start(1)):
                try:
                    mz = float(m.group(1).replace(',', '.'))
                    area_v2 = mz * 10000.0
                    break
                except: pass

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

def detect_section_context(line: str, config: dict):
    """
    Returns (transaction, type, category) if the line looks like a section header,
    else (None, None, None).
    """
    t = (line or "").strip().upper()
    for entry in (config or {}).get("section_headers", []):
        pat = (entry.get("pattern") or "").strip().upper()
        if pat and pat in t:
            #print(f"[MATCH FOUND] Pattern: {pat} in line: {t}")
            #print(f"Returning: transaction={entry.get('transaction')}, type={entry.get('type')}, category={entry.get('category')}")
            return (
                entry.get("transaction") or None,
                entry.get("type") or None,
                entry.get("category") or pat
            )
    
    # Fallback when nothing matches
    return (None, None, None)


def extract_transaction(text, config):
    """
    Try to detect transaction type (rent/sale).
    For some agencies this comes from the header, not the listing itself.
    """
    tx_keywords = config.get("transaction_keywords", {})
    for k, v in tx_keywords.items():
        if k.lower() in text.lower():
            return v
    return ""
