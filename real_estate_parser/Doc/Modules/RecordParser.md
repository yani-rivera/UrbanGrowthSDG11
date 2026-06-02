# Record Parser Module (`record_parser.py`)

## Purpose

The Record Parser is the central integration component of the SDG-11 real-estate reconstruction framework.

Its role is to transform a raw advertisement into a standardized listing record by coordinating multiple extraction modules and assembling their outputs into a unified schema.

The parser serves as the bridge between:

* Raw OCR text
* Agency-specific formats
* Extraction modules
* Standardized tabular datasets

---

# Position Within the Pipeline

```text
Raw Advertisement
        ↓
OCR Normalization
        ↓
Record Parser
        ↓
├── Price Extraction
├── Area Extraction
├── Bedroom Extraction
├── Bathroom Extraction
├── Neighborhood Extraction
├── Property Type Classification
└── Header Context Detection
        ↓
Standardized Listing Record
        ↓
L1 Cleaning
        ↓
Aggregation
```

---

# Design Philosophy

The parser follows a modular architecture.

Rather than implementing all extraction logic internally, it delegates specialized tasks to dedicated extraction modules.

Advantages include:

* Easier maintenance
* Independent testing
* Improved reproducibility
* Configuration-driven adaptation
* Support for new agencies and formats

---

# Main Responsibilities

The module performs five major tasks:

## 1. Text Normalization

Raw advertisement text is first standardized through OCR cleanup routines.

Examples include:

* Removal of OCR artifacts
* Whitespace normalization
* Character correction
* Encoding cleanup

This stage improves downstream extraction accuracy.

---

## 2. Context Detection

The parser can identify section-level metadata from advertisement headers.

Examples:

```text
# VENTA DE CASAS
```

```text
# APARTAMENTOS EN ALQUILER
```

These headers provide default values that may be inherited by individual listings.

Detected attributes include:

| Attribute     | Example                |
| ------------- | ---------------------- |
| Transaction   | Sale / Rent            |
| Property Type | House / Apartment      |
| Category      | Agency-defined section |

---

## 3. Attribute Extraction

The parser invokes specialized extraction modules.

### Price

```python
amount, currency = extract_price(...)
```

Extracts:

* Price
* Currency

Example:

```json
{
  "price": 250000,
  "currency": "USD"
}
```

---

### Bedrooms

```python
extract_bedrooms(...)
```

Example:

```text
3 habitaciones
```

Result:

```json
{
  "bedrooms": 3
}
```

---

### Bathrooms

```python
extract_bathrooms(...)
```

Example:

```text
2.5 baños
```

Result:

```json
{
  "bathrooms": 2.5
}
```

---

### Area Measurements

```python
extract_area(...)
```

Supports:

* AT (land area)
* AC (construction area)
* MZ (manzana area)
* Generic area

Example:

```json
{
  "AT": "800",
  "AT_unit": "Vrs²",
  "AC": "350",
  "AC_unit": "m²"
}
```

---

### Neighborhood

```python
extract_neighborhood(...)
```

Neighborhood extraction is entirely configuration-driven.

Agency configurations specify extraction strategies such as:

```json
{
  "strategy": "before_colon"
}
```

or

```json
{
  "strategy": "uppercase"
}
```

allowing different publication styles to be handled without modifying source code.

---

### Property Type

```python
extract_property_type(...)
```

Classifies listings into categories such as:

* House
* Apartment
* Land
* Commercial
* Other

The extractor result takes precedence over inherited header defaults.

---

# Neighborhood Strategy Engine

Neighborhood extraction relies on the configurable strategy framework implemented in:

```text
neighborhood_utils.apply_strategy()
```

Supported strategies include:

* uppercase
* first_line
* before_colon
* before_currency
* before_comma
* before_semicolon
* before_brack

This design allows historical newspaper formats and modern web formats to coexist within the same framework.

---

# Header Inheritance

Many historical advertisements omit information because it is already implied by the section header.

Example:

```text
# APARTAMENTOS EN ALQUILER

PALMIRA 2 HABITACIONES
```

The individual listing may not explicitly state:

```json
{
  "transaction": "rent",
  "property_type": "apartment"
}
```

The parser therefore supports inheritance from previously detected section headers.

---

# Area Traceability Mode

The parser supports the traceability-oriented area extraction system.

Example:

```json
{
  "AT": {
    "value": "800",
    "unit": "Vrs²"
  }
}
```

The parser maps these outputs into standardized record fields while preserving the original measurements.

This approach avoids premature unit conversion and facilitates quality-control review.

---

# Standardized Output Record

A typical parsed listing may contain:

```json
{
  "agency": "Makos",
  "date": "2011-02-28",
  "price": 250000,
  "currency": "USD",
  "bedrooms": 3,
  "bathrooms": 2.5,
  "AT": "800",
  "AT_unit": "Vrs²",
  "neighborhood": "EL HATILLO",
  "property_type": "HOUSE",
  "transaction": "SALE"
}
```

---

# Error Tolerance

The parser is intentionally fault-tolerant.

If an extractor fails:

```python
try:
    ...
except:
    ...
```

the remaining attributes can still be processed.

This behavior is important when working with:

* OCR-derived text
* historical newspapers
* incomplete advertisements
* corrupted records

The objective is to maximize record recovery while preserving transparency regarding missing values.

---

# Role Within the SDG-11 Framework

The Record Parser is the primary listing-construction engine of the SDG-11 real-estate reconstruction workflow.

It converts heterogeneous advertisement text into structured records that can subsequently be:

* standardized
* validated
* geocoded
* aggregated
* analyzed

for housing affordability studies, neighborhood indicators, urban growth analysis, and SDG-11 monitoring.

By separating extraction logic from record assembly, the framework remains modular, reproducible, and adaptable to new agencies, years, publication formats, and geographic contexts.
