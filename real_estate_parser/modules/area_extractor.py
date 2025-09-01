# modules/area_extractor.py (traceability mode with unit-token normalization)
import re
from typing import Optional, Dict, Any, Tuple, List

_DEFAULT_AREA_UNITS: List[str] = [
    "m²", "m2", "mt2", "mts2", "mtrs2", "metros cuadrados",
    "vrs²", "vrs2", "vr2", "vara2", "varas2", "varas cuadradas",
    "mz", "manzana", "manzanas",
    "ft²", "ft2", "sqft", "acre", "acres",
]

def _unit_pattern(cfg: Optional[Dict[str, Any]]) -> str:
    units = set(_DEFAULT_AREA_UNITS)
    if cfg:
        for u in (cfg.get("area_units") or []):
            if u:
                units.add(u)
        for lst in (cfg.get("area_aliases") or {}).values():
            for tok in (lst or []):
                if tok:
                    units.add(tok)
    return "|".join(re.escape(u) for u in sorted(units, key=len, reverse=True))

def _norm_unit_for_output(u: str) -> str:
    if not u: return u
    ul = u.strip()
    return "acres" if ul.lower() == "acre" else ul

# NEW: normalize tokens for classification (not for output)
_SPACES_DOTS_HYPHENS_UNDERSCORES = re.compile(r"[ \.\-_]+")
def _norm_unit_token(u: str) -> str:
    """
    Normalize a unit token for set-membership comparison.
    Examples:
      'Vrs²' -> 'vrs2'
      'vrs ²' -> 'vrs2'
      'm²'    -> 'm2'
      'metros cuadrados' -> 'metroscuadrados'
    """
    if not u:
        return ""
    u = u.strip().lower()
    u = u.replace("²", "2")
    u = _SPACES_DOTS_HYPHENS_UNDERSCORES.sub("", u)
    return u

def extract_area(text: str, cfg: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    TRACEABILITY:
      - Keeps raw number string and raw unit token (except 'acre' -> 'acres' string tweak).
      - Classification:
          * VARAS family -> AT
          * MANZANA family -> MZ
          * STRONG m² tokens (mt2/mts2/mtrs2/metros cuadrados) -> AC
          * Plain m2/m² -> ambiguous:
              - label 'AT:' / 'AC:' wins
              - AT context (terreno/parcela/solar) always allowed (even single)
              - AC context (construcción/construida/built/construction/casa) allowed if
                multiple m² values OR a lot unit (varas/manzanas) exists elsewhere
          * sqft/ft2/acres -> generic
      - If any classified exists, generic 'area' is not set.
    """
    out: Dict[str, Any] = {"area": None, "area_unit": None}
    if not text:
        return out

    unit_pat = _unit_pattern(cfg)
    AREA_RX = re.compile(
        rf"(?P<num>\d[\d.,\u00A0 ]*)\s*(?P<unit>{unit_pat})(?=$|\s|[.,;:)\]-])",
        re.I | re.UNICODE,
    )
    matches = list(AREA_RX.finditer(text))
    if not matches:
        return out

    # Build families from config and normalize tokens for classification
    aliases_cfg = (cfg or {}).get("area_aliases", {})
    ac_alias_raw = (aliases_cfg.get("ac") or [])
    at_alias_raw = (aliases_cfg.get("at") or [])
    mz_alias_raw = (aliases_cfg.get("mz") or [])

    # Ambiguous plain m2 always ambiguous even if listed in AC
    AMBIG_M2 = {"m2", "m²"}
    AMBIG_M2_N = {_norm_unit_token(x) for x in AMBIG_M2}  # {'m2'} effectively

    STRONG_AC = set(a.lower() for a in (ac_alias_raw or ["mt2", "mts2", "mtrs2", "metros cuadrados"]))
    # Remove ambiguous tokens from strong AC, then normalize
    STRONG_AC = {_norm_unit_token(x) for x in STRONG_AC if x not in AMBIG_M2}
    VARAS_FAM = {_norm_unit_token(x) for x in (at_alias_raw or ["vrs²","vrs2","vr2","vara2","varas2","varas cuadradas"])}
    MANZANA_FAM = {_norm_unit_token(x) for x in (mz_alias_raw or ["mz","manzana","manzanas"])}

    # Context regex
    AT_LABEL = re.compile(r"\bAT:\s*$", re.I)
    AC_LABEL = re.compile(r"\bAC:\s*$", re.I)
    AT_CTX   = re.compile(r"\b(terreno|parcela|solar)\b", re.I)  # NOTE: 'lote' intentionally excluded
    AC_CTX   = re.compile(r"\b(construcci[oó]n|construida|built|construction|casa)\b", re.I)

    # Pre-scan to decide AC gating and detect presence of lot units
    m2_family_positions: List[Tuple[int,int]] = []
    has_lot_unit = False
    for m in matches:
        unit_n = _norm_unit_token(m.group("unit"))
        if unit_n in STRONG_AC or unit_n in AMBIG_M2_N:
            m2_family_positions.append((m.start(), m.end()))
        if unit_n in VARAS_FAM or unit_n in MANZANA_FAM:
            has_lot_unit = True
    allow_ctx_for_m2 = len(m2_family_positions) >= 2

    classified: Dict[str, Dict[str, Any]] = {}
    generic: Optional[Tuple[str, str]] = None

    for m in matches:
        raw_val  = m.group("num").strip()
        raw_unit = m.group("unit").strip()
        unit_out = _norm_unit_for_output(raw_unit)  # for display
        unit_n   = _norm_unit_token(raw_unit)       # for classification

        # 1) Hard families
        if unit_n in VARAS_FAM:
            if "AT" not in classified:
                classified["AT"] = {"value": raw_val, "unit": unit_out}
            continue
        if unit_n in MANZANA_FAM:
            if "MZ" not in classified:
                classified["MZ"] = {"value": raw_val, "unit": unit_out}
            continue
        if unit_n in STRONG_AC:
            if "AC" not in classified:
                classified["AC"] = {"value": raw_val, "unit": unit_out}
            continue

        # 2) Ambiguous plain m2/m²
        if unit_n in AMBIG_M2_N:
            left = text[max(0, m.start()-6): m.start()]
            if AT_LABEL.search(left):
                if "AT" not in classified:
                    classified["AT"] = {"value": raw_val, "unit": unit_out}
                continue
            if AC_LABEL.search(left):
                if "AC" not in classified:
                    classified["AC"] = {"value": raw_val, "unit": unit_out}
                continue

            # AT context always allowed (even single m²)
            ctx = text[max(0, m.start()-18): m.end()+18]
            if AT_CTX.search(ctx):
                if "AT" not in classified:
                    classified["AT"] = {"value": raw_val, "unit": unit_out}
                continue

            # AC context allowed if multiple m² or lot unit elsewhere
            if (allow_ctx_for_m2 or has_lot_unit) and AC_CTX.search(ctx):
                if "AC" not in classified:
                    classified["AC"] = {"value": raw_val, "unit": unit_out}
                continue

            # Otherwise generic (first only)
            if generic is None:
                generic = (raw_val, unit_out)
            continue

        # 3) Everything else → generic (first only)
        if generic is None:
            generic = (raw_val, unit_out)

    if classified:
        out.update(classified)
        return out

    if generic:
        out["area"], out["area_unit"] = generic
    return out
