
# scripts/ingest.py
choices=["webscrape","ocr_auto","ocr_manual","manual"])
ap.add_argument("--file", required=True)
ap.add_argument("--config", required=True)
ap.add_argument("--output-dir", required=True)
ap.add_argument("--pipeline-version", default=DEFAULT_PIPELINE_VERSION)
ap.add_argument("--ingestion-id", default="")
args = ap.parse_args()

agency = infer_agency(args.config)
date = infer_date(args.file)
ing_id = args.ingestion_id or hashlib.md5(args.file.encode("utf-8")).hexdigest()[:10]

# manual path short-circuit: adapter returns rows ready to write
if args.source == "manual":
rows = manual_adapter.to_rows(args.file)
# make sure provenance fields are present
for i, r in enumerate(rows, 1):
r.setdefault("Listing ID", i)
r.setdefault("source_type", "manual")
r.setdefault("ingestion_id", ing_id)
r.setdefault("pipeline_version", args.pipeline_version)
return write_csv(rows, agency, date, args.output_dir)

# text-based sources → run preprocess + parse
raw_lines = load_raw_lines(args.source, args.file)
cfg = json.load(open(args.config, encoding="utf-8"))
configure_preprocess(cfg)
listings = preprocess_listings(raw_lines, marker=cfg.get("listing_marker"), agency=agency)

current_tx = current_type = current_cat = None
rows = []
for i, ln in enumerate(listings, 1):
tx, ty, cat = detect_section_context(ln, cfg)
if tx or ty or cat:
current_tx, current_type, current_cat = tx or current_tx, ty or current_type, cat or current_cat
continue
parsed = parse_record(ln, cfg, agency=agency, date=date, listing_no=i,
default_transaction=current_tx,
default_type=current_type,
default_category=current_cat)
rows.append(format_listing_row(parsed, ln, i,
source_type=args.source,
ingestion_id=ing_id,
pipeline_version=args.pipeline_version))

write_csv(rows, agency, date, args.output_dir)


def write_csv(rows, agency, date, output_dir):
outdir = os.path.join(output_dir, agency, date[:4])
os.makedirs(outdir, exist_ok=True)
outpath = os.path.join(outdir, f"{agency}_{date.replace('-', '')}.csv")
with open(outpath, "w", newline="", encoding="utf-8-sig") as outcsv:
writer = csv.DictWriter(outcsv, fieldnames=FIELDNAMES)
writer.writeheader(); writer.writerows(rows)
print(f"wrote {len(rows)} rows → {outpath}")

if __name__ == "__main__":
main()