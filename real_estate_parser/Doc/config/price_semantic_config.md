# price_semantic_config.json

## Purpose

The `price_semantic_config.json` file defines the semantic rules used to identify, normalize, validate, and interpret price information extracted from real-estate advertisements.

The configuration supports:

* Currency normalization
* Price magnitude interpretation
* Numeric masking
* Transaction inference
* Price validation
* Sale/rent boundary detection

By externalizing these rules, the framework can adapt to different currencies, price conventions, and market conditions without modifying the source code.

---

## Used By

* Parser
* Price standardization (`StdPrice.py`)
* Transaction validation
* Quality-control procedures

---

## Structure Overview

```text
price_semantic_config.json
├── currency_aliases
├── price_magnitude_aliases
├── price_locale_rules
├── mask_vocabulary
└── transaction_rules
```

---

## currency_aliases

Maps multiple textual currency representations into a standardized currency code.

### Example

| Alias | Standard Currency |
| ----- | ----------------- |
| $     | USD               |
| US$   | USD               |
| USD$  | USD               |
| U$    | USD               |
| L     | HNL               |
| L.    | HNL               |
| LPS   | HNL               |
| HNL   | HNL               |

### Purpose

Real-estate advertisements frequently use inconsistent currency notation. This section ensures all detected currencies are normalized to a common representation.

---

## price_magnitude_aliases

Defines abbreviations used to express large values.

### Example

| Token    | Multiplier |
| -------- | ---------- |
| k        | 1,000      |
| mil      | 1,000      |
| m        | 1,000,000  |
| mm       | 1,000,000  |
| millón   | 1,000,000  |
| millones | 1,000,000  |

### Examples

```text
250k  → 250,000
1.5m  → 1,500,000
2 millones → 2,000,000
```

### Purpose

Allows the parser to interpret abbreviated price expressions commonly used in advertisements.

---

## price_locale_rules

Controls how numeric values are interpreted.

### Parameters

| Parameter              | Description                        |
| ---------------------- | ---------------------------------- |
| decimal_max_digits     | Maximum decimal precision          |
| allow_mixed_separators | Allows mixed comma/period notation |
| allow_suffix_currency  | Currency after numeric value       |
| allow_prefix_currency  | Currency before numeric value      |

### Purpose

Supports advertisements originating from different formatting conventions and publication styles.

---

## mask_vocabulary

Defines numeric contexts that should not be interpreted as prices.

### Categories

#### Area Units

Examples:

* m2
* m²
* mts2
* v2
* vrs²
* varas cuadradas

#### Levels

Examples:

* nivel
* niveles
* niv.
* niv

#### Parking

Examples:

* garage
* garaje
* cochera
* parqueo

#### Bedrooms

Examples:

* hab
* habitaciones

#### Bathrooms

Examples:

* baños
* baths
* bths

#### Labels

Examples:

* ID
* Ref
* Código
* Code
* Price

### Purpose

Prevents non-price numbers from being incorrectly classified as monetary values.

For example:

```text
3 habitaciones
2 baños
450 m²
```

These numbers should not be interpreted as property prices.

---

## transaction_rules

Defines the rules used to infer and validate transactions.

---

### valid_property_types

Property categories eligible for transaction validation.

Current values:

```text
HOUSE
APARTMENT
```

---

### minimum_price

Defines minimum plausible prices by property type.

| Property Type | Minimum Price |
| ------------- | ------------- |
| HOUSE         | 60            |
| APARTMENT     | 50            |

Values below these thresholds are considered likely extraction errors.

---

### transaction_boundaries

Defines heuristic boundaries used to distinguish rentals from sales.

#### Apartments

| Rule     | Value  |
| -------- | ------ |
| rent_max | 10,000 |
| sale_min | 15,000 |

#### Houses

| Rule     | Value  |
| -------- | ------ |
| rent_max | 20,000 |
| sale_min | 15,000 |

### Example

```text
Apartment price = 1,500
→ likely RENT

Apartment price = 250,000
→ likely SALE
```

---

### sale_tokens

Keywords associated with sale transactions.

Examples:

* venta
* en venta
* se vende
* sale
* for sale

---

### rent_tokens

Keywords associated with rental transactions.

Examples:

* alquiler
* renta
* se alquila
* rent
* for rent

---

### ambiguous_patterns

Patterns that indicate uncertainty.

Examples:

```text
venta o renta
renta o venta
alquiler o venta
```

These records may require additional validation or manual review.

---

## Design Philosophy

This configuration file captures market-specific semantic knowledge that would otherwise be embedded directly within the software. By externalizing currency aliases, magnitude rules, masking vocabularies, and transaction boundaries, the framework remains adaptable, transparent, and reproducible while supporting historical and contemporary housing-market datasets.
