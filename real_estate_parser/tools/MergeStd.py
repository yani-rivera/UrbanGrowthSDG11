
#!/usr/bin/env python3
import os
import sys
import json
import argparse
from typing import List, Optional
import pandas as pd

# -------------------------------------------------------------------
# Option A: list inside this script (fill this if you prefer hardcode)
HARD_CODED_COLUMNS: List[str] = [
    # Example:
    # "listing_id", "agency_code", "agency_name", "source_url",
    # ...
]
# -------------------------------------------------------------------

def _load_columns_from_txt(path: str) -> List[str]:
    try:
        with open(path, "r", encoding="utf-8-sig") as f:
            cols = [line.strip() for line in f if line.strip() and not line.lstrip().startswith(("#","//"))]
        return cols
    except Exception as e:
        sys.exit(f"Error reading columns file '{path}': {e}")

def _json_get_by_keypath(obj, keypath: Optional[str]):
    """keypath like 'csv_header_order' or 'schema.fields' (dot-separated)."""
    if not keypath:
        return obj
    cur = obj
    for part in keypath.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            sys.exit(f"Key path '{keypath}' not found in JSON config.")
    return cur

def _load_columns_from_json(spec: str) -> List[str]:
    """
    spec format: <path_to_json>[:keypath]
    - If keypath is omitted, whole JSON must be a list of column names.
    - If provided, it should resolve to a list (e.g., output.json:csv_header_order)
    """
    if ":" in spec:
        path, keypath = spec.split(":", 1)
    else:
        path, keypath = spec, None
    if not os.path.exists(path):
        sys.exit(f"Columns config not found: {path}")
    try:
        with open(path, "r", encoding="utf-8-sig") as f:
            data = json.load(f)
    except Exception as e:
        sys.exit(f"Error reading JSON config '{path}': {e}")
    node = _json_get_by_keypath(data, keypath)
    if not isinstance(node, list) or not all(isinstance(x, str) for x in node):
        sys.exit(f"JSON keypath must resolve to a list[str]. Got: {type(node)} at '{spec}'")
    return node

def _resolve_columns(
    inline_cols: Optional[List[str]],
    cols_file: Optional[str],
    json_spec: Optional[str],
) -> Optional[List[str]]:
    """
    Priority:
        1) inline --columns
        2) --columns-file (txt, one per line)
        3) --columns-config (json[:keypath])
        4) HARD_CODED_COLUMNS (if not empty)
        5) None (no selection; keep all columns from concat)
    """
    if inline_cols:
        return inline_cols
    if cols_file:
        return _load_columns_from_txt(cols_file)
    if json_spec:
        return _load_columns_from_json(json_spec)
    if HARD_CODED_COLUMNS:
        return HARD_CODED_COLUMNS
    return None

def concat_csv_in_directory(
    input_dir: str,
    output_file: str,
    inline_cols: Optional[List[str]],
    cols_file: Optional[str],
    cols_json: Optional[str],
):
    if not os.path.isdir(input_dir):
        sys.exit(f"Error: Directory not found: {input_dir}")

    csv_files = sorted(
        os.path.join(input_dir, f)
        for f in os.listdir(input_dir)
        if f.lower().endswith(".csv")
    )
    if not csv_files:
        sys.exit(f"No CSV files found in directory: {input_dir}")

    frames = []
    for path in csv_files:
        try:
            df = pd.read_csv(path, encoding="utf-8-sig")
            frames.append(df)
            print(f"Loaded {path} ({len(df)} rows)")
        except Exception as e:
            print(f"Warning: Failed to read {path}: {e}")

    if not frames:
        sys.exit("No CSV files could be read successfully.")

    merged = pd.concat(frames, ignore_index=True)

    # Resolve column selection
    selected_cols = _resolve_columns(inline_cols, cols_file, cols_json)

    if selected_cols:
        # Ensure all requested columns exist; create missing as blank (empty string)
        for c in selected_cols:
            if c not in merged.columns:
                merged[c] = ""
        # Reorder to selected, keep only those columns
        merged = merged.reindex(columns=selected_cols)

    try:
        merged.to_csv(output_file, index=False, encoding="utf-8-sig")
        print(f"\n✅ Combined {len(csv_files)} files -> {output_file}")
        print(f"Total rows: {len(merged)}")
        if selected_cols:
            print(f"Columns ({len(selected_cols)}): {selected_cols}")
        else:
            print(f"Columns ({len(merged.columns)}): {list(merged.columns)}")
    except Exception as e:
        sys.exit(f"Error writing output: {e}")

def main():
    parser = argparse.ArgumentParser(description="Concatenate all CSV files in a directory into one file, with optional column selection.")
    parser.add_argument("-i", "--input-dir", required=True, help="Path to directory containing CSV files")
    parser.add_argument("-o", "--output", required=True, help="Output CSV file path")

    # Column selection sources (priority as documented above)
    parser.add_argument("-c", "--columns", nargs="+", help="Inline list of columns to include (highest priority)")
    parser.add_argument("--columns-file", help="Plain text file with one column per line")
    parser.add_argument("--columns-config", help="JSON file (optionally with :keypath). Example: output.json:csv_header_order")

    args = parser.parse_args()
    concat_csv_in_directory(args.input_dir, args.output, args.columns, args.columns_file, args.columns_config)

if __name__ == "__main__":
    main()
