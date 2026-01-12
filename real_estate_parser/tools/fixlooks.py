
import pandas as pd, re, numpy as np

wide = pd.read_csv('./output/configs_wide.csv', index_col=0)
sel_path = './output/configs_selected.csv'
sel = pd.read_csv(sel_path, index_col=0) if (pd.io.common.file_exists(sel_path)) else pd.DataFrame(index=wide.index)

# Find ANY preprocess array columns (case-insensitive, nested or top-level):
rx = re.compile(r'(?:^|\.)preprocess\[(\d+)\]$', re.IGNORECASE)
cols = []
for c in wide.columns:
    m = rx.search(c)
    if m:
        cols.append((int(m.group(1)), c))
cols = [c for _, c in sorted(cols, key=lambda t: t[0])]

# Build the joined string per agency
if cols:
    joined = wide[[c for c in cols]].apply(
        lambda r: ",".join(str(v).rstrip(".0") for v in r if pd.notna(v)), axis=1
    ).replace("", np.nan)
    sel["Preprocess Steps"] = joined

# Save back (overwrites if exists)
sel.to_csv(sel_path)
print("✅ Added 'Preprocess Steps' to configs_selected.csv")
