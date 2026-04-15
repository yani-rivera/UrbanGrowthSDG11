
## HOW TO EXECUTE THE SYNTHETIC DATA 

All steps are implemented as modular Python scripts and can be executed sequentially.

---

##  Reproducibility and Synthetic Data

To ensure full reproducibility while respecting data access constraints:

* Synthetic datasets are provided that **mimic the structure and format** of the original data sources.
* These datasets allow users to:

  * Execute the full pipeline end-to-end
  * Inspect intermediate outputs
  * Understand expected input/output schemas

> ⚠️ Note: Original data sources are not redistributed. The synthetic data preserves schema and behavior, enabling users to apply the pipeline to their own datasets.

---

## 📂 Project Structure

```
scripts/        # Parsing scripts (data extraction)
tools/          # Processing and transformation scripts
L1clean/        # Cleaning and classification modules
config/         # Configuration files (mnemonics, filters, etc.)
Catalog/        # Standardized neighborhood catalog
FXrate/         # Exchange rate tables
data/raw/       # Input raw data (synthetic examples)
consolidated/   # Intermediate and final outputs
```

---

## ⚙️ Pipeline Execution

Below is the full executable pipeline. Running these commands sequentially will reproduce the dataset.

### 1. Parsing

```bash
python scripts/parse_casamagica_listings_v2.py \
  --file "data/raw/Casamagica/2026/casamagica_20260415.txt" \
  --output "output" \
  --config "config/agency_casamagica.json"
```

### 2. Merging

```bash
python tools/merge_output_csvs.py \
  --year 2026 \
  --month 04 \
  --input output \
  --output consolidated
```

### 3. Word Filtering

```bash
python tools/word_filter.py \
  --input consolidated/2026/merged_202604.csv \
  --output consolidated/2026/merged_202604_flt.csv \
  --col neighborhood \
  --words-file config/remove_words.txt
```

### 4. UID Assignment + Temporal Features

```bash
python tools/AddUid.py \
  -i consolidated/2026/merged_202604_flt.csv \
  -o consolidated/2026/merged_202604_uid.csv \
  --agency-col agency \
  --date-col date \
  --mnemonics config/agency_mnemonics.csv \
  --mnemonic-required \
  --encoding utf-8-sig
```

This step also derives temporal variables such as `year_month`.

---

### 5. Neighborhood Cleaning

```bash
python tools/clean_neighborhoods.py \
  --input_csv consolidated/2026/merged_202604_uid.csv \
  --input_col neighborhood \
  --out_csv consolidated/2026/merged_202604_clean.csv \
  --add_norm
```

---

### 6. Property Type Classification

```bash
python L1clean/ptype_l1_clean_v8.py \
  --input consolidated/2026/merged_202604_clean.csv \
  --output consolidated/2026/merged_202604_clean_ptype_fixed.csv \
  --scores-output consolidated/2026/merged_202604_clean_ptype_fixed_scores.csv
```

---

### 7. Filtering (Quality Control)

```bash
python L1clean/FilterMergedFile.py \
  -i consolidated/2026/merged_202604_clean_ptype_fixed.csv \
  -o consolidated/2026/merged_202604_filtered.csv \
  --price-col "price" \
  --type-col "property_type_new" \
  --exclude-types-files config/exclude_types.csv:Type \
  --exclude-neighborhoods-files config/outside_metro.txt \
  --neigh-col neighborhood_clean_norm \
  --rejected consolidated/2026/202604_filtered_rejected.csv \
  --neigh-match exact
```

---

### 8. Spatial Matching

```bash
python tools/match_cleaned_to_catalog.py \
  --listings_csv consolidated/2026/merged_202604_filtered.csv \
  --listings_col neighborhood_clean_norm \
  --catalog_csv Catalog/standard_neighborhood_catalog.csv \
  --out_merged consolidated/2026/merged_202604_with_gis.csv \
  --out_matched consolidated/2026/matched.csv \
  --out_unmatched consolidated/2026/unmatched.csv
```

---

### 9. Unmatched Review

```bash
python tools/unmatched.py \
  --input consolidated/2026/merged_202604_with_gis.csv
```

---

### 10. Price Standardization

```bash
python tools/StdPrice.py \
  --input consolidated/2026/merged_202604_with_gis_valid.csv \
  --fx FXrate/fx_HNL_USD.csv \
  --output consolidated/2026/merged_202604_STDPrice.csv
```

---

### 11. Transaction Validation

```bash
python L1clean/ValidateTransaction.py \
  --input consolidated/2026/merged_202604_STDPrice.csv \
  --output consolidated/2026/merged_202604_STDPrice_t.csv
```

---

### 12. Area Harmonization

```bash
python tools/terrain_area_to_at.py \
  --input consolidated/2026/merged_202604_STDPrice_t.csv \
  --output consolidated/2026/merged_202604_STDPrice_AreaM2.csv
```

---

### 13. Aggregation (Monthly)

```bash
python tools/Aggregate_Neighborhood_Summary.py \
  --input consolidated/2026/merged_202604_STDPrice_AreaM2.csv \
  --min-n 1 \
  --output consolidated/2026/neighborhood_2026monthly.csv
```

---

### 14. Aggregation by Bedrooms (Year-level)

```bash
python tools/Aggregate_Neighborhood_Summary_ByYear_Bedrooms.py \
  --input consolidated/2026/merged_202604_STDPrice_AreaM2.csv \
  --year 2026 \
  --min-n 3 \
  --output consolidated/2026/neighborhood_monthly_bedrooms_price.csv
```

---

##  Outputs

Key outputs include:

* Cleaned and standardized listing datasets
* GIS-linked neighborhood datasets
* Quality-controlled filtered datasets
* Monthly and yearly aggregated summaries

---

## Notes

* The pipeline is **data-agnostic and can be applied to other real estate datasets with similar structure.
* Intermediate outputs are preserved at each step for **traceability and validation**.
* All CSV files are saved using `utf-8-sig` encoding.

---

