## General Configuration File Reference

This document describes the **common configuration variables** used across
agency-specific JSON configuration files.

Agency configuration files define **how listings are interpreted**, not the data itself.
All variables are explicit and override global defaults when present.

---

## File Scope

- Applies to files named `agency_<name>.json`
- Variables may be optional unless stated otherwise
- Missing variables fall back to parser defaults

---

## 1. Identification

| Field | Type | Description |
|------|------|------------|
| `agency` | string | Human-readable agency name |
| `nemonic` | string | Short stable mnemonic used in IDs and paths |

---

## 2. Preprocessing Controls

| Field | Type | Description |
|------|------|------------|
| `preprocessing_needed` | boolean | Whether preprocessing is required |
| `preprocess` | list | Ordered list of preprocessing steps |
| `sanitize` | boolean | Enable text sanitization |
| `emit_marker` | boolean | Emit normalized listing markers |
| `listing_marker` | string | Strategy for detecting listing starts |
| `listing_marker_tochange` | string | Marker to normalize to (usually `*`) |
| `symbols` | list | Characters recognized as listing starters |
| `start_exceptions` | list | Tokens ignored as listing starts |

---

## 3. Parsing Window and Constraints

| Field | Type | Description |
|------|------|------------|
| `max_cue_pos` | integer | Max character position for parsing cues |
| `max_token_span` | integer | Max number of tokens to inspect |
| `require_upper` | boolean | Require uppercase tokens for some strategies |
| `require_price_before` | boolean | Require price before other cues |

---

## 4. Neighborhood Extraction

### Core Rule

| Field | Type | Description |
|------|------|------------|
| `neighborhood_rule.strategy` | string | Extraction strategy name |
| `neighborhood_rule.strategy_order` | list | Order of strategies to try |
| `neighborhood_rule.prefix_tokens` | list | Tokens removed before matching |

Neighborhood extraction operates only within the configured parsing window.

---

### Neighborhood Flow

| Field | Type | Description |
|------|------|------------|
| `neighborhood_flow.flow_type` | string | Defines extraction flow logic |

---

### Neighborhood Aliases

| Field | Type | Description |
|------|------|------------|
| `neighborhood_aliases` | object | Maps shorthand or variants to canonical forms |

Aliases are resolved **before** catalog matching.

---

## 5. Currency Handling

### Currency Aliases

| Field | Type | Description |
|------|------|------------|
| `currency_aliases` | object | Maps symbols and strings to currencies |
| `currency_inherit_range` | boolean | Allow currency inheritance in ranges |

---

## 6. Area Handling

### Area Aliases

| Field | Type | Description |
|------|------|------------|
| `area_aliases` | object | Maps area types to accepted variants |
| `glue_area_tails` | boolean | Glue area suffixes to values |

---

## 7. Price Handling

| Field | Type | Description |
|------|------|------------|
| `glue_price_tails` | boolean | Glue price suffixes |
| `price_keywords` | list | Keywords signaling price context |
| `price_resolution` | string | Strategy for resolving multiple prices |
| `skip_price_per_unit` | boolean | Skip price-per-area expressions |

---

## 8. Numeric Ranges

| Field | Type | Description |
|------|------|------------|
| `range_separators` | list | Tokens indicating numeric ranges |

Used for prices, areas, and counts.

---

## 9. Bedrooms and Bathrooms

| Field | Type | Description |
|------|------|------------|
| `bedroom_keywords` | list | Keywords indicating bedrooms |
| `bathroom_keywords` | list | Keywords indicating bathrooms |
| `max_bathrooms` | integer | Maximum allowed bathroom count |
| `allow_slash_format` | boolean | Allow formats like `2/1` |

---

## 10. Section Headers

| Field | Type | Description |
|------|------|------------|
| `section_headers` | list | Maps section patterns to context |
| `section_headers.pattern` | string | Header text or regex |
| `section_headers.transaction` | string | Implied transaction |
| `section_headers.property_type` | string | Implied property type |

Section headers provide **strong contextual overrides**.

---

## 11. Design Principles

- Configuration files encode decisions, not logic
- All behavior is explicit and auditable
- Defaults exist but overrides are intentional
- Changes affect interpretation and must be documented

---

This reference serves as a shared vocabulary for understanding
and reviewing agency configuration files.
