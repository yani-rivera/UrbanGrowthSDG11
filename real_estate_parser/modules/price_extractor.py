# price_extractor.py — patched v2 (phase-1)
# Scope: minimal, surgical fixes to stabilize price extraction without refactor.
# Keeps public API: extract_price(text: str, config: dict) -> (value: Optional[float], currency: Optional[str])
# Notes:
# - Honors per-agency messy currency aliases (no normalization of aliases themselves)
# - Adds strict currency boundaries, numeric normalization inside digit runs
# - Masks areas/amenities/labels/years (config-driven)
# - Range logic: stricter "/" behavior; optional currency inheritance; first_only policy supported

from __future__ import annotations
import re
import unicodedata
from typing import Dict, List, Optional, Tuple

# -----------------------------
# Helpers
# -----------------------------

# --- ES/locale autofix helpers ---
_ES_THOUSANDS_ONLY = re.compile(r"\b\d{1,3}(?:\.\d{3})+\b")          # 675.000 | 1.200.000
_ES_THOUSANDS_DEC  = re.compile(r"\b\d{1,3}(?:\.\d{3})+,\d{2}\b")    # 1.200,50

def _autofix_price_locale(text: str, amount: Optional[float], locale: str = "auto") -> Optional[float]:
    """
    Return corrected amount or original if no action needed.
    - 'auto'/'es': fix Spanish-style tokens found in `text`
    - 'en'/'off' : no change
    """
    if amount is None or not text:
        return amount

    loc = (locale or "off").lower()
    if loc in {"en", "off"}:
        return amount

    # Prefer explicit ES decimal: 1.200,50 -> 1200.50
    m = _ES_THOUSANDS_DEC.search(text)
    if m and loc in {"auto", "es"}:
        try:
            return float(m.group(0).replace(".", "").replace(",", "."))
        except Exception:
            pass

    # Dotted thousands only: no-op; US parse is already correct for '500.000' -> 500000
    # (Disabled to prevent 500.000 being scaled down to 500.0)
    # m = _ES_THOUSANDS_ONLY.search(text)
    # if m and loc in {"auto", "es"}:
    #     pass

    return amount


def _fix_leading_dot_after_currency(s: str, currency_prefixes: list[str]) -> str:
    """
    Turn '$.550.00' -> '$550.00', 'L. .750' -> 'L.750'.
    Works for any alias that acts as a prefix (e.g., '$', 'US$', 'L.', 'Lps.').
    """
    if not currency_prefixes:
        return s
    # build alternation of prefix-like aliases
    pref = "|".join(sorted({re.escape(a) for a in currency_prefixes}, key=len, reverse=True))
    # remove a single '.' (optionally with spaces) right after the currency alias if a digit follows
    return re.sub(rf'(?i)\b(?:{pref})\s*\.(?=\d)', lambda m: m.group(0).rstrip().rstrip('.')[:-1], s)


def rhs_looks_pricey(rhs: str) -> bool:
    """
    Heuristic: does the RHS string look like a price-like number?
    Used when no explicit currency symbol is present, but we may inherit it
    from the LHS in a range expression.
    """
    if not rhs:
        return False

    # e.g. starts with digits, optionally with commas/periods
    m = re.match(r"\s*\d[\d,.\s]*", rhs)
    return bool(m)


def _round_val(val: Optional[float]) -> Optional[float]:
    if val is None:
        return None
    r = round(val, 2)
    if abs(r - int(r)) < 1e-9:
        return float(int(r))
    return r

def _scan_candidates(
    s_masked: str,
    pfx_pat,
    sfx_pat,
    sep_pat,
    aliases_map,
    require_currency: bool,
    accept_k: bool,
    accept_m: bool,
    inherit_in_ranges: bool,
    min_inherit_rhs: float,
    first_only: bool
) -> Optional[Tuple[float, str]]:

    candidates: List[Tuple[int, int, float, str]] = []

    matches = []
    matches.extend(pfx_pat.finditer(s_masked))
    matches.extend(sfx_pat.finditer(s_masked))
    matches.sort(key=lambda mm: mm.start())

    for m in matches:
        gd = m.groupdict()
        cur_tok  = gd.get("cur")
        num_text = gd.get("num")
        mag      = gd.get("mag")

        cur_code = _norm_currency(cur_tok, aliases_map)
        if not cur_code and require_currency:
            continue
        if mag and ((mag.lower() == "k" and not accept_k) or (mag.lower() == "m" and not accept_m)):
            continue

        val = _to_float_num(num_text, mag)
        if val is None:
            continue

        start, end = m.span()
        candidates.append((start, end, val, cur_code or "UNKNOWN"))

        # ---- range handling ----
        rest  = s_masked[end:]
        sep_m = sep_pat.match(rest)
        if not sep_m:
            continue

        rhs = rest[sep_m.end():]

        # dual-currency guard
        if sep_m.group(0).strip() == "/":
            if pfx_pat.match(rhs) or sfx_pat.match(rhs):
                # dual currency → NOT a range
                continue

        m_rhs = pfx_pat.match(rhs) or sfx_pat.match(rhs)
        if m_rhs:
            gd2       = m_rhs.groupdict()
            cur2_tok  = gd2.get("cur")
            num2_text = gd2.get("num")
            mag2      = gd2.get("mag")
            cur2_code = _norm_currency(cur2_tok, aliases_map)
            val2      = _to_float_num(num2_text, mag2)

            if cur2_code or (inherit_in_ranges and val2 is not None and val2 >= min_inherit_rhs):
                if not first_only and val2 is not None:
                    v = min(val, val2)
                    return (_round_val(v), cur_code)

        elif inherit_in_ranges and rhs_looks_pricey(rhs):
            m_bare = re.match(
                r"\s*(?P<num>" + _build_number_pattern() + r")(?P<mag>[kKmM])?",
                rhs
            )
            if m_bare:
                val2 = _to_float_num(m_bare.group("num"), m_bare.group("mag"))
                if val2 is not None and val2 >= min_inherit_rhs:
                    if not first_only:
                        v = min(val, val2)
                        return (_round_val(v), cur_code)

    # ---- FINAL SELECTION ----
    if not candidates:
        return None

    # choose most plausible candidate (largest value)
    start, end, val, cur = max(candidates, key=lambda t: t[2])
    return (_round_val(val), cur)



def _strip_nbsp(s: str) -> str:
    if not s:
        return s
    return s.replace("\u00A0", " ").replace("\u202F", " ")


def _collapse_spaces_in_digit_runs(s: str) -> str:
    def fix_run(m):
        run = m.group(0)
        # already had: remove spaces AFTER separator: 1, 000 -> 1,000
        run = re.sub(r"([.,])\s+(?=\d{3}(\D|$))", r"\1", run)
        # NEW: remove spaces BEFORE separator: 650 ,000 -> 650,000
        run = re.sub(r"\s+([.,])(?=\d{3}(\D|$))", r"\1", run)
        return run
    return re.sub(r"(?:\d[\d\s.,]*\d)", fix_run, s)



def _normalize_leading_dot_after_currency(s: str, currency_prefixes: List[str]) -> str:
    """Turn $.550.00 -> $550.00; L. .750 -> L.750 (allow spaces)."""
    if not currency_prefixes:
        return s
    # Build a union that matches the literal aliases (escaped) that act as prefixes
    pref = "|".join(sorted({re.escape(a) for a in currency_prefixes}, key=len, reverse=True))
    # currency [spaces] . digit  => currency digit
    return re.sub(rf"(?i)(?:{pref})\s*\.(?=\d)", lambda m: m.group(0).rstrip().rstrip('.')[:-1], s)


def _to_float_num(raw: str, mag: Optional[str]) -> Optional[float]:
    if raw is None:
        return None

    s = raw.strip()
    s = _strip_nbsp(s)

    # Support sign/parentheses  (NEW)
    sign = -1 if s.startswith("(") or s.startswith("-") else 1
    s = s.lstrip("()+- ").rstrip()

    # Normalize weird spaces
    s = s.replace("\u202F", " ").replace("\u2009", " ").replace("\u00A0", " ")
    s = re.sub(r"(?<=\d)\s+(?=[.,]?\d)", "", s)

    # Mixed separators: keep ONLY the last as decimal
    if "," in s and "." in s:
        last = max(s.rfind(","), s.rfind("."))
        intpart = re.sub(r"[^\d]", "", s[:last])
        decpart = re.sub(r"\D", "", s[last+1:])
        s = f"{intpart}.{decpart}" if decpart else intpart

    elif "," in s:
        if re.fullmatch(r"\d{1,3}(?:,\d{3})+", s):            # 1,200,000
            s = s.replace(",", "")
        elif re.fullmatch(r"\d+,\d{1,3}", s):                 # 600,5  / 600,50 / 600,500 (NEW allows 3)
            s = s.replace(",", ".")
        elif re.fullmatch(r"\d+,\d{4,}", s):                  # 800,1000 → likely TWO prices  (NEW)
            return None
        else:
            s = s.replace(",", "")

    elif "." in s:
        if re.fullmatch(r"\d{1,3}(?:\.\d{3})+", s) or re.fullmatch(r"\d+\.\d{3}", s):
            s = s.replace(".", "")
        elif s.count(".") > 1:
            last = s.rfind(".")
            intpart = s[:last].replace(".", "")
            decpart = re.sub(r"\D", "", s[last+1:])
            if 1 <= len(decpart) <= 3:                         # NEW: allow 3
                s = f"{intpart}.{decpart}"
            else:
                s = intpart + decpart
        elif re.fullmatch(r"\d+\.\d{1,3}", s):                 # NEW: allow 3
            pass
        else:
            if len(s.split(".")[-1]) == 3:
                s = s.replace(".", "")

    # Parse
    try:
        val = float(s)
    except ValueError:
        digits = re.sub(r"\D", "", s)
        val = float(digits) if digits else None
    if val is None:
        return None

    # Magnitudes
    m = (mag or "").strip().lower()
    if m in ("k", "mil"):
        val *= 1_000
    elif m in ("m", "mm", "millón", "millon", "millones"):
        val *= 1_000_000

    return sign * val


def _norm_currency(token: str, alias_map: Dict[str, str]) -> Optional[str]:
    if not token:
        return None
    t = token.strip()
    # exact then lowercase
    if t in alias_map:
        return alias_map[t]
    lower = t.lower()
    return alias_map.get(lower)

def _mask_nonprice_numbers(text: str, config: dict) -> str:
    """
    Replace numbers that are very likely not prices (areas, rooms, baths) with placeholders.
    This prevents false positives during price extraction.
    """
    s = text

    # Mask areas like "594V2", "400M2", "980 v²"
    s = re.sub(r"\b\d{2,5}\s*(v2|m2|mts2|m²|v²)\b", " ###AREA### ", s, flags=re.IGNORECASE)

    # Mask bedroom/bath counts like "(3) hab", "(2) baños", etc.
    s = re.sub(r"\(\d+\)\s*(hab|habitaciones?|baños?|baths?|recámaras?)", " ###ROOM### ", s, flags=re.IGNORECASE)

    # Mask simple bedroom/bath notations like "3hab", "2baños"
    s = re.sub(r"\b\d+\s*(hab|habitaciones?|baños?|baths?|recámaras?)\b", " ###ROOM### ", s, flags=re.IGNORECASE)

    return s



# -----------------------------
# Core compile helpers (config-driven)
# -----------------------------

def _compile_currency(alias_map: Dict[str, str]) -> Tuple[re.Pattern, List[str]]:
    """Return a regex that matches any currency alias and a list of 'prefix-style' aliases for leading-dot fix."""
    if not alias_map:
        # never match
        return re.compile(r"a^"), []
    aliases = list(alias_map.keys())
    # Build case-sensitive alternation preserving punctuation/spaces
    # Also keep a list of tokens that commonly appear as prefixes for leading-dot normalization
    prefix_like = []
    escaped = []
    for a in aliases:
        ea = re.escape(a)
        escaped.append(ea)
        if any(sym in a for sym in ("$", "L", "US$", "U$", "HNL")):
            prefix_like.append(a)
    pat = "(?:" + "|".join(sorted(escaped, key=len, reverse=True)) + ")"
    return re.compile(pat), prefix_like


def _build_number_pattern() -> str:
    # thousands first; decimal tail ≤2; (?!00) prevents taking "1.5" from "1.500"
    return r"(?:\d{1,3}(?:[.,]\s?\d{3})+(?:[.,]\d{1,2})?|\d+(?:[.,]\d{1,2})(?!00)|\d+)"



def _compile_price_patterns(cur_pat: re.Pattern) -> Tuple[re.Pattern, re.Pattern]:
    num = _build_number_pattern()
    # Prefix: currency (non-letter before), optional spaces, number, optional mag
    #pfx = re.compile(rf"(?<![A-Za-z])(?P<cur>{cur_pat.pattern})\s*(?P<num>{num})(?P<mag>[kKmM])?", re.IGNORECASE)
    MAG = r"(?P<mag>(?:mill(?:[óo]n|ones)|mm|m|k|mil))\b"  # longer-first + WORD BOUNDARY
    pfx = re.compile(rf"(?<![A-Za-z])(?P<cur>{cur_pat.pattern})\s*\.?\s*(?P<num>{num})\s*(?:{MAG})?", re.IGNORECASE)
    # Suffix: number, optional mag, spaces, currency
    #sfx = re.compile(rf"(?P<num>{num})(?P<mag>[kKmM])?\s*(?P<cur>{cur_pat.pattern})", re.IGNORECASE)
    # AFTER — disallow lone 1–9 unless they have cents
    sfx = re.compile(
        rf"(?P<num>{num})\s*(?:{MAG})?\s*(?P<cur>{cur_pat.pattern})",
        re.IGNORECASE
    )

    return pfx, sfx


def _compile_masks(cfg: dict) -> Dict[str, re.Pattern]:
    masks = {}
    mx = (cfg.get("masks_extras") or {})
    # Areas (always on)
    units = set(["m2", "m²", "mts2", "v2", "vrs2", "vrs²", "varas cuadradas"]) | set((cfg.get("masks", {}) or {}).get("areas", {}).get("units", []))
    # with/without space
    area_unit = r"(?:" + "|".join(sorted(map(re.escape, units), key=len, reverse=True)) + ")"
    masks["area_spaced"] = re.compile(rf"\b\d+(?:[.,]\d+)?\s*{area_unit}\b", re.IGNORECASE)
    masks["area_glued"] = re.compile(rf"\b\d+(?:[.,]\d+)?{area_unit}\b", re.IGNORECASE)
    # Amenities minimal for this phase
    levels = ["niv", "niv.", "nivel", "niveles"] + mx.get("levels", [])
    parking = ["gje", "garage", "garaje", "garajes", "cochera", "cocheras", "parqueo", "parqueos"] + mx.get("parking", [])
    masks["levels"] = re.compile(rf"\(?\d+\)?\s*(?:{ '|'.join(map(re.escape, levels)) })\b", re.IGNORECASE)
    masks["parking_pre"] = re.compile(rf"\(?\d+\)?\s*(?:{ '|'.join(map(re.escape, parking)) })\b", re.IGNORECASE)
    masks["parking_post"] = re.compile(rf"\b(?:{ '|'.join(map(re.escape, parking)) })\s*\.?\s*\(?\d+\)?\b", re.IGNORECASE)
    # Beds/Baths are likely already handled upstream, but keep light coverage
    masks["beds"] = re.compile(r"\(?\d+\)?\s*(?:hab(?:\.|itaciones)?)\b", re.IGNORECASE)
    masks["baths"] = re.compile(r"\(?\d+\)?\s*(?:ba(?:ños)?|baths?|bths?)\b", re.IGNORECASE)
    # Labels & years
    labels = ["ID", "Ref", "Código", "Code", "Price"] + mx.get("labels", [])
    masks["labels"] = re.compile(rf"\b(?:{ '|'.join(map(re.escape, labels)) })\s*[:=]\s*\d+\b", re.IGNORECASE)
    masks["years"] = re.compile(r"\b(19\d{2}|20\d{2})\b")
    return masks


def _apply_masks(text: str, masks: Dict[str, re.Pattern], glue_area_tails: bool, currency_pat: re.Pattern) -> str:
    s = text
    # Mask neighborhood exceptions if present in config (prevents currency confusion)
    # Caller can pre-replace those; keep here noop for now.
    # Area
    changed = True
    while changed:
        changed = False
        for key in ("area_spaced", "area_glued"):
            if key == "area_glued" and not glue_area_tails:
                continue
            rx = masks[key]
            new_s, n = rx.subn("<AREA>", s)
            if n:
                s = new_s
                changed = True
    # AREA/AREA cluster -> single placeholder so '/' can't trigger range
    s = re.sub(r"<AREA>\s*/\s*<AREA>", "<AREA>", s)
    # Amenities, labels, years
    for k in ("levels", "parking_pre", "parking_post", "beds", "baths", "labels", "years"):
        s = masks[k].sub("<META>", s)
    # Parenthetical clusters containing no currency but areas/amenities only
    def _paren_mask(m: re.Match) -> str:
        g = m.group(0)
        if currency_pat.search(g):
            return g
        if "<AREA>" in g or re.search(r"<(META)>", g):
            return "<META>"
        # quick heuristic: if it has only digits, separators, and amenity words → mask
        if re.search(r"\d", g) and not currency_pat.search(g):
            return "<META>"
        return g
    s = re.sub(r"\([^)]{1,120}\)", _paren_mask, s)
    return s



def extract_price(text: str, config: dict) -> Tuple[Optional[float], Optional[str]]:
    if not text:
        return (None, None)
    
    # --- load config knobs ---
    aliases_map = (config.get("currency_aliases") or {})            # {alias -> ISO}
    pov         = (config.get("parsing_overrides") or {})
    require_currency   = bool(pov.get("price_require_currency", True))
    accept_k           = bool(pov.get("price_accept_k", True))
    accept_m           = bool(pov.get("price_accept_mil", True))
    inherit_in_ranges  = bool(pov.get("inherit_currency_in_ranges", True))
    min_inherit_rhs    = int(pov.get("inherit_currency_in_ranges_min_value", 1000))
    first_only         = (pov.get("multi_price_policy") or "first_only").lower() == "first_only"

    # --- compile currency & price patterns ---
    cur_pat, _prefix_like = _compile_currency(aliases_map)          # regex for aliases
    pfx_pat, sfx_pat      = _compile_price_patterns(cur_pat)        # currency+number, number+currency
    # ---\

    
    # ---- pre-clean (normalize before masking) ----
    # NOTE: _compile_currency returned the list of prefix-like aliases as `_prefix_like`
    s = _strip_nbsp(text)
    s = _collapse_spaces_in_digit_runs(s)                       # e.g., "1, 000,000" → "1,000,000", "650 ,000" → "650,000"
    s = _fix_leading_dot_after_currency(s, _prefix_like)        # e.g., "$.550.00" → "$550.00", "L. .750" → "L.750"

    # ---- range separators ----
    seps    = config.get("range_separators") or ["-", "–", "—", "/", " to ", " a ", " hasta "]
    sep_pat = re.compile(r"\s*(?:" + "|".join(map(re.escape, seps)) + r")\s*", re.IGNORECASE)

    # ---- masking (areas, beds/baths, etc.) ----
    s_masked = _mask_nonprice_numbers(s, config)
    masks   = _compile_masks(config)

    result = _scan_candidates(
        s_masked,
        pfx_pat,
        sfx_pat,
        sep_pat,
        aliases_map,
        require_currency,
        accept_k,
        accept_m,
        inherit_in_ranges,
        min_inherit_rhs,
        first_only,
    )
    if result is None:
        return (None, None)
    amount, currency = result
    locale_flag = (config or {}).get("price_autofix_locale", "auto")   # "off" | "auto" | "es" | "en"
    amount = _autofix_price_locale(text, amount, locale=locale_flag)

    return (_round_val(amount), currency)
    
  
