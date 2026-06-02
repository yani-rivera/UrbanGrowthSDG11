# nonprice_numeric_cues.json

## Purpose

The `nonprice_numeric_cues.json` file defines vocabulary associated with numeric values that should **not** be interpreted as property prices.

Real-estate advertisements contain many numbers that represent:

* Area measurements
* Bedroom counts
* Bathroom counts
* Parking spaces
* Building levels
* Reference identifiers

Without additional context, these values may be incorrectly extracted as prices.

This configuration provides a vocabulary-based masking mechanism that reduces false-positive price detections during parsing and standardization.

---

## Used By

* Price extraction
* Price validation
* Semantic parsing
* Quality-control procedures

---

## Structure Overview

```text
nonprice_numeric_cues.json
└── mask_vocabulary
    ├── area_units
    ├── levels
    ├── parking
    ├── beds
    ├── baths
    └── labels
```

---

## area_units

Defines measurement units commonly associated with property size.

### Examples

* m2
* m²
* mts2
* v2
* vrs²
* varas cuadradas

### Example

```text
450 m²
1200 varas cuadradas
```

These values should be interpreted as area measurements rather than prices.

---

## levels

Defines terms associated with floors or building levels.

### Examples

* niv
* niv.
* nivel
* niveles

### Example

```text
3 niveles
```

The number represents building levels, not a monetary value.

---

## parking

Defines vocabulary associated with parking capacity.

### Examples

* garage
* garaje
* cochera
* parqueo

### Example

```text
2 parqueos
```

The number represents parking spaces and should not be treated as a price.

---

## beds

Defines vocabulary associated with bedroom counts.

### Examples

* hab
* habitaciones

### Example

```text
4 habitaciones
```

The value represents bedrooms rather than monetary information.

---

## baths

Defines vocabulary associated with bathroom counts.

### Examples

* baños
* baths
* bths

### Example

```text
3 baños
```

The value represents bathrooms rather than price information.

---

## labels

Defines common reference fields that may contain numbers.

### Examples

* ID
* Ref
* Código
* Code
* Price

### Example

```text
Código 45781
Ref: 10234
```

These identifiers should not be interpreted as property prices.

---

## Example Workflow

Consider the following advertisement:

```text
Casa en Palmira
4 habitaciones
3 baños
2 parqueos
450 m²
Precio: US$ 275,000
```

Without masking rules, several numbers could be incorrectly identified as candidate prices:

```text
4
3
2
450
275000
```

After applying `nonprice_numeric_cues.json`, only:

```text
275000
```

remains as a valid price candidate.

---

## Design Philosophy

This configuration implements a defensive extraction strategy. Rather than focusing exclusively on identifying prices, the framework explicitly documents contexts in which numeric values should be ignored. This reduces false-positive detections, improves data quality, and increases the reliability of downstream price standardization and transaction-classification procedures.
