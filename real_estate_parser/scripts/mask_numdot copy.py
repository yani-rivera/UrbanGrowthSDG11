
#!/usr/bin/env python3
import argparse, os, re, sys

# --- detection: "d." / "dd." followed by a letter or '#'
NUMDOT_START  = re.compile(r"^(\s*)(\d{1,3})\.\s*(?=[A-Za-zÁÉÍÓÚÜÑ#])")
INLINE_NUMDOT = re.compile(r"(?<![\d,])\b(\d{1,3})\.\s*(?=[A-Za-zÁÉÍÓÚÜÑ#])")
# --- area patterns (start-of-line and tail-of-line) ---
AREA_START = re.compile(
    r""" ^
        \s*
        \d{1,4}(?:[.,]\d{3})*(?:[.,]\d{1,2})?   # number or decimal
        \s*
        (?:m2|m²|mt2|mts2|mts|vrs2|vrs²|vrs|vr2|vr|varas?)\b
    """, re.IGNORECASE | re.VERBOSE
)

AREA_TAIL = re.compile(
    r""" 
        \d{1,4}(?:[.,]\d{3})*(?:[.,]\d{1,2})?   # number or decimal
        \s*
        (?:m2|m²|mt2|mts2|mts|vrs2|vrs²|vrs|vr2|vr|varas?)\b
        \s*[.,;:]?\s*$                          # ends the line
    """, re.IGNORECASE | re.VERBOSE
)

def read_lines_safely(path: str):
    for enc in ("utf-8", "utf-8-sig", "cp1252", "latin-1"):
        try:
            with open(path, "r", encoding=enc) as f:
                return f.read().splitlines()
        except UnicodeDecodeError:
            continue
    with open(path, "rb") as f:
        return f.read().decode("utf-8", "ignore").splitlines()

def mask_numdot(lines, glue_areas=False):
    """Return (masked_lines, stats). Optionally glue area lines."""
    out = []
    starts = inlines = 0
    start_nums = []
    area_starts = area_tails = 0

    prev = None  # last output line (for quick mutation)

    for idx, orig_ln in enumerate(lines, 1):
        ln = orig_ln

        # 1) NUMDOT at start → "* " (keep leading spaces)
        m = NUMDOT_START.match(ln)
        if m:
            starts += 1
            start_nums.append(int(m.group(2)))
            ln = NUMDOT_START.sub(r"\1* ", ln)

        # 2) NUMDOT inline (won't hit decimals due to lookahead)
        before = ln
        ln = INLINE_NUMDOT.sub("* ", ln)
        if ln != before and not m:
            inlines += 1

        # --- AREA handling (masking + optional glue) ---

        # a) If previous out line ends with area → this line is a continuation
        if glue_areas and out and AREA_TAIL.search(out[-1]) and not NUMDOT_START.match(ln):
            area_tails += 1
            out[-1] = (out[-1].rstrip() + " " + ln.strip()).strip()
            continue

        # b) If this line itself starts with area → attach to previous listing
        if glue_areas and AREA_START.match(ln):
            area_starts += 1
            if out:
                out[-1] = (out[-1].rstrip() + " " + ln.strip()).strip()
            else:
                out.append(ln)  # no previous: keep it (rare at top of file)
            continue

        out.append(ln)

    stats = {
        "total_lines": len(lines),
        "numdot_starts": starts,
        "numdot_inline": inlines,
        "start_numbers": start_nums,
        "area_starts_glued": area_starts,
        "area_tails_glued": area_tails,
    }
    return out, stats




def analyze_sequence(nums):
    """Quick sense of '1,2,3' pattern with resets at 1."""
    if not nums: return {"count": 0, "inc_by_1": 0, "resets": 0, "sample": []}
    inc1, resets = 0, 0
    prev = None
    for n in nums:
        if prev is None:
            resets += 1 if n == 1 else 0
        else:
            if n == prev + 1: inc1 += 1
            elif n == 1: resets += 1
        prev = n
    return {"count": len(nums), "inc_by_1": inc1, "resets": resets, "sample": nums[:30]}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", required=True)
    ap.add_argument("--out", help="Optional output file to write masked text")
    ap.add_argument("--show-samples", type=int, default=12)
    ap.add_argument("--glue-areas", action="store_true",
                help="Attach AREA_START lines to previous row; glue line after AREA_TAIL")

    args = ap.parse_args()

    lines = read_lines_safely(args.file)
    masked, stats = mask_numdot(lines, glue_areas=args.glue_areas)
    seq = analyze_sequence(stats["start_numbers"])

    print(f"\n[mask_numdot] file: {args.file}")
    print(f"  total lines:       {stats['total_lines']}")
    print(f"  NUMDOT @ start:    {stats['numdot_starts']}")
    print(f"  NUMDOT inline:     {stats['numdot_inline']}")
    if seq["count"]:
        denom = max(1, seq["count"] - 1)
        print(f"  sequence sample:   {seq['sample']}")
        print(f"  inc by 1 ratio:    {seq['inc_by_1']}/{denom} "
              f"({seq['inc_by_1']/denom:.0%})  | resets @1: {seq['resets']}")

    # show a few before/after samples where replacement happened
    print("\n[samples]")
    shown = 0
    for i, (orig, new) in enumerate(zip(lines, masked), 1):
        if orig != new:
            print(f"  L{i:04d}  {orig}")
            print(f"        →  {new}")
            shown += 1
            if shown >= args.show_samples:
                break
    if shown == 0:
        print("  (no NUMDOT patterns found)")

    if args.out:
        os.makedirs(os.path.dirname(args.out), exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as f:
            f.write("\n".join(masked) + "\n")
        print(f"\n✔ wrote masked text → {args.out}")

if __name__ == "__main__":
    main()
