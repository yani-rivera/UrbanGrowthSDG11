
## Version 3 GOSTO 26, 2025
# modules/mask_numdot.py
import re
from typing import Iterable, List, Optional

# headers we must not touch
_DEFAULT_HEADER_GUARDS = ("VENTA", "ALQUILER")

def _is_header(line: str, header_prefix: Optional[str], guards=_DEFAULT_HEADER_GUARDS) -> bool:
    if not line:
        return False
    s = line.lstrip()
    if header_prefix and s.startswith(header_prefix):
        return True
    sU = s.upper()
    return any(g in sU for g in guards)

# Robust BOF token:
#   1.a   | 12.a | 3) a | 12.- b | 7 . c - | 12a  | 12 .a
# Captures number, optional punctuation, optional letter (glued or spaced), optional trailing punct.
_NUM_LETTER_TOKEN = re.compile(
    r"""
    ^\s*
    (?P<num>\d{1,3})
    (?:                               # either:
        [\.\-)]\s*                    #   number + dot/dash/paren
        (?P<let1>[A-Za-z])?           #   optional letter (glued or after spaces)
      |                               # or:
        (?P<let2>[A-Za-z])            #   number + directly glued letter (e.g., "12a")
    )?
    (?:\s*[\.\-)]\s*)?                # optional trailing punctuation
    (?:-\s*)?                         # stray trailing dash (OCR "12.-")
    """,
    re.VERBOSE,
)

_SPACE = re.compile(r"\s+")

def mask_numdot(line: str, *, keep_marker: bool = False, header_prefix: Optional[str] = "#") -> str:
    """
    Remove (or normalize) a leading numbered/lettered bullet at BOF.
    Examples removed at start: '12.a', '3) b', '12.- c', '12a'
    Headers (e.g., '# VENTA ...', 'ALQUILER ...') are left intact.
    """
    if not line:
        return ""
    if _is_header(line, header_prefix):
        return _SPACE.sub(" ", line).strip()

    m = _NUM_LETTER_TOKEN.match(line)
    if not m:
        return _SPACE.sub(" ", line).strip()

    if keep_marker:
        # keep the token but normalize spacing (QA mode)
        tok = _SPACE.sub(" ", m.group(0)).strip()
        rest = _SPACE.sub(" ", line[m.end():]).strip()
        return (tok + " " + rest).strip()

    # strip the token (release mode)
    rest = _SPACE.sub(" ", line[m.end():]).strip()
    return rest

def apply_mask_numdot(listings: Iterable[str], *, keep_marker: bool = False, header_prefix: Optional[str] = "#") -> List[str]:
    return [mask_numdot(ln, keep_marker=keep_marker, header_prefix=header_prefix) for ln in listings]
