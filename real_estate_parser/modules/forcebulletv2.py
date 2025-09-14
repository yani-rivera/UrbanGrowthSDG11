#!/usr/bin/env python3
"""
forcebullet.py — normalize listing lines.

Default: ensure every non-empty line starts with "* " (asterisk + space).

- Strips any leading bullets/dashes/numbering ("1.", "1)") and stray punctuation from the line start.
- Preserves header lines that start with "#" (normalizes to "# " + content).
- Preserves blank lines unless --drop-blank-lines is set.
- Idempotent: if a line already starts with "* ", it stays standard.

NEW:
  --normalize-existing-only  → convert ONLY lines that already look like a list start
                                (bullets/enumerations) to "* "; leave other lines unchanged.

CLI:
  python forcebullet.py -i input.txt -o output.txt
  python forcebullet.py -i input.txt --in-place
  python forcebullet.py -i input.txt --verify-only
  python forcebullet.py -i input.txt -o output.txt --normalize-existing-only
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import re
import sys
from typing import List

# Leading markers to strip from non-empty, non-header lines at the start
_LEADING_MARKERS = re.compile(
    r"^\s*(?:"
    r"[\*\-•‣▪–—―·]+\s*|"      # bullets/dashes variants
    r"\d{1,3}[\.)]\s*|"        # enumerations: 1. / 1)
    r"[:\.,·]\s*"              # stray punctuation-only starts
    r")+",
    re.UNICODE,
)

# Strict detector for lines that already look like a list start
START_RX = re.compile(
    r'^[ \t]{0,3}(?:'               # allow up to 3 leading spaces
    r'\d{1,3}[.)]|'                 # 1. or 1)
    r'[\-•‣▪–—·*]'                  # bullet/dash variants
    r')\s+(?!\d{1,2}[:.]\d{2}\b)',  # avoid times like 10:30 / 10.30
    re.UNICODE
)

@dataclass
class Stats:
    total_lines: int
    non_empty_lines: int
    starts_with_bullet: int
    without_bullet: int

def _strip_bom(s: str) -> str:
    if s.startswith("\ufeff"):
        return s.lstrip("\ufeff")
    return s

def bulletize_line(line: str, normalize_existing_only: bool = False) -> str:
    """Return normalized listing line.
    - If header ('#'), normalize to '# ' + content.
    - If blank, return as-is (blank). The caller decides whether to keep or drop.
    - Else, strip leading markers and prefix '* '.
    - If normalize_existing_only=True, only act on lines that START_RX matches.
    """
    line = _strip_bom(line)
    # Preserve trailing newline; operate on content only
    nl = ""
    if line.endswith("\n"):
        nl = "\n"
        core = line[:-1]
    else:
        core = line

    lstr = core.lstrip()

    # Header case
    if lstr.startswith("#"):
        content = lstr[1:].lstrip()
        return f"# {content}{nl}"

    # Blank line
    if not lstr:
        return f"{lstr}{nl}"

    # In normalize-only mode, only act if the line already looks like a list start
    if normalize_existing_only and not START_RX.match(lstr):
        # Leave line as-is
        return f"{core}{nl}"

    # Strip known leading markers (numbering/bullets/punct) before applying "* "
    stripped = _LEADING_MARKERS.sub("", lstr)

    # Already bulletized?
    if stripped.startswith("* "):
        return f"* {stripped[2:].lstrip()}{nl}"
    if stripped.startswith("*"):
        return f"* {stripped[1:].lstrip()}{nl}"

    # Otherwise, prefix "* "
    return f"* {stripped.lstrip()}{nl}"

def verify_lines(lines: List[str]) -> Stats:
    total = len(lines)
    non_empty = 0
    starts = 0
    without = 0
    for ln in lines:
        s = _strip_bom(ln).lstrip()
        if not s:
            continue
        non_empty += 1
        if s.startswith("* "):
            starts += 1
        else:
            without += 1
    return Stats(total, non_empty, starts, without)

def parse_args(argv=None):
    ap = argparse.ArgumentParser(description="Normalize listing lines to begin with '* ' (keeps headers '#').")
    ap.add_argument("--in", "-i", dest="infile", required=True, help="Input text file")
    ap.add_argument("--out", "-o", dest="outfile", help="Output text file")
    ap.add_argument("--in-place", action="store_true", help="Overwrite the input file")
    ap.add_argument("--verify", action="store_true", help="Verify result after writing")
    ap.add_argument("--verify-only", action="store_true", help="Only verify input file (no write)")
    ap.add_argument("--drop-blank-lines", action="store_true", help="Drop blank lines in output")
    ap.add_argument(
        "--normalize-existing-only",
        action="store_true",
        help="Only convert lines that already start with a bullet/enumeration to '* '; leave other lines unchanged",
    )
    return ap.parse_args(argv)

def main(argv=None) -> int:
    args = parse_args(argv)

    try:
        with open(args.infile, "r", encoding="utf-8-sig") as f:
            lines = f.readlines()
    except Exception as e:
        print(f"[Forcebullet] Failed to read input: {e}", file=sys.stderr)
        return 1

    if args.verify_only:
        st = verify_lines(lines)
        print(f"[Forcebullet] VerifyOnly: total={st.total_lines} non_empty={st.non_empty_lines} starts_with_bullet={st.starts_with_bullet} without_bullet={st.without_bullet}")
        return 0

    # Transform
    out_lines: List[str] = []
    for ln in lines:
        norm = bulletize_line(ln, normalize_existing_only=args.normalize_existing_only)
        if args.drop_blank_lines and not norm.strip():
            continue
        out_lines.append(norm)

    # Decide output path
    outfile = args.outfile
    if not outfile and args.in_place:
        outfile = args.infile
    if not outfile:
        print("[Forcebullet] Must specify --out or --in-place", file=sys.stderr)
        return 1

    try:
        with open(outfile, "w", encoding="utf-8") as f:
            f.writelines(out_lines)
    except Exception as e:
        print(f"[Forcebullet] Failed to write output: {e}", file=sys.stderr)
        return 1

    if args.verify or args.verify_only:
        st = verify_lines(out_lines)
        print(f"[Forcebullet] Verify: total={st.total_lines} non_empty={st.non_empty_lines} starts_with_bullet={st.starts_with_bullet} without_bullet={st.without_bullet}")
        if st.without_bullet != 0 and not args.normalize_existing_only:
            return 2

    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
