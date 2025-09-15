#!/usr/bin/env python3
"""
SplitByCue_v2 — robust line segmentation for agencies with/without listing markers.

Features
- Supports explicit listing markers (e.g., "*", "•").
- Markerless mode: segment by CUE:COMMA or CUE:DOT at start-of-line neighborhood header.
- Guards for thousands commas, decimals, ellipses, and common abbreviations (COL., RES., BO.).
- Optional price/bed hint lookahead to avoid false positives.
- Normalizes common bullet variants into the configured marker.
- Accepts cue via literals or CUE tokens: CUE:COMMA, CUE:DOT, CUE:regex:... / CUE:regex=...

Config keys (examples)
{
  "listing_marker": "*",                  # or null/omitted for markerless mode
  "neighborhood_delimiter": "CUE:COMMA",  # or "CUE:DOT" or "CUE:regex:(?<=\\bCol\\.)[^:]+:"
  "max_cue_pos": 40,
  "min_name_words": 1,
  "require_uppercase": true,
  "require_price_after_cue": true,
  "cue_lookahead_chars": 80
}
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Optional, Tuple

# ------------------------- heuristics & regexes ------------------------- #
PRICE_NEAR = re.compile(r"(?:L\.|\$)\s*\d{1,3}(?:,\d{3})*(?:\.\d+)?", re.I)
BED_HINT   = re.compile(r"\b(\d+)\s*(hab|habitaciones|cuartos|dormitorios)\b", re.I)

# abbreviations we allow before a neighborhood name and skip a trailing dot
_ABBR_LEFT = {"col", "res", "bo"}

_COMMON_BULLETS = ("•", "·", "-", "—", "–", "*")

# ----------------------------- cue resolving ---------------------------- #
@dataclass
class CuePlan:
    cue_name: Optional[str] = None   # COMMA | DOT
    cue_regex: Optional[str] = None  # custom regex
    cue_literal: Optional[str] = None


def resolve_cue_from_marker(marker: Optional[str]) -> CuePlan:
    plan = CuePlan()
    if not marker:
        return plan
    s = str(marker).strip()
    if s.upper().startswith("CUE:"):
        token = s.split(":", 1)[1]
        tU = token.upper()
        if tU in {"COMMA", "DOT"}:
            plan.cue_name = tU
            return plan
        m = re.match(r"(?i)^regex[:=](.+)$", token)
        if m:
            plan.cue_regex = m.group(1).strip()
            return plan
        plan.cue_literal = token  # e.g., '•'
        return plan
    # literal char as cue
    plan.cue_literal = s
    return plan

# --------------------------- utilities --------------------------- #

def _uppercase_ratio(s: str) -> float:
    alpha = [c for c in s if c.isalpha()]
    return 0.0 if not alpha else sum(1 for c in alpha if c.isupper()) / len(alpha)


def _first_comma_pair(line: str, maxpos: int) -> Optional[Tuple[str, str]]:
    s = line.strip()
    m = re.search(r'^(.{1,' + str(maxpos) + r'}?),(.*)$', s)
    return (m.group(1), m.group(2)) if m else None


def _first_dot_pair(line: str, maxpos: int) -> Optional[Tuple[str, str]]:
    s = line.strip()
    limit = min(len(s), maxpos)
    i = 0
    while i < limit:
        ch = s[i]
        if ch == '.':
            # ellipses "..."
            if i+2 < len(s) and s[i+1] == '.' and s[i+2] == '.':
                i += 3
                continue
            # decimals: digit '.' digit
            if i-1 >= 0 and i+1 < len(s) and s[i-1].isdigit() and s[i+1].isdigit():
                i += 1
                continue
            # skip abbreviations like 'COL.' 'RES.' 'BO.'
            j = i-1
            while j >= 0 and s[j].isspace():
                j -= 1
            k = j
            while k >= 0 and s[k].isalpha():
                k -= 1
            token_left = s[k+1:j+1].lower()
            if token_left in _ABBR_LEFT:
                i += 1
                continue
            # valid cue
            return (s[:i], s[i+1:])
        i += 1
    return None


def _is_start_by_pair(pair: Tuple[str, str], cfg: dict) -> bool:
    left, right = pair
    left = left.strip()
    if len(left.split()) < int(cfg.get("min_name_words", 1)):
        return False
    if cfg.get("require_uppercase", True) and _uppercase_ratio(left) < 0.6:
        return False
    if cfg.get("require_price_after_cue", True):
        snippet = right[: int(cfg.get("cue_lookahead_chars", 80))]
        if not (PRICE_NEAR.search(snippet) or BED_HINT.search(snippet)):
            return False
    return True

# ---------------------- markerless segmentation ---------------------- #

def split_by_cue_when_no_marker(lines: List[str], cfg: dict) -> List[str]:
    plan = resolve_cue_from_marker(cfg.get("neighborhood_delimiter"))
    maxpos = int(cfg.get("max_cue_pos", 40))

    def first_pair(line: str) -> Optional[Tuple[str, str]]:
        if plan.cue_name == "COMMA":
            return _first_comma_pair(line, maxpos)
        if plan.cue_name == "DOT":
            return _first_dot_pair(line, maxpos)
        if plan.cue_regex:
            m = re.search(plan.cue_regex, line)
            if m:
                span = m.span()
                return (line[:span[0]], line[span[1]:])
        if plan.cue_literal:
            pos = line.find(plan.cue_literal)
            if 0 <= pos <= maxpos:
                return (line[:pos], line[pos+len(plan.cue_literal):])
        return None

    out: List[str] = []
    buf: List[str] = []

    for ln in lines:
        pair = first_pair(ln)
        if pair and _is_start_by_pair(pair, cfg) and buf:
            out.append("\n".join(buf))
            buf = [ln]
        else:
            buf.append(ln)
    if buf:
        out.append("\n".join(buf))
    return out

# ------------------------- bullet normalization ------------------------- #

def normalize_bullets(lines: List[str], marker: str) -> List[str]:
    marker = (marker or "*").strip()
    out: List[str] = []
    for raw in lines:
        line = raw.lstrip()
        if line.startswith(marker):
            out.append(line)
            continue
        if any(line.startswith(b) for b in _COMMON_BULLETS):
            out.append(f"{marker} {line[1:].lstrip()}")
            continue
        if re.match(r"^\d+\.\s+", line):
            out.append(f"{marker} {re.sub(r'^\d+\.\s+', '', line)}")
            continue
        # heuristic: appears to be a head (has colon + price soon after)
        if re.search(r":", line) and PRICE_NEAR.search(line[:120]):
            out.append(f"{marker} {line}")
            continue
        out.append(line)
    return out

# ------------------------------- main API ------------------------------- #

def split_by_cue(lines: List[str], cfg: dict) -> List[str]:
    """Entry point used by preprocessors.
    If listing_marker is present, ensure/normalize bullets and return lines.
    If markerless, segment by cue (COMMA, DOT, regex, or literal) at start-of-line.
    """
    marker = cfg.get("listing_marker")
    if marker:
        # normalize but DO NOT segment; the caller groups by bullets later if needed
        return normalize_bullets(lines, marker)
    # markerless mode
    return split_by_cue_when_no_marker(lines, cfg)

# ------------------------------- self-test ------------------------------- #
if __name__ == "__main__":
    sample = [
        "SAN IGNACIO, 3 HAB, $150,000 sala/comedor",
        "Detalles adicionales...",
        "LOMAS DEL GUIJARRO, APTO, $850 incluye mantenimiento",
        "RES. LA HACIENDA. CASA 3 HAB, $275,000 patio",  # DOT cue variant
    ]
    cfg_comma = {"neighborhood_delimiter": "CUE:COMMA", "max_cue_pos": 40, "require_uppercase": True, "require_price_after_cue": True}
    cfg_dot   = {"neighborhood_delimiter": "CUE:DOT",   "max_cue_pos": 60, "require_uppercase": True, "require_price_after_cue": True}
    print("-- COMMA --")
    for block in split_by_cue(sample, cfg_comma):
        print("[BLOCK]\n" + block)
    print("-- DOT --")
    for block in split_by_cue(sample, cfg_dot):
        print("[BLOCK]\n" + block)
