#!/usr/bin/env python3
"""
SplitByCue v4.0 — clean baseline (spec + robust impl)

Goals (stable + predictable):
  • Input: iterable of text lines (strings). Headers start with '#'.
  • Start-of-listing when:
      - a cue (',' ':' or '.') appears within first N chars (max_cue_pos), AND
      - the text BEFORE the cue looks like a place/name (not an amenity token).
  • Inline starts: if a single physical line contains another listing later, split it
    (conservatively) — usually only after a price fragment like "Lps. 10,000.00" or "$ 650.00".
  • Glue: all other lines/pieces attach to the current listing.
  • Numeric-grouping commas (e.g., 14, 000.00) never trigger a start.
  • "Never end on comma": if the current row ends with "," we keep gluing.
    On flush (header/EOF) we can strip a dangling comma.
  • ALWAYS return a list (never None). Empty input -> [].

Config (either positional or dict as 3rd arg):
  • listing_marker / cue: 'CUE:COMMA' | 'CUE:COLON' | 'CUE:DOT' | ',' | ':' | '.'
  • max_cue_pos: int (default 40; Racing often needs ~50)
  • require_upper: bool (gate on initial capital of first token; often False for Spanish data)
  • require_price_before: bool (default True; reduces false inline splits)
  • not_start_words: list[str] amenity words (AL, AS/AL, COMEDOR, BAÑO, ...)
  • no_trailing_comma_end: bool (default True)
  • strip_trailing_commas_on_flush: bool (default True)
  • debug: bool (print trace to stderr)

Compatibility:
  • Works with direct calls: split_by_cue(lines, cue, cfg_dict) — like your pipeline.
  • Also works with CLI. See main() at bottom.
"""

from typing import Iterable, List, Tuple
import sys
import re
import argparse

# ---------- Debug ----------
DEBUG = False

def dbg(*a):
    if DEBUG:
        print('[SplitByCue]', *a, file=sys.stderr)

# ---------- Defaults ----------
DEFAULT_NOT_START = {
    # amenities / features / common non-names
    "AL","AS","AL/AS","AS/AL",
    "SALA","COMEDOR","COCINA","BAÑO","BAÑOS",
    "GARAGE","GARAJE","CISTERNA","JARDIN","JARDÍN",
    "PATIO","VIGILANCIA","AREA","ÁREA","TERRAZA","PISCINA",
    "CIRCUITO","CERRADO","PLANTA","PLANTAS","HAB","HABITACIONES",
}

PRICE_RE = re.compile(r'(?:LPS?\.?|Lps\.?|L\.?|\$)\s?\d[\d\s.,/]*$')

# ---------- Helpers ----------

def _flush_line(current_parts, out_list, strip_trailing_commas_on_flush=True):
    if not current_parts:
        return
    line = " ".join(current_parts).rstrip()
    if strip_trailing_commas_on_flush:
        line = re.sub(r',\s*$', '', line)
    out_list.append(line)
    current_parts.clear()


def normalize_cue(cue: str) -> str:
    if not cue:
        return ","
    key = str(cue).strip().lower()
    if "comma" in key or "cue:comma" in key:
        return ","
    if "colon" in key or "cue:colon" in key:
        return ":"
    if "dot" in key or "cue:dot" in key or "punto" in key:
        return "."
    if len(cue) == 1 and cue in {",", ":", "."}:
        return cue
    return cue


def is_header(line: str) -> bool:
    return line.strip().startswith('#')


def _ends_with_soft_comma(text: str) -> bool:
    return bool(re.search(r',\s*$', text))


def find_cue_index(line: str, cue: str) -> int:
    """Find first cue index, but skip numeric-grouping commas: DIGIT , [SPACE]? DIGIT."""
    if cue != ',':
        return line.find(cue)
    i = 0
    while True:
        i = line.find(',', i)
        if i == -1:
            return -1
        prev = line[i-1] if i-1 >= 0 else ''
        j = i + 1
        if j < len(line) and line[j] == ' ':
            j += 1
        nxt = line[j] if j < len(line) else ''
        if prev.isdigit() and nxt.isdigit():
            i += 1
            continue
        return i



def _prefix_looks_like_name(line: str, idx: int, stop_words: set) -> bool:
    orig = line[:idx].strip().strip(",.;:()[]")
    if not orig:
        return False

    parts = [w for w in orig.split() if w]
    if not parts:
        return False

    # reject if the LAST word is an amenity/common word
    if parts[-1].upper() in stop_words:
        return False

    if len(parts) == 1:
        w = parts[0]
        if "/" in w:
            return False
        core = re.sub(r"[^A-Za-zÁÉÍÓÚÑ0-9]", "", w)
        # IMPORTANT: use original case for isupper()
        return w.isupper() and len(core) >= 3

    # Multi-word: mostly uppercase *in the original text*
    letters = [c for c in orig if c.isalpha()]
    if not letters:
        return False
    upper_ratio = sum(1 for c in orig if c.isalpha() and c.isupper()) / len(letters)
    return upper_ratio >= 0.8



def is_cue_start(line: str, cue: str, max_cue_pos: int, require_upper: bool, stop_words: set) -> bool:
    idx = find_cue_index(line, cue)
    if idx == -1 or idx > max_cue_pos:
        return False
    if not _prefix_looks_like_name(line, idx, stop_words):
        return False
    if require_upper:
        tok = line.lstrip().split(' ')[0]
        if not tok or not tok[0].isupper():
            return False
    return True


def embedded_split(text: str, cue: str, *, stop_words: set, require_price_before: bool, never_end_on_comma: bool) -> List[Tuple[str, bool]]:
    """Split a physical line into logical pieces where inline new listings appear.
    Conservative: require name-like token + (optionally) a price immediately before.
    Returns [(chunk, forced_start), ...].
    """
    if not text:
        return [("", False)]

    cue_esc = re.escape(cue)
    pat = re.compile(rf'(?:(?<=^)|(?<=\s))([A-ZÁÉÍÓÚÑ0-9][A-ZÁÉÍÓÚÑ0-9/# .-]{{1,40}}){cue_esc}(?=\s)')

    starts: List[int] = []
    tokens: List[str] = []
    for m in pat.finditer(text):
        s = m.start(1)
        cpos = m.end() - 1
        token = m.group(1).strip().upper()
        # Skip numeric-grouping commas: 14, 000.00
        if cue == ',':
            prev = text[cpos-1] if cpos-1 >= 0 else ''
            j = cpos + 1
            if j < len(text) and text[j] == ' ':
                j += 1
            nxt = text[j] if j < len(text) else ''
            if prev.isdigit() and nxt.isdigit():
                continue
        if s <= 1:
            continue
        if token in stop_words:
            continue
        if require_price_before:
            window = text[max(0, s-40):s]
            if not PRICE_RE.search(window):
                continue
        starts.append(s)
        tokens.append(token)

    if not starts:
        return [(text, False)]

    pieces: List[Tuple[str, bool]] = []
    pos = 0
    for i, start in enumerate(starts):
        left = text[pos:start].strip()
        if left:
            pieces.append((left, False))
        end = starts[i+1] if i+1 < len(starts) else len(text)
        chunk = text[start:end].strip()
        if chunk:
            pieces.append((chunk, True))
        pos = end

    if pos < len(text):
        tail = text[pos:].strip()
        if tail:
            pieces.append((tail, False))

    # Never end a listing on comma: if the previous piece ends with ',', merge next
    if never_end_on_comma and pieces:
        merged: List[Tuple[str, bool]] = []
        for chunk, forced in pieces:
            if merged and _ends_with_soft_comma(merged[-1][0]):
                prev = merged.pop()
                merged.append((prev[0] + ' ' + chunk, False))
            else:
                merged.append((chunk, forced))
        pieces = merged

    return pieces or [(text, False)]

# ---------- Core ----------

def split_by_cue(lines: Iterable[str], cue, max_cue_pos=40, require_upper=True) -> List[str]:
    """Core segmentation. Works with either:
        (lines, cue, max_cue_pos:int, require_upper:bool)
      or
        (lines, cue, cfg:dict)
    """
    # Guard against None/falsey
    if not lines:
        return []

    # Back-compat shim: allow a config dict as the 3rd positional arg
    cfg = {}
    stop_words = set(DEFAULT_NOT_START)
    require_price_before = True
    never_end_on_comma = True
    strip_commas_on_flush = True

    if isinstance(max_cue_pos, dict):
        cfg = max_cue_pos
        cue = cfg.get('listing_marker', cfg.get('cue', cue))
        try:
            max_cue_pos = int(cfg.get('max_cue_pos', 40))
        except Exception:
            max_cue_pos = 40
        require_upper = bool(cfg.get('require_upper', require_upper))
        require_price_before = bool(cfg.get('require_price_before', True))
        never_end_on_comma = bool(cfg.get('no_trailing_comma_end', True))
        strip_commas_on_flush = bool(cfg.get('strip_trailing_commas_on_flush', True))
        extra = cfg.get('not_start_words') or cfg.get('no_start_words') or []
        stop_words |= {str(w).strip().upper() for w in extra}
        global DEBUG
        DEBUG = bool(cfg.get('debug', False))

    cue = normalize_cue(cue)
    try:
        max_cue_pos = int(max_cue_pos)
    except Exception:
        max_cue_pos = 40
    require_upper = bool(require_upper)

    dbg(f"START cue={cue!r} max_cue_pos={max_cue_pos} require_upper={require_upper} price_before={require_price_before} never_end_on_comma={never_end_on_comma}")

    out: List[str] = []
    cur: List[str] = []

    for i, raw in enumerate(lines, 1):
        s = str(raw).strip()
        if not s:
            dbg(f"L{i} SKIP empty")
            continue
        dbg(f"L{i} IN: {s}")

        # explode into logical pieces
        pieces = embedded_split(
            s, cue,
            stop_words=stop_words,
            require_price_before=require_price_before,
            never_end_on_comma=never_end_on_comma,
        )

        for chunk, forced in pieces:
            if not chunk:
                continue

            if is_header(chunk):
                _flush_line(cur, out, strip_trailing_commas_on_flush=strip_commas_on_flush)  # <- cur, not current
                out.append(chunk)
                dbg("  -> HEADER flush + emit")
                continue


            # decide start vs glue
            start = forced or is_cue_start(chunk, cue, max_cue_pos, require_upper, stop_words)

            # If current ends with a comma, force GLUE regardless
            if start and never_end_on_comma and cur and _ends_with_soft_comma(' '.join(cur)):
                start = False

            if start:
                if cur:
                    line = ' '.join(cur).rstrip()
                    if strip_commas_on_flush and _ends_with_soft_comma(line):
                        line = re.sub(r',\s*$', '', line)
                    out.append(line)
                    dbg("  -> START: flush current")
                cur = [chunk]
                dbg("  -> START new listing")
            else:
                if cur:
                    cur.append(chunk)
                    dbg("  -> GLUE to current")
                else:
                    # backfill to previous non-header row
                    if out and not is_header(out[-1]):
                        out[-1] = out[-1] + ' ' + chunk
                        dbg("  -> BACKFILL to prev row")
                    else:
                        cur = [chunk]
                        dbg("  -> START implicit (no current)")

    if cur:
        line = ' '.join(cur).rstrip()
        if strip_commas_on_flush and _ends_with_soft_comma(line):
            line = re.sub(r',\s*$', '', line)
        out.append(line)
        dbg("END: flush trailing current   COMPLETE LISTINS")

    return out

# ---------- CLI ----------

def main():
    p = argparse.ArgumentParser()
    p.add_argument('-i', '--input', required=True)
    p.add_argument('-o', '--output', required=True)
    p.add_argument('--cue', default=',')
    p.add_argument('--max-cue-pos', type=int, default=40)
    p.add_argument('--no-require-uppercase', action='store_true')
    p.add_argument('--no-require-price-before', action='store_true')
    p.add_argument('--not-start-words', nargs='*', default=None)
    p.add_argument('--no-trailing-comma-end', action='store_true')
    p.add_argument('--no-strip-commas-on-flush', action='store_true')
    p.add_argument('--debug', action='store_true')
    args = p.parse_args()

    with open(args.input, encoding='utf-8') as f:
        lines = f.readlines()

    cfg = {
        'cue': args.cue,
        'max_cue_pos': args.max_cue_pos,
        'require_upper': not args.no_require_uppercase,
        'require_price_before': not args.no_require_price_before,
        'no_trailing_comma_end': not args.no_trailing_comma_end,
        'strip_trailing_commas_on_flush': not args.no_strip_commas_on_flush,
        'debug': args.debug,
    }
    if args.not_start_words:
        cfg['not_start_words'] = args.not_start_words

    # Route via back-compat signature (3rd arg is cfg dict)
    results = split_by_cue(lines, cue=args.cue, max_cue_pos=cfg) or []

    with open(args.output, 'w', encoding='utf-8') as f:
        for line in results:
            f.write(line + '\n')

if __name__ == '__main__':
    main()
