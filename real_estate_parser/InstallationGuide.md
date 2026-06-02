# Installation Guide

This document explains how to install and configure the SDG-11 Housing Data Reconstruction Framework.

---

# System Requirements

The framework has been developed and tested primarily on:

| Component        | Recommended      |
| ---------------- | ---------------- |
| Operating System | macOS, Linux     |
| Python           | 3.10+            |
| RAM              | 8 GB minimum     |
| Storage          | 5 GB+ free space |
| Git              | Latest version   |

For large historical datasets, 16–32 GB RAM is recommended.

---

# Clone the Repository

Clone the repository:

```bash
git clone https://github.com/<your-account>/<repository>.git
cd <repository>
```

---

# Create a Virtual Environment

Create a dedicated Python environment.

## macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
```

## Windows

```bash
python -m venv .venv
.venv\Scripts\activate
```

---

# Install Dependencies

Install all required packages:

```bash
pip install -r requirements.txt
```

Verify installation:

```bash
pip list
```

---

# Repository Structure

Expected structure:

```text
project/
│
├── config/
├── data/
├── scripts/
├── tools/
├── docs/
├── logs/
├── reports/
├── output/
└── requirements.txt
```

---

# Configure the Framework

The framework is configuration-driven.

The primary configuration file is:

```text
config/orchestrator_config.json
```

Example:

```json
{
  "paths": {
    "agency_config_dir": "config/agencies",
    "semantic_config": "config/price_semantic_config.json",
    "mnemonics_file": "config/agency_mnemonics.csv"
  }
}
```

Review and adjust paths as needed.

---

# Agency Configuration Files

Each agency requires a dedicated configuration file.

Example:

```text
config/agencies/
├── agency_makos.json
├── agency_casabianca.json
├── agency_inverprop.json
```

These files define:

* Parsing rules
* Section markers
* Transaction keywords
* Property-type cues
* Agency-specific formatting

See:

```text
docs/configuration.md
```

for details.

---

# Input Data Organization

Historical text files should be placed in:

```text
data/raw/
```

Recommended structure:

```text
data/raw/
│
├── Makos/
│   └── 2011/
│       ├── makos_20110128.txt
│       └── makos_20110228.txt
│
├── Casabianca/
│   └── 2011/
│       └── casabianca_20110128.txt
│
└── Inverprop/
    └── 2011/
        └── inverprop_20110128.txt
```

---

# Verify Configuration

Before running the framework, perform a dry run.

Example:

```bash
python scripts/SDG11_ORCHESTRATOR_V3.py --dry-run
```

The dry run verifies:

* Agency configurations
* Input file discovery
* Required paths
* Pipeline settings

No data processing occurs during this stage.

---

# Running the Pipeline

## Full Pipeline

Example:

```bash
python scripts/SDG11_ORCHESTRATOR_V3.py \
    --year 2011 \
    --month 01 \
    --day 28
```

The orchestrator will execute all configured stages.

---

## Selected Pipeline Steps

Example:

```bash
python scripts/SDG11_ORCHESTRATOR_V3.py \
    --year 2011 \
    --month 01 \
    --day 28 \
    --steps parse merge
```

Only the specified steps will run.

---

# Expected Outputs

Outputs are written to:

```text
output/
```

Example:

```text
output/
│
├── Makos/
├── Casabianca/
├── Inverprop/
└── consolidated/
```

Additional outputs include:

```text
logs/
reports/
```

---

# Logging

Execution logs are automatically created.

Example:

```text
logs/
├── parse_log.csv
└── 20260520_153222/
```

Logs contain:

* Execution status
* Processed agencies
* Input files
* Output files
* Error messages

---

# Quality Control Outputs

Several stages generate QC products.

Examples:

```text
reports/
├── QC_report.txt
├── QC_flags.csv
└── property_scores.csv
```

These outputs support manual review and validation.

---

# Common Installation Issues

## Python Version

Check:

```bash
python --version
```

Recommended:

```text
Python 3.10+
```

---

## Missing Packages

Install requirements again:

```bash
pip install -r requirements.txt
```

---

## Encoding Errors

Input files should preferably use:

```text
UTF-8
```

or

```text
UTF-8-SIG
```

The framework includes fallback encoding support for common legacy formats.

---

## Missing Agency Configuration

Error:

```text
Missing configuration file
```

Verify:

```text
config/agencies/
```

contains the corresponding:

```text
agency_<name>.json
```

file.

---

# Updating the Framework

Pull the latest changes:

```bash
git pull
```

Update dependencies:

```bash
pip install -r requirements.txt --upgrade
```

---

# Next Steps

After installation:

1. Read the architecture overview:

```text
docs/architecture.md
```

2. Review framework configuration:

```text
docs/configuration.md
```

3. Explore the orchestrator:

```text
docs/orchestrator.md
```

4. Review module documentation:

```text
docs/modules/
```

5. Run a dry run before processing production data.

---

# Recommended Citation

If you use this framework in research, please cite the associated dataset, software release, Zenodo archive, and related publications when available.
