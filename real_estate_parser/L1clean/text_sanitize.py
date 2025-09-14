
#!/usr/bin/env python3
"""
ext_sanitize.py t— Pre-enrichment CSV sanitizer for listings & FX files.

Goals
-----
• Enforce UTF-8, normalize Unicode (NFKC), fix punctuation (quotes/dashes/ellipsis), remove NBSP/zero-width.
• Optional diacritics stripping (produce *_key accentless columns).
• Canonicalize currencies (symbols/aliases → ISO code), headers, and dates (→ YYYY-MM-DD).
• Validate & clean numeric amounts (strip thousands separators / symbols → dot-decimal).
• FX profile: enforce headers [date,base,quote,rate(,source)], validate rate numeric & pair codes.
• Listings profile: normalize currency & date columns; optionally clean an amount column.

Usage examples
--------------
# FX file
python text_sanitize.py \
  --in FXrate/fx_HNL_USD_raw.csv \
  --out FXrate/fx_HNL_USD.csv \
  --profile fx \
  --strip-diacritics false

# Listings file (clean currency/date and produce price_clean)
python text_sanitize.py \
  --in input/listings_raw.csv \
  --out input/listings_clean.csv \
  --profile listings \
  --currency-col currency --date-col date \
  --amount-col price --amount-out price_clean

Notes
-----
• No third-party deps. Pure stdlib.
• Logs a compact summary of fixes and row-level issues to stderr.
"""
from __future__ import annotations
import argparse
import csv
import io
import re
import sys
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Iterable, List, Optional, Tuple

# ---------------------------- Unicode & punctuation helpers ----------------------------
NBSP = "\u00A0"
ZW_CHARS = [
    "\u200B", "\u200C", "\u200D", "\u200E", "\u200F",  # zero-width chars
    "\uFEFF",  # BOM inside text
]

PUNCT_MAP = {
    "\u2018": "'",  # left single quote
    "\u2019": "'",  # right single quote
    "\u201B": "'",  # single high-reversed-9 quotation mark
    "\u201C": '"',   # left double quote
    "\u201D": '"',   # right double quote
    "\u201E": '"',   # low double quote
    "\u2032": "'",  # prime → apostrophe
    "\u2013": "-",  # en dash
    "\u2014": "-",  # em dash
    "\u2212": "-",  # minus sign → hyphen
    "\u2026": "...", # ellipsis
}

CURRENCY_MAP: Dict[str, str] = {
    "$": "USD", "US$": "USD", "usd": "USD", "Usd": "USD",
    "€": "EUR", "eur": "EUR",
    "£": "GBP", "gbp": "GBP",
    "¥": "JPY", "jpy": "JPY",
    # Honduras Lempira aliases
    "L": "HNL", "L.": "HNL", "Lps": "HNL", "Lps.": "HNL", "HNL": "HNL", "hnl": "HNL",
}

ISO_CUR_RX = re.compile(r"^[A-Z]{3}$")
NON_DIGIT_RX = re.compile(r"[^0-9\.-]")  # for amount cleaning when symbols/commas appear
MULTI_SPACE_RX = re.compile(r"\s+")

# Accept common date formats to coerce → YYYY-MM-DD
DATE_FORMATS = (
    "%Y-%m-%d",
    "%Y/%m/%d",
    "%d/%m/%Y",
    "%m/%d/%Y",
    "%y-%m-%d",
    "%d-%m-%Y",
    "%m-%d-%Y",
    "%m/%d/%y",
    "%d/%m/%y",
)

@dataclass
class SanitizeConfig:
    profile: str  # 'fx' or 'listings'
    currency_col: str = "currency"
    date_col: str = "date"
    amount_col: Optional[str] = None
    amount_out: Optional[str] = None  # if None and amount_col set, will overwrite
    strip_diacritics: bool = False
    accentless_cols: Tuple[str, ...] = tuple()  # columns for which to add *_key accentless
    on_invalid_row: str = "skip"  # 'skip' | 'error' | 'nulls'

@dataclass
class SanitizeStats:
    rows_in: int = 0
    rows_out: int = 0
    dropped: int = 0
    fixed_quotes: int = 0
    fixed_dashes: int = 0
    removed_zw: int = 0
    replaced_nbsp: int = 0
    normalized_whitespace: int = 0
    normalized_dates: int = 0
    normalized_currency: int = 0
    cleaned_amounts: int = 0
    header_rewrites: int = 0
    errors: int = 0
    messages: List[str] = field(default_factory=list)

    def log(self, msg: str) -> None:
        self.messages.append(msg)

# ---------------------------- Core transformations ----------------------------

def nfkc_normalize(s: str) -> str:
    return unicodedata.normalize("NFKC", s)

def remove_zero_width(s: str, stats: Optional[SanitizeStats] = None) -> str:
    old = s
    for ch in ZW_CHARS:
        s = s.replace(ch, "")
    if stats and s != old:
        stats.removed_zw += 1
    return s

def fix_punctuation(s: str, stats: Optional[SanitizeStats] = None) -> str:
    old = s
    for k, v in PUNCT_MAP.items():
        s = s.replace(k, v)
    if stats:
        # count roughly
        if any(q in old for q in ("\u2018", "\u2019", "\u201B", "\u201C", "\u201D", "\u201E")):
            stats.fixed_quotes += 1
        if any(d in old for d in ("\u2013", "\u2014", "\u2212")):
            stats.fixed_dashes += 1
    return s

def normalize_spaces(s: str, stats: Optional[SanitizeStats] = None) -> str:
    old = s
    if NBSP in s:
        s = s.replace(NBSP, " ")
        if stats:
            stats.replaced_nbsp += 1
    s = MULTI_SPACE_RX.sub(" ", s).strip()
    if stats and s != old:
        stats.normalized_whitespace += 1
    return s

def strip_diacritics(s: str) -> str:
    # NFD then drop combining marks
    nfd = unicodedata.normalize("NFD", s)
    return "".join(ch for ch in nfd if not unicodedata.combining(ch))

def canonicalize_currency(token: str) -> Optional[str]:
    if not token:
        return None
    t = token.strip()
    t = nfkc_normalize(t)
    t = fix_punctuation(t)
    t = t.replace(" ", "")
    # Direct ISO code
    up = t.upper()
    if ISO_CUR_RX.match(up):
        return up
    return CURRENCY_MAP.get(t, CURRENCY_MAP.get(up, up if ISO_CUR_RX.match(up) else None))

# Robust date normalization

def normalize_date(token: str) -> Optional[str]:
    if token is None:
        return None
    raw = token.strip()
    if not raw:
        return None
    raw = nfkc_normalize(raw)
    raw = fix_punctuation(raw)
    raw = raw.replace(".", "-")  # e.g., 2015.10.28 → 2015-10-28
    raw = raw.replace(" ", "-")  # collapse spaces in some weird exports
    # common cases first
    for fmt in DATE_FORMATS:
        try:
            dt = datetime.strptime(raw, fmt)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            pass
    # try to rescue with regex (pick numbers in plausible order)
    m = re.findall(r"\d+", raw)
    if len(m) >= 3:
        # heuristic: if first number has 4 digits → year-first
        if len(m[0]) == 4:
            y, a, b = m[0], m[1], m[2]
        else:
            # assume mm/dd/yy or dd/mm/yy — ambiguous; prefer month-first for US data
            a, b, y = m[0], m[1], m[2]
            if len(y) == 2:
                y = ("20" if int(y) < 70 else "19") + y
        try:
            dt = datetime(int(y), int(a), int(b))
            return dt.strftime("%Y-%m-%d")
        except Exception:
            return None
    return None

# Amount cleaning: keep digits, optional leading minus, and one dot

def clean_amount(token: str) -> Optional[str]:
    if token is None:
        return None
    s = nfkc_normalize(token)
    s = fix_punctuation(s)
    s = s.replace(",", "")  # drop thousands separators
    s = s.replace(" ", "")
    # remove any currency symbols/letters
    s = re.sub(r"[A-Za-z$€£¥₤₡₱R$₽₺₭₦₴₪₫₸₿]", "", s)
    # keep only digits, minus, dot
    s = NON_DIGIT_RX.sub("", s)
    # validate pattern
    if not s or s in {"-", ".", "-."}:
        return None
    # collapse multiple dots to first
    if s.count(".") > 1:
        parts = s.split(".")
        s = parts[0] + "." + "".join(parts[1:])
    return s

# ---------------------------- Row sanitizers ----------------------------

def canonicalize_headers(headers: List[str], cfg: SanitizeConfig, stats: SanitizeStats) -> List[str]:
    orig = headers[:]
    H = [normalize_spaces(nfkc_normalize(h)) for h in headers]
    # common FX header rewrites
    if cfg.profile == "fx":
        mapping = {"from": "base", "to": "quote"}
        H = [mapping.get(h.lower(), h) for h in H]
    if H != orig:
        stats.header_rewrites += 1
    return H


def sanitize_fx_row(row: Dict[str, str], stats: SanitizeStats) -> Optional[Dict[str, str]]:
    # date
    d = normalize_date(row.get("date", ""))
    if not d:
        stats.errors += 1
        return None
    row["date"] = d
    # base / quote
    base = row.get("base", "").strip().upper()
    quote = row.get("quote", "").strip().upper()
    if not ISO_CUR_RX.match(base) or not ISO_CUR_RX.match(quote):
        stats.errors += 1
        return None
    row["base"], row["quote"] = base, quote
    # rate
    rate_raw = clean_amount(row.get("rate", ""))
    if rate_raw is None:
        stats.errors += 1
        return None
    row["rate"] = rate_raw
    # source (optional): cleanup whitespace/punct
    if "source" in row and row["source"] is not None:
        row["source"] = normalize_spaces(fix_punctuation(nfkc_normalize(row["source"])))
    return row


def sanitize_listings_row(row: Dict[str, str], cfg: SanitizeConfig, stats: SanitizeStats) -> Optional[Dict[str, str]]:
    # currency
    if cfg.currency_col in row:
        cur = canonicalize_currency(row.get(cfg.currency_col, ""))
        if cur:
            if row.get(cfg.currency_col) != cur:
                stats.normalized_currency += 1
            row[cfg.currency_col] = cur
        else:
            # leave as-is; downstream may decide
            pass
    # date
    if cfg.date_col in row:
        nd = normalize_date(row.get(cfg.date_col, ""))
        if nd:
            if nd != row.get(cfg.date_col):
                stats.normalized_dates += 1
            row[cfg.date_col] = nd
    # amount
    if cfg.amount_col and cfg.amount_col in row:
        cleaned = clean_amount(row.get(cfg.amount_col, ""))
        if cleaned is not None:
            out_col = cfg.amount_out or cfg.amount_col
            if row.get(out_col) != cleaned:
                stats.cleaned_amounts += 1
            row[out_col] = cleaned
    # accentless keys
    for col in cfg.accentless_cols:
        if col in row and row[col] is not None:
            ak = strip_diacritics(nfkc_normalize(row[col])).upper()
            row[f"{col}_key"] = normalize_spaces(fix_punctuation(remove_zero_width(ak)))
    return row

# ---------------------------- File processing ----------------------------

def sanitize_text_cell(value: Optional[str], stats: SanitizeStats) -> Optional[str]:
    if value is None:
        return None
    s = str(value)
    before = s
    s = nfkc_normalize(s)
    s = remove_zero_width(s, stats)
    s = fix_punctuation(s, stats)
    s = normalize_spaces(s, stats)
    # Optionally we could do more, but keep generic
    return s


def process_csv(in_path: str, out_path: str, cfg: SanitizeConfig) -> SanitizeStats:
    stats = SanitizeStats()
    # Read with replacement for bad bytes, assume input may not be utf-8
    with io.open(in_path, "r", encoding="utf-8", errors="replace", newline="") as f_in:
        reader = csv.DictReader(f_in)
        headers = canonicalize_headers(reader.fieldnames or [], cfg, stats)
        rows_out: List[Dict[str, str]] = []
        for row in reader:
            stats.rows_in += 1
            # normalize every string cell first
            row = {h: sanitize_text_cell(row.get(h), stats) for h in reader.fieldnames}
            # re-map headers if we rewrote
            if headers != (reader.fieldnames or []):
                row = {headers[i]: row.get((reader.fieldnames or [])[i]) for i in range(len(headers))}
            # profile-specific sanitation
            try:
                if cfg.profile == "fx":
                    row2 = sanitize_fx_row(row, stats)
                else:
                    row2 = sanitize_listings_row(row, cfg, stats)
            except Exception as e:
                stats.errors += 1
                row2 = None
            # handle invalid rows
            if row2 is None:
                if cfg.on_invalid_row == "error":
                    raise RuntimeError(f"Invalid row at input index {stats.rows_in}: {row}")
                elif cfg.on_invalid_row == "skip":
                    stats.dropped += 1
                    continue
                elif cfg.on_invalid_row == "nulls":
                    rows_out.append({h: row.get(h) for h in headers})
                    stats.rows_out += 1
                    continue
            rows_out.append(row2)
            stats.rows_out += 1

    # Write UTF-8 with normalized headers
    with io.open(out_path, "w", encoding="utf-8", newline="") as f_out:
        writer = csv.DictWriter(f_out, fieldnames=headers, extrasaction="ignore")
        writer.writeheader()
        for r in rows_out:
            writer.writerow(r)

    # Summary to stderr
    summary = (
        f"Sanitized {stats.rows_in} → {stats.rows_out} rows; dropped={stats.dropped}; "
        f"header_rewrites={stats.header_rewrites}; quotes={stats.fixed_quotes}; dashes={stats.fixed_dashes}; "
        f"ZW_removed={stats.removed_zw}; nbsp_fixed={stats.replaced_nbsp}; ws_norm={stats.normalized_whitespace}; "
        f"dates_norm={stats.normalized_dates}; curr_norm={stats.normalized_currency}; amt_clean={stats.cleaned_amounts}; "
        f"errors={stats.errors}"
    )
    print(summary, file=sys.stderr)
    return stats

# ---------------------------- CLI ----------------------------

def parse_args(argv: Optional[Iterable[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Sanitize CSV text for FX or listings profiles.")
    p.add_argument("--in", dest="input_csv", required=True, help="Input CSV path")
    p.add_argument("--out", dest="output_csv", required=True, help="Output CSV path (UTF-8)")
    p.add_argument("--profile", choices=["fx", "listings"], required=True, help="Sanitization profile")
    p.add_argument("--currency-col", default="currency", help="Listings: currency column name")
    p.add_argument("--date-col", default="date", help="Listings/FX: date column name")
    p.add_argument("--amount-col", default=None, help="Listings: amount column to clean")
    p.add_argument("--amount-out", default=None, help="Listings: name of cleaned amount column (default: overwrite amount-col)")
    p.add_argument("--strip-diacritics", dest="strip_diacritics", default="false", choices=["true", "false"], help="Apply diacritics stripping to *_key columns only (raw preserved)")
    p.add_argument("--accentless-col", dest="accentless_cols", action="append", default=[], help="Listings: add accentless *_key for this column (can be passed multiple times)")
    p.add_argument("--on-invalid-row", choices=["skip", "error", "nulls"], default="skip", help="Policy when a row cannot be sanitized")
    return p.parse_args(argv)


def main(argv: Optional[Iterable[str]] = None) -> None:
    args = parse_args(argv)
    cfg = SanitizeConfig(
        profile=args.profile,
        currency_col=args.currency_col,
        date_col=args.date_col,
        amount_col=args.amount_col,
        amount_out=args.amount_out,
        strip_diacritics=(args.strip_diacritics == "true"),
        accentless_cols=tuple(args.accentless_cols or []),
        on_invalid_row=args.on_invalid_row,
    )
    stats = process_csv(args.input_csv, args.output_csv, cfg)

if __name__ == "__main__":
    main()
