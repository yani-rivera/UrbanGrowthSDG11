# preprocess_listings_v2.6.1.py

## Purpose

`preprocess_listings_v2.6.1.py` is a preprocessing utility designed to transform OCR-derived classified advertisements into a normalized one-listing-per-line representation.

The script performs text sanitation, delimiter normalization, listing-boundary detection, and segmentation prior to structured parsing.

Although newer versions of the framework incorporate preprocessing functionality through reusable modules, this script documents the original preprocessing methodology and remains useful for understanding the evolution of the workflow.

---

# Workflow Position

```text
Scanned Newspaper
        ↓
OCR Text
        ↓
preprocess_listings_v2.6.1.py
        ↓
One Listing Per Line
        ↓
Agency Parser
        ↓
Structured CSV
```

The script operates before structured extraction begins.

---

# Objectives

The preprocessing stage addresses several challenges commonly found in OCR-generated newspaper advertisements:

* OCR character-recognition errors
* Inconsistent listing delimiters
* Broken line formatting
* Multiple advertisements appearing within the same paragraph
* Missing spacing around currencies
* Unit notation inconsistencies
* Unicode encoding artifacts

The output is a cleaner and more consistent representation suitable for parsing.

---

# Command-Line Usage

## Basic Example

```bash
python preprocess_listings_v2.6.1.py \
    --file temp/serpecal_20151228.txt \
    --config config/agency_serpecal.json \
    --agency SERPECAL \
    --out temp/serpecal_20151228_temp.txt
```

---

# Arguments

| Argument   | Required | Description          |
| ---------- | -------- | -------------------- |
| `--file`   | Yes      | OCR text file        |
| `--config` | Yes      | Agency configuration |
| `--agency` | Yes      | Agency identifier    |
| `--out`    | No       | Output file location |

If no output file is provided, the script automatically creates:

```text
<input>_temp.txt
```

---

# Processing Stages

## 1. OCR Sanitation

Function:

```python
ocr_sanitize()
```

Purpose:

Normalize OCR artifacts while preserving advertisement meaning.

Examples include:

### Currency Cleanup

Before:

```text
US$45000
```

After:

```text
US$ 45000
```

---

### Unit Normalization

Before:

```text
mts2
m2
vr2
```

After:

```text
m²
vrs²
```

---

### OCR Error Correction

Before:

```text
bafios
banos
```

After:

```text
baños
```

---

### Unicode Normalization

Removes:

* Soft hyphens
* Non-standard quotation marks
* OCR-generated formatting artifacts

---

## 2. Listing Boundary Detection

The script attempts to determine where one advertisement ends and another begins.

Function:

```python
should_start_new_listing()
```

Boundary detection uses multiple strategies.

---

### Symbol-Based Detection

Examples:

```text
*
•
>
```

Each symbol may indicate a new listing.

---

### Header-Based Detection

Examples:

```text
COL. PALMIRA:
RES. MONSEÑOR:
BARRIO EL CENTRO:
```

These patterns frequently represent advertisement starts.

---

### Capitalized Header Detection

Example:

```text
AMAPALA:
```

This heuristic helps when OCR omits standard prefixes such as:

```text
COL.
RES.
BARRIO
```

---

## 3. Segmentation

Function:

```python
segment_listings()
```

Purpose:

Transform multi-line OCR text into individual advertisements.

Input:

```text
COL. PALMIRA:
Casa 3 hab.
US$ 250,000

COL. MAYA:
Casa 4 hab.
US$ 300,000
```

Output:

```text
COL. PALMIRA: Casa 3 hab. US$ 250,000
COL. MAYA: Casa 4 hab. US$ 300,000
```

Each line becomes a candidate listing.

---

## 4. Marker Normalization

Agency-specific symbols are standardized.

Examples:

Before:

```text
> Casa Palmira
• Casa Palmira
* Casa Palmira
```

After:

```text
* Casa Palmira
```

This simplifies downstream parsing.

---

## 5. Noise Removal

Very short fragments are discarded.

Current threshold:

```python
len(record) >= 12
```

This reduces:

* OCR debris
* Isolated punctuation
* Incomplete advertisement fragments

---

# Agency-Specific Processing

Listing markers are loaded from agency configuration files.

Example:

```json
{
    "listing_symbols": [
        "*",
        "•",
        ">"
    ]
}
```

This allows different newspaper layouts to be processed using the same preprocessing engine.

---

# Output

The script produces a temporary text file containing one advertisement per line.

Example:

```text
Casa en Palmira 3 hab. US$ 250,000
Apartamento en Lomas del Guijarro US$ 1,200
Terreno en El Hatillo 1500 vrs² US$ 198,000
```

This output becomes the input for structured parsing.

---

# Quality-Control Features

## OCR Repair

Corrects common OCR errors.

## Boundary Detection

Uses multiple complementary heuristics.

## Delimiter Standardization

Converts heterogeneous markers into a common format.

## Noise Filtering

Removes likely OCR artifacts.

## Agency Adaptability

Supports agency-specific listing conventions.

---

# Relationship to the Framework

This script represents an early preprocessing implementation whose functionality is now largely incorporated into the framework's modular preprocessing architecture. Nevertheless, it remains an important reference because it formalizes the methodology used to transform OCR-derived newspaper advertisements into a consistent one-listing-per-line format prior to structured extraction.

The core concept introduced by this module—standardizing heterogeneous OCR text into canonical advertisement records before parsing—remains a foundational principle of the SDG-11 Real Estate Framework.
