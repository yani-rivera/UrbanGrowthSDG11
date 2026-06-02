# parser_utils.py --- Documentation

## Overview

`parser_utils.py` is a modular utility script used across the
newspaper real‑estate listing parsing system.\
It provides shared helpers for numeric normalization, OCR cleanup,
property feature extraction, and semantic detection.\
This module is **internal API** --- consumed by the parser engine (e.g.,
`record_parser.py`) and other extraction modules, not by external
clients.

------------------------------------------------------------------------

## Function Inventory

Below is a complete list of all function definitions present in the
module, based on the provided structure.

### 1. `_normalize_num_token(num_str: str) -> float | None`

Normalizes a number-like token (`"1.200"`, `"3,5"`, `"O"` → `"0"`) into
a float. Used internally by price and numeric parsers.

### 2. `normalize_currency_spacing(text: str) -> str`

Ensures consistent spacing around currency symbols\
(e.g., `"$1000"` → `"$ 1000"` when needed).

### 3. `strip_per_unit_prices(text: str) -> str`

Removes unit-based suffixes such as: - `/m²` - `/ft²` - `/m2`

Used before extracting base prices.

### 4. `clean_text_for_price(text: str) -> str`

Performs cleanup to prepare a string for numeric price extraction: -
remove noise characters\
- unify separators\
- normalize OCR distortions

### 5. `normalize_ocr_text(text)`

Fixes common OCR artifacts: - misread characters\
- incorrect spacing\
- broken number tokens

Used before any extraction steps.

### 6. `extract_area(text: str, config: dict)`

Extracts surface area of a property using configurable patterns. Typical
output: `{"area": 85, "unit": "m2"}`.

### 7. `extract_property_type(text, config)`

Detects whether the listing is for: - house\
- apartment\
- lot\
- PH\
- condo, etc.

Uses keyword + regex-based matching.

### 8. `detect_transaction(text, config)`

Infers transaction intent from text: - sale\
- rent\
- temporary / seasonal

Used by the parsing pipeline before fallback defaults.

### 9. `clean_listing_line(line)`

Final cleanup stage for a listing input line. Removes noise, whitespace,
and invalid characters.

### 10. `_word_to_int(s)`

Internal helper converting Spanish number words into integers: - "uno" →
1\
- "dos" → 2\
- "tres" → 3

Used by bedroom/bathroom extractors.

### 11. `extract_bedrooms(text: str, config: dict | None = None)`

Extracts bedroom count from text: - numeric (`"3 dormitorios"`) - OCR
patterns - number‑words\
Returns: `int | None`.

### 12. `extract_bathrooms(text: str, config: dict | None = None) -> Optional[float]`

Extracts total bathrooms, including fractional baths: - `"1.5 baños"` →
`1.5` - `"dos baños"` → `2`

### 13. `detect_section_context(line: str, config: dict)`

Determines whether a line belongs to a specific semantic section: -
amenities\
- pricing\
- area details\
- location clues

### 14. `extract_transaction(text, config)`

Explicit extractor for transaction keywords. Complements
`detect_transaction`.

------------------------------------------------------------------------

## Regular Expressions Used (Expected)

Although regex bodies are not visible, the functions imply use of
patterns such as:

### Numeric & Price:

    [0-9]+[.,]?[0-9]*
    [^0-9.,]

### Currency:

    ([$€₱])\s*([0-9])

### Area:

    ([0-9]+(?:[.,][0-9]+)?)\s*(m2|m²|ft2|ft²)

### Bedrooms:

    (\d+)\s*(hab|dorm|bed)

### Bathrooms:

    (\d+(?:\.\d+)?)\s*(baños|baths?)

### Transaction:

    (venta|alquiler|rent|sale|temporada)

------------------------------------------------------------------------

## How This Module Is Used

### Internal API (Used by the Parsing Engine)

Functions called directly by `record_parser.py` and other modules: -
`extract_area` - `extract_property_type` - `extract_bedrooms` -
`extract_bathrooms` - `detect_transaction` - `extract_transaction` -
`clean_listing_line`

### Internal Helpers (Not called by clients)

-   `_normalize_num_token`
-   `_word_to_int`
-   `normalize_currency_spacing`
-   `strip_per_unit_prices`
-   `normalize_ocr_text`
-   `clean_text_for_price`
-   `detect_section_context`

### External Clients

No external application or API endpoint calls this module directly. It
is strictly part of the **backend parsing core**.

------------------------------------------------------------------------

## Module Purpose Summary

`parser_utils.py` provides reusable, low‑level building blocks used
throughout the listing‑processing pipeline.\
It standardizes and normalizes raw text so other modules can perform
higher‑level property detail extraction.

------------------------------------------------------------------------

## Version

`Version 2.1`

------------------------------------------------------------------------

## Author Notes

This file is clean and modular.\
No unused functions detected based on the visible structure.\
It is safe to treat this module as a stable foundation for new
extraction modules.

------------------------------------------------------------------------
