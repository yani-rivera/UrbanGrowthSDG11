# Merge Output CSVs Module (`merge_output_csvs.py`)

## Purpose

The Merge Output CSVs module consolidates multiple agency-level datasets into a single standardized dataset for a specified temporal period.

The module operates after individual agencies have been parsed and validated, creating a unified dataset suitable for:

* Quality control
* Neighborhood standardization
* Currency standardization
* Aggregation
* Statistical analysis

Rather than combining raw text, the module merges already-structured records produced by the agency parsing workflow.

---

# Position Within the SDG-11 Pipeline

```text
Agency Text Files
        ↓
Agency Parser
        ↓
Agency CSV Files
        ↓
Merge Output CSVs
        ↓
Unified Dataset
        ↓
Neighborhood Cleaning
        ↓
Price Standardization
        ↓
Aggregation
```

---

# Problem Statement

Each agency is processed independently.

Example outputs:

```text
output/
├── Casabianca/
│   └── 2011/
│       └── Casabianca_20110128.csv
│
├── Makos/
│   └── 2011/
│       └── Makos_20110128.csv
│
└── Inverprop/
    └── 2011/
        └── Inverprop_20110128.csv
```

Analytical workflows require a consolidated dataset rather than separate agency files.

The merge module performs this integration step.

---

# Core Responsibilities

The module performs five primary functions:

1. File discovery
2. Schema harmonization
3. Provenance preservation
4. Optional deduplication
5. Consolidated dataset generation

---

# File Discovery

The module automatically locates CSV files matching user-specified filters.

Supported filters include:

| Filter | Example |
| ------ | ------- |
| Year   | 2011    |
| Month  | 03      |
| Day    | 28      |
| Agency | Makos   |

---

## Year-Level Merge

Example:

```bash
--year 2011
```

Produces:

```text
merged_2011.csv
```

containing all agency records for that year.

---

## Month-Level Merge

Example:

```bash
--year 2011 --month 03
```

Produces:

```text
merged_201103.csv
```

---

## Day-Level Merge

Example:

```bash
--year 2011 --month 03 --day 28
```

Produces:

```text
merged_20110328.csv
```

---

## Agency-Level Merge

Example:

```bash
--agency Casabianca
```

Produces:

```text
Casabianca_2011.csv
```

rather than a multi-agency dataset.

---

# Multi-Layout Support

The module supports both:

## Current Structure

```text
output/
└── Agency/
    └── Year/
        └── file.csv
```

and

## Legacy Structure

```text
output/
└── Agency/
    └── Agency_2011.csv
```

This improves compatibility across framework versions.

---

# Header Harmonization

Agency datasets may contain slightly different schemas.

The merge process automatically constructs a union of all detected columns.

Example:

Agency A:

```text
price
currency
bedrooms
```

Agency B:

```text
price
currency
bathrooms
```

Merged output:

```text
price
currency
bedrooms
bathrooms
```

Missing values are preserved as empty fields.

---

# Preferred Column Ordering

The module applies a standardized column order where possible.

Priority fields include:

```text
Listing ID
title
neighborhood
bedrooms
bathrooms
area
price
currency
transaction
property_type
agency
date
```

This improves consistency across datasets.

---

# Provenance Preservation

Two additional provenance fields are automatically added.

## Source File

```text
source_file
```

Example:

```text
Casabianca_20110128.csv
```

---

## Source Agency

```text
source_agency
```

Example:

```text
Casabianca
```

These fields preserve the origin of every record.

---

# Deduplication Framework

The module supports optional record deduplication.

Default deduplication key:

```text
agency
ingestion_id
Listing ID
```

Only records with identical key combinations are removed.

---

## Example

Record A:

```text
agency = Makos
ingestion_id = 20110128
Listing ID = 150
```

Record B:

```text
agency = Makos
ingestion_id = 20110128
Listing ID = 150
```

Result:

```text
1 record retained
```

---

# Custom Deduplication Keys

Researchers may define alternative keys.

Example:

```bash
--dedupe-key agency date ListingID
```

This flexibility supports different reconstruction strategies.

---

# Optional Deduplication Disable

Deduplication can be disabled entirely.

Example:

```bash
--no-dedupe
```

All records are retained.

This option is useful for auditing and debugging.

---

# Output Naming Convention

When no output file is specified, names are generated automatically.

Examples:

| Scope  | Output              |
| ------ | ------------------- |
| Year   | merged_2011.csv     |
| Month  | merged_201103.csv   |
| Day    | merged_20110328.csv |
| Agency | Casabianca_2011.csv |

This convention ensures predictable output locations.

---

# Safety Features

## Self-Ingestion Protection

The module prevents output directories from being placed inside the input directory tree.

This avoids recursive merging and duplicate ingestion.

---

## Encoding Robustness

Input CSVs are read using multiple fallback encodings:

```text
utf-8-sig
utf-8
latin-1
```

This improves compatibility with historical datasets and spreadsheet exports.

---

## Merge Validation

The module explicitly reports:

* Number of files merged
* Number of rows written
* Deduplication configuration

Example:

```text
Merged 25 files
Rows written: 4,200
```

This supports reproducibility and auditing.

---

# Example Workflow

Input:

```text
Makos_20110128.csv
Casabianca_20110128.csv
Inverprop_20110128.csv
```

Output:

```text
merged_20110128.csv
```

containing all agency listings in a single dataset.

---

# Command-Line Usage

## Merge Entire Year

```bash
python merge_output_csvs.py \
  --year 2011 \
  --input output \
  --output consolidated
```

---

## Merge Single Month

```bash
python merge_output_csvs.py \
  --year 2011 \
  --month 03 \
  --input output \
  --output consolidated
```

---

## Merge Single Agency

```bash
python merge_output_csvs.py \
  --year 2011 \
  --agency Casabianca \
  --input output \
  --output consolidated
```

---

# Role Within the SDG-11 Framework

The Merge Output CSVs module serves as the consolidation layer of the SDG-11 real-estate reconstruction framework.

Its purpose is to transform multiple agency-specific datasets into a unified analytical dataset while preserving provenance, maintaining schema consistency, and supporting reproducible deduplication.

The resulting consolidated datasets form the foundation for subsequent processing stages including:

* Neighborhood standardization
* Price standardization
* Transaction validation
* Aggregation
* Housing affordability analysis
* SDG-11 indicator generation

By preserving source metadata and implementing transparent merge rules, the module ensures that all consolidated datasets remain traceable, reproducible, and auditable.
