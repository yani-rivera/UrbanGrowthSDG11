## Parsed Output CSV Schema (Pipeline v1.0)

This document describes the **actual output table produced by the parser**
for a single TXT input file.

Each row represents **one real-estate listing** extracted from newspaper text.

---

## Identification & Traceability

| Column | Description |
|------|------------|
| `Listing ID` | Sequential identifier within the parsed dataset |
| `source_type` | Origin of the raw text (e.g. `ocr_manual`) |
| `ingestion_id` | Identifier of the raw input file |
| `pipeline_version` | Version of the parsing pipeline used |

---

## Core Listing Fields

| Column | Description |
|------|------------|
| `title` | Short inferred title or label |
| `neighborhood` | Resolved neighborhood name (after catalog matching) |
| `notes` | Full original listing text (preserved verbatim) |

> The `notes` field is the **ground truth reference** for all extracted values.

---

## Property Characteristics

| Column | Description |
|------|------------|
| `bedrooms` | Number of bedrooms extracted |
| `bathrooms` | Number of bathrooms extracted |
| `property_type` | Standardized property type (e.g. `House`, `Apartment`) |

---

## Area Information

| Column | Description |
|------|------------|
| `AT` | Area type indicator (if present) |
| `AT_unit` | Unit associated with `AT` |
| `area` | Numeric area value |
| `area_unit` | Area unit as detected (e.g. `m²`) |
| `area_m2` | Area converted to square meters |

Area-related fields may be partially empty depending on listing content.

---

## Price & Transaction

| Column | Description |
|------|------------|
| `price` | Numeric price value |
| `currency` | Detected currency (e.g. `USD`, `HNL`) |
| `transaction` | Standardized transaction type (`Rent`, `Sale`) |

---

## Provenance Metadata

| Column | Description |
|------|------------|
| `agency` | Agency name (must match script and config) |
| `date` | Date inferred from filename or context |

---

## Design Principles

- One row represents one listing
- Original text is always preserved (`notes`)
- Missing values are allowed and expected
- Normalized values do not overwrite raw meaning
- Output is flat, tabular, and analysis-ready

---

## Intended Use

This table is designed for:
- descriptive statistics
- temporal analysis
- spatial joining (via neighborhood catalogs)
- quality control and flagging

It is **not** intended to perfectly reconstruct every detail of the original advertisement.

---

> Interpretation is recorded in columns, not by deleting data.
