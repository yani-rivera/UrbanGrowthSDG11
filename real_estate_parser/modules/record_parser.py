

# record_parser.py — robust per-listing parser (beds/baths/areas/price)
# Public API preserved: parse_record(ln, config, ...)
from __future__ import annotations
import re
from typing import Dict, Optional, Tuple
import sys,os
from datetime import datetime
 

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
#======

# Core extractors / normalizer
from modules.parser_utils import (
    normalize_ocr_text,
    extract_price,
    extract_bedrooms,
    extract_bathrooms,
    extract_area,
    extract_property_type,
    clean_text_for_price)


# Neighborhood extractor

from scripts.neighborhood_utils import  (clean_neighborhood_before_currency,apply_strategy)


 

# --------------------------------------------------------------------------------------
# Optional project extractors; we will gracefully fall back to strict local versions
try:
    from parser_utils import (
        extract_price as _ext_price,
        extract_area as _ext_area,
        extract_bedrooms as _ext_beds,
        extract_bathrooms as _ext_baths,
    )
except Exception:  # pragma: no cover
    _ext_price = _ext_area = _ext_beds = _ext_baths = None

# --------------------------------------------------------------------------------------
# Helpers
_NUMDOT_PREFIX = re.compile(r"^\s*\d{1,3}\.?\s+")
_BULLET_PREFIX = re.compile(r"^\s*[\-*•>]\s+")
_WS = re.compile(r"\s+")




def _strip_leading_marker(text: str) -> str:
    t = _NUMDOT_PREFIX.sub("", text)
    t = _BULLET_PREFIX.sub("", t)
    return t.strip()


def _norm_spaces(s: str) -> str:
    return _WS.sub(" ", (s or "").strip())


# --------------------------------------------------------------------------------------
# Robust numeric parsing used by price/area
_PRICE_SYM = re.compile(
    r"(US\$|\$|LPS?\.?|L\.|USD|HNL)\s*"  # currency
    r"(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})?)",  # number
    re.I,
)

# 265 MIL / 265MIL. / 265 mil. → 265000
_PRICE_MIL = re.compile(r"\b(\d{1,3}(?:[.,]\d{3})*|\d{2,3})\s*MI?L\b\.?", re.I)


def _num_from_locale(s: str) -> Optional[float]:
    """Parse mixed-locale numerals robustly.
    Examples:
      170,000 → 170000
      1,200.50 → 1200.5
      1.200,50 → 1200.5
      2,5 → 2.5
      1.200 → 1200
    """
    if not s:
        return None
    s = s.strip()

    if "," in s and "." in s:
        # last separator is decimal
        if s.rfind(",") > s.rfind("."):
            s = s.replace(".", "").replace(",", ".")  # 1.200,50 → 1200.50
        else:
            s = s.replace(",", "")  # 1,200.50 → 1200.50
    elif "," in s:
        # thousands or decimal
        if re.fullmatch(r"\d{1,3}(?:,\d{3})+", s):
            s = s.replace(",", "")  # 170,000 → 170000
        else:
            s = s.replace(",", ".")  # 2,5 → 2.5
    elif "." in s:
        if re.fullmatch(r"\d{1,3}(?:\.\d{3})+", s):
            s = s.replace(".", "")  # 1.200 → 1200
    try:
        return float(s)
    except ValueError:
        return None


# --------------------------------------------------------------------------------------
# Local strict extractors (used if project versions are missing)



def clean_neighborhood_before_currency(text: str, cfg: dict) -> str:
    """
    Return neighborhood = everything before the first currency alias. Makos or other
    """
    cur_keys = sorted(cfg.get("currency_aliases", {}).keys(), key=len, reverse=True)
    cur_alt  = "|".join(re.escape(k) for k in cur_keys)

    m = re.search(rf"\b(?:{cur_alt})\b", text, flags=re.IGNORECASE)
    if m:
        return text[:m.start()].strip()
    return text.strip()




def detect_section_context(text: str, cfg: Optional[dict] = None) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    if not text:
        return (None, None, None)

    marker = (cfg or {}).get("header_marker", "#")

    # Normalize: strip BOM and left spaces so "#..." at col > 0 still counts
    s = text.replace("\ufeff", "").lstrip()

    # Only header lines (marker at start after lstrip)
    if not re.match(rf"^{re.escape(marker)}", s):
        return (None, None, None)

    # --- Config-driven section headers (case-insensitive) ---
    sh = (cfg or {}).get("section_headers") or []
    if sh:
        best = None  # (span_len, tx, ty, category)
        for item in sh:
            pat = item.get("pattern")
            if not pat:
                continue
            m = re.search(pat, s, flags=re.IGNORECASE)
            if m:
                span_len = m.end() - m.start()
                if (best is None) or (span_len > best[0]):
                    best = (
                        span_len,
                        item.get("transaction"),
                        item.get("type"),
                        item.get("category") or s[len(marker):].strip(" :\t")
                    )
        if best:
            _, tx, ty, cat = best
            return (tx, ty, cat)

    # Fallback heuristic
    h = s[len(marker):].strip().upper()
    tx = "Rent" if "ALQUIL" in h else ("Sale" if "VENTA" in h else None)
    ty = ("Apartment" if "APART" in h
          else "House" if ("CASA" in h or "CASAS" in h)
          else "Commercial" if ("BODEGA" in h or "PROPIEDADES COMERCIALES" in h)
          else "Land" if ("TERRENO" in h or "TERRENOS" in h)
          else None)
    return (tx, ty, h)



_AREA_RX = re.compile(
    r"\b(\d{1,5}(?:[.,]\d{3})*(?:[.,]\d{1,2})?)\s*"
    r"(m2|m²|mt2|mts2|mts|metros\s*cuadrados?|vrs2|vrs²|vrs|vr2|vr|varas?\s*cuadradas?)\b",
    re.I,
)

_BED_WORDS = r"(?:hab(?:itaciones)?|habs?\.?|dorm(?:itorios)?|recá?maras?|alcobas?)"
BED_RX_WORD = re.compile(rf"\b(\d{{1,2}})\s*{_BED_WORDS}\b", re.I)
BED_RX_H = re.compile(r"\b(\d{1,2})\s*[Hh]\b")  # 3H
SLASH_RX = re.compile(r"\b(\d{1,2})\s*/\s*(\d{1,2}(?:[.,]\d)?|\d\s*1/2|½)\b")

BATH_WORD = r"ba(?:ños|nos|ño|no)s?"
BATH_RX_MAIN = re.compile(rf"\b(\d{{1,2}}(?:[.,]\d)?|\d\s*1/2|½)\s*{BATH_WORD}\b", re.I)
BATH_RX_MEDIO = re.compile(rf"\b(\d{{1,2}})\s*y\s*medio\s*{BATH_WORD}?\b", re.I)
BATH_RX_B = re.compile(r"\b(\d{1,2}(?:[.,]\d)?|\d\s*1/2|½)\s*[Bb]\b", re.I)  # 2B


def _cur_map(cur: str, cfg: Optional[dict] = None) -> str:
    m = {"US$": "USD", "$": "USD", "USD": "USD", "L.": "HNL", "LPS": "HNL", "LPS.": "HNL", "HNL": "HNL"}
    if cfg and isinstance(cfg.get("currency_aliases"), dict):
        for k, v in cfg["currency_aliases"].items():
            m[str(k).upper()] = str(v).upper()
    return m.get(cur, cur)


def _local_extract_price(text: str, cfg: Optional[dict] = None) -> Tuple[Optional[float], Optional[str]]:
    t = text or ""
    cands = []
    for m in _PRICE_SYM.finditer(t):
        cur = m.group(1).upper().rstrip(".")
        val = _num_from_locale(m.group(2))
        if val is None:
            continue
        cands.append((val, _cur_map(cur, cfg)))
    cur_seen = cands[-1][1] if cands else None
    for m in _PRICE_MIL.finditer(t):
        base = _num_from_locale(m.group(1))
        if base is not None:
            cands.append((base * 1000.0, cur_seen))
    if not cands:
        return (None, None)
    return max(cands, key=lambda x: x[0])


def _norm_unit(u: str) -> str:
    u = (u or "").lower().replace(" ", "")
    if u in {"m2", "m²", "mt2", "mts2", "mts", "metroscuadrados"}:
        return "m2"
    if u in {"vrs2", "vrs²", "vrs", "vr2", "vr", "varascuadradas", "varacuadrada"}:
        return "vrs2"
    return u


def _local_extract_area(text: str, _cfg: Optional[dict] = None) -> Tuple[Optional[float], Optional[str]]:
    m = _AREA_RX.search(text or "")
    if not m:
        return (None, None)
    val = _num_from_locale(m.group(1))
    unit = _norm_unit(m.group(2))
    return (val, unit) if val is not None else (None, unit)


def _local_extract_bedrooms(text: str, cfg: Optional[dict] = None) -> Optional[int]:
   # t = text or ""
    #m = BED_RX_WORD.search(t) or BED_RX_H.search(t)
    #if m:
    #    v = int(m.group(1))
    #    return v if 0 < v < 20 else None
    #if (cfg or {}).get("allow_slash_bed_bath", True):
    #    m = SLASH_RX.search(t)
    #    if m:
    #        v = int(m.group(1))
    #        return v if 0 < v < 20 else None
    return extract_bedrooms(text, cfg)


def _to_float_half(s: Optional[str]) -> Optional[float]:
    if not s:
        return None
    s = s.replace("½", ".5")
    s = re.sub(r"(\d)\s*1/2", r"\1.5", s)
    return _num_from_locale(s)


def _local_extract_bathrooms(text: str, cfg: Optional[dict] = None) -> Optional[float]:
    t = text or ""
    m = BATH_RX_MAIN.search(t)
    if m:
        v = _to_float_half(m.group(1))
        return v if v and 0 < v < 20 else None
    m = BATH_RX_MEDIO.search(t)
    if m:
        base = _to_float_half(m.group(1))
        return (base + 0.5) if base else None
    m = BATH_RX_B.search(t)
    if m:
        v = _to_float_half(m.group(1))
        return v if v and 0 < v < 20 else None
    if (cfg or {}).get("allow_slash_bed_bath", True):
        m = SLASH_RX.search(t)
        if m:
            v = _to_float_half(m.group(2))
            return v if v and 0 < v < 20 else None
    return None


# Wrappers that accept both (text) and (text, config)
def EXTRACT_PRICE(text: str, cfg: Optional[dict] = None) -> Tuple[Optional[float], Optional[str]]:
    fn = _ext_price or _local_extract_price
    try:
        return fn(text, cfg)
    except TypeError:
        return fn(text)  # type: ignore[misc]


def EXTRACT_AREA(text: str, cfg: Optional[dict] = None) -> Tuple[Optional[float], Optional[str]]:
    fn = _ext_area or _local_extract_area
    try:
        return fn(text, cfg)
    except TypeError:
        return fn(text)  # type: ignore[misc]


def EXTRACT_BEDS(text: str, cfg: Optional[dict] = None) -> Optional[int]:
    fn = _ext_beds or _local_extract_bedrooms
    try:
        return fn(text, cfg)
    except TypeError:
        return fn(text)  # type: ignore[misc]


def EXTRACT_BATHS(text: str, cfg: Optional[dict] = None) -> Optional[float]:
    fn = _ext_baths or _local_extract_bathrooms
    try:
        return fn(text, cfg)
    except TypeError:
        return fn(text)  # type: ignore[misc]


# --------------------------------------------------------------------------------------
# Dual-area extractor: detect land (vrs2) vs built (m2)
AREA_ALL_RX = _AREA_RX  # reuse same pattern (captures both)


def extract_dual_areas(text: str, config: Optional[dict] = None) -> Dict[str, float | str]:
    out: Dict[str, float | str] = {}
    t = text or ""
    for m in AREA_ALL_RX.finditer(t):
        val = _num_from_locale(m.group(1))
        unit = _norm_unit(m.group(2))
        if val is None or not unit:
            continue
        if unit == "m2":
            if "built_value" not in out or val > out["built_value"]:  # keep largest
                out["built_value"], out["built_unit"] = val, unit
        elif unit == "vrs2":
            if "land_value" not in out or val > out["land_value"]:
                out["land_value"], out["land_unit"] = val, unit
    return out

def extract_neighborhood(text: str, cfg: dict) -> str:
    """
    Determine neighborhood using config-driven strategy.
    Supports strategies implemented in neighborhood_utils.apply_strategy,
    and passes the rule (with abbrev_exceptions etc.) down to it.
    """
    text = text or ""
    rule = (cfg or {}).get("neighborhood_rule", {}) or {}
    ##print("DEBUG.=====RULE from extract_neighborhood:", rule)
    strategy = rule.get("strategy", "first_line")
    #print("DEBUG.=====StratEgy from extract_neighborhood:", strategy)
    try:
        # pass the rule as cfg to apply_strategy so it sees abbrev_exceptions, etc.
        neigh = apply_strategy(text, strategy, rule)
        ##print("DEBUG.=====After STRATEGY:", neigh)
        if isinstance(neigh, str) and neigh.strip():
            return neigh.strip()
    except Exception:
        pass  # fall through to fallback

    # fallback: first line
    try:
        return apply_strategy(text, "first_line", rule).strip()
    except Exception:
        return text.strip()

# --------------------------------------------------------------------------------------
# Public API: parse one listing line into a dict

def parse_record(text, config, *, agency="", date="", listing_no=0,
                 default_transaction=None, default_type=None, default_category=None):
    
  
    
    ###########
    # 0) normalize
    text_norm = normalize_ocr_text(text)
    

    # 1) start the output dict early so we can safely assign to it
    parsed = {}
    if agency: parsed["agency"] = agency
    if date:   parsed["date"]   = date

    # 2) price / beds / baths (whatever you already had, 
    amount, currency = extract_price(text_norm, config)
    if amount is not None:
        parsed["price"] = amount
    if currency:
        parsed["currency"] = currency

    #bedrooms should be extracted before baths)
    parsed["bedrooms"]  = extract_bedrooms(text_norm)
    config["hint_bedrooms"] = parsed.get("bedrooms")
    parsed["bathrooms"] = extract_bathrooms(text_norm, config)


    # 3) areas (unitized) — AFTER parsed exists
    areas = extract_area(text_norm, config)
    # reset to avoid stale values
    parsed["area"] = parsed["area_unit"] = parsed.get("area_m2", None)
    parsed["area_m2"] = None
    parsed["AT"] = parsed["AT_unit"] = None
# If your schema includes these, keep them reset; otherwise this does nothing
    if "AC" in parsed: parsed["AC"] = None
    if "AC_unit" in parsed: parsed["AC_unit"] = None
    if "MZ" in parsed: parsed["MZ"] = None
    if "MZ_unit" in parsed: parsed["MZ_unit"] = None

    def _set_if_present(d, k, v):
        if k in d and d.get(k) is None:
            d[k] = v

    if isinstance(areas, dict):
    # --- NEW extractor shape (traceability): classified dicts and/or generic strings ---
     has_classified = any(isinstance(areas.get(k), dict) for k in ("AC", "AT", "MZ"))

    # AT (lot) always mapped if present
    if isinstance(areas.get("AT"), dict):
            parsed["AT"] = areas["AT"].get("value")
            parsed["AT_unit"] = areas["AT"].get("unit")

    # AC / MZ only copied if your schema has those columns
    if isinstance(areas.get("AC"), dict):
        _set_if_present(parsed, "AC", areas["AC"].get("value"))
        _set_if_present(parsed, "AC_unit", areas["AC"].get("unit"))

    if isinstance(areas.get("MZ"), dict):
        _set_if_present(parsed, "MZ", areas["MZ"].get("value"))
        _set_if_present(parsed, "MZ_unit", areas["MZ"].get("unit"))

    # Generic area only when no classified keys are present
    if not has_classified:
        if areas.get("area") is not None:
            parsed["area"] = areas.get("area")
        if areas.get("area_unit") is not None:
            parsed["area_unit"] = areas.get("area_unit")
        # traceability mode: do not compute area_m2 here

    # --- OLD extractor shape (backward-compat): single value/unit/value_m2 ---
    elif "value" in areas or "unit" in areas or "value_m2" in areas:
        # keep legacy behavior for agencies not yet migrated
        parsed["area"] = areas.get("value")
        parsed["area_unit"] = areas.get("unit")
        if "area_m2" in parsed:
            parsed["area_m2"] = areas.get("value_m2")





    # 4) neighborhood / type / transaction (inherit defaults)
    
    parsed["neighborhood"] = extract_neighborhood(text_norm, config) or ""
    ####print("before call extract neighbor :", text_norm[:40],parsed)
    try:
        parsed["neighborhood"] = extract_neighborhood(text_norm, config) or ""
         
    except TypeError:
    # --- optional currency-aware cleanup of neighborhood ---
        parsed["neighborhood"]= ""
    if config.get("neighborhood_split_on_currency", False):
        neigh, pre_price = clean_neighborhood_before_currency(text_norm, config)
        if neigh:
            parsed["neighborhood"] = neigh
        if pre_price:
            parsed["pre_price_text"] = pre_price
        print("neighborhood :", parsed["neighborhood"])

# --- property type ---

    ptype = extract_property_type(text_norm, config)

# Use extractor if it found something meaningful
    if ptype and str(ptype).strip().lower() not in ("", "other", "unknown"):
        parsed["property_type"] = ptype
# Otherwise use the header default if available
    elif default_type:
        parsed["property_type"] = default_type
# Fallback if nothing else
    else:
        parsed["property_type"] = "other"

#==========================================
# DEBUG: show inherited defaults coming in

    
#========================================

    if default_transaction:
        parsed["transaction"] = default_transaction
    if default_category:
        parsed["category"] = default_category

    # 5) title (whatever your logic is)
    parsed["title"] = parsed.get("title") or text_norm[:140]
    #==========================================
    # DEBUG: show inherited defaults coming in
    #print("return record parsed:", text_norm)
   
    return parsed

