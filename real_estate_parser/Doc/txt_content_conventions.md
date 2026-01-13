## TXT File Content Conventions

This document defines **how raw TXT files should be structured internally**
so that the parser can reliably extract listings and identify neighborhoods.

These rules apply to all files under `data/raw/`.

---

## 1. Listing Delimiter

Each listing **must start with a clear delimiter**.

### Preferred delimiter

```
* 
```

Example:
```text
* Centro de OZ: apartamento 2 hab 1 baño, 65 m2, agua 24 hrs
```

### Alternative delimiters

Other characters may appear in source text (e.g. `•`, `-`, `>`), but:

- they **must be normalized** to `* ` before parsing, or
- their replacement must be explicitly configured

> The parser **only looks for `* `** as the definitive listing boundary.

---

## 2. Listing Start Rule

After the `* ` delimiter:

1. The **first textual element must describe the neighborhood**
2. This is followed by a **neighborhood delimiter**
3. The rest of the line contains free descriptive text

General form:

```text
* <NEIGHBORHOOD><DELIMITER> <free text>
```

---

## 3. Parsing Window (Important)

By default, **only the first 60 characters** of each listing are examined
to extract the neighborhood name.

**Why this rule exists**
- Neighborhood names appear at the beginning of listings
- Limits false matches in long descriptive text
- Improves performance and determinism

**Configuration**
- The 60-character limit is the default
- A different limit may be specified via configuration parameters
- The rest of the listing remains untouched

> This rule constrains *where* the parser looks, not *what* it extracts.

---

## 4. Neighborhood Delimiters

The following delimiters are supported to separate the neighborhood name
from the rest of the listing:

### Recommended delimiters
- `:` (colon)
- `,` (comma)
- `;` (semicolon)

### Not recommended
- `.` (dot)

Dots may be used only when no other delimiter is present and must be handled
explicitly by the parser.

---

## 5. Neighborhood Extraction Strategies

Because newspaper text is inconsistent, multiple **extraction strategies**
are supported. Only **one strategy is applied per pass**, based on configuration.

The parser always operates on text **after removing the leading `* `**
and **within the configured parsing window**.

---

### Strategy: `uppercase`

Extracts consecutive **uppercase tokens** from the beginning of the text.

---

### Strategy: `first_comma`

Extracts everything before the first comma.

---

### Strategy: `first_line`

Uses the **first line** of a multi-line listing.

---

### Strategy: `before_colon`

Extracts text before the first colon.

---

### Strategy: `before_dot`

Extracts text before the first dot (`.`), only if the dot appears after
at least four characters.

---

### Strategy: `before_colon_dot`

Extracts text before the first colon or dot (`:` or `.`).

---

### Strategy: `before_semicolon_colon_comma`

Splits on the first occurrence of `: ; ,`.

---

### Strategy: `before_comma_or_colon`

Splits on the first comma or colon.

---

### Strategy: `beforecommacolondollar`

Splits on the first comma, colon, or dollar sign.

---

### Strategy: `before_currency`

Splits text at the first detected currency expression.

---

### Strategy: `before_brack`

Splits on colon or opening parenthesis.

---

### Strategy: `before_semicolon`

Splits on the first semicolon.

---

### Strategy: `before_comma_or_dot`

Splits on the first comma or dot, subject to a minimum character length.

---

## 6. General Rules

- Neighborhood extraction happens **before** catalog matching
- Only the configured leading characters are scanned
- Extracted text is normalized afterward
- Original raw text is always preserved
- Failed extraction results in **flagging**, not guessing

---

## Design Principle

> The parser constrains its search space deliberately  
> to avoid accidental matches and preserve reproducibility.

---

These conventions ensure that raw TXT files remain flexible while still
supporting deterministic and reproducible parsing.
