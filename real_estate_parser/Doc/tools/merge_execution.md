## Merge & Clean — CSV Consolidation (L1clean)

This document describes how to **merge parsed CSV outputs** produced by the parser
into consolidated tables as part of the **L1clean** stage.

The merge step combines multiple per-file outputs into a single table
at a chosen **temporal resolution**.

---

## Script Overview

**Script:** `tools/merge_output_csvs.py`  
**Stage:** L1clean (merge phase)

This script:
- reads parser outputs from the `output/` directory
- selects files by date scope
- concatenates them into a consolidated CSV
- preserves all rows and columns

No cleaning, filtering, or deduplication occurs at this stage.

---

## Basic Execution (Year-Level Merge)

To merge all parsed outputs for a given **year**:

```bash
python tools/merge_output_csvs.py   --year 2010   --input output   --output consolidated
```

This command:
- scans `output/` recursively
- selects all CSV files associated with year **2010**
- writes a merged file under the `consolidated/` directory

---

## Supported Merge Granularities

The script supports multiple temporal resolutions for merging.

### 1) Year-level (`yyyy`)

```bash
--year 2010
```

Use when:
- working with annual datasets
- preparing year-level statistics
- building longitudinal panels

---

### 2) Month-level (`yyyymm`)

```bash
--year 201001
```

Use when:
- monthly sampling is required
- intra-year seasonality is analyzed
- debugging specific months

All files matching `201001` are merged.

---

### 3) Day-level (`yyyymmdd`)

```bash
--year 20100115
```

Use when:
- validating a specific issue
- reproducing a single-day extraction
- debugging parser behavior

Only files matching the exact date are merged.

---

## Input and Output Parameters

| Argument | Description |
|--------|------------|
| `--year` | Temporal selector (`yyyy`, `yyyymm`, or `yyyymmdd`) |
| `--input` | Base directory containing parser outputs |
| `--output` | Directory where consolidated CSV is written |

---

## Input Structure Assumption

The script expects parser outputs organized as:

```text
output/
└── <Agency>/
    └── <Year>/
        └── *.csv
```

Files may originate from different agencies and dates,
as long as they share a compatible schema.

---

## Output

The merged file is written to:

```text
consolidated/
└── merged_<year>.csv
```

(Exact filename may vary, but includes the temporal selector.)

The output:
- contains all rows from the selected inputs
- preserves original columns and values
- introduces no transformations

---

## Important Notes

- This step is **pure concatenation**
- No deduplication is performed here
- No rows are dropped
- Order of rows is preserved as read

> Merge first. Clean later.

---

## Methodological Note

> Merging is performed prior to any cleaning or filtering to ensure
> that all raw parsed listings are preserved and auditable.

This guarantees transparency and reproducibility in downstream cleaning steps.
