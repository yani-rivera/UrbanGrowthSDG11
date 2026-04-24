# Webarchive Processing Workflow

This section describes the preprocessing steps used to transform archived web pages (`.webarchive`) into standardized plain-text files for downstream parsing.

---

Webarchive to HTML Conversion

Archived web pages in `.webarchive` format were converted into HTML files prior to parsing.

This conversion was performed using the macOS native `textutil` utility:

```bash
textutil -convert html <agency>.webarchive -output <agency>_<date>.html

HTML TO TEXT Conversion

python scripts/html_to_text_webarchive.py \
  --input <agency>_<date>.html \
  --output <agency>_<date>.txt \
  --debug
