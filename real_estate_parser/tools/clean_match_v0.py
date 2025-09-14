#!/usr/bin/env python3
"""
clean_match_v0.py — Neighborhood cleaner + matcher (v0.0)

What it does (non-destructive):
1) Cleans the existing `neighborhood` column.
2) Extracts a `neighborhood_type` from leading prefixes (COL., BARRIO, etc.).
3) Produces `neighborhood_clean` (prefix removed), with adaptive 20→30 char cap.
4) Matches against an official neighborhoods JSON (`config_known_neighborhoods.json`).
5) Adds `neighborhood_id`, `neighborhood_label`, `match_confidence`, `match_method`.
6) Optionally enriches building signals using existing `property_type` + listing text.
7) Writes a matched CSV and an unmatched summary for review.

Usage examples
--------------
python tools/clean_match_v0.py \
  --input output/consolidated/2025/merged_2025.csv \
  --official config_known_neighborhoods.json \
  --out-matched output/consolidated/2025/merged_2025_matched.csv \
  --out-unmatched output/consolidated/2025/merged_2025_unmatched.csv \
  --config configs/neigh_clean_v0.json

The external JSON config is optional. If omitted, built-in sane defaults are used.

Notes
-----
- We NEVER overwrite the original `neighborhood` field. We add:
  neighborhood_raw, neighborhood_type, neighborhood_clean, neighborhood_id,
  neighborhood_label, match_confidence, match_method, is_building, building_name
- Matching is accent-insensitive and whitespace-normalized.
- Official JSON must be a list of objects with fields like { "Neighborhood": ..., "Code": ... }.
"""

from __future__ import annotations
import argparse
import csv
import json
import os
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from typing import Dict, Iterable, List, Tuple

# ------------------------- Built‑in default config (can be overridden by --config) -------------------------
DEFAULT_CFG = {
    "uppercase": True,
    "strip_accents": True,
    "max_len_default": 20,
    "max_len_cap": 30,
    "min_len": 3,

    # Prefix → neighborhood_type
    "prefix_type_map": {
        "COL.": "COLONIA", "COL": "COLONIA", "COLONIA": "COLONIA",
        "BARRIO": "BARRIO", "BO.": "BARRIO", "BO": "BARRIO",
        "URB.": "URBANIZACION", "URBANIZACION": "URBANIZACION", "URBANIZACIÓN": "URBANIZACION",
        "ALDEA": "ALDEA",
        "AVENIDA": "AVENIDA", "AV.": "AVENIDA",
        "RES.": "RESIDENCIAL", "RESID.": "RESIDENCIAL", "RESIDENCIAL": "RESIDENCIAL"
    },

    # Canonical prefix to recompose when matching WITH type
    "type_to_prefix": {
        "COLONIA": "COL.",
        "BARRIO": "BARRIO",
        "URBANIZACION": "URB.",
        "ALDEA": "ALDEA",
        "AVENIDA": "AVENIDA",
        "RESIDENCIAL": "RES."
    },

    # Lightweight replacements to harmonize common variants
    "replace_map": {
        "B° ": "BARRIO ",
        "ALTOS MIRAFLORES": "ALTOS DE MIRAFLORES",
        "ALTOS MIRAMONTES": "ALTOS DE MIRAMONTES",
        "ALTOS TONCONTIN": "ALTOS DE TONCONTIN",
        "LOMAS GUIJARRO": "LOMAS DEL GUIJARRO",
        "VALLE ANGELES": "VALLE DE ANGELES"
    },

    # Regex patterns for stripping noise
    "strip_patterns": {
        # Remove leading price markers
        "leading_price": r"^(?:\$|US\$|USD|HNL|LPS?\.?|L\.)\s*[\d.,/\- ]+",
        # Remove trailing price blobs
        "trailing_price": r"[, ]*(?:\$|US\$|USD|HNL|LPS?\.?|L\.)?\s*[\d.,/\- ]+$",
        # Remove generic parenthetical fluff at the end (one group)
        "trailing_generic_paren": r"\s*\((?:NUEVA|AREA SOCIAL|ÁREA SOCIAL|SEG|24H(?:RAS)?|JARD[IÍ]N|GARAJE|INCLUID[OA])\)\s*$"
    },

    # Matching thresholds
    "match_thresholds": {
        "prefix_contains": 0.90,
        "token_jaccard": 0.70
    },

    # Aliases dictionary to boost exact matches (canonical → list of variants)
    "aliases": {
        "RES. CENTROAMÉRICA": ["RES. CENTROAMERICA"],
        "VALLE DE ÁNGELES": ["VALLE DE ANGELES"],
        "BARRIO MORAZÁN": ["BARRIO MORAZAN", "BO MORAZAN"],
        "ALTOS DE MIRAMONTES": ["ALTOS MIRAMONTES"],
        "LOMAS DEL GUIJARRO": ["LOMAS GUIJARRO"],
        "RES. TRAPICHE": ["TRAPICHE"],
        "EL CHIMBO": ["CHIMBO"],
        "COL. PALMIRA": ["PALMIRA"],
        "ALTOS DE TONCONTÍN": ["ALTOS DE TONCONTIN"]
    },

    # Building enrichment (uses existing property_type + text): token lists
    "building_tokens": ["torre", "edificio", "tower", "condominio"],
    "text_fields": ["title", "raw", "notes"],
}

# ------------------------- Text normalization helpers -------------------------

def nfkc_upper(s: str) -> str:
    return unicodedata.normalize("NFKC", (s or "")).upper().strip()

def strip_accents(s: str) -> str:
    nfkd = unicodedata.normalize("NFKD", s)
    noacc = "".join(ch for ch in nfkd if not unicodedata.combining(ch))
    return unicodedata.normalize("NFKC", noacc)

def normalize_label(s: str, cfg: Dict) -> str:
    t = s or ""
    # lightweight replacements first
    for k, v in (cfg.get("replace_map") or {}).items():
        t = re.sub(rf"\b{re.escape(k)}", v, t, flags=re.IGNORECASE)
    # remove obvious prices and fluff at both ends
    sp = cfg.get("strip_patterns") or {}
    if sp.get("leading_price"):
        t = re.sub(sp["leading_price"], "", t, flags=re.IGNORECASE)
    if sp.get("trailing_generic_paren"):
        t = re.sub(sp["trailing_generic_paren"], "", t, flags=re.IGNORECASE)
    if sp.get("trailing_price"):
        t = re.sub(sp["trailing_price"], "", t, flags=re.IGNORECASE)
    # normalize case/accents
    if cfg.get("uppercase", True):
        t = nfkc_upper(t)
    if cfg.get("strip_accents", True):
        t = strip_accents(t)
    # collapse punctuation to spaces; single spaces
    t = re.sub(r"[^\w\s\.]", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t

# ------------------------- Neighborhood type extraction -------------------------

def extract_type_and_core(text: str, cfg: Dict) -> Tuple[str, str]:
    """Return (neighborhood_type, core_name_without_prefix)."""
    if not text:
        return "", ""
    t = text.strip()
    # check the first token(s) against prefix map
    prefix_map = cfg.get("prefix_type_map", {})
    # Sort keys by length desc so we match longer prefixes first (e.g., "URBANIZACIÓN" before "URB.")
    for prefix in sorted(prefix_map.keys(), key=len, reverse=True):
        rx = re.compile(rf"^\s*{re.escape(prefix)}\s+", flags=re.IGNORECASE)
        if rx.search(t):
            core = rx.sub("", t, count=1).strip()
            return prefix_map[prefix], core
    return "", t

# ------------------------- Official list loading & indexing -------------------------

def load_official_json(path: str) -> List[Dict[str, str]]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError("Official JSON must be a list of objects.")
    rows: List[Dict[str, str]] = []
    for r in data:
        name = r.get("Neighborhood") or r.get("name") or r.get("NAME") or ""
        code = r.get("Code") or r.get("code") or r.get("ID") or r.get("id") or ""
        code_str = str(code).strip()
        # Treat NaN-like values as missing
        if code_str.upper() in {"", "NAN", "NONE", "NULL"}:
            code_str = ""
        name_str = str(name or "").strip()
        if not name_str:
            continue
        rows.append({"id": code_str, "name": name_str})
    return rows

def build_indexes(official_rows: List[Dict[str, str]]):
    exact_index: Dict[str, Tuple[str, str]] = {}
    token_index: Dict[str, List[Tuple[str, str]]] = defaultdict(list)

    def _norm(x: str) -> str:
        return normalize_label(x, {"uppercase": True, "strip_accents": True, "replace_map": {}, "strip_patterns": {}})

    for r in official_rows:
        nid = (r.get("id") or "").strip()
        name = (r.get("name") or "").strip()
        if not name:
            continue
        norm = _norm(name)
        if nid:
            exact_index.setdefault(norm, (nid, name))
        for tok in set(tokens(name)):
            token_index[tok].append((nid, name))
    return exact_index, token_index

# ------------------------- Tokenization & similarity -------------------------

def tokens(s: str) -> List[str]:
    s = normalize_label(s, {"uppercase": True, "strip_accents": True, "replace_map": {}, "strip_patterns": {}})
    raw = re.split(r"[\s,;:/\|\-]+", s)
    # remove obvious type/currency tokens
    drop = {"CASA", "APTO", "APARTAMENTO", "APARTMENT", "DEPARTAMENTO", "DEPTO", "DEPA",
            "RES", "RES.", "RESID", "RESIDENCIAL", "COL", "COL.", "COLONIA", "BARRIO", "URB", "URB.",
            "ALDEA", "AV", "AV.", "AVENIDA", "TORRE", "EDIFICIO", "TOWER",
            "$", "US$", "USD", "HNL", "L.", "LPS", "LPS."}
    return [t for t in raw if t and t not in drop and not t.isdigit()]

def jaccard(a: Iterable[str], b: Iterable[str]) -> float:
    A, B = set(a), set(b)
    if not A and not B:
        return 1.0
    if not A or not B:
        return 0.0
    return len(A & B) / len(A | B)

# ------------------------- Matching -------------------------

def try_match(cand: str, exact_index, token_index, thresholds: Dict) -> Tuple[str, str, float, str]:
    """Return (id, label, confidence, method) or blanks."""
    c = normalize_label(cand, {"uppercase": True, "strip_accents": True, "replace_map": {}, "strip_patterns": {}})
    if not c:
        return "", "", 0.0, "none"
    # 1) exact
    if c in exact_index:
        nid, lbl = exact_index[c]
        if nid:
            return nid, lbl, 1.0, "exact"
    # 2) prefix/contains over official names
    best = ("", "", 0.0, "none")
    for k, (nid, lbl) in exact_index.items():
        if not nid:
            continue
        if k.startswith(c):
            conf = min(0.97, max(0.85, len(c) / max(len(k), 1)))
            if conf > best[2]:
                best = (nid, lbl, conf, "prefix_name")
        if c.startswith(k):
            conf = min(0.95, max(0.80, len(k) / max(len(c), 1)))
            if conf > best[2]:
                best = (nid, lbl, conf, "contains_name")
    if best[2] >= thresholds.get("prefix_contains", 0.90):
        return best
    # 3) token jaccard (candidate bucketed by shared tokens)
    toks_c = tokens(c)
    bucket: Dict[Tuple[str, str], int] = {}
    for t in set(toks_c):
        for nid, lbl in token_index.get(t, []):
            if not nid:
                continue
            bucket[(nid, lbl)] = bucket.get((nid, lbl), 0) + 1
    for (nid, lbl), _ in bucket.items():
        conf = jaccard(toks_c, tokens(lbl))
        if conf > best[2]:
            best = (nid, lbl, conf, "token_jaccard")
    if best[2] >= thresholds.get("token_jaccard", 0.70):
        return best
    return "", "", 0.0, "none"

# ------------------------- Adaptive length clamp -------------------------

def clamp_adaptive(core: str, ntype: str, exact_index, thresholds: Dict, cfg: Dict) -> str:
    """Default 20, expand up to 30 if we can confirm an official name or avoid ugly truncation."""
    if not core:
        return ""
    core = core.strip()
    max20 = int(cfg.get("max_len_default", 20))
    max30 = int(cfg.get("max_len_cap", 30))
    if len(core) <= max20:
        return core

    # Try to expand to an official full name ≤30 if exact/unique prefix
    # 1) exact official (without type)
    nid, lbl, conf, method = try_match(core, exact_index, {}, thresholds)
    if method in {"exact", "prefix_name"} and len(lbl) <= max30:
        return normalize_label(lbl, cfg)

    # 2) with type recomposed
    if ntype:
        prefix = (cfg.get("type_to_prefix", {}).get(ntype) or "").strip()
        if prefix:
            candidate_with_type = f"{prefix} {core}"
            nid, lbl, conf, method = try_match(candidate_with_type, exact_index, {}, thresholds)
            if method in {"exact", "prefix_name"} and len(lbl) <= max30:
                return normalize_label(lbl, cfg)

    # 3) Otherwise, trim to whole word up to 30
    if len(core) <= max30:
        # ensure we don't cut mid-word if close to boundary
        return re.sub(r"\s+\S*$", "", core) if len(core) > max20 else core

    # hard clamp to 30, trimmed to last whole word
    trimmed = core[:max30]
    return re.sub(r"\s+\S*$", "", trimmed).strip() or trimmed.strip()

# ------------------------- Building enrichment (minimal, uses existing property_type + text) -------------------------

def enrich_building_fields(row: Dict[str, str], cfg: Dict) -> Tuple[str, str]:
    """Return (is_building, building_name). is_building is 'true'/'false' string for CSV friendliness."""
    # 1) authoritative from property_type
    ptype = (row.get("property_type") or "").strip().upper()
    if ptype in {"APARTMENT", "CONDO", "APARTAMENTO"}:
        is_building = True
    else:
        is_building = False

    # 2) secondary cues from text fields
    text = " ".join(str(row.get(f, "")) for f in (cfg.get("text_fields") or ["title"]))
    text_up = nfkc_upper(text)
    bname = ""
    tokens_b = cfg.get("building_tokens") or []
    if any(re.search(rf"\b{re.escape(tok)}\b", text_up, flags=re.IGNORECASE) for tok in tokens_b):
        is_building = True
        # capture building name after keyword
        m = re.search(r"\b(TORRE|EDIFICIO|TOWER)\s+([A-Z0-9ÁÉÍÓÚÑ\- ]{3,})", text_up)
        if m:
            bname = (m.group(0) or "").strip()
            # light cleanup: stop at comma/price
            bname = re.split(r"\s*[,\$]", bname)[0].strip()
            # cap length
            if len(bname) > 30:
                bname = bname[:30].rstrip()
    return ("true" if is_building else "false"), bname

# ------------------------- IO helpers -------------------------

def read_csv_rows(path: str):
    for enc in ("utf-8-sig", "utf-8"):
        try:
            with open(path, "r", encoding=enc, newline="") as f:
                r = csv.DictReader(f)
                return (r.fieldnames or []), [dict(x) for x in r]
        except UnicodeDecodeError:
            continue
    with open(path, "r", encoding="latin-1", newline="") as f:
        r = csv.DictReader(f)
        return (r.fieldnames or []), [dict(x) for x in r]

def write_csv(path: str, header: List[str], rows: List[Dict[str, str]]):
    os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=header)
        w.writeheader()
        w.writerows(rows)

# ------------------------- Main -------------------------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, help="Consolidated CSV to clean+match")
    ap.add_argument("--official", required=True, help="Official neighborhoods JSON (config_known_neighborhoods.json)")
    ap.add_argument("--out-matched", required=True, help="Output CSV with cleaned+matched columns added")
    ap.add_argument("--out-unmatched", required=True, help="Output CSV with unmatched summary")
    ap.add_argument("--config", help="Optional JSON config to override defaults")
    ap.add_argument("--no-building", action="store_true", help="Disable building enrichment")
    args = ap.parse_args()

    # Load config
    cfg = dict(DEFAULT_CFG)
    if args.config:
        with open(args.config, "r", encoding="utf-8") as f:
            user_cfg = json.load(f)
        # shallow-merge
        for k, v in user_cfg.items():
            if isinstance(v, dict) and isinstance(cfg.get(k), dict):
                cfg[k].update(v)
            else:
                cfg[k] = v

    # Official indexes
    official_rows = load_official_json(args.official)
    exact_index, token_index = build_indexes(official_rows)

    thresholds = cfg.get("match_thresholds") or {"prefix_contains": 0.90, "token_jaccard": 0.70}

    # Read input
    header, rows = read_csv_rows(args.input)

    # Extend header with output columns (if missing)
    out_cols = [
        "neighborhood_raw", "neighborhood_type", "neighborhood_clean",
        "neighborhood_id", "neighborhood_label", "match_confidence", "match_method",
        "is_building", "building_name",
    ]
    for c in out_cols:
        if c not in header:
            header.append(c)

    # Process rows
    unmatched_counter: Counter = Counter()
    matched_rows: List[Dict[str, str]] = []

    for r in rows:
        raw_nb = r.get("neighborhood", "")
        if not r.get("neighborhood_raw"):
            r["neighborhood_raw"] = raw_nb

        # Normalize the raw field for cleaning
        norm = normalize_label(raw_nb, cfg)
        ntype, core = extract_type_and_core(norm, cfg)
        # clamp/adapt
        core_clamped = clamp_adaptive(core, ntype, exact_index, thresholds, cfg)
        r["neighborhood_type"] = ntype
        r["neighborhood_clean"] = core_clamped

        # Build candidates for matching (with and without type)
        candidates = []
        if core_clamped:
            candidates.append(core_clamped)
            if ntype:
                prefix = (cfg.get("type_to_prefix", {}).get(ntype) or "").strip()
                if prefix:
                    candidates.append(f"{prefix} {core_clamped}")

        # Try candidates in order
        nid = lbl = ""
        conf = 0.0
        method = "none"
        for cand in candidates:
            nid, lbl, conf, method = try_match(cand, exact_index, token_index, thresholds)
            if nid:
                break

        # Record match columns
        r["neighborhood_id"] = nid
        r["neighborhood_label"] = nfkc_upper(lbl) if lbl else ""
        r["match_confidence"] = f"{conf:.3f}"
        r["match_method"] = method

        # Unmatched accounting (by normalized cleaned candidate)
        if not nid:
            key = core_clamped or norm or (raw_nb or "").strip() or "<EMPTY>"
            unmatched_counter[key] += 1

        # Building enrichment (optional)
        if args.no_building:
            r.setdefault("is_building", "")
            r.setdefault("building_name", "")
        else:
            is_b, bname = enrich_building_fields(r, cfg)
            r["is_building"] = is_b
            r["building_name"] = bname

        matched_rows.append(r)

    # Write matched rows
    write_csv(args.out_matched, header, matched_rows)

    # Unmatched summary
    um_rows = [{"candidate": k, "frequency": str(v)} for k, v in unmatched_counter.most_common()]
    write_csv(args.out_unmatched, ["candidate", "frequency"], um_rows)

    print(f"✅ Done. Rows processed: {len(rows)} | Unique unmatched candidates: {len(unmatched_counter)}")
    print(f"   Matched → {args.out_matched}")
    print(f"   Unmatched → {args.out_unmatched}")

if __name__ == "__main__":
    main()
