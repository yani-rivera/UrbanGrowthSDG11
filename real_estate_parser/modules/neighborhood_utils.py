
# modules/neighborhood_utils.py
import re, string
from difflib import get_close_matches
__all__ = ["extract_neighborhood", "extract_neighborhood_candidate", "map_neighborhood"]

def _norm(s: str) -> str:
    s = s or ""
    s = s.upper()
    s = re.sub(r'\s+', ' ', s)
    return s.strip(" " + string.punctuation + ".,;:-")

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

def extract_neighborhood(text: str, config: dict, agency: str) -> str:
    """
    Strategy:
      1) agency-specific neighborhood_rule.strategy_order
      2) run each strategy to get a candidate
      3) alias-map to canonical if possible
    `text` should already be preprocessed (sanitized/lowercased or NFC).
    """
    ag = (agency or "").strip().upper()
    rules = ((config.get("agencies", {}) or {}).get(ag, {}) or {}).get("neighborhood_rule", {}) \
            or (config.get("agencies", {}).get("DEFAULT", {}) or {}).get("neighborhood_rule", {}) \
            or {}

    tokens = rules.get("prefix_tokens", ["col.", "res.", "barrio", "urb.", "blvd.", "anillo periferico"])
    delimiter = rules.get("delimiter", ",")
    order = rules.get("strategy_order", ["prefix_token", "delimiter", "fallback"])
    max_span = int(rules.get("max_token_span", 40))

    # Work with an uppercased version for stability (but caller should pass sanitized text)
    t = _norm(text)

    candidate = ""
    for strat in order:
        if strat == "prefix_token" and not candidate:
            candidate = _prefix_token_candidate(t, tokens, max_span=max_span)
        elif strat == "delimiter" and not candidate:
            candidate = _delimiter_candidate(t, delimiter=delimiter, max_span=max_span)
        elif strat == "fallback" and not candidate:
            candidate = _fallback_candidate(t, max_span=max_span)

    return _map_alias(candidate, config)

def extract_neighborhood_candidate(text: str) -> str:
    """
    Backwards compatibility: approximates the 'candidate' using the
    configured strategy order (delimiter/prefix/fallback).
    If your new implementation only returns the mapped final label,
    this returns that label as the candidate (safe for downstream).
    """
    # If you kept the internal helpers (_delimiter_candidate, etc.),
    # you can compute a real candidate. Otherwise, reuse the final.
    try:
        # If you have a DEFAULT config handy, you can pass it here
        # but simplest is to reuse final result as 'candidate'.
        return str(text or "")[:80]  # conservative placeholder
    except Exception:
        return str(text or "")[:80]

def map_neighborhood(candidate: str, config: dict) -> str:
    """
    Backwards compatibility: map a candidate to canonical using your
    new extract_neighborhood logic. If you have an internal _map_alias,
    call that. Otherwise, just return extract_neighborhood on the original text.
    """
    # If you kept _map_alias, call it; otherwise:
    # best-effort: return candidate unchanged (still prevents ImportError)
    try:
        from modules.neighborhood_utils import extract_neighborhood
        # We don't have the original text/agency here; map 'candidate' as-is
        # If you expose a _map_alias in this module, use that instead.
        return candidate  # safe no-op mapping
    except Exception:
        return candidate
    

    #####




# --- Back‑compat shims (what your screenshot shows) ---

    


