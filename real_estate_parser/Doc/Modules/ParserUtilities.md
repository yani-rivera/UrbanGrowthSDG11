# Parser Utilities Module (`parser_utils.py`)

## Purpose

The Parser Utilities Module provides a collection of reusable extraction, normalization, and classification functions used throughout the SDG-11 real-estate reconstruction framework.

The module acts as a shared service layer between:

* OCR processing
* Listing parsing
* Price extraction
* Area extraction
* Property classification
* Bedroom and bathroom detection

By centralizing common parsing functions, the framework avoids duplication and ensures consistent behavior across agencies and years.

---

# Architectural Role

```text
Raw Advertisement
        ↓
normalize_ocr_text()
        ↓
parser_utils.py
        ↓
├── extract_bedrooms()
├── extract_bathrooms()
├── extract_property_type()
├── detect_transaction()
├── detect_section_context()
├── extract_area()
└── Price Utility Wrappers
        ↓
record_parser.py
        ↓
Standardized Record
```

---

# Core Design Principles

The module was designed around four principles:

## 1. OCR Tolerance

Historical newspaper advertisements frequently contain OCR artifacts.

Examples:

```text
bafios
banos
√±
√ë
```

The module automatically normalizes many common OCR errors.

---

## 2. Multilingual Support

The parser supports both:

* Spanish
* English

Examples:

```text
3 habitaciones
```

```text
3 bedrooms
```

```text
2 baños
```

```text
2 bathrooms
```

This flexibility supports both historical newspapers and modern web listings.

---

## 3. Configuration-Driven Behavior

Many extraction rules can be controlled through configuration files rather than source-code modifications.

Examples include:

* Transaction keywords
* Property type vocabularies
* Bathroom markers
* Section headers
* Bedroom/bathroom shorthand options

---

## 4. Conservative Extraction

The module prioritizes precision over aggressive inference.

When uncertainty exists, extraction routines prefer returning:

```python
None
```

rather than potentially incorrect values.

---

# OCR Normalization

## Function

```python
normalize_ocr_text()
```

## Purpose

Standardizes OCR-derived text before extraction.

---

### Unicode Normalization

Example:

```text
ＨＯＵＳＥ
```

becomes:

```text
HOUSE
```

---

### OCR Error Repair

Examples:

| Original | Corrected |
| -------- | --------- |
| banos    | baños     |
| bano     | baño      |
| bafios   | baños     |
| √±       | ñ         |
| √ë       | é         |

---

### Currency Cleanup

Examples:

| Original  | Normalized |
| --------- | ---------- |
| $.700     | $ 700      |
| US$250000 | US$ 250000 |
| L.350000  | L. 350000  |

---

### Area Unit Standardization

Examples:

| Original | Normalized |
| -------- | ---------- |
| mt2      | m²         |
| mts2     | m²         |
| vr2      | vrs²       |
| vrs2     | vrs²       |

---

# Property Type Detection

## Function

```python
extract_property_type()
```

## Purpose

Classifies advertisements according to semantic keyword dictionaries.

Example configuration:

```json
{
  "HOUSE": [
    "casa",
    "residencia"
  ],
  "APARTMENT": [
    "apartamento",
    "apart"
  ]
}
```

Example:

```text
Casa en venta en El Hatillo
```

Result:

```text
HOUSE
```

---

# Transaction Detection

## Function

```python
detect_transaction()
```

## Purpose

Determines whether a listing represents:

* Sale
* Rent
* Other transaction categories

using configuration-driven keyword mappings.

Example:

```json
{
  "alquiler": "RENT",
  "venta": "SALE"
}
```

---

# Bedroom Extraction

## Function

```python
extract_bedrooms()
```

## Supported Formats

### Standard Spanish

```text
3 habitaciones
```

```text
4 dormitorios
```

---

### English

```text
3 bedrooms
```

---

### Compact Forms

```text
3H
```

---

### Keyword-Value Format

```text
beds=4
```

```text
bedrooms: 3
```

---

### Number Words

The module converts small number words into digits.

Examples:

| Word   | Value |
| ------ | ----- |
| uno    | 1     |
| dos    | 2     |
| tres   | 3     |
| cuatro | 4     |
| cinco  | 5     |

Example:

```text
tres habitaciones
```

Result:

```text
3
```

---

### Slash Notation

When enabled:

```text
3/2
```

is interpreted as:

```text
3 bedrooms
2 bathrooms
```

---

# Bathroom Extraction

## Function

```python
extract_bathrooms()
```

## Supported Formats

### Numeric

```text
2 baños
```

```text
2 bathrooms
```

---

### Decimal Bathrooms

```text
2.5 baños
```

---

### Half Bathrooms

```text
2 y medio baños
```

Result:

```text
2.5
```

---

### Fractional Bathrooms

```text
½ baño
```

```text
1/2 baño
```

Result:

```text
0.5
```

---

### Compact Form

```text
2B
```

Result:

```text
2
```

---

### Word-First Format

```text
Baños: 3
```

Result:

```text
3
```

---

# Ensuite Inference

The parser can infer bathrooms from bedroom counts when advertisements describe:

```text
cada habitación con su baño
```

or similar configured markers.

Example:

```text
3 habitaciones, cada una con su baño
```

Result:

```text
3 baños
```

This feature is optional and configuration controlled.

---

# Section Header Detection

## Function

```python
detect_section_context()
```

## Purpose

Detects newspaper section headers and extracts inherited metadata.

Example:

```text
VENTA DE CASAS
```

returns:

```json
{
  "transaction": "SALE",
  "type": "HOUSE"
}
```

---

# Area Extraction Wrapper

## Function

```python
extract_area()
```

This function acts as a façade.

Rather than implementing area extraction directly, it delegates processing to:

```python
modules.area_extractor
```

This preserves backward compatibility while allowing the dedicated area extraction engine to evolve independently.

---

# Listing Cleanup

## Function

```python
clean_listing_line()
```

Removes redundant whitespace and standardizes formatting before parsing.

Example:

```text
CASA      EN      VENTA
```

becomes:

```text
CASA EN VENTA
```

---

# Supported Advertisement Patterns

Examples successfully handled by the module include:

```text
Casa en venta, 3 habitaciones, 2 baños, 800 Vrs²
```

```text
3H / 2B, El Hatillo
```

```text
Beds=4 Bathrooms=3.5
```

```text
Tres habitaciones y dos baños
```

```text
Apartamento de lujo, 4.5 bathrooms
```

---

# Role Within the SDG-11 Framework

The Parser Utilities Module provides the shared linguistic and semantic foundation used throughout the SDG-11 housing reconstruction workflow.

Its responsibilities include:

* OCR cleanup
* Semantic normalization
* Property classification
* Bedroom extraction
* Bathroom extraction
* Transaction detection
* Header interpretation

By consolidating these functions into a single reusable layer, the framework maintains consistency across agencies, publication formats, historical periods, and future data sources while minimizing duplicated parsing logic.
