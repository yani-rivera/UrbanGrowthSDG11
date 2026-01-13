## Merge & Clean — Deduplication Step (L1clean)

This document describes the **deduplication step** of the L1clean phase,
performed after CSV consolidation.

Deduplication separates **canonical listings** from **detected duplicates**
without deleting any data.

---

## Script Overview

**Script:** `tools/MergeDeduplicate.py`  
**Stage:** L1clean (deduplication phase)

This script:
- reads a consolidated CSV file
- identifies duplicate listings using deterministic rules
- outputs two separate files:
  - canonical listings
  - duplicate listings

No rows are overwritten or lost.

---

## Basic Execution

To deduplicate a merged yearly dataset:

```bash
python tools/MergeDeduplicate.py   --input consolidated/2010/merged_2010.csv   --out-canonical consolidated/2010/merged_2010_c.csv   --out-duplicates consolidated/2010/merged_2010_duplicates.csv
```

---

## Command-Line Arguments

| Argument | Description |
|--------|------------|
| `--input` | Path to merged CSV file |
| `--out-canonical` | Output path for canonical (unique) listings |
| `--out-duplicates` | Output path for detected duplicates |

---

## Input Requirements

The input CSV must:
- originate from the merge step
- use a consistent schema
- contain provenance fields (agency, date, ingestion ID, etc.)

---

## Output Files

### 1) Canonical file

```text
merged_2010_c.csv
```

Contains:
- one representative row per unique listing
- all original columns
- unchanged values

This file is used for **analysis and statistics**.

---

### 2) Duplicates file

```text
merged_2010_duplicates.csv
```

Contains:
- listings identified as duplicates
- full original content
- linkage to canonical counterparts (if available)

This file is used for:
- transparency
- audit
- methodological validation

---

## Important Rules

- No duplicate rows are deleted
- Deduplication is **reversible**
- Rules are deterministic and documented
- Canonical selection follows consistent precedence

> Deduplication classifies data — it does not erase it.

---

## Methodological Note

> Deduplication is applied after merging to ensure that all potential
> duplicates are evaluated in a single, comprehensive dataset.

This ensures comparability across agencies and time.

---

This step completes the structural consolidation of the dataset
and prepares it for quality control and analysis.
