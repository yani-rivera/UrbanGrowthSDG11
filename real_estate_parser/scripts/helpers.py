# scripts/helpers.py
DEFAULT_PIPELINE_VERSION = "v1.0"
# scripts/helpers.py


from decimal import Decimal, InvalidOperation
import os, re, json, csv
from pathlib import Path
from datetime import datetime
import unicodedata

# --- CSV schema (units included) ---
# scripts/helpers.py
FIELDNAMES = [
    "Listing ID","title","neighborhood","bedrooms","bathrooms",
    "AT","AT_unit","area","area_unit","area_m2",   # ← add normalized m²
    "price","currency","transaction","property_type",
    "agency","date","notes"
    "source_type","ingestion_id","pipeline_version" ,  # keep if you want provenance
]

_UNIT_PRICE = re.compile(
    r'(US\$|\$|L\.?)\s?\d+(?:[\.,]\d+)?\s?(?:x\s*)?(?:vrs²|vrs2|vr2|m²|m2|mt2)\b',
    re.I
)



# -----------------------------------------------------------------------------
# Prefile helpers
# -----------------------------------------------------------------------------

#====== to write prefile

def _dt(date_str: str) -> datetime:
    """Parse date in YYYY-MM-DD, YYYYMMDD, or YYYY/MM/DD."""
    for fmt in ("%Y-%m-%d", "%Y%m%d", "%Y/%m/%d"):
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            pass
    raise ValueError(f"Bad date: {date_str}")




def write_prefile(registry_path, input_file, rows, output_root="output"):
    input_file = Path(input_file)

    # infer agency + date from the *input file*
    agency_key = infer_agency(input_file)              # e.g. "agency_propiedades"
    base       = agency_key.replace("agency_", "")     # "propiedades"
    date_str   = infer_date(input_file).replace("-", "")  # "20101126"
    year       = date_str[:4]
    base=base.split("_")[0]
    # directory casing from registry
    reg   = json.loads(Path(registry_path).read_text(encoding="utf-8"))
    entry = (reg.get("agencies") or {}).get(agency_key, {})
    style = str(entry.get("dir_case", "lower")).lower()
    if style == "upper":
        Agency = base.upper()
    elif style == "mixed":
        Agency = entry.get("Agency (in-file)", base)
    else:
        Agency = base.capitalize()  # default neat dir name

    # build the canonical path (no template, no filename in directory)
    out_path = Path(output_root) / Agency / "pre" / year / f"pre_{base.lower()}_{date_str}.txt"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # one-time sanity print (remove after confirming)
    #print("[prefile ctx] Agency=", Agency, " base=", base, " date=", date_str, " ->", out_path)

    with out_path.open("w", encoding="utf-8", newline="\n") as f:
        for r in rows:
            f.write((r or "").rstrip("\n") + "\n")
    return out_path



def _normalize_num_token(num_str: str) -> float | None:
    """
    Robustly convert strings like '1,700.00', '1.700,00', '1 700', '1700' to float.
    Heuristic:
      - If both ',' and '.' appear: whichever comes last is the decimal separator.
      - If only ',' appears and looks like thousands groups (xxx,xxx[,xxx]) -> remove commas.
      - Otherwise replace a single ',' with '.' if it looks like decimal.
    """
    if not num_str:
        return None
    s = num_str.strip().replace(" ", "")
    has_comma = "," in s
    has_dot = "." in s

    if has_comma and has_dot:
        # whichever occurs last is the decimal separator
        if s.rfind(",") > s.rfind("."):
            # European style: 1.800,50 -> 1800.50
            s = s.replace(".", "")
            s = s.replace(",", ".", 1)
        else:
            # US style: 1,800.50 -> 1800.50
            s = s.replace(",", "")
    elif has_comma and not has_dot:
        parts = s.split(",")
        if all(len(p) == 3 for p in parts[1:-1]) and len(parts[-1]) in (3, 0):
            s = "".join(parts)            # 1,234,567 -> 1234567
        else:
            s = s.replace(",", ".", 1)    # 12,5 -> 12.5

    try:
        return float(s)
    except Exception:
        return None


def strip_per_unit_prices(s: str) -> str:
    """Remove per-unit amounts like 'US$ 4.00 vrs²' or '$ 10 m2' from text."""
    return _UNIT_PRICE.sub('', s)

def normalize_currency_spacing(s: str) -> str:
    """Ensure a space between currency and digits: 'US$45000' -> 'US$ 45000'."""
    return re.sub(r'(US\$|\$|L\.?)(\d)', r'\1 \2', s)

 
def format_listing_row(parsed: dict, final_line: str, listing_no: int,
                       *, source_type: str = "", ingestion_id: str = "",
                       pipeline_version: str = "") -> dict:
        return {
        "Listing ID": listing_no,
        "title": parsed.get("title",""),
        "neighborhood": parsed.get("neighborhood",""),
        "bedrooms": parsed.get("bedrooms",""),
        "bathrooms": parsed.get("bathrooms",""),

        # land size
        "AT": parsed.get("AT",""),
        "AT_unit": parsed.get("AT_unit",""),

        # built/general area
        "area": parsed.get("area",""),
        "area_unit": parsed.get("area_unit",""),
        "area_m2": parsed.get("area_m2",""),   # ← add normalized m²

        # price
        "price": parsed.get("price",""),
        "currency": parsed.get("currency",""),

        "transaction": parsed.get("transaction",""),
        "property_type": parsed.get("property_type",""),
        "agency": parsed.get("agency",""),
        "date": parsed.get("date",""),

        "notes": final_line,  # second-preprocess result
        "source_type": source_type,
        "ingestion_id": ingestion_id,
        "pipeline_version": pipeline_version,
    }



def build_release_row(parsed: dict, final_line: str, i: int, *, agency: str, date: str) -> dict:
    #at = parsed.get("area_terrain_v2") or ""
    #ac = parsed.get("area_construction_m2") or ""
    return {
        "Listing ID": i,
        "title": final_line[:60],
        "neighborhood": parsed.get("neighborhood",""),
        "bedrooms": parsed.get("bedrooms",""),
        "bathrooms": parsed.get("bathrooms",""),
     # land size
        "AT": parsed.get("AT",""),
        "AT_unit": parsed.get("AT_unit",""),

        # built/general area
        "area": parsed.get("area",""),
        "area_unit": parsed.get("area_unit",""),
        "area_m2": parsed.get("area_m2",""),   # ← add normalized m²

        "price": parsed.get("price",""),
        "currency": parsed.get("currency",""),
        "transaction": parsed.get("transaction",""),
        "property_type": parsed.get("property_type",""),
        "agency": parsed.get("agency","") or agency,
        "date": parsed.get("date","") or date,
        "raw": final_line,
    }
# assert len(FIELDNAMES) == len(set(FIELDNAMES))
# --- Utilities used by parsers ---

def infer_agency(config_path: str, default: str = "Agency") -> str:
    """Prefer agency name inside the config JSON; else derive from filename."""
    try:
        with open(config_path, encoding="utf-8") as fh:
            cfg = json.load(fh)
        if isinstance(cfg, dict) and cfg.get("agency"):
            return str(cfg["agency"])
    except Exception:
        pass
    # Fallback: config/agency_casabianca.json -> Casabianca
    stem = os.path.splitext(os.path.basename(config_path))[0]
    if stem.lower().startswith("agency_"):
        stem = stem.split("_", 1)[1]
    return stem.title() if stem else default

_DATE_PAT = re.compile(r"(20\d{2})[-_]?([01]\d)[-_]?([0-3]\d)")

def infer_date(file_path: str, default: str = "") -> str:
    """Find YYYYMMDD or YYYY-MM-DD in filename; return 'YYYY-MM-DD'."""
    m = _DATE_PAT.search(os.path.basename(file_path))
    if not m:
        return default
    y, mo, d = m.groups()
    return f"{y}-{mo}-{d}"

# --- Numbered-listings prefile (shared by all agencies) -----------------------


# Match only real bullets at line start: 1. TEXT / 12) TEXT / 7.- TEXT
# Avoid prices like 1.100 or 1,000 by requiring a letter after the bullet.
# Match bullets at line start:
# 1.XXX   12) XXX   7.-XXX   3. XXX   45.- XXX
# (no false matches for prices because we anchor at ^ and require a LETTER next)
_BULLET_RE = re.compile(
    r"""
    ^(?P<lead>\s*)           # leading spaces
    (?P<num>\d{1,3})         # 1–3 digits
    \s*                      # optional spaces between number and delimiter
    (?:[.)]|[.]-)            # ')' or '.' or '.-'
    \s*                      # <-- allow zero or more spaces after delimiter
    (?=[A-Za-zÁÉÍÓÚÜÑ])      # next visible char must be a letter
    """,
    re.VERBOSE
)
#======




def make_prefile_numbered(input_path: str, agency: str,year: str, tmp_root: str = "output") -> str:
    """
    Create a temp 'prefile' where numbered bullets are rewritten as '* '.
    Returns the new path: output/<Agency>/pre/<agency>/pre_<basename>.txt
    """
    base = os.path.basename(input_path)
    base="pre_"+base
    pre_dir  = os.path.join(tmp_root, agency, "pre", year)
    os.makedirs(pre_dir, exist_ok=True)
    pre_path = os.path.join(pre_dir, base)

    os.makedirs(pre_dir, exist_ok=True)


    replaced = 0
    with open(input_path, "r", encoding="utf-8", errors="ignore") as fi, \
         open(pre_path,  "w", encoding="utf-8", errors="ignore") as fo:
        for ln in fi:
            new = _BULLET_RE.sub(r"\g<lead>* ", ln, count=1)
            if new != ln:
                replaced += 1
            fo.write(new)

    print(f"[masq] → {pre_path}  bullets_replaced={replaced}")
    return pre_path



def make_prefile_star(input_path: str, agency: str, delimiter: str, year: str, tmp_root: str = "output") -> str:
    """
    Normalize listing delimiters: replace the given delimiter (single char) at the start of a line
    with the canonical '* ' (star + space).

    Output path: output/<Agency>/pre/<year>/<file>
    Example: input='data/raw/Inverprop/2015/inverprop_20151028.txt'
             output='output/Inverprop/pre/2015/inverprop_20151028.txt'

    Args:
        input_path: path to raw TXT file
        agency: agency code (e.g., "Inverprop")
        delimiter: the actual listing delimiter character to replace (e.g., '*', '-', '#')
        year: 4-digit year string (e.g., "2015")
        tmp_root: root output directory (default "output")

    Returns:
        Path to the new preprocessed file
    """
    if len(delimiter) != 1:
        raise ValueError("delimiter must be a single character")

    base = os.path.basename(input_path)
    base="pre_"+base
    pre_dir = os.path.join(tmp_root, agency, "pre", year)
    os.makedirs(pre_dir, exist_ok=True)
    pre_path = os.path.join(pre_dir, base)  # same filename, not prefixed with "pre_"

    # Regex: line start (^) + optional whitespace + delimiter + optional whitespace
    bullet_re = re.compile(rf"(?m)^(?P<lead>\s*){re.escape(delimiter)}\s*")

    replaced = 0
    with open(input_path, "r", encoding="utf-8", errors="ignore") as fi, \
         open(pre_path, "w", encoding="utf-8", errors="ignore") as fo:
        for ln in fi:
            new, n = bullet_re.subn(r"\g<lead>* ", ln, count=1)
            if n > 0:
                replaced += n
            fo.write(new)

    print(f"[make_prefile_star] {input_path} → {pre_path} delimiter='{delimiter}' bullets_replaced={replaced}")
    return pre_path




# Small QC counters you can print during debug
def count_numbered_bullets(path: str) -> int:
    rx = re.compile(r"^\s*\d{1,3}\s*(?:[.)]|[.]-)\s+(?=[A-Za-zÁÉÍÓÚÜÑ])")
    n = 0
    with open(path, encoding="utf-8", errors="ignore") as fh:
        for ln in fh:
            if rx.match(ln): n += 1
    return n

def count_star_bullets(path: str) -> int:
    rx = re.compile(r"^\s*\*\s+\S")
    n = 0
    with open(path, encoding="utf-8", errors="ignore") as fh:
        for ln in fh:
            if rx.match(ln): n += 1
    return n

# Keep bullet for human RAW, strip for parsing
_BULLET_STRIP = re.compile(r"^\s*([*\-•])\s+")

def split_raw_and_parse_line(ln: str):
    s = (ln or "").lstrip()
    raw_line = s
    if s.startswith("* "): s = s[2:]
    elif s.startswith("- "): s = s[2:]
    return raw_line, s

