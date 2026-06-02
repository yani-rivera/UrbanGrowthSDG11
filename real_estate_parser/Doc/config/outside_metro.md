# outside_metro.txt

## Purpose

The `outside_metro.txt` file contains geographic references that should not be matched to the canonical neighborhood catalog during spatial harmonization.

The file functions as a spatial exclusion list and quality-control resource. It prevents non-neighborhood locations, landmarks, municipalities, highways, commercial centers, and other geographic references from being incorrectly assigned a neighborhood identifier (SDG11UID).

---

## Used By

* Neighborhood normalization
* GIS matching
* Spatial quality control
* SDG11UID assignment

---

## Why It Is Needed

Real-estate advertisements frequently describe properties using nearby landmarks, highways, municipalities, commercial centers, or regional references instead of neighborhood names.

Examples include:

```text id="8utlzm"
Boulevard Morazán
Mall Multiplaza
UNITEC
Anillo Periférico
Carretera al Zamorano
```

Although these locations provide useful context for human readers, they do not represent valid neighborhood polygons within the study area.

Without an exclusion mechanism, these references could be incorrectly interpreted as neighborhoods.

---

## Typical Categories

### Municipalities Outside the Study Area

Examples:

* Danlí
* Choloma
* Tela
* La Ceiba
* Catacamas
* Marcala
* Yuscarán

### Transportation Corridors

Examples:

* Boulevard Morazán
* Boulevard Suyapa
* Boulevard Juan Pablo II
* Anillo Periférico
* Carretera al Norte
* Carretera al Sur

### Educational Institutions

Examples:

* UNITEC
* UTH

### Commercial Centers

Examples:

* Mall Multiplaza
* Plaza Miraflores
* Novacentro
* Interplaza

### Landmarks

Examples:

* BCIE
* Emisoras Unidas
* Aeropuerto
* Ministerio de Salud

### Regional References

Examples:

* Valle de Ángeles
* Santa Lucía
* Zambrano
* Ojojona
* Tatumbla

---

## Workflow Role

During neighborhood matching, candidate locations extracted from advertisements are compared against the canonical neighborhood catalog.

If a candidate location appears in `outside_metro.txt`, it is excluded from automatic neighborhood assignment and flagged for alternative processing or review.

This prevents the creation of incorrect spatial matches and improves the accuracy of neighborhood-level indicators.

---

## Maintenance

The file is maintained as an evolving quality-control resource.

New entries are added when:

* New municipalities are encountered.
* New commercial centers appear.
* Additional landmarks generate false matches.
* New transportation corridors are identified.
* Human review detects recurring spatial classification errors.

---

## Design Philosophy

The framework prioritizes spatial precision over aggressive matching. The purpose of `outside_metro.txt` is not to identify neighborhoods, but to explicitly document geographic references that should not be interpreted as neighborhoods. This defensive strategy reduces false-positive GIS matches and improves the reliability of downstream spatial analyses.
