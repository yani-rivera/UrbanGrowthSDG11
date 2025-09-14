#!/usr/bin/env python3
"""
neighborhood_unify.py — unify two neighborhood CSVs into one canonical file

- Matches rows across two CSVs using the common column 'Neighborhood' (messy names OK).
- Produces a single unified CSV with a full column union (A__*, B__*), plus
  canonical leaders: neighborhood_id, canonical_name, match_status, match_score, aliases.
- Designed for a single city (no geo blocking). If geo columns exist, they are preserved.

Usage
-----
python neighborhood_unify.py \
  --a neighborhoods_A.csv \
  --b neighborhoods_B.csv \
  --out neighborhoods_unified.csv \
  --field-a Neighborhood \
  --field-b Neighborhood \
  --auto-threshold 0.92 \
  --review-threshold 0.80 \
  --prefixes "col,col.,colonia,res,res.,residencial,fracc,fracc.,fraccionamiento,urb,urb.,villa,villas,barrio,conj,conjunto"

Notes
-----
- We do not drop or reconcile conflicting fields; you select columns later.
- All original columns are preserved and namespaced under A__ and B__.
- Matching transparency: each output row includes match_status and score.
"""
import unicodedata
import string
import argparse
import csv
import unicodedata
import string
from collections import defaultdict
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Dict, List, Tuple, Optional, Set

# -------------------------
# Text normalization
# -------------------------

def strip_accents(s: str) -> str:
    """Remove diacritics from a string (Á→A, ñ→n)."""
    # Normalize to NFKD then drop combining marks
    return ''.join(c for c in unicodedata.normalize('NFKD', s) if not unicodedata.combining(c))


def normalize_whitespace(s: str) -> str:
    """Collapse any whitespace (including NBSP/ZWSP) to single ASCII spaces."""
    # Replace common non-breaking / zero-width spaces with normal spaces
    s = s.replace(' ', ' ').replace('​', '').replace(' ', ' ').replace(' ', ' ')
    return ' '.join(s.split())




def clean_name(raw: str) -> str:
    """
    Unicode-safe normalizer:
    - Normalize to NFKC (compatibility: ligatures, etc.)
    - Remove diacritics (NFKD + drop combining marks)
    - Uppercase
    - Replace all punctuation with spaces
    - Collapse whitespace
    """
    s = (raw or "").strip()
    # 1) Normalize to NFKC first (handles ligatures, compatibility)
    s = unicodedata.normalize("NFKC", s)
    # 2) Decompose, remove accents
    s = ''.join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))
    # 3) Uppercase
    s = s.upper()
    # 4) Replace punctuation with spaces
    s = s.translate(str.maketrans({c: " " for c in string.punctuation}))
    # 5) Normalize spaces
    s = " ".join(s.split())
    return s



def token_base(name: str, stopwords: Set[str]) -> List[str]:
    tokens = clean_name(name).split()
    # stopwords are compared in upper-case now
    sw = {w.upper() for w in stopwords}
    tokens = [t for t in tokens if t not in sw]
    kept = []
    for t in tokens:
        if len(t) <= 1 and not t.isdigit():
            continue
        kept.append(t)
    return sorted(kept)

# -------------------------
# Similarity metrics
# -------------------------

def jaccard_token_set(a_tokens: List[str], b_tokens: List[str]) -> float:
    A, B = set(a_tokens), set(b_tokens)
    if not A and not B:
        return 1.0
    if not A or not B:
        return 0.0
    inter = len(A & B)
    union = len(A | B)
    return inter / union if union else 0.0

# Simple Jaro-Winkler implementation for robustness on transpositions
# (kept compact and safe for moderately sized strings)

def jaro_winkler(s1: str, s2: str, p: float = 0.1, max_l: int = 4) -> float:
    s1 = clean_name(s1)
    s2 = clean_name(s2)
    if s1 == s2:
        return 1.0
    len1, len2 = len(s1), len(s2)
    if len1 == 0 or len2 == 0:
        return 0.0
    match_distance = max(len1, len2) // 2 - 1
    s1_matches = [False] * len1
    s2_matches = [False] * len2
    matches = 0
    transpositions = 0

    for i in range(len1):
        start = max(0, i - match_distance)
        end = min(i + match_distance + 1, len2)
        for j in range(start, end):
            if s2_matches[j]:
                continue
            if s1[i] != s2[j]:
                continue
            s1_matches[i] = True
            s2_matches[j] = True
            matches += 1
            break
    if matches == 0:
        return 0.0

    k = 0
    for i in range(len1):
        if not s1_matches[i]:
            continue
        while not s2_matches[k]:
            k += 1
        if s1[i] != s2[k]:
            transpositions += 1
        k += 1
    transpositions //= 2

    jaro = (
        (matches / len1 + matches / len2 + (matches - transpositions) / matches) / 3.0
    )
    # Winkler boost for common prefix
    prefix = 0
    for i in range(min(min(len1, len2), max_l)):
        if s1[i] == s2[i]:
            prefix += 1
        else:
            break
    return jaro + prefix * p * (1 - jaro)


def seq_ratio(a: str, b: str) -> float:
    return SequenceMatcher(None, clean_name(a), clean_name(b)).ratio()

# Fuzzy token Jaccard: counts tokens as equal if identical OR very similar
# Useful for minor typos like OBELISCC vs OBELISCO

def fuzzy_token_jaccard(a_tokens: List[str], b_tokens: List[str], threshold: float = 0.88) -> float:
    A = list(a_tokens)
    B = list(b_tokens)
    if not A and not B:
        return 1.0
    if not A or not B:
        return 0.0
    used_b = set()
    inter = 0
    for i, ta in enumerate(A):
        best_j = -1
        best_sim = 0.0
        for j, tb in enumerate(B):
            if j in used_b:
                continue
            # exact match first
            if ta == tb:
                best_j = j
                best_sim = 1.0
                break
            # similarity on tokens
            s = SequenceMatcher(None, ta, tb).ratio()
            if s > best_sim:
                best_sim = s
                best_j = j
        if best_j >= 0 and best_sim >= threshold:
            used_b.add(best_j)
            inter += 1
    union = len(set(A)) + len(set(B)) - inter
    return inter / union if union else 0.0

@dataclass
class NameFeatures:
    original: str
    norm: str
    base_tokens: List[str]

# -------------------------
# Matching engine
# -------------------------

def build_features(rows: List[Dict[str, str]], field: str, stopwords: Set[str]) -> List[NameFeatures]:
    feats: List[NameFeatures] = []
    for r in rows:
        raw = (r.get(field) or '').strip()
        feats.append(NameFeatures(original=raw, norm=clean_name(raw), base_tokens=token_base(raw, stopwords)))
    return feats


def score_pair(a: NameFeatures, b: NameFeatures) -> float:
    # If token sets are exactly equal and non-empty, call it a perfect match
    if a.base_tokens and a.base_tokens == b.base_tokens:
        return 1.0
    # Weighted blend: token Jaccard + Jaro-Winkler + SequenceMatcher
    jacc = jaccard_token_set(a.base_tokens, b.base_tokens)
    jw = jaro_winkler(a.original, b.original)
    sr = seq_ratio(a.original, b.original)
    score = 0.45 * jacc + 0.35 * jw + 0.20 * sr
    # Containment boost: if one normalized string contains the other (post-clean)
    if a.norm and b.norm and (a.norm in b.norm or b.norm in a.norm):
        score = max(score, min(1.0, score + 0.1))
    return score


def best_matches(A_feats: List[NameFeatures], B_feats: List[NameFeatures]) -> Tuple[List[int], List[float]]:
    # For each A, find best B index & score
    best_idx = [-1] * len(A_feats)
    best_score = [0.0] * len(A_feats)
    # Blocking by first token of base to reduce false positives
    index_B: Dict[str, List[int]] = defaultdict(list)
    for j, bf in enumerate(B_feats):
        key = bf.base_tokens[0] if bf.base_tokens else ''
        index_B[key].append(j)
    for i, af in enumerate(A_feats):
        candidates = index_B.get(af.base_tokens[0] if af.base_tokens else '', [])
        # Fall back to all if no candidates (rare edge)
        if not candidates:
            candidates = range(len(B_feats))
        for j in candidates:
            s = score_pair(af, B_feats[j])
            if s > best_score[i]:
                best_score[i] = s
                best_idx[i] = j
    return best_idx, best_score

# -------------------------
# Canonicalization
# -------------------------

def titleize_base(tokens: List[str]) -> str:
    # Canonical form is ALL UPPERCASE, tokens joined with single spaces
    return ' '.join(t.upper() for t in tokens)

# -------------------------
# Main unify logic
# -------------------------

def unify(a_path: str, b_path: str, out_path: str, field_a: str = 'Neighborhood', field_b: str = 'Neighborhood', auto_thr: float = 0.92, review_thr: float = 0.80, prefixes: str = '') -> None:
    # Parse stopwords/prefixes
    stop = {p.strip().lower() for p in prefixes.split(',') if p.strip()}

    # Load CSVs
    with open(a_path, newline='', encoding='utf-8-sig') as fa:
        ra = list(csv.DictReader(fa))
    with open(b_path, newline='', encoding='utf-8-sig') as fb:
        rb = list(csv.DictReader(fb))

    # Build features
    A_feats = build_features(ra, field_a, stop)
    B_feats = build_features(rb, field_b, stop)

    # Best matches A->B and B->A
    A_to_B, A_scores = best_matches(A_feats, B_feats)
    B_to_A, B_scores = best_matches(B_feats, A_feats)

    # Build unified columns (union)
    a_cols = list(ra[0].keys()) if ra else []
    b_cols = list(rb[0].keys()) if rb else []

    lead_cols = ['neighborhood_id', 'canonical_name', 'match_status', 'match_score', 'aliases']
    out_cols = lead_cols + [f'A__{c}' for c in a_cols] + [f'B__{c}' for c in b_cols]

    # Prepare output
    out_rows: List[Dict[str, str]] = []

    # Track B rows already paired to avoid duplicate auto matches
    paired_B: Set[int] = set()

    # Helper to compute canonical + aliases
    def canonical_and_aliases(a_idx: Optional[int], b_idx: Optional[int]) -> Tuple[str, str]:
        variants: List[str] = []
        if a_idx is not None and a_idx >= 0:
            variants.append(A_feats[a_idx].original)
        if b_idx is not None and b_idx >= 0:
            variants.append(B_feats[b_idx].original)
        # Derive canonical from tokens union
        tokens: Set[str] = set()
        if a_idx is not None and a_idx >= 0:
            tokens.update(A_feats[a_idx].base_tokens)
        if b_idx is not None and b_idx >= 0:
            tokens.update(B_feats[b_idx].base_tokens)
        canonical = titleize_base(sorted(tokens)) if tokens else (variants[0].title() if variants else '')
        aliases = ';'.join(sorted({v for v in variants if v}))
        return canonical, aliases

    # Assign IDs
    def make_id(n: int) -> str:
        return f'NEI-{n:06d}'

    next_id = 1
    id_for_A: Dict[int, str] = {}
    id_for_B: Dict[int, str] = {}

    # Pass 1: Create rows for each A, try to attach best B when mutual best & score >= thresholds
    for i, arow in enumerate(ra):
        j = A_to_B[i]
        score = A_scores[i]
        attach_b = -1
        status = 'no_match'
        if j >= 0:
            # Mutual best check
            if B_to_A[j] == i:
                if score >= auto_thr:
                    status = 'auto'
                    attach_b = j
                elif score >= review_thr:
                    status = 'review'
                    attach_b = j
            else:
                if score >= review_thr:
                    status = 'review'
                    attach_b = j
        nid = make_id(next_id)
        next_id += 1
        id_for_A[i] = nid
        if attach_b >= 0:
            id_for_B.setdefault(attach_b, nid)
            paired_B.add(attach_b)
        canonical, aliases = canonical_and_aliases(i, attach_b if attach_b >= 0 else None)
        out = {c: '' for c in out_cols}
        out['neighborhood_id'] = nid
        out['canonical_name'] = canonical
        out['match_status'] = status
        out['match_score'] = f"{score:.4f}"
        out['aliases'] = aliases
        for c in a_cols:
            out[f'A__{c}'] = arow.get(c, '')
        if attach_b >= 0:
            brow = rb[attach_b]
            for c in b_cols:
                out[f'B__{c}'] = brow.get(c, '')
        out_rows.append(out)

    # Pass 2: Add B-only rows not paired yet
    for j, brow in enumerate(rb):
        if j in paired_B:
            continue
        # This row did not get paired above — determine status versus its best A
        i = B_to_A[j]
        score = B_scores[j]
        if i >= 0 and score >= review_thr:
            status = 'review'
        else:
            status = 'no_match'
        nid = id_for_B.get(j)
        if not nid:
            nid = make_id(next_id)
            next_id += 1
        canonical, aliases = canonical_and_aliases(i if i >= 0 else None, j)
        out = {c: '' for c in out_cols}
        out['neighborhood_id'] = nid
        out['canonical_name'] = canonical
        out['match_status'] = status
        out['match_score'] = f"{score:.4f}"
        out['aliases'] = aliases
        for c in b_cols:
            out[f'B__{c}'] = brow.get(c, '')
        out_rows.append(out)

    # Write output
    with open(out_path, 'w', newline='', encoding='utf-8') as fo:
        w = csv.DictWriter(fo, fieldnames=out_cols)
        w.writeheader()
        for r in out_rows:
            w.writerow(r)

# -------------------------
# CLI
# -------------------------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--a', required=True, help='Path to neighborhoods_A.csv')
    ap.add_argument('--b', required=True, help='Path to neighborhoods_B.csv')
    ap.add_argument('--out', required=True, help='Path to unified output CSV')
    ap.add_argument('--field-a', default='Neighborhood')
    ap.add_argument('--field-b', default='Neighborhood')
    ap.add_argument('--auto-threshold', type=float, default=0.92)
    ap.add_argument('--review-threshold', type=float, default=0.80)
    ap.add_argument('--prefixes', default='col,col.,colonia,res,res.,residencial,fracc,fracc.,fraccionamiento,urb,urb.,villa,villas,barrio,conj,conjunto')
    args = ap.parse_args()

    unify(
        a_path=args.a,
        b_path=args.b,
        out_path=args.out,
        field_a=args.field_a,
        field_b=args.field_b,
        auto_thr=args.auto_threshold,
        review_thr=args.review_threshold,
        prefixes=args.prefixes,
    )

if __name__ == '__main__':
    main()
