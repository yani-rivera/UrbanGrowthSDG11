
#!/usr/bin/env python3
import json
import argparse
from pathlib import Path
from collections import Counter
from copy import deepcopy

SENTINEL_VARIES = "__VARIES__"

def load_json(p: Path):
    with p.open("r", encoding="utf-8") as f:
        return json.load(f)

def typeof(x):
    if x is None: return "null"
    if isinstance(x, bool): return "boolean"
    if isinstance(x, int) or isinstance(x, float): return "number"
    if isinstance(x, str): return "string"
    if isinstance(x, list): return "array"
    if isinstance(x, dict): return "object"
    return "unknown"

def mode_or_varies(values):
    # Choose most common scalar/list/dict *stringified* value; if tie or too diverse, return SENTINEL_VARIES
    ser = [json.dumps(v, sort_keys=True, ensure_ascii=False) for v in values]
    c = Counter(ser)
    [(best, nbest)] = c.most_common(1)
    # If more than one unique and the top is weak (< 50%), mark as varies
    if len(c) > 1 and nbest < (len(values) / 2):
        return SENTINEL_VARIES
    return json.loads(best)

def merge_union(keys_values):
    """
    keys_values: list of values of the same key from different files (may be missing; pass None for missing)
    Produces a representative value for base_all_params.json while ensuring every nested key appears at least once.
    """
    present = [v for v in keys_values if v is not None]
    if not present:
        return None

    types = {typeof(v) for v in present}
    if len(types) > 1:
        # Mixed types across agencies → pick nothing concrete
        return SENTINEL_VARIES

    t = types.pop()
    if t in {"null", "boolean", "number", "string"}:
        return mode_or_varies(present)

    if t == "array":
        # For arrays, prefer the most common full array if small; otherwise, aggregate a sample of elements.
        # If arrays contain objects and share a natural key ("pattern"), union by that key.
        # Otherwise keep the mode or mark as varies.
        # Heuristic: if elements look like dicts with "pattern" → keyed union
        arrs = [a for a in present if isinstance(a, list)]
        # detect dict-of-pattern style
        dict_elem = any(isinstance(e, dict) for a in arrs for e in a[:3])
        pattern_style = dict_elem and all(
            all((not isinstance(e, dict)) or ("pattern" in e) for e in a) for a in arrs
        )
        if pattern_style:
            # Union by "pattern"
            by_pattern = {}
            for a in arrs:
                for e in a:
                    if not isinstance(e, dict) or "pattern" not in e:
                        continue
                    k = e["pattern"]
                    if k not in by_pattern:
                        by_pattern[k] = []
                    by_pattern[k].append(e)
            # For each pattern, merge fields with mode
            out = []
            for k, variants in by_pattern.items():
                # collect all keys
                all_keys = set().union(*(v.keys() for v in variants))
                merged = {}
                for field in all_keys:
                    vals = [v.get(field) for v in variants]
                    merged[field] = mode_or_varies([vv for vv in vals if vv is not None])
                out.append(merged)
            return out
        else:
            # If arrays differ a lot, keep the mode array; else mark varies
            candidate = mode_or_varies(arrs)
            return candidate

    if t == "object":
        # Union all keys seen across all objects
        all_keys = set().union(*(o.keys() for o in present))
        out = {}
        for k in sorted(all_keys):
            vals = [o.get(k) if isinstance(o, dict) else None for o in present]
            out[k] = merge_union(vals)
        return out

    return SENTINEL_VARIES

def union_all(files):
    data = [(p.name, load_json(p)) for p in files]
    # gather all top-level keys
    all_keys = set().union(*(d.keys() for _, d in data))
    base = {}
    for k in sorted(all_keys):
        vals = [d.get(k) for _, d in data]
        base[k] = merge_union(vals)
    return base, dict(data)

def compute_overrides(base, agency_cfg):
    """Return only the fields where agency_cfg differs from base."""
    def diff(a, b):
        if typeof(a) != typeof(b):
            return deepcopy(b)
        t = typeof(b)
        if t in {"null", "boolean", "number", "string"}:
            return None if a == b else deepcopy(b)
        if t == "array":
            return None if json.dumps(a, sort_keys=True, ensure_ascii=False) == json.dumps(b, sort_keys=True, ensure_ascii=False) else deepcopy(b)
        if t == "object":
            out = {}
            keys = set().union((a or {}).keys(), (b or {}).keys())
            for k in keys:
                da = None if a is None else a.get(k)
                db = None if b is None else b.get(k)
                d = diff(da, db)
                if d is not None:
                    out[k] = d
            return out or None
        return None if a == b else deepcopy(b)
    return diff(base, agency_cfg) or {}

def infer_schema_from_examples(examples):
    """
    Very light JSON Schema based on observed types.
    """
    def merge_types(ts):
        return sorted(list(ts))

    def walk(values):
        present = [v for v in values if v is not None]
        if not present:
            return {"type": ["null"]}
        types = {typeof(v) for v in present}
        if types == {"object"}:
            props = {}
            required = set()
            all_keys = set().union(*(v.keys() for v in present))
            for k in sorted(all_keys):
                subvals = [v.get(k) for v in present]
                props[k] = walk(subvals)
                # required if key appears in all
                if all(k in v for v in present):
                    required.add(k)
            schema = {"type": "object", "properties": props}
            if required:
                schema["required"] = sorted(list(required))
            return schema
        if types == {"array"}:
            # sample first elements to infer item type
            items_vals = []
            for a in present:
                if isinstance(a, list) and a:
                    items_vals.append(a[0])
            items_schema = walk(items_vals) if items_vals else {}
            return {"type": "array", "items": items_schema}
        # scalars or mixed — allow any of observed
        return {"type": merge_types(types)}

    return walk(examples)

def main():
    ap = argparse.ArgumentParser(description="Build a full-parameter base and per-agency diffs.")
    ap.add_argument("--agencies-dir", default="config/agencies", help="Directory with per-agency JSON configs")
    ap.add_argument("--out-base", default="config/base_all_params.json")
    ap.add_argument("--out-diffs", default="config/_diffs_by_agency.json")
    ap.add_argument("--out-schema", default="config/_schema.json")
    args = ap.parse_args()

    agencies_dir = Path(args.agencies_dir)
    files = sorted(agencies_dir.glob("*.json"))
    if not files:
        raise SystemExit(f"No JSON files found in {agencies_dir}")

    base, data_by_file = union_all(files)

    # Clean up SENTINEL_VARIES in base: prefer None for ambiguous scalars,
    # and keep arrays/objects as produced.
    def scrub(v):
        if v == SENTINEL_VARIES:
            return None
        if isinstance(v, dict):
            return {k: scrub(x) for k, x in v.items()}
        if isinstance(v, list):
            return [scrub(x) for x in v]
        return v
    base = scrub(base)

    # Write base
    Path(args.out_base).parent.mkdir(parents=True, exist_ok=True)
    with open(args.out_base, "w", encoding="utf-8") as f:
        json.dump(base, f, ensure_ascii=False, indent=2)

    # Compute diffs
    diffs = {}
    for fname, cfg in data_by_file.items():
        diffs[fname] = compute_overrides(base, cfg)
    with open(args.out_diffs, "w", encoding="utf-8") as f:
        json.dump(diffs, f, ensure_ascii=False, indent=2)

    # Schema
    examples = list(data_by_file.values())
    schema = infer_schema_from_examples(examples)
    with open(args.out_schema, "w", encoding="utf-8") as f:
        json.dump(schema, f, ensure_ascii=False, indent=2)

    print(f"Wrote:\n  {args.out_base}\n  {args.out_diffs}\n  {args.out_schema}")

if __name__ == "__main__":
    main()
