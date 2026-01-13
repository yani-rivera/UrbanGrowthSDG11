## Merge & Clean — UID Assignment Step (L1clean)

This document describes the **UID assignment step** of the L1clean phase,
where each listing is assigned a **stable unique identifier**.

This step occurs **after normalization and word filtering** and before
final QC and analysis.

---

## Script Overview

**Script:** `tools/AddUid.py`  
**Stage:** L1clean (identifier assignment)

This script:
- reads a cleaned CSV file
- assigns a stable UID to each row
- uses agency mnemonics and dates to ensure uniqueness
- writes a new CSV with the UID included

No rows are removed or reordered.

---

## Basic Execution

```bash
python tools/AddUid.py   -i consolidated/2010/merged_2010_flt.csv   -o consolidated/2010/merged_2010_uid.csv   --agency-col agency   --date-col date   --mnemonics config/agency_mnemonics.csv   --mnemonic-required   --encoding utf-8-sig
```

---

## Command-Line Arguments

| Argument | Description |
|--------|------------|
| `-i` | Input CSV file (filtered, canonical dataset) |
| `-o` | Output CSV file with UID column |
| `--agency-col` | Column containing agency name |
| `--date-col` | Column containing listing date |
| `--mnemonics` | CSV file mapping agencies to mnemonics |
| `--mnemonic-required` | Fail if agency mnemonic is missing |
| `--encoding` | Output file encoding |

---

## UID Construction Logic

UIDs are constructed deterministically using:

- agency mnemonic
- listing date
- row-level sequence

This ensures that:
- UIDs are stable across reruns
- listings can be traced to source and time
- datasets can be merged safely across years

> UID generation is deterministic, not random.

---

## Input Requirements

The input CSV must:
- originate from the word-filtering step (`*_flt.csv`)
- contain valid agency and date columns
- use consistent date formatting
- match entries in `agency_mnemonics.csv`

If `--mnemonic-required` is set and a mnemonic is missing,
the script will stop with an error.

---

## Output

The output file:

```text
merged_2010_uid.csv
```

Contains:
- all original columns
- an additional UID column
- unchanged row order

This file becomes the **canonical identifier layer**
for downstream QC and analysis.

---

## Important Notes

- UID assignment does not imply data quality
- No interpretation or filtering occurs
- Encoding is explicitly controlled (`utf-8-sig`)
- The original file is preserved

---

## Methodological Note

> Stable identifiers are assigned after normalization to ensure
> that equivalent listings receive comparable UIDs across runs.

This guarantees traceability and reproducibility.

---

This step completes the structural preparation of the dataset
for quality control and analysis.
