# version 2.0
# modules/neighborhood_utils.py
import re, string,unicodedata
from difflib import get_close_matches





__all__ = ["extract_neighborhood", "extract_neighborhood_candidate", "map_neighborhood"]

def _norm(s):
    """Robust normalizer: accepts str/list/tuple/dict/None → NFC upper() trimmed."""
    if s is None:
        s = ""
    elif isinstance(s, (list, tuple, set)):
        s = " ".join(map(str, s))
    elif isinstance(s, dict):
        s = " ".join(map(str, s.values()))
    s = unicodedata.normalize("NFKC", str(s))
    return s.upper().strip()

def apply_strategy(text: str, strategy: str, cfg: Optional[dict] = None) -> str:
    """
    Applies the selected strategy to the provided text.
    """
    text = text or ""
    cfg = cfg or {}

    # Handle 'before_colon' strategy - Extract text before the first colon.
    if strategy == "before_colon":
        return text.split(":")[0].strip()

    # Handle 'before_dot' strategy - Extract text before the first dot.
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

    # Handle 'before_comma_or_dot' strategy - Extract text before the first comma or dot.
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


def _prefix_token_candidate(text: str, tokens, max_span=40):
    if not tokens:
        return ""
    pat = rf'^\s*(?:{"|".join(map(re.escape, tokens))})\s*([^,:]{{1,{max_span}}})'
    # Try “token + name:” first
    m = re.match(pat + r'\s*:', text, flags=re.IGNORECASE)
    if m:
        # Reconstruct full token + name like "COL. PALMIRA"
        lead = re.match(r'^\s*([^\s:]+)', text)
        token = lead.group(1) if lead else ""
        return _norm(f"{token} {m.group(1)}")
    # Then “token + name,”
    m2 = re.match(pat + r'\s*,', text, flags=re.IGNORECASE)
    if m2:
        lead = re.match(r'^\s*([^\s,]+)', text)
        token = lead.group(1) if lead else ""
        return _norm(f"{token} {m2.group(1)}")
    return ""

def _delimiter_candidate(text: str, delimiter=",", max_span=40):
    # Everything before first delimiter, capped
    if not delimiter:
        delimiter = ","
    idx = text.find(delimiter)
    if idx == -1:
        return ""
    cand = text[:idx]
    # keep it conservative to avoid whole line grabs
    cand = cand[:max_span]
    return _norm(cand)

def _fallback_candidate(text: str, max_span=40):
    # first chunk before ":" or ","
    m = re.match(rf'^\s*([^,:]{{3,{max_span}}})[,:]', text)
    return _norm(m.group(1)) if m else ""

def _map_alias(candidate: str, config: dict) -> str:
    if not candidate:
        return ""
    table = (config or {}).get("neighborhood_aliases", {}) or {}
    cand = _norm(candidate)
    # exact canonical
    for canon in table.keys():
        if _norm(canon) == cand:
            return _norm(canon)
    # exact alias
    for canon, aliases in table.items():
        if _norm(canon) == cand:
            return _norm(canon)
        for a in aliases or []:
            if _norm(a) == cand:
                return _norm(canon)
    # fuzzy (one best)
    all_labels = list(table.keys()) + [a for v in table.values() for a in (v or [])]
    choices = [_norm(x) for x in all_labels]
    match = get_close_matches(cand, choices, n=1, cutoff=0.86)
    if match:
        m = match[0]
        for canon, aliases in table.items():
            if _norm(canon) == m or any(_norm(a) == m for a in (aliases or [])):
                return _norm(canon)
    # no match: return cleaned candidate
    return cand

def extract_neighborhood(text: str, config: dict, agency: str = "", **_) -> str:
    """
    Extracts the neighborhood candidate based on the configured strategy order.
    If neighborhood_flow is 'simple', directly apply the strategy and return the result.
    If neighborhood_flow is 'full', follow the full strategy order.
    """
    ag = (agency or "").strip().upper()
    rules = (
        ((config.get("agencies", {}) or {}).get(ag, {}) or {}).get("neighborhood_rule", {})
        or ((config.get("agencies", {}) or {}).get("DEFAULT", {}) or {}).get("neighborhood_rule", {})
        or (config.get("neighborhood_rule", {}) or {})   # <-- NEW fallback
    )
    
    # Extract strategy configurations
    tokens   = rules.get("prefix_tokens", ["col.", "res.", "barrio", "urb.", "blvd.", "anillo periferico"])
    delimiter = rules.get("delimiter", ",") or ","
    order    = rules.get("strategy_order", ["prefix_token", "delimiter", "fallback"])
    max_span = int(rules.get("max_token_span", 40))

    # Normalize the text (or apply any preprocessing if needed)
    t = _norm(text)
    candidate = ""

    # Check if flow_type is "simple"
    flow_type = rules.get("flow_type", "full")  # Default to 'full' if not provided

    if flow_type == "simple":
        # Apply the appropriate strategy (e.g., "delimiter") and return immediately
        candidate = apply_strategy(t, "delimiter", config)
    else:
        # If flow_type is "full", follow the original strategy order logic
        for strat in order:
            if strat == "prefix_token" and not candidate:
                candidate = _prefix_token_candidate(t, tokens, max_span=max_span)
            elif strat == "delimiter" and not candidate:
                candidate = _delimiter_candidate(t, delimiter=delimiter, max_span=max_span)
            elif strat == "before_colon" and not candidate:
                candidate = apply_strategy(t, "before_colon", config)
            elif strat == "before_dot" and not candidate:
                candidate = apply_strategy(t, "before_dot", config)
            elif strat == "before_comma_or_dot" and not candidate:
                candidate = apply_strategy(t, "before_comma_or_dot", config)
            elif strat == "fallback" and not candidate:
                candidate = _fallback_candidate(t, max_span=max_span)

    return _map_alias(candidate, config)  # Map to neighborhood alias if needed


def extract_neighborhood_candidate(text: str, config: dict = None, agency: str = "", **_) -> str:
    """
    Backwards compatibility: approximates the 'candidate' using the
    configured strategy order (delimiter/prefix/fallback).
    If your new implementation only returns the mapped final label,
    this returns that label as the candidate (safe for downstream).
    """
    ag = (agency or "").strip().upper()
    rules = (
        (((config or {}).get("agencies", {}) or {}).get(ag, {}) or {}).get("neighborhood_rule", {})
        or (((config or {}).get("agencies", {}) or {}).get("DEFAULT", {}) or {}).get("neighborhood_rule", {})
        or ((config or {}).get("neighborhood_rule", {}) or {})
    )
    tokens    = rules.get("prefix_tokens", ["col.", "res.", "barrio", "urb.", "blvd.", "anillo periferico"])
    delimiter = rules.get("delimiter", ",") or ","
    order     = rules.get("strategy_order", ["prefix_token", "delimiter", "fallback"])
    max_span  = int(rules.get("max_token_span", 40))

    t = _norm(text)
    candidate = ""
    for strat in order:
        if strat == "prefix_token" and not candidate:
            candidate = _prefix_token_candidate(t, tokens, max_span=max_span)
        elif strat == "delimiter" and not candidate:
            candidate = _delimiter_candidate(t, delimiter=delimiter, max_span=max_span)
        elif strat == "fallback" and not candidate:
            candidate = _fallback_candidate(t, max_span=max_span)
    return candidate



def map_neighborhood(candidate: str, config: dict) -> str:
    return _map_alias(candidate, config)


    #####




# --- Back‑compat shims (what your screenshot shows) ---

    


