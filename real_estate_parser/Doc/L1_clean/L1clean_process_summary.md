# SDG‑11 Real‑Estate Pipeline — L1clean Process Summary

This document provides a **high‑level summary** of the full workflow used to transform
raw newspaper real‑estate listings into **unified, analysis‑ready datasets** for SDG‑11.

It complements the step‑by‑step execution documents and is intended as a **conceptual overview**
for readers, reviewers, and new users.

---

## Scope of This Summary

This summary covers the process from:

**Parsed CSV outputs → Unified yearly / monthly datasets (L1clean)**

It does **not** cover:
- web scraping
- GIS analysis
- statistical modeling
- SDG‑11 indicator computation

---

## Design Principles

The workflow is built around the following principles:

- **Reproducibility** — same inputs + configs = same outputs  
- **Transparency** — no silent deletions or overwrites  
- **Traceability** — every record can be traced back to source text  
- **Determinism** — rule‑based, not heuristic guessing  
- **Auditability** — rejected and ambiguous data are preserved  

> Cleaning is treated as classification and documentation, not censorship.

---

## High‑Level Workflow

### 1. Parsing (Upstream)

- Newspaper listings are transcribed into TXT files
- Agency‑specific parsers extract structured fields
- Output: one CSV per source file

⬇

### 2. Merge (L1clean)

- Parsed CSVs are merged by **year** or **year–month**
- This is pure concatenation
- No filtering or deduplication yet

⬇

### 3. Deduplication

- Repeated or syndicated listings are identified
- Canonical listings and duplicates are written to separate files
- No data is deleted

⬇

### 4. Text Normalization

- Non‑informative words are removed from selected columns
- Neighborhood names are cleaned and normalized
- Original values are preserved

⬇

### 5. UID Assignment

- Each listing receives a stable, deterministic UID
- UIDs are based on agency mnemonics and dates
- Ensures cross‑year and cross‑agency traceability

⬇

### 6. Property Type Validation

- Mixed or ambiguous property types are scored
- A validated property type is selected
- Diagnostic scores are written for transparency

⬇

### 7. Scope Filtering

- Listings outside the research scope are rejected explicitly
- Filters include:
  - excluded property types
  - excluded neighborhoods
  - missing or invalid prices
- Accepted and rejected datasets are written separately

⬇

### 8. Catalog Matching & GIS Enrichment

- Cleaned neighborhoods are matched to a standard catalog
- GIS identifiers are added where matches exist
- Valid alias cases may duplicate rows to preserve semantics
- Unmatched listings are preserved

⬇

### 9. Price Standardization

- Prices are converted to a common currency (USD)
- External, versioned FX tables are used
- Original price and currency are retained

⬇

### 10. Transaction Validation

- Sale vs Rent is validated using standardized prices
- Implausible combinations are corrected or flagged
- No rows are dropped

⬇

### 11. Terrain / Lot Area Standardization

- Only terrain (lot) area values are converted to m²
- Built area values are left unchanged
- Original units are preserved

---

## Final Output

At the end of the L1clean pipeline, the process produces:

- **One unified dataset per year or per year–month**
- Fully standardized, validated, and traceable listings
- Spatially referencable records (when catalog matched)

Example:

```text
consolidated/2010/merged_2010_STDPrice_AreaM2.csv
```

These files constitute the **canonical analytical inputs**
for SDG‑11 housing and urban analysis.

---

## What Happens After L1clean

Subsequent stages (outside this document) may include:

- quality control summaries
- outlier detection
- neighborhood‑level aggregation
- spatial analysis and mapping
- indicator computation

---

## Methodological Statement

> The L1clean pipeline transforms heterogeneous historical advertisements into
> standardized, comparable, and auditable urban data while preserving original
> textual evidence and uncertainty.

This balance enables robust urban analysis in data‑scarce contexts.
