# modules/agency_preprocess.py
# ---------------------------------------------------------------------
# Unified listing preprocessing for multiple agencies.
# Produces ONE consolidated string per listing while preserving
# section headers as standalone lines for downstream context detection.
#
# Versioning
__version__ = "2.0.1"
__changelog__ = """
v2.0.0
 - Unified strategies: literal markers (e.g., '-', '*') and numbered bullets (#NUM)
 - Robust number formats: '1.', '2)', '3:-', '12.-', '5 -', '7—', '9/' etc.
 - Sanitization pass: Unicode normalize, common OCR fixes, spacing cleanup
 - Preserves section headers as standalone records
 - Backward-compatible signature: preprocess_listings(raw_lines, marker=None, agency=None)
"""

import re
import unicodedata
from typing import Iterable, List, Optional

# -------------------------
# Core normalization helpers
# -------------------------

def _norm_unicode(s: str) -> str:
    """Unicode normalize and strip trailing newlines (keeps inner spaces)."""
    return unicodedata.normalize("NFKC", (s or "")).rstrip("\n")

def _collapse_spaces(s: str) -> str:
    """Collapse all whitespace runs to a single space; trim edges."""
    return re.sub(r"\s+", " ", s).strip()

def _one_line(s: str) -> str:
    """Unified one-liner: normalize + collapse spacing."""
    return _collapse_spaces(_norm_unicode(s))

# -------------------------
# OCR sanitize (lightweight)
# -------------------------

def ocr_sanitize(text: str) -> str:
    """
    Light OCR cleanup. Keep this conservative; deep fixes should live in parsing stage.
    """
    if not text:
        return ""
    s = _norm_unicode(text)
    print("after unicode: ",s)

    # common OCR artifacts / encoding issues
    fixes = [
        # currency spacing
        (r"\$\.", "$ "),
        (r"(Lps?|L)\.(\d)", r"\1. \2"),
        (r"US\$(\d)", r"US$ \1"),

        # quotes & soft hyphen
        ("\u2018", "'"), ("\u2019", "'"),
        ("\u201C", '"'), ("\u201D", '"'),
        ("\u00AD", ""),

        # bathrooms variations
        (r"\bbafios\b", "baños"),
        (r"\bbaf̃os\b", "baños"),
        (r"\bbano\b", "baño"),
        (r"\bbano(s)?\b", r"baño\1"),

        # mis-decoded accents seen often
        ("Monse\\xF1or", "Monseñor"),
        ("Monsenor", "Monseñor"),

        # area units normalization (kept simple here)
        (r"\b(mts?2|mt2|m2)\b", "m²"),
        (r"\b(vr2|vrs2|v2)\b", "vrs²"),
    ]

    for a, b in fixes:
        if a.startswith(r"\b") or any(ch in a for ch in ".*+?()[]|\\"):
            s = re.sub(a, b, s, flags=re.IGNORECASE)
        else:
            s = s.replace(a, b)

    # Ensure a space after currency sign for easier price extraction
    s = re.sub(r"(\$)(\d)", r"\1 \2", s)
    s = re.sub(r"(Lps?\.?|US\$)(\s*)(\d)", r"\1 \3", s, flags=re.IGNORECASE)

    return _collapse_spaces(s)

# -------------------------
# Header detection (kept minimal)
# -------------------------

_HEADER_HINTS = ("ALQUILER", "VENTA", "COMERCIAL", "BODEGA", "TERRENO", "APART", "CASA")

def _looks_like_header(line: str) -> bool:
    """
    Heuristic: short-ish, uppercase-ish line containing key tokens and not a bullet.
    We PRESERVE these lines as standalone records so the parser can update context.
    """
    if not line:
        return False
    t = (line or "").strip()
    if t.startswith("-") or t.startswith("*"):
        return False
    up = t.upper()
    if 5 <= len(up) <= 100 and up == t and any(k in up for k in _HEADER_HINTS):
        return True
    # also treat lines that begin with a leading '#' as headers
    if t.startswith("#") and any(k in up for k in _HEADER_HINTS):
        return True
    return False

# -------------------------
# Numbered listings splitter (Casabianca & similar)
# -------------------------

# Accepts: 1.  2)  3:-  12.-  5 -  7—  9/  (and minor variants)
_NUM_BULLET = re.compile(r"^\s*\d{1,4}\s*([)\.:\-\/—–]|-\s|\.\-)\s*")

def _split_numbered_listings(lines: Iterable[str]) -> List[str]:
    blocks: List[str] = []
    cur: List[str] = []

    for raw in lines:
        ln = _norm_unicode(raw)

        # Headers: flush current and keep header as its own record
        if _looks_like_header(ln):
            if cur:
                blocks.append(_one_line(" ".join(cur)))
                cur = []
            blocks.append(_one_line(ln))
            continue

        # New numbered listing?
        if _NUM_BULLET.match(ln):
            if cur:
                blocks.append(_one_line(" ".join(cur)))
                cur = []
            # strip numeric bullet
            ln = _NUM_BULLET.sub("", ln, count=1)

        if ln.strip():
            cur.append(ocr_sanitize(ln.strip()))

    if cur:
        blocks.append(_one_line(" ".join(cur)))

    # drop empties
    return [b for b in blocks if b]

# -------------------------
# Literal marker splitter ('-', '*', '>' etc.)
# -------------------------

def _split_literal_marker(lines: Iterable[str], marker: str) -> List[str]:
    marker = (marker or "").strip()
    blocks: List[str] = []
    cur: List[str] = []

    for raw in lines:
        ln = _norm_unicode(raw)

        # Preserve headers as standalone records
        if _looks_like_header(ln):
            if cur:
                blocks.append(_one_line(" ".join(cur)))
                cur = []
            blocks.append(_one_line(ln))
            continue

        if marker and ln.strip().startswith(marker):
            if cur:
                blocks.append(_one_line(" ".join(cur)))
                cur = []
            # remove the literal marker once
            ln = ln.strip()[len(marker):].lstrip()

        if ln.strip():
            cur.append(ocr_sanitize(ln.strip()))

    if cur:
        blocks.append(_one_line(" ".join(cur)))

    return [b for b in blocks if b]

# -------------------------
# Public API
# -------------------------

def preprocess_listings(
    raw_lines: Iterable[str],
    marker: Optional[str] = None,
    agency: Optional[str] = None,
) -> List[str]:
    """
    Unifies preprocessing strategies:
      - Numbered bullets (marker '#NUM' or agency == 'Casabianca')
      - Literal marker lines (e.g., '-', '*', '>')
    Preserves section headers as separate lines.
    """
    # normalize input early (keep per-line granularity)
    lines = [(_norm_unicode(x)) for x in (raw_lines or [])]

    # Strategy: numbered agencies (Casabianca & any config that sets "#NUM")
    if (marker or "").upper() == "#NUM" or (agency or "").strip().lower() == "casabianca":
        return _split_numbered_listings(lines)

    # Strategy: literal marker (default for Eugenia '-', Serpecal '*', etc.)
    if marker:
        return _split_literal_marker(lines, marker=marker)

    # Fallback: if no marker provided, try numbered first, then literal '-'
    # This keeps backward compatibility for older configs that forgot the marker.
    guess = _split_numbered_listings(lines)
    if len(guess) > 1:
        return guess
    return _split_literal_marker(lines, marker="-")

# --- Backward-compat shim for older scripts/modules ---
def preprocess(raw_lines, marker=None, agency=None):
    """
    DEPRECATED: use preprocess_listings(...)
    Kept for backward compatibility with older parsers.
    """
    return preprocess_listings(raw_lines, marker=marker, agency=agency)

