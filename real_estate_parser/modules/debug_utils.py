
# modules/debug_utils.py

#from modules.parser_utils import (
  #  extract_bedrooms,
   # extract_bathrooms,
   # extract_area,
   # extract_price,
   # extract_property_type
#)
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from modules.record_parser import parse_record

def debug_listing(text, config):
    
    parsed = parse_record(
        text,
        config,
        agency="DEBUG",
        date="2025-08-23",
        listing_no=1
    )

    print("=== DEBUGGING LISTING ===")
    print(f"Input text:\n{text}\n")
    print(f"Bedrooms: {parsed.get('bedrooms', '')}")
    print(f"Bathrooms: {parsed.get('bathrooms', '')}")
    print(f"Area construction: {parsed.get('area_construction', '')}")
    print(f"Area terrain: {parsed.get('area_terrain', '')}")
    print(f"Price: {parsed.get('price', '')}")
    print(f"Currency: {parsed.get('currency', '')}")
    print(f"Property type: {parsed.get('property_type', '')}")
    print(f"Notes: {parsed.get('description', '')[:150]}")
    print("=========================")