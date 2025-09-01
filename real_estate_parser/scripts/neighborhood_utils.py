
import re
import json
from typing import Optional, Tuple

#======================================================================================

_DEF_NEIGH_DELIM = ","

#=======================================================================================


def load_neighborhoods(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def clean_neighborhood_before_currency(text: str, cfg: dict) -> Tuple[str, str]:
    """
    Split neighborhood before the first currency token.
    Returns (neighborhood_clean, pre_price_text).
      - neighborhood_clean: everything left of the first currency alias
      - pre_price_text: context before currency; controlled by cfg["neighborhood_pre_price_keep"]
          - "last_token" (default): keep only the last word before currency
          - "all": keep the entire left side
    If no currency found or no aliases configured, returns (text.strip(), "").
    """
    pat = build_currency_regex(cfg)
    if not pat:
        return text.strip(), ""

    m = pat.search(text or "")
    if not m:
        return (text or "").strip(), ""

    left = (text or "")[:m.start()].rstrip()

    keep = (cfg or {}).get("neighborhood_pre_price_keep", "last_token")
    if keep == "all":
        pre_price = left.strip()
    else:
        toks = left.split()
        pre_price = toks[-1] if toks else ""

    return left.strip(), pre_price.strip()


def _norm_spaces(s: str) -> str:
    return _WS.sub(" ", (s or "").strip())

def normalize_text(text):
    return re.sub(r"[^\w\s]", "", text.lower())

def build_currency_regex(cfg: dict) -> Optional[re.Pattern]:
    """
    Compile a regex that matches any configured currency alias (case-insensitive).
    Uses cfg["currency_aliases"].keys() as the single source of truth.
    """
    keys = list((cfg or {}).get("currency_aliases", {}).keys())
    if not keys:
        return None
    # Longest-first so 'US$' matches before '$'
    alt = "|".join(re.escape(k) for k in sorted(keys, key=len, reverse=True))
    return re.compile(rf"(?:{alt})", flags=re.IGNORECASE)

# --------------------------------------------------------------------------------------
# Neighborhood (best-effort). If you already have a dedicated module, feel free to override.



    # 2) Fallback: first chunk before delimiter
    if delim in text:
        return _norm_spaces(text.split(delim, 1)[0]).upper()

    return None



def apply_strategy(text: str, strategy: str, cfg: Optional[dict] = None) -> str:
    text = text or ""
    cfg = cfg or {}
    #print("DEBUG RECIVE STRATEGY===:", strategy)

    if strategy == "first_comma":
        return text.split(",")[0].strip()

    elif strategy == "before_colon":
        return text.split(":")[0].strip()

    elif strategy == "first_line":
        return text.splitlines()[0].strip()

    # NEW: stop at the first dot that's NOT part of an abbreviation (e.g., "Col.", "Res.", "Bo.")
    elif strategy == "before_dot":
        abbrev = set(a.lower() for a in cfg.get("abbrev_exceptions", ["col", "res", "urb", "bo"]))
        pos_dot = -1
        for m in re.finditer(r"\.", text):
            before = text[:m.start()]
            tail = re.search(r"(\b\w+)$", before)
            token = (tail.group(1).lower() if tail else "")
            if token in abbrev:
                continue  # skip abbrev dot and keep scanning
            pos_dot = m.start()
            break
        if pos_dot != -1:
            return text[:pos_dot].strip()
        return text.strip()

    elif strategy == "before_comma_or_dot":
        abbrev = set(a.lower() for a in cfg.get("abbrev_exceptions", ["col", "res", "urb", "bo"]))
        pos_comma = text.find(",")
        pos_dot = -1
        for m in re.finditer(r"\.", text):
            before = text[:m.start()]
            tail = re.search(r"(\b\w+)$", before)
            token = (tail.group(1).lower() if tail else "")
            if token in abbrev:
                continue
            pos_dot = m.start()
            break
        idxs = [i for i in (pos_comma, pos_dot) if i != -1]
        if idxs:
            return text[:min(idxs)].strip()
        return text.strip()

    return text.strip()



def match_neighborhood(text, neighborhoods, strategy=None, debug=False):
    text_norm = normalize_text(text)

    # 1. Strategy-based override (highest priority)
    if strategy:
        fallback = apply_strategy(text, strategy)
        if fallback:
            if debug:
                print(f"[Strategy Match: {strategy}] → {fallback}")
            return fallback.upper()

    # 2. Exact match or alias match
    for entry in neighborhoods:
        name = entry["Neighborhood"] if isinstance(entry, dict) else entry
        aliases = entry.get("Aliases", []) if isinstance(entry, dict) else []
        all_names = [name] + aliases
        for n in all_names:
            if normalize_text(n) in text_norm:
                if debug:
                    print(f"[Alias Match] Found: {n}")
                return name.upper()

    # 3. Regex-based fallback (e.g., Col., Loma)
    fallback_patterns = [
        r'Col\.?\s?[A-Za-zÁÉÍÓÚÑñ ]+',
        r'Loma\s+[A-Za-z]+',
        r'Altos\s+de\s+[A-Za-z]+',
        r'San\s+[A-Za-z]+',
        r'Res\.?\s?[A-Za-z ]+'
    ]

    for pattern in fallback_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            result = match.group().strip().upper()
            if debug:
                print(f"[Regex Match] → {result}")
            return result

    if debug:
        print("[No Match] Unable to detect neighborhood.")
    return ""
