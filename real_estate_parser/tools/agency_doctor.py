#!/usr/bin/env python3
from __future__ import annotations
import re, json, argparse, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
REGISTRY = ROOT / "config" / "agencies_registry.json"

IMP_LINE = "from helpers import write_prefile\n"
DATE_NORMALIZER = """
def _norm_date_str(x):
    from datetime import date, datetime
    s = x.strftime("%Y%m%d") if isinstance(x, (date, datetime)) else str(x)
    return s.replace("-", "") if "-" in s else s
""".lstrip()

CALL_FIX_RE = re.compile(
    r"write_prefile\(\s*registry_path\s*=\s*([\"']?config/agencies_registry\.json[\"']?)\s*,\s*agency\s*=\s*([\"'][^\"']+[\"'])\s*,\s*date_str\s*=\s*([^)]+?)\s*,\s*rows\s*=\s*([^)]+?)\s*\)",
    re.DOTALL
)

def load_registry():
    if not REGISTRY.exists():
        return {}
    try:
        data = json.loads(REGISTRY.read_text(encoding="utf-8"))
        keys = set(data.keys())
        if isinstance(data.get("agencies"), dict):
            keys |= set(data["agencies"].keys())
        return {"_raw": data, "keys": keys}
    except Exception as e:
        return {"_error": str(e), "keys": set()}

def ensure_import(text: str) -> tuple[str, bool]:
    if "from helpers import write_prefile" in text:
        return text, False
    # insert after first block of imports
    lines = text.splitlines(keepends=True)
    i = 0
    while i < len(lines) and (lines[i].startswith(("import ", "from ")) or not lines[i].strip()):
        i += 1
    lines.insert(i, IMP_LINE)
    return "".join(lines), True

def ensure_date_normalization(text: str) -> tuple[str, bool]:
    if "_norm_date_str" in text:
        return text, False
    return text + ("\n\n" + DATE_NORMALIZER), True

def rewrite_call(text: str) -> tuple[str, bool]:
    m = CALL_FIX_RE.search(text)
    if not m:
        return text, False
    reg, agency, date_expr, rows_expr = m.groups()
    new = f"""write_prefile(
    registry_path="config/agencies_registry.json",
    agency={agency},
    date_str=_norm_date_str({date_expr.strip()}),
    rows={rows_expr.strip()}
)"""
    return CALL_FIX_RE.sub(new, text, count=1), True

def main(apply: bool):
    reg = load_registry()
    problems = []
    for py in SCRIPTS.glob("parse_*.py"):
        txt = py.read_text(encoding="utf-8")
        calls = "write_prefile(" in txt
        has_import = "from helpers import write_prefile" in txt
        # find agency literals used in call sites
        agencies = re.findall(r'agency\s*=\s*["\']([^"\']+)["\']', txt)
        missing = [a for a in agencies if a not in reg.get("keys", set())]
        issues = []
        if not calls:
            issues.append("no_write_prefile_call")
        if calls and not has_import:
            issues.append("missing_helpers_import")
        if missing:
            issues.append(f"agency_not_in_registry:{missing}")
        if issues:
            problems.append((py, issues))

        if apply and calls:
            new_txt, changed = txt, False
            new_txt, c1 = ensure_import(new_txt); changed |= c1
            new_txt, c2 = ensure_date_normalization(new_txt); changed |= c2
            new_txt, c3 = rewrite_call(new_txt); changed |= c3
            if changed:
                py.write_text(new_txt, encoding="utf-8")

    # report
    if reg.get("_error"):
        print(f"[registry] ERROR reading: {reg['_error']}")
    else:
        print(f"[registry] loaded with {len(reg.get('keys', []))} keys")

    if not problems:
        print("[doctor] No issues found 🎉")
        return

    print("[doctor] Issues:")
    for p, iss in problems:
        print(f" - {p.relative_to(ROOT)} :: {', '.join(iss)}")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="apply safe fixes (imports, date normalization, call rewrite)")
    ap.add_argument("--report", action="store_true", help="only report issues (default)")
    args = ap.parse_args()
    if not (args.apply or args.report):
        args.report = True
    main(apply=args.apply)
