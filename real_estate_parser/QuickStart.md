# Quick Start

This guide demonstrates the basic workflow for running the SDG-11 Housing Data Reconstruction Framework.

If you are new to the project, start here.

For installation instructions see:

- installation.md
- architecture.md
- orchestrator.md

---

# 1. Clone the Repository

```bash
git clone <repository-url>
cd <repository>
```

---

# 2. Create a Virtual Environment

```bash
python -m venv .venv
source .venv/bin/activate
```

Windows:

```bash
.venv\Scripts\activate
```

---

# 3. Install Dependencies

```bash
pip install -r requirements.txt
```

---

# 4. Verify Configuration

Run a dry run.

```bash
python scripts/SDG11_ORCHESTRATOR_V3.py --dry-run
```

Expected result:

```text
Agency Configurations Found
Input Files Found
Pipeline Validated
```

No processing occurs during this stage.

---

# 5. Add Input Data

Example structure:

```text
data/raw/

└── Makos/
    └── 2011/
        └── makos_20110128.txt
```

Each agency should have:

```text
agency_name/
    year/
        file.txt
```

---

# 6. Run the Full Pipeline

Example:

```bash
python scripts/SDG11_ORCHESTRATOR_V3.py \
    --year 2011 \
    --month 01 \
    --day 28
```

The orchestrator will automatically execute:

```text
Parse
Merge
Deduplicate
Filter
UID
Neighborhood Cleaning
Price Standardization
Transaction Validation
Aggregation
```

---

# 7. Review Outputs

Typical outputs include:

```text
output/
logs/
reports/
consolidated/
```

Examples:

```text
merged_20110128.csv
merged_20110128_UID.csv
merged_20110128_STDPrice.csv
neighborhood_20110128.csv
```

---

# 8. Review Logs

Execution logs are stored in:

```text
logs/
```

Example:

```text
logs/
├── parse_log.csv
└── 20260520_153222/
```

---

# 9. Review Quality-Control Reports

QC outputs are written to:

```text
reports/
```

Examples:

```text
QC_report.txt
QC_flags.csv
property_scores.csv
```

These reports should be reviewed before publication or aggregation.

---

# Typical Workflow

The most common workflow is:

```text
OCR Text
    ↓
Orchestrator
    ↓
Parsed Listings
    ↓
Standardized Dataset
    ↓
Neighborhood Aggregates
```

---

# Running Individual Steps

To execute only selected stages:

```bash
python scripts/SDG11_ORCHESTRATOR_V3.py \
    --steps parse merge
```

Examples:

```text
parse
merge
deduplicate
filter
uid
clean
stdprice
transaction_validate
aggregate
```

---

# Common Commands

Validate configuration:

```bash
python scripts/SDG11_ORCHESTRATOR_V3.py --dry-run
```

Run parser only:

```bash
python scripts/SDG11_ORCHESTRATOR_V3.py --steps parse
```

Run parser and merge:

```bash
python scripts/SDG11_ORCHESTRATOR_V3.py --steps parse merge
```

Run complete workflow:

```bash
python scripts/SDG11_ORCHESTRATOR_V3.py \
    --year 2011 \
    --month 01 \
    --day 28
```

---

# Next Steps

After completing the Quick Start:

1. Read architecture.md
2. Read orchestrator.md
3. Review configuration.md
4. Review data_dictionary.md
5. Explore module documentation in docs/modules/

You are now ready to reconstruct and standardize housing-market datasets using the SDG-11 framework.