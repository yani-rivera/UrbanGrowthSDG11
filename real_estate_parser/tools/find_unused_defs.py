# save as tools/find_unused_defs.py, run: python tools/find_unused_defs.py modules/price_extractor.py .
import sys, re, os, pathlib
target = pathlib.Path(sys.argv[1])  # modules/price_extractor.py
root   = pathlib.Path(sys.argv[2])  # repo root (.)
defs = []
for i, line in enumerate(target.read_text(encoding="utf-8", errors="ignore").splitlines(), 1):
    m = re.match(r'\s*def\s+([_A-Za-z]\w*)\s*\(', line)
    if m: defs.append((m.group(1), i))
refs = {name: [] for name, _ in defs}
for p in root.rglob("*"):
    if not p.is_file(): continue
    if p.suffix not in {".py",".json",".md",".txt"}: continue
    text = p.read_text(encoding="utf-8", errors="ignore")
    for name, _ in defs:
        # count any call-like reference "name(" outside the def line
        for m in re.finditer(rf'\b{name}\s*\(', text):
            # skip the def line itself
            if p == target and f"def {name}(" in text[max(0, m.start()-30):m.end()+30]:
                continue
            refs[name].append(str(p))
unused = [ (n, ln) for n, ln in defs if not refs[n] ]
print("Unused defs in", target, ":\n" + ("\n".join(f"- {n} (line {ln})" for n, ln in unused) if unused else "None"))
