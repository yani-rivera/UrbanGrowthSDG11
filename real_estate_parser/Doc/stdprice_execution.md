## Merge & Clean — Currency Standardization (L1clean)

This document describes the **currency standardization step** of the L1clean phase,
where listing prices are converted to a **common reference currency** using
external exchange rate tables.

This step produces **analysis-ready, comparable prices** across time.

---

## Script Overview

**Script:** `tools/StdPrice.py`  
**Stage:** L1clean (price standardization)

This script:
- reads GIS-enriched and validated listings
- applies exchange rates from an external FX table
- converts prices to a standard currency (USD)
- preserves original price and currency information

No rows are dropped.

---

## Purpose of This Step

Historical listings may:
- use different currencies (e.g. HNL, USD)
- span multiple years with changing exchange rates

This step ensures that:
- all prices are comparable
- temporal analysis is meaningful
- original monetary context is preserved

---

## Basic Execution

```bash
python tools/StdPrice.py   --input consolidated/2010/merged_2010_with_gis_valid.csv   --fx FXrate/fx_HNL_USD.csv   --output consolidated/2010/merged_2010_STDPrice.csv
```

---

## Command-Line Arguments

| Argument | Description |
|--------|------------|
| `--input` | Input CSV with validated, GIS-enriched listings |
| `--fx` | Exchange rate CSV file |
| `--output` | Output CSV with standardized prices |

---

## Exchange Rate File

The FX file (e.g. `fx_HNL_USD.csv`) typically contains:
- source currency
- target currency
- exchange rate
- applicable year or date

Exchange rates are **fixed per period** and documented externally.

---

## Standardization Logic

- Original price and currency columns are preserved
- A standardized price column is created (e.g. `price_usd`)
- Conversion uses the exchange rate corresponding to the listing period
- Missing or invalid prices are left unchanged and flagged if applicable

> Standardization does not overwrite economic context.

---

## Output

The output file:

```text
merged_2010_STDPrice.csv
```

Contains:
- all original columns
- standardized price column(s)
- unchanged row order

This file is suitable for:
- statistical analysis
- cross-year comparison
- SDG-11 indicators

---

## Important Notes

- Currency conversion is deterministic
- FX tables are versioned and auditable
- No inference is made when FX data is missing
- Original values remain the ground truth

---

## Methodological Note

> Price standardization is applied after full validation and GIS enrichment
> to ensure that only in-scope, spatially valid listings are converted.

This preserves analytical integrity across space and time.
