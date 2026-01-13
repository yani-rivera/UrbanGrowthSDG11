## Merge & Clean — Final Filtering & Exclusion (L1clean)

This document describes the **final filtering step** of the L1clean phase.
At this stage, listings are **explicitly accepted or rejected** based on
property type, neighborhood scope, and price presence.

This step produces the **analysis-ready dataset** and a **rejected listings log**.

---

## Script Overview

**Script:** `L1clean/FilterMergedFile.py`  
**Stage:** L1clean (final filtering)

This script:
- reads a property-type-validated CSV
- filters listings based on inclusion rules
- separates accepted and rejected listings
- writes both outputs explicitly

No data is silently dropped.

---

## Purpose of This Step

This step enforces **research scope constraints**, including:
- allowed property types
- geographic coverage (metro vs outside)
- minimal structural validity (e.g. price present)

It is the **only step** where listings are formally rejected.

---

## Basic Execution

```bash
python L1clean/FilterMergedFile.py   -i consolidated/2010/merged_2010_clean_ptype_fixed.csv   -o consolidated/2010/merged_2010_filtered.csv   --price-col "price"   --type-col "property_type_new"   --exclude-types-files config/exclude_types.csv:Type   --exclude-neighborhoods-files config/outside_metro.txt   --neigh-col neighborhood_clean_norm   --rejected consolidated/2010/2010_filtered_rejected.csv   --neigh-match exact
```

---

## Command-Line Arguments

| Argument | Description |
|--------|------------|
| `-i` | Input CSV after property type validation |
| `-o` | Output CSV containing accepted listings |
| `--rejected` | Output CSV containing rejected listings |
| `--price-col` | Column containing price values |
| `--type-col` | Column containing validated property types |
| `--exclude-types-files` | CSV file and column defining excluded property types |
| `--exclude-neighborhoods-files` | Text file listing neighborhoods outside scope |
| `--neigh-col` | Neighborhood column used for matching |
| `--neigh-match` | Neighborhood matching mode (`exact`) |

---

## Filtering Logic

A listing is **accepted** only if:
- property type is **not** listed in `exclude_types.csv`
- neighborhood is **not** listed in `outside_metro.txt`
- price value is present and valid
- neighborhood matching passes the specified strategy

Listings failing any rule are **written to the rejected file**.

---

## Output Files

### 1) Accepted listings (analysis-ready)

```text
merged_2010_filtered.csv
```

Contains:
- only listings within scope
- validated and normalized attributes
- stable UIDs
- ready for analysis and GIS joining

---

### 2) Rejected listings (audit trail)

```text
2010_filtered_rejected.csv
```

Contains:
- full original rows
- reason(s) for rejection (if available)
- preserved provenance

This file ensures:
- transparency
- reproducibility
- methodological defensibility

---

## Important Notes

- Rejection is explicit and documented
- No listings are deleted without trace
- Scope is enforced consistently across years
- Configuration files define research boundaries

> Filtering defines the dataset — not the parser.

---

## Methodological Note

> Final filtering is applied only after full normalization and validation
> to ensure that exclusion decisions are based on stable, comparable data.

This step produces the **final L1clean dataset** used for SDG‑11 analysis.
