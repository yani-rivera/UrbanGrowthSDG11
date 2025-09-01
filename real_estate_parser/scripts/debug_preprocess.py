
# scripts/debug_preprocess.py
import re, json, sys
from modules.agency_preprocess import preprocess_listings

def load_lines(path):
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        return [ln.rstrip("\n") for ln in f]

def dbg_preprocess(file_path, marker=None, agency=None):
    raw = load_lines(file_path)
    rows = preprocess_listings(raw, marker=marker, agency=agency)
    print(f"[DBG] raw_lines={len(raw)} → listings_preserved={len(rows)}")
    for i, r in enumerate(rows[:50], 1):
        print(f"{i:03d} | {r}")
    return rows

if __name__ == "__main__":
    # Usage:
    # python scripts/debug_preprocess.py data/raw/AGENCY/sample.txt "-" AgencyName
    fp = sys.argv[1]
    marker = None if sys.argv[2] == "None" else sys.argv[2]
    agency = None if len(sys.argv) < 4 or sys.argv[3] == "None" else sys.argv[3]
    dbg_preprocess(fp, marker=marker, agency=agency)
