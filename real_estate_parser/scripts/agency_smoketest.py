
# after summarizing units, also summarize source_type
units = collections.Counter(); sources = collections.Counter()
...
if row.get('source_type'):
sources[row['source_type']] += 1
return n, units, sources

# when printing
n, units, sources = summarize_csv(csv_path)
print(f" rows={n} units={dict(units)} sources={dict(sources)} csv={csv_path}")
