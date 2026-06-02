# SDG11_ORCHESTRATOR_V3

## Overview

`SDG11_ORCHESTRATOR_V3.py` is the central workflow controller of the SDG-11 Real Estate Framework.

The orchestrator coordinates execution of all processing stages required to transform heterogeneous real-estate advertisements into standardized analytical datasets. It manages workflow execution, configuration loading, agency discovery, quality-control checkpoints, logging, aggregation, and reproducibility reporting.

The orchestrator was designed following a configuration-driven philosophy in which processing rules, paths, catalogs, and auxiliary resources are maintained outside the source code whenever possible. This approach improves maintainability, transparency, reproducibility, and adaptability across different agencies, years, and geographic contexts.

---

# Design Principles

The orchestrator was developed around the following principles:

* Configuration over hard-coding
* Reproducible processing
* Deterministic outputs
* Modular workflow stages
* Human-in-the-loop quality control
* Incremental execution
* Complete auditability
* Separation of processing logic and domain knowledge

The orchestrator itself does not perform parsing or standardization. Instead, it coordinates specialized scripts responsible for each stage of the workflow.

---

# Repository Architecture

The framework follows the directory structure below:

```text
config/
│
├── agencies/
├── orchestrator_config.json
├── price_semantic_config.json
├── property_semantic_config.json
├── transaction_rules.json
├── agency_mnemonics.csv
├── remove_words.txt
├── exclude_types.csv
└── outside_metro.txt

data/
└── raw/

output/

consolidated/

logs/

reports/

scripts/

tools/

L1clean/
```

## Directory Responsibilities

### config/

Contains all configuration resources, vocabularies, catalogs, semantic dictionaries, and validation rules.

### data/raw/

Stores canonical source files used as workflow inputs.

### output/

Stores agency-level parser outputs.

### consolidated/

Stores merged and progressively standardized datasets.

### logs/

Stores workflow logs and execution summaries.

### reports/

Stores generated reports and metrics.

### scripts/

Contains parsing modules and orchestration logic.

### tools/

Contains utility scripts, standardization modules, GIS utilities, and aggregation procedures.

### L1clean/

Contains validation, filtering, classification, and quality-control modules.

---

# Workflow Architecture

The orchestrator executes the following workflow:

```text
RAW TEXT
    ↓
PARSE
    ↓
MERGE
    ↓
DEDUPLICATE
    ↓
WORD FILTER
    ↓
UID ASSIGNMENT
    ↓
NEIGHBORHOOD CLEANING
    ↓
PROPERTY TYPE CLASSIFICATION
    ↓
RECORD FILTERING
    ↓
GIS MATCHING
    ↓
UNMATCHED QA
    ↓
PRICE STANDARDIZATION
    ↓
TRANSACTION VALIDATION
    ↓
AREA STANDARDIZATION
    ↓
AGGREGATION
```

Each stage produces intermediate outputs that may be inspected independently.

---

# Step Registry

The orchestrator uses a registry-based architecture.

```python
STEP_REGISTRY = {
    "parse",
    "merge",
    "deduplicate",
    "word_filter",
    "uid",
    "clean_neighborhoods",
    "ptype_fix",
    "filter_records",
    "gis_match",
    "unmatched_check",
    "price_standardize",
    "transaction_validate",
    "area_standardize",
    "aggregate"
}
```

New processing stages can be incorporated by registering additional functions.

---

# Discovery Phase

Before parsing begins, the orchestrator performs an agency discovery process.

Discovery identifies:

* Agencies with available source files
* Available configuration files
* Missing configurations
* Processing coverage

The resulting summary provides a preflight validation report before execution begins.

Example output:

```text
DISCOVERY SUMMARY

Agencies discovered : 25
Configured          : 22
Missing config      : 3
```

---

# Configuration Management

The orchestrator loads its settings from:

```text
config/orchestrator_config.json
```

This configuration controls:

* Workflow paths
* Script locations
* Catalog locations
* Aggregation tasks
* Logging columns
* Reporting behavior

Most operational changes can be performed through configuration updates without modifying source code.

---

# Processing Stages

## 1. Parse

Script:

```text
AgencyCoreParser_v1.py
```

Purpose:

* Convert canonical TXT files into structured CSV records.
* Apply agency-specific parsing rules.
* Extract advertisements into the standard schema.

Output:

```text
output/<agency>/<year>/*.csv
```

---

## 2. Merge

Script:

```text
merge_output_csvs.py
```

Purpose:

* Consolidate agency outputs into a unified dataset.

Output:

```text
merged_YEAR.csv
```

---

## 3. Deduplicate

Script:

```text
MergeDeduplicate.py
```

Purpose:

* Remove duplicate records.
* Separate duplicates into an audit file.

Outputs:

```text
merged_YEAR_c.csv
merged_YEAR_duplicates.csv
```

---

## 4. Word Filter

Script:

```text
word_filter.py
```

Purpose:

* Remove non-geographic vocabulary from neighborhood strings.

Configuration:

```text
remove_words.txt
```

Output:

```text
merged_YEAR_flt.csv
```

---

## 5. UID Assignment

Script:

```text
AddUid.py
```

Purpose:

* Generate deterministic unique identifiers.

Configuration:

```text
agency_mnemonics.csv
```

Output:

```text
merged_YEAR_uid.csv
```

Example UID:

```text
ROCA-20110128-000123
```

---

## 6. Neighborhood Cleaning

Script:

```text
clean_neighborhoods.py
```

Purpose:

* Normalize neighborhood names.
* Generate matching-ready location strings.

Output:

```text
merged_YEAR_clean.csv
```

---

## 7. Property Type Classification

Script:

```text
ptype_l1_clean_v8.py
```

Purpose:

* Classify listings into:

  * HOUSE
  * APARTMENT
  * LAND
  * COMMERCIAL
  * WAREHOUSE

Produces classification scores and confidence metrics.

Outputs:

```text
merged_YEAR_clean_ptype_fixed.csv
merged_YEAR_clean_ptype_fixed_scores.csv
```

---

## 8. Record Filtering

Script:

```text
FilterMergedFile.py
```

Purpose:

* Remove excluded property types.
* Remove records outside study area.

Configuration:

```text
exclude_types.csv
outside_metro.txt
```

Outputs:

```text
merged_YEAR_filtered.csv
filtered_rejected.csv
```

---

## 9. GIS Matching

Script:

```text
match_cleaned_to_catalog.py
```

Purpose:

* Match normalized neighborhoods to GIS polygons.

Configuration:

```text
standard_neighborhood_catalog.csv
```

Outputs:

```text
merged_YEAR_with_gis.csv
matched.csv
unmatched.csv
```

---

## 10. Unmatched QA

Script:

```text
unmatched.py
```

Purpose:

* Review unmatched neighborhoods.
* Support catalog expansion.

This stage is a critical human-in-the-loop validation step.

---

## 11. Price Standardization

Script:

```text
StdPrice.py
```

Purpose:

* Normalize currencies.
* Apply exchange rates.
* Standardize historical prices.

Supported modes:

```text
daily
monthly_avg
```

Outputs:

```text
merged_YEAR_STDPrice.csv
```

---

## 12. Transaction Validation

Script:

```text
ValidateTransaction.py
```

Purpose:

* Validate RENT versus SALE classification.
* Correct likely transaction errors.
* Apply market-specific thresholds.

Output:

```text
merged_YEAR_STDPrice_t.csv
```

---

## 13. Area Standardization

Script:

```text
terrain_area_to_at.py
```

Purpose:

* Standardize area measurements.
* Convert heterogeneous units into common metrics.

Output:

```text
merged_YEAR_STDPrice_AreaM2.csv
```

---

## 14. Aggregation

Purpose:

Generate analytical products.

Examples:

* Neighborhood summaries
* Bedroom summaries
* Area summaries
* Combined area-bedroom summaries

Outputs are defined through:

```text
orchestrator_config.json
```

---

# Logging System

Every execution receives a unique Run ID.

Example:

```text
20260520_153344
```

Logs are stored in:

```text
logs/<run_id>/
```

Typical outputs include:

```text
log_ALL_2011_01.csv
summary.txt
missing_configs.csv
```

---

# Quality Control

Quality control occurs throughout the workflow.

Examples include:

## Discovery Validation

Detects:

* Missing configurations
* Missing source files

## UID Validation

Detects:

* Missing mnemonics
* UID conflicts

## GIS Validation

Produces:

```text
matched.csv
unmatched.csv
```

## Transaction Validation

Detects:

* Sale/rent inconsistencies
* Out-of-range values

## Aggregation Validation

Applies minimum observation thresholds before publication.

---

# Temporal Processing

The orchestrator supports multiple processing scales.

## Daily

```bash
python SDG11_ORCHESTRATOR_V3.py \
    --all-agencies \
    --year 2011 \
    --month 01
```

## Monthly

```bash
python SDG11_ORCHESTRATOR_V3.py \
    --all-agencies \
    --year 2011 \
    --month 05 \
    --steps parse merge
```

## Yearly

```bash
python SDG11_ORCHESTRATOR_V3.py \
    --all-agencies \
    --year 2011
```

---

# Reproducibility

The orchestrator is designed to produce deterministic results.

Given:

* identical source files,
* identical configurations,
* identical software versions,
* identical execution parameters,

the workflow will generate identical outputs.

Changes in outputs should therefore be attributable to:

* new source data,
* configuration updates,
* software revisions,
* methodological modifications.

---

# Execution and Command-Line Arguments

The orchestrator can execute the complete workflow or selected processing stages through command-line arguments.

## Basic Syntax

```bash
python SDG11_ORCHESTRATOR_V3.py [OPTIONS]
```

---

## Common Examples

### Dry Run

Validate configuration files and discover available agencies without executing processing steps.

```bash
python SDG11_ORCHESTRATOR_V3.py \
    --all-agencies \
    --year 2011 \
    --dry-run
```

---

### Parse Only

Execute only the parsing stage.

```bash
python SDG11_ORCHESTRATOR_V3.py \
    --all-agencies \
    --year 2011 \
    --month 01 \
    --steps parse
```

---

### Parse and Merge

```bash
python SDG11_ORCHESTRATOR_V3.py \
    --all-agencies \
    --year 2011 \
    --month 01 \
    --steps parse merge
```

---

### Full Workflow

Execute all default processing stages defined in `orchestrator_config.json`.

```bash
python SDG11_ORCHESTRATOR_V3.py \
    --all-agencies \
    --year 2011 \
    --month 01
```

---

### Single Agency

```bash
python SDG11_ORCHESTRATOR_V3.py \
    --agency roca \
    --year 2011 \
    --month 01 \
    --steps parse
```

---

## Core Arguments

| Argument         | Description                               |
| ---------------- | ----------------------------------------- |
| `--agency`       | Process a specific agency                 |
| `--all-agencies` | Process all discovered agencies           |
| `--year`         | Processing year                           |
| `--month`        | Processing month                          |
| `--steps`        | List of workflow stages to execute        |
| `--dry-run`      | Validate configuration without executing  |
| `--config`       | Alternate orchestrator configuration file |
| `--report`       | Generate execution report                 |
| `--verbose`      | Enable detailed console output            |

---

## Available Workflow Steps

The following steps may be executed individually or combined:

| Step                   | Description                          |
| ---------------------- | ------------------------------------ |
| `parse`                | Parse canonical TXT files into CSV   |
| `merge`                | Merge agency outputs                 |
| `deduplicate`          | Remove duplicate records             |
| `filter`               | Apply text and record filtering      |
| `uid`                  | Generate unique identifiers          |
| `clean`                | Normalize neighborhood names         |
| `ptype_fix`            | Property-type classification         |
| `gis_match`            | GIS matching and SDG11UID assignment |
| `unmatched_check`      | Review unmatched neighborhoods       |
| `stdprice`             | Price and currency standardization   |
| `transaction_validate` | Validate sale/rent classifications   |
| `area_standardize`     | Standardize area units               |
| `aggregate`            | Generate analytical products         |

---

## Resuming Processing

Because the workflow is modular, processing can resume from any stage.

Example:

```bash
python SDG11_ORCHESTRATOR_V3.py \
    --year 2011 \
    --month 01 \
    --steps stdprice transaction_validate aggregate
```

This allows users to correct intermediate files and rerun only the required stages.

---

## Configuration File Override

To execute using an alternate configuration:

```bash
python SDG11_ORCHESTRATOR_V3.py \
    --config config/custom_orchestrator.json \
    --all-agencies \
    --year 2011
```

This is useful when testing alternative workflows or adapting the framework to another study area.

---

## Reproducible Execution

For reproducibility purposes, every execution records:

* Run ID
* Execution date
* Parameters used
* Processing steps executed
* Configuration files loaded
* Success and error metrics

These records are written to the logging directory and can be used to regenerate the workflow under identical conditions.


# Future Extensions

The orchestrator architecture was designed to support future modules, including:

* OCR ingestion workflows
* Historical newspaper reconstruction
* Web archive processing
* Multi-language parsing
* Additional GIS enrichment layers
* Automated anomaly detection
* Additional aggregation products
* Longitudinal monitoring pipelines

without requiring major changes to the core workflow controller.
