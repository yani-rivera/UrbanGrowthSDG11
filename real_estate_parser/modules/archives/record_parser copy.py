# version 2
import re
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


from modules.agency_preprocess import preprocess
from modules.neighborhood_utils import extract_neighborhood
from modules.parser_utils import (
    extract_price, extract_area, extract_bedrooms, extract_bathrooms, extract_property_type
)



# from modules.parser_utils import (
#     extract_price,
#     extract_area,
#     extract_bedrooms,
#     extract_bathrooms,
#     extract_property_type,
#     normalize_ocr_text
# )

def parse_record(text, config, agency, date, listing_no):
    try:
        raw_text = text  # keep original for Notes

        # PREPROCESS (one call; no if/else by agency here)
        norm = preprocess(text, agency)

        # NEIGHBORHOOD (config‑driven)
        neighborhood = extract_neighborhood(norm, config, agency)

        # OTHER FIELDS
        price, currency = extract_price(norm, config)
        ac, at         = extract_area(norm, config)
        beds           = extract_bedrooms(norm, config)
        baths          = extract_bathrooms(norm, config)
        prop_type      = extract_property_type(norm, config)

        return {
            "bedrooms": beds,
            "bathrooms": baths,
            "area_construction": ac,
            "area_terrain": at,
            "property_type": prop_type,
            "description": raw_text.strip(),
            "agency": agency,
            "date": date,
            "listing_no": listing_no,
            "price": price,
            "currency": currency,
            "neighborhood": neighborhood,
        }
    except Exception as e:
        print(f"Error parsing listing #{listing_no}: {e}")
        return {
            "bedrooms": "",
            "bathrooms": "",
            "area_construction": "",
            "area_terrain": "",
            "property_type": "",
            "description": raw_text.strip() if text else "",
            "agency": agency,
            "date": date,
            "listing_no": listing_no,
            "price": "",
            "currency": "",
            "neighborhood": "",
        }
    except Exception as e:
        print(f"Error parsing listing #{listing_no}: {e}")
        return {
            "bedrooms": "", "bathrooms": "", "area_construction": "",
            "area_terrain": "", "property_type": "",
            "description": text.strip(), "agency": agency, "date": date,
            "listing_no": listing_no, "price": "", "currency": "",
            "transaction": "", "neighborhood": ""
        }