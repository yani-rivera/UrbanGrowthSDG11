#!/usr/bin/env python3
"""
Match cleaned listings to neighborhood catalog (aliases) → GISID / UID
- Repairs mojibake (CASTA√ëOS → CASTAÑOS)
- Preserves Ñ distinct from N
- Expands month abbreviations (SEP., SEPT. → SEPTIEMBRE)
- Strips OCR tails (SEPT.z* → SEPTIEMBRE)
- Deterministic: exact normalized alias match only
"""

import argparse, csv, re, unicodedata
import pandas as pd

# ---------- Mojibake repair ----------
MOJIBAKE_FIXES = {
    "√±": "ñ", "√ë": "Ñ",
    "Ã±": "ñ", "Ã‘": "Ñ",
    "Ã¡": "á", "Ã©": "é", "Ãí": "í", "Ã³": "ó", "Ãº": "ú",
    "ÃÁ": "Á", "Ã‰": "É", "ÃÍ": "Í", "Ã“": "Ó", "Ãš": "Ú",
    "Â": "",
}
def fix_mojibake(s: str) -> str:
    t = "" if s is None else str(s)
    for bad, good in MOJIBAKE_FIXES.items():
        t = t.replace(bad, good)
    return t

# ---------- Ñ-preserving normalization ----------
_WS_RE = re.compile(r"\s+")
_PUNCT = re.compile(r"[^A-ZÑ0-9\s/\-\.]")  # allow Ñ

def strip_accents_preserve_ene(s: str) -> str:
    s = "" if s is None else str(s)
    s = s.replace("Ñ","##ENE_UP##").replace("ñ","##ene_low##")
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = s.replace("##ENE_UP##","Ñ").replace("##ene_low##","ñ")
    return s.upper()

def normalize_key(s: str) -> str:
    s = strip_accents_preserve_ene(s)
    s = _PUNCT.sub(" ", s)
    s = _WS_RE.sub(" ", s).strip()
    return s

# ---------- Month expansions + OCR tails ----------
MONTH_MAP = [
    (r"\bENE\.?\b", "ENERO"),
    (r"\bFEB\.?\b", "FEBRERO"),
    (r"\bMAR\.?\b", "MARZO"),
    (r"\bABR\.?\b", "ABRIL"),
    (r"\bMAY\.?\b", "MAYO"),
    (r"\bJUN\.?\b", "JUNIO"),
    (r"\bJUL\.?\b", "JULIO"),
    (r"\bAGO\.?\b", "AGOSTO"),
    (r"\bSET\.?\b|\bSEP\.?T?\.?\b", "SEPTIEMBRE"),
    (r"\bOCT\.?\b", "OCTUBRE"),
    (r"\bNOV\.?\b", "NOVIEMBRE"),
    (r"\bDIC\.?\b", "DICIEMBRE"),
]
def expand_months(s: str) -> str:
    t = s
    for pat, repl in MONTH_MAP:
        t = re.sub(pat, repl, t, flags=re.IGNORECASE)
    return t

OCR_TAIL_RE = re.compile(r"\b(SEPTIEMBRE|SEPT|SEP|SET)\.[A-Z\*]+\b", re.IGNORECASE)
def strip_ocr_tails(s: str) -> str:
    return OCR_TAIL_RE.sub(lambda m: m.group(1), s)

def prep_key(s: str) -> str:
    """mojibake → month expand → strip OCR tails → Ñ-preserving normalize"""
    return normalize_key(strip_ocr_tails(expand_months(fix_mojibake(s))))

# ---------- Main ----------
def main():
    ap = argparse.ArgumentParser(description="Match cleaned neighborhoods to catalog aliases → GIS code")
    ap.add_argument("--listings_csv", required=True, help="Cleaned listings CSV")
    ap.add_argument("--listings_col", default="neighborhood_clean_norm",
                    help="Column in listings to match on (recommend neighborhood_clean_norm)")
    ap.add_argument("--catalog_csv", required=True, help="Catalog CSV with columns: uid,GISID,name,alias")
    ap.add_argument("--out_merged", required=True, help="All rows with match columns appended")
    ap.add_argument("--out_matched", required=True, help="Only matched rows")
    ap.add_argument("--out_unmatched", required=True, help="Unmatched frequency table")
    ap.add_argument("--encoding", default="utf-8")
    args = ap.parse_args()

    # Read CSVs
    L = pd.read_csv(args.listings_csv, encoding=args.encoding)
    C = pd.read_csv(args.catalog_csv, encoding=args.encoding)

    # Validate columns
    if args.listings_col not in L.columns:
        raise SystemExit(f"Listings missing column '{args.listings_col}'. Columns: {list(L.columns)}")
    for req in ["uid","GISID","name","alias"]:
        if req not in C.columns:
            raise SystemExit(f"Catalog missing column '{req}'. Columns: {list(C.columns)}")

    # Build normalized keys
    L["match_key"] = L[args.listings_col].astype(str).map(prep_key)
    C["alias_key"] = C["alias"].astype(str).map(prep_key)

    # Alias → (uids, gisids, names)
    grp = C.groupby("alias_key").agg({
        "uid":   lambda s: list(pd.unique(s)),
        "GISID": lambda s: list(pd.unique(s)),
        "name":  lambda s: list(pd.unique(s)),
    }).reset_index()
    alias_map = {row["alias_key"]: (row["uid"], row["GISID"], row["name"]) for _, row in grp.iterrows()}

    # Match
    match_uid, match_gis, match_name, match_status, candidates = [], [], [], [], []
    for key in L["match_key"]:
        if key in alias_map:
            uids, gises, names = alias_map[key]
            if len(uids) == 1:
                match_uid.append(uids[0])
                match_gis.append(gises[0] if gises else "")
                match_name.append(names[0] if names else "")
                match_status.append("exact_alias")
                candidates.append("")
            else:
                match_uid.append("")
                match_gis.append("")
                match_name.append("")
                match_status.append("ambiguous_alias_multi_uid")
                candidates.append("|".join(uids))
        else:
            match_uid.append("")
            match_gis.append("")
            match_name.append("")
            match_status.append("unmatched")
            candidates.append("")

    # Append outputs
    L["neighborhood_uid"]   = match_uid
    L["GISID"]              = match_gis
    L["neighborhood_label"] = match_name
    L["match_method"]       = match_status
    L["uid_candidates"]     = candidates

    # Write files
    L.to_csv(args.out_merged, index=False, encoding=args.encoding)
    L[L["match_method"] != "unmatched"].to_csv(args.out_matched, index=False, encoding=args.encoding)

    um = L[L["match_method"] == "unmatched"]["match_key"].value_counts().reset_index()
    um.columns = ["candidate","frequency"]
    um.to_csv(args.out_unmatched, index=False, encoding=args.encoding)

    print(f"Done. Matched: {(L['match_method']!='unmatched').sum()} / {len(L)}")
    print(f"All rows  → {args.out_merged}")
    print(f"Matched   → {args.out_matched}")
    print(f"Unmatched → {args.out_unmatched}")

if __name__ == "__main__":
    main()
