#!/usr/bin/env python3
"""
Glue listings by explicit marker, then (optionally) standardize the marker.

SPEC (simple & strict)
- A header is any line that starts with '#'. Headers are preserved as-is and
  flush the current listing buffer.
- A *marker* (delimiter) identifies the *start* of a listing. It must appear at the beginning of the line (BOL). Mid-line markers are ignored. Each BOL marker starts a new listing.
- Step 1 (merge): glue everything from a BOL marker until the *next* BOL marker.
  Produce exactly one line per listing. The produced line is prefixed with
  the ORIGINAL marker + a single space: "<marker> <text>\n".
- Step 2 (standardize): if a *to_marker* is provided, rewrite the first token of
  each listing line from <marker> to <to_marker>. If emit_marker=False, drop the
  marker entirely and emit only the text.

CONFIG KEYS (any of these are accepted)
- input marker  : "listing_marker", "listing_delimiter", "delimiter",
                  "input_listing_marker", "marker", "bullet"
- output marker : "listing_marker_tochange", "to_marker",
                  "output_listing_marker", "output_marker"
- emit control  : "emit_marker" (bool)

PUBLIC API
- merge_listings(lines, marker, drop_blank_lines=True) -> List[str]
- standardize_marker(rows, from_marker, to_marker=None, emit_marker=True) -> List[str]
- bulletize(lines, cfg=None, marker=None, to_marker=None, emit_marker=None,
            drop_blank_lines=True) -> List[str]   # merge first, then standardize
- bulletize_file(in_path, out_path, cfg=None, **kwargs) -> List[str]

CLI
  python glue.py -i in.txt -o out.txt --config agency.json
  python glue.py -i in.txt -o out.txt --marker "*" --to-marker "-"
  python glue.py -i in.txt -o out.txt --marker "*" --no-emit-marker


"""



from __future__ import annotations
from typing import Iterable, List, Dict, Any
import argparse
import json
import re
import sys

HEADER_PREFIX = "#"

# ---------------- core ----------------

def _flush(buf: List[str], out: List[str], marker: str) -> None:
    """Append current listing with ORIGINAL marker and clear buffer."""
    if not buf:
        return
    text = " ".join(p for p in buf if p).strip()
    if text:
        out.append(f"{marker} {text}\n")
    buf.clear()


def merge_listings(lines: Iterable[str], marker: str, drop_blank_lines: bool = True) -> List[str]:
    """MERGE step: glue text from each BOL `marker` to the next BOL `marker`.
    - Mid-line markers are ignored.
    - Headers ('#...') are preserved and flush the current buffer.
    - Returns one line per listing, prefixed with the ORIGINAL marker.
    """
    if not marker:
        raise ValueError("merge_listings: `marker` must be non-empty")
    out: List[str] = []
    cur: List[str] = []

    def starts_with(line: str) -> tuple[bool, str]:
        l = line.rstrip("")
        if l.startswith(marker):
            return True, l[len(marker):].lstrip()
        return False, l.strip()

    for raw in lines:
        s = (raw if isinstance(raw, str) else str(raw)).rstrip("")
        if not s.strip() and drop_blank_lines:
            continue

        # headers: flush and keep as-is
        if s.strip().startswith(HEADER_PREFIX):
            _flush(cur, out, marker)
            out.append(s.strip() + "\n")
            continue

        is_start, rest = starts_with(s)
        if is_start:
            _flush(cur, out, marker)
            if rest:
                cur.append(rest)
            continue

        # continuation line (no BOL marker)
        txt = rest
        if txt:
            if cur:
                cur.append(txt)
            else:
                if out and not out[-1].startswith(HEADER_PREFIX):
                    out[-1] = out[-1].rstrip("\n") + " " + txt + ""
                else:
                    cur.append(txt)

    _flush(cur, out, marker)
    return out

def standardize_marker(rows: List[str], *, from_marker: str, to_marker: str | None,
                       emit_marker: bool = True) -> List[str]:
    if not from_marker:
        raise ValueError("standardize_marker: `from_marker` must be non-empty")

    # keep original marker, maybe strip
    if to_marker is None or to_marker == from_marker:
        if emit_marker:
            return rows
        strip = len(from_marker) + 1
        out: List[str] = []
        for ln in rows:
            if ln.startswith(HEADER_PREFIX):
                out.append(ln)
            elif ln.startswith(f"{from_marker} "):
                out.append(ln[strip:])
            else:
                out.append(ln)
        return out

    # rewrite marker token at line start (headers untouched)
    pat = re.compile(rf"^\s*{re.escape(from_marker)}\s+")
    out = []
    for ln in rows:
        if ln.startswith(HEADER_PREFIX):
            out.append(ln)
        else: 
            ln2 = pat.sub(f"{to_marker} ", ln, count=1)
            if not emit_marker and ln2.startswith(f"{to_marker} "):
                ln2 = ln2[len(to_marker) + 1:]
            out.append(ln2)
    return out

# -------------- config + back-compat --------------

def _read_markers(cfg: dict | None,
                  default_in: str | None = None,
                  default_out: str | None = None) -> Tuple[str | None, str | None, bool]:
    """Return (in_marker, out_marker, emit_flag) from cfg (with flexible key names)."""
    if not isinstance(cfg, dict):
        return (default_in, default_out, True)
    in_keys  = ["listing_marker", "listing_delimiter", "delimiter", "input_listing_marker", "marker", "bullet"]
    out_keys = ["listing_marker_tochange", "to_marker", "output_listing_marker", "output_marker"]
    inp = next((str(cfg[k]) for k in in_keys  if cfg.get(k)), default_in)
    outm= next((str(cfg[k]) for k in out_keys if cfg.get(k)), default_out)
    emit = bool(cfg.get("emit_marker", True))
    return (inp, outm, emit)







def bulletize(lines: Iterable[str], cfg: Dict[str, Any] | None = None) -> List[str]:
    cfg = cfg or {}
    out_marker = (str(cfg.get("to_marker") or cfg.get("listing_marker") or "*").strip() or "*")

    tok_pat = r"[-*+•–—·]|(?:\d+)[.)]"  # known bullet tokens
    bullet_rx = re.compile(rf"^(?P<lead>\s*)(?P<tok>{tok_pat})\s+(?P<rest>.*)$")

    out: List[str] = []
    for raw in lines:
        s = "" if raw is None else raw

        # keep blank lines as-is
        if s.strip() == "":
            out.append(s)
            continue

        m = bullet_rx.match(s)
        if m:
            lead, rest = m.group("lead"), m.group("rest")
            # if what follows the (optional) bullet is a header, drop the bullet
            if rest.lstrip().startswith("#"):
                out.append(lead + rest.lstrip())
            else:
                out.append(f"{lead}{out_marker} {rest}")
            continue

        # no bullet at start
        lead = re.match(r"^(\s*)", s).group(1)
        body = s[len(lead):]
        if body.lstrip().startswith("#"):
            out.append(lead + body.lstrip())     # keep header
        else:
            out.append(f"{lead}{out_marker} {body}")

        # done

    return out




def bulletize_file(in_path: str, out_path: str, cfg: dict | None = None, **overrides) -> List[str]:
    with open(in_path, "r", encoding="utf-8-sig") as f:
        lines = f.readlines()
    rows = bulletize(lines, cfg, **overrides)
    with open(out_path, "w", encoding="utf-8") as f:
        f.writelines(rows)
    return rows

# ---------------- CLI ----------------

def _parse_args(argv=None):
    ap = argparse.ArgumentParser(description="Merge listings by explicit marker, then standardize marker (headers preserved).")
    ap.add_argument("-i", "--input", required=True, help="Input text file")
    ap.add_argument("-o", "--output", required=True, help="Output text file")
    ap.add_argument("--config", help="JSON config with listing_marker / listing_marker_tochange / emit_marker")
    ap.add_argument("--marker", help="Input listing marker (overrides config)")
    ap.add_argument("--to-marker", dest="to_marker", help="Output marker (overrides config)")
    ap.add_argument("--no-emit-marker", action="store_true", help="Emit no marker; only text")
    ap.add_argument("--drop-blank-lines", action="store_true", help="Drop blank lines while merging")
    return ap.parse_args(argv)


def main(argv=None) -> int:
    args = _parse_args(argv)
    cfg = None
    if args.config:
        try:
            with open(args.config, "r", encoding="utf-8") as cf:
                cfg = json.load(cf)
        except Exception as e:
            print(f"[glue] Warning: failed to read config: {e}", file=sys.stderr)

    overrides = {
        "marker": args.marker,
        "to_marker": args.to_marker,
        "emit_marker": (False if args.no_emit_marker else None),
        "drop_blank_lines": args.drop_blank_lines,
    }
    rows = bulletize_file(args.input, args.output, cfg=cfg, **overrides)
    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
