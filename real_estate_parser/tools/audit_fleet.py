
# tools/audit_fleet.py
import re, json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT/"scripts"; REG = ROOT/"config"/"agencies_registry.json"

reg = json.loads(REG.read_text(encoding="utf-8")); keys = set((reg.get("agencies") or {}).keys())
problems = []
for p in SCRIPTS.glob("parse_*.py"):
    t = p.read_text(encoding="utf-8")
    uses_writer = "write_prefile(" in t
    imports_writer = ("from helpers_prefile import write_prefile" in t) or ("from helpers import write_prefile" in t)
    has_release = "build_release_row" in t
    agencies = re.findall(r'agency\s*=\s*[\'"]([^\'"]+)[\'"]', t)
    bad_agencies = [a for a in agencies if a not in keys]
    if not uses_writer: problems.append((p.name, "no_write_prefile_call"))
    if uses_writer and not imports_writer: problems.append((p.name, "missing_write_prefile_import"))
    if not has_release: problems.append((p.name, "no_release_row"))
    for a in bad_agencies: problems.append((p.name, f"agency_literal_not_in_registry:{a}"))
for name, issue in problems:
    print(f"[{issue}] {name}")
if not problems: print("[ok] fleet looks good ✅")
