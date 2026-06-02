# SDG-11 Processing Workflow

This document summarizes the end-to-end processing workflow used to transform raw real-estate advertisements into standardized neighborhood-level datasets.

---

## Full Pipeline

| Step                            | Script / Process                    | Description                                                                              | Input                         | Output                                |
| ------------------------------- | ----------------------------------- | ---------------------------------------------------------------------------------------- | ----------------------------- | ------------------------------------- |
| 1. Parsing                      | `parse_casamagica_listings_v2.py`   | Extracts structured listing data from raw text files using agency-specific configuration | Raw text listings             | `casamagica_20260415.csv`             |
| 2. Merging                      | `merge_output_csvs.py`              | Consolidates parsed outputs into a monthly dataset                                       | Parsed CSVs                   | `merged_202604.csv`                   |
| 3. Word Filtering               | `word_filter.py`                    | Removes undesired or noisy terms from neighborhood field                                 | Merged dataset                | `merged_202604_flt.csv`               |
| 4. UID Assignment               | `AddUid.py`                         | Generates unique identifiers using agency, date, and mnemonic rules                      | Filtered dataset              | `merged_202604_uid.csv`               |
| 5. Neighborhood Cleaning        | `clean_neighborhoods.py`            | Standardizes and normalizes neighborhood names                                           | UID dataset                   | `merged_202604_clean.csv`             |
| 6. Property Type Classification | `ptype_l1_clean_v8.py`              | Assigns and corrects property types using rule-based scoring                             | Clean dataset                 | `merged_202604_clean_ptype_fixed.csv` |
| 7. Filtering                    | `FilterMergedFile.py`               | Removes invalid entries (excluded types, out-of-scope neighborhoods, missing prices)     | Classified dataset            | `merged_202604_filtered.csv`          |
| 8. Spatial Matching             | `match_cleaned_to_catalog.py`       | Matches cleaned neighborhoods to standardized GIS catalog                                | Filtered dataset              | `merged_202604_with_gis.csv`          |
| 9. Unmatched Review             | `unmatched.py`                      | Review unresolved GIS matches                                                            | GIS-linked dataset            | `merged_202604_with_gis_valid.csv`    |
| 10. Price Standardization       | `StdPrice.py`                       | Convert and standardize currencies                                                       | GIS-validated dataset         | `merged_202604_STDPrice.csv`          |
| 11. Transaction Validation      | `ValidateTransaction.py`            | Validate rent/sale assignment using semantic rules                                       | Standardized dataset          | `merged_202604_STDPrice_t.csv`        |
| 12. Area Harmonization          | `terrain_area_to_at.py`             | Standardize area measurements into metric units                                          | Transaction-validated dataset | `merged_202604_STDPrice_AreaM2.csv`   |
| 13. Aggregation                 | `Aggregate_Neighborhood_Summary.py` | Generate monthly neighborhood-level indicators                                           | Standardized dataset          | `neighborhood_2026monthly.csv`        |

---

## Orchestrator Execution

The recommended way to run the framework is through the orchestrator.

### Full Pipeline Example

```bash
python scripts/SDG11_ORCHESTRATOR_V3.py \
  --all-agencies \
  --year 2010 \
  --steps \
    parse \
    merge \
    deduplicate \
    word_filter \
    uid \
    clean_neighborhoods \
    ptype_fix \
    filter_records \
    gis_match \
    unmatched_check \
    price_standardize \
    transaction_validate \
    area_standardize \
    aggregate
```

### Pipeline Executed

```text
Raw Listings
      ↓
Parse
      ↓
Merge
      ↓
Deduplicate
      ↓
```
