
# modules/preprocess_freeform.py
from typing import Iterable, List, Tuple, Optional, Dict
import os, re

__all__ = ["maybe_masquerade_freeform"]

# --- generic patterns ---
PRICE = re.compile(r"(US\$|\$|LPS?\.?|L\.|USD|HNL)\s*\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})?", re.I)
AREA  = re.compile(r"\d{1,4}(?:[.,]\d{3})*(?:[.,]\d{1,2})?\s*(m2|m²|mt2|mts2|mts|vrs2|vrs²|vrs|vr2|vr)\b", re.I)
BEDS  = re.compile(r"\b(\d{1,2})\s*(hab(?:itaciones)?|dorm|cuartos?)\b", re.I)
BATHS = re.compile(r"\b(\d{1,2})(?:\s*(?:\.|,|y|/)\s*(\d))?\s*(ba(?:ños|nos)?|bano|baño)\b", re.I)
PHONE = re.compile(r"\b(?:\+?\d{2,3}[-.\s]?)?\d{4}[-.\s]?\d{4}\b")
UPPER_HEADING = re.compile(r"^[A-ZÁÉÍÓÚÜÑ][A-ZÁÉÍÓÚÜÑ\s,.'-]{8,}$")

# “inline next start”: end of sentence + Capitalized word
INLINE_CAP = re.compile(r"([.!?]\s+)(?=[A-ZÁÉÍÓÚÜÑ][a-záéíóúüñ]{2,})")

HEADER = re.compile(r"^\s*#")
PAGE_COUNTER = re.compile(r"^\s*\d{1,3}\s*[.)]?\s*$")

def _coerce(lines: Iterable[str]) -> List[str]:
    return [ln.rstrip("\n") for ln in lines]

def _score(ln: str, cfg: Dict) -> int:
    """Cheap heuristic score for 'looks like a listing start'."""
    s = 0
    if PRICE.search(ln): s += 2
    if AREA.search(ln):  s += 1
    if BEDS.search(ln):  s += 1
    if BATHS.search(ln): s += 1
    if PHONE.search(ln): s += 1
    # neighborhood prefixes from config
    for tok in cfg.get("freeform_tokens", {}).get("neighborhood_prefixes", []):
        if tok and tok.lower() in ln.lower(): s += 1; break
    # a very title-ish all-caps line
    if UPPER_HEADING.match(ln.strip()): s += 1
    # long enough & starts with Capital
    if re.match(r"^\s*[A-ZÁÉÍÓÚÜÑ]", ln): s += 1
    return s

def _attach(out: List[str], frag: str) -> None:
    if out:
        out[-1] = (out[-1].rstrip() + " " + frag.strip()).strip()
    else:
        out.append(frag)

def masquerade_freeform(lines: Iterable[str], cfg: Dict, *, threshold: int = 3) -> List[str]:
    """Insert '* ' at probable listing starts; glue obvious continuations."""
    out: List[str] = []
    L = _coerce(lines)

    for ln in L:
        if HEADER.match(ln):          # keep headers standalone
            out.append(ln); continue
        if PAGE_COUNTER.match(ln):    # ignore lonely page counters unless inside text
            _attach(out, ln); continue

        # Glue lines that are obviously continuations
        if out and out[-1].rstrip().endswith(("US$", "$", "USD", "HNL", "L.", "Lps.", "LPS.")) \
           and re.match(r"^\s*\d", ln):
            _attach(out, ln); continue
        if out and re.search(r"(m2|m²|vrs2?|vr2?)\s*[.,;:]?$", out[-1], re.I) and not ln.strip().startswith("*"):
            _attach(out, ln); continue

        # Split inline “next start”: “… . Nueva casa …”
        if out and INLINE_CAP.search(ln):
            # keep as continuation; the next line’s scoring will mark a new start if needed
            pass

        # Decide if this line is a new start
        if _score(ln, cfg) >= threshold:
            # masquerade: put a bullet in front (does not alter content beyond the prefix)
            out.append("* " + ln.lstrip())
        else:
            _attach(out, ln)

    return out

def maybe_masquerade_freeform(
    lines: Iterable[str],
    cfg: Dict,
    *,
    auto: bool = True,
    threshold: Optional[int] = None,
    min_hits: int = 5,
    dump_path: Optional[str] = None,
) -> Tuple[List[str], bool]:
    """
    Auto/force a masquerade for freeform agencies (no delimiter).
    If auto=True, we test first: if ≥ min_hits lines score as starts, we mask.
    Returns (new_lines, used_mask: bool).
    """
    L = _coerce(lines)
    used = False

    th = threshold if threshold is not None else int(cfg.get("freeform_threshold", 3))
    if auto:
        hits = sum(1 for ln in L if _score(ln, cfg) >= th)
        if hits >= min_hits:
            L = masquerade_freeform(L, cfg, threshold=th)
            used = True
    else:
        L = masquerade_freeform(L, cfg, threshold=th)
        used = True

    if used and dump_path:
        os.makedirs(os.path.dirname(dump_path), exist_ok=True)
        with open(dump_path, "w", encoding="utf-8") as f:
            f.write("\n".join(L) + "\n")

    return L, used
