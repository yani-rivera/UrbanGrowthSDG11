
# modules/output_utils.py

OUTPUT_FIELDS = [
    "Listing ID",
    "Title",
    "Neighborhood",
    "Bedrooms",
    "Bathrooms",
   "AT","Area","Area_Unit","Area_m2",
    "Area",
    "Price",
    "Currency",
    "Transaction",
    "Type",
    "Agency",
    "Date",
    "Notes",
    "Completeness"
]


def format_listing_row(parsed, raw_text, idx):
    return {
        "Listing ID": idx,
        "Title": raw_text[:60],
        "Neighborhood": parsed.get("neighborhood", ""),
        "Bedrooms": parsed.get("bedrooms", ""),
        "Bathrooms": parsed.get("bathrooms", ""),
  # built/general area
        "area": parsed.get("area",""),
        "area_unit": parsed.get("area_unit",""),
        "area_m2": parsed.get("area_m2",""),   # ← add normalized m²
        "Price": parsed.get("price", ""),
        "Currency": parsed.get("currency", ""),
        "Transaction": parsed.get("transaction", ""),
        "Type": parsed.get("property_type", ""),
        "Agency": parsed.get("agency", ""),
        "Date": parsed.get("date", ""),
        "Notes": raw_text[:200]
    }
