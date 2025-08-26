# version 2
import re
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


from modules.agency_preprocess import preprocess
from modules.neighborhood_utils import extract_neighborhood
from modules.parser_utils import (
    extract_price, extract_area, extract_bedrooms, extract_bathrooms, extract_property_type,extract_transaction,detect_section_context
)



# from modules.parser_utils import (
#     extract_price,
#     extract_area,
#     extract_bedrooms,
#     extract_bathrooms,
#     extract_property_type,
#     normalize_ocr_text
# )

def parse_record(text, config, agency, date, listing_no,default_transaction=None, default_type=None, default_category=None):
    raw_text = text
    norm = preprocess(text, agency)

    neighborhood = extract_neighborhood(norm, config, agency)
    price, currency = extract_price(norm, config)
    ac, at = extract_area(norm, config)
    beds = extract_bedrooms(norm, config)
    baths = extract_bathrooms(norm, config)
     
    result = detect_section_context(text, config)
    #print(f"[DEBUG] detect_section_context returned: {result} (type: {type(result)})")

    # Force unpacking for visibility
    if isinstance(result, tuple) and len(result) == 3:
        tx, ty, cat = result
    else:
        raise ValueError(f"Unexpected return value from detect_section_context: {result}")


   # if not property_type or property_type.lower() == "other":
    #    property_type = default_type

    return {
        "bedrooms": beds or "",
        "bathrooms": baths or "",
        "area_construction": ac or "",
        "area_terrain": at or "",
        "property_type": ty,
        "description": raw_text.strip(),
        "agency": agency,
        "date": date,
        "listing_no": listing_no,
        "price": price or "",
        "currency": currency or "",
        "transaction": tx,                    # ← inherited if missing
        "neighborhood": neighborhood or "",
        "category": cat or ""    # optional; use in output if you like
       }
#except Exception as e:
   # print(f"Error parsing listing #{listing_no}: {e}")
   
def preprocess_listings(lines: list[str], marker: str = "-") -> list[str]:
    """
    Merge multiline listings into a single row based on a start marker.

    Args:
        lines (list[str]): Raw lines from the input text.
        marker (str): The symbol/string that marks the beginning of a new listing (e.g., "-").

    Returns:
        list[str]: List of full listings, each as a single space-joined string.
    """
    merged = []
    current_listing = []

    for line in lines:
        clean_line = line.strip()
        if not clean_line:
            continue

        if clean_line.startswith(marker) and current_listing:
            merged.append(" ".join(current_listing).strip())
            current_listing = [clean_line]
        else:
            current_listing.append(clean_line)

    if current_listing:
        merged.append(" ".join(current_listing).strip())

    return merged

  