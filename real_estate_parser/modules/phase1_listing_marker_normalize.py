# modules/phase1_listing_marker_normalize.py
import os, io, re
from datetime import datetime

import sys,csv
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


#==========================
from modules.mask_anychar import normalize_listing_leader

def _ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)

def _is_writable_dir(path: str) -> bool:
    try:
        _ensure_dir(path)
        test = os.path.join(path, ".writetest")
        with open(test, "w") as f:
            f.write("ok")
        os.remove(test)
        return True
    except Exception:
        return False

def _phase1_root(cfg: dict) -> str:
    # 1) explicit in cfg
    root = (cfg or {}).get("phase1_output_root")
    if root:
        return root
    # 2) env var
    env = os.getenv("PHASE1_ROOT")
    if env:
        return env
    # 3) /data/phase1 if writable
    candidate = "/data/phase1"
    if _is_writable_dir(candidate):
        return candidate
    # 4) project-local fallback
    return os.path.join(os.getcwd(), "data", "phase1")

def _infer_year_from_path(raw_file: str) -> str:
    m = re.search(r"\b(20\d{2})\b", raw_file)
    return m.group(1) if m else str(datetime.now().year)

def _phase1_output_path(raw_file: str, cfg: dict, agency: str, year: str) -> str:
    base_root = _phase1_root(cfg)
    base = os.path.basename(raw_file)
    root, _ = os.path.splitext(base)
    outdir = os.path.join(base_root, agency.upper(), year)
    _ensure_dir(outdir)
    return os.path.join(outdir, f"{root}_phase1.txt")

def run_phase1_normalize_listing_marker(
    raw_file: str,
    cfg: dict,
    agency: str = None,
    year: str = None,
    test_mode: bool = False,
) -> str:
    """
    Phase-1: normalize ONLY leading listing markers per cfg, write Phase-1 file, return its full path.

    Required in production:
      - agency: must be provided by caller (parser_agency). If missing and not test_mode -> ValueError.
    Test convenience:
      - if agency is None and test_mode=True, uses 'ADUM'.
    Year:
      - if not provided, infer from path (first 20xx), else fall back to current year.

    Config keys:
      - listing_marker (str): canonical marker (e.g. "*")
      - listing_marker_tochange (str|list[str]): markers to normalize (at line start only)
      - phase1_output_root (optional): override output root
    """
    if agency is None:
        if test_mode:
            agency = "ADUM"
        else:
            # you can relax this by inferring from parent dir if you prefer,
            # but as requested: for real agencies, require explicit agency.
            raise ValueError("agency is required for Phase-1 runs (not in test_mode)")

    year = year or _infer_year_from_path(raw_file)

    out_path = _phase1_output_path(raw_file, cfg, agency, year)

    with io.open(raw_file, "r", encoding="utf-8", errors="replace", newline="") as fin, \
         io.open(out_path, "w", encoding="utf-8", newline="") as fout:
        for line in fin:
            cleaned = normalize_listing_leader(line.rstrip("\r\n"), cfg)
            fout.write(cleaned + "\n")

    return out_path

if __name__ == "__main__":
    import sys, json
    if len(sys.argv) < 2:
        print("usage: python -m modules.phase1_listing_marker_normalize <raw_file> [cfg_json_path] [AGENCY] [YEAR]")
        sys.exit(1)

    raw_file = sys.argv[1]
    cfg = {"listing_marker": "*"}
    if len(sys.argv) > 2 and sys.argv[2].strip():
        with io.open(sys.argv[2], "r", encoding="utf-8") as f:
            cfg = json.load(f)

    agency = sys.argv[3] if len(sys.argv) > 3 and sys.argv[3].strip() else None
    year   = sys.argv[4] if len(sys.argv) > 4 and sys.argv[4].strip() else None

    # CLI defaults to test_mode if agency not provided
    out = run_phase1_normalize_listing_marker(raw_file, cfg, agency=agency, year=year, test_mode=(agency is None))
    print(f"[phase1] wrote: {out}")
