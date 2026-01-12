#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
word_cleaner.py

Cleans a specified column in a CSV by removing words/phrases
listed in a .txt file (one per line). Keeps ALL other columns intact.

Usage:
  # Clean and save to a new file
  python tools/word_cleaner.py \
    --input listings.csv \
    --output listings.cleaned.csv \
    --col neighborhood_clean \
    --words-file config/remove_words.txt

  # Clean the file in-place (overwrite input file)
  python tools/word_cleaner.py \
    --input listings.csv \
    --col neighborhood_clean \
    --words-file config/remove_words.txt \
    --inplace
"""

import argparse
import re
import sys
import pandas as pd
from pathlib import Path

def read_words_file(path: str) -> list[str]:
    with open(path, "r", encoding="utf-8-sig") as f:
        return [line.strip() for line in f if line.strip()]

def build_pattern(words: list[str]) -> re.Pattern:
    """
    Build a regex that removes both single words and multi-word phrases.
    - Matches case-insensitively
    - Ignores multiple spaces or punctuation between words
    - Matches whole words/phrases, not substrings
    """
    # Sort longer phrases first to avoid partial matches (e.g. "los olivos" before "olivos")
    words = sorted(set(w.strip() for w in words if w.strip()), key=len, reverse=True)

    # Build phrase-aware regex pattern
    escaped = []
    for w in words:
        # Replace internal spaces with a flexible matcher (any whitespace or punctuation)
        part = re.escape(w)
        part = part.replace(r"\ ", r"[\s,.]*")  # tolerate commas, dots, or spaces
        escaped.append(part)

    # \b boundaries only around phrase edges, not inside
    pat = r"(?i)\b(" + "|".join(escaped) + r")\b"
    return re.compile(pat)


def remove_words_from_series(series: pd.Series, pattern: re.Pattern):
    """Return cleaned series, and count how many cells changed."""
    original = series.fillna("").astype(str)
    cleaned = original.apply(lambda x: pattern.sub("", x))
    cleaned = cleaned.str.replace(r"\s+", " ", regex=True).str.strip()
    changes = (original != cleaned).sum()
    return cleaned, changes

def main():
    parser = argparse.ArgumentParser(description="Clean a CSV column by removing words from a .txt list.")
    parser.add_argument("--input", required=True, help="Path to input CSV")
    parser.add_argument("--output", help="Path to output CSV (ignored if --inplace is used)")
    parser.add_argument("--col", required=True, help="Column to clean")
    parser.add_argument("--words-file", required=True, help="Path to .txt with one word/phrase per line")
    parser.add_argument("--encoding", default="utf-8-sig", help="CSV encoding (default: utf-8-sig)")
    parser.add_argument("--inplace", action="store_true", help="Overwrite the input file directly")
    args = parser.parse_args()

    try:
        df = pd.read_csv(args.input, dtype=str, encoding=args.encoding)
    except Exception as e:
        sys.stderr.write(f"[ERROR] Could not read input CSV: {e}\n")
        sys.exit(1)

    if args.col not in df.columns:
        sys.stderr.write(f"[ERROR] Column '{args.col}' not found. Found: {list(df.columns)}\n")
        sys.exit(1)

    words = read_words_file(args.words_file)
    if not words:
        sys.stderr.write("[WARN] Words file is empty. No changes applied.\n")
        changes = 0
    else:
        pattern = build_pattern(words)
        df[args.col], changes = remove_words_from_series(df[args.col], pattern)

    # Decide output path
    if args.inplace:
        out_path = Path(args.input)
    else:
        if not args.output:
            sys.stderr.write("[ERROR] You must provide --output unless using --inplace.\n")
            sys.exit(1)
        out_path = Path(args.output)

    df.to_csv(out_path, index=False, encoding=args.encoding)

    # === Summary ===
    print("\n=== Word Cleaner Summary ===")
    print(f"Input file     : {args.input}")
    print(f"Output file    : {out_path}")
    print(f"Column cleaned : {args.col}")
    print(f"Words file     : {args.words_file}")
    print(f"Rows total     : {len(df)}")
    print(f"Rows modified  : {changes}")
    print("[OK] Done.\n")

if __name__ == "__main__":
    main()
