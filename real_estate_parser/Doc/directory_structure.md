## Directory Structure

This project follows a clear, provenance-first directory structure designed for
long-term reproducibility, archival integrity, and transparent data processing.

The structure separates **raw sources**, **intermediate cleaning**, **final outputs**,
**configuration**, and **quality control**.

---

## Top-level Layout

```text
Catalog/
config/
data/
Doc/
FXrate/
L1clean/
modules/
output/
qc_reports/
scripts/
tools/
```

---

## Directory Descriptions

### `Catalog/`

Reference catalogs used for validation and harmonization, such as:

- controlled vocabularies
- lookup tables
- canonical identifiers

This directory is read-only during processing.

---

### `config/`

Configuration files that control parsing and standardization logic.

Typical contents include:
- agency definitions
- neighborhood mappings
- property types
- transaction labels
- unit conversion rules

**No parsing logic is hard-coded in scripts**; all rules live here.

---

### `data/`

Primary data storage.

#### `data/raw/`

Immutable source data, organized by **agency → year**.

```text
data/raw/
  Acme/
    2010/
      acme_20100115.txt
  Hobitown/
  Loontoon/
```

Rules:
- Files in `data/raw/` are never edited.
- These files represent the archival record.

---

### `Doc/`

Human-readable documentation, notes, and supporting material.

This may include:
- methodological notes
- screenshots
- provenance descriptions
- contextual explanations

---

### `FXrate/`

Exchange-rate data used for currency normalization.

Separated from listings to:
- preserve temporal context
- avoid coupling with parsing logic
- allow independent verification

---

### `L1clean/`

Level-1 cleaned text.

This directory contains:
- OCR outputs after manual or automated cleanup
- line-normalized text
- human-readable but **not yet parsed** listings

No interpretation or field extraction occurs at this stage.

---

### `modules/`

Reusable Python modules.

This directory contains:
- parsing helpers
- text normalization utilities
- validation functions

Modules are imported by scripts but are not run directly.

---

### `output/`

Processed outputs derived from raw data.

```text
output/
  Acme/
    2010/
```

Rules:
- Outputs may be deleted and regenerated.
- Directory structure mirrors `data/raw/` for traceability.

---

### `qc_reports/`

Quality-control outputs.

This directory contains:
- acceptance vs rejection summaries
- anomaly reports
- validation statistics

QC outputs are analytical artifacts, not source data.

---

### `scripts/`

Runnable scripts and pipeline entry points.

Typical scripts include:
- text parsing
- tabulation
- validation
- report generation

Scripts orchestrate work but contain minimal logic.

---

### `tools/`

Auxiliary and one-off utilities.

Used for:
- migration tasks
- experiments
- diagnostics
- data inspection

Tools are not part of the core pipeline.

---

## Design Principles

- Raw data is immutable
- Processing is reproducible
- Logic is configuration-driven
- Dependencies are minimal
- Every stage is inspectable

---

This structure supports historical reconstruction, iterative refinement,
and transparent publication workflows.
