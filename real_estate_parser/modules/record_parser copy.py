# version 2
import re
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from modules.agency_preprocess import serpecal_preprocess, extract_neighborhood_serpecal

from modules.parser_utils import (
    extract_price,
    extract_area,
    extract_bedrooms,
    extract_bathrooms,
    extract_property_type,
    normalize_ocr_text
)

def parse_record(text, config, agency, date, listing_no):
    try:
        if agency.upper() == "SERPECAL":
            text = serpecal_preprocess(text)
            
        else:
            text = normalize_ocr_text(text)

        # neighborhood (agency-specific)
        neighborhood = extract_neighborhood_serpecal(text) if agency.upper() == "SERPECAL" else ""

        price, curr = extract_price(text, config)
        area_construction, area_terrain = extract_area(text, config)
        bedrooms = extract_bedrooms(text, config)
        bathrooms = extract_bathrooms(text, config)
        property_type = extract_property_type(text, config)

        # optional: infer transaction if not set elsewhere
        tx = ""
        if "alquiler" in text or "renta" in text:
            tx = "Rent"
        elif any(w in text for w in ("venta", "se vende", "lps.", "$")):
            tx = "Sale"

        return {
            "bedrooms": bedrooms,
            "bathrooms": bathrooms,
            "area_construction": area_construction,
            "area_terrain": area_terrain,
            "property_type": property_type,
            "description": text.strip(),
            "agency": agency,
            "date": date,
            "listing_no": listing_no,
            "price": price,
            "currency": curr,
            "transaction": tx,
            "neighborhood": neighborhood,
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