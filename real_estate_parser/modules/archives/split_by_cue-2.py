#!/usr/bin/env python3
"""
SplitByCue.py — CUE-ONLY Phase-2 segmenter.

Use this when an agency has **no explicit listing delimiter** but a stable
**neighborhood cue** near the start of each listing (e.g., ":", ",", "." or a regex).

What it does
  • Preserves headers that start with '#'.
  • Starts a NEW listing when the cue appears within the first N characters
    (default 40). Optionally require the line to start with an uppercase token.
  • Merges continuation fragments (lines without a price) into the previous listing.
  • Produces ONE LINE PER LISTING. It does NOT add bullets; run Forcebullet as
    your final Phase-2 step to enforce the leading "* ".

This module knows only about cue-based segmentation. It does not handle
UPPERCASE, NUMBERED, or LITERAL token paths.

CLI (CUE only)
  python SplitByCue.py -i <raw.txt> -o <pre.txt> --cue-name colon --max-cue-pos 40
  python SplitByCue.py -i <raw.txt> -o <pre.txt> --cue "," --no-require-uppercase
  python SplitByCue.py -i <raw.txt> -o <pre.txt> --cue-regex "^.{0,30}:"

Exit codes: 0 ok, 1 IO/args error.
"""
from __future__ import annotations
import argparse
import io
import os
import re
import sys
from statistics import median
from typing import Iterable, Optional, Dict, List, Pattern

DEFAULT_PRICE_RX = r"(?:\$|Lps?\.?|L\.)\s*[\d\.,]+"

# ----------------- helpers -----------------

def is_header(line: str, header_marker: str) -> bool:
    s = line.lstrip()
    return s.startswith(header_marker) if header_marker else False


def compile_cue_regex(cue: Optional[str], cue_name: Optional[str], cue_regex: Optional[str], max_pos: int) -> Pattern[str]:
    """Build a regex that matches when the cue appears within the first max_pos chars.
    - cue: a literal like ':' or ','
    - cue_name: one of {'colon','comma','dot'} (case-insensitive)
    - cue_regex: full regex (overrides cue/cue_name)
    """
    if cue_regex:
        return re.compile(cue_regex)
    if cue_name:
        n = cue_name.lower().strip()
        if n == 'colon':
            cue = ':'
        elif n == 'comma':
            cue = ','
        elif n == 'dot':
            cue = '\.'
    if cue is None:
        raise ValueError("SplitByCue: cue not provided")
    lit = cue if cue == '\\.' else re.escape(cue)
    return re.compile(rf"^.{{0,{max_pos}}}{lit}")


def looks_like_start(line: str, cue_rx: Pattern[str], require_uppercase: bool) -> bool:
    s = line.strip()
    if not s:
        return False
    if require_uppercase and not re.match(r"^[A-ZÁÉÍÓÚÑ]", s):
        return False
    return bool(cue_rx.search(s))


# ----------------- core -----------------

def collapse_by_cue(raw_text: str, *, cue_rx: Pattern[str], require_uppercase: bool,
                    header_marker: str, price_rx: Pattern[str]) -> List[str]:
    lines = [l.rstrip() for l in raw_text.splitlines()]
    out: List[str] = []
    buf: Optional[str] = None

    def flush():
        nonlocal buf
        if buf is not None:
            out.append(buf.strip())
            buf = None

    for ln in lines:
        if not ln.strip():
            continue  # drop empty
        if is_header(ln, header_marker):
            flush()
            out.append(ln.strip())  # keep header exactly
            continue
        if looks_like_start(ln, cue_rx, require_uppercase):
            flush()
            buf = ln.strip()
        else:
            buf = (buf + " " + ln.strip()) if buf else ln.strip()

    flush()

    # Merge trailing fragments without a price into the previous listing
    merged: List[str] = []
    for item in out:
        if is_header(item, header_marker):
            merged.append(item)
            continue
        if not price_rx.search(item) and merged and not is_header(merged[-1], header_marker):
            merged[-1] = (merged[-1] + " " + item).strip()
        else:
            merged.append(item)

    return merged


def quality_report(lines: List[str], *, cue_rx: Pattern[str], price_rx: Pattern[str], header_marker: str) -> str:
    listings = [l for l in lines if l.strip() and not is_header(l, header_marker)]
    cue_hits = sum(1 for l in listings if cue_rx.search(l.strip()))
    price_hits = sum(1 for l in listings if price_rx.search(l))
    lens = [len(l) for l in listings]
    m = int(median(lens)) if lens else 0
    return (
        f"lines={len(lines)} listings={len(listings)} cue_hits={cue_hits}/{len(listings) or 1} "
        f"with_price={price_hits}/{len(listings) or 1} median_len={m}"
    )


# ----------------- CUE-only public API -----------------

def resolve_cue_from_marker(marker: Optional[str], cfg: Optional[Dict] = None) -> Dict:
    """Parse a marker of the form 'CUE:COLON' / 'CUE:COMMA' / 'CUE:DOT' /
    'CUE:<literal>' / 'CUE:regex=…'. If marker is None or not 'CUE:*', falls back
    to cfg['neighborhood_delimiter'] (string or {'regex': ...}). If neither is
    present, raise ValueError.
    """
    cfg = cfg or {}
    plan: Dict = {
        "max_cue_pos": int(cfg.get("max_cue_pos", 40)),
        "require_uppercase": bool(cfg.get("require_uppercase", True)),
        "header_marker": cfg.get("header_marker", "#"),
        "price_regex": cfg.get("price_regex", DEFAULT_PRICE_RX),
    }

    token: Optional[str] = None
    if marker and str(marker).upper().startswith("CUE:"):
        token = str(marker).split(":", 1)[1]
    else:
        nd = cfg.get("neighborhood_delimiter")
        if isinstance(nd, dict) and nd.get("regex"):
            plan["cue_regex"] = nd["regex"]
        elif isinstance(nd, str):
            token = nd
        else:
            raise ValueError("SplitByCue: cue required (marker must start with 'CUE:' or cfg['neighborhood_delimiter'] must be set)")

    if token is not None:
        tU = str(token).upper()
        if tU in {"COLON", "COMMA", "DOT"}:
            plan["cue_name"] = tU
        elif str(token).lower().startswith("regex="):
            plan["cue_regex"] = str(token)[len("regex="):]
        else:
            plan["cue"] = str(token)  # literal ':' or ',' etc.
    return plan


def split_by_cue_lines(raw_lines: Iterable[str], marker: Optional[str] = None, cfg: Optional[Dict] = None) -> List[str]:
    """Join `raw_lines`, resolve the CUE from marker/cfg, and return ONE-LINE
    listings with headers preserved (no bullets). **CUE-only**.
    """
    cfg = cfg or {}
    plan = resolve_cue_from_marker(marker, cfg)
    cue_rx = compile_cue_regex(
        cue=plan.get("cue"),
        cue_name=plan.get("cue_name"),
        cue_regex=plan.get("cue_regex"),
        max_pos=plan.get("max_cue_pos", 40),
    )
    price_rx = re.compile(plan.get("price_regex", DEFAULT_PRICE_RX), re.I)
    text = "\n".join(raw_lines)
    return collapse_by_cue(
        text,
        cue_rx=cue_rx,
        require_uppercase=plan.get("require_uppercase", True),
        header_marker=plan.get("header_marker", "#"),
        price_rx=price_rx,
    )


def process(raw_lines: Iterable[str], marker: Optional[str] = None, cfg: Optional[Dict] = None) -> List[str]:
    """Self-contained CUE entrypoint for callers.
    Requires a CUE marker ('CUE:*') or cfg['neighborhood_delimiter'].
    Returns one-line listings with headers preserved (no bullets).
    """
    print("SPLIT BY CUE PROCESS")
    return split_by_cue_lines(raw_lines, marker=marker, cfg=cfg)


# ----------------- CLI (CUE only) -----------------

def main(argv: List[str]) -> int:
    ap = argparse.ArgumentParser(description="Collapse raw text to one-line listings using a neighborhood cue (':', ',', '.', or regex). Headers pass through.")
    ap.add_argument("--in", "-i", dest="in_path", required=True, help="Input raw text file")
    ap.add_argument("--out", "-o", dest="out_path", required=True, help="Output pre text file (no bullets)")
    ap.add_argument("--encoding", default="utf-8")

    # cue controls (CUE only)
    ap.add_argument("--cue", help="Literal cue, e.g., ':' or ','")
    ap.add_argument("--cue-name", choices=["colon","comma","dot"], help="Named cue")
    ap.add_argument("--cue-regex", help="Custom regex; overrides --cue/--cue-name")
    ap.add_argument("--max-cue-pos", type=int, default=40, help="Max index within which the cue must appear (default 40)")
    ap.add_argument("--no-require-uppercase", action="store_true", help="Do not require uppercase token at line start")

    # headers / price
    ap.add_argument("--header-marker", default="#")
    ap.add_argument("--price-regex", default=DEFAULT_PRICE_RX)

    args = ap.parse_args(argv)

    try:
        if not os.path.isfile(args.in_path):
            print(f"[SplitByCue] Input not found: {args.in_path}", file=sys.stderr)
            return 1
        raw = io.open(args.in_path, "r", encoding=args.encoding, newline=None).read()

        cue_rx = compile_cue_regex(
            cue=args.cue,
            cue_name=args.cue_name,
            cue_regex=args.cue_regex,
            max_pos=args.max_cue_pos,
        )
        price_rx = re.compile(args.price_regex or DEFAULT_PRICE_RX, re.I)
        collapsed = collapse_by_cue(
            raw,
            cue_rx=cue_rx,
            require_uppercase=(not args.no_require_uppercase),
            header_marker=args.header_marker,
            price_rx=price_rx,
        )

        os.makedirs(os.path.dirname(args.out_path), exist_ok=True)
        io.open(args.out_path, "w", encoding=args.encoding, newline="\n").write("\n".join(collapsed) + "\n")

        # quick report
        print("[SplitByCue]", quality_report(collapsed, cue_rx=cue_rx, price_rx=price_rx, header_marker=args.header_marker))
        return 0

    except Exception as e:
        print(f"[SplitByCue] Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
