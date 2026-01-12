# Version 2.1
import re
import unicodedata
import sys,os
from typing import Optional

#=============

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

######

from modules.price_extractor import extract_price
from modules.area_extractor import extract_area as _extract_area_new



#==================END IMPORTS

 
_BED_WORDS = r"(?:hab(?:itaciones)?|habit\.?|habs?\.?|dorm(?:itorios)?|recá?maras?|alcobas?|BEDROOMS)"

BED_RX_KV = re.compile(
    r"\b(?:beds?|bedrooms?)\s*[:=]\s*(\d{1,2})\b",
    re.IGNORECASE
)


BED_RX_EQUALS = re.compile(
    r"\b(?:beds?|bedrooms?)\s*=\s*(\d{1,2})\b",
    re.IGNORECASE
)


BED_RX_1 = re.compile(
    rf"(?:\((\d{{1,2}})\)|\b(\d{{1,2}}))\s*{_BED_WORDS}(?!\w)",
    re.IGNORECASE
)

BED_RX_2 = re.compile(r"\b(\d{1,2})\s*[Hh]\b")  # 3H, 4 h
BED_RX_WORD_FIRST = re.compile(
    rf"\b{_BED_WORDS}\s*[:\-]?\s*(\d{{1,2}})\b",
    re.IGNORECASE
)
#----------
_NUM_WORDS_0_5 = {
    "cero": "0",
    "uno": "1", "una": "1", "un": "1",
    "dos": "2",
    "tres": "3",
    "cuatro": "4",
    "cinco": "5",
}
_NUM_WORDS_RX = re.compile(r"\b(?:cero|uno|una|un|dos|tres|cuatro|cinco)\b", re.IGNORECASE)

def _normalize_small_numbers_0_5(s: str) -> str:
    # replace standalone number-words with digits; keeps accents untouched elsewhere
    return _NUM_WORDS_RX.sub(lambda m: _NUM_WORDS_0_5[m.group(0).lower()], s)

#---------


# bathrooms: decimals/½, words + shorthand B
#BATH_WORD = r"ba(?:ños|nos|ño|no)s?"
BATH_WORD = r"(?:bañ(?:o|os)|ban(?:o|os)|ba|bathrooms?)"


BATH_RX_WORD_NUM = re.compile(
    rf"\b{BATH_WORD}\s*(\d{{1,2}}(?:[.,]\d)?)\b",
    re.I
)

BATH_RX_NUM_WORD = re.compile(
    rf"\b(\d{{1,2}}(?:[.,]\d)?)\s*{BATH_WORD}\b",
    re.I
)


BATH_RX = re.compile(rf"\b(\d{{1,2}}(?:[.,]\d)?)\s*{BATH_WORD}", re.I)


BATH_RX_MEDIO = re.compile(
    rf"\b(\d{{1,2}})\s*y\s*medio(?:\s+{BATH_WORD})?\b", re.I)

BATH_RX_B = re.compile(
    r"\b(\d{1,2}(?:[.,]\d)?|\d\s*1/2|½)\s*[Bb]\b", re.I)

# optional "3/2" shorthand: assume beds/baths if enabled
SLASH_RX = re.compile(r"\b(\d{1,2})\s*/\s*(\d{1,2}(?:[.,]\d)?|\d\s*1/2|½)\b")

# inverse baths

BATH_RX_WORD_FIRST = re.compile(
    rf"\b{BATH_WORD}\s*[:\-]?\s*(\d{{1,2}}(?:[.,]\d)?|\d\s*1/2|½)\b",
    re.IGNORECASE
)


####------Price regex
_UNIT_PRICE_RE = re.compile(
    r'(US\$|\$|L\.?)\s?\d+(?:[\.,]\d+)?\s?(?:x\s*)?(?:vrs²|vrs2|vr2|m²|m2|mt2)\b',
    re.IGNORECASE
)
_CURR_TIGHT_RE = re.compile(r'(US\$|\$|L\.?)(\d)')   # "US$45000" -> "US$ 45000"
_SPACE_COLLAPSE_RE = re.compile(r'\s+')

###########

AREA_RX = re.compile(
    r'\b(\d{1,4}(?:[.,]\d{3})*(?:[.,]\d{1,2})?)\s*'
    r'(m2|m²|mt2|mts2|mts|area_m2|vrs2|vrs²|vrs|vr2|vr)\b',
    re.IGNORECASE,
)

# PRICE must have a currency; take the LAST one on the line
PRICE_RX = re.compile(
    r'(US\$|\$|LPS?\.?|L\.|USD|HNL)\s*'
    r'(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})?)',
    re.IGNORECASE,
)



def normalize_currency_spacing(text: str) -> str:
    """Ensure a space between currency token and digits."""
    if text is None:
        return ""
    s = str(text)
    return _CURR_TIGHT_RE.sub(r'\1 \2', s)
    #return text

def strip_per_unit_prices(text: str) -> str:
    """Remove per-unit amounts like 'US$ 4.00 vrs²' or '$ 10 m2'; keep totals."""
    if text is None:
        return ""
    s = str(text)
    s = _UNIT_PRICE_RE.sub('', s)
    return _SPACE_COLLAPSE_RE.sub(' ', s).strip()

def clean_text_for_price(text: str) -> str:
    """Convenience pipeline before price extraction."""
    return normalize_currency_spacing(strip_per_unit_prices(text))


def normalize_ocr_text(text):
    """Robust text normalizer for OCR output; accepts str/list/tuple/dict/None."""
    if text is None:
        s = ""
    elif isinstance(text, (list, tuple, set)):
        s = " ".join(map(str, text))
    elif isinstance(text, dict):
        s = " ".join(map(str, text.values()))
    else:
        s = str(text)

    # Unicode normalize
    s = unicodedata.normalize("NFKC", s)

    # Common mis-encodings / artifacts
    fixes = [
        ("√±", "ñ"), ("√ë", "é"), ("√≥", "ó"), ("√∫", "ú"), ("√°", "á"),
        ("bafios", "baños"), ("banos", "baños"), ("baf̃os", "baños"), ("bano", "baño"),
        ("\\u00ad", ""),  # soft hyphen if it slipped in
    ]
    for a, b in fixes:
        s = s.replace(a, b)

    # Currency spacing
    s = re.sub(r"\$\.(\d)", r"$ \1", s)                  # "$.700" -> "$ 700"
    s = re.sub(r"(Lps?|L)\.(\d)", r"\1. \2", s, flags=re.I)
    s = re.sub(r"US\$(\d)", r"US$ \1", s, flags=re.I)
    s = re.sub(r"(\$)(\d)", r"\1 \2", s)
    s = re.sub(r"(Lps?\.?|US\$)(\s*)(\d)", r"\1 \3", s, flags=re.I)

    # Area units
    s = re.sub(r"\b(mts?2|mt2|m2)\b", "m²", s, flags=re.I)
    s = re.sub(r"\b(vr2|vrs2|v2)\b", "vrs²", s, flags=re.I)

    # Collapse spaces
    s = re.sub(r"\s+", " ", s).strip()
    return s


def extract_area(text: str, config: dict):
    """Façade: keep old import path working, call the new module."""
    return _extract_area_new(text, config)


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

# def _word_to_int(s): return NUM_WORDS.get(s.strip().lower(), None)


""" def extract_bedrooms(text: str, config: dict | None = None):
    # CHANGED: normalize only 0–5 words; do NOT strip accents
    t = _normalize_small_numbers_0_5(text or "")

    # 1) explicit words
    m = BED_RX_1.search(t)
    if m:
        n_str = m.group(1) or m.group(2)
        if n_str is None:
            return None
        n = int(n_str)
        return n if 0 <= n <= 5 else None

    # 2) shorthand "3H"
    m = BED_RX_2.search(t)
    if m:
        n = int(m.group(1))
        return n if 0 <= n <= 5 else None

    # 3) word-first "Dormitorios 3"
    if not config or config.get("enable_word_first_bedbath", False):
        m = BED_RX_WORD_FIRST.search(t)
        if m:
            n = int(m.group(1))
            return n if 0 <= n <= 5 else None

    #return None


    # 4) "3/2" pattern (config-gated; on by default)
    allow_slash = True if not config else bool(config.get("allow_slash_bed_bath", True))
    if allow_slash:
        m = SLASH_RX.search(t)
        if m:
            return int(m.group(1))
    return None
 """


def extract_bedrooms(text: str, config: dict | None = None):
    # CHANGED: normalize only 0–5 words; do NOT strip accents
    t = _normalize_small_numbers_0_5(text or "")

    # 0) explicit key=value: beds=4, bedrooms=3
    m = BED_RX_EQUALS.search(t)
    if m:
        n = int(m.group(1))
        return n if 0 <= n <= 5 else None

    # 0) explicit key:value or key=value: beds: 4; bedrooms=3
    m = BED_RX_KV.search(t)
    if m:
        n = int(m.group(1))
        return n if 0 <= n <= 5 else None



    # 1) explicit words: "(3) hab", "3 dormitorios"
    m = BED_RX_1.search(t)
    if m:
        n_str = m.group(1) or m.group(2)
        if n_str is None:
            return None
        n = int(n_str)
        return n if 0 <= n <= 5 else None

    # 2) shorthand "3H"
    m = BED_RX_2.search(t)
    if m:
        n = int(m.group(1))
        return n if 0 <= n <= 5 else None

    # 3) word-first "Dormitorios 3"
    if not config or config.get("enable_word_first_bedbath", False):
        m = BED_RX_WORD_FIRST.search(t)
        if m:
            n = int(m.group(1))
            return n if 0 <= n <= 5 else None

    # 4) "3/2" pattern (config-gated; on by default)
    allow_slash = True if not config else bool(config.get("allow_slash_bed_bath", True))
    if allow_slash:
        m = SLASH_RX.search(t)
        if m:
            return int(m.group(1))

    return None



def extract_bathrooms(text: str, config: dict | None = None) -> Optional[float]:
    cfg = config or {}
    baths: Optional[float] = None
    half_already_accounted = False

    def _to_float(s: str) -> Optional[float]:
        try:
            return float(s.replace(",", "."))
        except Exception:
            return None

    # --------------------------------------------------
    # 0) Direct numeric + keyword (agency style)
    #    e.g. "4.5 BATHROOMS"
    # --------------------------------------------------
    m = BATH_RX_NUM_WORD.search(text)
    if m:
        v = _to_float(m.group(1))
        if v is not None and v <= 10:
            return v

    # 1) Slash shorthand beds/baths (3/2 or 3-2)
    # Slash shorthand beds/baths (3/2 or 3-2)
    # Slash shorthand beds/baths (3/2 or 3-2)
    # Slash shorthand beds/baths (3/2 or 3-2)
    if bool(cfg.get("allow_slash_bed_bath", True)):
        m = re.search(r"\b(\d+(?:[.,]\d+)?)\s*[/\-]\s*(\d+(?:[.,]\d+)?)\b", text)
        if m:
        # ---- anti-price guards (tiny, context-only) ----
            aliases = list((cfg or {}).get("currency_aliases", {}).keys())
            if aliases:
                # any alias anywhere before the slash => very likely a price range
                alias_rx = re.compile("|".join(re.escape(a) for a in sorted(aliases, key=len, reverse=True)), re.I)
                if alias_rx.search(text[:m.start()]):          # currency before match
                    m = None
                    if m:
                    # if bathrooms token is followed by ',' or '.' => it's a thousands continuation
                        next_char = text[m.end(2):m.end(2)+1]
                        if next_char in {",", "."}:
                            m = None
        if m:
            # if the immediate tail looks like thousands ('000' soon after), drop it
            tail = text[m.end(2):m.end(2)+6]
            raw2 = text[m.start(2):m.end(2)]
            if ("000" in tail) and ("," in raw2 or "." in raw2):
                m = None
        # -----------------------------------------------

        if m:
            v = _to_float(m.group(2))
            if v is not None:
                if v > 10:                 # unrealistic bathrooms
                    v = None
                if v is not None:
                    baths = v  # don't return yet; half-bath may add 0.5 later


                       


    # Helper to build config keyword alternation
    def _kw_alt_from_cfg() -> Optional[str]:
        kws = cfg.get("bathroom_keywords")
        if isinstance(kws, list) and kws:
            safe = [re.escape(str(k).strip()) for k in kws if str(k).strip()]
            if safe:
                return "(?:" + "|".join(safe) + ")"
        return None

    kw_alt = _kw_alt_from_cfg()

    # 2) "X y medio <keyword>" (config-driven)
    if kw_alt and half_already_accounted is False:
        m = re.search(rf"\b(\d+)\s+y\s+medio(?:\s+{kw_alt})?\b", text, flags=re.IGNORECASE)
        if m:
            base = _to_float(m.group(1))
            if base is not None:
                baths = (base + 0.5)
                half_already_accounted = True
#==========inverse baths
    if baths is None:                     # after main/y-medio/short failed
        m = BATH_RX_WORD_FIRST.search(text)
        if m:
            grp = m.group(1).replace("½", "0.5").replace(" ", "")
            grp = grp.replace(",", ".").replace("1/2", "0.5")
            v = _to_float(grp)
            if v is not None:
                baths = v


    # 3) "X <keyword>" (config-driven)
    if kw_alt and baths is None:
        m = re.search(rf"\b(\d+(?:[.,]\d+)?)\s*{kw_alt}\b", text, flags=re.IGNORECASE)
        if m:
            v = _to_float(m.group(1))
            if v is not None:
                baths = v

    # 3b) Built-in fallbacks if config not provided
    if baths is None:
        # "X baños y medio" (builtin)
        m = re.search(r"\b(\d+)\s+y\s+medio(?:\s+ba(?:ños?|nos?)|\s+ba\.?)?\b", text, flags=re.IGNORECASE)
        if m:
            base = _to_float(m.group(1))
            if base is not None:
                baths = (base + 0.5)
                half_already_accounted = True

    if baths is None:
        # "X baños" (builtin)
        m = re.search(r"\b(\d+(?:[.,]\d+)?)\s*ba(?:ños?|nos?)\b|\b(\d+(?:[.,]\d+)?)\s*ba\.\b", text, flags=re.IGNORECASE)
        if m:
            grp = m.group(1) or m.group(2)
            v = _to_float(grp)
            if v is not None:
                baths = v

    # 4) Ensuite inference (only if no numeric result yet)
    if baths is None and cfg.get("bathroom_infer_from_bedrooms", True) and cfg.get("hint_bedrooms"):
        # accept either key name from config
        markers = cfg.get("bathroom_ensuite_markers") or cfg.get("bathroom_en_suite_keywords")
        if isinstance(markers, list) and markers:
            use_regex = bool(cfg.get("bathroom_ensuite_regex", False))

            matched = False
            if use_regex:
                for pat in markers:
                    try:
                        if re.search(pat, text, flags=re.IGNORECASE):
                            matched = True
                            break
                    except re.error:
                        continue
            else:
                # accent-insensitive substring
                def _fold(s: str) -> str:
                    return ''.join(ch for ch in unicodedata.normalize('NFKD', s.lower())
                                   if not unicodedata.combining(ch))
                low = _fold(text)
                for mkr in markers:
                    if isinstance(mkr, str) and _fold(mkr) in low:
                        matched = True
                        break
            if matched:
                try:
                    baths = float(cfg.get("hint_bedrooms"))
                except Exception:
                    pass  # leave None if hint is not numeric

    # 5) Half-bath tolerant add-on (only add if not already accounted)
    half_present = any(re.search(p, text, flags=re.IGNORECASE) for p in [
        r"\bmedio\s+ba[^\s,.;:]*",        # medio baño / medio bano / medio bañod...
        r"\bba[^\s,.;:]*\s+y\s+medio\b",  # baño y medio (in case not caught earlier)
        r"(?:½|1/2)\s*ba",                # ½ baño / 1/2 baño
    ])
    if half_present and not half_already_accounted:
        baths = (baths if baths is not None else 0.0) + 0.5

    return baths



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
