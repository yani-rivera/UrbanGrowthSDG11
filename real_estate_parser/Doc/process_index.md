# Process Index — SDG-11 Real‑Estate Data Pipeline

This document is the **master index** for the entire SDG‑11 real‑estate data pipeline.
It provides a single entry point to understand **what exists, in what order,
and where to find the documentation** for each stage.

Use this file if you want to:
- understand the full workflow at a glance,
- navigate the documentation efficiently,
- reproduce the pipeline step by step.

---

## Pipeline Overview (Bird’s‑Eye View)

```
Raw Text (Synthetic or Real)
        ↓
Parsing (TXT → CSV)
        ↓
L1clean (Merge, Validate, Standardize)
        ↓
GIS Enrichment
        ↓
Unified Year / Month Dataset
        ↓
Aggregation
        ↓
Published Data Products
```

Each block below links to the **authoritative documentation** for that stage.

---

## 1. Input Data & Conventions

**What this stage does**
- Defines how raw TXT listings must look
- Establishes directory and naming conventions
- Provides synthetic data for reproducibility

**Documentation**
- `docs/data_index.md`
- `docs/txt_content_conventions.md`
- `docs/raw_data_conventions.md`
- `docs/directory_structure.md`

---

## 2. Parsing (TXT → Structured CSV)

**What this stage does**
- Converts newspaper‑style text into structured rows
- Uses agency‑specific configuration files
- Preserves original text for traceability

**Documentation**
- `docs/script_execution.md`
- `docs/config_reference.md`
- `docs/clone_parser.md`
- `docs/output_schema.md`

**Key scripts**
- `scripts/parse_<agency>_listings_v2.py`

---

## 3. L1clean — Structural Consolidation

### 3.1 Merge

**Purpose**
- Combine parsed CSVs by year or year‑month

**Documentation**
- `docs/merge_execution.md`

**Script**
- `tools/merge_output_csvs.py`

---

### 3.2 Deduplication

**Purpose**
- Separate canonical listings from duplicates
- Preserve auditability

**Documentation**
- `docs/deduplication_execution.md`

**Script**
- `tools/MergeDeduplicate.py`

---

### 3.3 Text & Identifier Normalization

Includes:
- word filtering
- UID assignment
- neighborhood normalization

**Documentation**
- `docs/word_filter_execution.md`
- `docs/add_uid_execution.md`
- `docs/clean_neighborhoods_execution.md`

---

### 3.4 Property & Transaction Validation

Includes:
- property type scoring
- transaction (rent/sale) validation

**Documentation**
- `docs/ptype_validation_execution.md`
- `docs/validate_transaction_execution.md`

---

### 3.5 Scope Filtering

**Purpose**
- Enforce research boundaries
- Explicitly separate accepted vs rejected listings

**Documentation**
- `docs/filter_merged_execution.md`

---

## 4. GIS Enrichment

**What this stage does**
- Matches neighborhoods to a standard catalog
- Assigns GIS identifiers
- Handles alias cases explicitly

**Documentation**
- `docs/catalog_matching_execution.md`
- Neighborhood catalog docs

**Script**
- `tools/match_cleaned_to_catalog.py`

---

## 5. Economic & Area Standardization

**Includes**
- currency standardization
- terrain / lot area conversion

**Documentation**
- `docs/stdprice_execution.md`
- `docs/terrain_area_execution.md`

---

## 6. Unified L1clean Output

**What this represents**
- One fully standardized dataset per year or year‑month
- Canonical analytical input

**Documentation**
- `docs/L1clean_process_summary.md`

**Typical output**
```
consolidated/<year>/merged_<year>_STDPrice_AreaM2.csv
```

---

## 7. Aggregation & Publication Outputs

**What this stage does**
- Aggregates listings to neighborhood level
- Applies minimum‑sample thresholds
- Produces publishable datasets

**Documentation**
- `docs/aggregation_execution_summary.md`
- `docs/published_data_summary.md`

**Scripts**
- `tools/Aggregate_*.py`

---

## How to Use This Index

- **New users**: start at Section 1, then follow sequentially
- **Reproduction**: follow Sections 2 → 6
- **Publication**: focus on Sections 6 → 7
- **Reviewers**: Sections 6 and 7 summarize analytical validity

---

## Methodological Statement

> This process index documents a deterministic, auditable pipeline for
> reconstructing historical housing market data from heterogeneous
> newspaper sources, suitable for SDG‑11 analysis in data‑scarce contexts.

---

This file is the **navigation spine** of the repository.
