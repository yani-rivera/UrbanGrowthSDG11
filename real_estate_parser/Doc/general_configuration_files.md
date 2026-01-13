## General Configuration Files

This project relies on a small set of **explicit configuration files** to control
scope, normalization, and exclusion rules.

These files define *what is included, excluded, or standardized* during processing.
They contain **decisions**, not observations.

All configuration files are read-only during execution.

---

## Overview

| File | Type | Purpose |
|------|------|--------|
| `agency_mnemonics.csv` | CSV | Defines stable short codes for data sources |
| `outside_metro.txt` | TXT | Lists locations outside the metropolitan study area |
| `remove_words.txt` | TXT | Defines non-informative words to remove from text |
| `exclude_types.csv` | CSV | Defines property types excluded from the study |

---

## 1. `agency_mnemonics.csv`

**Purpose**  
Defines short, stable identifiers (mnemonics) for each data source
(newspaper, agency, or platform).

**Why it exists**
- Agency names may change over time
- Filenames and identifiers should remain short and consistent
- Source logic should never be hard-coded in scripts

**Typical uses**
- File naming
- Output directory structure
- Provenance fields
- Unique listing identifiers

This file is the **authoritative reference** for source identity.

---

## 2. `outside_metro.txt`

**Purpose**  
Lists place names that are explicitly **outside the metropolitan study area**.

**Why it exists**
- Newspapers often include listings from nearby towns or rural areas
- These listings may be valid advertisements but out of scope for the study

**How it is used**
- Extracted locations are compared against this list
- Matches are flagged or excluded during processing
- Original text is preserved for traceability

This file defines **spatial scope**, not data quality.

---

## 3. `remove_words.txt`

**Purpose**  
Defines words or phrases that should be removed during neighborhood text normalization.

**Typical contents**
- Descriptive adjectives
- Marketing language
- Repetitive fillers

**Why it exists**
- Reduces noise in free-text listings
- Improves pattern matching and parsing
- Keeps scripts simple and configurable, and match the neihborhood catalog.

Text cleaning rules live here, not in code.

---

## 4. `exclude_types.csv`

**Purpose**  
Defines property types that are **explicitly excluded** from the study.

**Examples**
- Land / lots
- Commercial properties
- Warehouses
- Offices

**Why it exists**
- The study may focus only on residential housing
- Exclusion rules should be transparent and documented

Listings matching excluded types are flagged or removed according to pipeline rules.

---

## Design Principles

- Configuration files encode decisions, not logic
- Scripts remain generic and reusable
- Scope changes are traceable and auditable
- New cases are handled by extending configs, not rewriting code

---

These configuration files form the **interpretive boundary** of the pipeline
and should be reviewed alongside scripts and outputs.
