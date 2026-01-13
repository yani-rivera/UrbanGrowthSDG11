## Prerequisites

Before running the scripts in this project, ensure the following requirements are met.

---

### 1. Operating System

The workflow is platform-independent and can be used on:

- Linux
- macOS
- Windows

No operating-system-specific features are required.

---

### 2. Python

- **Python 3.8 or newer** (Python 3.9+ recommended)

Check if Python is installed:

```bash
python --version
```

or

```bash
python3 --version
```

If Python is not installed, download it from:  
https://www.python.org/downloads/

> Make sure Python is added to your system `PATH`.

---

### 3. Python Environment (Recommended)

Using a virtual environment is strongly recommended to avoid dependency conflicts.

Create a virtual environment:

```bash
python -m venv venv
```

Activate it:

- **macOS / Linux**
```bash
source venv/bin/activate
```

- **Windows**
```bash
venv\Scripts\activate
```

---

### 4. Python Packages

#### Core parser

The core newspaper parser relies **exclusively on the Python standard library**.  
No third-party Python packages are required.

#### Tabulation and CSV export (optional)

If tabulated output (CSV) is required, install:

```bash
pip install pandas
```

`pandas` is the **only external dependency** used for tabulation and aggregation.

---

### 5. Optional Tools (Not Required)

The following tools are optional and used only for preprocessing:

- PDF reader (to inspect source newspapers)
- OCR software (if converting scanned PDFs to text), for example:
  - Tesseract OCR
  - Adobe OCR
  - equivalent tools

OCR can be performed outside Python.  
The pipeline assumes **plain text (TXT)** as the stable input format.

---

### 6. Assumptions

- Input text files are UTF-8 encoded
- Each newspaper issue is processed independently
- No internet connection is required once data is captured

---

### Design Principle

> The workflow is designed to minimize dependencies and maximize long-term reproducibility.  
> Parsing logic uses only the Python standard library; third-party packages are introduced only when strictly necessary.
