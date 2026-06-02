# Word Filter Module (`word_filter.py`)

## Purpose

The Word Filter module removes predefined words and phrases from a selected dataset column using an external configuration file.

The module is designed to support data standardization workflows where recurring non-informative terms, descriptors, or agency-specific artifacts must be removed before matching, aggregation, or analysis.

Rather than hard-coding cleanup rules, all removable terms are maintained in an external text file, allowing the cleaning behavior to evolve without modifying source code.

---

# Position Within the SDG-11 Pipeline

```text
Raw Extracted Values
        ↓
Neighborhood Cleaning
        ↓
Word Filter
        ↓
Standardized Text
        ↓
Matching
        ↓
Aggregation
```

The module can be applied to any text field, although it is most commonly used for neighborhood standardization.

---

# Design Philosophy

The module follows three principles:

## 1. Configuration-Driven Cleaning

Words and phrases are stored externally.

Example:

```text
config/remove_words.txt
```

This allows:

* New terms to be added easily
* Agency-specific cleanup
* Historical format adaptation
* Reproducible preprocessing

without changing the source code.

---

## 2. Preserve Dataset Structure

Only the specified column is modified.

All other columns remain unchanged.

Example:

Input:

| neighborhood_clean | price  |
| ------------------ | ------ |
| COL. EL HATILLO    | 250000 |

Output:

| neighborhood_clean | price  |
| ------------------ | ------ |
| EL HATILLO         | 250000 |

---

## 3. Phrase-Aware Matching

The module supports both:

* Single words
* Multi-word phrases

This is important because neighborhood descriptions often contain repeated phrases rather than isolated terms.

---

# Input Components

The module requires:

| Parameter   | Description      |
| ----------- | ---------------- |
| Input CSV   | Dataset to clean |
| Column Name | Target column    |
| Words File  | Terms to remove  |

---

## Example

Input CSV:

```csv
neighborhood_clean
COL. EL HATILLO
RES. LOS OLIVOS
```

Words file:

```text
COL.
RES.
```

Output:

```csv
neighborhood_clean
EL HATILLO
LOS OLIVOS
```

---

# Word Dictionary

The words file contains one word or phrase per line.

Example:

```text
COL.
COLONIA
RES.
RESIDENCIAL
URB.
URBANIZACION
```

Each entry is treated as a removable token.

---

# Phrase Matching

The module supports multi-word phrases.

Example dictionary:

```text
LOS OLIVOS
VILLA OLIMPICA
```

Input:

```text
RES. LOS OLIVOS
```

Output:

```text
RES.
```

after phrase removal.

---

# Longest-Match Strategy

Entries are automatically sorted by length before matching.

Example dictionary:

```text
OLIVOS
LOS OLIVOS
```

The longer phrase:

```text
LOS OLIVOS
```

is evaluated first.

This prevents partial removal errors.

---

# Flexible Separator Handling

The module tolerates punctuation and spacing variations.

Examples:

Dictionary entry:

```text
LOS OLIVOS
```

Matches:

```text
LOS OLIVOS
```

```text
LOS, OLIVOS
```

```text
LOS. OLIVOS
```

```text
LOS    OLIVOS
```

This improves robustness when processing OCR-derived text.

---

# Case-Insensitive Matching

Matching ignores capitalization.

Example:

Dictionary:

```text
colonia
```

Matches:

```text
COLONIA
```

```text
Colonia
```

```text
colonia
```

---

# Post-Cleanup Normalization

After word removal the module:

1. Removes redundant whitespace
2. Collapses repeated spaces
3. Trims leading/trailing spaces

Example:

```text
COL.   EL   HATILLO
```

becomes:

```text
EL HATILLO
```

---

# Change Tracking

The module reports:

```text
Rows total
Rows modified
```

Example:

```text
Rows total    : 500
Rows modified : 127
```

This provides a simple audit trail for preprocessing.

---

# In-Place Processing

The module can overwrite the source file.

Example:

```bash
--inplace
```

This option is useful when the cleaning stage becomes part of an automated workflow.

---

# Output File Processing

Alternatively, the cleaned dataset can be written to a new file.

Example:

```bash
python word_filter.py \
    --input listings.csv \
    --output listings.cleaned.csv \
    --col neighborhood_clean \
    --words-file config/remove_words.txt
```

This approach preserves the original dataset.

---

# Example Workflow

Input:

```csv
neighborhood_clean
COL. EL HATILLO
RES. LOS OLIVOS
URB. PALMIRA
```

Dictionary:

```text
COL.
RES.
URB.
```

Output:

```csv
neighborhood_clean
EL HATILLO
LOS OLIVOS
PALMIRA
```

---

# Typical SDG-11 Applications

The module is commonly used to remove:

* COL.
* COLONIA
* RES.
* RESIDENCIAL
* URB.
* URBANIZACION
* Agency-specific labels
* OCR artifacts
* Administrative descriptors

before neighborhood matching.

---

# Relationship to Neighborhood Cleaning

The Word Filter module complements rather than replaces the Neighborhood Cleaning module.

### Neighborhood Cleaning

Handles:

* Encoding repair
* Punctuation cleanup
* Description removal
* Case normalization

### Word Filter

Handles:

* Controlled vocabulary removal
* Phrase elimination
* Domain-specific cleanup

Together they form a two-stage neighborhood standardization workflow.

---

# Role Within the SDG-11 Framework

The Word Filter module provides a configurable vocabulary-cleaning layer for the SDG-11 real-estate reconstruction framework.

Its primary purpose is to remove known non-informative terms from text fields while preserving the overall dataset structure.

By externalizing removable terms into configuration files, the framework remains adaptable to:

* New agencies
* Historical newspaper formats
* OCR artifacts
* Alternative languages
* Future geographic contexts

Clean_neighborhoods.py removes structural noise, while word_filter.py removes semantic noise through a controlled vocabulary. That distinction makes the workflow much easier for readers to understand.

This configuration-driven approach supports reproducibility, transparency, and long-term maintainability of the SDG-11 data pipeline.
