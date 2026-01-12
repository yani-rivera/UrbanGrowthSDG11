# record_parser.py — Documentation (GitHub Ready)

## Script Name
**File:** `record_parser.py`  
**Role:** Main per-listing parser/orchestrator.

---

## Overview

`record_parser.py` is the **central orchestrator** of the listing‑parsing system.  
It takes a raw listing text line and transforms it into a structured dictionary by coordinating multiple extractor utilities distributed across the `modules/` package.

This script does **not** contain heavy parsing logic inside itself — instead, it delegates tasks to specialized modules such as:

- `parser_utils`  
- numeric extractors  
- area extractors  
- property‑type detectors  
- transaction detectors  
- OCR cleaners  

This design keeps `record_parser.py` clean, maintainable, and highly modular.

---

## Function Inventory (All `def` in This Script)

This module contains **exactly one function definition**.  
Below is the full inventory of all `def` in `record_parser.py`:

### 1. `parse_record(ln, config, ..., default_transaction=None, default_category=None)`

**Type:** Public internal API (called by your backend parsing pipeline, not by external clients directly).

**Purpose:**  
Transforms one unstructured listing text line (`ln`) into a standardized Python dictionary.

**High‑Level Steps:**
1. Normalize the raw text (`ln`).
2. Pass the normalized text into various extractors:
   - area  
   - bedrooms  
   - bathrooms  
   - price  
   - property type  
   - transaction  
3. Merge extraction results into a `parsed` dictionary.
4. Apply default transaction or category if extraction fails.
5. Generate a fallback title (first 60 chars of normalized text or an existing title field).
6. Return the final structured record.

**Parameters (conceptual):**

| Name                 | Type            | Description                                         |
|----------------------|-----------------|-----------------------------------------------------|
| `ln`                 | `str`           | Raw listing line text                               |
| `config`             | `dict`          | Parsing rules / settings for the current agency     |
| `default_transaction`| `str \| None`   | Optional fallback transaction type (e.g. "sale")  |
| `default_category`   | `str \| None`   | Optional fallback property category (e.g. "house")|
| `...`                | varies          | Additional internal options depending on pipeline   |

**Return Value:**

A dictionary containing normalized fields such as:

```python
{
  "beds": 3,
  "baths": 2,
  "area": 120,
  "price": 350000,
  "transaction": "sale",
  "category": "house",
  "title": "Hermosa casa de 3 dormitorios cerca del centro..."
}
```

> 🔎 **Note:** There are no other `def` functions defined in this file.

---

## Regular Expressions Inventory

`record_parser.py` itself does **not** define or use any regular expressions directly.

All regex‑based extraction and pattern matching is delegated to lower‑level modules, for example:

- `parser_utils.py`
- numeric/price extractors
- area extractors
- property‑type detectors
- transaction detectors
- text normalization helpers

### Regex Inventory for `record_parser.py`:

| # | Regex Literal | Used In | Notes |
|---|--------------|---------|-------|
| – | *None*       | –       | This script does not declare regex patterns |

So if you are searching for regex logic, you should inspect the utility modules instead of this orchestrator.

---

## How `parse_record` Is Called (API vs Client)

### Public/Internal API

`parse_record()` is the **single entry point** that other backend components call in order to parse a listing.

Typical usage from another module:

```python
from record_parser import parse_record

parsed = parse_record(line, agency_config, default_transaction="sale")
```

### Called By

- Batch processors that read agency TXT files  
- ETL jobs that normalize listing feeds  
- Backend services that ingest or re‑index listings  

### Not Called Directly By

- Frontend clients  
- External users  
- Public HTTP APIs (they call higher‑level services, which then call `parse_record`)

In other words: **this is an internal backend API**, not a public client API.

---

## Responsibilities of `record_parser.py`

1. **Input Normalization**  
   - Clean and normalize `ln` before extraction.

2. **Delegation to Specialized Extractors**  
   - Call functions in `modules/` (like `parser_utils`) to extract:
     - area  
     - beds  
     - baths  
     - price  
     - property type  
     - transaction  

3. **Aggregation of Results**  
   - Build a single `parsed` dictionary from multiple extraction steps.

4. **Defaults & Fallbacks**  
   - Apply `default_transaction` and `default_category` when extraction fails.
   - Generate a simple fallback `title` if one is not provided.

5. **Return a Clean Record**  
   - Provide a structured, consistent representation of a listing that other systems can store, index, or analyze.

---

## Version & Maintenance Notes

- This documentation reflects a version of `record_parser.py` where **`parse_record()` is the only function** in the script.
- The file has been cleaned and refactored; no dead/unused defs remain.
- The module is intentionally thin; new parsing rules should go into helper modules, not into this file.

---

