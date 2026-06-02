# SplitByCue Module (`SplitByCue.py`)

## Purpose

The SplitByCue module converts raw newspaper text into individual candidate real-estate advertisements.

Historical classified advertisements frequently appear as continuous blocks of text without explicit record boundaries. This module uses configurable structural cues to identify where one advertisement ends and another begins.

The resulting output is a normalized text file containing one candidate listing per line, which can then be processed by the downstream parsing framework.

---

# Position Within the SDG-11 Pipeline

```text
Newspaper Page
        ↓
OCR
        ↓
Raw Text File
        ↓
SplitByCue
        ↓
One Listing Per Line
        ↓
Record Parser
        ↓
Structured Dataset
```

---

# Problem Statement

Historical classified advertisements rarely follow a single format.

Examples include:

```text
EL HATILLO, CASA 3 HABITACIONES...
LOMAS DEL GUIJARRO, APARTAMENTO...
```

or

```text
EL HATILLO: CASA DE LUJO...
LOMAS DEL GUIJARRO: APARTAMENTO...
```

or

```text
EL HATILLO. CASA NUEVA...
LOMAS DEL GUIJARRO. APARTAMENTO...
```

The separator used to indicate the start of a listing varies by:

* Agency
* Newspaper
* Year
* Editor

The module therefore implements a configurable cue-based splitting strategy.

---

# Core Concept

A **cue** is a punctuation symbol that commonly appears immediately after the location or heading that starts an advertisement.

Supported cues include:

| Cue | Description |
| --- | ----------- |
| `,` | Comma       |
| `:` | Colon       |
| `;` | Semicolon   |
| `.` | Period      |

Examples:

```text
EL HATILLO, CASA...
```

```text
EL HATILLO: CASA...
```

```text
EL HATILLO; CASA...
```

---

# Configuration-Driven Design

The splitter is controlled entirely through configuration files.

Example:

```json
{
  "listing_marker": "CUE:COLON"
}
```

or

```json
{
  "listing_marker": "CUE:COMMA"
}
```

The parser automatically translates these symbolic definitions into their corresponding punctuation characters.

---

# Supported Cue Types

## Comma Agencies

Example:

```text
EL HATILLO, CASA 3 HAB...
```

A listing start is recognized when:

* A comma appears early in the line
* The comma is not part of a number
* Alphabetic content exists before the comma
* A price-like value appears shortly afterward

---

## Colon Agencies

Example:

```text
EL HATILLO: CASA 3 HAB...
```

A colon near the beginning of the line is treated as a strong listing-start indicator.

---

## Semicolon Agencies

Example:

```text
EL HATILLO; CASA 3 HAB...
```

Semicolons are treated similarly to colons.

---

## Period Agencies

Example:

```text
EL HATILLO. CASA NUEVA...
```

Period-based splitting is supported but uses additional safeguards to avoid conflicts with:

* Decimal numbers
* Currency values
* Common abbreviations

---

# Header Preservation

Many newspaper pages contain section headers.

Example:

```text
# APARTAMENTOS EN ALQUILER
```

These headers provide contextual information for subsequent listings.

The splitter preserves headers as independent records rather than merging them into advertisements.

Example output:

```text
# APARTAMENTOS EN ALQUILER
EL HATILLO, APARTAMENTO...
LOMAS DEL GUIJARRO, APARTAMENTO...
```

---

# Numeric Protection

One of the most important safeguards prevents splitting inside numeric values.

Example:

```text
$1,500
```

The comma in:

```text
1,500
```

is not treated as a listing boundary.

Similarly:

```text
$250,000
```

remains intact.

This protection dramatically reduces false-positive record splits.

---

# Continuation-Line Detection

Advertisements frequently span multiple OCR lines.

Example:

```text
EL HATILLO, CASA DE LUJO,
3 HABITACIONES,
2 BAÑOS,
PATIO
```

The splitter detects that the first line ends with a continuation marker and automatically joins subsequent lines.

Result:

```text
EL HATILLO, CASA DE LUJO, 3 HABITACIONES, 2 BAÑOS, PATIO
```

---

# Price-Led Continuations

Some OCR layouts place prices on separate lines.

Example:

```text
EL HATILLO, CASA DE LUJO
$250,000
```

Lines beginning with price-like values are treated as continuations rather than new records.

This prevents fragmentation of advertisements.

---

# Forbidden Start Words

Certain words frequently appear at the beginning of a line but should not be interpreted as the start of a new advertisement.

Examples include:

```text
RES.
COND.
TORRE
EDIF.
COL.
URB.
```

These tokens are maintained in a configurable exclusion list.

Example:

```json
{
  "not_start_words": [
    "RES",
    "COND",
    "TORRE"
  ]
}
```

This mechanism significantly reduces false-positive splits.

---

# Inline Multi-Record Detection

Some OCR outputs contain multiple advertisements on the same line.

Example:

```text
EL HATILLO: CASA $250,000 LOMAS DEL GUIJARRO: APARTAMENTO $180,000
```

The splitter can identify these situations and divide them into separate candidate records.

This capability is particularly useful when OCR software merges newspaper columns.

---

# Staging Window Architecture

The module uses a temporary staging buffer before committing records.

Advantages include:

* Better handling of continuation lines
* Reduced false-positive boundaries
* Improved reconstruction of fragmented OCR text

Rather than immediately creating a record when a cue is detected, the splitter evaluates nearby context before finalizing the decision.

---

# Output

Input:

```text
# CASAS EN VENTA

EL HATILLO, CASA 3 HAB
$250,000

LOMAS DEL GUIJARRO, CASA 4 HAB
$350,000
```

Output:

```text
# CASAS EN VENTA

EL HATILLO, CASA 3 HAB $250,000

LOMAS DEL GUIJARRO, CASA 4 HAB $350,000
```

One advertisement per line.

---

# UTF-8 and OCR Compatibility

The splitter uses UTF-8-SIG input handling to support:

* Historical OCR exports
* Windows-generated text files
* UTF-8 with BOM
* Cross-platform processing

This improves interoperability and reduces encoding-related failures.

---

# Role Within the SDG-11 Framework

The SplitByCue module is the first advertisement-level segmentation stage of the SDG-11 real-estate reconstruction workflow.

Its purpose is not to extract information but to reconstruct candidate listing boundaries from noisy OCR text.

The module transforms unstructured newspaper pages into advertisement-level records suitable for:

* Price extraction
* Area extraction
* Property classification
* Neighborhood identification
* Dataset construction

Without this segmentation stage, downstream parsing would operate on entire newspaper pages, substantially reducing extraction accuracy and reproducibility.

The configuration-driven cue architecture allows the same framework to be applied across agencies, publication years, and newspaper formats without modifying source code.
