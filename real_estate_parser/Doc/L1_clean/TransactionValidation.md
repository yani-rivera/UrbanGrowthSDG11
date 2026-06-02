# Transaction Validation Module (`ValidateTransaction.py`)

## Purpose

The Transaction Validation Module evaluates the plausibility of property transactions using a rule-based framework that combines:

* Property type
* Price
* Declared transaction
* Advertisement text

The objective is to determine whether a listing represents:

```text
SALE
```

or

```text
RENT
```

while identifying records that are inconsistent, ambiguous, or outside the expected analytical scope.

---

# Position Within the SDG-11 Pipeline

```text
Property Type Validation
        ↓
Price Standardization
        ↓
Transaction Validation
        ↓
Validated Transaction
        ↓
Aggregation
        ↓
Housing Indicators
```

---

# Problem Statement

Real-estate advertisements frequently contain transaction ambiguities.

Examples:

```text
Casa en venta
```

but:

```text
Price = $850
```

A sale at $850 is highly improbable.

Similarly:

```text
Apartamento en alquiler
```

with:

```text
Price = $350,000
```

is unlikely to be a rental listing.

The Transaction Validation Module evaluates these inconsistencies using explicit business rules.

---

# Design Philosophy

The module follows five principles.

## 1. Price × Property Type Consistency

Transaction decisions must be compatible with both:

* Property type
* Observed price

---

## 2. Explicit Rule-Based Logic

All decisions are deterministic and reproducible.

No machine learning is used.

---

## 3. Transparent Corrections

When a transaction is corrected, the reason is recorded.

Example:

```text
CORRECTED_PRICE_BOUNDARY
```

---

## 4. Scope Enforcement

Listings outside the project's target property categories are flagged.

---

## 5. Auditability

Every decision records:

* Source of evidence
* Confidence level
* Validation outcome

---

# Configuration-Driven Architecture

All transaction rules are externalized into:

```text
config/price_semantic_config.json
```

This allows:

* Country adaptation
* Currency adaptation
* Market-specific thresholds
* Historical calibration

without modifying source code.

---

# Transaction Rule Components

The configuration defines:

---

## Valid Property Types

Example:

```json
{
  "valid_property_types": [
    "HOUSE",
    "APARTMENT",
    "LAND",
    "COMMERCIAL"
  ]
}
```

Listings outside this scope are flagged.

---

## Minimum Prices

Example:

```json
{
  "minimum_price": {
    "HOUSE": 60,
    "APARTMENT": 50
  }
}
```

Prices below these values are considered invalid.

---

## Transaction Boundaries

Example:

```json
{
  "HOUSE": {
    "rent_max": 20000,
    "sale_min": 15000
  }
}
```

These thresholds define the feasible transaction space.

---

## Sale Indicators

Examples:

```text
venta
vendo
for sale
```

Used when scanning advertisement notes.

---

## Rental Indicators

Examples:

```text
alquiler
renta
for rent
```

Used when scanning advertisement notes.

---

## Ambiguous Patterns

Examples:

```text
venta o renta
sale or rent
```

These expressions trigger ambiguity flags.

---

# Processing Workflow

```text
Listing
      ↓
Property Type Validation
      ↓
Price Validation
      ↓
Transaction Detection
      ↓
Price Boundary Evaluation
      ↓
Final Transaction Decision
```

---

# Step 1: Scope Validation

The module verifies that the property type belongs to the allowed set.

Example:

```text
DORMS
```

Result:

```text
FLAG_OUT_OF_SCOPE
```

These records are excluded from transaction evaluation.

---

# Step 2: Minimum Price Validation

The module evaluates whether the price exceeds the minimum allowed value.

Example:

```text
House
Price = $25
```

Result:

```text
REMOVED_INVALID_PRICE
```

This protects against OCR errors and extraction failures.

---

# Step 3: Transaction Signal Detection

The module evaluates two independent information sources.

---

## Declared Transaction

Field:

```text
transaction
```

Examples:

```text
SALE
```

```text
RENT
```

These receive:

```text
HIGH
```

confidence.

---

## Notes-Based Detection

The advertisement text is scanned for:

* Sale indicators
* Rental indicators
* Ambiguous indicators

Example:

```text
Casa en alquiler
```

Result:

```text
RENT
```

with:

```text
MEDIUM
```

confidence.

---

# Step 4: Price × Type Feasibility Analysis

This is the authoritative decision stage.

The module evaluates:

```text
Property Type
        +
Price
        +
Transaction
```

simultaneously.

---

# Example: Valid Rental

Property:

```text
Apartment
```

Price:

```text
1200
```

Transaction:

```text
RENT
```

Result:

```text
OK_DECLARED
```

---

# Example: Valid Sale

Property:

```text
House
```

Price:

```text
250000
```

Transaction:

```text
SALE
```

Result:

```text
OK_DECLARED
```

---

# Automatic Transaction Correction

The module can automatically correct obvious transaction errors.

---

## Example

Declared:

```text
SALE
```

Price:

```text
800
```

Property:

```text
Apartment
```

Because the price falls within the rental range:

Result:

```text
RENT
```

Flag:

```text
CORRECTED_PRICE_BOUNDARY
```

Source:

```text
price+ptype
```

Confidence:

```text
HIGH
```

---

# Infeasible Listings

If neither transaction type is plausible:

Example:

```text
Price = 12000
```

when:

```text
rent_max = 10000
sale_min = 15000
```

Result:

```text
REMOVED_PRICE_OUT_OF_RANGE
```

These records are flagged for exclusion or review.

---

# Decision Sources

The module records where the final decision originated.

Possible values:

| Source      | Meaning                    |
| ----------- | -------------------------- |
| declared    | Original transaction field |
| notes       | Advertisement text         |
| price+ptype | Feasibility analysis       |
| scope       | Scope validation           |

---

# Confidence Levels

The module assigns confidence indicators.

| Confidence | Meaning                   |
| ---------- | ------------------------- |
| HIGH       | Strong evidence           |
| MEDIUM     | Text-derived evidence     |
| LOW        | Weak or inferred evidence |

---

# Generated Fields

The module creates:

| Field                       | Description                  |
| --------------------------- | ---------------------------- |
| transaction_final           | Final validated transaction  |
| transaction_flag            | Validation result            |
| flag_polarity               | Positive or negative outcome |
| transaction_decision_source | Evidence source              |
| transaction_confidence      | Confidence level             |

---

# Example Output

Input:

| property_type_new | transaction | price_usd |
| ----------------- | ----------- | --------- |
| House             | SALE        | 900       |

Output:

| transaction_final | transaction_flag         |
| ----------------- | ------------------------ |
| RENT              | CORRECTED_PRICE_BOUNDARY |

---

# Positive Outcomes

Examples:

```text
OK_DECLARED
```

```text
CORRECTED_PRICE_BOUNDARY
```

These indicate usable records.

---

# Negative Outcomes

Examples:

```text
FLAG_OUT_OF_SCOPE
```

```text
REMOVED_INVALID_PRICE
```

```text
REMOVED_PRICE_OUT_OF_RANGE
```

These indicate problematic records.

---

# Example Workflow

Input:

```text
Property Type: House
Declared Transaction: SALE
Price: 950
```

Evaluation:

```text
Sale feasible?  NO
Rent feasible?  YES
```

Result:

```text
Transaction Final = RENT
Flag = CORRECTED_PRICE_BOUNDARY
Confidence = HIGH
```

---

# Command-Line Usage

```bash
python ValidateTransaction.py \
    --input listings.csv \
    --output listings_validated.csv \
    --config config/price_semantic_config.json
```

---

# Relationship to Earlier Stages

### Property Type Validation

Determines:

```text
property_type_new
```

---

### Price Standardization

Provides:

```text
price_usd
```

---

### Transaction Validation

Combines both variables with textual evidence to determine:

```text
transaction_final
```

This creates a multi-variable consistency check rather than relying on a single source of information.

---

# Role Within the SDG-11 Framework

The Transaction Validation Module provides the transaction-consistency and semantic validation layer of the SDG-11 real-estate reconstruction framework.

Its purpose is to ensure that property transactions remain consistent with observed prices, validated property types, and advertisement content.

The resulting transaction assignments support:

* Housing market segmentation
* Rental market analysis
* Sales market analysis
* Affordability indicators
* Neighborhood aggregation
* Longitudinal market reconstruction
* SDG-11 housing metrics

By combining property type, price boundaries, and textual evidence in a transparent rule-based framework, the module improves classification reliability while preserving complete auditability and reproducibility.
