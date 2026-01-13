# SDG-11 Real-Estate Dataset — Published Data Summary

This document describes the **final aggregated datasets** produced from the
L1clean pipeline and prepared for **public release and publication**.

These datasets are derived from the unified, cleaned listings and are designed
to support **reproducible urban and housing analysis** under SDG‑11.

---

## Purpose of Aggregation

Raw or listing-level data:
- is high volume,
- contains sensitive contextual detail,
- and is not always suitable for direct publication.

Aggregation serves to:
- protect sensitive information,
- reduce noise and duplication,
- enable comparison across space and time,
- and produce compact, reusable research products.

> Aggregated data represents *patterns*, not individual listings.

---

## Level of Aggregation

Published datasets are aggregated along the following dimensions:

- **Spatial**: neighborhood (GIS-linked)
- **Temporal**: year or year–month
- **Market**:
  - transaction type (Sale / Rent)
  - property type (House / Apartment)

Each row represents a **summary of multiple listings**.

---

## Core Aggregated Tables

### 1. Listing Counts

Counts of listings per group:

- total listings
- listings by transaction type
- listings by property type

Used to assess:
- market activity
- spatial coverage
- temporal trends

---

### 2. Price Statistics (Standardized Currency)

All prices are based on **standardized values (USD)**.

Typical statistics include:
- minimum price
- maximum price
- mean price
- median price
- standard deviation
- interquartile range (IQR)

These are computed separately for:
- sales
- rentals

---

### 3. Area Statistics

Where area information is available:

- mean built area (m²)
- median built area (m²)
- mean terrain / lot size (m²)
- median terrain / lot size (m²)

Missing values are excluded from area-based metrics,
but retained in count-based summaries.

---

### 4. Quality & Coverage Indicators

Additional indicators may include:
- percentage of listings with valid price
- percentage with matched GIS neighborhood
- percentage of rejected or excluded listings
- number of unmatched neighborhoods

These metrics document **data completeness and uncertainty**.

---

## Example Aggregated Schema

```text
year
month (optional)
neighborhood_uid
neighborhood_name
transaction_type
property_type
n_listings
price_min_usd
price_max_usd
price_mean_usd
price_median_usd
price_std_usd
area_median_m2
lot_median_m2
```

Exact column names may vary by release,
but structure remains stable.

---

## Publication Outputs

Aggregated datasets are typically published as:

- CSV files (tabular analysis)
- GeoPackage / GeoJSON (spatial analysis)
- summary tables for manuscripts
- figures and maps derived from aggregates

Each release includes:
- data dictionary
- processing description
- version identifier

---

## Relationship to Listing-Level Data

Aggregated datasets are:
- derived **only** from accepted L1clean listings,
- fully reproducible from the pipeline,
- traceable to source years and agencies,
- independent of individual advertisement text.

Raw and listing-level data may be archived separately
under controlled access or supplementary materials.

---

## Methodological Statement

> The published aggregated datasets summarize standardized, validated,
> and spatially referenced housing listings, enabling longitudinal
> and neighborhood-level analysis while preserving transparency
> about data coverage and limitations.

---

## Intended Use

These datasets support:
- SDG‑11 monitoring
- housing affordability analysis
- urban inequality research
- spatial–temporal market studies

They are **not intended** for:
- individual property valuation
- legal or commercial use
- real-time market prediction

---

This aggregated data represents the **final research output**
of the SDG‑11 real-estate data pipeline.
