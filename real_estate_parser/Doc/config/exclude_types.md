# exclude_types.csv

## Purpose

The `exclude_types.csv` file defines property categories that should be excluded from specific analytical workflows.

The SDG-11 framework is capable of processing multiple property types, including residential, commercial, industrial, and land-related listings. However, some analyses may focus exclusively on residential housing markets. In such cases, property categories not relevant to the research objective can be filtered automatically using this exclusion list.

---

## Used By

* Filtering stage
* Dataset preparation
* Residential-only analyses
* Quality-control procedures

---

## Structure

The file contains a single column:

| Column | Description                  |
| ------ | ---------------------------- |
| Type   | Property category to exclude |

### Example

| Type                 |
| -------------------- |
| land                 |
| commercial           |
| warehouse            |
| Partial_Construction |

---

## Workflow Role

During the filtering stage, the property type assigned to each record is compared against the exclusion list.

If a match is found, the record is removed from subsequent processing steps.

Example:

```text
Property Type = LAND
```

↓

```text
Found in exclude_types.csv
```

↓

```text
Record excluded
```

---

## Typical Use Cases

### Residential Housing Analysis

Exclude:

* Land
* Commercial properties
* Warehouses
* Industrial facilities

Retain:

* Houses
* Apartments

### Commercial Market Analysis

The exclusion list can be modified to retain commercial properties while excluding residential listings.

### Custom Studies

Researchers may tailor the exclusion list to match the objectives of a specific project.

---

## Maintenance

The file can be updated without modifying the framework source code.

New categories can be:

* Added
* Removed
* Renamed

depending on project requirements.

---

## Design Philosophy

The framework separates classification from analytical scope. Property types are first identified and standardized during processing. The exclusion list then determines which categories are retained for a particular analysis. This approach provides flexibility while preserving a consistent underlying data model.
