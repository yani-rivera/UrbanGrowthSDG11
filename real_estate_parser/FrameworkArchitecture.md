# Framework Architecture

This document describes the overall architecture of the SDG-11 Housing Data Reconstruction Framework and explains how raw housing advertisements are transformed into standardized analytical datasets.

---

# Overview

The framework was designed to reconstruct housing-market datasets from heterogeneous and often unstructured sources, including:

* Historical newspaper advertisements
* OCR-derived text
* Archived websites
* Modern web listings
* Agency-specific exports

The architecture follows a modular design where each processing stage has a clearly defined responsibility.

---

# High-Level Workflow

```text
Raw Sources
      ↓
Preprocessing
      ↓
Parsing
      ↓
Quality Control
      ↓
Consolidation
      ↓
Standardization
      ↓
Aggregation
      ↓
Research Products
```

---

# Layer 1: Raw Sources

The framework can ingest housing advertisements originating from multiple source types.

## Historical Sources

* Newspaper classified advertisements
* OCR text files
* Digitized archives

## Contemporary Sources

* Real-estate websites
* Agency exports
* Structured CSV files

### Examples

```text
La Tribuna Classifieds (2010)
OCR Archive (2015)
Web Listings (2025)
```

---

# Layer 2: Preprocessing

The objective of preprocessing is to reconstruct advertisement structure before parsing.

## ForceBullet

Repairs missing bullet separators and normalizes listing boundaries.

**Input**

```text
* CASA ... * APARTAMENTO ...
```

**Output**

```text
* CASA ...
* APARTAMENTO ...
```

---

## SplitByCue

Identifies advertisement boundaries using configurable markers such as:

```text
:
,
;
.
```

This module transforms page-level OCR text into candidate advertisement records.

---

## Agency-Specific Preprocessors

Some agencies require custom normalization before parsing.

Examples include:

* OCR cleanup
* Header removal
* Formatting repair

---

# Layer 3: Parsing

The parsing layer converts advertisement text into structured records.

## Agency Parser

The agency parser coordinates parsing according to agency-specific configuration files.

Examples:

```text
agency_makos.json
agency_casabianca.json
```

---

## Record Parser

Transforms a single advertisement into a structured record.

Example:

```text
EL HATILLO
3 HAB
$250,000
```

↓

```json
{
  "price": 250000,
  "bedrooms": 3,
  "neighborhood": "EL HATILLO"
}
```

---

## Specialized Extractors

The parser delegates extraction tasks to dedicated modules.

### Price Extractor

Extracts:

* Price
* Currency

### Area Extractor

Extracts:

* Terrain area
* Built area
* Units

### Neighborhood Extractor

Extracts candidate neighborhood names.

### Property-Type Extractor

Extracts:

* House
* Apartment
* Land
* Commercial

---

# Layer 4: Quality Control

The framework incorporates multiple quality-control stages.

---

## QC Report Generator

Evaluates:

* Missing fields
* Multi-offer advertisements
* Parsing anomalies

Produces review-ready audit reports.

---

## Property Type Validation

Re-evaluates property classifications using a transparent scoring framework.

Example:

```text
HOUSE
```

↓

```text
COMMERCIAL
```

if sufficient evidence exists.

---

## Transaction Validation

Evaluates consistency between:

* Property type
* Price
* Transaction

Example:

```text
SALE
```

↓

```text
RENT
```

when price boundaries strongly indicate a rental listing.

---

# Layer 5: Consolidation

After agency-level processing, datasets are merged.

---

## Merge Output CSVs

Combines agency outputs into a unified dataset.

```text
Makos
Casabianca
Inverprop
```

↓

```text
merged_201101.csv
```

---

## Deduplication

Identifies repeated advertisements.

Outputs:

```text
Canonical Dataset
Duplicate Dataset
```

Duplicates are preserved rather than deleted.

---

## Scope Filtering

Removes records outside study scope.

Examples:

* Invalid prices
* Excluded neighborhoods
* Excluded property types

Produces:

```text
Accepted Dataset
Rejected Dataset
```

with explicit rejection reasons.

---

# Layer 6: Standardization

The standardization layer creates analysis-ready variables.

---

## UID Assignment

Creates reproducible identifiers.

Example:

```text
mak-20110128-0001
```

---

## Neighborhood Cleaning

Repairs OCR artifacts and standardizes extracted neighborhood names.

---

## Word Filtering

Removes controlled vocabulary terms.

Example:

```text
COL.
RES.
URB.
```

---

## Catalog Matching

Links neighborhoods to official reference identifiers.

Outputs:

```text
Neighborhood UID
GISID
Canonical Name
```

---

## Area Standardization

Converts heterogeneous area measurements into square meters.

Examples:

```text
800 Vrs²
```

↓

```text
558.96 m²
```

---

## Price Standardization

Converts prices into a common analytical currency.

Examples:

```text
3,500,000 HNL
```

↓

```text
165,200 USD
```

while preserving:

```text
fx_rate_used
fx_method
```

---

# Layer 7: Aggregation

The aggregation layer transforms listing-level data into analytical indicators.

Examples include:

## Neighborhood Summaries

* Mean prices
* Median prices
* Listing counts

---

## Property-Type Summaries

* Houses
* Apartments
* Land
* Commercial

---

## Area-Based Indicators

* Price per square meter
* Area distributions

---

## Housing Market Indicators

* Rental markets
* Sales markets
* Affordability measures

---

# Layer 8: Research Outputs

The framework ultimately produces datasets suitable for:

## Scientific Publications

* Methods papers
* Data papers
* Urban studies

---

## GIS Analysis

* Neighborhood mapping
* Housing affordability maps
* Urban development analysis

---

## SDG Monitoring

Particularly:

```text
SDG 11
Sustainable Cities and Communities
```

---

# Configuration Architecture

A central design principle of the framework is the separation of configuration from processing logic.

```text
Code
     +
Configuration
```

rather than:

```text
Hard-Coded Rules
```

Examples include:

* Agency configurations
* Property vocabularies
* Transaction rules
* Neighborhood exclusions
* Mnemonic catalogs

This allows new agencies, years, languages, and geographic contexts to be incorporated without modifying the core software.

---

# Data Philosophy

The framework preserves both:

## Observed Variables

Examples:

```text
price
currency
AT
property_type
transaction
```

and

## Derived Variables

Examples:

```text
price_usd
area_m2_std
property_type_new
transaction_final
neighborhood_uid
```

This design maximizes transparency and reproducibility.

---

# Human-in-the-Loop Design

The framework intentionally incorporates human review.

Examples:

* QC reports
* Classification audits
* Outlier review notebooks
* Rejected-record datasets

Records are generally flagged rather than silently removed.

This philosophy prioritizes transparency over aggressive automation.

---

# Architectural Summary

```text
Raw Sources
      ↓
Preprocessing
      ↓
Parsing
      ↓
Quality Control
      ↓
Consolidation
      ↓
Standardization
      ↓
Aggregation
      ↓
Research Products
```

Each layer has a single responsibility, making the framework:

* Modular
* Reproducible
* Auditable
* Extensible
* Research-oriented

This architecture enables the reconstruction of housing-market datasets from fragmented and heterogeneous sources while maintaining methodological transparency throughout the entire workflow.
