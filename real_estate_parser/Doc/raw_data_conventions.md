## Raw Data Directory Structure and Naming Conventions

All raw real-estate listings must follow a **strict directory structure and file-naming convention**
to ensure traceability, reproducibility, and automated processing.

This structure applies to the `real_estate_parser` project.

---

## Root Location

```text
real_estate_parser/
└── data/
    └── raw/
```

All raw inputs live under `data/raw/`.

---

## Directory Hierarchy

```text
data/raw/
└── <AGENCY>/
    └── <YEAR>/
        └── <agency>_<date>.txt
```

### Levels Explained

#### 1. Agency directory

- One directory per data source (agency, newspaper, or platform)
- Directory name is **case-sensitive**
- Must match the canonical agency name

Examples:
```text
data/raw/Acme/
data/raw/Hobitown/
data/raw/Loontoon/
```

> ⚠ Keep an eye on case sensitivity: `Acme` and `acme` are treated as different directories.

---

#### 2. Year directory

- Four-digit year
- Represents the publication year of the listings

Example:
```text
data/raw/Acme/2010/
data/raw/Acme/2026/
```

---

#### 3. File naming convention

Each file represents **one newspaper issue or one listing batch**.

```text
<agency>_<date>.txt
```

Where:

- `agency` is **lowercase**
- `<date>` follows one of the accepted patterns below
- File extension is `.txt`
- No spaces allowed

##### Accepted date patterns

| Pattern | Meaning | Example |
|-------|--------|--------|
| `yyyy` | Year-level batch | `acme_2010.txt` |
| `yyyymm` | Month-level batch | `acme_201001.txt` |
| `yyyymmdd` | Day-level issue | `acme_20100115.txt` |

All three formats are valid, as long as the pattern is applied consistently.

---

## What Goes Into These Files

- Plain UTF-8 encoded text
- One batch or issue per file
- Listings may be noisy, unstructured, or partially cleaned

No parsing or interpretation occurs at this stage.

---

## Immutability Rule

> Files under `data/raw/` are **never edited** once created.

If corrections are needed:
- create a new file
- document the change
- preserve the original

---

## Design Rationale

This structure:
- encodes provenance directly in the path
- supports different temporal resolutions (year, month, day)
- allows batch processing by agency and year
- prevents accidental overwrites
- supports long-term archival use

Scripts rely on this structure for automated discovery of input files.

---

Following these conventions is mandatory for the parser to operate correctly.
