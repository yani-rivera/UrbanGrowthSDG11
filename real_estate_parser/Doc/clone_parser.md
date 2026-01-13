## Cloning the Parser Script

This document explains how to **clone and reuse the parser script**
for new agencies **by copying and renaming the file**, without changing
the internal parsing logic.

---

## Core Rule (Very Important)

> **Cloning the parser means copying the script and updating its filename only.**

No internal code changes are required for normal use.

---

## How Cloning Works in Practice

To add a new agency parser:

1. **Copy the existing parser script**
2. **Rename it following the convention below**
3. Use a different agency configuration file at runtime

---

## Naming Convention

Parser scripts must follow this pattern:

```text
parse_<agency>_listings_v2.py
```

Where:
- `<agency>` is lowercase
- the suffix `_v2` reflects the parser version

### Examples

```text
parse_acme_listings_v2.py
parse_hobitown_listings_v2.py
parse_loontoon_listings_v2.py
```

The filename documents **which agency configuration the script is expected to use**,
but the internal logic remains generic.

---

## What Changes and What Does Not

### Changes when cloning
- Script filename
- Agency config file passed at runtime
- Raw input directory used

### Does NOT change
- Parsing logic
- Regex rules
- Extraction strategies
- Catalog matching behavior

---

## Why This Is Done

- Keeps agency workflows isolated
- Allows parallel development and debugging
- Preserves reproducibility of historical runs
- Makes command history and logs self-describing

> The script name provides context.  
> The behavior comes from configuration.

---

## Running a Cloned Script

Example:

```bash
python scripts/parse_hobitown_listings_v2.py   --agency Hobitown   --year 2010   --config config/agency_hobitown.json
```

---

## When to Create a New Version

Increment the script version (`_v3`, `_v4`, etc.) **only if**:
- the parsing model changes
- backward compatibility breaks
- outputs are not comparable

Otherwise, reuse the same version number.

---

## Design Principle

> One parser logic, many scripts, many configurations  
> → clarity without code divergence

---

This approach ensures transparent, repeatable, and auditable parsing across agencies.
