# modules/ListingUppercaseMask.py
from __future__ import annotations
import re
from typing import Iterable, List, Dict, Sequence, Optional

# --- Debug (optional) ---------------------------------------------------------
DEBUG_MASK_SUMMARY = False
DEBUG_EXCEPTIONS   = False

# --- Unicode-friendly classes (Spanish included) ------------------------------
_UP = r"A-ZÁÉÍÓÚÜÑ"
_LO = r"a-záéíóúüñ"

# Split leading "title chunk" at first ., or , or :
_LEAD_BREAK = re.compile(r"[.,:]", re.UNICODE)
# Strip leading bullets like "* ", "- ", "• "
_BULLET_LEAD_RE = re.compile(r"^\s*([*\-•])\s*")

# Inline ALL-CAPS title ending with a dot (optional helper for run-ons)
_TITLE_DOT_RE = re.compile(rf"\b([{_UP}]+(?:\s+[{_UP}]+)*)\.", re.UNICODE)


# --- helpers ------------------------------------------------------------------
def _strip_bullet(s: str) -> str:
    return _BULLET_LEAD_RE.sub("", s or "")

def _leading_chunk(s: str) -> str:
    """Return substring from start up to the first ., , : (or whole line if none)."""
    s = (s or "").strip()
    if not s:
        return ""
    m = _LEAD_BREAK.search(s)
    return s if not m else s[:m.start()]

def _norm_phrase(s: str) -> str:
    """Uppercase, trim punctuation, collapse spaces."""
    t = (s or "").strip(" .,:;").upper()
    return re.sub(r"\s+", " ", t)

def _has_upper_no_lower(s: str) -> bool:
    return bool(re.search(f"[{_UP}]", s)) and not bool(re.search(f"[{_LO}]", s))

def is_header(line: str, header_marker: str = "#") -> bool:
    line = _strip_bullet(line)
    return (line or "").lstrip().startswith(header_marker)


# --- public API ----------------------------------------------------------------
def is_uppercase_start(line: str, *, exceptions: set[str]) -> bool:
    """
    A line starts a listing IFF its LEADING CHUNK (before ., , :) has ≥1 uppercase,
    no lowercase, and the normalized chunk is NOT in exceptions.
    (Runs once per line; strips any leading bullet before evaluation.)
    """
    line  = _strip_bullet(line)
    chunk = _leading_chunk(line)
    if not chunk:
        return False

    norm = _norm_phrase(chunk)
    if norm in exceptions:
        if DEBUG_EXCEPTIONS:
            print(f"[EXC] skip start: '{chunk}' → '{norm}'")
        return False

    return _has_upper_no_lower(chunk)


def build_mask(
    raw_lines: Iterable[str],
    *,
    header_marker: str = "#",
    start_exceptions: Optional[Iterable[str]] = None,
) -> Dict[str, List[bool]]:
    """
    Produce aligned boolean masks:
      headers[i] = line i is a header (#...)
      starts[i]  = line i starts a new listing (chunk-based uppercase rule, minus exceptions)

    Order:
      1) header check
      2) chunk = leading text before ., , :
      3) exception check on chunk (exact phrase match after normalization)
      4) uppercase-start test on chunk
      5) demotion: if line i is a start and its chunk had NO terminator (. , :),
         and line i+1 also qualifies as an uppercase start, demote i+1 to continuation.
    """
    # materialize & de-bullet once (accept generators safely)
    lines: List[str] = [_strip_bullet(ln) for ln in list(raw_lines)]

    n = len(lines)
    headers: List[bool] = [False] * n
    starts:  List[bool] = [False] * n
    exc = {_norm_phrase(x) for x in (start_exceptions or [])}

    # pass 1: headers & starts (one decision per line)
    for i, ln in enumerate(lines):
        if (ln or "").lstrip().startswith(header_marker):
            headers[i] = True
            continue

        chunk = _leading_chunk(ln)
        if not chunk:
            continue

        norm = _norm_phrase(chunk)
        if norm in exc:
            continue

        if _has_upper_no_lower(chunk):
            starts[i] = True

    # pass 2: demotion for broken titles split across lines
    for i in range(n - 1):
        if headers[i] or not starts[i] or headers[i + 1]:
            continue

        # did the chunk end with terminator in line i?
        # (if there's a break char anywhere, chunk had a terminator)
        chunk_i = _leading_chunk(lines[i])
        has_break = bool(_LEAD_BREAK.search(lines[i]))
        if has_break:
            continue

        # next line also looks like an uppercase start by the same rule?
        if is_uppercase_start(lines[i + 1], exceptions=exc):
            starts[i + 1] = False  # demote next to continuation

    if DEBUG_MASK_SUMMARY:
        print(f"[MASK] lines={n} headers={sum(headers)} starts={sum(starts)} exc={len(exc)}")

    return {"headers": headers, "starts": starts}


def slice_blocks_from_mask(
    raw_lines: Sequence[str],
    mask: Dict[str, List[bool]],
    *,
    marker_visual: str = "*",
    header_marker: str = "#",
) -> List[Dict[str, object]]:
    """
    Turn masks into blocks your pipeline expects:
      {"kind":"header","text": ...}
      {"kind":"listing","lines":[...], "marker":"*"}
    """
    out: List[Dict[str, object]] = []
    buf: List[str] = []

    def flush():
        nonlocal buf
        if buf:
            out.append({"kind": "listing", "lines": buf, "marker": marker_visual})
            buf = []

    lines: List[str] = list(raw_lines)  # keep original text for content
    for i, ln in enumerate(lines):
        if mask["headers"][i]:
            flush()
            out.append({"kind": "header", "text": ln.strip()})
            continue
        if mask["starts"][i]:
            flush()
            buf = [ln.rstrip("\n")]
            continue
        if buf:
            buf.append(ln.rstrip("\n"))
        else:
            # ignore prelude noise
            pass

    flush()
    return out


# Optional helper if you later want to split run-on single-line listings:
def split_inline_titles(
    text: str,
    *,
    title_excludes: Optional[Iterable[str]] = None
) -> List[str]:
    """
    Split a long line at subsequent ALL-CAPS titles ending with '.',
    excluding phrases in `title_excludes`. First title remains at the start.
    Not required for core flow; provided for agencies that need run-on fixes.
    """
    s = (text or "").strip()
    if not s:
        return [s]
    matches = list(_TITLE_DOT_RE.finditer(s))
    if len(matches) <= 1:
        return [s]
    excl = {_norm_phrase(x) for x in (title_excludes or [])}
    cuts: List[int] = []
    for idx, m in enumerate(matches):
        if idx == 0:
            continue
        phrase = _norm_phrase(m.group(1))
        if phrase in excl:
            continue
        cuts.append(m.start())
    if not cuts:
        return [s]
    parts: List[str] = []
    prev = 0
    for c in cuts:
        parts.append(s[prev:c].strip()); prev = c
    parts.append(s[prev:].strip())
    return [p for p in parts if p]
