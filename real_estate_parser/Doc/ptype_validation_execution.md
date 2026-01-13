## Merge & Clean — Property Type Validation (L1clean)

This document describes the **property type validation and correction step**
of the L1clean phase.

This step resolves listings with **mixed, ambiguous, or inconsistent property types**
and produces both corrected outputs and diagnostic scores.

---

## Script Overview

**Script:** `L1clean/ptype_l1_clean_v8.py`  
**Stage:** L1clean (property type validation)

This script:
- reads a neighborhood-cleaned CSV
- evaluates property type assignments
- resolves mixed or conflicting signals
- outputs a corrected dataset
- produces a scoring file for transparency

No rows are deleted.

---

## Why This Step Is Needed

Real-estate listings often:
- mention multiple property types (e.g. house + apartment)
- contain contradictory cues
- reuse marketing language inconsistently

Rather than guessing, this step **scores and validates** property types explicitly.

---

## Basic Execution

```bash
python L1clean/ptype_l1_clean_v8.py   --input consolidated/2010/merged_2010_clean.csv   --output consolidated/2010/merged_2010_clean_ptype_fixed.csv   --scores-output consolidated/2010/merged_2010_clean_ptype_fixed_scores.csv
```

---

## Command-Line Arguments

| Argument | Description |
|--------|------------|
| `--input` | Input CSV after neighborhood cleaning |
| `--output` | Output CSV with validated property types |
| `--scores-output` | CSV containing scoring and decision diagnostics |

---

## Property Type Validation Logic

The script evaluates property type using multiple signals, which may include:
- parsed property type field
- keywords in listing text
- section headers
- exclusion rules

Each candidate type is assigned a **score**.

The final property type is selected based on:
- highest score
- consistency rules
- exclusion thresholds

If ambiguity remains, the listing is flagged.

---

## Output Files

### 1) Corrected dataset

```text
merged_2010_clean_ptype_fixed.csv
```

Contains:
- all original columns
- validated `property_type`
- preserved raw values
- unchanged row order

This file is used for downstream analysis.

---

### 2) Scoring diagnostics

```text
merged_2010_clean_ptype_fixed_scores.csv
```

Contains:
- candidate property types
- individual scores
- decision rationale per listing

This file exists for:
- transparency
- debugging
- methodological validation

---

## Important Notes

- No listings are removed
- Decisions are explicit and traceable
- Mixed-type listings are resolved deterministically
- Scores allow post-hoc review and tuning

> Validation replaces ambiguity with documented decisions.

---

## Methodological Note

> Property type validation is applied after structural cleaning to ensure
> that classification decisions are made on normalized, stable inputs.

This preserves consistency across agencies and years.

---

This step completes **property type resolution** within the L1clean pipeline.
