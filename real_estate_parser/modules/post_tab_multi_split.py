#!/usr/bin/env python3
"""
Post-tabulation multi-listing detector & splitter

Now supports a JSON config (`--config config_splitter.json`) and four
split modes:
  1) **Anchor-based multi** (Name:Prices, multiple IDs, addresses) → N children
  2) **Bedroom variants** (e.g., "1,2,3 cuartos 400,500,600 usd") → K children
  3) **Range phrases** (e.g., "desde 230000 hasta 300000 usd") → 2 children
  4) **Aligned bedrooms + prices with markers** (e.g., "1 y 2 habitaciones … 5500 y 7500 respectivamente") → children aligned pairwise
  5) **Multi-offer burst exploder** (e.g., "Roble Oeste: L.1,400,000/$105,000/125,000/150,000") → one child per price (configurable)

Outputs
-------
- <outdir>/children.parquet (and .csv): one row per child listing, with
  lineage: parent_row_id, child_idx, children_count, child_fraction.
- <outdir>/parent_child_review.csv: parent→children mapping with previews.

Usage
-----
python post_tab_multi_split.py \
  --input data/tabulated_2020.parquet \
  --outdir out/splits_2020 \
  --notes-col notes \
  --id-col id \
  [--year 2020 --month 06] [--config config_splitter.json]

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


RE_NAME_PRICES_SEGMENTER = re.compile(
    r"""
    (?:                             # a new segment starts after...
        ^                           #   start of string
      | [\s(\u2022*;\-]             #   or a separator (space, (, bullet, *, ;, -)
    )
    (?P<name>[A-Za-zÁÉÍÓÚÜÑñ0-9' .-]+?)   # the name
    \s*:\s*                         # colon separator
    (?P<prices>.+?)                 # the prices blob (lazy)
    (?=                             # ...until we look ahead to next segment start
        (?:[\s(\u2022*;\-][A-Za-zÁÉÍÓÚÜÑñ0-9' .-]+?\s*:)  # sep + next Name:
      | $                           # or end of string
    )
    """,
    re.IGNORECASE | re.DOTALL | re.VERBOSE,
)



RE_PRICE_EXTRACT = re.compile(
    r"^\s*(?P<cur>L\.|\$)?\s*(?P<num>\d{1,3}(?:,\d{3})*(?:\.\d+)?|\d+(?:\.\d+)?)"
)

# ------------------------------ Helpers & Data classes -------------------- #

# --- Coerce child schema for parquet safety ---
def _coerce_children_schema(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    # integers with possible NA
    for col in ["child_idx", "children_count", "bedrooms"]:
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce").astype("Int64")
    # ids as strings
    for col in ["parent_row_id", "listing_uid", "neighborhood", "raw_prices_blob", "child_fraction"]:
        if col in out.columns:
            out[col] = out[col].astype("string")
    return out

 


def tokenize_offers(prices_blob: str) -> list:
    """Tokenize a prices blob into a list of price strings with currency
    inheritance. This returns a list like ["L. 1,200,000", "$90,000", "$120,000"].
    """
    tokens = re.findall(r"(?:L\.|\$)?\s*\d{1,3}(?:,\d{3})*(?:\.\d+)?", prices_blob)
    offers: list[str] = []
    last_cur: Optional[str] = None
    for tok in tokens:
        m = RE_PRICE_EXTRACT.search(tok)
        if not m:
            continue
        cur = m.group("cur")  # 'L.' or '$' or None
        num = m.group("num")
        if cur:
            last_cur = cur
            offers.append(f"{cur} {num}".strip())
        else:
            if last_cur:
                offers.append(f"{last_cur} {num}".strip())
            else:
                offers.append(num)
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
        if not RE_PRICE_TOKEN.search(prices[:60]):
            continue
        # Detect dual-currency single-option: exactly 2 offers, different currencies
        offers = tokenize_offers(prices)
        if len(offers) == 2:
            cur1 = offers[0][0]
            cur2 = offers[1][0]
            if cur1 != cur2:
                # Single segment with both currencies kept in blob
                segs.append(Segment(name=name, prices_blob=" / ".join(offers), start=m.start(), end=m.end()))
                return segs
        segs.append(Segment(name=name, prices_blob=prices, start=m.start(), end=m.end()))
    if segs:
        # Explode multi-offer bursts into one child per price if enabled
        if cfg.get("split_multi_offers", False):
            expanded: List[Segment] = []
            for s in segs:
                offers = tokenize_offers(s.prices_blob)
                # Detect currency diversity
                cur_set = []
                for o in offers:
                    m = RE_PRICE_EXTRACT.search(o)
                    if m:
                        cur = (m.group("cur") or "").strip()
                        if cur and cur not in cur_set:
                            cur_set.append(cur)
                mixed = len(cur_set) > 1
                dont_split_mixed = (
                    mixed and not cfg.get("split_multi_offers_when_mixed_currency", False)
                    and len(offers) <= cfg.get("dont_split_mixed_currency_max_offers", 2)
                )
                if dont_split_mixed:
                    # Keep as single child; downstream price parser will record both currencies
                    expanded.append(s)
                    continue
                if len(offers) >= cfg.get("min_offers_to_split", 2):
                    for p in offers:
                        expanded.append(Segment(name=s.name, prices_blob=p, start=s.start, end=s.end, bedrooms=s.bedrooms))
                else:
                    expanded.append(s)
            return expanded
        return segs

    # 2) Bedroom variants (comma/and list + multiple prices)
    bedword_regex = r"|".join(cfg.get("bedroom_keywords", DEFAULT_CONFIG["bedroom_keywords"]))
    bed_pattern = re.compile(rf"(?P<counts>(?:\d+[\s,y/–-]*){{1,5}})\s*(?P<label>{bedword_regex})\b.*?(?P<prices>(?:\d{{1,3}}(?:,\d{{3}})*(?:\.\d+)?)(?:\s*[,y/–-]\s*\d{{1,3}}(?:,\d{{3}})*(?:\.\d+)?)+)\s*(?P<cur>usd|\$|L\.)?", re.IGNORECASE)
    bm = bed_pattern.search(notes)
    if bm:
        counts = [int(c) for c in re.split(r"[ ,y/–-]+", bm.group("counts")) if c.strip().isdigit()]
        price_tokens = re.split(r"\s*[,y/–-]\s*", bm.group("prices"))
        cur = (bm.group("cur") or "").strip()
        if cur and all(not re.search(r"(?:L\.|\$|usd)", p, re.I) for p in price_tokens):
            price_tokens = [f"{p} {cur}" for p in price_tokens]
        if len(counts) == len(price_tokens) and len(counts) >= 2:
            for c, p in zip(counts, price_tokens):
                segs.append(Segment(name=extract_location(notes, cfg) or "", prices_blob=p.strip(), start=0, end=0, bedrooms=c))
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

def process_file(input_path: Path, outdir: Path, notes_col: str, id_col: str, year: Optional[int], month: Optional[int], config: dict) -> None:
    outdir.mkdir(parents=True, exist_ok=True)

    if input_path.suffix.lower() in {".parquet", ".pq"}:
        df = pd.read_parquet(input_path)
    else:
        df = pd.read_csv(input_path)

    if notes_col not in df.columns:
        raise SystemExit(f"Missing notes column: {notes_col}")
    if id_col not in df.columns:
        df[id_col] = [stable_uid(str(input_path), i) for i in range(len(df))]

    notes_norm = df[notes_col].fillna("").map(lambda x: pre_normalize(x, config))
    anchors = notes_norm.map(count_anchors)
    anchor_df = pd.DataFrame(list(anchors))
    df = df.copy()
    for c in anchor_df.columns:
        df[c] = anchor_df[c].values
    df["multi_listing"] = df.apply(lambda r: is_multi_listing({
        "name_colon_count": r["name_colon_count"],
        "mls_id_count": r["mls_id_count"],
        "addr_anchor_count": r["addr_anchor_count"],
        "date_count": r["date_count"],
        "price_token_count": r["price_token_count"],
        "slash_offer_burst": r["slash_offer_burst"],
    }), axis=1)

    children_rows = []
    review_rows = []

    for idx, row in df.iterrows():
        raw = notes_norm.iloc[idx]
        parent_id = row[id_col]

        segs: List[Segment] = []
        if row["multi_listing"]:
            segs = segment_notes(raw, config)
        else:
            segs = segment_notes(raw, config)

        if not segs:
            continue

        total_children = len(segs)
        child_count = 0
        previews = []
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
            label = seg.name or (f"{seg.bedrooms} br" if seg.bedrooms is not None else "variant")
            previews.append(f"{label} ({s_idx}/{total_children}): {seg.prices_blob[:60].replace('\n',' ')}")

        review_rows.append({
            "parent_row_id": parent_id,
            "children_count": child_count,
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

    review_df = pd.DataFrame(review_rows)
    review_csv = outdir / "parent_child_review.csv"
    review_df.to_csv(review_csv, index=False)

    if children_rows:
        children_df = pd.DataFrame(children_rows)
        children_df = _coerce_children_schema(children_df)  # <-- NOW it exists

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
    p = argparse.ArgumentParser(description="Detect & split multi-listings in tabulated files")
    p.add_argument("--input", required=True, type=Path, help="Input CSV or Parquet file")
    p.add_argument("--outdir", required=True, type=Path, help="Output directory for children & review files")
    p.add_argument("--notes-col", default="notes", help="Column containing raw/original text (default: notes)")
    p.add_argument("--id-col", default="id", help="Unique row identifier column (default: id). If absent, a synthetic id is created.")
    p.add_argument("--year", type=int, default=None, help="(Optional) Year for UID lineage")
    p.add_argument("--month", type=int, default=None, help="(Optional) Month (1-12) for UID lineage")
    p.add_argument("--config", type=Path, default=None, help="Optional JSON config file for splitter (keywords, aliases)")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    config = load_config(args.config)
    process_file(args.input, args.outdir, args.notes_col, args.id_col, args.year, args.month, config)


if __name__ == "__main__":
    main()
