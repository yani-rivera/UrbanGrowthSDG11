#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Add per-(agency,date) sequential UID as the FIRST column of a CSV.
- Keeps ALL original columns
- Uses existing columns: `agency` and `date` (configurable via flags)
- UID format: {mnemonic-or-slug}-{YYYYMMDD}-{0001}
- UTF-8-SIG I/O for Excel compatibility
- Optional external mnemonic maps (TXT/CSV/JSON)

CSV mnemonic file must have columns: `agency`, `mnemonic` (optional `aliases` pipe/comma-separated)
TXT mnemonic file expects lines like:  Agency Name = mnemonic   (lines starting with # are ignored)
JSON mnemonic file must be an object mapping agency name to mnemonic.
"""
import argparse
import json
import re
import unicodedata
from pathlib import Path

import pandas as pd

# ---------- helpers ----------

def _normalize_headers(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = (
        df.columns
          .str.replace("\ufeff", "", regex=False)   # BOM
          .str.replace("\u00a0", " ", regex=False)  # NBSP
          .str.strip()
    )
    return df


def _strip_accents(s: str) -> str:
    if not isinstance(s, str):
        s = str(s) if s is not None else ""
    s = unicodedata.normalize("NFKD", s)
    return "".join(ch for ch in s if not unicodedata.combining(ch))


def _norm_key(s: str) -> str:
    """Normalize an agency name for matching (case/space/diacritics-insensitive)."""
    s = _strip_accents(s).lower().strip()
    s = re.sub(r"[^a-z0-9]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _ensure_slug(s: str) -> str:
    s = (s or "").lower().strip()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s or "na"


# ---------- mnemonic config loaders ----------

def load_mnemonic_map(files=None, encoding: str = "utf-8-sig") -> dict:
    """Load mapping of agency name -> mnemonic (slug) from TXT/CSV/JSON files.
    Matching is case-insensitive and accent-insensitive. Later files override earlier ones.
    """
    m: dict[str, str] = {}
    if not files:
        return m
    for spec in files:
        p = Path(spec)
        if not p.exists():
            print(f"[warn] mnemonics file not found: {p}")
            continue
        suf = p.suffix.lower()
        try:
            if suf == ".csv":
                dfm = pd.read_csv(p, encoding=encoding, dtype=str)
                cols = {c.lower().strip(): c for c in dfm.columns}
                if "agency" not in cols or "mnemonic" not in cols:
                    print(f"[warn] CSV {p} missing required columns 'agency' and 'mnemonic'")
                    continue
                c_ag = cols["agency"]; c_mn = cols["mnemonic"]; c_al = cols.get("aliases")
                for _, r in dfm.iterrows():
                    names = [r.get(c_ag, "")] 
                    if c_al and isinstance(r.get(c_al), str):
                        names += [a.strip() for a in re.split(r"[|,]", r[c_al]) if a.strip()]
                    mn = _ensure_slug(r.get(c_mn, ""))
                    for nm in names:
                        key = _norm_key(nm)
                        if key:
                            m[key] = mn
            elif suf == ".json":
                obj = json.load(open(p, "r", encoding=encoding))
                if isinstance(obj, dict):
                    for nm, mn in obj.items():
                        key = _norm_key(nm)
                        if key:
                            m[key] = _ensure_slug(str(mn))
                else:
                    print(f"[warn] JSON {p} must be an object mapping agency->mnemonic")
            else:  # TXT
                with open(p, "r", encoding=encoding, newline="") as fh:
                    for line in fh:
                        line = line.strip()
                        if not line or line.startswith("#"):
                            continue
                        if "=" in line:
                            nm, mn = line.split("=", 1)
                            key = _norm_key(nm)
                            if key:
                                m[key] = _ensure_slug(mn)
        except Exception as e:
            print(f"[warn] failed to read mnemonics from {p}: {e}")
    return m


# ---------- core ----------

def _yyyymmdd_series_flexible(s: pd.Series) -> pd.Series:
    """Try day-first first (LATAM), then month-first for leftovers."""
    s = s.astype(str)
    dt1 = pd.to_datetime(s, errors="coerce", format="%Y-%m-%d")
    ymd = dt1.dt.strftime("%Y%m%d")
    mask = dt1.isna()
    if mask.any():
        dt2 = pd.to_datetime(s[mask], errors="coerce", format="%Y-%m-%d")
        ymd = ymd.copy()
        ymd.loc[mask] = dt2.dt.strftime("%Y%m%d")

        




    return ymd.fillna("00000000").replace("NaT", "00000000")


def add_uid_from_cols(
    df: pd.DataFrame,
    agency_col: str = "agency",
    date_col: str = "date",
    uid_col: str = "uid",
    seq_width: int = 4,
    sort_keys: list[str] | None = None,
    mnemonic_map: dict | None = None,
    mnemonic_required: bool = False,
) -> pd.DataFrame:
    out = _normalize_headers(df)

    if agency_col not in out.columns:
        raise KeyError(f"agency column '{agency_col}' not found; available: {list(out.columns)}")
    if date_col not in out.columns:
        raise KeyError(f"date column '{date_col}' not found; available: {list(out.columns)}")

    # agency mnemonic (from map) or fallback to slugified agency name
    if mnemonic_map:
        keys = out[agency_col].fillna("").astype(str).map(_norm_key)
        mapped = keys.map(lambda k: mnemonic_map.get(k, ""))
        if mnemonic_required and (mapped.eq("") | mapped.isna()).any():
            missing = sorted(set(keys[(mapped.eq("") | mapped.isna())]))
            raise SystemExit(f"[error] missing mnemonic for agencies: {missing[:10]}{' ...' if len(missing)>10 else ''}")
        ag_slug = mapped.where(mapped.astype(bool), out[agency_col].fillna("").astype(str).map(_ensure_slug))
    else:
        ag_slug = out[agency_col].fillna("").astype(str).map(_ensure_slug)

    ymd = _yyyymmdd_series_flexible(out[date_col])

    base = out.assign(_ag=ag_slug, _dk=ymd)

    # Sequence per (agency,date)
    if sort_keys:
        keys = [c for c in sort_keys if c in base.columns]
        if keys:
            tmp = base.sort_values(["_ag", "_dk"] + keys, kind="stable")
        else:
            tmp = base
        seq_sorted = tmp.groupby(["_ag", "_dk"]).cumcount() + 1
        seq = pd.Series(index=base.index, dtype="Int64")
        seq.loc[tmp.index] = seq_sorted
        seq = seq.fillna(0).astype(int)
    else:
        seq = base.groupby(["_ag", "_dk"]).cumcount() + 1

    out[uid_col] = ag_slug + "-" + ymd + "-" + seq.astype(str).str.zfill(seq_width)

    # Put UID first, keep all other columns in their original order
    cols = [uid_col] + [c for c in df.columns if c != uid_col]
    return out.loc[:, cols]


# ---------- CLI ----------

def main():
    ap = argparse.ArgumentParser(description="Add per-(agency,date) sequential UID as first column.")
    ap.add_argument("-i", "--input", required=True, help="Input CSV")
    ap.add_argument("-o", "--output", required=True, help="Output CSV")
    ap.add_argument("--agency-col", default="agency", help="Agency column name")
    ap.add_argument("--date-col", default="date", help="Date column name")
    ap.add_argument("--uid-col", default="Listing_uid", help="UID column name to create")
    ap.add_argument("--seq-width", type=int, default=4, help="Zero-pad width for the sequence")
    ap.add_argument("--sort-keys", default="", help="Comma-separated columns to stabilize order inside each (agency,date)")
    ap.add_argument("--encoding", default="utf-8-sig", help="CSV encoding for read/write")
    ap.add_argument("--mnemonics", nargs="*", help="TXT/CSV/JSON files mapping agency->mnemonic (CSV needs 'agency' and 'mnemonic'; optional 'aliases'). Later files override earlier.")
    ap.add_argument("--mnemonic-required", action="store_true", help="Fail if an agency has no mnemonic mapping (otherwise fallback to slug)")
    args = ap.parse_args()

    sort_keys = [s.strip() for s in args.sort_keys.split(',') if s.strip()]

    df = pd.read_csv(args.input, encoding=args.encoding, dtype=str)
    m = load_mnemonic_map(args.mnemonics, encoding=args.encoding)
    out = add_uid_from_cols(
        df,
        agency_col=args.agency_col,
        date_col=args.date_col,
        uid_col=args.uid_col,
        seq_width=args.seq_width,
        sort_keys=sort_keys or None,
        mnemonic_map=m or None,
        mnemonic_required=args.mnemonic_required,
    )
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(args.output, index=False, encoding=args.encoding)
    print(f"[done] {len(out)} rows → {args.output}  (added '{args.uid_col}' as first column)")


if __name__ == "__main__":
    main()
