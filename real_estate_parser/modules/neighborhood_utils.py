
import re
import json
import unicodedata
from typing import List, Dict, Optional, Pattern, Iterable, Union, Any,Tuple
#======================================================================================

_DEF_NEIGH_DELIM = ","

#=======================================================================================


# Drop property-type prefixes at start, and heal OCR’s leading “C” glitch (e.g., "CApto", "CCol.")
def strip_property_prefixes(s: str, cfg: dict | None = None) -> str:
    cfg = cfg or {}
    prefixes = {p.upper() for p in (cfg.get("property_prefixes") or [])}
    if not prefixes:
        return s

    txt = _norm_spaces(s)
    # Heal common OCR: leading 'C' stuck to a known prefix (CApto, CCol., CComercial)
    txt = re.sub(r"^[Cc](?=(?:Casa|Apto|Apart|Comercial|Col\.|Lote|Lotes|Terreno)\b)", "", txt, flags=re.IGNORECASE)

    tokens = txt.split()
    i = 0
    while i < len(tokens):
        head = tokens[i].upper().rstrip(".,:;")
        if head in prefixes:
            i += 1
            continue
        # allow two-word prefixes like "LOTE DE" if you decide to add them later
        break
    return " ".join(tokens[i:]) if i else txt

DEFAULT_ABBREV_MAP: Dict[str, str] = {
    "RESIDENCIAL": "RES.",
    "URBANIZACIÓN": "URB.",
    "URBANIZACION": "URB.",
    "COLONIA": "COL.",
    "BARRIO": "BO.",
}

BARE_ABBREVS_WITH_DOT = {"RES", "URB", "COL", "BO"}


def apply_abbrev_reduction(s: str, cfg: Optional[dict] = None) -> str:
    cfg = cfg or {}
    result = s or ""  # safe default: original text (or empty)

    #print(">>> enter abrev:", repr((s or "")[:80]), flush=True)

    try:
        if not s:
            return result  # empty in, empty out

        # build maps (normalize abbr_map keys for case-insensitive lookup)
        mp = dict(DEFAULT_ABBREV_MAP)
        mp.update(cfg.get("neighborhood_abbrev_map") or {})
        mp.update({k.lower(): v for k, v in (cfg.get("abbr_map") or {}).items()})

        ns = _norm_spaces(s)
        if not ns:
            result = ""
            return result

        # limit parsing to first 60 chars, avoid cutting mid-token
        CUT = 60
        if len(ns) <= CUT:
            prefix, suffix = ns, ""
        else:
            cut = CUT
            if ns[cut - 1].isalnum() and ns[cut].isalnum():
                back = ns.rfind(" ", 0, cut)
                prefix = ns[: back + 1] if back != -1 else ns[:cut]
                suffix = ns[back + 1:] if back != -1 else ns[cut:]
            else:
                prefix, suffix = ns[:cut], ns[cut:]

        tokens = prefix.split()
        if not tokens:
            result = suffix
            return result

        out = []
        for tok in tokens:
            base = tok.rstrip(".,;!?")
            punct = tok[len(base):]
            key = base.lower()
            if key in mp:
                out.append(mp[key] + punct)
            elif base.upper().rstrip(".") in BARE_ABBREVS_WITH_DOT:
                out.append(base.upper().rstrip(".") + "." + punct)
            else:
                out.append(tok)

        parsed_prefix = " ".join(out)
        result = parsed_prefix + suffix
        return result

    except Exception as e:
        # surface the error without killing the pipeline
        #print("<<< abrev ERROR:", repr(e), flush=True)
        return result

    #finally:
        #print("<<< leave  abrev:", repr((result or "")[:80]), flush=True)



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
    """Collapse multiple whitespace into a single space and strip ends."""
    return re.sub(r"\s+", " ", (s or "").strip())

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
     
    cfg = cfg or {}
    text = text or ""
    #text=strip_property_prefixes(text,cfg)
    text=apply_abbrev_reduction(text,cfg)
    temtext=text
    
    span = int(cfg.get("max_token_span", 40))

    # Normalize leading bullets/spaces once for all strategies
    text = text.lstrip("*• ")
    # Get tokens to drop (normalize to lowercase for comparison)
    prefix_tokens = [t.lower() for t in cfg.get("prefix_tokens", [])]

    tokens = text.strip().split()
    if tokens and tokens[0].lower().rstrip(".,;") in prefix_tokens:
        tokens = tokens[1:]
    text = " ".join(tokens)


    if strategy == "uppercase":
         
        tokens = text.strip().split()
        uppercase_tokens: List[str] = []
        for tok in tokens:
            # Remove trailing punctuation before the check
            clean_tok = tok.rstrip(".,:;!?")
            if clean_tok and clean_tok.isupper():
                uppercase_tokens.append(clean_tok)
            else:
                break
        temtext= " ".join(uppercase_tokens)

    elif strategy == "first_comma":
        #print("retrun before coomma:",_cut_before_first_of(text, [","]))
        temtext=text.split(',')[0]
       
    elif strategy == "first_line":
    # Return the very first line (after the existing lstrip("*• ") in apply_strategy)
        temtext= (text or "").splitlines()[30].strip()
    elif strategy == "before_colon":
        temtext= text.split(':')[0]

    elif strategy == "before_comma_or_colon":
        temtext= re.split('[;,]', text)[0]

    elif strategy == "before_currency":
        rx = build_currency_regex(cfg)
        if not rx:
            temtext=""
        m = rx.search(text or "")
        temtext= text[: m.start()].strip() if m else ""



    elif strategy == "is_currency":
        # Diagnostic strategy: returns the matched currency token or "" if none.
        rx = build_currency_regex(cfg)
        if not rx:
            temtext=""
        else:
            m = rx.search(text or "")
            temtext= m.group(0)

    # Back-compat common name
    elif strategy == "before_comma_or_dot":
       temtext = re.split('[,.]', text)[0]

    # Unknown strategy
    if not temtext:
        temtext=text[:span]
    else:
        temtext=temtext[:span]
    #print("final after span ==>",temtext)
    return temtext



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
