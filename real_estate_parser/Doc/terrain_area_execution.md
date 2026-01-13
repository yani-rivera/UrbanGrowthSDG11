## Merge & Clean — Terrain / Lot Area Standardization (L1clean)

This document describes the **terrain (lot) area standardization step** of the L1clean phase.
At this stage, **only land / lot size measurements** are converted to square meters (m²),
when required.

Built area measurements are not modified in this step.

---

## Script Overview

**Script:** `tools/terrain_area_to_at.py`  
**Stage:** L1clean (area standardization — terrain only)

This script:
- reads listings with validated transactions and standardized prices
- identifies terrain / lot area values (AT)
- converts terrain area units to square meters (m²) when necessary
- preserves original area values and units

No rows are dropped.

---

## Purpose of This Step

Historical listings may express **terrain (lot) size** using:
- square meters (`m2`, `mts`)
- square varas (`v2`, `varas`)
- other local units

To enable:
- cross-listing comparison
- density and land-use analysis
- price-per-area metrics

terrain area must be standardized to **m²**.

---

## Basic Execution

```bash
python tools/terrain_area_to_at.py   --input consolidated/2010/merged_2010_STDPrice_t.csv   --output consolidated/2010/merged_2010_STDPrice_AreaM2.csv
```

---

## Command-Line Arguments

| Argument | Description |
|--------|------------|
| `--input` | Input CSV with validated transactions and prices |
| `--output` | Output CSV with standardized terrain area |

---

## Conversion Logic

- Only **terrain / lot area (AT)** fields are considered
- Built area values remain unchanged
- Unit detection is rule-based and deterministic
- Conversion factors are fixed and documented
- Original area values and units are preserved

A new standardized field (e.g. `AT_m2`) is created or updated.

> This step does not infer missing areas.

---

## Input Requirements

The input CSV must:
- originate from the transaction validation step (`*_STDPrice_t.csv`)
- contain terrain area values when applicable
- follow the standard schema

---

## Output

The output file:

```text
merged_2010_STDPrice_AreaM2.csv
```

Contains:
- all original columns
- standardized terrain area in square meters
- unchanged row order

This file is suitable for:
- land price analysis
- density calculations
- spatial normalization

---

## Important Notes

- Only lot size is converted
- Built area is not altered
- Missing or ambiguous units are left unchanged
- Conversion is deterministic and reversible

---

## Methodological Note

> Terrain area standardization is applied after price and transaction validation
> to ensure that area-based metrics are computed on economically consistent listings.

This maintains analytical integrity across dimensions.

---

This step completes **area standardization** within the L1clean pipeline.
