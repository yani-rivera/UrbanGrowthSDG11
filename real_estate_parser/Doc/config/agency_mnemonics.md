# agency_mnemonics.csv

## Purpose

The `agency_mnemonics.csv` file provides the mapping between agency names and standardized agency mnemonics used throughout the SDG-11 Real Estate Framework.

Its primary function is to support the generation of unique identifiers (UIDs) and preserve source provenance across all processing stages.

---

## Used By

* UID generation (`AddUid.py`)
* Source tracking
* Logging
* Quality-control procedures
* Data provenance

---

## Why It Is Needed

Agency names often appear in multiple formats across datasets, files, and publication periods.

Examples:

```text id="wz4o4v"
Fenix
FENIX
Fénix
Fenix Bienes Raíces
```

Using a standardized mnemonic ensures that all records originating from the same source are assigned a consistent identifier.

---

## Structure

Example:

| Agency    | Mnemonic |
| --------- | -------- |
| Fenix     | FENX     |
| Inverprop | INVP     |
| Makos     | MAKO     |
| Roca      | ROCA     |

---

## UID Generation

The mnemonic forms part of the unique identifier assigned to each record.

Illustrative example:

```text id="9p1f4g"
FENX-20110128-000123
```

Where:

* `FENX` = Agency mnemonic
* `20110128` = Source date
* `000123` = Sequential record number

This structure enables rapid identification of the source and origin of each listing.

---

## Benefits

### Provenance Tracking

Every record can be traced back to its originating agency.

### Consistency

Different spellings or naming conventions are normalized into a single source identifier.

### Reproducibility

UID generation remains deterministic across repeated workflow executions.

### Auditability

Researchers can identify the originating source of a record without consulting the original advertisement.

---

## Maintenance

New agencies should be added to this file before processing begins.

Each agency should be assigned:

* A unique mnemonic
* A stable mnemonic that does not change over time
* A mnemonic that is not reused by another agency

---

## Design Philosophy

The framework treats source provenance as a first-class attribute. Rather than relying on agency names embedded in advertisement text, a standardized mnemonic system is used to generate stable unique identifiers. This approach improves reproducibility, auditing, source tracking, and long-term maintenance of the dataset.
