#!/usr/bin/env python3
# add_uid_from_columns.py
import argparse
import re
from pathlib import Path
import pandas as pd

def _slugify_series(s: pd.Series) -> pd.Series:
    return (
        s.fillna("")
         .astype(str).str.lower().str.strip()
         .str.replace(r"[^a-z0-9]+", "-", regex=True)
         .str.strip("-")
         .replace("", "na")
    )

def _yyyymmdd_series(s: pd.Series) -> pd.Series:
    # dayfirst=True is safer for LATAM-style dates; adjust if your column is US-style
    dt = pd.to_datetime(s, errors="coerce", dayfirst=True)
    return dt.dt.strftime("%Y%m%d").fillna("00000000")

def add_uid_from_cols(
    df: pd.DataFrame,
    agency_col: str = "agency",
    date_col: str = "date",
    uid_col: str = "uid",
    seq_width: int = 4,
    sort_keys: list[str] | None = None,  # optional stable order inside (agency,date)
) -> pd.DataFrame:
    out = df.copy()

    # Normalize headers (BOM/NBSP/trim) so " price " etc. don't break
    out.columns = (
        out.columns.str.replace("\ufeff", "", regex=False)
                  .str.replace("\u00a0", " ", regex=False)
                  .str.strip()
    )

    if agency_col not in out.columns:
        raise KeyError(f"agency column '{agency_col}' not found")
    if date_col not in out.columns:
        raise KeyError(f"date column '{date_col}' not found")

    ag_slug = _slugify_series(out[agency_col])
    ymd = _yyyymmdd_series(out[date_col])

    # Sequence per (agency_slug, yyyymmdd)
    if sort_keys:
        keys = [k for k in sort_keys if k in out.columns]
        tmp = out.assign(_ag=ag_slug, _dk=ymd).sort_values(["_ag", "_dk"] + keys, kind="stable")
        seq = (tmp.groupby(["_ag", "_dk"]).cumcount() + 1).reindex(out.index).fillna(0).astype(int)
    else:
        tmp = out.assign(_ag=ag_slug, _dk=ymd)
        seq = tmp.groupby(["_ag", "_dk"]).cumcount() + 1

    out[uid_col] = ag_slug + "-" + ymd + "-" + seq.astype(str).str.zfill(seq_width)

    # Put UID first, keep all other columns in original order
    # Put UID first, keep all other columns in their original order
# Put UID first, keep all other columns in their original order
    cols = [uid_col] + [c for c in out.columns if c != uid_col]
    print(cols)
    out = out.loc[:, cols]


