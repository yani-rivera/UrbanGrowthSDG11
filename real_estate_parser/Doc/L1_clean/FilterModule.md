# Dataset Scope Filter Module (`FilterMergedFile.py`)

## Purpose

The Dataset Scope Filter Module performs rule-based exclusion of records after dataset consolidation and before analytical processing.

The module applies a series of configurable filters to remove records that are:

* Outside the geographic study area
* Outside the target property categories
* Missing valid prices
* Otherwise unsuitable for aggregation

Unlike traditional filtering workflows, all rejected records are preserved in a dedicated audit dataset together with the specific reason for exclusion.

---

# Position Within the SDG-11 Pipeline

```text
Agency Parsing
        ↓
Merge Output CSVs
        ↓
Deduplication
        ↓
Dataset Scope Filter
        ↓
├── Accepted Dataset
├── Rejected Dataset
└── Rejection Metadata
        ↓
UID Generation
        ↓
Neighborhood Processing
        ↓
Price Standardization
        ↓
Aggregation
```

---

# Problem Statement

Historical real-estate datasets frequently contain records that should not contribute to analytical indicators.

Examples include:

### Outside Metropolitan Area

```text
Valle de Ángeles
```

```text
Ojojona
```

```text
Comayagua
```

depending on study scope.

---

### Non-Target Property Types

```text
Farm
```

```text
Industrial Plant
```

```text
Hotel
```

when the study focuses on residential housing.

---

### Missing Prices

```text
Price upon request
```

```text
Call for information
```

```text
N/A
```

Without filtering, these records can distort analytical results.

---

# Design Philosophy

The module follows five principles.

## 1. Configuration-Driven Exclusions

Exclusions are managed through external files.

No exclusion logic is hard-coded.

---

## 2. Preserve Rejected Records

Records are never silently discarded.

All excluded observations are written to a rejection dataset.

---

## 3. Explain Every Exclusion

Each rejected record receives a rejection reason.

---

## 4. Deterministic Filtering

The same inputs always produce identical outputs.

---

## 5. Study-Specific Adaptability

Different projects may define different exclusion criteria without modifying source code.

---

# Processing Workflow

```text
Merged Dataset
        ↓
Price Validation
        ↓
Property-Type Filtering
        ↓
Neighborhood Filtering
        ↓
Accepted Dataset
        +
Rejected Dataset
```

---

# Input Components

The module requires:

| Component                    | Purpose                       |
| ---------------------------- | ----------------------------- |
| Input CSV                    | Dataset to filter             |
| Neighborhood Exclusion List  | Locations outside study scope |
| Property Type Exclusion List | Unwanted property categories  |
| Price Validation Rule        | Remove invalid prices         |

---

# Configuration Files

## Neighborhood Exclusions

Example:

```text
outside_metro.txt
```

Contents:

```text
VALLE DE ANGELES
OJOJONA
COMAYAGUA
```

Listings located in these areas are excluded.

---

## Property-Type Exclusions

Example:

```text
exclude_types.csv
```

Contents:

```csv
property_type
FARM
HOTEL
INDUSTRIAL
```

These categories are excluded.

---

# Flexible Exclusion Sources

The module supports:

### Text Files

```text
outside_metro.txt
```

---

### CSV Files

```text
exclude_types.csv
```

---

### CSV Column References

```text
exclude_types.csv:property_type
```

This flexibility simplifies configuration management.

---

# Text Normalization

Before comparisons:

* Lowercase conversion
* Whitespace normalization
* Null handling

Example:

```text
EL HATILLO
```

and

```text
 el   hatillo
```

become equivalent.

---

# Price Validation

The module can remove listings lacking valid prices.

Examples removed:

```text
N/A
```

```text
Call
```

```text
(blank)
```

---

## Accepted

```text
250000
```

```text
1500
```

---

## Rejected

```text
Not Available
```

```text
Contact Agent
```

---

# Property-Type Filtering

The module compares:

```text
property_type
```

against an exclusion list.

Example:

Input:

```text
HOTEL
```

Exclusion:

```text
HOTEL
```

Result:

```text
Excluded
```

---

# Neighborhood Filtering

The module evaluates:

```text
neighborhood
```

against a configurable exclusion list.

Example:

Input:

```text
VALLE DE ANGELES
```

Exclusion List:

```text
VALLE DE ANGELES
```

Result:

```text
Excluded
```

---

# Matching Modes

The module supports:

## Exact Match

```text
VALLE DE ANGELES
```

matches only:

```text
VALLE DE ANGELES
```

---

## Substring Match

```text
VALLE
```

may match:

```text
VALLE DE ANGELES
```

This mode supports broader filtering strategies.

---

# Accepted Dataset

Records surviving all filters are written to:

```text
output.csv
```

These records continue through the analytical pipeline.

---

# Rejected Dataset

Rejected records are written to:

```text
rejected.csv
```

This dataset forms an audit trail.

---

# Rejection Metadata

Each rejected record receives:

```text
rejection_cause
```

Possible values include:

```text
price_null_or_non_numeric
```

```text
excluded_property_type
```

```text
excluded_neighborhood
```

Multiple reasons can be recorded simultaneously.

---

# Example

Input:

| Listing                   | Reason                    |
| ------------------------- | ------------------------- |
| Hotel in Tegucigalpa      | excluded_property_type    |
| House in Valle de Ángeles | excluded_neighborhood     |
| Apartment with no price   | price_null_or_non_numeric |

All records remain available for review.

---

# Differential Dataset Logic

The module compares:

```text
Original Dataset
```

against:

```text
Filtered Dataset
```

using:

```text
Listing_uid
```

This ensures that every excluded observation can be traced back to its source record.

---

# Auditability Features

The module reports:

* Initial row count
* Price exclusions
* Property-type exclusions
* Neighborhood exclusions
* Final row count

Example:

```text
Initial rows: 5,200

Dropped due to invalid price: 32
Dropped due to type exclusions: 71
Dropped due to neighborhood exclusions: 104

Final rows: 4,993
```

This provides a reproducible exclusion summary.

---

# Example Workflow

Input:

```text
5,000 listings
```

↓

```text
32 invalid prices removed
```

↓

```text
71 excluded property types removed
```

↓

```text
104 excluded neighborhoods removed
```

↓

```text
4,793 accepted listings
```

and

```text
207 rejected listings
```

saved for auditing.

---

# Command-Line Usage

```bash
python FilterMergedFile.py \
    --input merged.csv \
    --output filtered.csv \
    --price-col price \
    --exclude-neighborhoods-files config/outside_metro.txt \
    --exclude-types-files config/exclude_types.csv \
    --rejected rejected.csv
```

---

# Relationship to Other Modules

### Merge Output CSVs

Creates:

```text
merged.csv
```

---

### FilterMergedFile

Creates:

```text
filtered.csv
```

and

```text
rejected.csv
```

---

### Later Processing

Only accepted records continue into:

* Neighborhood standardization
* Catalog matching
* Price standardization
* Aggregation

Rejected records remain available for auditing.

---

# Role Within the SDG-11 Framework

The Dataset Scope Filter Module provides the analytical-scope enforcement layer of the SDG-11 real-estate reconstruction framework.

Its purpose is to ensure that only records consistent with the project's geographic, thematic, and quality requirements enter the final analytical dataset.

The resulting outputs support:

* Transparent exclusion management
* Reproducible study boundaries
* Quality-control auditing
* Dataset traceability
* Housing affordability analysis
* Neighborhood-level aggregation
* SDG-11 indicator production

By preserving both accepted and rejected records together with explicit exclusion reasons, the framework maintains transparency, reproducibility, and methodological rigor throughout the data preparation process.
