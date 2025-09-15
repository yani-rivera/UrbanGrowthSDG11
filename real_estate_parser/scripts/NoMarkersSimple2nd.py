# scripts/run_agency.py
import argparse, json
from pathlib import Path
import sys,csv
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from modules.SplitByCue import split_by_cue
from modules.ListingUppercaseMask import build_mask, slice_blocks_from_mask
from scripts.NoMarkersSimple import parse_lines, to_schema, write_csv


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", required=True, help="Raw input TXT")
    ap.add_argument("--config", required=True, help="Agency config JSON")
    ap.add_argument("--output", required=True, help="Output directory")
    args = ap.parse_args()

    cfg = json.loads(Path(args.config).read_text(encoding="utf-8"))

    lines = Path(args.file).read_text(encoding="utf-8-sig").splitlines()
    marker = cfg.get("listing_marker", "").upper()
    
    # --- dispatch to right splitter ---
    if marker == "BULLET":
        parsed = parse_lines(lines)  # bullet-style
    elif marker == "CUE":
        parsed = [{"title": r, "raw": r, "prices": []} 
                  for r in split_by_cue(lines, cfg)]
    elif marker == "UPPERCASE":
        mask = build_mask(lines, header_marker=cfg.get("header_marker", "#"))
        records = slice_blocks_from_mask(lines, mask)
        parsed = [{"title": r, "raw": r, "prices": []} for r in records]
    else:
        raise ValueError(f"Unknown listing_marker {marker}")

    # --- schema mapping ---
    final = to_schema(
        parsed,
        agency=cfg["agency"],
        date_str=cfg.get("date", ""),  # or infer from filename
        source_type=cfg.get("source_type", "ocr_manual"),
        ingestion_id=Path(args.file).name,
        pipeline_version="v1.0",
        default_transaction=cfg.get("transaction", "Sale"),
    )

    outdir = Path(args.output)
    outdir.mkdir(parents=True, exist_ok=True)
    outfile = outdir / f"{cfg['agency']}_{Path(args.file).stem}.csv"
    write_csv(outfile, final)
    print(f"✅ Exported {len(final)} listings to {outfile}")

if __name__ == "__main__":
    main()
