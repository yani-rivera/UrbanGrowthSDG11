# property_semantic_config.json

## Purpose

The `property_semantic_config.json` file defines the semantic rules used to extract residential property attributes from advertisement text.

The configuration focuses on identifying:

* Bedrooms
* Bathrooms
* Half bathrooms
* Numeric word representations
* Bed/Bath shorthand expressions
* Attribute validation limits

By externalizing these rules, the framework can accommodate variations in terminology, abbreviations, and language conventions without requiring modifications to the extraction code.

---

## Used By

* Property attribute extraction
* Bedroom detection
* Bathroom detection
* Listing standardization
* Quality-control procedures

---

## Structure Overview

```text
property_semantic_config.json
├── bedroom_terms
├── bedroom_shorthand
├── bathroom_terms
├── bathroom_shorthand
├── half_bath_terms
├── number_words_0_5
└── property_attribute_rules
```

---

## bedroom_terms

Defines vocabulary associated with bedrooms.

### Examples

| Term         |
| ------------ |
| hab          |
| habitacion   |
| habitaciones |
| dormitorio   |
| dormitorios  |
| recamara     |
| recámaras    |
| alcoba       |
| bedroom      |
| bedrooms     |
| bed          |
| beds         |

### Purpose

Allows the parser to recognize bedroom references across different writing styles, abbreviations, and languages.

### Example

```text
3 habitaciones
4 dormitorios
2 bedrooms
```

All examples are interpreted as bedroom counts.

---

## bedroom_shorthand

Defines abbreviated forms used in classified advertisements.

### Examples

```text
3H
4 h
```

### Purpose

Supports extraction from compact newspaper-style listings where space is limited.

---

## bathroom_terms

Defines vocabulary associated with bathrooms.

### Examples

| Term      |
| --------- |
| baño      |
| baños     |
| bano      |
| banos     |
| bathroom  |
| bathrooms |
| bath      |
| baths     |

### Purpose

Supports multilingual bathroom extraction and normalization.

---

## bathroom_shorthand

Defines abbreviated bathroom notation.

### Examples

```text
2B
3 b
```

### Purpose

Allows recognition of compact advertisement formats.

---

## half_bath_terms

Defines expressions associated with half bathrooms.

### Examples

```text
1/2 baño
½ baño
medio baño
```

### Purpose

Supports more accurate representation of residential property layouts.

---

## number_words_0_5

Maps textual numbers to numeric values.

### Example

| Word   | Value |
| ------ | ----- |
| uno    | 1     |
| dos    | 2     |
| tres   | 3     |
| cuatro | 4     |
| cinco  | 5     |

### Example

```text
tres habitaciones
```

is interpreted as:

```text
3 habitaciones
```

### Purpose

Allows extraction from advertisements that use words rather than digits.

---

## property_attribute_rules

Controls attribute extraction behavior.

### Parameters

| Parameter                 | Description                     |
| ------------------------- | ------------------------------- |
| allow_slash_bed_bath      | Allows formats such as 3/2      |
| enable_word_first_bedbath | Supports word-based expressions |
| max_bedrooms              | Maximum allowed bedroom count   |
| max_bathrooms             | Maximum allowed bathroom count  |
| allow_half_bath           | Enables half-bath recognition   |

### Example

```text
3/2
```

interpreted as:

```text
3 bedrooms
2 bathrooms
```

### Validation

The maximum bedroom and bathroom limits provide a quality-control mechanism that helps identify likely extraction errors and malformed advertisements.

---

## Design Philosophy

Real-estate advertisements frequently describe property attributes using highly abbreviated, multilingual, and inconsistent formats. This configuration centralizes the semantic knowledge required to interpret those expressions while keeping extraction logic separate from vocabulary definitions. The result is a more transparent, maintainable, and adaptable attribute-extraction process.
