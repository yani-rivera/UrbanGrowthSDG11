#!/usr/bin/env python3
r"""
Agency Config Comparator
------------------------

Purpose
    - Read every agency's JSON config file from a folder
    - Flatten nested objects/arrays using dot + [index] notation
    - Build a single comparison table with one row per agency and one column per parameter
    - **Filter to specific parameters** via `--include`, `--exclude`, or a `--keys` YAML/CSV file (with aliases, transforms, and required flags)
    - Export:
        1) configs_wide.csv  (full matrix)
        2) configs_wide.xlsx (Excel with handy filters)
        3) differences.csv   (only keys whose values differ across agencies)
        4) data_dictionary.csv (per key type summary + null/missing stats)
        5) configs_selected.csv / .xlsx (only requested parameters if filters are used)

Usage
    # simplest
    python compare_agency_configs.py --input ./configs --out ./out

    # include / exclude keys by regex (Python regex on flattened keys)
    python compare_agency_configs.py --input ./configs --out ./out \
        --include "^api\\.|^auth\\.|timeout$" --exclude "secret|token|password"

    # use a keys file that defines exact keys, aliases, required flags, and transforms
    python compare_agency_configs.py --input ./configs --out ./out \
        --keys ./keys.yaml

Notes
    - Filename (without extension) becomes the agency name.
    - Non-primitive values are JSON-serialized so you can still compare.
    - Missing keys are left as empty cells (NaN in CSV/Excel).
"""

from __future__ import annotations
import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Tuple, Optional
import pandas as pd
import csv
try:
    import yaml  # optional, only if you pass --keys .yaml
except Exception:
    yaml = None

# ----------------------------
# Flatten helpers
# ----------------------------

def _is_primitive(x: Any) -> bool:
    return isinstance(x, (str, int, float, bool)) or x is None


def flatten(obj: Any, parent_key: str = "") -> Dict[str, Any]:
    """Flatten dict/list into a single level dict using dot + [idx] paths.
    Examples:
        {"a": {"b": 1}, "c": [10, 20]} -> {"a.b": 1, "c[0]": 10, "c[1]": 20}
    """
    items: Dict[str, Any] = {}

    if isinstance(obj, dict):
        for k, v in obj.items():
            k_str = str(k)
            new_key = f"{parent_key}.{k_str}" if parent_key else k_str
            for sub_k, sub_v in flatten(v, new_key).items():
                items[sub_k] = sub_v
    elif isinstance(obj, list):
        for idx, v in enumerate(obj):
            new_key = f"{parent_key}[{idx}]" if parent_key else f"[{idx}]"
            for sub_k, sub_v in flatten(v, new_key).items():
                items[sub_k] = sub_v
    else:
        # Convert non-primitive leaves to deterministic JSON strings
        if not _is_primitive(obj):
            try:
                obj = json.dumps(obj, sort_keys=True)
            except Exception:
                obj = str(obj)
        items[parent_key] = obj

    return items


# ----------------------------
# Stats & reporting
# ----------------------------

def friendly_type(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, int):
        return "int"
    if isinstance(value, float):
        return "float"
    if isinstance(value, str):
        # try detect json-looking strings
        v = value.strip()
        if (v.startswith("{") and v.endswith("}")) or (v.startswith("[") and v.endswith("]")):
            return "json-string"
        return "string"
    return type(value).__name__


def summarize_types(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for col in df.columns:
        series = df[col]
        non_null = series.dropna()
        types = sorted({friendly_type(v) for v in non_null})
        rows.append({
            "key": col,
            "types": ", ".join(types) if types else "(all missing)",
            "non_null": int(non_null.shape[0]),
            "missing": int(series.isna().sum()),
            "unique_values": int(non_null.nunique(dropna=True)),
        })
    return pd.DataFrame(rows).sort_values(["missing", "key"]).reset_index(drop=True)


def find_differences(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for col in df.columns:
        series = df[col]
        non_null = series.dropna()
        uniq = non_null.unique()
        if len(uniq) <= 1:
            continue  # no differences
        # Build up to 8 sample values for readability
        sample_values = list(pd.Series(uniq).astype(str).head(8))
        rows.append({
            "key": col,
            "agencies_with_value": int(non_null.shape[0]),
            "missing": int(series.isna().sum()),
            "unique_count": int(len(uniq)),
            "sample_values": " | ".join(sample_values),
        })
    return pd.DataFrame(rows).sort_values(["unique_count", "key"], ascending=[False, True]).reset_index(drop=True)


# ----------------------------
# IO
# ----------------------------

def read_json_file(path: Path) -> Any:
    text = path.read_text(encoding="utf-8")
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse JSON: {path} — {e}") from e


def collect_configs(input_dir: Path, glob: str) -> List[Tuple[str, Dict[str, Any]]]:
    files = sorted(input_dir.rglob(glob))
    if not files:
        raise SystemExit(f"No files matched {glob!r} under {input_dir}")

    rows: List[Tuple[str, Dict[str, Any]]] = []
    for fp in files:
        agency = fp.stem  # filename without extension
        data = read_json_file(fp)
        flat = flatten(data)
        rows.append((agency, flat))
    return rows


def build_dataframe(rows: List[Tuple[str, Dict[str, Any]]]) -> pd.DataFrame:
    # Create a DataFrame where index = agency, columns = union of all keys
    records = []
    index = []
    for agency, flat in rows:
        records.append(flat)
        index.append(agency)
    df = pd.DataFrame.from_records(records, index=index)
    df.index.name = "agency"
    # Ensure stable column order (alphabetical)
    df = df.reindex(sorted(df.columns), axis=1)
    return df


def export_outputs(df: pd.DataFrame, out_dir: Path, selected: Optional[pd.DataFrame] = None) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)

    # 1) Wide CSV
    df.to_csv(out_dir / "configs_wide.csv")

    # 2) Excel (single sheet + filters)
    with pd.ExcelWriter(out_dir / "configs_wide.xlsx", engine="xlsxwriter") as xw:
        df.to_excel(xw, sheet_name="configs_wide")
        ws = xw.sheets["configs_wide"]
        ws.freeze_panes(1, 1)
        last_row, last_col = df.shape
        ws.autofilter(0, 0, last_row, last_col)
        ws.set_column(0, 0, 28)
        ws.set_column(1, last_col, 36)

    # 3) Differences (full)
    diff = find_differences(df)
    diff.to_csv(out_dir / "differences.csv", index=False)

    # 4) Data dictionary (full)
    dd = summarize_types(df)
    dd.to_csv(out_dir / "data_dictionary.csv", index=False)

    # 5) Selected (if provided)
    if selected is not None:
        selected.to_csv(out_dir / "configs_selected.csv")
        with pd.ExcelWriter(out_dir / "configs_selected.xlsx", engine="xlsxwriter") as xw:
            selected.to_excel(xw, sheet_name="configs_selected")
            ws = xw.sheets["configs_selected"]
            ws.freeze_panes(1, 1)
            last_row, last_col = selected.shape
            ws.autofilter(0, 0, last_row, last_col)
            ws.set_column(0, 0, 28)
            ws.set_column(1, last_col, 40)


# ----------------------------
# CLI
# ----------------------------

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Compare agency JSON config files and produce a column-wise diff table.")
    p.add_argument("--input", required=True, type=Path, help="Folder containing agency config files")
    p.add_argument("--out", required=True, type=Path, help="Output folder for CSV/Excel reports")
    p.add_argument("--glob", default="*.json", help="File pattern to match within --input (default: *.json)")
    # selection controls
    p.add_argument("--include", default=None, help="Regex to include keys (applied to flattened keys)")
    p.add_argument("--exclude", default=None, help="Regex to exclude keys (applied after include)")
    p.add_argument("--keys", type=Path, default=None, help="YAML or CSV listing keys to extract; supports alias, transform, and required flag")
    p.add_argument("--fail_on_missing", action="store_true", help="Exit with non-zero if any requested *required* key is missing for any agency")
    p.add_argument("--debug_join", action="store_true", help="Print which indexed columns are joined for each 'join' transform")
    return p.parse_args()


def load_keys_file(path: Path) -> List[Dict[str, Any]]:
    """Return a list of mappings: {key, alias?, transform?, required?}
    YAML example:
      - key: api.baseUrl
        alias: API Base
        transform: lower
        required: true
    CSV example (headers: key,alias,transform,required)
    """
    rows: List[Dict[str, Any]] = []
    if path.suffix.lower() in {".yml", ".yaml"}:
        if yaml is None:
            raise SystemExit("PyYAML is required for YAML keys file. pip install pyyaml")
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or []
        if not isinstance(data, list):
            raise SystemExit("YAML keys file must be a list of mappings")
        for item in data:
            if not isinstance(item, dict) or "key" not in item:
                raise SystemExit("Each YAML item must be a mapping with 'key'")
            norm: Dict[str, Any] = {k: (str(v) if k != "required" else bool(v)) for k, v in item.items()}
            if "required" not in norm:
                norm["required"] = True
            rows.append(norm)
    else:
        with path.open(newline='', encoding="utf-8") as f:
            for r in csv.DictReader(f):
                if not r.get("key"):
                    continue
                norm: Dict[str, Any] = {k: v for k, v in r.items() if v is not None}
                norm["required"] = str(norm.get("required", "true")).strip().lower() in {"1","true","yes","y"}
                rows.append(norm)
    return rows


def apply_transform(val: Any, name: Optional[str]) -> Any:
    if val is None or pd.isna(val):
        return val
    if not name:
        return val
    name = name.strip().lower()
    if name == "lower":
        return str(val).lower()
    if name == "upper":
        return str(val).upper()
    if name == "strip":
        return str(val).strip()
    if name == "boolify":
        v = str(val).strip().lower()
        return v in {"1", "true", "yes", "y", "on"}
    if name == "int":
        try:
            return int(val)
        except Exception:
            return val
    if name == "float":
        try:
            return float(val)
        except Exception:
            return val
    if name == "json":
        try:
            return json.loads(val) if isinstance(val, str) else val
        except Exception:
            return val
    return val


def select_columns(df: pd.DataFrame, include: Optional[str], exclude: Optional[str], keys_file: Optional[Path], fail_on_missing: bool) -> pd.DataFrame:
    import re
    cols = list(df.columns)

    def build_join_series(base_key: str, sep: str = ",") -> pd.Series:
        pattern = re.compile(rf"^{re.escape(base_key)}\[(\d+)\]$")
        # find all matching index columns
        matches = [(int(m.group(1)), c) for c in cols for m in [pattern.match(c)] if m]
        if not matches:
            return pd.Series([pd.NA]*len(df), index=df.index)
        # order by index and join non-null values
        ordered_cols = [c for _, c in sorted(matches, key=lambda x: x[0])]
        def join_row(row):
            vals = [row[c] for c in ordered_cols if pd.notna(row[c])]
            if not vals:
                return pd.NA
            return sep.join(str(v) for v in vals)
        return df.apply(join_row, axis=1)

    def parse_join_sep(transform: Optional[str]) -> Optional[str]:
        if not transform:
            return None
        t = transform.strip().lower()
        if t == "join":
            return ","
        if t.startswith("join:"):
            return t.split(":", 1)[1] or ","
        return None

    # keys file overrides regexes if provided
    if keys_file:
        spec = load_keys_file(keys_file)
        # fail only on required keys that are missing entirely (no indices present either)
        missing_required = []
        for it in spec:
            k = it["key"]
            if it.get("required", False):
                if k not in cols:
                    # treat presence of any k[0] style as satisfying existence
                    has_indexed = any(re.match(rf"^{re.escape(k)}\[\d+\]$", c) for c in cols)
                    if not has_indexed:
                        missing_required.append(it)
        if missing_required and fail_on_missing:
            raise SystemExit(f"Missing requested required keys: {[m['key'] for m in missing_required]}")

        sel = pd.DataFrame(index=df.index)
        for item in spec:
            k = item["key"]
            alias = item.get("alias") or k
            transform = item.get("transform")
            join_sep = parse_join_sep(transform)

            if k in df.columns:
                s = df[k]
                # normal per-cell transform
                if join_sep is not None and s.apply(lambda v: isinstance(v, list)).any():
                    # if somehow a list survived flattening, join it
                    s = s.apply(lambda v: (join_sep.join(str(x) for x in v) if isinstance(v, list) else v))
            else:
                # if not found, try to compose from indexed cols when transform asks to join
                if join_sep is not None:
                    s = build_join_series(k, join_sep)
                else:
                    # fall back to NA series
                    s = pd.Series([pd.NA]*len(df), index=df.index)

            sel[alias] = s.apply(lambda v: apply_transform(v, None if join_sep is not None else transform))
        return sel

    # regex path
    selected = cols
    if include:
        inc = re.compile(include)
        selected = [c for c in selected if inc.search(c)]
    if exclude:
        exc = re.compile(exclude)
        selected = [c for c in selected if not exc.search(c)]
    return df.reindex(columns=selected)


def main() -> None:
    args = parse_args()
    rows = collect_configs(args.input, args.glob)
    df = build_dataframe(rows)

    # Optional selection layer
    selected_df = select_columns(df, args.include, args.exclude, args.keys, args.fail_on_missing) if (args.include or args.exclude or args.keys) else None

    export_outputs(df, args.out, selected_df)
    print(f"\nDone. Generated files in: {args.out.resolve()}")
    print(" - configs_wide.csv")
    print(" - configs_wide.xlsx")
    print(" - differences.csv")
    print(" - data_dictionary.csv")
    if selected_df is not None:
        print(" - configs_selected.csv")
        print(" - configs_selected.xlsx")


if __name__ == "__main__":
    main()
