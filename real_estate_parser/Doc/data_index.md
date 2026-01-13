# Data Index — Synthetic Listings

## Purpose

This repository includes a small set of **synthetic (fantasy) real‑estate listings**
designed to allow users to execute the full SDG‑11 pipeline **end‑to‑end**.

These data:
- mirror the structure and variability of real newspaper advertisements,
- exercise all parsing, cleaning, validation, and aggregation steps,
- do **not** represent real properties, prices, locations, or markets.

Any resemblance to real entities is coincidental.

---

## Data Location

All synthetic input data are stored under:

```
data/raw/
```

### Directory Structure

```
data/raw/
├── Acme/
│   └── 2010/
│       └── acme_20100115.txt
├── Hobitown/
│   └── 2010/
│       └── hobitown_20100115.txt
└── Loontoon/
    └── 2010/
        └── loontoon_20100115.txt
```

Each TXT file represents a **single newspaper issue** for a given agency and date.

---

## Available Synthetic Datasets

| Agency    | Year | Description |
|----------|------|-------------|
| Acme     | 2010 | Mixed house and apartment listings; rent and sale |
| Hobitown | 2010 | Neighborhood alias cases and varied naming |
| Loontoon | 2010 | Edge cases: mixed property types, missing areas |

These datasets are intentionally small but structurally complete.

---

## File Format Expectations

Synthetic TXT files follow the same conventions as real inputs:

- each listing begins with a delimiter (default: `* `)
- neighborhood appears at the beginning of the listing
- free‑text prose includes price, area, and property cues
- multiple lines per listing are allowed

These conventions are documented in:
- `docs/txt_content_conventions.md`

---

## How to Run the Pipeline (Example)

### 1. Parse a synthetic file

```bash
python scripts/parse_acme_listings_v2.py   --file data/raw/Acme/2010/acme_20100115.txt   --output output   --config config/agency_acme.json
```

### 2. Run L1clean and aggregation

Follow the documented steps in:
- `docs/script_execution.md`
- `docs/L1clean_process_summary.md`
- `docs/aggregation_execution_summary.md`

---

## Notes and Limitations

- Synthetic data is minimal by design
- Aggregated results are illustrative only
- Outputs are intended for **method validation**, not analysis

---

## Citation

When using this repository, cite it as:

> SDG‑11 Real‑Estate Data Pipeline — Synthetic Demonstration Data and Methods.
