import re
import sys
sys.path.append('../scripts')



from scripts.parser_utils import (
     extract_price,
     extract_area,
     extract_bedrooms,
     extract_bathrooms,
     extract_property_type
)


def parse_record(text, config, agency, date, listing_no):
    try:
        price, curr = extract_price(text, config.get("currency_aliases", {}))
        area_construction, area_terrain = extract_area(text, config.get("area_aliases", {}))
        bedrooms = extract_bedrooms(text, config.get("bedroom_keywords", []))
        bathrooms = extract_bathrooms(text, config.get("bathroom_keywords", []))
        property_type = extract_property_type(text, config.get("type_keywords", {}))

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
            "currency": curr
        }

    except Exception as e:
        print(f"Error parsing listing #{listing_no}: {e}")
        return {
            "bedrooms": "",
            "bathrooms": "",
            "area_construction": "",
            "area_terrain": "",
            "property_type": "",
            "description": text.strip(),
            "agency": agency,
            "date": date,
            "listing_no": listing_no,
            "price": "",
            "currency": ""
        }
