# Aggregated Neighborhood Data — Execution Summary

This document describes the **aggregation stage** used to produce
**publishable neighborhood-level datasets** from the unified L1clean files.

All aggregation scripts operate on **standardized, validated, GIS-linked data**
and apply minimum-sample thresholds to ensure statistical robustness.

---

## Input to Aggregation

All aggregation scripts take as input the **final unified L1clean dataset**
for a given year (or year–month):

```text
consolidated/2010/merged_2010_STDPrice_AreaM2.csv
```

This file contains:
- standardized prices (USD)
- validated transaction types
- standardized terrain area (m²)
- cleaned and normalized neighborhoods
- GIS identifiers
- only in-scope listings

---

## Minimum Sample Rule (`--min-n`)

All aggregation scripts apply a **minimum count threshold**:

```text
--min-n 5
```

This means:
- groups with fewer than 5 listings are excluded
- protects privacy
- improves statistical stability
- avoids over-interpreting sparse data

This rule is consistent across all published aggregates.

---

## 1. Neighborhood Monthly Summary (Core)

**Script**
```bash
python tools/Aggregate_2010_Neighborhood_Summary.py   --input consolidated/2010/merged_2010_STDPrice_AreaM2.csv   --min-n 5   --output consolidated/2010/neighborhood_2010monthly.csv
```

### Output
```text
neighborhood_2010monthly.csv
```

### Description
Produces a **monthly neighborhood-level summary**, including:
- listing counts
- price statistics (USD)
- transaction splits (rent / sale)

This is the **core published table** for longitudinal analysis.

---

## 2. Price by Bedrooms (Neighborhood × Month)

**Script**
```bash
python tools/Aggregate_Neighborhood_Summary_ByYear_Bedrooms.py   --input consolidated/2010/merged_2010_STDPrice_AreaM2.csv   --year 2010   --min-n 5   --output consolidated/2010/neighborhood_monthly_bedrooms_price.csv
```

### Output
```text
neighborhood_monthly_bedrooms_price.csv
```

### Description
Aggregates prices by:
- neighborhood
- month
- number of bedrooms

Used to analyze:
- price stratification by dwelling size
- affordability gradients within neighborhoods

---

## 3. Area-Based Neighborhood Summary

**Script**
```bash
python tools/Aggregate_Neighborhood_Summary_ByYear_Area.py   --input consolidated/2010/merged_2010_STDPrice_AreaM2.csv   --year 2010   --min-n 5   --output consolidated/2010/neighborhood_2010_monthly_area.csv
```

### Output
```text
neighborhood_2010_monthly_area.csv
```

### Description
Aggregates area metrics by neighborhood and month, including:
- median built area
- median terrain / lot size
- area-based listing counts

Supports density and land-use analysis.

---

## 4. Flexible Area × Bedrooms Summary

**Script**
```bash
python tools/Aggregate_Neighborhood_Summary_ByYear_AreaBeds_Flexible.py   --input consolidated/2010/merged_2010_STDPrice_AreaM2.csv   --year 2010   --min-n 5   --output consolidated/2010/neighborhood_2010_monthly_area_beds.csv
```

### Output
```text
neighborhood_2010_monthly_area_beds.csv
```

### Description
Produces a **multi-dimensional aggregation** by:
- neighborhood
- month
- bedrooms
- area ranges

This table enables:
- price-per-area analysis
- size-adjusted affordability studies
- flexible downstream grouping

---

## Output Characteristics (All Aggregates)

All aggregated datasets:

- are derived only from **accepted L1clean listings**
- are reproducible from the pipeline
- contain no individual-level identifiers
- apply consistent minimum-sample thresholds
- are suitable for public release

---

## Methodological Statement

> Neighborhood-level aggregation transforms validated real-estate listings
> into statistically robust summaries that support spatial and temporal
> analysis while protecting individual listing detail.

---

These aggregated files represent the **final published research products**
of the SDG-11 real-estate data pipeline.
