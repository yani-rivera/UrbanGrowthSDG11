#!/usr/bin/env python3
"""
Post-tabulation multi-listing detector & splitter (v2, patched)

What's new vs earlier versions:
- **Safer Name:Prices segmenter** (no Unicode/"-" charclass pitfalls)
- **Stricter bedroom logic**: only splits when there are **≥ 2 bedroom counts**
- **Offer tokenizer hardened**: only explodes per-price for **currency-anchored chains**
- **Mixed-currency pair** (e.g., "L1,900,000 / $140,000") defaults to **single child** unless configured
- **Manual gating**: `--gate-expansion` honors a candidate column (default `CHILDREN_CANDIDATE`) so you approve rows first
- **Export candidates**: writes `parents_with_candidates.csv` for review
- **Parquet-safe dtypes**: coerces children schema before writing

Outputs
-------
- <outdir>/children.parquet and children.csv — exploded children
- <outdir>/parent_child_review.csv — QA summary with suggestions
- <outdir>/summary.json — run stats
- (optional) <outdir>/parents_with_candidates.csv — parent rows + flags

Usage
-----
python post_tab_multi_splitv2_patched.py \
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
from typing import List, Optional

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

def tokenize_offers(prices_blob: str) -> list:
    """Return price offers only from a currency-anchored chain.
    Ignores bare numbers like "3 dormitorios" or "2 autos" unless
    they follow a currency-bearing token (currency inheritance).
    """
    chain_rx = re.compile(
        r"(?:L\.|\$)\s*\d{1,3}(?:,\d{3})*(?:\.\d+)?"
        r"(?:\s*(?:/|,|\by\b|\be\b)\s*(?:L\.|\$)?\s*\d{1,3}(?:,\d{3})*(?:\.\d+)?)*",
        re.IGNORECASE,
    )
    m = chain_rx.search(prices_blob)
    if not m:
        one = re.search(r"(?:L\.|\$)\s*\d{1,3}(?:,\d{3})*(?:\.\d+)?", prices_blob)
        return [one.group(0)] if one else []

    parts = re.split(r"\s*(?:/|,|\by\b|\be\b)\s*", m.group(0))
    offers: list[str] = []
    last_cur: Optional[str] = None
    for part in parts:
        pm = re.search(r"(L\.|\$)?\s*(\d{1,3}(?:,\d{3})*(?:\.\d+)?)", part)
        if not pm:
            continue
        cur, num = pm.group(1), pm.group(2)
        if cur:
            last_cur = cur
            offers.append(f"{cur} {num}")
        elif last_cur:
            offers.append(f"{last_cur} {num}")
    return offers

@dataclass
class Segment:
    name: str
    prices_blob: str
    start: int
    end: int
    bedrooms: Optional[int] = None


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


def segment_notes(notes: str, cfg: dict) -> List[Segment]:
    segs: List[Segment] = []
    # 1) Anchor-based Name:Prices
    for m in RE_NAME_PRICES_SEGMENTER.finditer(notes):
        name = m.group("name").strip()
        prices = m.group("prices").strip()
        # Require a currency-bearing price to avoid splitting on plain counts
        if not RE_PRICE_WITH_CURRENCY.search(prices[:120]):
            continue
        # Detect dual-currency single-option: exactly 2 offers, different currencies
        offers = tokenize_offers(prices)
        if len(offers) == 2:
            cur1 = offers[0][0]
            cur2 = offers[1][0]
            if cur1 != cur2:
                segs.append(Segment(name=name, prices_blob=" / ".join(offers), start=m.start(), end=m.end()))
                continue
        segs.append(Segment(name=name, prices_blob=prices, start=m.start(), end=m.end()))
    if segs:
        # Explode multi-offer bursts into one child per price if enabled
        if cfg.get("split_multi_offers", False):
            expanded: List[Segment] = []
            for s in segs:
                offers = tokenize_offers(s.prices_blob)
                # Detect currency diversity
                cur_set: list[str] = []
                for o in offers:
                    m2 = RE_PRICE_EXTRACT.search(o)
                    if m2:
                        cur = (m2.group("cur") or "").strip()
                        if cur and cur not in cur_set:
                            cur_set.append(cur)
                mixed = len(cur_set) > 1
                dont_split_mixed = (
                    mixed and not cfg.get("split_multi_offers_when_mixed_currency", False)
                    and len(offers) <= cfg.get("dont_split_mixed_currency_max_offers", 2)
                )
                if dont_split_mixed:
                    expanded.append(s)
                    continue
                if len(offers) >= cfg.get("min_offers_to_split", 2):
                    for p in offers:
                        expanded.append(Segment(name=s.name, prices_blob=p, start=s.start, end=s.end, bedrooms=s.bedrooms))
                else:
                    expanded.append(s)
            return expanded
        return segs

    # 2) Bedroom variants (comma/and list + multiple prices) — requires ≥ 2 counts
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


def stable_uid(*parts: Optional[str]) -> str:
    s = "|".join(["" if p is None else str(p) for p in parts])
    return hashlib.sha1(s.encode("utf-8")).hexdigest()


# ------------------------------- Main flow -------------------------------- #

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
        # Still allow processing by generating a synthetic parent id
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

    children_rows: list[dict] = []
    review_rows: list[dict] = []

    def _is_yes(val) -> bool:
        s = str(val).strip().lower() if val is not None else ""
        return s in {"y", "yes", "1", "true", "sí", "si"}

    for idx, row in df.iterrows():
        raw = notes_norm.iloc[idx]
        parent_id = row[id_col]

        # Always compute proposed segments for suggestion/export
        segs: List[Segment] = segment_notes(raw, config)

        total_children = len(segs)
        suggested_flag = 'y' if total_children >= 2 else 'n'

        # Build previews (even if we don't expand)
        previews = []
        for s_idx, seg in enumerate(segs, start=1):
            label = seg.name or (f"{seg.bedrooms} br" if seg.bedrooms is not None else "variant")
            previews.append(f"{label} ({s_idx}/{total_children}): {seg.prices_blob[:60].replace('\n',' ')}")

        # Gate expansion if requested
        allow_expand = True
        if gate_expansion:
            allow_expand = _is_yes(row.get(candidate_column, 'n'))

        child_count = 0
        if allow_expand and segs:
            for s_idx, seg in enumerate(segs, start=1):
                child = row.to_dict()
                child.update({
                    "parent_row_id": parent_id,
                    "child_idx": s_idx,
                    "children_count": total_children,
                    "child_fraction": f"{s_idx}/{total_children}",
                    "neighborhood": seg.name,
                    "raw_prices_blob": seg.prices_blob,
                })
                if seg.bedrooms is not None:
                    child["bedrooms"] = seg.bedrooms
                child["listing_uid"] = stable_uid(
                    child.get("agency"), year, month, parent_id, s_idx, seg.name, seg.bedrooms
                )
                children_rows.append(child)
                child_count += 1

        review_rows.append({
            "parent_row_id": parent_id,
            "children_count": child_count,
            "suggested_children": total_children,
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

    # Write review/candidates
    review_df = pd.DataFrame(review_rows)
    review_csv = outdir / "parent_child_review.csv"
    review_df.to_csv(review_csv, index=False)

    # Optionally export parents with candidate column for manual marking
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
        pd.DataFrame(columns=["parent_row_id","child_idx"]).to_parquet(outdir / "children.parquet", index=False)
        pd.DataFrame(columns=["parent_row_id","child_idx"]).to_csv(outdir / "children.csv", index=False)

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
    p = argparse.ArgumentParser(description="Detect & split multi-listings in tabulated files (v2, patched)")
    p.add_argument("--input", required=True, type=Path, help="Input CSV or Parquet file")
    p.add_argument("--outdir", required=True, type=Path, help="Output directory for children & review files")
    p.add_argument("--notes-col", default="notes", help="Column containing raw/original text (default: notes)")
    p.add_argument("--id-col", default="id", help="Unique row identifier column (default: id). If absent, a synthetic id is created.")
    p.add_argument("--year", type=int, default=None, help="(Optional) Year for UID lineage")
    p.add_argument("--month", type=int, default=None, help="(Optional) Month (1-12) for UID lineage")
    p.add_argument("--config", type=Path, default=None, help="Optional JSON config file for splitter (keywords, aliases)")
    # Candidate-gating controls
    p.add_argument("--candidate-column", default="CHILDREN_CANDIDATE", help="Name of the manual review column to gate expansion (default: CHILDREN_CANDIDATE)")
    p.add_argument("--gate-expansion", action="store_true", help="Only expand rows where candidate-column is 'y'/'yes'/1/true")
    p.add_argument("--export-candidates", action="store_true", help="Export a parents_with_candidates.csv with suggestions and previews")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    config = load_config(args.config)
    process_file(
        args.input,
        args.outdir,
        args.notes_col,
        args.id_col,
        args.year,
        args.month,
        config,
        candidate_column=args.candidate_column,
        gate_expansion=args.gate_expansion,
        export_candidates=args.export_candidates,
    )


if __name__ == "__main__":
    main()
