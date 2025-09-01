
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
    currency_aliases = config.get("currency_aliases", {})

    price_patterns = [
        r'(\$[\d,.]+)',         # $2,600.00
        r'(Lps?\.?\s?[\d,.]+)', # Lps. 8500
        r'(L\.?\s?[\d,.]+)',    # L. 8500
    ]

    found = []
    for pattern in price_patterns:
        found.extend(re.findall(pattern, text))

    for p in found:
        for symbol, currency in currency_aliases.items():
            if p.startswith(symbol):
                digits = re.findall(r'[\d,.]+', p)
                if digits:
                    try:
                        return float(digits[0].replace(',', '')), currency
                    except:
                        continue

    return "", ""
