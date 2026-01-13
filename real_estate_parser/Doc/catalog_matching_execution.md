## Merge & Clean — Catalog Matching & GIS Enrichment (L1clean)

This document describes the **catalog matching step** of the L1clean phase,
where cleaned listings are matched to a **standard neighborhood catalog**
to obtain stable GIS identifiers.

This step enriches the dataset with spatial reference codes while preserving
all matching uncertainty.

---

## Script Overview

**Script:** `tools/match_cleaned_to_catalog.py`  
**Stage:** L1clean (catalog matching / GIS enrichment)

This script:
- reads the final filtered listings
- matches normalized neighborhood names to a standard catalog
- assigns GIS identifiers from the catalog
- produces separate outputs for matched and unmatched records

No listings are silently discarded.

---

## Purpose of This Step

The neighborhood catalog provides:
- authoritative neighborhood names
- stable GIS identifiers
- consistent spatial references across years

This step converts **textual neighborhoods** into **spatially referencable units**.

---

## Basic Execution

```bash
python tools/match_cleaned_to_catalog.py   --listings_csv consolidated/2010/merged_2010_filtered.csv   --listings_col neighborhood_clean_norm   --catalog_csv Catalog/standard_neighborhood_catalog.csv   --out_merged consolidated/2010/merged_2010_with_gis.csv   --out_matched consolidated/2010/matched.csv   --out_unmatched consolidated/2010/unmatched.csv
```

---

## Command-Line Arguments

| Argument | Description |
|--------|------------|
| `--listings_csv` | Input CSV containing filtered listings |
| `--listings_col` | Neighborhood column used for matching |
| `--catalog_csv` | Standard neighborhood catalog CSV |
| `--out_merged` | Output CSV enriched with GIS identifiers |
| `--out_matched` | Output CSV containing matched listings only |
| `--out_unmatched` | Output CSV containing unmatched listings |

---

## Matching Logic

- Matching is performed using the normalized neighborhood field
- Matches are exact or rule-based (as configured)
- GIS identifiers are copied from the catalog into matched rows
- Unmatched listings are preserved without GIS enrichment

The catalog typically provides fields such as:
- `GISID`
- `uid`
- standardized neighborhood labels

---

## Output Files

### 1) Enriched dataset (primary output)

```text
merged_2010_with_gis.csv
```

Contains:
- all filtered listings
- GIS identifiers for matched neighborhoods
- unchanged non-spatial attributes

This file is used for:
- spatial joins
- GIS analysis
- SDG-11 indicators

---

### 2) Matched listings

```text
matched.csv
```

Contains only listings successfully linked to the catalog.

---

### 3) Unmatched listings

```text
unmatched.csv
```

Contains:
- listings with unresolved neighborhood names
- full original context
- candidates for catalog expansion or manual review

---

## Important Notes

- Matching does not modify listing attributes
- Unmatched listings are expected in historical data
- Catalog completeness evolves over time
- Matching is deterministic and reproducible

> Unmatched data is information, not failure.

---

## Methodological Note

> Catalog matching is applied after full cleaning and filtering to ensure
> that spatial identifiers are assigned only to in-scope, validated listings.

This preserves spatial integrity and analytical consistency.

---

This step completes **GIS enrichment** of the L1clean dataset.
