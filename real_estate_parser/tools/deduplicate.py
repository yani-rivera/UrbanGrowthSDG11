#!/usr/bin/env python3
"""
Deduplicate listing lines inside block headers and sort blocks and listings.

Rules:
- Headers (#...) are preserved
- Listings (* ...) are deduplicated ONLY within the same block
- Same listing under different blocks is kept
- Blocks are sorted alphabetically by header
- Listings inside blocks are sorted by text AFTER '* '
- UTF-8-SIG safe
"""

import argparse
from pathlib import Path


def sort_key(line: str) -> str:
    if line.startswith("* "):
        return line[2:].lower()
    return line.lower()


def main():
    ap = argparse.ArgumentParser(
        description="Deduplicate TXT listings, sort blocks and listings"
    )
    ap.add_argument("--input", required=True, help="Input TXT file")
    ap.add_argument("--output", required=True, help="Output TXT file")
    args = ap.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)

    blocks = {}
    seen_per_block = {}
    current_block = None

    with input_path.open("r", encoding="utf-8-sig") as f:
        for raw_line in f:
            line = raw_line.rstrip("\n")

            # Header
            if line.startswith("#"):
                current_block = line.strip()
                blocks.setdefault(current_block, [])
                seen_per_block.setdefault(current_block, set())
                continue

            # Listing
            if line.startswith("*"):
                if current_block is None:
                    current_block = "__NO_HEADER__"
                    blocks.setdefault(current_block, [])
                    seen_per_block.setdefault(current_block, set())

                if line not in seen_per_block[current_block]:
                    seen_per_block[current_block].add(line)
                    blocks[current_block].append(line)
                continue

            # Other lines (rare)
            if current_block is not None:
                blocks[current_block].append(line)

    # Sort block headers
    sorted_headers = sorted(h for h in blocks if h != "__NO_HEADER__")

    with output_path.open("w", encoding="utf-8") as out:
        for header in sorted_headers:
            out.write(header + "\n")

            # Sort listings inside block correctly
            for line in sorted(blocks[header], key=sort_key):
                out.write(line + "\n")

            out.write("\n")

        # Orphan listings last (if any)
        if "__NO_HEADER__" in blocks:
            for line in sorted(blocks["__NO_HEADER__"], key=sort_key):
                out.write(line + "\n")

    print(f"[OK] Deduplicated and correctly sorted file written to: {output_path}")


if __name__ == "__main__":
    main()
