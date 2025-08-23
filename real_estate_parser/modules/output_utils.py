
# modules/output_utils.py

OUTPUT_FIELDS = [
    "Listing ID",
    "Title",
    "Neighborhood",
    "Bedrooms",
    "Bathrooms",
    "AT",
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
        "AT": parsed.get("area_terrain", ""),
        "Area": parsed.get("area_construction", ""),
        "Price": parsed.get("price", ""),
        "Currency": parsed.get("currency", ""),
        "Transaction": parsed.get("transaction", ""),
        "Type": parsed.get("property_type", ""),
        "Agency": parsed.get("agency", ""),
        "Date": parsed.get("date", ""),
        "Notes": raw_text[:200]
    }
