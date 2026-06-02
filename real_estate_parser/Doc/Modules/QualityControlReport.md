# Quality Control Report Generator (`generate_qc_report.py`)

## Purpose

The Quality Control (QC) Report Generator provides automated auditing of parsed real-estate listings before they are incorporated into the final SDG-11 datasets.

The objective of this module is not to modify records, but to identify potential issues requiring review, including:

* Missing attributes
* Multi-offer advertisements
* Incomplete records
* Parsing anomalies

The resulting reports support human-in-the-loop validation and improve transparency throughout the data reconstruction process.

---

# Position Within the SDG-11 Pipeline

```text
Raw Listings
      ↓
Record Parser
      ↓
Structured Records
      ↓
QC Report Generator
      ↓
├── Missing Field Audit
├── Multi-Offer Detection
├── Flag Reports
└── Summary Statistics
      ↓
Human Review
      ↓
Validated Dataset
```

---

# Design Philosophy

The QC framework follows a fundamental principle:

> Flag suspicious records for review rather than automatically deleting or modifying them.

This preserves transparency and allows researchers to evaluate questionable records manually.

The QC process therefore acts as an advisory layer rather than a filtering mechanism.

---

# Objectives

The module provides three primary functions:

## 1. Completeness Assessment

Identify missing attributes.

## 2. Multi-Offer Detection

Identify advertisements that may contain multiple properties.

## 3. Audit Reporting

Generate review-ready reports for researchers.

---

# Inputs

The script requires:

| Parameter  | Description          |
| ---------- | -------------------- |
| `--file`   | Listing text file    |
| `--config` | Agency configuration |
| `--agency` | Agency identifier    |
| `--date`   | Advertisement date   |
| `--out`    | Output directory     |

Example:

```bash
python generate_qc_report.py \
  --file agency_20110128.txt \
  --config agency.json \
  --agency Makos \
  --date 2011-01-28
```

---

# Processing Workflow

```text
Input Listings
      ↓
Parse Record
      ↓
Standardized Row
      ↓
Field Completeness Check
      ↓
Multi-Offer Analysis
      ↓
Flag Generation
      ↓
QC Reports
```

---

# Record Parsing

Each advertisement is processed using the standard parsing framework.

```python
parse_record(...)
```

This ensures that QC evaluation is based on the same extraction logic used to construct the final dataset.

---

# Missing Field Analysis

The module evaluates the presence of critical variables.

Fields monitored include:

```text
Price
Currency
Bedrooms
Bathrooms
AT
Area
Transaction
Type
Neighborhood
```

---

## Example

Parsed record:

```json
{
  "price": 250000,
  "currency": "USD",
  "bedrooms": 3
}
```

Missing:

```text
Bathrooms
Neighborhood
Type
```

These fields are recorded as QC flags.

---

# Missing Field Statistics

The module aggregates missing values across the entire file.

Example output:

```text
Missing fields counts:

Price: 12
Currency: 4
Bedrooms: 18
Bathrooms: 23
Neighborhood: 9
```

These metrics provide a quick overview of extraction quality.

---

# Multi-Offer Detection

Historical advertisements occasionally contain multiple properties within a single listing.

Example:

```text
EL HATILLO 3 HAB $250,000
LOMAS DEL GUIJARRO 4 HAB $350,000
```

Such records can distort statistical analyses if treated as a single property.

The QC system therefore evaluates indicators such as:

* Multiple prices
* Multiple bedroom counts
* Repeated property patterns

---

## Example Flag

```text
Prices Found:
250000
350000

Bedrooms Found:
3
4
```

Result:

```text
Multi Offer = YES
```

---

# Flagged Records File

The script generates a detailed CSV file containing all review flags.

Fields include:

| Field          | Description                            |
| -------------- | -------------------------------------- |
| Listing ID     | Internal record identifier             |
| Title          | Listing title                          |
| Missing Fields | Missing attributes                     |
| Multi Offer    | Candidate multi-property advertisement |
| Prices Found   | Detected prices                        |
| Bedrooms Found | Detected bedroom counts                |
| Notes          | Truncated source text                  |

---

## Example

```csv
Listing ID,Multi Offer,Missing Fields
25,YES,Bathrooms;Neighborhood
```

This file serves as a review queue for manual validation.

---

# Summary Report

The module also produces a human-readable text report.

Example:

```text
QC SUMMARY

Total Listings: 250

Missing Fields:
Price: 5
Bathrooms: 17
Neighborhood: 8

Multi-Offer Candidates:
#12
#38
#101
```

This report provides a high-level overview of dataset quality.

---

# Human-in-the-Loop Validation

The QC framework is designed to support expert review.

Flagged records are not automatically removed.

Instead, researchers can:

* Inspect original advertisements
* Confirm parser output
* Correct extraction errors
* Identify agency-specific anomalies

This approach improves reproducibility and reduces the risk of unintended data loss.

---

# Output Files

The script produces two outputs:

## QC Summary Report

```text
agency_20110128_QC_report.txt
```

Contains:

* Total records
* Missing field statistics
* Multi-offer summary

---

## QC Flags Report

```text
agency_20110128_QC_flags.csv
```

Contains:

* Listing-level flags
* Missing-field details
* Multi-offer indicators

---

# Role Within the SDG-11 Framework

The QC Report Generator forms the quality-assurance layer of the SDG-11 real-estate reconstruction framework.

Its role is to systematically identify records requiring review while preserving all extracted data.

The module supports:

* Data completeness assessment
* Parser validation
* Multi-offer detection
* Human-in-the-loop quality control
* Transparent dataset construction

By generating reproducible audit reports rather than silently modifying records, the QC framework improves reliability and accountability throughout the historical housing-data reconstruction process.
