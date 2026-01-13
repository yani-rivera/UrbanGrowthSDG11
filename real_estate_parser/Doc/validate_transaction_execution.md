## Merge & Clean — Transaction Validation (L1clean)

This document describes the **transaction validation step** of the L1clean phase.
Using standardized prices, this step verifies that each listing’s transaction
type (Sale vs Rent) is **internally consistent** with its price.

This step corrects or flags listings that were misclassified during parsing.

---

## Script Overview

**Script:** `L1clean/ValidateTransaction.py`  
**Stage:** L1clean (transaction validation)

This script:
- reads price-standardized listings
- evaluates transaction type against price signals
- corrects misclassified transactions where rules are decisive
- writes a validated output CSV

No rows are dropped.

---

## Why This Step Is Needed

Historical listings may:
- label a sale as rent (or vice versa)
- reuse section headers incorrectly
- mix marketing language across transactions

Once prices are standardized, **price magnitude becomes a strong validator**
of transaction intent.

---

## Basic Execution

```bash
python L1clean/ValidateTransaction.py   --input consolidated/2010/merged_2010_STDPrice.csv   --output consolidated/2010/merged_2010_STDPrice_t.csv
```

---

## Command-Line Arguments

| Argument | Description |
|--------|------------|
| `--input` | Input CSV with standardized prices |
| `--output` | Output CSV with validated transactions |

---

## Validation Logic

The script evaluates each listing using:
- standardized price (e.g. USD)
- property type
- predefined price thresholds per transaction type

Typical rules include:
- implausibly low prices for sales → candidate rent
- implausibly high prices for rent → candidate sale

When validation rules are conclusive:
- the transaction type is corrected
- the decision is recorded

When ambiguity remains:
- the original transaction is preserved
- the listing may be flagged for QC

> Price is used as a validator, not as a classifier of first resort.

---

## Output

The output file:

```text
merged_2010_STDPrice_t.csv
```

Contains:
- all original columns
- validated (or confirmed) transaction type
- unchanged row order

This file is used for:
- downstream QC
- statistical analysis
- rent vs sale segmentation

---

## Important Notes

- Original transaction labels are never deleted
- Corrections are deterministic and rule-based
- No listing is removed at this step
- Ambiguous cases remain explicit

---

## Methodological Note

> Transaction validation is applied after price standardization to ensure
> that corrections are based on comparable economic signals.

This reduces classification bias and improves analytical consistency.

---

This step completes **transaction consistency validation**
within the L1clean pipeline.
