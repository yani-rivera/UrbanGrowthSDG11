# Property Type L1 Validation Module (`ptype_l1_clean_v8.py`)

## Purpose

The Property Type L1 Validation Module performs semantic validation and reclassification of real-estate listings after the initial parsing stage.

The objective is not simply to assign a property type, but to evaluate whether the originally assigned type remains consistent with the evidence contained within the advertisement text.

The module operates as a quality-control and classification refinement layer within the SDG-11 framework.

*  Uses property_semantic_config.json

---

# Position Within the SDG-11 Pipeline

```text
Property Extraction
        ↓
Initial Property Type
        ↓
Property Type L1 Validation
        ↓
Validated Property Type
        ↓
Aggregation
        ↓
Housing Indicators
```

---

# Problem Statement

Property classifications derived during parsing may occasionally be incomplete or ambiguous.

Example:

```text
Casa para oficinas
```

Initial classification:

```text
HOUSE
```

However, the intended use is commercial.

The L1 classifier evaluates the entire advertisement and determines whether the original classification remains appropriate.

---

# Design Philosophy

The module follows five core principles.

## 1. Evidence-Based Classification

Classifications are determined through observable textual evidence rather than rigid keyword replacement.

---

## 2. Points-Based Scoring

Each property category accumulates positive and negative evidence.

The category with the strongest score becomes the preferred classification.

---

## 3. Human-Readable Decisions

Every classification records the reason for the decision.

Example:

```text
POINTS:Commercial(22)
```

---

## 4. Preserve Original Classification

The original property type remains available for auditing.

Example fields:

```text
property_type_original
property_type_new
```

---

## 5. Human-in-the-Loop Compatibility

Ties and uncertain cases are intentionally preserved rather than aggressively resolved.

---

# Supported Property Categories

The classifier currently evaluates:

| Category   | Description                                        |
| ---------- | -------------------------------------------------- |
| House      | Residential houses                                 |
| Apartment  | Apartments and condominiums                        |
| Commercial | Offices, warehouses, retail, mixed commercial uses |
| Land       | Lots, parcels, terrain                             |

---

# Configuration-Driven Architecture

All classification vocabularies are externalized into:

```text
config/typewords.yaml
```

This design allows:

* New terminology
* Additional languages
* Historical vocabulary
* Agency-specific wording

without modifying source code.

---

# Classification Workflow

```text
Advertisement Text
        ↓
Text Normalization
        ↓
Keyword Detection
        ↓
Score Calculation
        ↓
Winner Selection
        ↓
Audit Output
```

---

# Text Normalization

Before scoring:

* Accents are removed
* Text is converted to lowercase
* Excess whitespace is removed

Example:

```text
APARTAMENTO DE LUJO
```

becomes:

```text
apartamento de lujo
```

This improves matching consistency.

---

# Residential Signals

## House Indicators

Examples:

```text
casa
residencia
vivienda
```

These contribute positive evidence toward:

```text
House
```

---

## Apartment Indicators

Examples:

```text
apartamento
condominio
penthouse
```

These contribute positive evidence toward:

```text
Apartment
```

---

## Bedroom Indicators

Examples:

```text
3 habitaciones
```

```text
4 dormitorios
```

increase residential confidence.

---

## Residential Amenities

Examples:

```text
sala
comedor
cocina
```

provide additional residential evidence.

---

# Commercial Signals

## Commercial Units

Examples:

```text
local
oficina
consultorio
```

increase:

```text
Commercial
```

scores.

---

## Warehouses

Examples:

```text
bodega
```

provide strong commercial evidence.

---

## Corporate Signals

Examples:

```text
corporativo
empresarial
```

increase commercial confidence.

---

## Commercial Use Language

Examples:

```text
uso comercial
```

```text
ideal para oficinas
```

increase commercial scores.

---

# Land Signals

## Terrain Indicators

Examples:

```text
terreno
solar
lote
parcela
```

increase:

```text
Land
```

scores.

---

## Vara-Based Measurements

Examples:

```text
800 Vrs²
```

provide strong land evidence.

---

## Land Pricing Patterns

Examples:

```text
$300 por vara
```

are interpreted as land-related signals.

---

# Scoring Model

Each category accumulates evidence independently.

Example:

```text
House = 18
Apartment = 4
Commercial = 2
Land = 0
```

Winner:

```text
House
```

---

# Positive and Negative Evidence

The model supports both rewards and penalties.

Example:

```text
apartamento
```

may add:

```text
Apartment +10
```

while:

```text
800 Vrs²
```

may apply:

```text
Apartment -10
```

because large vara-based land measurements are rarely apartment listings.

---

# Original-Type Prior

The original classification receives a small prior score.

Example:

```text
Apartment +6
```

This prevents unnecessary reclassification when evidence is weak.

---

# Explicit Overrides

Some patterns trigger immediate decisions.

---

## Dormitories

Example:

```text
Dorms
```

Result:

```text
KEEP:ORIGINAL_DORMS
```

Dormitories are inherited and never inferred.

---

## Partial Construction

Example:

```text
construcción parcial
```

Result:

```text
Partial_Construction
```

This category bypasses the standard scoring process.

---

# Tie Handling

If multiple categories obtain identical top scores:

Example:

```text
House = 12
Commercial = 12
```

Result:

```text
KEEP:TIE(House|Commercial)
```

The original classification is retained.

This design supports human review.

---

# No-Cue Handling

If no meaningful evidence is detected:

Example:

```text
max_score = 0
```

Result:

```text
KEEP:NO_CUES
```

The original classification remains unchanged.

---

# Generated Fields

The module creates:

| Field                  | Description                    |
| ---------------------- | ------------------------------ |
| property_type_original | Original parser classification |
| property_type_new      | L1 validated classification    |
| property_type_reason   | Explanation of decision        |
| property_type_changed  | Change indicator               |

---

# Example

Input:

```text
Casa ideal para oficinas
```

Original:

```text
House
```

Scores:

```text
House = 10
Commercial = 18
```

Output:

```text
property_type_new = Commercial
property_type_reason = POINTS:Commercial(18)
property_type_changed = TRUE
```

---

# Optional Audit File

The module can generate a classification audit dataset.

Example:

```bash
--scores-output property_scores.csv
```

The audit file records:

* Category scores
* Winning category
* Score margins
* Tie indicators
* Classification changes

---

# Example Audit Fields

| Field            | Description                               |
| ---------------- | ----------------------------------------- |
| score_house      | House score                               |
| score_apartment  | Apartment score                           |
| score_commercial | Commercial score                          |
| score_land       | Land score                                |
| winner_margin    | Difference between first and second place |
| tie_flag         | Indicates tie                             |
| changed          | Indicates reclassification                |

---

# Classification Transparency

Every decision is traceable.

Example:

```text
POINTS:Land(25)
```

immediately reveals:

* Winning category
* Final score

This transparency greatly simplifies quality control.

---

# Command-Line Usage

## Standard Processing

```bash
python ptype_l1_clean_v8.py \
    --input listings.csv \
    --output listings_l1.csv
```

---

## With Audit Output

```bash
python ptype_l1_clean_v8.py \
    --input listings.csv \
    --output listings_l1.csv \
    --scores-output property_scores.csv
```

---

# Relationship to Earlier Stages

### Initial Parser

Provides:

```text
property_type
```

based on immediate extraction.

---

### L1 Validation

Provides:

```text
property_type_new
```

based on semantic evidence.

This separation improves reproducibility and auditability.

---

# Role Within the SDG-11 Framework

The Property Type L1 Validation Module provides the semantic classification quality-control layer of the SDG-11 real-estate reconstruction framework.

Its purpose is to evaluate whether extracted property types remain consistent with the full advertisement context while preserving the original classification and documenting all classification decisions.

The resulting classifications support:

* Housing market segmentation
* Residential vs commercial analysis
* Neighborhood-level aggregation
* Housing affordability indicators
* Urban land-use studies
* SDG-11 monitoring

By using a transparent points-based model rather than opaque machine-learning predictions, the module prioritizes interpretability, reproducibility, and human review throughout the classification process.
