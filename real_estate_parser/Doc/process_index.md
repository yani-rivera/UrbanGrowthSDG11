# Process Index — SDG-11 Real-Estate Data Pipeline

This document is the master index for the entire SDG-11 real-estate data pipeline. It provides a single entry point to understand what exists, in what order, and where to find the documentation for each stage.

Use this file if you want to:

- understand the full workflow at a glance,
- navigate the documentation efficiently,
- reproduce the pipeline step by step.

---

# SDG11_ORCHESTRATOR_V3

The SDG11_ORCHESTRATOR_V3 is the primary execution engine for the entire workflow.

The orchestrator coordinates all processing stages through a configuration-driven framework and preserves intermediate outputs, logs, and quality-control artifacts throughout execution.

Typical execution:

```bash
python scripts/SDG11_ORCHESTRATOR_V3.py
```

Available workflow modules:

```text
parse
merge
deduplicate
word_filter
uid
clean_neighborhoods
ptype_fix
filter_records
gis_match
unmatched_check
price_standardize
transaction_validate
area_standardize
aggregate
```

Intermediate outputs are retained rather than overwritten, providing a complete audit trail and supporting validation, quality-control checks, troubleshooting, and human-in-the-loop review at any stage of the workflow.

Documentation:

- docs/orchestrator_usage.md
- docs/orchestrator_configuration.md

---

# Pipeline Overview (Bird’s-Eye View)

Raw Text (Synthetic or Real)
        ↓
Parsing (TXT → CSV)
        ↓
L1clean (Merge, Validate, Standardize)
        ↓
GIS Enrichment
        ↓
Unified Year / Month Dataset
        ↓
Aggregation
        ↓
Published Data Products