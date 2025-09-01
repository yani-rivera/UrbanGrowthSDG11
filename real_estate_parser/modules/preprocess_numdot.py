
# VERSION 1

# modules/preprocess_numdot.py
from typing import Iterable, List, Tuple, Dict, Optional
import os, re

__all__ = ["detect_numdot", "masquerade_numdot", "maybe_masquerade_numdot"]

# — detection: "d." / "dd." followed by a letter or '#'
_NUMDOT_START  = re.compile(r"^(\s*)(\d{1,3})\.\s*(?=[A-Za-zÁÉÍÓÚÜÑ#])")
_INLINE_NUMDOT = re.compile(r"(?<![\d,])\b(\d{1,3})\.\s*(?=[A-Za-zÁÉÍÓÚÜÑ#])")

# — price + currency glue
_PRICE_ONLY    = re.compile(
    r""" ^
         \s* (?:US\$|\$|L\.|LPS\.?|USD|HNL)? \s*
         \d{1,3} (?:[.,]\d{3})* (?:[.,]\d{2})? \s* \.? \s*
       $ """, re.IGNORECASE | re.VERBOSE
)
_CURRENCY_TAIL = re.compile(r"(US\$|USD|DOLARES|DÓLARES|\$|LPS?\.?|HNL)\s*(?:['\"”])?\s*$",
                            re.IGNORECASE)

# — area tails / starts (m², m2, vrs, etc.)
_AREA_TAIL = re.compile(
    r"""\d{1,4}(?:[.,]\d{3})*(?:[.,]\d{1,2})?\s*(?:m2|m²|mt2|mts2|mts|vrs2|vrs²|vrs|vr2|vr|varas?)\b\s*[.,;:]?\s*$""",
    re.IGNORECASE,
)
_AREA_START = re.compile(
    r""" ^
         \s*\d{1,4}(?:[.,]\d{3})*(?:[.,]\d{1,2})?
         \s*(?:m2|m²|mt2|mts2|mts|vrs2|vrs²|vrs|vr2|vr|varas?)\b
      """, re.IGNORECASE | re.VERBOSE
)

def _coerce_lines(lines: Iterable[str]) -> List[str]:
    return [ln.rstrip("\n") for ln in lines]

def detect_numdot(lines: Iterable[str], sample: Optional[int] = None) -> Dict[str, int]:
    """Count NUMDOT at start and inline (ignores decimals like 1,200.00)."""
    L = _coerce_lines(lines)
    if sample:
        L = L[:sample]
    starts = inlines = 0
    for ln in L:
        if _NUMDOT_START.match(ln):
            starts += 1
        # count inline occurrences (excluding start)
        if _INLINE_NUMDOT.search(ln) and not _NUMDOT_START.match(ln):
            inlines += 1
    return {"lines": len(L), "numdot_starts": starts, "numdot_inline": inlines}

def masquerade_numdot(lines: Iterable[str], glue_areas: bool = True) -> List[str]:
    """Replace NUMDOT with '*' (start + inline) and glue price/area fragments."""
    out: List[str] = []
    for ln in _coerce_lines(lines):
        # glue after currency/area tails
        if out and _CURRENCY_TAIL.search(out[-1]) and _PRICE_ONLY.match(ln):
            out[-1] = f"{out[-1].rstrip()} {ln.strip()}";  continue
        if glue_areas and out and _AREA_TAIL.search(out[-1]) and not _NUMDOT_START.match(ln):
            out[-1] = f"{out[-1].rstrip()} {ln.strip()}";  continue
        if glue_areas and _AREA_START.match(ln) and out:
            out[-1] = f"{out[-1].rstrip()} {ln.strip()}";  continue
        # replace NUMDOT at start
        m = _NUMDOT_START.match(ln)
        if m:
            ln = _NUMDOT_START.sub(r"\1* ", ln)
        # replace inline NUMDOT (won’t hit decimals due to lookahead)
        ln = _INLINE_NUMDOT.sub("* ", ln)
        out.append(ln)
    return out

def maybe_masquerade_numdot(
    lines: Iterable[str],
    *,
    glue_areas: bool = True,
    auto: bool = True,
    min_hits: int = 5,
    ratio_threshold: float = 0.01,        # ≥1% of lines have NUMDOT → mask
    dump_path: Optional[str] = None,
) -> Tuple[List[str], bool]:
    """
    Auto-detect NUMDOT and apply masquerade when it looks like a real marker.
    Returns (new_lines, used_mask: bool).
    """
    L = _coerce_lines(lines)
    used = False
    if auto:
        stats = detect_numdot(L)
        hits = stats["numdot_starts"] + stats["numdot_inline"]
        ratio = (hits / max(1, stats["lines"]))
        if hits >= min_hits and ratio >= ratio_threshold:
            L = masquerade_numdot(L, glue_areas=glue_areas)
            used = True
    else:
        L = masquerade_numdot(L, glue_areas=glue_areas)
        used = True

    if used and dump_path:
        os.makedirs(os.path.dirname(dump_path), exist_ok=True)
        with open(dump_path, "w", encoding="utf-8") as tf:
            tf.write("\n".join(L) + "\n")
    return L, used
