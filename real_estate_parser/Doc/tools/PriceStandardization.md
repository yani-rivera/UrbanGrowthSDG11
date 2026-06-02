# Price Standardization Module (`StdPrice.py`)

## Purpose

The Price Standardization Module converts extracted property prices into a common currency (USD) using a configurable foreign-exchange (FX) methodology.

Historical real-estate datasets often contain listings reported in multiple currencies. Direct comparison of prices across years is therefore impossible without a standardized monetary framework.

This module provides a reproducible and transparent mechanism for converting prices while preserving:

* Original currency
* Exchange rate used
* Conversion methodology
* Conversion date context

---

# Position Within the SDG-11 Pipeline

```text
Raw Listings
      ↓
Price Extraction
      ↓
Parsed Dataset
      ↓
Price Standardization
      ↓
USD-Standardized Dataset
      ↓
Aggregation
      ↓
Neighborhood Indicators
```

---

# Problem Statement

Real-estate advertisements may report prices using different currencies.

Examples:

```text
$250,000
```

```text
L. 3,500,000
```

```text
Lps. 2,800,000
```

Without currency standardization:

* Neighborhood averages become misleading
* Longitudinal comparisons become unreliable
* Housing affordability metrics become distorted

The Price Standardization Module addresses this issue.

---

# Design Principles

The module follows four principles:

## 1. Preserve Original Values

The original price remains unchanged.

Example:

```text
3500000 HNL
```

is preserved.

---

## 2. Create Standardized Values

A new standardized variable is created:

```text
price_usd
```

---

## 3. Preserve Methodological Traceability

Every conversion records:

```text
fx_rate_used
```

and

```text
fx_method
```

allowing complete reproducibility.

---

## 4. Fail Explicitly

Missing exchange rates generate warnings or errors rather than silently estimating values.

---

# Supported Currencies

Current implementation supports:

| Currency             | Code |
| -------------------- | ---- |
| United States Dollar | USD  |
| Honduran Lempira     | HNL  |

Example:

```text
USD
```

```text
HNL
```

Unsupported currencies trigger validation errors.

---

# Required Input Fields

The input dataset must contain:

| Field    | Description            |
| -------- | ---------------------- |
| price    | Original listing price |
| currency | Listing currency       |
| date     | Listing date           |

Example:

```csv
price,currency,date
250000,USD,2015-01-28
3500000,HNL,2015-01-28
```

---

# Exchange Rate Data

The module uses external exchange-rate tables.

This design separates:

* Real-estate data
* Financial reference data

and improves reproducibility.

---

# Supported FX Methodologies

## Daily Exchange Rates

Uses the exact listing date.

Example FX file:

```csv
date,base,quote,rate
2015-01-28,HNL,USD,0.0472
```

Conversion:

```text
Listing Date
      ↓
Matching Daily Rate
      ↓
USD Conversion
```

---

## Monthly Average Exchange Rates

Uses a monthly mean exchange rate.

Example:

```csv
year_month,base,quote,rate
2015-01,HNL,USD,0.0468
```

Conversion:

```text
Listing Date
      ↓
Extract Year-Month
      ↓
Monthly Average Rate
      ↓
USD Conversion
```

This methodology is particularly useful when:

* Daily rates are unavailable
* Historical reconstruction spans long periods
* Monthly aggregation is the primary analytical unit

---

# Date Validation

The module enforces strict ISO date formats.

Required format:

```text
YYYY-MM-DD
```

Example:

```text
2015-01-28
```

Invalid examples:

```text
28/01/2015
```

```text
2015/01/28
```

trigger validation errors.

---

# Exchange Rate Validation

For monthly averages:

Required format:

```text
YYYY-MM
```

Example:

```text
2015-01
```

Invalid formats generate explicit errors.

---

# Conversion Logic

## USD Listings

Listings already reported in USD require no conversion.

Example:

```text
250000 USD
```

Output:

```text
price_usd = 250000
fx_rate_used = 1
fx_method = identity
```

---

## HNL Listings

Listings reported in Honduran Lempiras are converted using the selected FX methodology.

Example:

```text
3,500,000 HNL
```

with:

```text
0.0472
```

produces:

```text
165,200 USD
```

---

# Missing Exchange Rates

The module supports two behaviors.

---

## Error Mode

```bash
--on-missing-rate error
```

Execution stops if no FX rate is available.

This mode maximizes reproducibility.

---

## Null Mode

```bash
--on-missing-rate null
```

Missing conversions are assigned null values.

This mode allows processing to continue while preserving transparency.

---

# Output Fields

The module adds:

| Field        | Description            |
| ------------ | ---------------------- |
| price_usd    | Standardized USD value |
| fx_rate_used | Exchange rate applied  |
| fx_method    | Conversion methodology |

Example:

```csv
price,currency,price_usd,fx_rate_used,fx_method
3500000,HNL,165200,0.0472,daily
```

---

# Example Workflow

Input:

```csv
price,currency,date
3500000,HNL,2015-01-28
250000,USD,2015-01-28
```

FX:

```csv
date,base,quote,rate
2015-01-28,HNL,USD,0.0472
```

Output:

```csv
price,currency,price_usd,fx_rate_used,fx_method
3500000,HNL,165200,0.0472,daily
250000,USD,250000,1,identity
```

---

# Command-Line Usage

## Monthly Average FX

```bash
python StdPrice.py \
  --input listings.csv \
  --fx fx_monthly.csv \
  --output listings_std.csv \
  --fx-mode monthly_avg
```

---

## Daily FX

```bash
python StdPrice.py \
  --input listings.csv \
  --fx fx_daily.csv \
  --output listings_std.csv \
  --fx-mode daily
```

---

# Quality Assurance Features

The module performs:

### Currency Validation

Ensures all currencies belong to the supported currency set.

### Date Validation

Verifies ISO-compliant dates.

### Exchange Rate Validation

Ensures required FX records exist.

### Relationship Validation

Uses merge validation rules to prevent duplicate FX mappings.

These safeguards reduce the risk of silent conversion errors.

---

# Role Within the SDG-11 Framework

The Price Standardization Module provides the monetary harmonization layer of the SDG-11 real-estate reconstruction framework.

Its purpose is to transform heterogeneous historical price data into a common analytical currency while preserving complete traceability of the conversion process.

The resulting standardized prices support:

* Neighborhood-level aggregation
* Housing affordability analysis
* Longitudinal price comparisons
* Inflation-adjusted studies
* SDG-11 housing indicators

By recording both the exchange rate and methodology used, the module ensures that all monetary transformations remain transparent, reproducible, and auditable.
