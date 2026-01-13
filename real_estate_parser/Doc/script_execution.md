## Script Execution Guide

This document describes **how to execute the parser script**
to transform raw TXT listings into structured CSV output.

The instructions apply to all cloned parser scripts following the pattern:
`parse_<agency>_listings_v2.py`.

---

## Preconditions

Before running the script, ensure that:

- Python is installed and available in your environment
- Required packages are installed (`pandas`, etc.)
- Raw data follows the directory and naming conventions
- An agency-specific configuration file exists
- The parser script has been cloned and renamed correctly
- The internal `agency` variable matches the config file

---

## Basic Execution (Single File)

To parse a **single raw TXT file**, run:

```bash
python scripts/parse_<agency>_listings_v2.py   --file "data/raw/<Agency>/<Year>/<agency>_<date>.txt"   --output "output"   --config "config/agency_<agency>.json"
```

### Example (ACME)

```bash
python scripts/parse_acme_listings_v2.py   --file "data/raw/Acme/2010/acme_20100115.txt"   --output "output"   --config "config/agency_acme.json"
```

This mode is recommended for:
- first runs
- debugging
- documentation examples

---

## Batch Execution (Directory-Based)

If the script supports directory discovery, it can be run without `--file`:

```bash
python scripts/parse_<agency>_listings_v2.py   --config "config/agency_<agency>.json"   --output "output"
```

The script will automatically process all eligible files under:

```text
data/raw/<Agency>/
```

Optionally, a year filter may be provided:

```bash
python scripts/parse_<agency>_listings_v2.py   --config "config/agency_<agency>.json"   --output "output"   --year 2010
```

---

## Command-Line Arguments

| Argument | Description |
|--------|------------|
| `--file` | Path to a single raw TXT file |
| `--output` | Base output directory |
| `--config` | Path to agency configuration file |
| `--year` | Optional year filter |

Arguments not provided fall back to script defaults.

---

## What Happens During Execution

When executed, the script:

1. Binds execution to the agency via the internal `agency` variable
2. Loads the agency-specific configuration
3. Reads raw TXT input(s)
4. Normalizes listing delimiters
5. Extracts structured fields
6. Applies catalogs and standardization rules
7. Writes output CSV files
8. Emits warnings and QC signals if applicable

Raw input files are **never modified**.

---

## Output Location

Outputs are written under the specified base directory:

```text
output/<Agency>/<Year>/
```

Typical outputs include:
- parsed listings CSV
- QC or flag tables (if enabled)

---

## Execution Notes

- Warnings are expected and informative
- Missing values do not stop execution
- If results look incorrect, adjust configuration files — not the script

---

## Methodological Note

> Script execution is deterministic given the same inputs, configuration files,
> and parser version.

This guarantees reproducibility across runs and agencies.
