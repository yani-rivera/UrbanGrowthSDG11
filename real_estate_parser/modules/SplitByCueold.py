#!/usr/bin/env python3
"""
SplitByCue_v2
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


def looks_like_start(
    line: str,
    *,
    cue: str,
    max_cue_pos: int,
    require_upper: bool,
    not_start_words: Sequence[str],
) -> bool:
    p = line.find(cue)
    if p == -1 or p > max_cue_pos:
        return False
    head = line[:p]
    if not LETTER_PRESENT_RE.search(head):
        return False
    if not passes_upper_gate(head, require_upper):
        return False
    if is_forbidden_start(head, not_start_words):
        return False
    return True


def strong_start(line: str, *, cue: str, max_cue_pos: int, require_upper: bool, not_start_words: Sequence[str]) -> bool:
    if starts_with_price(line):
        return False
    return looks_like_start(line, cue=cue, max_cue_pos=max_cue_pos, require_upper=require_upper, not_start_words=not_start_words)


def should_glue(prev: str | None, line: str, *, cue: str, max_cue_pos: int, require_upper: bool, not_start_words: Sequence[str], trailing_comma_glue: bool) -> bool:
    if starts_with_price(line):
        return True
    if trailing_comma_glue and prev and TRAILING_COMMA_RE.search(prev):
        return not strong_start(line, cue=cue, max_cue_pos=max_cue_pos, require_upper=require_upper, not_start_words=not_start_words)
    if CONNECTOR_START_RE.match(line):
        return True
    return False

# --------------------------- Embedded splitter --------------------------------

def inline_splits(text: str, *, cue: str, max_cue_pos: int, require_upper: bool, not_start_words: Sequence[str], require_price_before: bool, price_lookback: int) -> List[str]:
    parts: List[str] = []
    i = 0
    n = len(text)
    while i < n:
        rel_cue = text.find(cue, i)
        if rel_cue == -1:
            parts.append(text[i:])
            break
        if rel_cue - i <= max_cue_pos:
            head = text[i:rel_cue]
            if LETTER_PRESENT_RE.search(head) and passes_upper_gate(head, require_upper) and not is_forbidden_start(head, not_start_words):
                j = rel_cue + 1
                found_next = False
                while j < n:
                    next_rel = text.find(cue, j)
                    if next_rel == -1:
                        break
                    seg_start = j
                    if next_rel - seg_start <= max_cue_pos:
                        head2 = text[seg_start:next_rel]
                        if LETTER_PRESENT_RE.search(head2) and passes_upper_gate(head2, require_upper) and not is_forbidden_start(head2, not_start_words):
                            if not require_price_before:
                                parts.append(text[i:seg_start].strip())
                                i = seg_start
                                found_next = True
                                break
                            else:
                                lookback_start = max(i, seg_start - price_lookback)
                                window = text[lookback_start:seg_start]
                                if PRICE_ANYWHERE_RE.search(window):
                                    parts.append(text[i:seg_start].strip())
                                    i = seg_start
                                    found_next = True
                                    break
                    j = next_rel + 1
                if not found_next:
                    parts.append(text[i:].strip())
                    break
                else:
                    continue
        i = rel_cue + 1
    cleaned = [re.sub(r"\s+", " ", p).strip().rstrip(",;") for p in parts if p and p.strip()]
    return cleaned

# ------------------------------- Core API ------------------------------------


def _split_by_cue_core(
    lines: Iterable[str],
    *,
    cue: str = DEFAULT_CUE,
    max_cue_pos: int = DEFAULT_MAX_CUE_POS,
    require_upper: bool = DEFAULT_REQUIRE_UPPER,
    not_start_words: Sequence[str] = DEFAULT_NOT_START_WORDS,
    require_price_before: bool = DEFAULT_REQUIRE_PRICE_BEFORE,
    inline_price_lookback: int = DEFAULT_INLINE_PRICE_LOOKBACK,
    trailing_comma_glue: bool = DEFAULT_TRAILING_COMMA_GLUE,
) -> List[str]:
    out: List[str] = []
    current: str | None = None

    def flush():
        nonlocal current
        if current is not None:
            s = re.sub(r"\s+", " ", current).strip().rstrip(",;")
            if s:
                out.append(s)
        current = None

    for raw in lines:
        line = raw.rstrip("\n\r")
        if should_glue(
            current, line,
            cue=cue, max_cue_pos=max_cue_pos,
            require_upper=require_upper,
            not_start_words=not_start_words,
            trailing_comma_glue=trailing_comma_glue,
        ):
            current = (current + " " + line.strip()) if current else line.strip()
            continue

        if looks_like_start(
            line, cue=cue, max_cue_pos=max_cue_pos,
            require_upper=require_upper, not_start_words=not_start_words,
        ):
            pieces = inline_splits(
                line.strip(),
                cue=cue,
                max_cue_pos=max_cue_pos,
                require_upper=require_upper,
                not_start_words=not_start_words,
                require_price_before=require_price_before,
                price_lookback=inline_price_lookback,
            )
            if pieces:
                flush()
                for p in pieces[:-1]:
                    out.append(p)
                current = pieces[-1]
            else:
                flush()
                current = line.strip()
        else:
            current = (current + " " + line.strip()) if current else line.strip()

    if current is not None and current.strip():
        s = re.sub(r"\s+", " ", current).strip().rstrip(",;")
        if s:
            out.append(s)

    return out


  
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
from pathlib import Path
import json as _json

def _coerce_cfg(cfg_like):
    """Return a dict from a cfg-like value: dict or path to JSON/YAML/TOML."""
    if cfg_like is None or isinstance(cfg_like, dict):
        return cfg_like or {}
    p = Path(cfg_like)
    if not p.exists():
        raise FileNotFoundError(f"Config file not found: {p}")
    sfx = p.suffix.lower()
    txt = p.read_text(encoding="utf-8")
    if sfx == ".json":
        return _json.loads(txt)
    if sfx in (".yaml", ".yml"):
        try:
            import yaml  # type: ignore
        except Exception as e:
            raise RuntimeError("YAML config specified but PyYAML is not installed. Run `pip install pyyaml`.") from e
        return yaml.safe_load(txt) or {}
    if sfx == ".toml":
        try:
            import tomllib  # py>=3.11
        except Exception:
            try:
                import tomli as tomllib  # type: ignore
            except Exception as e:
                raise RuntimeError("TOML config specified but tomllib/tomli not available. Install `tomli` for Py<3.11.") from e
        return tomllib.loads(txt) or {}
    raise ValueError(f"Unsupported config file type: {sfx}")

def split_by_cue(lines: Iterable[str], cfg: Dict[str, Any] | str | None = None, **overrides) -> List[str]:
    """Compat entry point.

    Supports:
      split_by_cue(lines, cfg_dict)
      split_by_cue(lines, 'configs/agency.json')
      split_by_cue(lines, cue=',', max_cue_pos=25, ...)
    Dict values are merged with explicit keyword overrides.
    """
    cfg = _coerce_cfg(cfg)
    params = {
        "cue": cfg.get("cue", DEFAULT_CUE),
        "max_cue_pos": int(cfg.get("max_cue_pos", DEFAULT_MAX_CUE_POS)),
        "require_upper": bool(cfg.get("require_upper", DEFAULT_REQUIRE_UPPER)),
        # legacy key: no_trailing_comma_end (True disables glue)
        "trailing_comma_glue": bool(overrides.get("trailing_comma_glue",
            (not cfg.get("no_trailing_comma_end")) if "no_trailing_comma_end" in cfg else cfg.get("trailing_comma_glue", DEFAULT_TRAILING_COMMA_GLUE))),
        "require_price_before": bool(cfg.get("require_price_before", DEFAULT_REQUIRE_PRICE_BEFORE)),
        "inline_price_lookback": int(cfg.get("inline_price_lookback", DEFAULT_INLINE_PRICE_LOOKBACK)),
        "not_start_words": cfg.get("not_start_words", DEFAULT_NOT_START_WORDS),
    }
    # Apply explicit overrides on top
    params.update(overrides)
    return _split_by_cue_core(lines, **params)

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
