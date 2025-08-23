
# scripts/debug_listing.py
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import json
from modules.debug_utils import debug_listing

# Load config
with open("config/agency_serpecal.json", "r", encoding="utf-8") as f:
    config = json.load(f)

# Example raw listing text
sample_text = "Casa de 3 habitaciones, 2 baños, cocina amplia, 180 m² de construcción y 498.23 vrs² de terreno, Lps. 2,500,000"

# Debug it
debug_listing(sample_text, config)
