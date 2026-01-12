import re
import pandas as pd
from typing import Dict, Set, Any

UPPER_WORD_RE = re.compile(r"^[A-ZÁÉÍÓÚÜÑ-]+\.?$")
# Add near top-level with your imports
 
COLON_ANY_RE = re.compile(r'[:\uFF1A\uFE55\u2236\u02D0]')  # ASCII ':' + common Unicode variants

def add_colon_after_uppercase_block(text: str, standalone_re, combined_re) -> str:
    if not isinstance(text, str) or not text.strip():
        return text
    # >>> HARD STOP: if any colon exists, keep the line as-is
    if COLON_ANY_RE.search(text):
        return text.strip()

    # ... existing logic follows ...
    words = text.strip().split()
    uppercase_block = []
    i = 0
    while i < len(words):
        w = words[i]
        if is_currency_token(w, standalone_re, combined_re):
            break
        if UPPER_WORD_RE.match(w):
            uppercase_block.append(w.rstrip("."))
            i += 1
        else:
            break

    if not uppercase_block:
        return text.strip()

    block_str = " ".join(uppercase_block)
    remainder = " ".join(words[i:]) if i < len(words) else ""
    return f"{block_str}: {remainder}" if remainder else f"{block_str}:"


def preprocess_neighborhood_delimiter_lines(lines, cfg):
    """Lines: list[str] -> list[str], config-aware."""
    markers = extract_currency_markers(cfg)
    standalone_re, combined_re = build_currency_regex(markers)
    return [add_colon_after_uppercase_block(s, standalone_re, combined_re) for s in lines]


def extract_currency_markers(cfg: Dict[str, Any]) -> Set[str]:
    """Extract currency markers from a loaded CFG dict."""
    markers = set()

    if not cfg:
        return {"LPS", "L", "USD", "US$", "$", "HNL", "DOLARES", "DÓLARES"}

    # From aliases
    if "currency_aliases" in cfg:
        aliases = cfg["currency_aliases"]
        if isinstance(aliases, dict):
            markers.update(aliases.keys())
            markers.update(aliases.values())

    # From markers
    if "currency_markers" in cfg and isinstance(cfg["currency_markers"], list):
        markers.update(cfg["currency_markers"])

    # Normalize
    return {m.upper().strip() for m in markers if isinstance(m, str) and m.strip()}


def build_currency_regex(markers: Set[str]):
    """Build regex for detecting currencies (case-insensitive)."""
    variants = [re.escape(m) for m in markers if m]
    if not variants:
        variants = [re.escape(m) for m in ["LPS", "L", "USD", "US$", "$"]]

    standalone = r"^(?:%s)[\.\,\:\;\)]?$" % "|".join(sorted(variants, key=len, reverse=True))
    combined = r"^(?:%s)[\.\s]*\d[\d\.\,]*$" % "|".join(sorted(variants, key=len, reverse=True))
    return re.compile(standalone, re.IGNORECASE), re.compile(combined, re.IGNORECASE)


def is_currency_token(token: str, standalone_re: re.Pattern, combined_re: re.Pattern) -> bool:
    if not token:
        return False
    t = token.strip()
    if combined_re.match(t):
        return True
    t_stripped = t.strip(".,:;()[]{}")
    return bool(standalone_re.match(t_stripped))




def preprocess_neighborhood_delimiter(df: pd.DataFrame, column: str, cfg: Dict[str, Any]) -> pd.DataFrame:
    """Main entry point — uses already loaded CFG dict."""
    markers = extract_currency_markers(cfg)
    standalone_re, combined_re = build_currency_regex(markers)
    df[column] = df[column].apply(lambda x: add_colon_after_uppercase_block(x, standalone_re, combined_re))
    return df
