#   .py
import re
import pandas as pd

# ---------- Shared patterns ----------
CURRENCY_PREFIXES = [r"US\$", r"AU\$", r"CA\$", r"C\$", r"A\$", r"R\$", r"\$", r"€", r"£", r"L"]
CURRENCY_PREFIX_RE = r"(?:" + "|".join(CURRENCY_PREFIXES) + r")"

# "1hab" / "1hab." / "1 habitación" / "3dorms" / "2br" / "2 beds"
BED_TOKEN_RE = r"(?:hab(?:itaci[oó]n)?|hab\.?|dorms?|dorm|br|bed(?:room)?s?)"

# ---------- (A) Normalize Lempira variants ----------
LEMPIRA_NORM_RE = re.compile(r"\bL(?:ps\.?|\.?)\b", re.IGNORECASE)
def cm_norm_lempira(s: pd.Series, col="listing_text") -> pd.Series:
    """Lps, Lps., L.  -> L (idempotent)"""
    return s[col].fillna("").str.replace(LEMPIRA_NORM_RE, "L", regex=True)

# ---------- (B) Insert space between bedrooms and currency ----------
GLUE_BED_CUR_RE = re.compile(
    rf"""
    (?P<br>\b\d+\s*{BED_TOKEN_RE}\b)    # e.g., 1hab / 2 dorm / 3br
    (?P<cur>{CURRENCY_PREFIX_RE})(?=\s*\d)  # currency glued right after
    """,
    re.IGNORECASE | re.VERBOSE,
)
def cm_space_bedrooms_currency(s: pd.Series, col="listing_text") -> pd.Series:
    def _repl(m):
        br = m.group("br")
        br = re.sub(rf"(\d+)\s*({BED_TOKEN_RE})", r"\1 \2", br, flags=re.IGNORECASE)
        return f"{br} {m.group('cur')}"
    return s[col].fillna("").str.replace(GLUE_BED_CUR_RE, _repl, regex=True)

# ---------- (C) Insert a space BEFORE a currency stuck to a word ----------
PRE_WORD_CURRENCY_RE = re.compile(
    rf"(?P<prev>[\w\u00C0-\u024F])(?P<cur>{CURRENCY_PREFIX_RE})", re.UNICODE
)
def cm_space_before_currency(s: pd.Series, col="listing_text") -> pd.Series:
    return s[col].fillna("").str.replace(PRE_WORD_CURRENCY_RE, r"\g<prev> \g<cur>", regex=True)

# ---------- (D) Optional: make a clean price snippet column for your extractor ----------
PRICE_SNIPPET_RE = re.compile(
    rf"(?P<cur>{CURRENCY_PREFIX_RE})\s*(?P<amt>\d{{1,3}}(?:[.,]\d{{3}})+|\d+)(?:[.,]\d{{2}})?",
    re.IGNORECASE,
)
def cm_make_price_snippet(df: pd.DataFrame, src="listing_text", dst="raw_price_text") -> pd.DataFrame:
    def _extract(txt: str):
        m = PRICE_SNIPPET_RE.search(txt or "")
        if not m: return None
        # ensure single space between currency and number
        return f"{m.group('cur')} " + (txt[m.start('amt'): m.end()]).lstrip()
    df = df.copy()
    df[dst] = df[src].fillna("").map(_extract)
    return df

# ---------- (E) Optional: bedrooms int for convenience / QA ----------
BEDROOM_RE = re.compile(rf"\b(?P<n>\d+)\s*{BED_TOKEN_RE}\b", re.IGNORECASE)
def cm_parse_bedrooms(df: pd.DataFrame, src="listing_text", dst="bedrooms") -> pd.DataFrame:
    def _parse(txt: str):
        m = BEDROOM_RE.search(txt or "")
        if not m: return None
        try: return int(m.group("n"))
        except: return None
    df = df.copy()
    df[dst] = df[src].fillna("").map(_parse)
    return df
