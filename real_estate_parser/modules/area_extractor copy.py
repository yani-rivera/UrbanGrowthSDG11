# modules/area_extractor.py (traceability mode; final tuned rules)
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
            if u: units.add(u)
        for lst in (cfg.get("area_aliases") or {}).values():
            for tok in (lst or []):
                if tok: units.add(tok)
    return "|".join(re.escape(u) for u in sorted(units, key=len, reverse=True))

def _norm_unit_for_output(u: str) -> str:
    if not u: return u
    ul = u.strip()
    return "acres" if ul.lower() == "acre" else ul

def extract_area(text: str, cfg: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
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

    aliases_cfg = (cfg or {}).get("area_aliases", {})
    ac_alias = [s.lower() for s in (aliases_cfg.get("ac") or [])]
    at_alias = [s.lower() for s in (aliases_cfg.get("at") or [])]
    mz_alias = [s.lower() for s in (aliases_cfg.get("mz") or [])]

    AMBIG_M2 = {"m2", "m²"}  # always ambiguous
    STRONG_AC = set(ac_alias or ["mt2", "mts2", "mtrs2", "metros cuadrados"])
    STRONG_AC -= AMBIG_M2  # remove plain m² tokens even if config lists them
    VARAS_FAM = set(at_alias or ["vrs²","vrs2","vr2","vara2","varas2","varas cuadradas"])
    MANZANA_FAM = set(mz_alias or ["mz","manzana","manzanas"])

    AT_LABEL = re.compile(r"\bAT:\s*$", re.I)
    AC_LABEL = re.compile(r"\bAC:\s*$", re.I)
    AT_CTX   = re.compile(r"\b(terreno|parcela|solar)\b", re.I)
    # AFTER (add |casa)
    AC_CTX   = re.compile(r"\b(construcci[oó]n|construida|built|construction|casa)\b", re.I)

    m2_family_positions: List[Tuple[int,int]] = []
    has_lot_unit = False  # NEW: track whether we saw varas/manzanas

    for m in matches:
        unit_l = m.group("unit").strip().lower()
        if unit_l in (AMBIG_M2 | STRONG_AC):
            m2_family_positions.append((m.start(), m.end()))
        if unit_l in VARAS_FAM or unit_l in MANZANA_FAM:
            has_lot_unit = True

    allow_ctx_for_m2 = len(m2_family_positions) >= 2
   



    classified: Dict[str, Dict[str, Any]] = {}
    generic: Optional[Tuple[str, str]] = None



    for m in matches:
        raw_val  = m.group("num").strip()
        raw_unit = m.group("unit").strip()
        unit_l   = raw_unit.lower()
        unit_out = _norm_unit_for_output(raw_unit)

    # 1) Hard families
        if unit_l in VARAS_FAM:
            if "AT" not in classified:
                classified["AT"] = {"value": raw_val, "unit": unit_out}
            continue
        if unit_l in MANZANA_FAM:
            if "MZ" not in classified:
                classified["MZ"] = {"value": raw_val, "unit": unit_out}
            continue
        if unit_l in STRONG_AC:
            if "AC" not in classified:
                classified["AC"] = {"value": raw_val, "unit": unit_out}
            continue

    # 2) Ambiguous plain m2/m²  ⬇️  (THIS is where the new check goes)
        if unit_l in AMBIG_M2:
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

        # ✅ AC context allowed when multiple m² OR a lot unit exists
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
