# Price Extraction Module (`price_extractor.py`)

## Purpose

The Price Extraction Module identifies, validates, and standardizes monetary values contained in real-estate advertisements.

The module was designed specifically for heterogeneous housing-market sources, including:

* Historical newspaper advertisements
* OCR-derived text
* Modern web listings
* Agency-specific formats
* Multilingual real-estate records

Unlike simple regular-expression approaches, the extractor incorporates currency normalization, numeric masking, contextual filtering, and range handling to improve robustness in noisy historical datasets.

---

# Design Objectives

The module was developed to address several common challenges:

| Challenge                             | Example                 |
| ------------------------------------- | ----------------------- |
| OCR formatting errors                 | `$ .550.000`            |
| Mixed separators                      | `1,200.000`             |
| Area values mistaken as prices        | `800 Vrs²`              |
| Bedroom counts mistaken as prices     | `3 habitaciones`        |
| Multiple currencies                   | `$150,000 / L3,800,000` |
| Price ranges                          | `$120,000-$140,000`     |
| Historical formatting inconsistencies | `US$. 250,000`          |

---

# Workflow Overview

```text
Raw Advertisement Text
          ↓
Text Normalization
          ↓
Currency Detection
          ↓
Non-Price Number Masking
          ↓
Price Candidate Extraction
          ↓
Range Interpretation
          ↓
Currency Assignment
          ↓
Final Price Selection
```

---

# Currency Detection

The extractor supports configurable currency aliases.

Example:

```json
{
  "currency_aliases": {
    "$": "USD",
    "US$": "USD",
    "USD": "USD",
    "L": "HNL",
    "L.": "HNL",
    "LPS": "HNL"
  }
}
```

All aliases map to standardized currency codes.

---

# Numeric Normalization

Historical advertisements frequently contain formatting inconsistencies.

Examples:

```text
$.550.000
L. .750,000
650 ,000
1, 200,000
```

The module automatically repairs these cases before extraction.

Examples:

| Original    | Normalized |
| ----------- | ---------- |
| $.550.000   | $550.000   |
| L. .750,000 | L.750,000  |
| 650 ,000    | 650,000    |
| 1, 200,000  | 1,200,000  |

---

# Locale-Aware Parsing

The extractor supports both English-style and Spanish-style number formats.

Examples:

| Format   | Value   |
| -------- | ------- |
| 1,200.50 | 1200.50 |
| 1.200,50 | 1200.50 |
| 500,000  | 500000  |
| 500.000  | 500000  |

This capability is essential when processing OCR archives and historical newspaper records.

---

# Non-Price Number Masking

One of the major causes of extraction errors in housing advertisements is the presence of non-price numeric information.

The module masks these values before searching for prices.

---

## Area Measurements

Examples:

```text
800 Vrs²
250 m²
5 Manzanas
```

are replaced internally by placeholders.

This prevents land-area values from being interpreted as prices.

---

## Bedrooms

Examples:

```text
3 habitaciones
4 hab
```

are masked.

---

## Bathrooms

Examples:

```text
2 baños
3 baños
```

are masked.

---

## Parking Spaces

Examples:

```text
2 estacionamientos
3 parqueos
```

are masked.

---

## Levels and Floors

Examples:

```text
2 niveles
3 pisos
```

are masked.

---

## Years

Examples:

```text
2010
2025
1998
```

are masked to avoid false-positive price detection.

---

# Price Candidate Extraction

After masking, the module searches for valid price candidates.

Two principal structures are supported.

---

## Prefix Currency

Currency before the number.

Example:

```text
$250,000
US$ 180,000
L. 3,500,000
```

---

## Suffix Currency

Currency after the number.

Example:

```text
250,000 USD
3,500,000 HNL
```

---

# Magnitude Support

The extractor recognizes abbreviated monetary magnitudes.

Examples:

| Input      | Interpreted As |
| ---------- | -------------- |
| 250k       | 250,000        |
| 1.5M       | 1,500,000      |
| 2 millones | 2,000,000      |
| 1 MM       | 1,000,000      |

---

# Price Range Handling

Advertisements frequently report ranges.

Example:

```text
$120,000 - $140,000
```

The extractor interprets both values.

Depending on configuration, the minimum value can be selected as the representative price.

---

## Currency Inheritance

Example:

```text
$120,000 - 140,000
```

The second value inherits the currency from the first value.

Result:

```text
USD
```

for both values.

---

## Dual-Currency Protection

Example:

```text
$150,000 / L3,800,000
```

This is treated as two different prices rather than a price range.

The separator `/` is therefore not automatically interpreted as a range when a second currency appears.

---

# Candidate Selection

Multiple price candidates may exist in the same advertisement.

Example:

```text
Antes $250,000
Ahora $220,000
```

The extractor evaluates all detected candidates and selects the most plausible value according to the configured policy.

Current default behavior:

```text
Largest monetary value
```

unless alternative policies are specified.

---

# Configuration Parameters

## Currency Controls

```json
{
  "price_require_currency": true
}
```

Only values accompanied by a recognized currency are accepted.

---

## Magnitude Controls

```json
{
  "price_accept_k": true,
  "price_accept_mil": true
}
```

Enables support for:

```text
250k
1.5M
2 millones
```

---

## Range Controls

```json
{
  "inherit_currency_in_ranges": true
}
```

Allows:

```text
$120,000 - 140,000
```

to inherit the USD currency.

---

## Multi-Price Policy

```json
{
  "multi_price_policy": "first_only"
}
```

Possible strategies include:

* first detected price
* minimum range value
* largest candidate
* custom selection logic

---

# Output

The module returns:

```python
(price_value, currency)
```

Example:

```python
(250000.0, "USD")
```

or

```python
(3500000.0, "HNL")
```

If no valid price is detected:

```python
(None, None)
```

is returned.

---

# Integration Within the SDG-11 Pipeline

The Price Extraction Module is one of the foundational components of the SDG-11 real-estate reconstruction framework.

Outputs generated by this module are subsequently used for:

* Currency standardization
* Historical exchange-rate conversion
* Price-per-area calculations
* Housing affordability indicators
* Neighborhood-level aggregation
* Temporal housing-market analysis
* SDG-11 monitoring and urban sustainability metrics

Because historical real-estate records often contain substantial formatting inconsistencies, the module emphasizes conservative extraction, contextual filtering, and traceable decision rules rather than aggressive price inference.
