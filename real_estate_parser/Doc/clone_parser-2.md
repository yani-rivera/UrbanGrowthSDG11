## Cloning the Parser Script

This document explains how to **clone and reuse the parser script**
for new agencies by copying and renaming the file, with **one explicit in-script change**.

---

## Core Rule (Very Important)

> **Cloning the parser means copying the script, renaming it, and updating a single variable.**

No other internal code changes are required.

---

## Required In-Script Change

Inside the cloned script, **only one line must be updated**:

```python
agency = "<AGENCY_NAME>"
```

Where `<AGENCY_NAME>` **must exactly match** the agency name defined in the
corresponding configuration file (`agency_<name>.json`).

### Example

For Hobitown:

```python
agency = "Hobitown"
```

This value is used to:
- select the correct raw data directory
- associate outputs with the correct agency
- ensure consistency with configuration and catalogs

⚠ **Case and spelling must match the config exactly.**

---

## Naming Convention

Parser scripts must follow this pattern:

```text
parse_<agency>_listings_v2.py
```

Where:
- `<agency>` is lowercase (file name)
- the internal `agency = "..."` value matches the config (human-readable)

### Examples

```text
parse_acme_listings_v2.py      → agency = "Acme"
parse_hobitown_listings_v2.py  → agency = "Hobitown"
parse_loontoon_listings_v2.py  → agency = "Loontoon"
```

---

## What Changes and What Does Not

### Changes when cloning
- Script filename
- Internal `agency` variable
- Agency config file used at runtime
- Raw input directory

### Does NOT change
- Parsing logic
- Regex rules
- Extraction strategies
- Catalog matching behavior

---

## Why This Single Change Exists

- Makes each script self-describing
- Prevents accidental cross-agency execution
- Simplifies debugging and logging
- Keeps runtime behavior explicit

> The script name gives context.  
> The `agency` variable binds execution.

---

## Running a Cloned Script

Example:

```bash
python scripts/parse_hobitown_listings_v2.py   --config config/agency_hobitown.json   --year 2010
```

---

## Versioning Rule

Increment the script version (`_v3`, `_v4`, etc.) **only if**:
- the parsing model changes
- outputs are no longer comparable

Otherwise, reuse the same version number.

---

## Design Principle

> One parser logic, many scripts, one explicit agency binding  
> → clarity, safety, reproducibility

---

This approach ensures transparent and auditable parsing across agencies.
