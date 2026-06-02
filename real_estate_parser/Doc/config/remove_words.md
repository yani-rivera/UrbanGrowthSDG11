# remove_words.txt

## Purpose

The `remove_words.txt` file contains phrases, descriptors, and advertisement terminology that should be removed before neighborhood normalization and GIS matching.

Real-estate advertisements frequently combine neighborhood names with marketing language, property descriptions, amenities, and promotional text. These elements can interfere with automated location extraction and reduce neighborhood-matching accuracy.

This file provides a configurable mechanism for removing non-geographic text before spatial harmonization.

---

## Used By

* Neighborhood cleaning
* Neighborhood normalization
* GIS matching
* Spatial quality control

---

## Why It Is Needed

Consider the following advertisement fragment:

```text id="ynhprx"
VENTA APARTAMENTO EN COLONIA PALMIRA
```

Without preprocessing, the extracted location candidate may be:

```text id="a4y8b7"
VENTA APARTAMENTO EN COLONIA PALMIRA
```

After applying `remove_words.txt`:

```text id="x8nlyw"
COLONIA PALMIRA
```

This significantly improves matching against the canonical neighborhood catalog.

---

## Typical Categories

### Transaction Phrases

Examples:

```text id="e32xf4"
VENTA APARTAMENTO EN
RENTA CASA EN
RENTA APARTAMENTO EN
PREVENTA EN
SE VENDE EN
```

### Property Descriptors

Examples:

```text id="pkz1jg"
CASA
APARTAMENTO
PENTHOUSE
TOWNHOUSE
EDIFICIO
LOCAL
```

### Marketing Language

Examples:

```text id="g0oz2m"
GANGA
PRECIOSO
HERMOSO
DE LUJO
IDEAL
```

### Amenity References

Examples:

```text id="n5g5ws"
PISCINA
CIRCUITO
COMPLEJO
ZONA PRIVADA
```

### Positional Modifiers

Examples:

```text id="3rm6xv"
A POCOS METROS DEL
FRENTE AL
CONTIGUO A
CERCA
DENTRO DE
```

---

## Workflow Role

The cleaning stage applies these removal rules before neighborhood matching occurs.

### Example

Original text:

```text id="4g1p6q"
HERMOSA CASA EN RESIDENCIAL PALMIRA CON PISCINA
```

After cleaning:

```text id="rz2wsl"
RESIDENCIAL PALMIRA
```

After neighborhood normalization:

```text id="gx53g0"
PALMIRA
```

This cleaned value can then be matched against the canonical neighborhood catalog and assigned an SDG11UID.

---

## Maintenance

The file is maintained as an evolving resource.

New entries are added when:

* Human review identifies recurring false matches.
* New marketing terminology appears.
* New advertisement styles emerge.
* Additional agency-specific descriptors are discovered.

Because the vocabulary is externalized, updates can be made without modifying the framework source code.

---

## Design Philosophy

The framework prioritizes extraction of geographic information over promotional content. The purpose of `remove_words.txt` is to progressively remove descriptive and marketing language so that neighborhood names remain as the dominant signal for spatial matching. This improves GIS linkage accuracy, reduces false-positive matches, and increases consistency across agencies, publication periods, and advertisement formats.
