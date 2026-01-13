## Merge & Clean — Word Filtering Step (L1clean)

This document describes the **word filtering step** of the L1clean phase,
applied after merging and deduplication.

This step removes predefined non-informative words from a selected column
to improve consistency and downstream matching.

---

## Script Overview

**Script:** `tools/word_filter.py`  
**Stage:** L1clean (normalization phase)

This script:
- reads a canonical (deduplicated) CSV file
- applies a word-removal list to a specific column
- writes a filtered version of the dataset

No rows are dropped or reordered.

---

## Basic Execution

To apply word filtering to the neighborhood column:

```bash
python tools/word_filter.py   --input consolidated/2010/merged_2010_c.csv   --output consolidated/2010/merged_2010_flt.csv   --col neighborhood   --words-file config/remove_words.txt
```

---

## Command-Line Arguments

| Argument | Description |
|--------|------------|
| `--input` | Path to the canonical (deduplicated) CSV |
| `--output` | Path for the filtered output CSV |
| `--col` | Column to apply word filtering to |
| `--words-file` | Text file containing words to remove |

---

## Input Requirements

The input CSV must:
- originate from the deduplication step (`*_c.csv`)
- contain the specified column (e.g. `neighborhood`)
- follow the standard output schema

---

## Word Removal Logic

- Words listed in `remove_words.txt` are removed **exactly**
- Matching is case-insensitive
- Only the specified column is modified
- Other columns remain unchanged

The original unfiltered file is preserved.

---

## Output

The filtered file is written to:

```text
merged_2010_flt.csv
```

This file:
- contains the same rows as the input
- has normalized text in the target column
- is suitable for catalog matching and QC

---

## Important Notes

- This step supports **normalization**, not interpretation
- No guessing or replacement is performed
- Word filtering is deterministic and reversible
- The operation is column-scoped

> Words are removed to reduce noise, not to redefine meaning.

---

## Methodological Note

> Word filtering is applied after deduplication to ensure
> consistent normalization across unique listings only.

This maintains transparency and avoids compounding effects on duplicates.

---

This step prepares the dataset for quality control
and standardized analysis.
