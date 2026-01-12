#!/usr/bin/env python3
"""
SplitByCue_v2.8 20250920 =>cue decoded
---------------
Robust splitter for agency TXT feeds using a cue character (default comma) to
identify record starts, with safeguards for:
  - UTF-8 (BOM-safe) reading only
  - "first-letter uppercase" start gate (not ALL-caps required)
  - ignore numeric-grouping commas ("$1,500") as cue at start of line
  - glue continuation lines when previous ends with comma/semicolon
  - force-glue lines that begin with a price/number
  - optional inline (same-line) multi-record splitting with price-before check
  - per-agency NOT_START_WORDS to avoid false starts (e.g., RES., COND., TORRE)

Outputs one record per line by default (plain text). Can also emit CSV with
--csv if desired (single "record" column).
"""
from __future__ import annotations

import argparse
import io
import re
import sys
from pathlib import Path
import json
from typing import Iterable, List, Sequence, Dict, Any
from collections import deque
 

# ------------------------------- Defaults ------------------------------------
DEFAULT_CUE = ","
DEFAULT_MAX_CUE_POS = 25
DEFAULT_REQUIRE_UPPER = True
DEFAULT_REQUIRE_PRICE_BEFORE = True
DEFAULT_INLINE_PRICE_LOOKBACK = 50
DEFAULT_TRAILING_COMMA_GLUE = True
DEFAULT_NOT_START_WORDS = [
    "RES","RES.","RESIDENCIAL","COND","COND.","CONDOMINIO",
    "TORRE","EDIF","EDIF.","EDIFICIO","KM","KILOMETRO","KILÓMETRO",
    "CARRETERA","BARRIO","COL","COL.","COLONIA","URB","URB.",
    "URBANIZACION","URBANIZACIÓN","MZA","MANZANA","LOTE",
    "BLOQUE","PAS","PAS.","PASAJE","BO","BO."
]

# --------------------------------- Regex -------------------------------------
ALPHA_CHARS = "A-Za-zÁÉÍÓÚÜÑáéíóúüñ"
LETTER_PRESENT_RE = re.compile(rf"[{ALPHA_CHARS}]")
FIRST_ALPHA_TOKEN_RE = re.compile(rf"([{ALPHA_CHARS}][\w\.-ÁÉÍÓÚÜÑáéíóúüñ]*)")
PRICE_AT_START_RE = re.compile(
    r"^\s*(?:[$¢L]|Lps\.?|L\.?)?\s*\d{1,3}(?:,\d{3})*(?:\.\d+)?\b",
    re.IGNORECASE,
)
PRICE_ANYWHERE_RE = re.compile(
    r"(?:[$¢L]|Lps\.?|L\.?)?\s*\d{1,3}(?:,\d{3})*(?:\.\d+)?\b",
    re.IGNORECASE,
)
CONNECTOR_START_RE = re.compile(r"^\s*(y|e|con|incluye|cerca de|sobre|entre)\b", re.IGNORECASE)
TRAILING_COMMA_RE = re.compile(r"[;,]\s*$")

# --------------------------------- IO ----------------------------------------

def read_lines_utf8_sig(path: str) -> List[str]:
    with io.open(path, "r", encoding="utf-8-sig", newline=None) as f:
        return f.readlines()

# ------------------------------ Heuristics -----------------------------------

import re

# $ 1,200.00  |  Lps. 1,200  |  L 1,200 — tweak if you have others
_PRICE_RE = re.compile(r'(?:\$|Lps\.?|L)\s*\d{1,3}(?:[.,]\d{3})*(?:[.,]\d+)?', re.UNICODE)

# Heads like "Col. Marichal:", "Res. Las Uvas:", or generic Title Case "El Hatillo:"
_HEAD_COLON_RE = re.compile(
    r'(?P<head>(?:Col\.|Res\.|Bo\.|Urb\.)\s+[A-ZÁÉÍÓÚÑ][^:]{1,50}|[A-ZÁÉÍÓÚÑ][^:]{2,50})\s*:',
    re.UNICODE
)

def _split_on_colon_after_price(line: str, cue: str) -> list[str]:
    """If a Title-like '...:' appears after a price in this line, split there."""
    # Only applies when this agency’s cue is colon
    if cue != ":":
        return [line.strip()]
    s = line.strip()
    pieces: list[str] = []
    cut = 0
    pos = 0
    while True:
        m = _HEAD_COLON_RE.search(s, pos)
        if not m:
            break
        head_start = m.start()
        # Has a price between last cut and this head?
        if _PRICE_RE.search(s[cut:head_start]):
            prev = s[cut:head_start].strip()
            if prev:
                pieces.append(prev)
            cut = head_start  # start new listing at the head (keeps its ':')
            pos = m.end()
        else:
            pos = m.end()
    tail = s[cut:].strip()
    if tail:
        pieces.append(tail)
    return pieces






 #----------

def decode_cue(cue: str) -> str:
    """
    Decode a cue name into its corresponding character.

    Supported mappings:
      CUE:DOT       -> "."
      CUE:COMMA     -> ","
      CUE:SEMICOLON -> ";"
      CUE:COLON     -> ":"

    If cue is already one of the characters (".", ",", ";", ":"),
    it is returned unchanged.

    Raises ValueError if cue is not recognized.
    """
    if not cue:
        raise ValueError("Cue cannot be empty")

    # Direct characters are allowed
    if cue in {".", ",", ";", ":"}:
        return cue

    # Normalize case
    cue_norm = cue.strip().upper()

    mapping = {
        "CUE:DOT": ".",
        "CUE:COMMA": ",",
        "CUE:SEMICOLON": ";",
        "CUE:COLON": ":",
    }

    if cue_norm in mapping:
        return mapping[cue_norm]

    raise ValueError(f"Unknown cue: {cue}")

def _ensure_char_cue(cue: str) -> str:
    """Accept 'CUE:COLON'/'CUE:COMMA'/... or a single char and return ':', ',', ';', or '.'."""
    if isinstance(cue, str) and len(cue) == 1:
        return cue
    m = {
        "CUE:COLON": ":",
        "CUE:SEMICOLON": ";",
        "CUE:COMMA": ",",
        "CUE:DOT": ".",
    }
    return m.get(str(cue).upper(), str(cue))  # fallback = pass-through


def first_alpha_token(text: str) -> str:
    m = FIRST_ALPHA_TOKEN_RE.search(text)
    return m.group(1) if m else ""


def passes_upper_gate(head: str, require_upper: bool) -> bool:
    if not require_upper:
        return True
    tok = first_alpha_token(head)
    return bool(tok) and tok[0].isupper()


def token_before_cue(head: str) -> str:
    tok = re.split(r"\s+", head.strip())[0] if head.strip() else ""
    norm = re.sub(rf"[^\w\.{ALPHA_CHARS}]", "", tok)
    return norm.upper()


def is_forbidden_start(head: str, not_start_words: Sequence[str]) -> bool:
    tok = token_before_cue(head)
    return tok in {w.upper() for w in not_start_words}


def starts_with_price(line: str) -> bool:
    return bool(PRICE_AT_START_RE.match(line))



def strong_start(line: str, *, cue: str, max_cue_pos: int, require_upper: bool, not_start_words: Sequence[str]) -> bool:
    if starts_with_price(line):
        return False
    return looks_like_start(line, cue=cue, max_cue_pos=max_cue_pos, require_upper=require_upper, not_start_words=not_start_words)


PRICE_RE = re.compile(r'(?:\$|Lps\.?|L)\s*\d{1,3}(?:[.,]\d{3})*(?:[.,]\d+)?', re.UNICODE)
LETTER_RE = re.compile(r'[A-Za-zÁÉÍÓÚÑáéíóúñ]', re.UNICODE)
ABBREV_DOT_BLOCK = ("Col.", "Res.", "Av.", "Blvd.", "Km.", "No.", "Urb.", "Bo.", "Sta.", "St.", "Dr.", "Ing.")

def _pre_split_colon_after_price(line: str, cue: str) -> List[str]:
    """Call your existing _split_on_colon_after_price if present; else no-op."""
    fn = globals().get("_split_on_colon_after_price")
    if callable(fn):
        pieces = fn(line, cue)
        if pieces:
            return pieces
    return [line]

def _flush(accum_parts: List[str], out: List[str]) -> None:
    if accum_parts:
        s = re.sub(r"\s+", " ", " ".join(accum_parts)).strip().rstrip(",;")
        if s:
            out.append(s)
        accum_parts.clear()

def _force_start_colon_semicolon(line: str, cue: str, max_cue_pos: int) -> bool:
    p = line.find(cue)
    return (p != -1 and p <= max_cue_pos)

def _force_start_comma(line: str, max_cue_pos: int) -> bool:
    # 1) early comma
    p = line.find(",")
    if p == -1 or p > max_cue_pos:
        return False
    # 2) not numeric comma (avoid thousands)
    if (p > 0 and line[p-1].isdigit()) or (p+1 < len(line) and line[p+1].isdigit()):
        return False
    # 3) head looks like a place
    head = line[:p]
    if not LETTER_RE.search(head):
        return False
    # 4) price soon after the comma (within ~40 chars)
    tail = line[p+1:p+1+40]
    if not PRICE_RE.search(tail):
        return False
    return True

def _force_start_dot(line: str, max_cue_pos: int) -> bool:
    # Very conservative dot start
    p = line.find(".")
    if p == -1 or p > max_cue_pos:
        return False
    # avoid decimals like 1,200.00 or 1200.00
    if (p > 0 and line[p-1].isdigit()) or (p+1 < len(line) and line[p+1].isdigit()):
        return False
    head = line[:p].strip()
    # avoid common abbreviations ending exactly at the dot
    if any(head.endswith(abbrev[:-1]) or head.endswith(abbrev) for abbrev in ABBREV_DOT_BLOCK):
        return False
    # either next token starts uppercase OR a price shows quickly
    tail = line[p+1:].lstrip()
    return (tail[:1].isupper() or PRICE_RE.search(tail[:40]) is not None)

# -------------------- A) colon/semicolon agencies ----------------------------

def split_by_colon_semicolon(
    lines: Iterable[str],
    *,
    cue: str,
    max_cue_pos: int = 32,
    staging_window: int = 1,
) -> List[str]:
    """
    One-listing-per-line for ':' or ';' agencies.
    - Header-first (lines containing '#...'): always flush, always emit verbatim (strip only EOLs), set context elsewhere.
    - Force-start when cue is within max_cue_pos.
    - Optional same-line guardrail: pre-split when another Head: appears after a price.
    """
    out: List[str] = []
    accum_parts: List[str] = []
    staging: deque[str] = deque()  # N-line look-ahead; N=1 by default

    for raw in lines:
        line = raw.rstrip("\r\n").replace("\u00A0", " ")

        # HEADER FIRST (anywhere in line)
        hp = line.find("#")
        if hp != -1:
            left = line[:hp].rstrip()
            header = line[hp:]  # verbatim
            if left:
                # treat left as continuation then flush
                staging.append(left.strip())
                while staging:
                    accum_parts.append(staging.popleft())
                _flush(accum_parts, out)
            else:
                # header at col 0
                while staging:
                    accum_parts.append(staging.popleft())
                _flush(accum_parts, out)
            out.append(header)   # ALWAYS emit
            continue

        # Same-line guardrail (if available)
        for seg in _pre_split_colon_after_price(line, cue):
            seg = seg.strip()
            if not seg:
                continue
            staging.append(seg)
            # START beats GLUE (force on early ':' or ';')
            if _force_start_colon_semicolon(seg, cue, max_cue_pos):
                # older staged lines belong to previous listing
                while len(staging) > 1:
                    accum_parts.append(staging.popleft())
                _flush(accum_parts, out)
                # newest staged line starts new listing
                accum_parts.append(staging.pop())
                staging.clear()
                continue

            # Not a start: keep staging bounded
            while len(staging) > staging_window:
                accum_parts.append(staging.popleft())

    # EOF
    while staging:
        accum_parts.append(staging.popleft())
    _flush(accum_parts, out)
    return out

# -------------------- B) comma/dot agencies ----------------------------------

def split_by_comma_dot(
    lines: Iterable[str],
    *,
    cue: str,                               # ',' or '.'
    max_cue_pos: int = 32,
    staging_window: int = 1,
) -> List[str]:
    """
    One-listing-per-line for ',' or '.' agencies (guarded starts).
    Comma: start only if (early comma) & (not numeric) & (price soon after) & (head has letters).
    Dot:   start only if (early dot)   & (not numeric) & (not common abbrev) & (Uppercase next or price soon).
    """
    out: List[str] = []
    accum_parts: List[str] = []
    staging: deque[str] = deque()

    for raw in lines:
        line = raw.rstrip("\r\n").replace("\u00A0", " ")

        # HEADER FIRST (anywhere)
        hp = line.find("#")
        if hp != -1:
            left = line[:hp].rstrip()
            header = line[hp:]
            if left:
                staging.append(left.strip())
                while staging:
                    accum_parts.append(staging.popleft())
                _flush(accum_parts, out)
            else:
                while staging:
                    accum_parts.append(staging.popleft())
                _flush(accum_parts, out)
            out.append(header)
            continue

        # (No same-line pre-split for comma/dot by default – keep simple & safe)
        seg = line.strip()
        if not seg:
            continue
        staging.append(seg)

        # START detection by cue type
        is_start = False
        if cue == ",":
            is_start = _force_start_comma(seg, max_cue_pos)
        elif cue == ".":
            is_start = _force_start_dot(seg, max_cue_pos)

        if is_start:
            while len(staging) > 1:
                accum_parts.append(staging.popleft())
            _flush(accum_parts, out)
            accum_parts.append(staging.pop())
            staging.clear()
            continue

        # Not a start: bound staging
        while len(staging) > staging_window:
            accum_parts.append(staging.popleft())

    # EOF
    while staging:
        accum_parts.append(staging.popleft())
    _flush(accum_parts, out)
    return out

# -------------------- Router --------------------------------------------------

def split_by_cue_v2(
    lines,
    *,
    cue: str,
    max_cue_pos: int = 32,
    staging_window: int = 1,
):
    cue = _ensure_char_cue(cue)  # <-- critical
    if cue in (":", ";"):
        return split_by_colon_semicolon(
            lines, cue=cue, max_cue_pos=max_cue_pos, staging_window=staging_window
        )
    if cue in (",", "."):
        return split_by_comma_dot(
            lines, cue=cue, max_cue_pos=max_cue_pos, staging_window=staging_window
        )
    # Fallback: treat as plain continuation, header-aware
    out, accum = [], []
    for raw in lines:
        s = raw.rstrip("\r\n").replace("\u00A0", " ").strip()
        if not s:
            continue
        if s.lstrip().startswith("#"):
            if accum:
                out.append(re.sub(r"\s+", " ", " ".join(accum)).strip().rstrip(",;"))
                accum = []
            out.append(s)
            continue
        accum.append(s)
    if accum:
        out.append(re.sub(r"\s+", " ", " ".join(accum)).strip().rstrip(",;"))
    return out


# -----------------------------------------------------------------------------


# Wrapper to accept cfg dict or path
def _coerce_cfg(cfg):
    if cfg is None or isinstance(cfg, dict):
        return cfg
    p = Path(cfg)
    if not p.exists():
        raise FileNotFoundError(f"Config file not found: {p}")
    if p.suffix.lower() == ".json":
        return json.loads(p.read_text(encoding="utf-8"))
    if p.suffix.lower() in (".yaml", ".yml"):
        import yaml
        return yaml.safe_load(p.read_text(encoding="utf-8"))
    if p.suffix.lower() == ".toml":
        try:
            import tomllib
        except ImportError:
            import tomli as tomllib
        return tomllib.loads(p.read_text(encoding="utf-8"))
    raise ValueError(f"Unsupported config type: {p.suffix}")


# ----- Back-compat wrapper: accept dict or path as second arg -----------------




def split_by_cue(lines, cfg=None, **overrides):
    cfg = _coerce_cfg(cfg)
    cue = decode_cue(str(cfg.get("listing_marker", DEFAULT_CUE)))
    max_cue_pos = int(cfg.get("max_cue_pos", 32))
    staging_window = int(cfg.get("staging_window", 1))
    # Route to v2
    print ("DEBUG ENTER SPLIBY CUE CALLLING", cfg.get("listing_marker", DEFAULT_CUE))
    return split_by_cue_v2(
        lines, cue=cue, max_cue_pos=max_cue_pos, staging_window=staging_window
    )

# --------------------------------- CLI ---------------------------------------

def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Split agency TXT by cue into one-record-per-line")
    p.add_argument("-i", "--input", required=True, help="Path to input TXT (UTF-8/UTF-8-SIG)")
    p.add_argument("-o", "--output", required=False, help="Path to output file (defaults to stdout)")
    p.add_argument("--cue", default=DEFAULT_CUE, help="Cue character to detect starts (default ',')")
    p.add_argument("--max-cue-pos", type=int, default=DEFAULT_MAX_CUE_POS, help=f"Max index of first cue to qualify as start (default {DEFAULT_MAX_CUE_POS})")
    req_upper = p.add_mutually_exclusive_group()
    req_upper.add_argument("--require-uppercase", dest="require_upper", action="store_true", default=DEFAULT_REQUIRE_UPPER, help="Require first alphabetic token to start uppercase (default on)")
    req_upper.add_argument("--no-require-uppercase", dest="require_upper", action="store_false", help="Disable uppercase requirement")

    price_before = p.add_mutually_exclusive_group()
    price_before.add_argument("--require-price-before", dest="require_price_before", action="store_true", default=DEFAULT_REQUIRE_PRICE_BEFORE, help="For inline splits, require a price within lookback before a new start (default on)")
    price_before.add_argument("--no-require-price-before", dest="require_price_before", action="store_false", help="Disable price-before check for inline splits")

    p.add_argument("--inline-price-lookback", type=int, default=DEFAULT_INLINE_PRICE_LOOKBACK, help=f"Chars to look back for a price before inline start (default {DEFAULT_INLINE_PRICE_LOOKBACK})")

    trailing = p.add_mutually_exclusive_group()
    trailing.add_argument("--trailing-comma-glue", dest="trailing_comma_glue", action="store_true", default=DEFAULT_TRAILING_COMMA_GLUE, help="Glue next line when previous ended with comma/semicolon (default on)")
    trailing.add_argument("--no-trailing-comma-glue", dest="trailing_comma_glue", action="store_false", help="Disable trailing-comma glue")

    p.add_argument("--not-start-words", default=",".join(DEFAULT_NOT_START_WORDS), help="Comma-separated list of forbidden leading tokens (e.g., RES., COND., TORRE)")

    p.add_argument("--csv", action="store_true", help="Write CSV with a single 'record' column instead of TXT")

    return p


def main(argv: Sequence[str] | None = None) -> int:
    ap = build_arg_parser()
    args = ap.parse_args(argv)

    if len(args.cue) != 1:
        print("--cue must be a single character (e.g., ',')", file=sys.stderr)
        return 2

    lines = read_lines_utf8_sig(args.input)
    not_start_words = [w.strip() for w in (args.not_start_words or "").split(",") if w.strip()]

    records = split_by_cue(
        lines,
        cue=args.cue,
        max_cue_pos=args.max_cue_pos,
        require_upper=args.require_upper,
        not_start_words=not_start_words,
        require_price_before=args.require_price_before,
        inline_price_lookback=args.inline_price_lookback,
        trailing_comma_glue=args.trailing_comma_glue,
    )

    if args.output:
        out_path = args.output
        if args.csv:
            import csv
            with io.open(out_path, "w", encoding="utf-8-sig", newline="") as f:
                w = csv.writer(f)
                w.writerow(["record"])
                for r in records:
                    w.writerow([r])
        else:
            with io.open(out_path, "w", encoding="utf-8-sig", newline="\n") as f:
                for r in records:
                    f.write(r + "\n")
    else:
        if args.csv:
            import csv
            w = csv.writer(sys.stdout)
            w.writerow(["record"])
            for r in records:
                w.writerow([r])
        else:
            for r in records:
                sys.stdout.write(r + "\n")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
