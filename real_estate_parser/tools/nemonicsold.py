#!/usr/bin/env python3
"""
Build agency_mnemonics.json by scanning per-agency config files.

- Scans a directory for JSON (and optionally YAML if PyYAML present) config files.
- Extracts the agency name and nemonic (configurable key names).
- Produces a single JSON mapping with lowercase agency keys for case-insensitive lookups:

  {
    "nemonics": {
      "vinsa": "VINSA",
      "inverprop": "INVP"
    }
  }

Default heuristics:
- Agency key candidates:    ["agency", "name"]
- Nemonic key candidates:   ["nemonic", "mnemonic", "mnem", "code", "shortcode"]
- If nemonic is missing, derive from agency (first 6 alphanumerics uppercased) and warn.
- If agency is missing, try to infer from filename stem (e.g., agency_vinsa.json -> vinsa).
- Merges with an existing output file unless --overwrite is passed.

Examples:
  python build_mnemonics_from_configs.py \
    --configs-dir ./configs \
    --pattern "agency_*.json" \
    --output agency_mnemonics.json

  python build_mnemonics_from_configs.py \
    --configs-dir . \
    --pattern "*.json" \
    --output agency_mnemonics.json --overwrite
"""

import argparse
import json
import os
import re
import sys
from glob import glob
from typing import Dict, Optional, Tuple

try:
    import yaml  # type: ignore
except Exception:
    yaml = None

AGENCY_KEYS_DEFAULT = ["agency", "name"]
NEMONIC_KEYS_DEFAULT = ["nemonic", "mnemonic", "mnem", "code", "shortcode"]


def load_any(path: str) -> Dict:
    _, ext = os.path.splitext(path.lower())
    with open(path, "r", encoding="utf-8") as fh:
        if ext in (".yml", ".yaml"):
            if yaml is None:
                raise RuntimeError(
                    f"PyYAML not installed; cannot read YAML file: {path}. Install pyyaml or limit to JSON.")
            data = yaml.safe_load(fh)
        else:
            data = json.load(fh)
    if not isinstance(data, dict):
        raise ValueError(f"Root of {os.path.basename(path)} must be a JSON/YAML object")
    return data


def derive_from_name(name: str, max_len: int = 6) -> str:
    base = re.sub(r"[^A-Za-z0-9]", "", name or "").upper()
    return (base[:max_len] or "AGENCY")


def pick_keys(obj: Dict, candidates) -> Optional[str]:
    for k in candidates:
        v = obj.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()
    return None


def infer_agency_from_filename(path: str) -> Optional[str]:
    stem = os.path.splitext(os.path.basename(path))[0]
    for token in re.split(r"[^A-Za-z0-9]+", stem):
        if token:
            return token
    return None


def build_map(configs_dir: str, pattern: str, agency_keys, nemonic_keys) -> Dict[str, str]:
    paths = sorted(glob(os.path.join(configs_dir, pattern)))
    if not paths:
        print(f"No files matched {os.path.join(configs_dir, pattern)}")
    result: Dict[str, str] = {}

    for p in paths:
        try:
            data = load_any(p)
        except Exception as e:
            print(f"[WARN] Skip {p}: {e}")
            continue

        agency = pick_keys(data, agency_keys)
        if not agency:
            agency = infer_agency_from_filename(p)
        if not agency:
            print(f"[WARN] {os.path.basename(p)}: no agency found; skipping")
            continue

        nemonic = pick_keys(data, nemonic_keys)
        if not nemonic:
            nemonic = derive_from_name(agency)
            print(f"[WARN] {os.path.basename(p)}: no nemonic; derived '{nemonic}' from '{agency}'")

        key = agency.strip().lower()
        val = nemonic.strip().upper()
        if key in result and result[key] != val:
            print(f"[WARN] conflict for agency '{key}': keeping '{result[key]}', ignoring '{val}' from {os.path.basename(p)}")
        else:
            result[key] = val

    return result


def merge_with_existing(out_path: str, new_map: Dict[str, str]) -> Tuple[Dict[str, str], bool]:
    if not os.path.exists(out_path):
        return new_map, True
    try:
        with open(out_path, "r", encoding="utf-8") as fh:
            existing_root = json.load(fh)
        existing = existing_root.get("nemonics", existing_root)
        if not isinstance(existing, dict):
            existing = {}
    except Exception:
        existing = {}
    merged = {**existing, **new_map}
    changed = merged != existing
    return merged, changed


def run(args: argparse.Namespace) -> None:
    new_map = build_map(args.configs_dir, args.pattern, args.agency_keys, args.nemonic_keys)

    if args.overwrite:
        payload = {"nemonics": dict(sorted(new_map.items()))}
        os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
        with open(args.output, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, ensure_ascii=False, indent=2)
        print(f"Wrote {len(new_map)} entries to {args.output} (overwrite)")
        return

    merged, changed = merge_with_existing(args.output, new_map)
    payload = {"nemonics": dict(sorted(merged.items()))}
    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)
    print(f"Wrote {len(merged)} entries to {args.output}{' (updated)' if changed else ' (no change)'}")


def build_argparser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Build agency_mnemonics.json by scanning per-agency configs")
    p.add_argument("--configs-dir", required=True, help="Directory containing per-agency config files")
    p.add_argument("--pattern", default="*.json", help="Glob for config files (default: *.json). YAML also supported if PyYAML installed.")
    p.add_argument("--output", default="agency_mnemonics.json", help="Output JSON path (default: agency_mnemonics.json)")
    p.add_argument("--overwrite", action="store_true", help="Overwrite output instead of merging with existing")
    p.add_argument("--agency-keys", nargs="*", default=AGENCY_KEYS_DEFAULT, help=f"Keys to try for agency (default: {AGENCY_KEYS_DEFAULT})")
    p.add_argument("--nemonic-keys", nargs="*", default=NEMONIC_KEYS_DEFAULT, help=f"Keys to try for nemonic (default: {NEMONIC_KEYS_DEFAULT})")
    return p


if __name__ == "__main__":
    args = build_argparser().parse_args()
    run(args)