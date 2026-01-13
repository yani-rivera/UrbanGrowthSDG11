## Merge & Clean — Neighborhood Normalization Step (L1clean)

This document describes the **neighborhood cleaning and normalization step**
of the L1clean phase.

This step standardizes neighborhood names and optionally adds a normalized
variant for matching and analysis.

---

## Script Overview

**Script:** `tools/clean_neighborhoods.py`  
**Stage:** L1clean (neighborhood normalization)

This script:
- reads a CSV with assigned UIDs
- cleans the neighborhood column
- optionally adds a normalized neighborhood field
- writes a new cleaned CSV

No rows are dropped or reordered.

---

## Basic Execution

```bash
python tools/clean_neighborhoods.py   --input_csv consolidated/2010/merged_2010_uid.csv   --input_col neighborhood   --out_csv consolidated/2010/merged_2010_clean.csv   --add_norm
```

---

## Command-Line Arguments

| Argument | Description |
|--------|------------|
| `--input_csv` | Input CSV file with UID-assigned listings |
| `--input_col` | Column containing neighborhood names |
| `--out_csv` | Output CSV with cleaned neighborhoods |
| `--add_norm` | Add an additional normalized neighborhood column |

---

## Cleaning and Normalization Logic

The script applies deterministic transformations to the neighborhood column,
which may include:

- trimming extra whitespace
- standardizing case
- removing punctuation
- applying accent normalization
- collapsing repeated separators

When `--add_norm` is used, a new column is created (e.g. `neighborhood_norm`)
containing a fully normalized version suitable for matching and grouping.

The original neighborhood value is preserved.

---

## Input Requirements

The input CSV must:
- originate from the UID assignment step (`*_uid.csv`)
- contain the specified neighborhood column
- follow the standard schema

---

## Output

The output file:

```text
merged_2010_clean.csv
```

Contains:
- all original columns
- cleaned neighborhood values
- optional normalized neighborhood column
- unchanged row order

This file is used for:
- catalog matching
- spatial joins
- quality control
- analysis-ready datasets

---

## Important Notes

- No interpretation or reassignment occurs
- Cleaning is deterministic and reversible
- Original values are preserved
- This step does not validate neighborhoods against catalogs

---

## Methodological Note

> Neighborhood normalization is applied after UID assignment to ensure
> that identifier stability is preserved regardless of textual cleaning.

This maintains traceability while improving analytical consistency.

---

This step completes neighborhood preparation within the L1clean phase.
