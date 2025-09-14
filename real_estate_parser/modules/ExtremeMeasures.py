
import re
from typing import Iterable, List, Dict, Any, Optional

# Beds like "3 hab", "3 habitaciones", "5 bed"
BED_RX   = re.compile(r"\b(\d+)\s*(?:hab(?:itaciones)?|bed(?:rooms)?)\b", re.I)

# Baths like "2 baños", "2 ½ baños", "2.5 baños", "2 banos"
BATH_RX  = re.compile(r"\b(\d+(?:\s*[.,]?\s*½)?)\s*(?:bañ(?:os)?|banos?|bath(?:rooms)?)\b", re.I)

# Price tokens: "$ 1,300.00", "$. 650.00", "Lps. 14, 000.00", "L. 1,250,000.00"
PRICE_RX = re.compile(r"(?i)(?:\$\s*\.?|LPS?\.?|L\.)\s*[\d.,\s]+")

# --- helpers ---------------------------------------------------------------

def _half_to_float(s: str) -> float:
    s = s.strip().replace("½", ".5")
    s = re.sub(r"(\d+)\s*[,\.]?\s*5$", r"\1.5", s)
    s = re.sub(r"[^\d\.]", "", s)
    try:
        return float(s)
    except ValueError:
        return 0.0

def _parse_price(s: str):
    m = PRICE_RX.findall(s)
    if not m:
        return None, None, None
    raw = m[-1]                            # take last price on the line
    cur = "USD" if "$" in raw else "HNL"
    num = re.sub(r"[^\d.]", "", raw.replace(",", ""))
    try:
        val = float(num)
    except ValueError:
        val = None
    return cur, val, raw.strip()

def _flatten_text(raw: str) -> str:
    # reflow hard-wrapped lines into one string
    flat = re.sub(r"\s*\n\s*", " ", raw or "")
    flat = re.sub(r"\s{2,}", " ", flat)
    return flat.strip()

# Split when a price is followed by what looks like a NEW listing start (UPPER/NUM + comma)
FUSION_SPLIT_RX = re.compile(
    r"(?P<price>(?:\$\s*\.?|LPS?\.?|L\.)\s*[\d.,\s]+)\s+(?=(?:[A-ZÁÉÍÓÚÑ0-9][A-ZÁÉÍÓÚÑ0-9 .#/-]*,))",
    re.I
)

def split_fused_listings_from_raw(raw: str) -> List[str]:
    flat = _flatten_text(raw)
    parts, i = [], 0
    for m in FUSION_SPLIT_RX.finditer(flat):
        end = m.end("price")
        part = flat[i:end].strip(" ,")
        if part:
            parts.append(part)
        i = end
    tail = flat[i:].strip(" ,")
    if tail:
        parts.append(tail)
    return parts if parts else [flat]

# --- main parsing ----------------------------------------------------------

def parse_listing_line(line: str) -> Optional[Dict[str, Any]]:
    s = (line or "").strip()
    if not s or s.startswith("#"):
        return None

    parts = [p.strip() for p in s.split(",") if p.strip()]
    if not parts:
        return None

    neighborhood = parts[0]
    tail = ", ".join(parts[1:]) if len(parts) > 1 else ""

    beds  = int(BED_RX.search(tail).group(1)) if BED_RX.search(tail) else None
    baths = _half_to_float(BATH_RX.search(tail).group(1)) if BATH_RX.search(tail) else None
    currency, price, price_text = _parse_price(tail or s)

    # keep descriptive tokens that aren’t bed/bath/price
    features = [
        p for p in parts[1:]
        if not (BED_RX.search(p) or BATH_RX.search(p) or PRICE_RX.search(p))
    ]

    return {
        "neighborhood": neighborhood,
        "beds": beds,
        "baths": baths,
        "currency": currency,
        "price": price,
        "price_text": price_text,
        "features": features,
        "raw": s,
    }

def parse_agency_text(raw: str) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for piece in split_fused_listings_from_raw(raw):
        rec = parse_listing_line(piece)
        if rec:
            out.append(rec)
    return out
