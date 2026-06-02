# Dependencies

The SDG-11 Housing Data Reconstruction Framework was intentionally designed to minimize external dependencies and maximize portability.

## Core Dependencies

| Package | Purpose |
|----------|----------|
| pandas | Tabular data processing and aggregation |
| numpy | Numerical operations and area calculations |
| PyYAML | Configuration-driven property classification and parsing rules |

Install:

```bash
pip install -r requirements.txt
```

## Optional Dependencies

These packages are only required for notebooks and exploratory analysis.

| Package | Purpose |
|----------|----------|
| jupyter | Interactive notebooks |
| matplotlib | QC visualizations and boxplots |
| openpyxl | Excel import/export support |

Install:

```bash
pip install -r requirements-dev.txt
```

## Standard Library Modules

The framework also uses Python standard library modules including:

- argparse
- ast
- bisect
- csv
- fnmatch
- glob
- hashlib
- io
- json
- os
- random
- re
- string
- subprocess
- sys
- unicodedata
- warnings

No additional installation is required for these modules.