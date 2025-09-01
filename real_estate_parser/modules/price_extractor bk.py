
import re
import unicodedata
from typing import Dict, Optional, Tuple
import sys,os
from datetime import datetime
 
######
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

######
PRICE_PAT = r"""
(?P<cur>US\$|USD|\$|HNL|LPS|L\.?|L)
\s*
(?P<num>\d{1,3}(?:[.,]\d{3})*(?:[.,]\d+)?)
"""
REV_PRICE_PAT = r"""
(?P<num>\d{1,3}(?:[.,]\d{3})*(?:[.,]\d+)?)
\s*
(?P<cur>US\$|USD|\$|HNL|LPS|L\.?|L)
"""


RANGE_SEP = r"(?:-|–|a|hasta)"

def _to_float_num(s: str) -> float:
    s = s.replace(".", "").replace(",", ".")
    return float(s)

def _norm_cur(token: str, aliases: dict) -> str:
    t = token.strip()
    return aliases.get(t, aliases.get(t.rstrip("."), t))

def extract_price(text: str, cfg: dict | None = None):
    cfg = cfg or {}
    cur_alias = cfg.get("currency_aliases", {"$": "USD", "US$": "USD", "L.": "LPS", "L": "LPS"})

    # ======= NEW: prefer first price after dot anchor =======
    if cfg.get("price_hints", {}).get("prefer_first_after_dot"):
        dot_idx = cfg.get("dot_idx")
        if isinstance(dot_idx, int) and dot_idx >= 0:
            window = cfg.get("price_hints", {}).get("scan_window_chars", 40)
            span = text[dot_idx + 1 : dot_idx + 1 + window]

            # Try RANGE first: CUR NUM SEP CUR? NUM
            m = re.search(
                rf"{PRICE_PAT}\s*{RANGE_SEP}\s*(?:{PRICE_PAT}|(?P<num2>\d{{1,3}}(?:[.,]\d{{3}})*(?:[.,]\d+)?))",
                span,
                flags=re.IGNORECASE | re.VERBOSE,
            )
            if m and cfg.get("price_hints", {}).get("allow_range", True):
                cur1 = _norm_cur(m.group("cur"), cur_alias)
                n1 = _to_float_num(m.group("num"))
                # second price may omit currency; reuse cur1 if so
                cur2 = _norm_cur(m.group("cur_2"), cur_alias) if "cur_2" in m.groupdict() and m.group("cur_2") else cur1
                n2_str = m.group("num_2") if "num_2" in m.groupdict() and m.group("num_2") else m.group("num2")
                n2 = _to_float_num(n2_str)
                return {
                    "price_min": min(n1, n2),
                    "price_max": max(n1, n2),
                    "currency": cur1,  # use first currency as canonical
                }

            # Single price: CUR NUM
            m = re.search(rf"{PRICE_PAT}", span, flags=re.IGNORECASE | re.VERBOSE)
            if m:
                cur = _norm_cur(m.group("cur"), cur_alias)
                n = _to_float_num(m.group("num"))
                return {"price": n, "currency": cur}
            
def _normalize_num_token(num_str: str) -> float | None:
    """
    Robustly convert strings like '1,700.00', '1.700,00', '1 700', '1700' to float.
    Heuristic:
      - If both ',' and '.' appear: whichever comes last is the decimal separator.
      - If only ',' appears and groups look like thousands (xxx,xxx[,xxx]) -> remove commas.
      - Otherwise replace ',' with '.' once if it looks like decimal.
    """
    s = num_str.strip().replace(" ", "")
    has_comma = "," in s
    has_dot = "." in s

    if has_comma and has_dot:
        # Heuristic: whichever separator comes last is the decimal
        if s.rfind(',') > s.rfind('.'):
            # European style: 1.800,50 -> 1800.50
            s = s.replace('.', '')
            s = s.replace(',', '.', 1)
        else:
            # US style: 1,800.50 -> 1800.50
            s = s.replace(',', '')
    elif has_comma and not has_dot:
        # Decide if comma is thousands or decimal
        parts = s.split(",")
        if all(len(p) == 3 for p in parts[1:-1]) and len(parts[-1]) in (3, 0):
            s = "".join(parts)            # 1,234,567 -> 1234567
        else:
            s = s.replace(",", ".", 1)    # 12,5 -> 12.5

    try:
        return float(s)
    except Exception:
        return None
    

#=========EXTRACT PRICE


def extract_price(text: str, config: dict):
    if not text:
        return (None, None)

    aliases = (config.get("currency_aliases") or {})
    pov = (config.get("parsing_overrides") or {})
    accept_mil = bool(pov.get("price_accept_mil"))
    accept_k   = bool(pov.get("price_accept_k"))
    #####
    req_cur = bool(pov.get("price_require_currency"))   # <--- add here
    block_units = []
    ###
    
    if "price_block_area_units" in pov:
        block_units = pov["price_block_area_units"]
    else:
    # derive from area_aliases automatically
        for vals in (config.get("area_aliases") or {}).values():
            block_units.extend(vals)
    # add a few generic fallbacks
    block_units.extend(["vara", "varas"])

    AREA_NEAR = tuple(u.lower() for u in block_units)

    ###
    price_kw = tuple(k.lower() for k in pov.get("price_keywords", []))
    # ... rx1, rx2 definitions ...
    NUM = r'(?P<num>\d{1,3}(?:[.,\s\u00A0\u202F]\d{3})*(?:[.,]\d+)?|\d+(?:[.,]\d+)?)'
    NUM_TRAIL = r'(?:[.,](?!\d))?'
    CUR = r'(?P<cur>US\$|USD\$|USD\s?\$|\$|L\.?|Lps\.?|USD|HNL|L)'
    TAIL = r'(?P<tail>(?:k|K|mil|mm|m|M|mill(?:ones?|ón|on)?)\b)?'
    # regex definitions for price candidates
    rx1 = re.compile(CUR + r'[\s\u00A0\u202F]*[,.:;–—-]?\s*' + NUM + NUM_TRAIL + r'\s*' + TAIL,
    re.IGNORECASE)
    
    rx2 = re.compile(
    r'(?P<num>\d{1,3}(?:[.,]\d{3})*(?:[.,]\d+)?|\d+(?:[.,]\d+)?)'   # number (1,200.50 / 1200,50 / 1200)
    r'(?:[.,](?!\d))?'                                             # allow a trailing . or , not followed by a digit
    r'\s*'
    r'(?P<cur>US\$|USD\$|USD\s?\$|\$|L\.|Lps\.?|USD|HNL)?'         # currency variants (optional)
    r'\s*'
    r'(?P<tail>(?:k|K|mil|mm|m|M|mill(?:ones?|ón|on)?)\b)?',       # K / mil / mm / m / mill(on|ones|ón)
    re.IGNORECASE)



    # --- collect candidates (our new logic) ---
    cands = []
    for m in rx1.finditer(text):
        cands.append(("rx1", m))
    for m in rx2.finditer(text):
        cands.append(("rx2", m))

    if not cands:
        return (None, None)

    
    BED_BATH_RE = re.compile(r"\b(hab(?:s|itaciones?)?|br|bd|dorms?)\b|\b\d+\s*/\s*\d+\b", re.IGNORECASE)

    best = None
     
    
    for kind, m in cands:

        # 1) 
        start, end = m.span()
        ctx = text[max(0, start-12): end+12].lower()
        # 2) 
        if any(unit in ctx for unit in AREA_NEAR):
            continue  # skip this candidate (it’s too close to area units)
        
        # 3) Parse raw tokens from the match (use your existing logic)
        #    raw_cur, raw_num, tail, etc. = parse_from_match(kind, m)
        #    (don’t change how you already extract them—just do it here)

       
        gd = m.groupdict()
        raw_cur = (gd.get("cur") or "").strip()
        raw_num = m.group("num")                             # <-- keep this
        tail = (gd.get("tail") or "").lower().strip()
        #r===========
       

        # CLEANUP + CANONICALIZE (drop this whole block in)
        raw_num = (raw_num or "").strip()
        raw_num = raw_num.replace("\u00A0", "").replace("\u202F", "")  # remove NBSP/thin NBSP
        raw_num = raw_num.rstrip(".,)") 

       # Strict thousands detection:
        # - If it clearly looks like 1,234 or 1,234,567(.89) → remove commas (US style)
        # - If it clearly looks like 1.234 or 1.234.567(,89) → swap dot thousands + comma decimal (EU style)
        if re.fullmatch(r"\d{1,3}(?:,\d{3})+(?:\.\d+)?", raw_num):
            raw_num = raw_num.replace(",", "")
        elif re.fullmatch(r"\d{1,3}(?:\.\d{3})+(?:,\d+)?", raw_num):
            raw_num = raw_num.replace(".", "").replace(",", ".")


        # 3) PER-M² GUARD (skip for now; no schema change)
        if re.search(r"(x\s*m2|/m2|por m2|p/m2|x\s*m²|/m²|por m²|p/m²)", ctx, re.IGNORECASE):
            mode = pov.get("treat_price_per_m2_as", "skip")
            if mode == "skip" or mode == "total":   # 'total' requires area support; skip for now
                 continue
            elif mode == "unit_price":
                # Don't return a different shape here; either:
                #  (a) store a side-flag for later, or
                #  (b) also 'continue' until you extend the return type.
                continue

        # only valid if you’ve parsed `area` too
       
        # 4) CURRENCY GUARD — only after raw_cur is known
        
        if req_cur and not raw_cur:
            continue  # skip candidate because config requires explicit currency
        
    # 5) Normalize currency + number (keep your current helpers)
    #    cur = normalize_currency(raw_cur, aliases)
        cur = aliases.get(raw_cur, raw_cur).upper() if raw_cur else None
        if not cur and aliases:
            for tok, norm in aliases.items():
                if tok in text:
                    cur = norm.upper()
                    break

      # number normalize
        value = _normalize_num_token(raw_num)
        if value is not None and tail:
            if accept_mil and (tail in ("m","mm") or tail.startswith("mill")):
                value *= 1_000_000
            elif accept_k and (tail == "k" or tail == "mil"):
                value *= 1_000
        ####

        score = 0

         # optional: add your existing penalties for bed/bath tokens, etc.

        if cur:
            score += 2
        if any(k in ctx for k in price_kw):
            score += 1
        if BED_BATH_RE.search(ctx):
            score -= 3     
       
        if tail in ("mm", "mil", "k") or tail.startswith("mill"):
            score += 1
        

    # 7) Select best (tie-break by rightmost)
        cand = (score, end, value, cur)
        if best is None or cand[0] > best[0] or (cand[0] == best[0] and cand[1] > best[1]):
            best = cand

    # 8) Finalize

    if not best:
        return (None, None)

    _, _, val, cur = best
 
    #========

    if val is not None:
        val = int(round(val)) if abs(val - round(val)) < 1e-9 else round(val, 2)

    return (val, cur)  # <— ALWAYS a tuple


#===================END EXTRACT PRICE