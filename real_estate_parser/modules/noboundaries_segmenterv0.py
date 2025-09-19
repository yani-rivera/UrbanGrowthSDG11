# noboundaries_segmenter.py
# -------------------------------------------------------------
# Purpose: Segment historic/local classifieds that lack a clear
# listing delimiter into one-line records, preserving headers
# verbatim and collapsing whitespace for listings only.
#
# This module is intentionally independent from SplitByCue.
# It relies on simple, configurable start gates + price proximity.
# Neighborhood boundary punctuation is *not* edited here; keep
# that logic in your downstream extractor if needed.
# -------------------------------------------------------------
from __future__ import annotations

import json
import os
import re
import unicodedata
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Iterable, List, Dict, Any, Optional, Tuple

# -------------------------
# Utilities
# -------------------------

def _fold(s: str) -> str:
    """Lowercase + strip accents + collapse inner spaces.
    Keeps punctuation for simple startswith checks; callers may strip.
    """
    s = s.replace("\u00A0", " ")  # non-breaking space
    s = "".join(c for c in unicodedata.normalize("NFKD", s.lower()) if not unicodedata.combining(c))
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _collapse_ws(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


# -------------------------
# Default config (safe fallbacks)
# -------------------------
DEFAULT_CFG: Dict[str, Any] = {
    "mode": "plain",  # or "anchor" or "auto" (we don't branch much here; kept for compat)
    "windows": {
        "head_window_chars": 60,
        "price_lookahead_lines": 2,
        "price_lookahead_chars": 320,
        "anchor_lookback_chars": 60,
        "min_anchor_gap": 10,
    },
    "start_exceptions": [
        "Mts.", "Mts", "mt2", "m²", "mts", "mts2",
        "Lps", "Lps.", "L.", "$",
        "vr2", "vrs", "Vrs", "Vr²", "Vrs²",
        "area", "área",
        "baños", "baño", "habitaciones", "hab.", "cubículos", "dormitorios",
        "garaje", "lavandería", "cocina", "sala", "comedor",
    ],
    "start_gate": {
        "block_price_first": True,
        "block_area_number_first": True,
        "block_feature_words_first": True,
        "family_tags": ["Res.", "Col.", "Colonia", "Barrio", "Bo."],
        "family_soft_validate": True,
        "connectors": ["de", "del", "la", "las", "los", "y", "el"],
        "family_name_max_tokens": 7,
        "allow_numeric_date_neighborhoods": True,
        "numeric_date_pattern": r"(?i)^[\s\"'“”‘’]*(\d{1,2})(?:º|ro|er)?\s+(?:de|del)\s+(?:enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|setiembre|octubre|noviembre|diciembre)\b",
        "qualifiers_after_name": [
            r"zona\s+\d+", r"sector\s+\d+",
            r"etapa\s+(?:[IVXLC]+|\d+)", r"fase\s+\d+",
            r"km\s+\d+", r"anexo", r"manzana\s+[A-Z0-9]+", r"bloque\s+\w+",
        ],
    },
    "prices": {
        "pattern": r"(?:Lps\.|\$)\s?\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})?",
    },
    "gazetteer": {
        "enabled": True,
        "mode": "hint",  # hint only; still require price
        "prefer_document_lexicon": True,
        "city_gazetteer_path": None,  # set by caller if available
        "fuzzy_max_distance": 1,
        "max_influenced_starts": 30,
        "cooldown_lines": 2,
    },
    "headers": {"keep": True, "preserve_whitespace": True},
    "inline_split": {"clone_per_price": False},
    "output": {
        "target_dir": None,  # if None, derive from agency
        "file_name_format": "pre_<originalfilename>.txt",
        "flatten_whitespace_for": "listings_only",
    },
}


@dataclass
class SegmentMeta:
    agency: Optional[str]
    original_filename: Optional[str]
    wrote: Optional[str]
    counts: Dict[str, int]
    any_newlines: bool
    config_fingerprint: Optional[str]
    seg_version: str = "segment_no_delim.es.v1"


# -------------------------
# Gazetteer (optional hints)
# -------------------------
class Gazetteer:
    def __init__(self, names: Optional[List[str]] = None):
        self.names_norm = set()
        if names:
            for n in names:
                self.names_norm.add(_fold(n))

    @classmethod
    def from_path(cls, path: Optional[str | os.PathLike]):
        if not path:
            return cls([])
        p = Path(path)
        if not p.exists():
            return cls([])
        try:
            with p.open("r", encoding="utf-8") as fh:
                data = json.load(fh)
            # Accept {"names": [...]} or plain list
            if isinstance(data, dict) and "names" in data:
                names = list(data.get("names") or [])
                # Accept optional aliases
                aliases = data.get("aliases") or {}
                for k in aliases.keys():
                    names.append(k)
                return cls(names)
            elif isinstance(data, list):
                return cls(data)
            else:
                return cls([])
        except Exception:
            return cls([])

    def hit(self, phrase: str) -> bool:
        return _fold(phrase) in self.names_norm


# -------------------------
# Core heuristics
# -------------------------
class NoBoundariesSegmenter:
    def __init__(self, cfg: Dict[str, Any]):
        self.cfg = self._merge_cfg(cfg)
        self.win = self.cfg["windows"]
        self.start_gate = self.cfg["start_gate"]
        self.start_exceptions = [_fold(x) for x in self.cfg.get("start_exceptions", [])]
        self.price_re = re.compile(self.cfg.get("prices", {}).get("pattern", DEFAULT_CFG["prices"]["pattern"]))
        self.numeric_date_re = re.compile(self.start_gate.get("numeric_date_pattern", DEFAULT_CFG["start_gate"]["numeric_date_pattern"]))
        self.family_tags = self.start_gate.get("family_tags", [])
        self.connectors = set(_fold(x) for x in self.start_gate.get("connectors", []))
        # Gazetteer (optional)
        gaz_path = (self.cfg.get("gazetteer") or {}).get("city_gazetteer_path")
        self.gaz = Gazetteer.from_path(gaz_path)

        # Simple feature words set for soft validation
        self.feature_words = set(
            _fold(x) for x in [
                "amueblado", "semiamueblado", "incluye", "con", "sin", "oferta", "promocion",
                "baño", "baños", "hab", "habitaciones", "rec", "dormitorios", "m2", "m²", "mts", "garaje",
                "cochera", "terraza", "jardin", "patio", "sala", "comedor",
            ]
        )

    @staticmethod
    def _merge_cfg(cfg: Dict[str, Any]) -> Dict[str, Any]:
        def deep_merge(a: Dict[str, Any], b: Dict[str, Any]) -> Dict[str, Any]:
            out = dict(a)
            for k, v in (b or {}).items():
                if isinstance(v, dict) and isinstance(out.get(k), dict):
                    out[k] = deep_merge(out[k], v)
                else:
                    out[k] = v
            return out
        return deep_merge(DEFAULT_CFG, cfg or {})

    # ---------- basic predicates ----------
    def _is_header(self, line: str) -> bool:
        return line.lstrip().startswith("#")

    def _has_price(self, s: str) -> bool:
        return bool(self.price_re.search(s))

    def _currency_first(self, line: str) -> bool:
        return bool(re.match(r"^\s*(?:US\$|\$|Lps\.?|L\.)\s*\d", line))

    def _number_area_first(self, line: str) -> bool:
        return bool(re.match(r"^\s*\d+(?:[.,]\d+)?\s*(?:m2|m²|mts?2?|vr2|vrs(?:²)?|vr²)\b", _fold(line)))

    def _feature_first(self, line: str) -> bool:
        head = _fold(line).split(" ", 1)[0]
        return head in self.feature_words or head in self.start_exceptions

    def _numeric_date_start(self, line: str) -> bool:
        return bool(self.numeric_date_re.match(line))

    def _family_tag_start(self, line: str) -> bool:
        # True if starts with allowed family tag + plausible name tokens nearby
        head = line.lstrip()
        for tag in self.family_tags:
            if head.startswith(tag):
                # Soft validate: look at next few tokens
                tail = head[len(tag):].strip()
                tokens = re.split(r"[\s,;:()\-]+", tail)[: self.start_gate.get("family_name_max_tokens", 7)]
                score = 0.0
                for t in tokens:
                    if not t:
                        continue
                    tf = _fold(t)
                    if tf in self.connectors:
                        continue
                    if self.gaz.hit(tf):
                        score += 1.0
                        break
                    # Title-ish or roman/numeric/qualifier
                    if re.match(r"^[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+$", t) or re.match(r"^(i{1,3}|iv|v|vi|vii|viii|ix|x|\d{1,2})$", tf):
                        score += 1.0
                        break
                    if tf in self.feature_words:
                        score -= 1.0
                return score >= 1.0
        return False

    def _plain_title_start(self, line: str) -> bool:
        # TitleCase burst at head (forgiving)
        hw = line[: self.win["head_window_chars"]]
        tokens = re.split(r"[\s,;:()\-]+", hw)
        count = 0
        for t in tokens:
            if not t:
                continue
            tf = _fold(t)
            if tf in self.connectors:
                continue
            # stop when we hit price marker or feature word early
            if tf in self.feature_words or self.price_re.match(t):
                break
            if re.match(r"^[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+$", t) or self.gaz.hit(tf):
                count += 1
                if count >= 2:
                    return True
            else:
                # Non-title token breaks the burst early
                break
        return False

    def _looks_like_start(self, line: str) -> bool:
        # Hard header
        if self._is_header(line):
            return True
        # start exceptions (glue)
        f = _fold(line)
        head_token = f.split(" ", 1)[0] if f else ""
        if head_token in self.start_exceptions:
            return False
        if self.start_gate.get("block_price_first") and self._currency_first(line):
            return False
        if self.start_gate.get("block_area_number_first") and self._number_area_first(line):
            return False
        if self.start_gate.get("block_feature_words_first") and self._feature_first(line):
            return False
        # positive starts
        if self.start_gate.get("allow_numeric_date_neighborhoods") and self._numeric_date_start(line):
            return True
        if self._family_tag_start(line):
            return True
        if self._plain_title_start(line):
            return True
        # fallback: price very early with short left context
        if self.price_re.search(line[: self.win["price_lookahead_chars"]]):
            left = line[: self.win["head_window_chars"]]
            # any capitalized token on the left window
            if re.search(r"\b[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+\b", left):
                return True
        return False

    # -------------------------
    # Main segmenter
    # -------------------------
    def segment(self, raw_lines: Iterable[str]) -> Tuple[List[str], Dict[str, Any]]:
        records: List[str] = []
        modified_records: List[Dict[str, Any]] = []
        modified_line_numbers: set[int] = set()

        current_buf: List[str] = []
        current_src_lines: List[int] = []
        current_has_price = False

        def flush(force: bool = False):
            nonlocal current_buf, current_src_lines, current_has_price
            if not current_buf:
                return
            text = " ".join(l.strip() for l in current_buf)
            is_header = self._is_header(current_buf[0])
            if is_header:
                out = current_buf[0] if self.cfg["headers"].get("preserve_whitespace", True) else _collapse_ws(current_buf[0])
                records.append(out)
                modified_records.append({
                    "record_index": len(records) - 1,
                    "type": "header",
                    "source_line_numbers": current_src_lines[:1],
                    "before_lines": current_buf[:1],
                    "after": out,
                    "change": "header_verbatim",
                })
                # do not mark headers as modified lines
            else:
                if not current_has_price and not force:
                    # drop conservative buffers without price
                    current_buf = []
                    current_src_lines = []
                    current_has_price = False
                    return
                out = _collapse_ws(text)
                records.append(out)
                change = "glued_lines" if len(current_src_lines) > 1 else "whitespace_collapsed_only"
                modified_records.append({
                    "record_index": len(records) - 1,
                    "type": "listing",
                    "source_line_numbers": current_src_lines[:],
                    "before_lines": current_buf[:],
                    "after": out,
                    "change": change,
                })
                for n in current_src_lines:
                    modified_line_numbers.add(n)
            # reset
            current_buf = []
            current_src_lines = []
            current_has_price = False

        # iterate
        for idx, raw in enumerate(raw_lines):
            line = raw.rstrip("\r\n")
            if not line.strip():
                continue

            if self._is_header(line):
                # header is a hard boundary
                flush(force=False)
                current_buf = [line]
                current_src_lines = [idx]
                current_has_price = False
                flush(force=True)
                continue

            # decide if this line begins a new record
            is_new_start = self._looks_like_start(line)
            if is_new_start:
                # if there was an open listing
                if current_buf and not self._is_header(current_buf[0]):
                    # flush only if it already had a price; else drop
                    flush(force=False)
                # start new buffer
                current_buf = [line]
                current_src_lines = [idx]
                current_has_price = self._has_price(line)
                continue

            # not a new start: glue
            if current_buf:
                current_buf.append(line)
                current_src_lines.append(idx)
                if not current_has_price and self._has_price(line):
                    current_has_price = True
                # If we exceed lookahead chars a lot without price, keep buffering; conservative
            else:
                # No open buffer; start a soft buffer only if we see price very early (fallback)
                if self._has_price(line) and re.search(r"\b[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+\b", line[: self.win["head_window_chars"]]):
                    current_buf = [line]
                    current_src_lines = [idx]
                    current_has_price = True
                else:
                    # orphan line; ignore
                    continue

        # end
        flush(force=False)

        # sanity
        any_newlines = any(("\n" in r or "\r" in r) for r in records)
        meta = {
            "modified": {
                "line_numbers": sorted(modified_line_numbers),
                "records": modified_records,
            },
            "counts": {
                "records": len(records),
                "headers": sum(1 for r in records if r.lstrip().startswith("#")),
                "listings": sum(1 for r in records if not r.lstrip().startswith("#")),
            },
            "any_newlines": any_newlines,
        }
        return records, meta


# -------------------------
# Public API
# -------------------------

def segment_by_anchor(lines: Iterable[str], cfg: Dict[str, Any] | None = None) -> Tuple[List[str], Dict[str, Any]]:
    seg = NoBoundariesSegmenter(cfg or {})
    return seg.segment(lines)


def write_pre_file(records: List[str], agency: str, original_filename: str, cfg: Dict[str, Any] | None = None) -> str:
    cfg = NoBoundariesSegmenter._merge_cfg(cfg or {})
    outdir = cfg["output"].get("target_dir") or f"output/{agency}/pre"
    Path(outdir).mkdir(parents=True, exist_ok=True)
    outname = cfg["output"].get("file_name_format", "pre_<originalfilename>.txt").replace("<originalfilename>", Path(original_filename).name)
    outpath = str(Path(outdir) / outname)
    with open(outpath, "w", encoding="utf-8") as fh:
        fh.write("\n".join(records))
    return outpath


# -------------------------
# Minimal CLI (optional)
# -------------------------
if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description="Segment historic classifieds without explicit listing delimiters.")
    ap.add_argument("--infile", required=True)
    ap.add_argument("--agency", required=True)
    ap.add_argument("--config", required=False)
    ap.add_argument("--outfile", required=False, help="Override output file name (defaults to pre_<original>.txt)")
    args = ap.parse_args()

    cfg = dict(DEFAULT_CFG)
    if args.config and os.path.exists(args.config):
        with open(args.config, "r", encoding="utf-8") as fh:
            cfg = NoBoundariesSegmenter._merge_cfg(json.load(fh))

    with open(args.infile, "r", encoding="utf-8") as fh:
        raw_lines = fh.readlines()

    records, meta = segment_by_anchor(raw_lines, cfg)

    original_filename = Path(args.infile).name
    if args.outfile:
        cfg = NoBoundariesSegmenter._merge_cfg(cfg)
        cfg["output"]["file_name_format"] = args.outfile

    wrote = write_pre_file(records, args.agency, original_filename, cfg)

    print(f"records={meta['counts']['records']} headers={meta['counts']['headers']} listings={meta['counts']['listings']} any_newlines={meta['any_newlines']}")
    print(f"wrote {wrote}")
