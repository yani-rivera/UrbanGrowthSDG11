# version 2.1 Feb 09 2026
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
extract_agency_html_to_txt.py
------------------------------

Modular HTML → TXT extractor for SDG-11 dataset.

Supports:
    - Specialized parsers (CS, Trebol, Mariposa…)
    - Generic extraction (Wasi JSON-LD + HTML selectors)
    - YAML configuration per agency
    - One-line output format per listing

Output encoding: UTF-8-SIG (Excel friendly)
"""

import os, sys
import argparse
import yaml
import json
import re
import warnings
from bs4 import BeautifulSoup, MarkupResemblesLocatorWarning

#=============

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

######



warnings.filterwarnings("ignore", category=MarkupResemblesLocatorWarning)

# -------------------------------------------------------
# Import specialized agency parsers (inside scripts/parsers/)
# -------------------------------------------------------
#from parsers import parser_cs
from parsers.parse_cs import parse_cs
from parsers.parse_mariposa import parse_mariposa

# Add more when available:
# from parsers import parser_trebol
#from parsers import parser_mariposa
# from parsers import parser_wasi


# -------------------------------------------------------
# Map agency → parser strategy
# -------------------------------------------------------
AGENCY_TEMPLATE_MAP = {
    "carttonlands": "wasi",
    "fantasia": "wasi",
    "lonitton": "wasi",

}

# Specialized parser dispatch
PARSER_DISPATCH = {
    "carttonlands": parse_cl,
    "casamagica": parse_casamagica,

}


# -------------------------------------------------------
# Text cleaning helpers
# -------------------------------------------------------

_EMOJI_RE = re.compile(
    "[" 
    "\U0001F300-\U0001F5FF"
    "\U0001F600-\U0001F64F"
    "\U0001F680-\U0001F6FF"
    "\U0001F700-\U0001F77F"
    "\U0001F780-\U0001F7FF"
    "\U0001F800-\U0001F8FF"
    "\U0001F900-\U0001F9FF"
    "\U0001FA00-\U0001FA6F"
    "\U0001FA70-\U0001FAFF"
    "\U00002600-\U000026FF"
    "\U00002700-\U000027BF"
    "]",
    flags=re.UNICODE,
)

def clean_text_field(val: str) -> str:
    """Basic normalization for text extracted from HTML."""
    if not val:
        return ""
    val = val.strip()
    # Remove emojis and symbols
    val = _EMOJI_RE.sub("", val)
    # Normalize spaces
    val = re.sub(r"\s+", " ", val)
    return val.strip()


def clean_html(raw: str) -> str:
    """Clean descriptions or large text bodies."""
    if not raw:
        return ""
    txt = BeautifulSoup(raw, "html.parser").get_text(" ", strip=True)
    txt = _EMOJI_RE.sub(" ", txt)
    txt = re.sub(r"\s+", " ", txt)
    return txt.strip()


def safe_soup(html):
    return BeautifulSoup(html, "html.parser")


# -------------------------------------------------------
# JSON-LD extraction for WASI-type agencies
# -------------------------------------------------------
def parse_jsonld_all(soup):
    """Extract all JSON-LD blocks and return Python objects."""
    results = []
    for tag in soup.find_all("script", type="application/ld+json"):
        try:
            txt = tag.string or tag.text
            if txt:
                obj = json.loads(txt)
                if isinstance(obj, list):
                    results.extend(obj)
                else:
                    results.append(obj)
        except Exception:
            continue
    return results


def extract_fields_from_jsonld_obj(obj, cfg):
    """Extract JSON-LD values based on YAML config."""
    out = []
    for f in cfg.get("fields", []):
        key = f.get("jsonld_key")
        if key and key in obj:
            val = obj[key]
            if isinstance(val, dict) and "@value" in val:
                val = val["@value"]
            val = clean_text_field(str(val))
            out.append(f"{f['name']}: {val}")
    return out

# -------------------------------------------------------
# JSON-LD extraction ID FOS 504
# -------------------------------------------------------


def extract_property_id(soup: BeautifulSoup, cfg: dict) -> str:
    """Extract the property ID from the listing (dynamically based on agency config)."""
    # Look for the <input> with id='contact_request_property_id'
    id_node = soup.select_one('input#contact_request_property_id')
    if id_node and id_node.has_attr('value'):
        return clean_text_field(id_node['value'])  # Return the value of the input tag
    
    return "No ID Found"  # Return if no ID found


def extract_url(soup: BeautifulSoup) -> str:
    """Extract the URL from the meta tags."""
    # Look for the <meta> tag with property="og:url"
    url_node = soup.select_one('meta[property="og:url"]')
    if url_node and url_node.has_attr('content'):
        return clean_text_field(url_node['content'])  # Return the content attribute
    
    return "No URL Found"  # Return if no URL found

def extract_detailed_desc(soup: BeautifulSoup) -> str:
    """Extract the detailed description from the 'div#description' section."""
    # Look for the detailed description in the div with id="description"
    detailed_desc_node = soup.select_one('div#description')
    
    if detailed_desc_node:
        # Clean and return the detailed description text
        return clean_html(detailed_desc_node.get_text(strip=True))
    
    return "No Detailed Description Found"  # If no description found

# -------------------------------------------------------
# Bullet formatting for generic extraction
# -------------------------------------------------------
def to_bullet(line: str) -> str:
    if not line:
        return ""
    line = line.replace(";;", ";").strip()
    return "* " + line

def format_listing_output(location: str, data: dict) -> str:
    """Format the listing data as a one-line output."""
    # Start with the neighborhood (or location)
    output = f"* {location}: "
    print("data in format", data)
    # Collect all fields in a single string (ignore empty values)
    details = []
    for key, value in data.items():
        
        if value:  # Skip empty values
            # Exclude URL if it is already added in the listing text
            # if key.lower() == "url":
            #     continue
            details.append(f"{key.capitalize()}: {value}")

    # Join all details into a single string, separated by commas
    output += ", ".join(details)

    # Append the listing URL at the end
    # if "url" in data and data["url"] != "No URL found":
    output += f"\n"

    return output


# -------------------------------------------------------
# Load YAML configurations
# -------------------------------------------------------
def load_configs(cfg_dir):
    cfgs = {}
    for fn in os.listdir(cfg_dir):
        if fn.endswith(".yaml") or fn.endswith(".yml"):
            path = os.path.join(cfg_dir, fn)
            name = os.path.splitext(fn)[0]
            with open(path, "r", encoding="utf-8-sig") as f:
                cfgs[name] = yaml.safe_load(f)
    return cfgs


# -------------------------------------------------------
# Generic fallback extraction (Wasi, Cointec, etc.)
# -------------------------------------------------------
def generic_extract(raw_html, cfg):
    soup = safe_soup(raw_html)
    lines = []

    # 1) JSON-LD extraction path
    if cfg.get("parser") == "wasi" or cfg.get("jsonld_split", False):
        json_objs = parse_jsonld_all(soup)
        if json_objs:
            for obj in json_objs:
                parts = extract_fields_from_jsonld_obj(obj, cfg)
                if parts:
                    lines.append("; ".join(parts))

    # 2) HTML fallback if no JSON-LD
    if not lines:
        listing_sel = cfg.get("listing_selector")
        elems = soup.select(listing_sel) if listing_sel else [soup]

        def sel_fix(s):
            return s.replace(":contains(", ":-soup-contains(") if s else s

        for el in elems:
            parts = []
            for f in cfg.get("fields", []):
                sel = sel_fix(f.get("selector"))
                attr = f.get("attr")
                val = None

                if sel:
                    node = el.select_one(sel)
                    if node:
                        val = node.get(attr) if attr else node.get_text(strip=True)

                if val:
                    name = f["name"]
                    keylower = name.lower()
                    if keylower in {"description", "name", "extras", "address"}:
                        val = clean_html(val)
                    else:
                        val = clean_text_field(val)
                    parts.append(f"{name}: {val}")

            if parts:
                lines.append("; ".join(parts))

    return [to_bullet(l) for l in lines if l.strip()]

def extract_agency_data(soup: BeautifulSoup, parser_type: str, cfg: dict) -> list:
    """Extract agency-specific data based on the provided configuration."""
    lines = []
    
    # Check if the agency-specific parser exists in the configuration
    agency_config = cfg.get(parser_type, {})

    # Extract data based on the fields in the config
    for field in agency_config.get("fields", []):
        name = field.get("name")
        selector = field.get("selector")
        attr = field.get("attr", None)
        method = field.get("method", None)  # Custom method for extraction (if any)

        # Extract the value based on the selector
        if selector:
            node = soup.select_one(selector)
            if node:
                # Extract the value based on the type of field (attribute or text)
                if attr:
                    value = node.get(attr)
                else:
                    value = node.get_text(strip=True)

                # If a custom method is defined (like for extracting phone numbers, etc.)
                if method:
                    value = globals().get(method, lambda x: x)(value)

                # Clean and add the extracted value to the lines list
                if value:
                    lines.append(f"{name}: {clean_text_field(value)}")

    return lines

# -------------------------------------------------------
# Unified file processor (specialized → generic)
# -------------------------------------------------------

def process_file(file_path, cfg, parser_type, date, out_path):
    """Return a list of formatted text lines extracted from a single HTML file."""
    
    with open(file_path, "r", encoding="utf-8-sig", errors="ignore") as f:
        raw = f.read()

    # Parse the HTML with BeautifulSoup
    soup = BeautifulSoup(raw, "html.parser")

    # Initialize the list to hold extracted fields
    lines = []
    data = {}

    # Extract agency-specific data (e.g., contact info, property ID)
    agency_data = extract_agency_data(soup, parser_type, cfg)
    for field in agency_data:
        lines.append(field)

    # 1) Extract the property ID (reuse the existing extraction function)
    property_id = extract_property_id(soup, cfg)  # Property ID extraction
    data["property_id"] = property_id  # Store the extracted property ID

    # 2) Extract the URL (call the new extract_url function only once)
    url = extract_url(soup)  # Extract the URL
    data["url"] = url  # Store the URL in the data dictionary

    # 3) Extract the detailed description (new function call)
    detailed_desc = extract_detailed_desc(soup)  # Extract the large description
    data["detailed_description"] = detailed_desc  # Store the detailed description

    # 4) Extract other general fields (price, description, etc.)
    for f in cfg.get("fields", []):  # Use 'fields' for other common fields
        key = f['name']
        if key not in ["contact_info", "property_id", "url", "detailed_description"]:  # Skip already extracted fields
            sel = f.get("selector")
            val = None
            if sel:
                node = soup.select_one(sel)
                if node:
                    val = node.get_text(strip=True)
            if val:
                # Clean the value and store it in the data dictionary
                data[key] = clean_text_field(val)

    # 5) Extract the neighborhood (location) for the listing
    location = data.get("location", "Unknown location")

    # 6) Format the listing output in one line with the property ID and URL included
    formatted_output = format_listing_output(location, data)

    # Write the formatted output to the output file
    with open(out_path, "a", encoding="utf-8-sig") as out_file:
        out_file.write(formatted_output)

    return lines


# -------------------------------------------------------
# Folder processor
# -------------------------------------------------------
def process_folder(folder, cfg, parser_type, out_path, date):
    all_lines = []

    for root, _, files in os.walk(folder):
        for fn in files:
            if fn.lower().endswith((".html", ".htm")):
                fp = os.path.join(root, fn)
                extracted = process_file(fp, cfg, parser_type, date, out_path)  # Pass date and out_path to process_file
                all_lines.extend(extracted)

    print(f"[OK] Processed folder → {folder}")


# -------------------------------------------------------
# MAIN
# -------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description="Extract listings from HTML to TXT with modular parsers.")
    ap.add_argument("--folder", required=True, help="Folder containing .html/.htm files")
    ap.add_argument("--date", required=True, help="Date tag (e.g., 20250529)")
    ap.add_argument("--output", required=True, help="Output folder")
    ap.add_argument("--agency", required=True, help="Agency name (cs, wasi, trebol, etc.)")
    ap.add_argument("--configs", default=None, help="Directory containing YAML configs")
    args = ap.parse_args()

    here = os.path.dirname(os.path.abspath(__file__))

    # Resolve config directory
    cfg_dir = args.configs or os.path.join(here, "configs")
    if not os.path.isdir(cfg_dir):
        alt = os.path.join(here, "..", "configs")
        if os.path.isdir(alt):
            cfg_dir = alt
        else:
            raise SystemExit(f"Config directory not found: {cfg_dir}")

    cfgs = load_configs(cfg_dir)

    agency = args.agency.lower()
    parser_type = AGENCY_TEMPLATE_MAP.get(agency, agency)

    config_file = os.path.join(cfg_dir, f"{parser_type}.yaml")
    if not os.path.exists(config_file):
        raise SystemExit(f"No config file found for parser type '{parser_type}' → {config_file}")

    with open(config_file, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    os.makedirs(args.output, exist_ok=True)
    out_name = f"{agency}_{args.date}.txt"  # Now the date is used from the argument
    out_path = os.path.join(args.output, out_name)

    print(f"[info] Agency: {agency} → Parser: {parser_type}")
    print(f"[info] Config: {config_file}")

    process_folder(args.folder, cfg, parser_type, out_path, args.date)


if __name__ == "__main__":
    main()
