import re

PRICE_ANY   = re.compile(r'(?:L\.|LPS\.|\$)\s*\d', re.I)
PRICE_NEAR  = re.compile(r'(?:L\.|LPS\.|\$)\s*\d{1,3}(?:,\d{3})*(?:\.\d+)?', re.I)
BED_HINT    = re.compile(r'\b\d+\s*(hab|habitaciones|cuartos|dormitorios)\b', re.I)
ELLIPSES    = re.compile(r'\.\.\.')
DECIMAL_DOT = re.compile(r'(?<=\d)\.(?=\d)')
ABBR_DOT    = re.compile(r'\b(?:col|res|bo)\.$', re.I)

CONT_PREFIXES = tuple([
    "y ", "e ", "incluye", "con ", "sin ", "garaje", "garages", "estacionamiento",
    "cisterna", "area ", "área ", "cuarto", "cocina", "comedor", "sala",
    "vista", "terraza", "patio", "jardín", "jardin", "seguridad", "mantenimiento",
    "amueblado", "semi-amueblada", "semi amueblada", "amueblada"
])

def _uppercase_ratio(s: str) -> float:
    letters = [c for c in s if c.isalpha()]
    return 0 if not letters else sum(1 for c in letters if c.isupper()) / len(letters)

def _collapse(s: str) -> str:
    return re.sub(r"\s+", " ", s.replace("\r", "\n").replace("\n", " ")).strip()

def _first_comma_pair(s: str, maxpos: int):
    m = re.search(r'^(.{1,' + str(maxpos) + r'}?),(.*)$', s.strip())
    return (m.group(1).strip(), m.group(2).lstrip()) if m else None

def _looks_like_head(content: str, maxpos=40, require_uc=True, lookahead=80) -> bool:
    s = content.strip()
    if not s:
        return False
    # reject obvious continuations
    low = s.lower()
    if low.startswith(CONT_PREFIXES):
        return False
    if PRICE_ANY.match(s):        # price at the start → continuation
        return False
    if s[:2].isdigit() and s[2:3] == ".":  # "1. ..." numbered paragraph
        return True

    pair = _first_comma_pair(s, maxpos)
    if not pair:
        return False

    left, right = pair
    # skip dots that are decimals/ellipses/abbrev when delimiter is DOT (not used here but safe)
    if ELLIPSES.search(left) or DECIMAL_DOT.search(left) or ABBR_DOT.search(left):
        return False

    # left should look like a neighborhood header
    if len(left.split()) < 1:
        return False
    if require_uc and _uppercase_ratio(left) < 0.55:
        return False

    # right should quickly look like a listing (price or bed hint soon)
    snippet = right[:lookahead]
    if not (PRICE_NEAR.search(snippet) or BED_HINT.search(snippet)):
        return False

    return True

def force_bulletize_oneline(lines, cfg: dict):
    """
    Collapse wrapped lines into single-line listings.
    New head only when _looks_like_head() is True.
    Always returns lines starting with '* '.
    """
    maxpos   = int(cfg.get("max_cue_pos", 40))
    require_uc = bool(cfg.get("require_uppercase", True))
    lookahead  = int(cfg.get("cue_lookahead_chars", 80))

    out, buf = [], []

    def flush():
        if not buf: return
        text = _collapse(" ".join(buf))
        if text:
            if not text.lstrip().startswith("* "):
                text = "* " + text.lstrip("* ").lstrip()
            out.append(text)
        buf.clear()

    for raw in lines:
        if not raw or not str(raw).strip():
            continue
        if str(raw).lstrip().startswith("#"):   # header/section -> flush and skip
            flush()
            continue

        s = str(raw).lstrip()
        # strip any leading OCR bullet for head test
        if s.startswith("* "):
            content = s[2:].lstrip()
        else:
            content = s

        is_head = _looks_like_head(content, maxpos=maxpos, require_uc=require_uc, lookahead=lookahead)

        if is_head and buf:
            flush()
            buf.append(content)  # store without bullet
        else:
            # Continuation: append raw content without the leading bullet if present
            buf.append(content)

    flush()

    # Final safety: one-line & bullet
    out = ["* " + _collapse(x).lstrip("* ").lstrip() if not x.lstrip().startswith("* ") else _collapse(x) for x in out]
    return out
