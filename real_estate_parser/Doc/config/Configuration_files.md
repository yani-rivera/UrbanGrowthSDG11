# Configuration Resources and Supporting Files

## Overview

The SDG-11 Real Estate Framework separates processing logic from source-specific knowledge through a configuration-driven architecture. Rather than embedding agency rules, neighborhood references, semantic vocabularies, and validation parameters directly into the code, these resources are maintained as external files.

This approach improves reproducibility, transparency, maintainability, and adaptability. New agencies, years, or datasets can often be incorporated by updating configuration resources without modifying the core processing scripts.

The table below summarizes the principal configuration files, reference datasets, and auxiliary resources used by the framework.

---

## Core Configuration Resources

| File                                | Type            | Description                                                                                        | Required    | Notes                                                           |
| ----------------------------------- | --------------- | -------------------------------------------------------------------------------------------------- | ----------- | --------------------------------------------------------------- |
| `orchestrator_config.json`          | Configuration   | Master pipeline configuration controlling paths, scripts, catalogs, logging, and aggregation tasks | Yes         | Coordinates workflow execution                                  |
| `<agency>.json`                     | Configuration   | Agency-specific parsing rules and source characteristics                                           | Yes         | Required for source interpretation and extraction               |
| `price_semantic_config.json`        | Configuration   | Price extraction, normalization, and interpretation rules                                          | Yes         | Supports standardized price processing                          |
| `property_semantic_config.json`     | Configuration   | Property-type classification rules and vocabularies                                                | Yes         | Supports housing-type standardization                           |
| `transaction_rules.json`            | Configuration   | Transaction classification and validation rules                                                    | Yes         | Supports sale/rent identification and validation                |
| `agency_mnemonics.csv`              | CSV             | Agency-to-mnemonic crosswalk table                                                                 | Yes         | Supports unique identifier generation                           |
| `standard_neighborhood_catalog.csv` | Catalog         | Canonical neighborhood reference catalog with SDG11UID mappings                                    | Yes         | Supports spatial matching and neighborhood normalization        |
| `remove_words.txt`                  | Text            | Terms removed during cleaning and normalization                                                    | Optional    | Improves neighborhood matching performance                      |
| `exclude_types.txt`                 | Text            | Property types excluded from analysis                                                              | Optional    | Applied during filtering procedures                             |
| `outside_metro.txt`                 | Text            | Locations outside the study area                                                                   | Optional    | Supports spatial-scope restrictions                             |
| `fx_HNL_USD.csv`                    | Historical Data | Daily exchange-rate reference table                                                                | Conditional | Required when standardizing historical prices across currencies |
| `fx_mean_HNL_USD.csv`               | Historical Data | Monthly average exchange-rate reference table                                                      | Conditional | Alternative to daily exchange rates                             |
| `nonprice_numeric_cues.json`        | Configuration   | Numeric patterns unlikely to represent prices                                                      | Optional    | Reduces false-positive price detections                         |
| `typewords.yaml`                    | Configuration   | Extended property-type vocabulary definitions                                                      | Optional    | Supports classification refinement and customization            |

---

## Agency Configuration Files

Agency configuration files are the primary mechanism used to adapt the framework to new data sources.

Before a dataset can be parsed, a configuration file must be created describing the characteristics of the source material. Typical parameters include:

* Advertisement delimiters
* Transaction headers
* Neighborhood indicators
* Currency formats
* Property-type cues
* Listing boundaries
* Text normalization rules
* Agency-specific exceptions

These files allow heterogeneous advertisement formats to be interpreted using a common extraction framework.

Example:

```text
config/agencies/agency_roca.json
config/agencies/agency_makos.json
config/agencies/agency_avanti.json
```

---

## Neighborhood Catalog

The neighborhood catalog is one of the most important resources in the framework.

It functions as a spatial crosswalk between advertisement text and GIS polygons.

The catalog contains:

* Standardized neighborhood names
* Alternative spellings
* Common abbreviations
* Historical aliases
* SDG11UID identifiers

Example:

| Alias           | Canonical Neighborhood | SDG11UID     |
| --------------- | ---------------------- | ------------ |
| Col. Palmira    | Palmira                | SDG11-000123 |
| Palmira         | Palmira                | SDG11-000123 |
| Colonia Palmira | Palmira                | SDG11-000123 |

The catalog is maintained as a living resource and is periodically updated as new neighborhoods, developments, and naming variations are identified.

---

## Exchange Rate Resources

Historical advertisements may contain prices expressed in different currencies.

The framework supports exchange-rate standardization using either:

* Daily exchange rates (`fx_HNL_USD.csv`)
* Monthly average exchange rates (`fx_mean_HNL_USD.csv`)

At least one exchange-rate source is required when historical currency normalization is performed.

---

## Reproducibility

The framework is designed as a deterministic processing pipeline.

Given:

* The same source files
* The same configuration resources
* The same software version
* The same processing parameters

the workflow will generate identical outputs.

Changes in output should therefore be attributable to documented modifications in source data, configuration resources, processing rules, or software revisions.

This design allows historical datasets to be regenerated whenever parsing rules, classification logic, validation procedures, or spatial catalogs are improved.
