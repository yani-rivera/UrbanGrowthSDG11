## Webarchive Processing

### Step 1: Webarchive to HTML Conversion

Archived web pages in `.webarchive` format were converted into HTML files prior to parsing.

This conversion was performed using the macOS native `textutil` utility:

```bash
textutil -convert html <agency>.webarchive -output <agency>_<date>.html