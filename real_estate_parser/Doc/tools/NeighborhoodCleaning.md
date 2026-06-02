# Neighborhood Cleaning Module (`clean_neighborhoods.py`)

## Purpose

The Neighborhood Cleaning Module standardizes extracted neighborhood names while preserving the original source text.

The module is designed to address the substantial variability present in historical newspaper advertisements, OCR outputs, and real-estate listings, where the same neighborhood may appear under multiple spellings, abbreviations, encodings, or descriptive formats.

Unlike neighborhood matching systems, this module performs cleaning and normalization only. No geographic matching or neighborhood assignment occurs at this stage.

---

# Position Within the SDG-11 Pipeline

```text
Raw Neighborhood Text
        ↓
Neighborhood Cleaning
        ↓
Neighborhood Clean
        ↓
Neighborhood Normalization Key
        ↓
Neighborhood Matching
        ↓
GIS Integration
        ↓
Aggregation
```

---

# Design Philosophy

The module follows three core principles:

## 1. Preserve Original Values

The original extracted neighborhood field is never modified.

Example:

```text
Col. El Hatillo, casa de lujo
```

remains available in the source dataset.

---

## 2. Produce Human-Readable Output

A cleaned version is generated for inspection and review.

Example:

```text
EL HATILLO
```

---

## 3. Produce Machine-Friendly Keys

An optional normalized key can be generated for matching and joins.

Example:

```text
EL HATILLO
```

becomes:

```text
EL HATILLO
```

or

```text
COL. SAN JOSÉ
```

becomes:

```text
COL SAN JOSE
```

---

# Output Fields

The module adds:

| Field                   | Purpose                     |
| ----------------------- | --------------------------- |
| neighborhood_clean      | Human-readable cleaned text |
| neighborhood_clean_norm | Matching key (optional)     |

The original neighborhood field remains unchanged.

---

# OCR and Encoding Repair

Historical newspaper archives frequently contain encoding problems.

Examples:

| Corrupted | Corrected |
| --------- | --------- |
| Ã±        | ñ         |
| Ã¡        | á         |
| √±        | ñ         |
| √ë        | é         |

The module automatically repairs many common encoding artifacts.

---

# Robust Encoding Support

Input files are automatically tested using multiple encodings:

```text
utf-8-sig
utf-8
latin1
cp1252
```

This improves compatibility with:

* Historical OCR exports
* Excel-generated CSV files
* Legacy datasets
* Mixed-source archives

Output files are written using:

```text
UTF-8 with BOM
```

to maximize interoperability with spreadsheet software.

---

# Neighborhood Pre-Cleaning

The module applies a series of transformations before standardization.

---

## Uppercase Standardization

Example:

```text
El Hatillo
```

becomes:

```text
EL HATILLO
```

---

## Description Removal

Many advertisements append descriptive text.

Example:

```text
EL HATILLO - CASA DE LUJO
```

becomes:

```text
EL HATILLO
```

---

## Colon Truncation

Example:

```text
EL HATILLO: CASA DE LUJO
```

becomes:

```text
EL HATILLO
```

---

## Parenthesis Removal

Example:

```text
EL HATILLO (ZONA SUR)
```

becomes:

```text
EL HATILLO
```

---

## Currency Truncation

Some agencies place prices immediately after neighborhood names.

Example:

```text
EL HATILLO $250,000
```

becomes:

```text
EL HATILLO
```

This reduces contamination from advertisement formatting.

---

# Boulevard Detection

The module contains specialized handling for boulevard references.

Examples:

```text
BLVD MORAZAN
```

```text
BLVD SUYAPA
```

These names are preserved rather than truncated.

This is important because boulevards often function as location identifiers within real-estate advertisements.

---

# Non-Location Term Removal

Certain terms are unlikely to represent neighborhood names.

Examples include:

```text
VENTA
ALQUILER
RENTA
SALE
PRICE
```

These tokens are removed during preprocessing.

---

# Accent Handling

Two separate representations are maintained.

---

## Human-Readable Version

Accents are preserved whenever possible.

Example:

```text
JOSÉ ÁNGEL
```

remains:

```text
JOSÉ ÁNGEL
```

---

## Matching Key

Accents are removed.

Example:

```text
JOSÉ ÁNGEL
```

becomes:

```text
JOSE ANGEL
```

This improves matching reliability.

---

# Normalization Key Generation

The optional normalization key:

```text
neighborhood_clean_norm
```

is intended for:

* Database joins
* Neighborhood catalogs
* GIS matching
* Longitudinal aggregation

The normalization process includes:

* Uppercasing
* Accent removal
* Punctuation removal
* Whitespace normalization

---

## Example

Original:

```text
Col. San José
```

Cleaned:

```text
COL. SAN JOSÉ
```

Normalized:

```text
COL SAN JOSE
```

---

# Configurable Word Removal

Additional non-neighborhood words can be removed through an external configuration file.

Example:

```text
config/remove_words.txt
```

Each line contains a word or phrase to remove.

This allows agency-specific cleanup without modifying source code.

---

# Example Workflow

Input:

```text
Col. El Hatillo: Casa de lujo $250,000
```

Output:

```text
neighborhood_clean:
EL HATILLO

neighborhood_clean_norm:
EL HATILLO
```

---

# Command-Line Usage

Example:

```bash
python clean_neighborhoods.py \
  --input_csv listings.csv \
  --input_col neighborhood \
  --out_csv listings_clean.csv \
  --add_norm
```

---

# Role Within the SDG-11 Framework

The Neighborhood Cleaning Module serves as the first stage of neighborhood standardization.

Its purpose is not to determine the correct neighborhood but to transform noisy extracted text into a cleaner and more consistent representation suitable for subsequent matching and aggregation.

This separation between cleaning and matching improves transparency, reproducibility, and auditability by preserving the original extracted values while generating standardized representations for analysis.

The module is a critical component of the SDG-11 workflow because neighborhood names form the primary geographic key used for:

* Neighborhood-level aggregation
* GIS integration
* Housing affordability indicators
* Longitudinal market analysis
* Urban sustainability metrics

```
```
