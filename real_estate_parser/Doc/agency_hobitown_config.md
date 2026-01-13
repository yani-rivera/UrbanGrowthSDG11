## Agency Configuration: Hobitown

This document describes the configuration file used to parse and standardize
real-estate listings originating from the **Hobitown** agency.

The configuration is stored as a JSON file and defines **agency-specific parsing behavior**,
overriding generic defaults where necessary.

---

## File Overview

- **Filename:** `agency_hobitown.json`
- **Agency name:** Hobitown
- **Mnemonic:** HBTWN

This file is read-only during execution.

---

## General Settings

| Field | Description |
|------|------------|
| `agency` | Human-readable agency name |
| `nemonic` | Stable mnemonic used in IDs and paths |
| `preprocessing_needed` | Whether preprocessing steps are required |
| `preprocess` | Ordered preprocessing stages to apply |
| `sanitize` | Enables text sanitization |
| `emit_marker` | Whether to emit listing markers in output |
| `listing_marker` | Strategy used to detect listing starts |
| `listing_marker_tochange` | Optional replacement marker |
| `symbols` | Symbols recognized as listing starters |
| `max_cue_pos` | Maximum character position for parsing cues |
| `require_upper` | Requires uppercase tokens for certain strategies |
| `require_price_before` | Whether price must precede other cues |
| `trailing_comma_glue` | Whether trailing commas are glued |
| `glue_price_tails` | Whether price suffixes are glued |
| `glue_area_tails` | Whether area suffixes are glued |

---

## Listing Marker Behavior

Hobitown listings use a **dot-based cue strategy** (`CUE:DOT`) to detect listing starts.

Recognized starter symbols include:

```
*, •, >, -
```

All detected markers are normalized internally to the canonical `* ` delimiter.

---

## Neighborhood Extraction Rules

### Neighborhood Rule

```json
"strategy": "before_dot"
```

Neighborhood extraction:
- operates within the configured parsing window (`max_cue_pos = 30`)
- removes generic prefixes before matching
- extracts text before the first dot

#### Prefix Tokens

The following tokens are stripped before matching:

```
col., colonia, res., resid., residencial, urb., bo., barrio,
ave., av., Lps.
```

This improves deterministic matching against the Neighborhood Catalog.

---

### Neighborhood Flow

| Field | Description |
|------|------------|
| `neighborhood_flow.flow_type` | Defines the extraction flow logic |

Hobitown uses a **simple flow**, meaning extraction is attempted once per listing.

---

### Neighborhood Aliases

Defines accepted shorthand or alternate names:

```json
"COL. OZ"       → "OZ"
"COL. COMARCA"  → "COMARCA"
"RES. ZANAHORA" → "ZANAHORIA"
```

Aliases are resolved **before** catalog matching.

---

## Currency Handling

### Currency Aliases

Maps currency symbols and abbreviations to canonical currency codes.

Supported currencies:
- **USD**
- **HNL**

Examples:
- `$`, `$.`, `$ ` → USD
- `L`, `Lps.`, `LPS.` → HNL

Currency inheritance across ranges is enabled under defined constraints.

---

## Area Units and Conversion

### Area Aliases

| Key | Meaning |
|----|--------|
| `ac` | Constructed area |
| `at` | Terrain area |
| `mz` | Manzana units |

Each key maps to multiple textual variants used in listings.

---

## Range and Separator Rules

Supported range separators:

```
/, -, a, hasta, –, —
```

These apply to prices, areas, and numeric attributes.

---

## Parsing Overrides

This section fine-tunes extraction behavior for Hobitown listings.

### Bathrooms

- Keyword-based detection required
- Maximum allowed value: 6
- Sliding token window applied
- Slash formats allowed (e.g. `2/1`)

### Price Rules

- Currency is required
- `k` and `mil` suffixes accepted
- Multiple prices resolved using `first_only`
- Price-per-square-meter expressions are skipped
- Currency inheritance enabled for ranges above 1000

### Price Keywords

```
precio, venta, alquiler, renta, mensual, /mes, por mes
```

---

## Section Headers

Section headers provide strong contextual cues and override ambiguous listings.

| Pattern | Transaction | Property Type |
|-------|------------|---------------|
| ALQUILER DE APARTAMENTOS | Rent | Apartment |
| ALQUILER DE CASAS | Rent | House |
| VENTA DE APARTAMENTOS | Sale | Apartment |
| VENTA DE CASAS | Sale | House |
| VENTA DE TERRENOS | Sale | Land |
| VENTA DE BODEGAS | Sale | Commercial |

---

## Design Notes

- All rules are explicit and auditable
- No assumptions are inferred implicitly
- Changes to this file affect interpretation and must be documented
- This configuration is specific to Hobitown and should not be reused blindly

---

This configuration enables deterministic parsing of Hobitown listings
while preserving original text and provenance.
