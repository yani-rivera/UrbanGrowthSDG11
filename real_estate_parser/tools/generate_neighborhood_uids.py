

#!/usr/bin/env python3
"""
Generate composite neighborhood UIDs as <sector>-<alphanumeric>-<sequential>
--------------------------------------------------------------------------
Preserves Ñ as a distinct letter in the slug (CAMPANA ≠ CAMPAÑA).
Ensures sequential numbers are integers (001, 002, … not 1.0).

Usage
-----
python generate_neighborhood_uids.py \
  --input_csv neighborhoods.csv \
  --sector_col sector \
  --name_col neighborhood \
  --out_csv neighborhoods_with_uid.csv \
  --encoding utf-8 \
  --slug_len 6 --pad_sector 2 --start_seq 1
"""

import argparse, re, unicodedata, sys
from typing import List, Dict, Tuple, Optional
import pandas as pd

# ---------------------------
# Normalization – preserve Ñ
# ---------------------------
_WS_RE = re.compile(r"\s+")
_PUNCT_ALNUM_RE = re.compile(r"[^A-ZÑ0-9]")  # allow A-Z, Ñ, 0-9 only
PREFIX_SLUG_RE = re.compile(r"^(?:COLONI|COLONIA|COL\\.?|BARRIO|RESIDENCIAL|RES\\.?|APARTAM|APT\\.?)\\s+", re.IGNORECASE)

# --- Prefixes to ignore for mnemonic ---
PREFIX_SLUG_RE = re.compile(
    r"^(?:COLONI|COLONIA|COL\.?|BARRIO|RESIDENCIAL|RES\.?|APARTAM|APARTAMENTO[S]?|APT\.?)\s+",
    re.IGNORECASE
)

STOPWORDS = {"DE","DEL","LA","LAS","LOS","EL","Y"}  # expand if you like

def strip_prefix_for_slug(name: str) -> str:
    return PREFIX_SLUG_RE.sub("", str(name)).strip()







def strip_accents_preserve_ene(s: str) -> str:
    s = "" if s is None else str(s)
    s = s.replace("Ñ", "##ENE_UP##").replace("ñ", "##ene_low##")
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = s.replace("##ENE_UP##", "Ñ").replace("##ene_low##", "ñ")
    return s.upper()

def make_slug(name: str, length: int = 6) -> str:
    """
    Build a 6-char mnemonic from the first two meaningful words:
      - strip admin prefixes (COLONIA, COL., BARRIO, RES., etc.)
      - preserve Ñ (CAMPANA != CAMPAÑA)
      - ignore stopwords (DE, DEL, LA, LOS, LAS, EL, Y)
      - take 3 letters from up to 2 words -> 6 chars, pad with X
    """
    # 1) remove generic prefixes
    name = strip_prefix_for_slug(name)

    # 2) normalize (accents off, Ñ preserved), uppercase
    norm = strip_accents_preserve_ene(name)

    # 3) tokenize to words (letters/digits/Ñ)
    tokens = re.findall(r"[A-ZÑ0-9]+", norm)

    # 4) drop stopwords
    sig = [t for t in tokens if t not in STOPWORDS]

    # 5) take up to 2 words, 3 letters each
    parts = []
    for t in sig[:2]:
        parts.append(t[:3])

    if not parts:
        slug = "X"
    else:
        slug = "".join(parts)

    # 6) pad/trim to requested length
    slug = (slug[:length]).ljust(length, "X")
    return slug


def parse_uid(uid: str) -> Optional[Tuple[str, str, int]]:
    if not isinstance(uid, str):
        return None
    parts = uid.strip().split("-")
    if len(parts) != 3:
        return None
    sector, slug, seq_s = parts
    try:
        seq = int(seq_s)
    except ValueError:
        return None
    return sector, slug, seq

# ---------------------------
# Main
# ---------------------------
def main():
    ap = argparse.ArgumentParser(description="Generate <sector>-<slug>-<seq> UIDs (Ñ preserved)")
    ap.add_argument("--input_csv", required=True)
    ap.add_argument("--out_csv", required=True)
    ap.add_argument("--sector_col", default="sector")
    ap.add_argument("--name_col", default="neighborhood")
    ap.add_argument("--existing_uid_col", default=None)
    ap.add_argument("--encoding", default="utf-8")
    ap.add_argument("--slug_len", type=int, default=6)
    ap.add_argument("--pad_sector", type=int, default=2)
    ap.add_argument("--start_seq", type=int, default=1)
    args = ap.parse_args()

    df = pd.read_csv(args.input_csv, encoding=args.encoding)

    for col in (args.sector_col, args.name_col):
        if col not in df.columns:
            sys.exit(f"Missing column '{col}'. Available: {list(df.columns)}")

    # Slug
    df["slug"] = df[args.name_col].apply(
    lambda x: make_slug(strip_prefix_for_slug(x), args.slug_len)
)


    # Sector formatting
    if args.pad_sector > 0:
        df["sector_str"] = df[args.sector_col].astype(str).str.zfill(args.pad_sector)
    else:
        df["sector_str"] = df[args.sector_col].astype(str)

    # Sequence assignment
    start_map: Dict[Tuple[str, str], int] = {}
    seq_values: List[int] = []
    for sec, slug in zip(df["sector_str"], df["slug"]):
        key = (sec, slug)
        base = start_map.get(key, args.start_seq - 1)
        next_seq = base + 1
        start_map[key] = next_seq
        seq_values.append(next_seq)

    df["seq"] = seq_values
    df["seq_str"] = df["seq"].astype(int).astype(str).str.zfill(3)

    # Final UID
    df["uid"] = df["sector_str"] + "-" + df["slug"] + "-" + df["seq_str"]

    # Save
    df.to_csv(args.out_csv, index=False, encoding=args.encoding)
    print(f"✅ Wrote {len(df)} rows to {args.out_csv}")

if __name__ == "__main__":
    main()
