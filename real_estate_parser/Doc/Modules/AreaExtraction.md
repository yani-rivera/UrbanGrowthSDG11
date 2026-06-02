# Area Extraction Module (`area_extractor.py`)

## Purpose

The Area Extraction Module is responsible for identifying and classifying property area measurements from real-estate advertisements.

Unlike simple pattern matching approaches, the module preserves the original reported values and units while applying contextual rules to distinguish between:

* Land Area (`AT`)
* Construction Area (`AC`)
* Manzana Area (`MZ`)
* Generic Area Measurements
* Uses area_units_hn_v1.yaml
  
This design supports traceability, reproducibility, and later quality-control review.

---

# Design Principles

The module follows four core principles:

## 1. Preserve Original Values

Extracted measurements are stored exactly as reported in the advertisement.

Example:

```text
800 Vrs²
```

is preserved as:

```json
{
  "AT": {
    "value": "800",
    "unit": "Vrs²"
  }
}
```

No automatic conversion to square meters is performed at this stage.

---

## 2. Unit-Aware Classification

The system classifies area measurements according to unit families rather than relying solely on surrounding text.

Examples:

| Unit             | Classification         |
| ---------------- | ---------------------- |
| Vrs²             | Land Area (AT)         |
| Varas Cuadradas  | Land Area (AT)         |
| Manzana          | MZ                     |
| Manzanas         | MZ                     |
| Mts²             | Construction Area (AC) |
| Metros Cuadrados | Construction Area (AC) |

---

## 3. Contextual Disambiguation

Some units are inherently ambiguous.

For example:

```text
250 m²
```

could represent either:

* land area
* construction area

The module therefore evaluates contextual clues before assigning a category.

---

## 4. Traceability First

The extraction process is designed to preserve the evidence used to identify areas.

This allows:

* manual review
* future auditing
* reproducibility
* correction of extraction rules

without losing the original advertisement information.

---

# Supported Area Categories

## AT — Land Area

Represents lot, parcel, or site area.

Typical units include:

```text
Vrs²
Vrs2
Varas Cuadradas
Vara2
```

Example:

```text
Terreno de 800 Vrs²
```

Output:

```json
{
  "AT": {
    "value": "800",
    "unit": "Vrs²"
  }
}
```

---

## AC — Construction Area

Represents built or constructed area.

Typical units include:

```text
Mts²
Mt2
Mtrs2
Metros Cuadrados
```

Example:

```text
Construcción 320 Mts²
```

Output:

```json
{
  "AC": {
    "value": "320",
    "unit": "Mts²"
  }
}
```

---

## MZ — Manzana Area

Used primarily for agricultural or large land parcels.

Typical units:

```text
Mz
Manzana
Manzanas
```

Example:

```text
5 Manzanas
```

Output:

```json
{
  "MZ": {
    "value": "5",
    "unit": "Manzanas"
  }
}
```

---

## Generic Area

Used when classification is uncertain.

Example:

```text
250 m²
```

Output:

```json
{
  "area": "250",
  "area_unit": "m²"
}
```

---

# Ambiguous Square-Meter Logic

The unit:

```text
m²
m2
```

is intentionally treated as ambiguous.

The module attempts to classify it using contextual evidence.

---

## Explicit Labels

Advertisements sometimes contain structured labels.

Example:

```text
AT: 500 m²
```

Output:

```json
{
  "AT": {
    "value": "500",
    "unit": "m²"
  }
}
```

Similarly:

```text
AC: 300 m²
```

becomes:

```json
{
  "AC": {
    "value": "300",
    "unit": "m²"
  }
}
```

---

## Land Context Detection

Keywords indicating land area include:

```text
terreno
parcela
solar
```

Example:

```text
Terreno de 400 m²
```

Result:

```json
{
  "AT": {
    "value": "400",
    "unit": "m²"
  }
}
```

---

## Construction Context Detection

Keywords indicating built area include:

```text
construcción
construida
construction
built
casa
```

Example:

```text
Casa de 250 m²
```

When sufficient supporting evidence exists, the value is classified as:

```json
{
  "AC": {
    "value": "250",
    "unit": "m²"
  }
}
```

---

# Multiple Area Detection

Advertisements frequently contain both lot and construction measurements.

Example:

```text
800 Vrs² de terreno
350 m² de construcción
```

Output:

```json
{
  "AT": {
    "value": "800",
    "unit": "Vrs²"
  },
  "AC": {
    "value": "350",
    "unit": "m²"
  }
}
```

The module supports simultaneous extraction of multiple area types from a single advertisement.

---

# Unit Normalization

For classification purposes only, unit tokens are internally normalized.

Examples:

| Original         | Normalized      |
| ---------------- | --------------- |
| Vrs²             | vrs2            |
| VRS ²            | vrs2            |
| m²               | m2              |
| Metros Cuadrados | metroscuadrados |

The original unit string remains unchanged in the output.

---

# Configuration Support

Additional units and aliases can be supplied through configuration files.

Example:

```json
{
  "area_aliases": {
    "at": [
      "vrs²",
      "varas cuadradas"
    ],
    "ac": [
      "mts2",
      "metros cuadrados"
    ],
    "mz": [
      "manzana",
      "manzanas"
    ]
  }
}
```

This allows adaptation to:

* new agencies
* historical sources
* OCR variants
* alternative languages

without modifying source code.

---

# Output Structure

Typical output:

```json
{
  "AT": {
    "value": "800",
    "unit": "Vrs²"
  },
  "AC": {
    "value": "350",
    "unit": "m²"
  }
}
```

or

```json
{
  "area": "250",
  "area_unit": "m²"
}
```

when classification is uncertain.

---

# Role Within the SDG-11 Pipeline

The Area Extraction Module is executed during the parsing stage and provides standardized area measurements for subsequent processing steps, including:

* property-type validation
* price-per-area calculations
* housing-market indicators
* neighborhood aggregation
* affordability analysis
* SDG-11 urban sustainability metrics

By separating extraction, classification, and later conversion stages, the module preserves transparency while supporting reproducible housing-market reconstruction from heterogeneous historical sources.
