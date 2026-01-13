## Agency Configuration: ACME

This document describes the configuration file used to parse and standardize
real-estate listings originating from the **ACME** agency.

The configuration is stored as a JSON file and controls **agency-specific parsing behavior**.
All values are explicit and override generic defaults where needed.

---

## File Overview

**Filename:** `agency_acme.json`  
**Agency name:** Acme  
**Mnemonic:** ACM

This configuration is read-only during execution.

---

## General Settings

| Field | Description |
|------|------------|
| `agency` | Human-readable agency name |
| `nemonic` | Short stable mnemonic used in IDs and paths |
| `preprocessing_needed` | Whether preprocessing steps must be applied |
| `preprocess` | Ordered preprocessing steps to apply |
| `sanitize` | Enables text sanitization |
| `emit_marker` | Whether to emit explicit markers in output |
| `max_cue_pos` | Maximum character position for parsing cues |
| `require_upper` | Requires uppercase tokens for some strategies |
| `require_price_before` | Whether price must appear before other cues |

---

## Listing Delimiters and Markers

| Field | Description |
|------|------------|
| `listing_marker` | Primary listing delimiter detection strategy |
| `listing_marker_tochange` | Optional replacement marker |
| `symbols` | Symbols recognized as potential listing starters |
| `start_exceptions` | Tokens that should not be treated as listing starts |
| `trailing_comma_glue` | Whether trailing commas are glued to text |

The parser normalizes all listing starters to the canonical `* ` marker.

---

## Neighborhood Extraction Rules

### Core Neighborhood Rule

```json
"neighborhood_rule": {
  "strategy_order": ["delimiter"],
  "prefix_tokens": [...],
  "max_token_span": 25,
  "strategy": "before_dot"
}
```

| Field | Description |
|------|------------|
| `strategy_order` | Order in which extraction strategies are attempted |
| `prefix_tokens` | Tokens removed before neighborhood matching |
| `max_token_span` | Maximum number of tokens to consider |
| `strategy` | Active extraction strategy |

Neighborhood extraction operates only within the configured parsing window.

---

### Neighborhood Flow

| Field | Description |
|------|------------|
| `neighborhood_flow.flow_type` | Controls neighborhood extraction flow logic |

For ACME, a **simple flow** is used.

---

### Neighborhood Aliases

Defines known shorthand or alternate spellings.

Example:
```json
"COL. OZ": ["OZ"]
```

Aliases are resolved **before** catalog matching.

---

## Currency Handling

### Currency Aliases

Maps symbols and abbreviations to canonical currency codes.

Examples:
- `$`, `$.`, `$ ` → USD
- `L`, `Lps.`, `LPS.` → HNL

Currency inheritance is allowed within ranges when conditions are met.

---

## Area Units and Conversion

### Area Aliases

| Key | Meaning |
|----|--------|
| `ac` | Constructed area |
| `at` | Terrain area |
| `mz` | Manzana units |

Each key maps to a list of accepted textual variants.

---

## Range and Separator Rules

| Field | Description |
|------|------------|
| `range_separators` | Tokens used to express numeric ranges |

Used for prices, areas, and counts.

---

## Parsing Overrides

This section fine-tunes extraction rules for ACME listings.

### Bathrooms and Bedrooms

- Keyword-based detection required
- Maximum bathrooms allowed: 6
- Sliding window used to avoid false positives
- Slash-separated formats allowed (e.g. `2/1`)

### Price Rules

- Currency is required
- `k` and `mil` suffixes accepted
- Multiple prices resolved using `first_only`
- Price-per-m² expressions are skipped

### Keywords

Defines keywords that signal price or transaction context:
`precio`, `venta`, `alquiler`, `mensual`, etc.

---

## Section Headers

Defines how section headers map to transactions and property types.

Example:

| Pattern | Transaction | Type |
|-------|------------|------|
| ALQUILER DE APARTAMENTOS | Rent | Apartment |
| VENTA DE CASAS | Sale | House |

Section headers provide **strong contextual cues** and override ambiguous listings.

---

## Design Notes

- All rules are explicit and auditable
- No logic is hard-coded in scripts
- Changes to this file affect interpretation and must be documented
- This configuration is agency-specific and should not be reused blindly

---

This configuration enables deterministic parsing of ACME listings while preserving
the original text and all provenance information.
