# currency_utils.py
# Version 1.0

import re
from typing import Dict, Optional, Tuple
import json
from pathlib import Path


# =========================================================
# GLOBAL PRICE / CURRENCY CONFIG
# =========================================================

def load_price_currency_config():

    config_path = (
        Path(__file__).resolve().parent.parent
        / "config"
        / "price_semantic_config.json"
    )

    with open(config_path, "r", encoding="utf-8-sig") as f:

        return json.load(f)


GLOBAL_PRICE_CONFIG = load_price_currency_config()

def merge_currency_configs(
    agency_config: dict | None = None
):

    merged = dict(GLOBAL_PRICE_CONFIG)

    if not agency_config:
        return merged

    # -----------------------------------------
    # currency aliases
    # -----------------------------------------

    merged_aliases = {
        **GLOBAL_PRICE_CONFIG.get(
            "currency_aliases",
            {}
        ),
        **agency_config.get(
            "currency_aliases",
            {}
        )
    }

    merged["currency_aliases"] = merged_aliases

    # -----------------------------------------
    # magnitude aliases
    # -----------------------------------------

    merged_magnitudes = {
        **GLOBAL_PRICE_CONFIG.get(
            "price_magnitude_aliases",
            {}
        ),
        **agency_config.get(
            "price_magnitude_aliases",
            {}
        )
    }

    merged["price_magnitude_aliases"] = merged_magnitudes

    return merged
# =========================================================
# REGEX BUILDERS
# =========================================================

def compile_currency_regex(
    alias_map: dict
):
    """
    Build compiled currency regex and
    identify prefix-style aliases.
    """

    if not alias_map:
        return re.compile(r"a^"), []

    aliases = list(alias_map.keys())

    escaped = []

    prefix_like = []

    for alias in aliases:

        alias = str(alias)

        escaped.append(re.escape(alias))

        # heuristic:
        # aliases ending in symbol/punctuation
        # usually behave as prefixes

        if re.search(r"[$€£¥.]$", alias):
            prefix_like.append(alias)

    pattern = (
        "(?:"
        + "|".join(
            sorted(
                escaped,
                key=len,
                reverse=True
            )
        )
        + ")"
    )

    return (
        re.compile(pattern, re.IGNORECASE),
        prefix_like
    )


def build_currency_regex(config: dict) -> str:
    """
    Build dynamic currency token regex from config aliases.

    Example config:

    "currency_aliases": {
        "$": "USD",
        "US$": "USD",
        "L.": "HNL",
        "€": "EUR"
    }
    """

    config = merge_currency_configs(config)

    aliases = config.get(
        "currency_aliases",
        {}
    )

    if not aliases:
        return r"(?:US\$|\$|L\.?|USD|HNL)"

    tokens = []

    for alias in aliases.keys():

        alias = str(alias).strip()

        if not alias:
            continue

        tokens.append(re.escape(alias))

    # longest first avoids partial collisions
    tokens = sorted(set(tokens), key=len, reverse=True)

    return r"(?:%s)" % "|".join(tokens)


def build_price_regex(config: dict):
    """
    Build price regex dynamically from config currencies.
    Supports:

    USD 45,000
    $45,000
    45,000 USD
    45,000€
    """

    curr = build_currency_regex(config)

    number = (
        r'(\d{1,3}'
        r'(?:[.,]\d{3})*'
        r'(?:[.,]\d{1,2})?)'
    )

    pattern = (
        rf'({curr})\s*{number}'
        rf'|{number}\s*({curr})'
    )

    return re.compile(pattern, re.IGNORECASE)


def build_currency_spacing_regex(config: dict):
    """
    Regex for fixing:
    US$45000 -> US$ 45000
    €45000   -> € 45000
    """

    curr = build_currency_regex(config)

    return re.compile(
        rf'({curr})(\d)',
        re.IGNORECASE
    )


def build_unit_price_regex(config: dict):
    """
    Remove unit prices like:

    US$ 4.00 vrs²
    € 100 m2
    """

    curr = build_currency_regex(config)

    return re.compile(
        rf'({curr})\s?'
        r'\d+(?:[\.,]\d+)?\s?'
        r'(?:x\s*)?'
        r'(?:vrs²|vrs2|vr2|m²|m2|mt2)\b',
        re.IGNORECASE
    )


# =========================================================
# NORMALIZATION
# =========================================================

def normalize_currency_token(
    token: str,
    config: dict
) -> Optional[str]:
    """
    Convert aliases to canonical currency.

    "$"   -> USD
    "L."  -> HNL
    "€"   -> EUR
    """

    if token is None:
        return None

    aliases = config.get("currency_aliases", {})

    cleaned = str(token).strip()

    for alias, canonical in aliases.items():

        if cleaned.lower() == str(alias).strip().lower():
            return canonical

    return cleaned.upper()


def normalize_currency_spacing(
    text: str,
    config: dict
) -> str:
    """
    Ensure spacing between currency token and number.

    US$45000 -> US$ 45000
    €50000   -> € 50000
    """

    if text is None:
        return ""

    rx = build_currency_spacing_regex(config)

    return rx.sub(r'\1 \2', str(text))


# =========================================================
# CLEANING
# =========================================================

def strip_per_unit_prices(
    text: str,
    config: dict
) -> str:
    """
    Remove unit prices while preserving total price.

    Removes:
    US$ 5 vrs²
    € 100 m2
    """

    if text is None:
        return ""

    rx = build_unit_price_regex(config)

    s = rx.sub('', str(text))

    s = re.sub(r'\s+', ' ', s)

    return s.strip()


def clean_text_for_price(
    text: str,
    config: dict
) -> str:
    """
    Full preprocessing pipeline before price extraction.
    """

    s = normalize_currency_spacing(text, config)

    s = strip_per_unit_prices(s, config)

    return s


# =========================================================
# EXTRACTION
# =========================================================

def extract_currency_and_price(
    text: str,
    config: dict
) -> Tuple[Optional[str], Optional[float]]:
    """
    Extract normalized currency + numeric price.

    Returns:
        ("USD", 45000)
        ("HNL", 3500000)

    Supports:
        US$ 45,000
        45,000 USD
        €45000
        45000€
    """

    if not text:
        return None, None

    text = clean_text_for_price(text, config)

    rx = build_price_regex(config)

    matches = list(rx.finditer(text))

    if not matches:
        return None, None

    # usually final price in classified listings is safest
    m = matches[-1]

    groups = m.groups()

    currency = None
    number = None

    # PREFIX FORMAT
    # currency + number
    if groups[0] and groups[1]:

        currency = groups[0]
        number = groups[1]

    # SUFFIX FORMAT
    # number + currency
    elif groups[2] and groups[3]:

        number = groups[2]
        currency = groups[3]

    if currency is None or number is None:
        return None, None

    currency = normalize_currency_token(currency, config)

    value = parse_price_number(number)

    return currency, value


# =========================================================
# PRICE PARSER
# =========================================================

def parse_price_number(value: str) -> Optional[float]:
    """
    Parse localized price strings safely.

    Handles:
        45,000
        45.000
        45,000.50
        45.000,50
    """

    if value is None:
        return None

    s = str(value).strip()

    try:

        # 45.000,50
        if "." in s and "," in s:

            if s.rfind(",") > s.rfind("."):
                s = s.replace(".", "")
                s = s.replace(",", ".")

            else:
                s = s.replace(",", "")

        # 45.000
        elif s.count(".") > 1:
            s = s.replace(".", "")

        # 45,000
        elif s.count(",") > 1:
            s = s.replace(",", "")

        # decimal comma
        elif "," in s and "." not in s:
            s = s.replace(",", ".")

        return float(s)

    except Exception:
        return None


# =========================================================
# BOOLEAN HELPERS
# =========================================================

def contains_currency(
    text: str,
    config: dict
) -> bool:

    if not text:
        return False

    curr = build_currency_regex(config)

    return bool(
        re.search(curr, text, re.IGNORECASE)
    )


def extract_currency_only(
    text: str,
    config: dict
) -> Optional[str]:

    if not text:
        return None

    curr = build_currency_regex(config)

    m = re.search(curr, text, re.IGNORECASE)

    if not m:
        return None

    return normalize_currency_token(
        m.group(0),
        config
    )