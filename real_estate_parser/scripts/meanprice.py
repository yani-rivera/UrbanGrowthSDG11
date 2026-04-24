import pandas as pd
import os

# Input file
input_file = "nature/gis/price_mean_neighborhood_n5.csv"

# Output folder
output_dir = "by_year"
os.makedirs(output_dir, exist_ok=True)

# Read data
df = pd.read_csv(input_file, encoding="utf-8-sig")

# Ensure year is numeric
df["year"] = df["year"].astype(int)

# Years of interest
years = [2010, 2015, 2020, 2025]

# Split and save
for y in years:
    df_year = df[df["year"] == y]
    
    output_file = os.path.join(output_dir, f"price_mean_neighborhood_{y}.csv")
    df_year.to_csv(output_file, index=False, encoding="utf-8-sig")
    
    print(f"Saved: {output_file} ({len(df_year)} rows)")