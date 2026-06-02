# SDG-11 Housing Data Reconstruction Framework

##Software
[![Software DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.18226605.svg)](https://doi.org/10.5281/zenodo.18226605)

## Data
[![Dataset DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.18226143.svg)](https://doi.org/10.5281/zenodo.18226)

A reproducible, configuration-driven framework for reconstructing historical and contemporary real-estate datasets from heterogeneous sources, including newspaper advertisements, OCR archives, web listings, and agency publications.

The framework was developed as part of the SDG-11 (Sustainable Cities and Communities) research program focused on housing affordability, urban development, neighborhood dynamics, and long-term housing-market monitoring in data-scarce environments.

---

## Framework Overview

![SDG-11 Framework](docs/images/OrchestratorV3.png)

# Why This Project Exists

In many countries, historical housing-market data are fragmented, inaccessible, or entirely unavailable.

Researchers frequently encounter:

* Scanned newspaper advertisements
* OCR-derived text
* Archived websites
* Inconsistent agency formats
* Missing structured datasets

As a result, longitudinal housing-market analysis becomes difficult or impossible.

This framework addresses that challenge by providing a transparent and reproducible workflow for transforming unstructured real-estate advertisements into standardized analytical datasets.

---

# Key Features

## Historical Reconstruction

Supports extraction from:

* Newspaper advertisements
* OCR text archives
* Historical classified sections

## Modern Listing Processing

Supports:

* Web-derived listings
* Agency exports
* Structured CSV workflows

## Configuration-Driven Architecture

New agencies and formats can be incorporated through configuration files rather than source-code modifications.

Examples:

* Agency configurations
* Property vocabularies
* Price semantic rules
* Neighborhood normalization rules
* Transaction validation rules

## Human-in-the-Loop Quality Control

Includes:

* Automated QC reports
* Outlier review workflows
* Classification audits
* Rejection tracking

## Reproducibility

All major transformations preserve:

* Original values
* Derived values
* Processing metadata
* Validation decisions
* Provenance information

---

# Framework Architecture

```text
Raw Sources
─────────────────────────────────
Newspapers
OCR Text
Archived Websites
Modern Listings

                ↓

Preprocessing
─────────────────────────────────
ForceBullet
SplitByCue
Agency Preprocessors

                ↓

Parsing
─────────────────────────────────
Agency Parser
Record Parser
Price Extractor
Area Extractor
Property Extraction
Neighborhood Extraction

                ↓

Quality Control
─────────────────────────────────
QC Reports
Property Type Validation
Transaction Validation

                ↓

Consolidation
─────────────────────────────────
Merge Output CSVs
Deduplication
Dataset Scope Filtering

                ↓

Standardization
─────────────────────────────────
UID Assignment
Neighborhood Cleaning
Word Filtering
Catalog Matching
Area Standardization
Price Standardization

                ↓

Aggregation
─────────────────────────────────
Neighborhood Indicators
Monthly Summaries
Housing Metrics

                ↓

Research Outputs
─────────────────────────────────
Datasets
Maps
Indicators
Publications
```

---

# Main Components

## Parsing Layer

Transforms raw advertisements into structured records.

Modules include:

* AgencyCoreParser
* Record Parser
* Parser Utilities
* Price Extractor
* Area Extractor

---

## Quality-Control Layer

Validates extracted information and generates audit reports.

Modules include:

* QC Report Generator
* Property Type Validation
* Transaction Validation

---

## Consolidation Layer

Combines agency outputs into unified analytical datasets.

Modules include:

* Merge Output CSVs
* Deduplication
* Scope Filtering

---

## Standardization Layer

Creates comparable and analysis-ready variables.

Modules include:

* UID Generation
* Neighborhood Cleaning
* Catalog Matching
* Area Standardization
* Price Standardization

---

# Data Philosophy

The framework follows a simple principle:

> Preserve observed data. Create derived analytical variables separately.

Examples:

| Observed      | Derived           |
| ------------- | ----------------- |
| price         | price_usd         |
| AT            | area_m2_std       |
| neighborhood  | neighborhood_uid  |
| property_type | property_type_new |
| transaction   | transaction_final |

This approach maximizes transparency and reproducibility.

---

# Quality Assurance

The framework includes multiple validation stages:

## Parsing QC

* Missing-field detection
* Multi-offer detection

## Semantic QC

* Property-type validation
* Transaction validation

## Dataset QC

* Scope filtering
* Deduplication auditing
* Rejection tracking

## Manual Review

Flagged records are preserved for human inspection rather than automatically discarded.

---

# Project Structure

```text
config/
│
├── agencies/
├── price_semantic_config.json
├── property_semantic_config.json
├── typewords.yaml
├── agency_mnemonics.csv
├── outside_metro.txt
├── exclude_types.csv
└── remove_words.txt

scripts/
│
├── AgencyCoreParser_v1.py
├── SDG11_ORCHESTRATOR_V3.py
├── record_parser.py
├── parser_utils.py
└── ...

tools/
│
├── merge_output_csvs.py
├── MergeDeduplicate.py
├── AddUid.py
├── StdPrice.py
├── clean_neighborhoods.py
├── word_filter.py
├── terrain_area_to_at.py
├── match_cleaned_to_catalog.py
└── ...

notebooks/
│
└── QC_Boxplot_Review.ipynb

docs/
│
├── architecture.md
├── data_dictionary.md
├── configuration_guide.md
└── ...
```

---

# Research Applications

The framework supports studies related to:

* Housing affordability
* Real-estate market dynamics
* Urban growth
* Neighborhood change
* Housing accessibility
* Longitudinal housing reconstruction
* Sustainable Development Goal 11 (SDG-11)

---

# Design Principles

* Reproducible
* Configuration-driven
* Auditable
* Human-review friendly
* Transparent
* Extensible
* Open-science oriented

---

# Citation

If you use this framework in academic research, please cite the associated dataset, documentation, and publications when available.

---

# Acknowledgements

This framework was developed as part of an ongoing effort to reconstruct housing-market information in data-scarce environments and to support open, reproducible urban research aligned with Sustainable Development Goal 11 (Sustainable Cities and Communities).
