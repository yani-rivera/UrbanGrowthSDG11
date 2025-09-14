#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import argparse, glob, json, os, sys

# --- import orchestrator from pipeline/ ---
ROOT = Path(__file__).resolve().parents[1]     # repo root
sys.path.insert(0, str(ROOT))
from pipeline.orchestrator import run_orchestrator  # make sure this exists

def load_cfg(path: str) -> dict:
    ext = Path(path).suffix.lower()
    with open(path, "r", encoding="utf-8") as f:
        if ext == ".json":                     # your default
            return json.load(f)
        elif ext in (".yml", ".yaml"):         # optional, only if you ever pass YAML
            import yaml                         # lazy import so no dependency if unused
            return yaml.safe_load(f)
        # fallback: try JSON
        return json.load(f)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", required=True, help="YYYYMMDD e.g. 20151028")
    ap.add_argument("--config", required=True, help="Path to agencies JSON")
    ap.add_argument("--out", default="output", help="Output dir (for CSV)")
    args = ap.parse_args()

    date = args.date
    year = date[:4]

    cfg = load_cfg(args.config)

    # Stage tmp/raw_agencies_<date>/<Agency>.txt from your pre files
    stage = Path("tmp") / f"raw_agencies_{date}"
    stage.mkdir(parents=True, exist_ok=True)

    staged = 0
    for agency in cfg.get("agencies", {}):
        pat = f"{args.out}/{agency}/pre/{year}/*{date}*.txt"   # adjust if your layout differs
        files = sorted(glob.glob(pat))
        if not files:
            continue
        text = "\n".join(Path(p).read_text(encoding="utf-8", errors="ignore") for p in files)
        (stage / f"{agency}.txt").write_text(text, encoding="utf-8")
        staged += 1

    print(f"[run_pipeline] staged agencies: {staged} at {stage}")

    out_csv = Path(args.out) / f"cleaned_listings_{date}.csv"
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    # call positionally to match any of:
#   def run_orchestrator(raw_dir, config, out_csv)
#   def run_orchestrator(raw_dir, cfg, out_csv)
    run_orchestrator(str(stage), str(args.config), str(out_csv))

    print(f"[run_pipeline] wrote {out_csv}")

if __name__ == "__main__":
    main()


