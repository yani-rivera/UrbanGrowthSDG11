# agency_preprocess.py — two-phase preprocessing (split → join/sanitize)
# Public API preserved. New: preprocess_split() and preprocess_join().
from __future__ import annotations
import re
from typing import Iterable, List, Dict, Optional

import sys,os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from modules.ListingUppercaseMask import build_mask, slice_blocks_from_mask
#from modules.forcebulletv3 import bulletize_line, verify_lines
from modules.forcebullet import bulletize
from modules.SplitByCue import split_by_cue


# --------------------------------------------------------------------------------------
# Module config (overridden by configure_preprocess)
_CFG: Dict[str, object] = {
    "header_marker": "#",            # lines starting with this are section headers
    "listing_marker": "*",           # "*", "-", "NUMBERED", "UPPERCASE"
    "auto_masquerade_numdot": False,  # handled by scripts (prefile), kept for reference
    "sanitize": False,                # phase-2 only
    "glue_price_tails": True,         # phase-2: glue a price-only next line
    "glue_area_tails": False,         # optional phase-2 rule (rare)
    "start_exceptions": [],           # strings that must NOT start a listing
}

__all__ = [
    "configure_preprocess",
    "preprocess_split",
    "preprocess_join",
    "preprocess_listings",  # compatibility wrapper (phase1+phase2)
]

# --------------------------------------------------------------------------------------
# Helpers
_UP_WORD = re.compile(r"[A-ZÁÉÍÓÚÑ]", re.UNICODE)
_HAS_LOWER = re.compile(r"[a-záéíóúñ]", re.UNICODE)
_NUM_START = re.compile(r"^\s*\d{1,3}[\.)]?\s+")

_PRICE_ONLY = re.compile(
    r"^(?:US\$|\$|LPS?\.?|L\.|USD|HNL)\s*"  # currency
    r"\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})?$",  # number
    re.IGNORECASE,
)
_AREA_TAIL = re.compile(r"(m2|m²|mt2|mts2|mts|vrs2|vrs²|vrs|vr2|vr)\s*$", re.IGNORECASE)

#===========



def configure_preprocess(config: Dict[str, object]) -> None:
    """Shallow-merge agency config into module defaults."""
    if not isinstance(config, dict):
        return
    for k in list(_CFG.keys()):
        if k in config:
            _CFG[k] = config[k]
    


# --------------------------------------------------------------------------------------
# Phase 1: split to blocks
# We return a list of blocks: {"kind":"header","text":...} or {"kind":"listing","lines":[...]}

Block = Dict[str, object]


def _is_header(ln: str) -> bool:
    return ln.lstrip().startswith(str(_CFG.get("header_marker", "#")))


def _is_uppercase_title(ln: str) -> bool:
    t = (ln or "").strip()
    if not t:
        return False
    # must contain at least one uppercase letter and no lowercase letters in the leading chunk
    has_up = bool(_UP_WORD.search(t))
    has_low = bool(_HAS_LOWER.search(t.split(",")[0].split(":")[0]))
    return has_up and not has_low


# modules/agency_preprocess.py
import re

def preprocess_split(raw_lines, *, mode=None, marker=None):
    """
    Returns a list of blocks:
      {"kind": "header",  "text": "# ALQUILER DE CASAS"}
      {"kind": "listing", "lines": ["FLORENCIA NORTE, ...", "precio ..."], "marker": "*"}
    """
    out = []
    buf = []            # current listing content (marker removed)
    cur_marker = None   # "*" or "-" etc.

    def flush_listing():
        nonlocal buf, cur_marker
        if buf:
            out.append({"kind": "listing", "lines": buf, "marker": cur_marker or "*"})
             
            buf, cur_marker = [], None

    header_rx = re.compile(r"^\s*#\s*")

    

    if not mode:
        mode = "LITERAL"
    mode = str(mode).upper()

    # NUMBERED → after masquerade we read literal '*' anyway
    if mode == "NUMBERED":
        return preprocess_split(raw_lines, mode="LITERAL", marker="*")

    if mode == "UPPERCASE":
        #print("DEBUG ENTER SPLIT UPPERCASE")
        lines = list(raw_lines)  # raw_lines may be a generator
        mask = build_mask(
            lines,
            header_marker=str(_CFG.get("header_marker", "#")),
            start_exceptions=_CFG.get("start_exceptions", []),
        )
    
        return slice_blocks_from_mask(
        lines,
        mask,
        marker_visual=(marker or "*"),
        header_marker=str(_CFG.get("header_marker", "#")),
        )

    
    # LITERAL mode (explicit markers like "*", "-")
    lit = str(marker or "*").strip()
    lit_rx = re.compile(rf"^\s*{re.escape(lit)}\s+")
    for ln in raw_lines:
        # 1) headers: flush current and emit header
        if header_rx.match(ln):
            flush_listing()
            out.append({"kind": "header", "text": ln.strip()})
            continue

        # 2) listing start: line begins with the literal marker
        if lit_rx.match(ln):
            flush_listing()
            stripped = lit_rx.sub("", ln, count=1).rstrip("\n")
            cur_marker = lit
            buf = [stripped]              # ← add ONCE
            continue

        # 3) continuation: only if we are inside a listing
        if buf:
            buf.append(ln.rstrip("\n"))
        else:
            # outside any listing; ignore or buffer per your policy
            # (most newspaper OCR has no prelude; ignoring is safest)
            pass

    flush_listing()
    return out


def _starts_with_any(ln: str, items: object) -> bool:
    if not items:
        return False
    s = ln.strip().lower()
    for it in items:  # type: ignore[assignment]
        if s.startswith(str(it).lower()):
            return True
    return False


# --------------------------------------------------------------------------------------
# Phase 2: join/sanitize blocks into one-line listings

try:
    from modules.ocr_sanitize import ocr_sanitize  # if you have a central sanitizer
except Exception:  # fallback minimal
    def ocr_sanitize(x: str) -> str:  # type: ignore[override]
        return x


def preprocess_join(blocks: List[Block], *, sanitize: Optional[bool] = None,
                     glue_price_tails: Optional[bool] = None,
                     glue_area_tails: Optional[bool] = None,
                     keep_marker: Optional[bool] = None) -> List[str]:
    """
    Phase-2: join/sanitize blocks into one-line rows.
    If keep_marker/emit_marker is True, re-prefix listing rows with their original marker
    so reviewers see the same delimiter ('*', '-', etc.). Headers are passed through.
    """
    do_san = bool(_CFG.get("sanitize") if sanitize is None else sanitize)
    glue_p = bool(_CFG.get("glue_price_tails") if glue_price_tails is None else glue_price_tails)
    glue_a = bool(_CFG.get("glue_area_tails") if glue_area_tails is None else glue_area_tails)
    keep   = bool(_CFG.get("emit_marker") if keep_marker is None else keep_marker)

    out: List[str] = []

    def join_lines(lines: List[str]) -> str:
        if not lines:
            return ""
        buf: List[str] = []
        for i, ln in enumerate(lines):
            if i > 0 and glue_p and _PRICE_ONLY.match(ln.strip()) and buf:
                # price-only line glued to previous
                buf[-1] = f"{buf[-1]} {ln.strip()}"
                continue
            if i > 0 and glue_a and _AREA_TAIL.search(buf[-1]) and ln.strip():
                buf[-1] = f"{buf[-1]} {ln.strip()}"
                continue
            buf.append(ln.strip())
        j = " ".join(p for p in buf if p)
        return ocr_sanitize(j) if do_san else j

    for b in blocks:
        if b.get("kind") == "header":
            out.append(str(b.get("text", "")))
            continue

        joined = join_lines(list(map(str, b.get("lines", []))))

        # modules/agency_preprocess.py → preprocess_join(...)
        if keep:  # keep == emit_marker
             m = str(b.get("marker") or "*").strip()
             if m and not re.match(r"^\s*([*\-•])\s+\S", joined):
                joined = f"{m} {joined}".lstrip()
        
        out.append(joined)

    return out



# --------------------------------------------------------------------------------------
# Compatibility wrapper: phase1 + phase2 in one call (what scripts already use)

def preprocess_listings(raw_lines: Iterable[str], marker: Optional[str] = None,
                        agency: Optional[str] = None) -> List[str]:
    # map marker into a phase-1 mode
     
    m = str(marker or _CFG.get("listing_marker", "*")).upper()
    mu=_CFG.get("listing_marker", "*").upper()
    marker = _CFG.get("listing_marker")
    marker_s = (marker or "").strip()
     
    mode: Optional[str]
    lit: Optional[str] = None
    

       # ----- CUE path: collapse with SplitByCue, DO NOT call preprocess_join -----
    if marker_s.upper().startswith("CUE:"):
    # Example: "CUE:COMMA" | "CUE:DOT" | "CUE:regex:..."
        #print("calling split by cue")
        rows = split_by_cue(raw_lines, _CFG)
        return rows
    else:

        if m in {"NUMBERED", "#NUM", "#NUMDOT"}:
            mode = "NUMBERED"
        elif m == "UPPERCASE":
            
            mode = "UPPERCASE"
       
        else:
            mode = "LITERAL"; lit = marker or str(_CFG.get("listing_marker", "*"))
             
        blocks = preprocess_split(raw_lines, mode=mode, marker=lit)
        rows = preprocess_join(blocks)
    # Ensuere that everylisting have an "*" start
    #rows = bulletize(((l) for l in rows),_CFG )

    return rows


