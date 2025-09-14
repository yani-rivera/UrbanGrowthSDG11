
# adapters/ocr_manual_adapter.py

def to_raw_lines(txt_path):
with open(txt_path, "r", encoding="utf-8", errors="ignore") as fh:
for ln in fh:
yield ln.rstrip("\n")

# adapters/ocr_auto_adapter.py — identical to ocr_manual for now

# adapters/webscrape_adapter.py — assume you saved scraped HTML/JSON → text lines elsewhere
# Placeholder: adapt from your actual web scraping output

def to_raw_lines(scraped_text_path):
with open(scraped_text_path, "r", encoding="utf-8", errors="ignore") as fh:
for ln in fh:
yield ln.rstrip("\n")

# adapters/manual_adapter.py — manual rows already structured (CSV). Normalize columns.
import csv

def to_rows(csv_path):
rows = []
with open(csv_path, encoding="utf-8-sig") as fh:
rd = csv.DictReader(fh)
for i, r in enumerate(rd, 1):
# ensure AT/area unit canonicals exist
r.setdefault("AT_unit", "vrs2" if r.get("AT") else "")
r.setdefault("area_unit", "m2" if r.get("area") else "")
r.setdefault("Listing ID", r.get("Listing ID", i))
rows.append(r)
return rows