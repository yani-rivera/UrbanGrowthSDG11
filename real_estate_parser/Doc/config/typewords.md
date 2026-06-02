# typewords.yaml

## Purpose

The `typewords.yaml` file provides the semantic vocabulary used by the SDG-11 Real Estate Framework to classify property types and identify housing-related attributes within advertisement text.

Rather than hard-coding keywords directly into the software, classification terms are externalized into a configurable resource. This allows researchers to extend, refine, translate, or customize property classifications without modifying the underlying code.

The file functions as a domain-specific vocabulary describing residential, commercial, and land-related concepts commonly encountered in real-estate advertisements.

---

## Used By

* Property type classification
* Semantic scoring
* Residential/commercial identification
* Land detection
* Bedroom extraction
* Area interpretation
* Quality-control procedures

---

## Structure Overview

```text
typewords.yaml
├── version
├── residential
│   ├── house
│   ├── apartment
│   ├── bedrooms
│   ├── rooms
│   ├── amenities
│   ├── apartment_adj
│   ├── house_adj
│   └── construction
├── land
├── area_units
├── land_varas_units
├── commercial
└── patterns
```

---

## Residential Vocabulary

The residential section contains terms associated with housing advertisements.

### House Indicators

Examples:

* casa
* residencia
* vivienda
* townhouse
* condominio

These terms contribute evidence that an advertisement refers to a residential house.

### Apartment Indicators

Examples:

* apartamento
* departamento
* apto
* penthouse
* condominio

These terms contribute evidence that an advertisement refers to an apartment or condominium.

### Bedroom Indicators

Examples:

* habitación
* hab
* dormitorio
* recámara
* alcoba
* cuarto

These terms support bedroom extraction and housing-type classification.

### Room Indicators

Examples:

* sala
* comedor
* cocina
* terraza
* oficina
* lavandería
* patio

These provide additional contextual evidence for residential properties.

### Residential Amenities

Examples:

* balcón
* piscina
* gimnasio
* walk closet
* cuarto de empleada
* elevador

These terms contribute supplementary classification signals.

---

## Land Vocabulary

The land section contains terms associated with vacant land and undeveloped parcels.

Examples:

* terreno
* lote
* solar
* parcela
* finca
* manzana

These terms are used to distinguish land listings from built properties.

---

## Area Units

Defines measurement units recognized by the framework.

Examples:

* m2
* mts2
* metros
* m²
* vara
* varas
* vrs²

These units support area normalization and price-per-area calculations.

---

## Commercial Vocabulary

The commercial section contains terminology associated with business and institutional properties.

### Commercial Units

Examples:

* local comercial
* oficina
* colegio
* hotel
* clínica
* galería
* nave industrial
* plaza comercial

### Warehouses

Examples:

* bodega
* ofi-bodega

### Corporate Properties

Examples:

* corporativo
* edificio corporativo
* edificio comercial

### Commercial Usage

Examples:

* comercial
* coworking
* co-working

### Commercial Amenities

Examples:

* lobby
* recepción
* vigilancia
* fibra óptica
* planta eléctrica
* estacionamiento

These categories support identification of commercial and mixed-use properties.

---

## Weighted Classification

Each category includes a weight value.

Example:

```yaml
house:
  weight: 5
```

Weights are used by the classification engine to assign confidence and determine the most likely property category based on the vocabulary detected within an advertisement.

This approach allows multiple categories to contribute evidence while preserving transparency in classification decisions.

---

## Pattern Definitions

The patterns section contains regular expressions used to identify common real-estate expressions.

Examples include:

### Bedroom Counts

```text
3 hab
4 hab
5 hab
```

### Zero Bedrooms

```text
habitaciones: 0
hab: 0
```

### Price Per Area

```text
$50 por m2
$120 x m²
```

### Land Measurement Patterns

Detection of:

* varas
* varas cuadradas
* vrs²

These patterns complement the vocabulary-based classification system.

---

## Customization

The vocabulary can be adapted to:

* Different countries
* Alternative terminology
* Regional abbreviations
* New property categories
* Additional languages

Because all terms are maintained externally, updates can be applied without modifying the framework source code.

---

## Design Philosophy

The `typewords.yaml` file acts as a configurable real-estate vocabulary and semantic classification resource. By separating domain knowledge from processing logic, the framework remains maintainable, transparent, and adaptable while supporting reproducible property classification across heterogeneous housing-market datasets.
