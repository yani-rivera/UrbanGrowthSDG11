# Force Bullet Module (`forcebulletv4.py`)

## Purpose

The Force Bullet module is a lightweight preprocessing utility designed to reconstruct and normalize bullet-based real-estate listings from OCR-derived text.

Many historical classified advertisements use bullet markers (`*`) to separate listings. During OCR extraction, spacing and formatting around these markers are often lost or corrupted, making downstream parsing difficult.

This module restores a consistent bullet structure and ensures that each listing appears on its own line.

---

# Position Within the SDG-11 Pipeline

```text
OCR Output
      ↓
Force Bullet
      ↓
One Bullet Per Listing
      ↓
SplitByCue
      ↓
Record Parser
      ↓
Structured Dataset
```

Depending on the agency format, this module may be executed before the main splitting stage.

---

# Problem Statement

OCR frequently transforms newspaper bullet lists into continuous text.

Example OCR output:

```text
* EL HATILLO CASA 3 HAB $250,000 * LOMAS DEL GUIJARRO CASA 4 HAB $350,000
```

While humans can easily identify two listings, automated parsers may struggle when bullet spacing is inconsistent.

The Force Bullet module reconstructs these boundaries.

---

# Core Function

## `bulletize()`

The module processes a collection of text lines and returns a normalized list of bullet-based records.

### Input

```text
* EL HATILLO CASA 3 HAB $250,000 * LOMAS DEL GUIJARRO CASA 4 HAB $350,000
```

### Output

```text
* EL HATILLO CASA 3 HAB $250,000
* LOMAS DEL GUIJARRO CASA 4 HAB $350,000
```

---

# Processing Workflow

```text
Raw OCR Text
      ↓
Whitespace Normalization
      ↓
Bullet Detection
      ↓
Listing Separation
      ↓
Price Detection
      ↓
Area Detection
      ↓
Record Reconstruction
      ↓
Normalized Bullet Records
```

---

# Whitespace Normalization

The module first standardizes spacing around bullet markers.

Example:

```text
*EL HATILLO
```

becomes:

```text
* EL HATILLO
```

Similarly:

```text
*   EL HATILLO
```

becomes:

```text
* EL HATILLO
```

This step reduces OCR-induced formatting variability.

---

# Bullet-Based Segmentation

The asterisk character is treated as a record boundary.

Example:

```text
* CASA 1 * CASA 2 * CASA 3
```

becomes:

```text
CASA 1
CASA 2
CASA 3
```

during internal processing.

Empty segments are discarded.

---

# Price Detection

The module identifies monetary values near the end of a listing.

Supported examples include:

```text
$250,000
```

```text
Lps. 3,500,000
```

The final detected price is preserved during reconstruction.

---

# Area Detection

The module also identifies common area measurements.

Examples:

```text
800 V2
```

```text
250 M2
```

The final detected area measurement is preserved.

---

# Listing Reconstruction

After identifying areas and prices, the module reconstructs a standardized listing.

Example input:

```text
EL HATILLO CASA 3 HAB 800 V2 $250,000
```

Output:

```text
* EL HATILLO CASA 3 HAB 800 V2 $250,000
```

The reconstructed listing always begins with a bullet marker.

---

# Area and Price Ordering

During reconstruction:

1. Listing description is preserved.
2. Area information is appended.
3. Price information is appended last.

Result:

```text
* CASA EN EL HATILLO 800 V2 $250,000
```

This creates a consistent structure across records.

---

# Supported Area Formats

The module currently recognizes:

```text
V2
```

```text
M2
```

Examples:

```text
500 V2
```

```text
250 M2
```

These values are preserved and moved to the standardized output structure.

---

# Supported Price Formats

Examples include:

```text
$250,000
```

```text
Lps. 1,200,000
```

```text
Lps 500,000
```

The final detected monetary expression is treated as the listing price.

---

# Typical Use Cases

The module is particularly useful when:

* OCR merges multiple bullet listings into a single paragraph
* Newspaper exports lose line breaks
* Historical archives contain inconsistent spacing
* Bullet markers survive OCR but record boundaries do not

---

# Example

## Input

```text
* EL HATILLO CASA 3 HAB 800 V2 $250,000
* LOMAS DEL GUIJARRO CASA 4 HAB 1200 V2 $350,000
```

## Output

```text
* EL HATILLO CASA 3 HAB 800 V2 $250,000
* LOMAS DEL GUIJARRO CASA 4 HAB 1200 V2 $350,000
```

Each listing becomes an independent, consistently formatted record.

---

# Command-Line Usage

The script supports standard input and output streams.

Example:

```bash
cat input.txt | python forcebulletv4.py > output.txt
```

This design allows easy integration into larger processing pipelines.

---

# Role Within the SDG-11 Framework

The Force Bullet module is a preprocessing utility used to restore structural consistency in OCR-derived classified advertisements.

Unlike the main parsing modules, it does not extract attributes such as bedrooms, bathrooms, or neighborhoods. Instead, it focuses on reconstructing listing boundaries and preserving key trailing attributes (areas and prices) in a consistent format.

By normalizing bullet-based advertisements before deeper parsing, the module improves the reliability of downstream extraction routines and reduces errors caused by OCR formatting inconsistencies.
