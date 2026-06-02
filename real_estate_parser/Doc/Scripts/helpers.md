# helpers.py

## Purpose

`helpers.py` contains shared utility functions, schema definitions, preprocessing helpers, identifier generation support, text normalization routines, and file-management functions used throughout the SDG-11 Real Estate Framework.

The module centralizes common functionality so that parsers, validation modules, and workflow components can share a consistent implementation.

Rather than duplicating logic across scripts, reusable operations are maintained in a single location.

---

# Role in the Framework

```text
Agency Parser
      │
      ├── infer_agency()
      ├── infer_date()
      ├── format_listing_row()
      ├── write_prefile()
      ├── split_raw_and_parse_line()
      │
      ▼

Standardized CSV Output
```

Many core workflow components depend on this module.

---

# Core Responsibilities

The module provides functionality for:

* Canonical schema definitions
* Agency inference
* Date inference
* Prefile generation
* Listing normalization
* Price cleanup
* Currency normalization
* Record formatting
* File writing
* Utility quality-control functions

---

# Canonical Schema

The module defines the standard output schema used by the framework.

```python
FIELDNAMES
```

The canonical schema includes:

| Field            | Description                        |
| ---------------- | ---------------------------------- |
| Listing ID       | Sequential listing identifier      |
| title            | Listing title                      |
| neighborhood     | Extracted neighborhood             |
| bedrooms         | Bedroom count                      |
| bathrooms        | Bathroom count                     |
| AT               | Terrain area                       |
| AT_unit          | Terrain area unit                  |
| area             | Built area                         |
| area_unit        | Area unit                          |
| area_m2          | Standardized area in square meters |
| price            | Extracted price                    |
| currency         | Currency code                      |
| transaction      | Rent or sale                       |
| property_type    | Property classification            |
| agency           | Source agency                      |
| date             | Advertisement date                 |
| notes            | Original advertisement text        |
| source_type      | Data source classification         |
| ingestion_id     | Input filename                     |
| pipeline_version | Framework version                  |

This schema is used throughout the workflow and ensures consistency across agencies and publication years.

---

# Pipeline Versioning

The module defines:

```python
DEFAULT_PIPELINE_VERSION
```

Purpose:

* Provenance tracking
* Dataset version identification
* Reproducibility support

Every generated record includes the pipeline version used during processing.

---

# Agency Inference

Function:

```python
infer_agency()
```

Purpose:

Automatically determine the originating agency from:

1. Configuration files
2. Filenames
3. Directory structure

Example:

```text
agency_roca.json
```

↓

```text
ROCA
```

This reduces manual metadata entry.

---

# Date Inference

Function:

```python
infer_date()
```

Purpose:

Extract advertisement dates from filenames.

Supported formats include:

```text
20110128
2011-01-28
2011_01_28
```

Output:

```text
2011-01-28
```

This provides consistent temporal metadata across datasets.

---

# Record Formatting

Function:

```python
format_listing_row()
```

Purpose:

Convert parser outputs into the canonical SDG-11 schema.

Responsibilities:

* Field alignment
* Provenance assignment
* Schema consistency
* Output standardization

This function ensures that all agencies produce identical output structures.

---

# Release Record Generation

Function:

```python
build_release_row()
```

Purpose:

Generate simplified release-ready records.

Typical use cases:

* Public datasets
* Aggregated outputs
* External dissemination

This separates internal processing records from publication products.

---

# Prefile Generation

Function:

```python
write_prefile()
```

Purpose:

Create intermediate text files used during preprocessing.

Directory structure:

```text
output/
└── Agency/
    └── pre/
        └── YYYY/
```

Example:

```text
output/Roca/pre/2011/pre_roca_20110128.txt
```

Benefits:

* Auditability
* Debugging
* Workflow transparency

---

# Numbered Listing Conversion

Function:

```python
make_prefile_numbered()
```

Purpose:

Convert numbered advertisements into the framework's canonical listing format.

Example:

Original:

```text
1. CASA EN PALMIRA
2. APARTAMENTO EN TEGUCIGALPA
```

Converted:

```text
* CASA EN PALMIRA
* APARTAMENTO EN TEGUCIGALPA
```

This standardization simplifies downstream parsing.

---

# Delimiter Normalization

Function:

```python
make_prefile_star()
```

Purpose:

Convert agency-specific delimiters into the canonical format.

Supported examples:

```text
-
#
*
•
```

↓

```text
*
```

This allows different agencies to share a common parser.

---

# Price Cleanup Utilities

## strip_per_unit_prices()

Purpose:

Remove price-per-area expressions.

Example:

```text
US$ 50 m²
US$ 10 vrs²
```

These expressions can interfere with total-price extraction.

---

## normalize_currency_spacing()

Purpose:

Normalize currency formatting.

Example:

```text
US$45000
```

↓

```text
US$ 45000
```

This improves price-detection reliability.

---

# Parsing Helpers

Function:

```python
split_raw_and_parse_line()
```

Purpose:

Maintain two versions of advertisement text:

### Raw Version

Preserved for provenance.

### Parsing Version

Normalized for extraction.

Example:

```text
* CASA EN PALMIRA
```

Raw:

```text
* CASA EN PALMIRA
```

Parse:

```text
CASA EN PALMIRA
```

This preserves original formatting while simplifying parsing.

---

# Quality-Control Functions

## count_numbered_bullets()

Counts numbered listings.

Example:

```text
1.
2.
3.
```

Useful for preprocessing validation.

---

## count_star_bullets()

Counts canonical listing markers.

Example:

```text
*
*
*
```

Useful for verifying delimiter conversion.

---

# Design Philosophy

The purpose of `helpers.py` is to centralize shared workflow functionality and enforce consistency across the framework. By maintaining schema definitions, preprocessing logic, metadata extraction, and utility functions in a common module, the framework reduces duplication, improves maintainability, and ensures that all agencies and datasets are processed using the same underlying conventions.

Although `helpers.py` does not directly perform parsing or analysis, it provides much of the infrastructure required to make the SDG-11 workflow reproducible, standardized, and scalable.
