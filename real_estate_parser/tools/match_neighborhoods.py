
#!/usr/bin/env python3
# tools/match_neighborhoods.py
"""
Match parsed neighborhoods to an official gazetteer.

Inputs
  --input <CSV>        Consolidated rows (e.g., output/consolidated/2025/merged_20250901.csv)
  --official <CSV/JSON> Official list with columns/fields:
                        CSV: id,name[,aliases]  (aliases optional; pipe-separated)
                        JSON: [{"id": "...", "name": "...", "aliases": ["..",".."]}, ...]
  --out-matched <CSV>  Output matched rows (same as input + mapping columns)
  --out-unmatched <CSV> Aggregated unmatched candidates for review (freq, suggestion)

Behavior
  - Tries: exact (normalized), alias-exact, prefix/contains, token-Jaccard similarity.
  - Adds: neighborhood_id, neighborhood_label, match_confidence (0.0–1.0), match_method.
  - For unmatched: groups by candidate, counts frequency, suggests parent by token overlap.

Usage
  python tools/match_neighborhoods.py \
      --input output/consolidated/2025/merged_2025.csv \
      --official data/neighborhoods_official.csv \
      --out-matched output/consolidated/2025/merged_2025_matched.csv \
      --out-unmatched output/consolidated/2025/merged_2025_unmatched.csv

Optional
  --field-neighborhood neighborhood_clean   # default; falls back to 'neighborhood' if empty
  --uppercase                                # force uppercase label in output (default)
  --no-uppercase
  --min-jaccard 0.6                          # token Jaccard acceptance threshold
  --min-prefix 0.9                           # relative prefix/contains acceptance threshold (len-based)
"""

import argparse, csv, json, os, sys, unicodedata, re
from collections import defaultdict, Counter
from typing import Dict, List, Tuple, Iterable, Optional

# ---------- Normalization & tokenization ----------

TYPE_STOPWORDS = {
    "CASA","APTO","APARTAMENTO","CONDOMINIO","TOWN","HOUSE","VILLA","LOCAL","BODEGA",
    "EDIF","EDIFICIO","TORRE","RESIDENCIA","RESIDENCIAL","RES","RES.","URB","URB.","URBANIZACION",
    "COL","COL.","COLONIA","BARRIO","BO","BO.","AVE","AVE.","AV","AV.","BLVD","BLVD.","BOULEVARD"
}

CURRENCY_TOKENS = {"$", "US$", "USD", "HNL", "L.", "LPS", "LPS."}

def nfkc_upper(s: str) -> str:
    return unicodedata.normalize("NFKC", (s or "")).upper().strip()

def strip_accents(s: str) -> str:
    # Keep NFKD + remove diacritics, then back to NFKC
    nfkd = unicodedata.normalize("NFKD", s)
    noacc = "".join(ch for ch in nfkd if not unicodedata.combining(ch))
    return unicodedata.normalize("NFKC", noacc)

def normalize_label(s: str) -> str:
    s = nfkc_upper(s)
    s = strip_accents(s)
    # Remove currency & numbers at edges
    s = re.sub(r"^(\$|US\$|USD|HNL|LPS?\.?|L\.)[\s\d.,\-]*", "", s)
    s = re.sub(r"[\s,;:/\|\-]*$", "", s)
    # Collapse punctuation to spaces, normalize whitespace
    s = re.sub(r"[^\w\s\.]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

def tokens(s: str) -> List[str]:
    s = normalize_label(s)
    raw = re.split(r"[\s,;:/\|\-]+", s)
    toks = [t for t in raw if t and t not in TYPE_STOPWORDS and t not in CURRENCY_TOKENS and not t.isdigit()]
    return toks

def jaccard(a: Iterable[str], b: Iterable[str]) -> float:
    A, B = set(a), set(b)
    if not A and not B: return 1.0
    if not A or not B:  return 0.0
    return len(A & B) / len(A | B)

# ---------- Gazetteer loading ----------

def load_official(path: str) -> List[Dict[str, str]]:
    if path.lower().endswith(".json"):
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        out = []
        for row in data:
            out.append({
                "id": str(row.get("id","")).strip(),
                "name": str(row.get("name","")).strip(),
                "aliases": "|".join(row.get("aliases") or [])
            })
        return out
    # CSV
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        need = {"id","name"}
        if not need.issubset(set(map(str.lower, reader.fieldnames or []))):
            # try exact-case
            need = {"id","name"}
        rows = []
        for r in reader:
            rows.append({
                "id": r.get("id","") or r.get("ID",""),
                "name": r.get("name","") or r.get("NAME",""),
                "aliases": r.get("aliases","") or r.get("ALIASES","")
            })
        return rows

def build_index(official: List[Dict[str,str]]) -> Tuple[Dict[str, Tuple[str,str]], Dict[str, List[Tuple[str,str]]], Dict[str, List[Tuple[str,str]]]]:
    """
    Returns:
      exact_index: norm_name -> (id, label)
      alias_index: norm_alias -> [(id, label)]
      token_index: token -> [(id, label)]
    """
    exact_index: Dict[str, Tuple[str,str]] = {}
    alias_index: Dict[str, List[Tuple[str,str]]] = defaultdict(list)
    token_index: Dict[str, List[Tuple[str,str]]] = defaultdict(list)

    for row in official:
        nid = str(row["id"]).strip()
        name = str(row["name"]).strip()
        if not nid or not name: continue
        norm = normalize_label(name)
        exact_index[norm] = (nid, name)
        # aliases
        aliases = []
        if row.get("aliases"):
            aliases = [a.strip() for a in str(row["aliases"]).split("|") if a.strip()]
        for a in aliases:
            na = normalize_label(a)
            alias_index[na].append((nid, name))
        # token index for suggestions
        for t in set(tokens(name)):
            token_index[t].append((nid, name))
        for a in aliases:
            for t in set(tokens(a)):
                token_index[t].append((nid, name))
    return exact_index, alias_index, token_index

# ---------- Matching ----------

def match_one(cand: str,
              exact_index, alias_index, token_index,
              min_jaccard: float, min_prefix: float) -> Tuple[str,str,float,str]:
    """
    Returns: (neighborhood_id, neighborhood_label, confidence, method)
    or ("","",0.0,"none")
    """
    raw = cand or ""
    if not raw.strip():
        return "","",0.0,"none"

    norm = normalize_label(raw)
    if not norm:
        return "","",0.0,"none"

    # 1) Exact name
    if norm in exact_index:
        nid, lbl = exact_index[norm]
        return nid, lbl, 1.0, "exact"

    # 2) Exact alias
    if norm in alias_index:
        nid, lbl = alias_index[norm][0]
        return nid, lbl, 0.98, "alias_exact"

    # 3) Prefix/contains against official names (len-aware)
    #    Try quick pass over exact_index keys
    for k, (nid, lbl) in exact_index.items():
        if k.startswith(norm):
            # confidence grows with proportion of covered length
            conf = min(0.97, max(0.85, len(norm) / max(len(k), 1)))
            if conf >= min_prefix:
                return nid, lbl, conf, "prefix_name"
        if norm.startswith(k):
            conf = min(0.95, max(0.80, len(k) / max(len(norm), 1)))
            if conf >= min_prefix:
                return nid, lbl, conf, "contains_name"

    # 4) Token Jaccard (order-insensitive)
    toks_c = tokens(norm)
    best = ("","",0.0,"none")
    if toks_c:
        # Gather candidates by shared tokens to reduce comparisons
        bucket: Dict[Tuple[str,str], int] = {}
        for t in set(toks_c):
            for nid, lbl in token_index.get(t, []):
                bucket[(nid, lbl)] = bucket.get((nid,lbl), 0) + 1
        # Score by Jaccard
        for (nid,lbl), _ in bucket.items():
            conf = jaccard(set(toks_c), set(tokens(lbl)))
            if conf > best[2]:
                best = (nid, lbl, conf, "token_jaccard")
        if best[2] >= min_jaccard:
            return best

    return "","",0.0,"none"

def suggest_parent(cand: str, exact_index, token_index) -> Tuple[str,str,float]:
    """Suggest an official parent by token overlap—useful for gated communities."""
    toks_c = tokens(cand)
    if not toks_c:
        return "","",0.0
    best = ("","",0.0)
    bucket: Dict[Tuple[str,str], int] = {}
    for t in set(toks_c):
        for nid, lbl in token_index.get(t, []):
            bucket[(nid,lbl)] = bucket.get((nid,lbl), 0) + 1
    for (nid,lbl), _ in bucket.items():
        score = jaccard(set(toks_c), set(tokens(lbl)))
        if score > best[2]:
            best = (nid, lbl, score)
    return best

# ---------- IO ----------

def read_csv_rows(path: str) -> Tuple[List[str], List[Dict[str,str]]]:
    for enc in ("utf-8-sig","utf-8"):
        try:
            with open(path, "r", encoding=enc, newline="") as f:
                r = csv.DictReader(f)
                return (r.fieldnames or []), [dict(x) for x in r]
        except UnicodeDecodeError:
            continue
    with open(path, "r", encoding="latin-1", newline="") as f:
        r = csv.DictReader(f)
        return (r.fieldnames or []), [dict(x) for x in r]

def write_csv(path: str, header: List[str], rows: List[Dict[str,str]]) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=header)
        w.writeheader()
        w.writerows(rows)

# ---------- Main ----------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, help="Consolidated CSV to match")
    ap.add_argument("--official", required=True, help="Official neighborhoods list (CSV or JSON)")
    ap.add_argument("--out-matched", required=True, help="Output CSV with mapping columns added")
    ap.add_argument("--out-unmatched", required=True, help="Output CSV with unmatched report")
    ap.add_argument("--field-neighborhood", default="neighborhood_clean",
                    help="Source field; falls back to 'neighborhood' if empty")
    ap.add_argument("--min-jaccard", type=float, default=0.70, help="Min token Jaccard to accept")
    ap.add_argument("--min-prefix", type=float, default=0.90, help="Min confidence to accept prefix/contains")
    ap.add_argument("--uppercase", dest="uppercase", action="store_true", default=True)
    ap.add_argument("--no-uppercase", dest="uppercase", action="store_false")
    args = ap.parse_args()

    print("→ Loading official list…")
    official_rows = load_official(args.official)
    exact_idx, alias_idx, token_idx = build_index(official_rows)
    print(f"   Official entries: {len(exact_idx)} (names) | aliases: {sum(len(v) for v in alias_idx.values())}")

    print("→ Reading input rows…")
    header, rows = read_csv_rows(args.input)
    print(f"   Rows: {len(rows)}")

    # Extend header
    add_cols = ["neighborhood_raw","neighborhood_id","neighborhood_label","match_confidence","match_method"]
    for c in add_cols:
        if c not in header: header.append(c)

    matched_rows: List[Dict[str,str]] = []
    unmatched_counter: Counter = Counter()
    unmatched_suggestions: Dict[str, Tuple[str,str,float]] = {}

    for r in rows:
        source = r.get(args.field_neighborhood,"") or r.get("neighborhood","") or ""
        if r.get("neighborhood_raw","") == "":
            r["neighborhood_raw"] = source

        nid, lbl, conf, method = match_one(source, exact_idx, alias_idx, token_idx,
                                           args.min_jaccard, args.min_prefix)
        r["neighborhood_id"] = nid
        r["neighborhood_label"] = nfkc_upper(lbl) if (lbl and args.uppercase) else lbl
        r["match_confidence"] = f"{conf:.3f}"
        r["match_method"] = method

        if not nid:
            # aggregate unmatched for review
            cand = normalize_label(source)
            if not cand:
                cand = (source or "").strip()
            if not cand:
                cand = "<EMPTY>"
            unmatched_counter[cand] += 1
            if cand not in unmatched_suggestions:
                pnid, plbl, pscore = suggest_parent(cand, exact_idx, token_idx)
                unmatched_suggestions[cand] = (pnid, plbl, pscore)

        matched_rows.append(r)

    print("→ Writing matched rows…")
    write_csv(args.out_matched, header, matched_rows)

    print("→ Writing unmatched report…")
    # Build unmatched table
    um_rows: List[Dict[str,str]] = []
    for cand, freq in unmatched_counter.most_common():
        pnid, plbl, pscore = unmatched_suggestions.get(cand, ("","",0.0))
        um_rows.append({
            "candidate": cand,
            "frequency": str(freq),
            "suggested_parent_id": pnid,
            "suggested_parent_label": nfkc_upper(plbl) if (plbl and args.uppercase) else plbl,
            "suggested_parent_score": f"{pscore:.3f}"
        })
    um_header = ["candidate","frequency","suggested_parent_id","suggested_parent_label","suggested_parent_score"]
    write_csv(args.out_unmatched, um_header, um_rows)

    matched = len(matched_rows) - sum(1 for r in matched_rows if not r.get("neighborhood_id"))
    print(f"✅ Done. Matches: {matched} | Unmatched: {len(unmatched_counter)} unique candidates")
    print(f"   Matched → {args.out_matched}")
    print(f"   Unmatched → {args.out_unmatched}")

if __name__ == "__main__":
    main()
