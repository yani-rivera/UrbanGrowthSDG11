## Neighborhood Catalog

The neighborhood catalog defines the **canonical spatial units** used to standardize
location information extracted from newspaper listings.

Listings often reference neighborhoods using:
- informal names
- abbreviations
- partial names
- spelling variants

This catalog provides a stable reference to resolve those variations.

---

## Structure and Fields

Each row in the catalog represents **one canonical neighborhood**.

| Field | Description |
|------|------------|
| `ogc_fid` | Internal feature identifier |
| `sector` | Higher-level grouping or zone code |
| `cod_col` | Neighborhood code |
| `name` | Canonical neighborhood name |
| `NEIGHBORHOOD` | Primary standardized label |
| `alias` | Accepted alias or alternate spelling |
| `AliasType` | Alias classification (e.g. Default, Variant) |
| `GISID` | Spatial identifier used in GIS layers |
| `uid` | Stable unique identifier |

---

## Example

```text
cod_col: OZ-CEN
name: Centro de OZ
alias: Centro de OZ
GISID: 1OZ-CEN00
uid: OZ-CEN-GIS
```

This means that any listing referencing  
“Centro de OZ” — regardless of formatting —  
is mapped to the canonical neighborhood **OZ-CEN**.

---

## How the Catalog Is Used

During parsing:

1. A neighborhood string is extracted from a listing
2. The value is compared against the `alias` field
3. If a match is found:
   - the canonical `name` is assigned
   - the corresponding `uid` and `GISID` are attached
4. If no match is found:
   - the listing is flagged for review

The original text is always preserved.

---

## Design Principles

- Neighborhoods are defined **once**
- Spatial identifiers are **stable over time**
- Aliases can be expanded without changing code
- No assumptions are made about spelling or format in raw text

> The catalog does not guess locations.  
> It records decisions explicitly.

---

## Notes

- The catalog can be extended as new aliases appear
- Changes should be versioned
- Updates affect interpretation and should be documented
