#!/usr/bin/env python3
"""
Post‑tabulation multi‑listing detector & splitter — v3 (full patched)

Highlights vs earlier versions
------------------------------
- Robust Name:Price segmenter (handles bullets/UTF8, avoids char‑class '-' pitfalls).
- Currency‑anchored offer parsing that **never** splits inside thousands separators.
- Bedrooms splitting only when there are **≥2 counts** aligned with prices (e.g.,
  "1 y 2 hab ... L. 5,500 y L. 7,500 respectivamente").
- Mixed‑currency pair safeguard (e.g., "L1,900,000 / $140,000") ⇒ **1 child** by default
  unless configured otherwise.
- Manual gating: `--gate-expansion` uses a review column (default
  `CHILDREN_CANDIDATE`) so you approve rows before expansion.
- Candidate suggestions computed from **actual offers**, not rough heuristics.
- Per‑segment and per‑parent **deduplication** so duplicates don't slip through.
- Parquet‑safe dtype coercion on write.

Outputs
-------
- <outdir>/children.parquet and children.csv — expanded children (one per listing)
- <outdir>/parent_child_review.csv — QA summary w/ suggestions & previews
- <outdir>/parents_with_candidates.csv — (opt) editable parent rows + flags
- <outdir>/summary.json — basic run stats

Usage (example)
---------------
python post_tab_multi_split_v3.py \
  --input output/consolidated/universe_2010_2015_2020.csv \
  --outdir output/consolidated/splits_2020 \
  --notes-col notes \
  --id-col row_uid \
  --config config/config_splitter.json \
  --export-candidates \
  --gate-expansion
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

import pandas as pd

# ----------------------------- Default config ----------------------------- #
DEFAULT_CONFIG = {
    "bedroom_keywords": [
        "beds", "bed", "hab", "habitaciones", "cuartos", "dormitorios", "dorms", "recámaras", "alcobas"
    ],
    "usd_aliases": ["usd", "us$", "$", "uss", "udd", "u$d"],
    "hnl_aliases": ["lps.", "lps", "lempiras", "lempira"],
    "neighborhood_prefixes": ["res.", "res", "residencial", "colonia", "condominio", "torre", "edificio", "villas", "complejo"],
    "listing_types": ["casa", "casas", "apartamento", "apartamentos", "apartaestudio", "terreno", "lote", "local", "oficina", "bodega", "condo", "duplex"],
    "separators": [";", "|", "•", " - ", " y "],
    "ignore_before_colon": ["col.", "col", "colón"],
    "location_prepositions": ["en", "en la", "en el", "en residencial"],
    "range_keywords": ["desde", "de"],
    "range_connectors": ["hasta", "a", "–", "-", "al", "to"],
    "alignment_markers": ["respectivamente", "respectively", "en ese orden"],
    "availability_units": ["apartamentos", "apartamento", "residencias", "residencia", "villas", "villa", "unidades", "unidad"],
    "availability_markers": ["disponibilidad", "disponibles", "cupos"],
    "per_unit_markers": ["por apartamento", "c/u", "cada", "cada uno", "cada unidad"],
    "pair_connectors": [" y ", " e "],
    "split_multi_offers": True,
    "min_offers_to_split": 2,
    "split_multi_offers_when_mixed_currency": False,
    "dont_split_mixed_currency_max_offers": 2,
    "max_children_warn": 25
}

# ----------------------------- Regex patterns ----------------------------- #
RE_NBSP = re.compile(r"\u00A0|\u200B|\u200C|\u200D|\uFEFF")
RE_MULTI_SPACE = re.compile(r"[\t ]{2,}")
RE_SPACED_THOUSANDS = re.compile(r"(?<=\d),\s+(?=\d{3}\b)")
RE_CURRENCY_L = re.compile(r"\bL\s*\.?\s*")
RE_CURRENCY_USD = re.compile(r"US\$")

RE_NAME_COLON = re.compile(
    r"(?<!\bCol)\b([A-Za-zÁÉÍÓÚÜÑñ0-9' .-]{3,}?)\s*:\s*(?=(L\.|\$|\d))",
    re.IGNORECASE,
)
RE_MLS_ID = re.compile(r"\b(?:MLS|ID|REF)\s*[:#]?\s*[A-Z0-9-]{5,}\b", re.IGNORECASE)
RE_ADDR_ANCHOR = re.compile(
    r"(?:^|[;•(]\s*)(\d{1,6}\s+[A-Za-z0-9'.-]+\s+(?:ST|RD|AVE|AV|BLVD|LN|DR|CT|PL|WAY|HWY|TRL|PKWY)\b)",
    re.IGNORECASE,
)
RE_DATE = re.compile(r"\b(20(0\d|1\d|2[0-5]))[-/.](0[1-9]|1[0-2])[-/.](0[1-9]|[12]\d|3[01])\b")
RE_PRICE_TOKEN = re.compile(r"(?:L\.|\$)?\s?\d{1,3}(?:,\d{3})*(?:\.\d+)?")
RE_SLASH_OFFER_BURST = re.compile(
    r"(?:L\.|\$)?\s*\d{1,3}(?:,\d{3})*(?:\.\d+)?(?:\s*/\s*(?:L\.|\$)?\s*\d{1,3}(?:,\d{3})*(?:\.\d+)?){2,}")

# Name: Prices segmenter — robust (handles literal bullet and dashes safely)
RE_NAME_PRICES_SEGMENTER = re.compile(
    r"""
    (?:                             # a new segment starts after...
        ^                           #   start of string
      | [\s(\u2022*;\-]             #   or a separator (space, (, bullet, *, ;, -)
    )
    (?P<name>[A-Za-zÁÉÍÓÚÜÑñ0-9' .-]+?)   # the name
    \s*:\s*                         # colon separator
    (?P<prices>.+?)                 # the prices blob (lazy)
    (?=                             # until the next segment start...
        (?:[\s(\u2022*;\-][A-Za-zÁÉÍÓÚÜÑñ0-9' .-]+?\s*:)  # sep + next Name:
      | $                           # or end of string
    )
    """,
    re.IGNORECASE | re.DOTALL | re.VERBOSE,
)

# price with explicit currency (prefix $/L. or suffix 'usd')
RE_PRICE_WITH_CURRENCY = re.compile(r"""
    (?: (?:L\.|\$)\s*\d{1,3}(?:,\d{3})*(?:\.\d+)? )     # L. 1,200,000  or  $ 900.00
  | (?: \d{1,3}(?:,\d{3})*(?:\.\d+)?\s*usd\b )          # 900 usd
""", re.IGNORECASE | re.VERBOSE)

RE_PRICE_EXTRACT = re.compile(
    r"^\s*(?P<cur>L\.|\$)?\s*(?P<num>\d{1,3}(?:,\d{3})*(?:\.\d+)?|\d+(?:\.\d+)?)"
)

# ------------------------------ Helpers & Data classes -------------------- #
@dataclass
class Segment:
    name: str
    prices_blob: str
    start: int
    end: int
    bedrooms: Optional[int] = None


def _norm_price_token(p: str) -> str:
    # "$ 1,800.00" -> "$1800" ; "L. 1,400,000" -> "L1400000"
    p = (p or "").strip()
    p = p.replace(" ", "").replace(",", "").replace("L.", "L")
    m = re.search(r"^(L|\$)?(\d+(?:\.\d+)?)", p)
    if not m:
        return p.lower()
    cur = m.group(1) or ""
    num = m.group(2)
    if num.endswith(".00"):
        num = num[:-3]
    return f"{cur}{num}".lower()


# --------------------------- Helper functions ---------------------------- #

def load_config(config_path: Optional[Path]) -> dict:
    if config_path and Path(config_path).exists():
        with open(config_path, "r", encoding="utf-8") as f:
            user_cfg = json.load(f)
        cfg = DEFAULT_CONFIG.copy()
        cfg.update(user_cfg)
        return cfg
    return DEFAULT_CONFIG


def pre_normalize(text: str, cfg: dict) -> str:
    if text is None:
        return ""
    t = RE_NBSP.sub(" ", str(text))
    t = RE_SPACED_THOUSANDS.sub(",", t)
    t = RE_CURRENCY_L.sub("L.", t)
    t = RE_CURRENCY_USD.sub("$", t)
    for alias in cfg.get("usd_aliases", []):
        t = re.sub(rf"\b{re.escape(alias)}\b", "usd", t, flags=re.IGNORECASE)
    for alias in cfg.get("hnl_aliases", []):
        t = re.sub(rf"\b{re.escape(alias)}\b\.?", "L.", t, flags=re.IGNORECASE)
    t = RE_MULTI_SPACE.sub(" ", t)
    return t.strip()


def count_anchors(text: str) -> dict:
    return {
        "name_colon_count": len(RE_NAME_COLON.findall(text)),
        "mls_id_count": len(RE_MLS_ID.findall(text)),
        "addr_anchor_count": len(RE_ADDR_ANCHOR.findall(text)),
        "date_count": len(RE_DATE.findall(text)),
        "price_token_count": len(RE_PRICE_TOKEN.findall(text)),
        "slash_offer_burst": 1 if (RE_SLASH_OFFER_BURST.search(text) and len(RE_NAME_COLON.findall(text)) == 1) else 0,
    }


def is_multi_listing(anchor_counts: dict) -> bool:
    if anchor_counts["name_colon_count"] >= 2:
        return True
    if anchor_counts["mls_id_count"] >= 2:
        return True
    if anchor_counts["addr_anchor_count"] >= 2:
        return True
    if (
        anchor_counts["date_count"] >= 2
        and anchor_counts["price_token_count"] >= 2
        and anchor_counts["slash_offer_burst"] == 0
    ):
        return True
    return False


def extract_location(notes: str, cfg: dict) -> Optional[str]:
    preps = sorted(cfg.get("location_prepositions", []), key=len, reverse=True)
    if not preps:
        return None
    prep_rx = r"|".join([re.escape(p) for p in preps])
    m = re.search(rf"\b(?:{prep_rx})\s+(?P<name>[A-Za-zÁÉÍÓÚÜÑñ' .-]{{3,}})", notes, flags=re.IGNORECASE)
    if m:
        return m.group("name").strip()
    return None


# --- price tokenization (currency‑anchored, no split inside thousands) --- #
TOK_PRICE = re.compile(
    r"""
    (?P<cur>L\.|\$)?\s*
    (?P<num>\d{1,3}(?:,\d{3})*(?:\.\d+)?)
    (?:\s*(?P<suf>usd)\b)?
    """,
    re.IGNORECASE | re.VERBOSE,
)
TOK_SEP = re.compile(r"^\s*(/|,|;|\by\b|\be\b)\s*$", re.IGNORECASE)


def tokenize_offers(prices_blob: str) -> List[str]:
    """Extract a sequence of price tokens from `prices_blob` without breaking
    on thousands separators. Returns normalized tokens with currency inheritance.
    """
    if not prices_blob:
        return []
    matches = list(TOK_PRICE.finditer(prices_blob))
    if not matches:
        return []

    offers: List[str] = []
    last_cur: Optional[str] = None
    for i, m in enumerate(matches):
        cur = (m.group("cur") or "").strip()
        suf = (m.group("suf") or "").strip().lower()
        num = m.group("num").strip()
        if suf == "usd":
            cur = "$"
        if i > 0:
            gap = prices_blob[matches[i-1].end():m.start()]
            if not TOK_SEP.match(gap):
                if offers:
                    break
        if cur:
            last_cur = cur
        elif last_cur:
            cur = last_cur
        token = f"{cur} {num}".strip()
        offers.append(token)

    if not any(t.startswith(("$", "L.")) for t in offers):
        return []

    seen, uniq = set(), []
    for t in offers:
        k = _norm_price_token(t)
        if k not in seen:
            seen.add(k)
            uniq.append(t)
    return uniq


# ----------------------------- Segment extraction ------------------------- #

def segment_notes(notes: str, cfg: dict) -> List[Segment]:
    segs: List[Segment] = []

    # 1) Anchor-based Name:Prices
    for m in RE_NAME_PRICES_SEGMENTER.finditer(notes):
        name = m.group("name").strip()
        prices = m.group("prices").strip()
        if not RE_PRICE_WITH_CURRENCY.search(prices[:120]):
            continue
        segs.append(Segment(name=name, prices_blob=prices, start=m.start(), end=m.end()))
    if segs:
        return segs

    # 2) Bedroom variants (comma/and list + multiple prices) — requires ≥2 counts
    bedword_regex = r"|".join(cfg.get("bedroom_keywords", DEFAULT_CONFIG["bedroom_keywords"]))
    bed_pattern = re.compile(
        rf"(?P<counts>(?:\d+(?:\s*(?:,|/|–|-|\by\b|\be\b)\s*)\d+){{1,5}})\s*"
        rf"(?P<label>{bedword_regex})\b.*?"
        rf"(?P<prices>(?:\d{{1,3}}(?:,\d{{3}})*(?:\.\d+)?)(?:\s*(?:,|/|–|-|\by\b|\be\b)\s*\d{{1,3}}(?:,\d{{3}})*(?:\.\d+)?)+)"
        rf"\s*(?P<cur>usd|\$|L\.)?",
        re.IGNORECASE,
    )
    bm = bed_pattern.search(notes)
    if bm:
        counts = [int(c) for c in re.split(r"\s*(?:,|/|–|-|\by\b|\be\b)\s*", bm.group("counts")) if c.strip().isdigit()]
        price_tokens = re.split(r"\s*(?:,|/|–|-|\by\b|\be\b)\s*", bm.group("prices"))
        cur = (bm.group("cur") or "").strip()
        if cur and all(not re.search(r"(?:L\.|\$|usd)", p, re.I) for p in price_tokens):
            price_tokens = [f"{p} {cur}" for p in price_tokens]
        if len(counts) == len(price_tokens) and len(counts) >= 2:
            name = extract_location(notes, cfg) or ""
            for c, p in zip(counts, price_tokens):
                segs.append(Segment(name=name, prices_blob=p.strip(), start=0, end=0, bedrooms=c))
            return segs

    # 3) Range phrase fallback → two children (min/max)
    rk = r"|".join([re.escape(k) for k in cfg.get("range_keywords", DEFAULT_CONFIG["range_keywords"])])
    rc = r"|".join([re.escape(k) for k in cfg.get("range_connectors", DEFAULT_CONFIG["range_connectors"])])
    range_rx = re.compile(rf"(?:{rk})\b\s*(?P<min>\d{{1,3}}(?:[\.,]\d{{3}})*(?:\.\d+)?)[^\d]{{0,20}}(?:{rc})\s*(?P<max>\d{{1,3}}(?:[\.,]\d{{3}})*(?:\.\d+)?)(?:\s*(?P<cur>usd|\$|L\.))?", re.IGNORECASE)
    rm = range_rx.search(notes)
    if rm:
        name = extract_location(notes, cfg) or ""
        cur = (rm.group("cur") or "").strip()
        pmin = rm.group("min").replace(",", "")
        pmax = rm.group("max").replace(",", "")
        min_blob = f"{pmin} {cur}".strip()
        max_blob = f"{pmax} {cur}".strip()
        segs.append(Segment(name=name, prices_blob=min_blob, start=0, end=0))
        segs.append(Segment(name=name, prices_blob=max_blob, start=0, end=0))
        return segs

    return segs


# ------------------------------- Main flow -------------------------------- #

def stable_uid(*parts: Optional[str]) -> str:
    s = "|".join(["" if p is None else str(p) for p in parts])
    return hashlib.sha1(s.encode("utf-8")).hexdigest()


def process_file(input_path: Path, outdir: Path, notes_col: str, id_col: str, year: Optional[int], month: Optional[int], config: dict, candidate_column: str = "CHILDREN_CANDIDATE", gate_expansion: bool = False, export_candidates: bool = False) -> None:
    outdir.mkdir(parents=True, exist_ok=True)

    def _coerce_children_schema(df: pd.DataFrame) -> pd.DataFrame:
        out = df.copy()
        for col in ["child_idx", "children_count", "bedrooms"]:
            if col in out.columns:
                out[col] = pd.to_numeric(out[col], errors="coerce").astype("Int64")
        for col in ["parent_row_id", "listing_uid", "neighborhood", "raw_prices_blob", "child_fraction"]:
            if col in out.columns:
                out[col] = out[col].astype("string")
        return out

    # Load input
    if input_path.suffix.lower() in {".parquet", ".pq"}:
        df = pd.read_parquet(input_path)
    else:
        df = pd.read_csv(input_path)

    if notes_col not in df.columns:
        raise SystemExit(f"Missing notes column: {notes_col}")
    if id_col not in df.columns:
        # create synthetic parent ids if absent
        df[id_col] = [stable_uid(str(input_path), i) for i in range(len(df))]

    # Pre-normalize notes text
    notes_norm = df[notes_col].fillna("").map(lambda x: pre_normalize(x, config))

    # Anchor counts
    anchors = notes_norm.map(count_anchors)
    anchor_df = pd.DataFrame(list(anchors))

    df = df.copy()
    for c in anchor_df.columns:
        df[c] = anchor_df[c].values

    # Ensure candidate column exists
    if candidate_column not in df.columns:
        df[candidate_column] = 'n'

    # Multi-listing heuristic flag (for reference)
    df["multi_listing"] = df.apply(lambda r: is_multi_listing({
        "name_colon_count": r["name_colon_count"],
        "mls_id_count": r["mls_id_count"],
        "addr_anchor_count": r["addr_anchor_count"],
        "date_count": r["date_count"],
        "price_token_count": r["price_token_count"],
        "slash_offer_burst": r["slash_offer_burst"],
    }), axis=1)

    children_rows: List[dict] = []
    review_rows: List[dict] = []

    def _is_yes(val) -> bool:
        s = str(val).strip().lower() if val is not None else ""
        return s in {"y", "yes", "1", "true", "sí", "si"}

    for idx, row in df.iterrows():
        raw = notes_norm.iloc[idx]
        parent_id = row[id_col]

        # Compute segments & offers for suggestions
        segs: List[Segment] = segment_notes(raw, config)

        seg_offer_counts: List[int] = []
        seg_offers_list: List[List[str]] = []
        for s in segs:
            toks = tokenize_offers(s.prices_blob)
            # de-dup within segment
            seen, uniq = set(), []
            for t in toks:
                k = _norm_price_token(t)
                if k not in seen:
                    seen.add(k)
                    uniq.append(t)
            seg_offers_list.append(uniq)
            seg_offer_counts.append(len(uniq))

        suggested_children = sum(seg_offer_counts) if seg_offer_counts else 0

        # Corroborating anchors for 'y'
        has_multi_anchor = (row["name_colon_count"] >= 2) or (row["slash_offer_burst"] == 1)
        has_bedroom_alignment = any(s.bedrooms is not None for s in segs) and suggested_children >= 2
        one_clean_name_price = (len(segs) == 1 and seg_offer_counts == [1])

        if one_clean_name_price:
            suggested_flag = 'n'
        else:
            suggested_flag = 'y' if (suggested_children >= 2 and (has_multi_anchor or has_bedroom_alignment)) else 'n'

        # Previews
        previews = []
        running_index = 1
        for s, offers in zip(segs, seg_offers_list):
            if offers:
                for o in offers:
                    previews.append(f"{(s.name or '').strip()} ({running_index}/{suggested_children or 1}): {o}")
                    running_index += 1
            else:
                previews.append(f"{(s.name or '').strip()} ({running_index}/{suggested_children or 1}): {s.prices_blob[:60].replace('\n',' ')}")
                running_index += 1

        # Expansion gating
        allow_expand = True if not gate_expansion else _is_yes(row.get(candidate_column, 'n'))

        child_count = 0
        if allow_expand and segs:
            # Expand to children while enforcing mixed-currency rule & dedup per segment
            for s, offers in zip(segs, seg_offers_list):
                if not offers:
                    continue
                # Mixed-currency detection
                cur_set: List[str] = []
                for o in offers:
                    m2 = RE_PRICE_EXTRACT.search(o)
                    if m2:
                        cur = (m2.group("cur") or "").strip()
                        if cur and cur not in cur_set:
                            cur_set.append(cur)
                mixed = len(cur_set) > 1
                dont_split_mixed = (
                    mixed and not config.get("split_multi_offers_when_mixed_currency", False)
                    and len(offers) <= config.get("dont_split_mixed_currency_max_offers", 2)
                )
                eff_offers = offers if not dont_split_mixed else [" / ".join(offers)]

                # Emit child rows
                for o in eff_offers:
                    child = row.to_dict()
                    child.update({
                        "parent_row_id": parent_id,
                        "child_idx": 0,  # provisional, will resequence after dedup
                        "children_count": 0,
                        "child_fraction": "",
                        "neighborhood": s.name,
                        "raw_prices_blob": o,
                    })
                    if s.bedrooms is not None:
                        child["bedrooms"] = s.bedrooms
                    child["listing_uid"] = stable_uid(
                        child.get("agency"), year, month, parent_id, 0, s.name, s.bedrooms, o
                    )
                    children_rows.append(child)
                    child_count += 1

        review_rows.append({
            "parent_row_id": parent_id,
            "children_count": child_count,
            "suggested_children": suggested_children,
            "suggested_candidate": suggested_flag,
            "existing_candidate": row.get(candidate_column, 'n'),
            "name_colon_count": row["name_colon_count"],
            "mls_id_count": row["mls_id_count"],
            "addr_anchor_count": row["addr_anchor_count"],
            "date_count": row["date_count"],
            "price_token_count": row["price_token_count"],
            "slash_offer_burst": row["slash_offer_burst"],
            "multi_listing": int(row["multi_listing"]),
            "children_preview": " | ".join(previews) if previews else "",
            "notes_preview": raw[:140].replace("\n", " "),
        })

    # --- De‑duplicate across segments for the same parent & resequence ---
    if children_rows:
        deduped: List[dict] = []
        seen: set[Tuple[str, str, str, Optional[int]]] = set()
        for r in children_rows:
            key = (
                str(r.get("parent_row_id")),
                _norm_price_token(str(r.get("raw_prices_blob", ""))),
                (r.get("neighborhood") or "").strip().lower(),
                int(r.get("bedrooms")) if r.get("bedrooms") is not None and str(r.get("bedrooms")).isdigit() else (r.get("bedrooms") if r.get("bedrooms") is not None else None),
            )
            if key not in seen:
                seen.add(key)
                deduped.append(r)
        children_rows = deduped

        # Resequence per parent
        from collections import defaultdict
        bucket: dict[str, List[dict]] = defaultdict(list)
        for r in children_rows:
            bucket[str(r["parent_row_id"])].append(r)
        for pid, rows in bucket.items():
            rows.sort(key=lambda x: (_norm_price_token(str(x.get("raw_prices_blob", ""))), x.get("bedrooms") or 0, (x.get("neighborhood") or "")))
            total = len(rows)
            for i, r in enumerate(rows, 1):
                r["child_idx"] = i
                r["children_count"] = total
                r["child_fraction"] = f"{i}/{total}"
                # refresh UID with final child_idx
                r["listing_uid"] = stable_uid(
                    r.get("agency"), year, month, r.get("parent_row_id"), i, r.get("neighborhood"), r.get("bedrooms"), r.get("raw_prices_blob")
                )

    # Write review/candidates
    review_df = pd.DataFrame(review_rows)
    review_csv = outdir / "parent_child_review.csv"
    review_df.to_csv(review_csv, index=False)

    if export_candidates:
        parents_out = outdir / "parents_with_candidates.csv"
        df_out = df.copy()
        df_out["suggested_children"] = review_df["suggested_children"].values
        df_out["suggested_candidate"] = review_df["suggested_candidate"].values
        df_out.to_csv(parents_out, index=False)

    # Write children
    if children_rows:
        children_df = pd.DataFrame(children_rows)
        children_df = _coerce_children_schema(children_df)
        children_parquet = outdir / "children.parquet"
        children_csv = outdir / "children.csv"
        children_df.to_parquet(children_parquet, index=False)
        children_df.to_csv(children_csv, index=False)
    else:
        # still create empty outputs for consistent pipelines
        empty = pd.DataFrame(columns=["parent_row_id", "child_idx"])
        empty.to_parquet(outdir / "children.parquet", index=False)
        empty.to_csv(outdir / "children.csv", index=False)

    summary = {
        "input": str(input_path),
        "outdir": str(outdir),
        "total_rows": int(len(df)),
        "multi_rows": int(df["multi_listing"].sum()),
        "children_rows": int(len(children_rows)),
    }
    (outdir / "summary.json").write_text(json.dumps(summary, indent=2))


# --------------------------------- CLI ----------------------------------- #

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Detect & split multi-listings in tabulated files (v3)")
    p.add_argument("--input", required=True, type=Path, help="Input CSV or Parquet file")
    p.add_argument("--outdir", required=True, type=Path, help="Output directory for children & review files")
    p.add_argument("--notes-col", default="notes", help="Column containing raw/original text (default: notes)")
    p.add_argument("--id-col", default="id", help="Unique row identifier column (default: id). If absent, a synthetic id is created.")
    p.add_argument("--year", type=int, default=None, help="(Optional) Year for UID lineage")
    p.add_argument("--month", type=int, default=None, help="(Optional) Month (1-12) for UID lineage")
    p.add_argument("--config", type=Path, default=None, help="Optional JSON config file for splitter (keywords, aliases)")
    # Candidate-gating controls
    p.add_argument("--candidate-column", default="CHILDREN_CANDIDATE", help="Manual review column that gates expansion (default: CHILDREN_CANDIDATE)")
    p.add_argument("--gate-expansion", action="store_true", help="Only expand rows where candidate-column is 'y'/'yes'/1/true/sí/si")
    p.add_argument("--export-candidates", action="store_true", help="Export a parents_with_candidates.csv with suggestions and previews")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    cfg = load_config(args.config)
    process_file(
        args.input,
        args.outdir,
        args.notes_col,
        args.id_col,
        args.year,
        args.month,
        cfg,
        candidate_column=args.candidate_column,
        gate_expansion=args.gate_expansion,
        export_candidates=args.export_candidates,
    )


if __name__ == "__main__":
    main()
