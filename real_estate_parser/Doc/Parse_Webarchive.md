
## Step 1: Webarchive to Text Conversion

Archived web pages in `.webarchive` format were converted into HTML and text files prior to parsing.

This conversion was performed using the macOS native `textutil` utility:

```bash
textutil -convert html <agency>.webarchive -output <agency>_<date>.html


## Step 2: HTML to Text Extraction

The HTML files generated from `.webarchive` conversion were processed using a custom Python script to extract clean textual content for parsing.

Command:

```bash
python scripts/html_to_text_webarchive.py \
  --input <agency>_<date>.html \
  --output <agency>_<date>.txt \
  --debug