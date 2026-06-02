# AgencyCoreParser_v1.py

## Purpose

`AgencyCoreParser_v1.py` is the primary parsing engine of the SDG-11 Real Estate Framework.

Its purpose is to transform agency-specific canonical text files into standardized CSV records using agency configuration files and shared parsing modules.

The parser serves as the first structured extraction stage of the workflow and converts semi-structured real-estate advertisements into the canonical dataset schema used throughout the framework.

---

# Workflow Position

```text
Raw Advertisement Text
          ↓
Canonical TXT File
          ↓
AgencyCoreParser_v1.py
          ↓
Agency CSV Output
          ↓
Merge
          ↓
Standardization
          ↓
Aggregation
```

This parser represents the transition from unstructured text to structured data.

---

# Design Philosophy

The parser was designed around three principles:

1. Configuration-driven extraction
2. Agency-independent processing
3. Reproducible outputs

Rather than creating a separate parser for each agency, the same parsing engine is reused across all agencies by loading agency-specific configuration files.

---

# Inputs

## Required Inputs

### Source File

Canonical UTF-8 text file.

Example:

```text
data/raw/roca/2011/roca_20110128.txt
```

### Agency Configuration

Defines how advertisements should be interpreted.

Example:

```text
config/agencies/agency_roca.json
```

### Output Directory

Location where parsed CSV files will be written.

Example:

```text
output/
```

---

# Command Line Usage

## Basic Execution

```bash
python AgencyCoreParser_v1.py \
    --file data/raw/roca/2011/roca_20110128.txt \
    --config config/agencies/agency_roca.json \
    --output-dir output
```

---

# Arguments

| Argument       | Required | Description               |
| -------------- | -------- | ------------------------- |
| `--file`       | Yes      | Canonical TXT input file  |
| `--config`     | Yes      | Agency configuration file |
| `--output-dir` | Yes      | Root output directory     |
| `--debug`      | No       | Enable debugging output   |

---

# Processing Stages

## 1. Configuration Loading

The parser loads the agency configuration file.

Example:

```python
cfg = json.load(...)
```

The configuration controls:

* Listing delimiters
* Neighborhood cues
* Property type vocabulary
* Currency definitions
* Section headers
* Parsing overrides

---

## 2. Agency and Date Detection

Agency and source date are inferred automatically.

### Agency

Derived from:

```text
agency_roca.json
```

### Date

Derived from:

```text
roca_20110128.txt
```

Result:

```text
Agency = ROCA
Date = 20110128
```

---

## 3. Preprocessing

The parser optionally applies preprocessing rules defined in the agency configuration.

Examples:

* Numbered listing conversion
* Text normalization
* Marker insertion
* Advertisement separation

This stage prepares heterogeneous source files for standardized parsing.

---

## 4. Listing Segmentation

The source file is divided into individual advertisement records.

The segmentation method depends on:

```json
{
    "listing_marker": "NUMBERED"
}
```

or alternative agency-specific markers.

---

## 5. Section Context Detection

The parser detects contextual headers.

Examples:

```text
VENTA DE CASAS
ALQUILER DE APARTAMENTOS
VENTA DE TERRENOS
```

Detected context is inherited by subsequent listings until a new section header appears.

This allows transaction type and property type to be inferred even when not explicitly stated within the advertisement.

---

## 6. Record Parsing

Each advertisement is processed using:

```python
parse_record(...)
```

Attributes extracted may include:

* Neighborhood
* Bedrooms
* Bathrooms
* Area
* Terrain area
* Price
* Currency
* Property type
* Transaction type

---

## 7. Price Extraction

The parser performs an additional price-detection pass.

Processing includes:

### Text Cleaning

```python
clean_text_for_price(...)
```

### Price Extraction

```python
extract_price(...)
```

The parser compares candidate prices and retains the most plausible value.

This defensive strategy improves extraction accuracy when multiple numeric values are present.

---

## 8. Area Standardization

The parser prioritizes construction area when available.

Priority order:

```text
Construction Area (m²)
        ↓
General Area
        ↓
Terrain Area (v²)
```

Outputs include:

* area
* area_unit
* area_m2
* AT
* AT_unit

---

## 9. Canonical Record Creation

Each listing is transformed into the standard framework schema.

Core fields include:

| Field            | Description                 |
| ---------------- | --------------------------- |
| Listing ID       | Sequential identifier       |
| title            | Advertisement title         |
| neighborhood     | Parsed neighborhood         |
| bedrooms         | Bedroom count               |
| bathrooms        | Bathroom count              |
| AT               | Terrain area                |
| area             | Built area                  |
| price            | Extracted price             |
| currency         | Standardized currency       |
| transaction      | Rent or sale                |
| property_type    | Property classification     |
| agency           | Source agency               |
| date             | Advertisement date          |
| notes            | Original advertisement text |
| source_type      | Source classification       |
| ingestion_id     | Input filename              |
| pipeline_version | Processing version          |

---

# Output Structure

Output files are organized automatically.

Structure:

```text
output/
└── roca/
    └── 2011/
        └── ROCA_20110128.csv
```

Pattern:

```text
output/<agency>/<year>/<AGENCY>_<date>.csv
```

---

# Output Encoding

CSV files are written using:

```text
UTF-8-SIG
```

This improves compatibility with spreadsheet software and GIS tools.

---

# Quality Control Features

## Context Inheritance

Section headers propagate transaction and property types to subsequent listings.

## Secondary Price Detection

A second extraction pass validates candidate prices.

## Standardized Schema

All agencies generate identical output structures.

## Configuration-Based Processing

Agency-specific behavior is isolated from parser code.

---

# Generated Metadata

The parser automatically records:

* Agency
* Advertisement date
* Source filename
* Pipeline version
* Source type

These fields support provenance tracking and reproducibility.

---

# Typical Output

Example:

| Listing ID | Neighborhood       | Price  | Currency | Transaction | Property Type |
| ---------- | ------------------ | ------ | -------- | ----------- | ------------- |
| 1          | Palmira            | 250000 | USD      | SALE        | HOUSE         |
| 2          | Lomas del Guijarro | 1200   | USD      | RENT        | APARTMENT     |

---

# Relationship to the Framework

`AgencyCoreParser_v1.py` is the foundational extraction component of the SDG-11 Real Estate Framework.

All downstream processes—including deduplication, GIS matching, price standardization, transaction validation, and aggregation—depend on the standardized records generated by this parser.

Because the parser is configuration-driven, new agencies, publication years, and source formats can be incorporated primarily through configuration updates rather than software modifications, supporting long-term sustainability and reproducibility of the framework.

Field dictionary table documenting every output column (Listing ID, AT, AT_unit, source_type, pipeline_version, etc.). That would become the canonical schema documentation for the entire project.