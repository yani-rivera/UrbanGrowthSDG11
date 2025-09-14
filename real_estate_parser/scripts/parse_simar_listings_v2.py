import argparse, csv, os, re, json


import sys,csv
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from datetime import datetime
import argparse, csv, json, os, re, hashlib


###############
from modules.parser_utils import clean_text_for_price,extract_price
from modules.agency_preprocess import configure_preprocess, preprocess_listings
from modules.record_parser import parse_record, detect_section_context
from scripts.helpers import infer_agency, infer_date, format_listing_row, FIELDNAMES, DEFAULT_PIPELINE_VERSION,build_release_row
from scripts.helpers import (
    make_prefile_numbered,
    count_numbered_bullets,
    count_star_bullets,
    split_raw_and_parse_line,make_prefile_star,write_prefile
)


#####---------------------------------------------------

# in scripts/parse_simar_listings_v1.py

def load_lines(path):
    with open(path, "r", encoding="utf-8", errors="ignore") as fh:
        for ln in fh:
            yield ln.rstrip("\n")

def main(file, config_path, output_dir):
    cfg = json.load(open(config_path, encoding="utf-8"))
    agency = infer_agency(config_path)
    date   = infer_date(file)
    year = date[:4]

     #======

    # ----- Phase 1: normalize leading listing markers (only if configured)
    # Phase-1 only if there's anything to change
    if cfg.get("listing_marker_tochange"):
        deli=cfg.get("listing_marker_tochange")
        file = make_prefile_star(
            input_path=file,
            agency=agency, 
            delimiter=deli,   # required in production
            year=year      # optional; inferred from path if omitted
              # ensure we don't silently fall back
        )

    if cfg.get("listing_marker") == "NUMBERED" and cfg.get("auto_masquerade_numdot"):
        file = make_prefile_numbered(file, agency)

    # =====LOAD FILE AND PREPROCESS

    configure_preprocess(cfg)
    listings = preprocess_listings(load_lines(file),
                marker=cfg.get("listing_marker"),
                agency=agency)
    
    #============
    
    out_path = write_prefile(
    registry_path="config/agencies_registry.json",
    agency="Simar",
    date_str=date,   # or "2025-09-04"
    rows=listings
        )
    print("prefile saved at:", out_path)

    #print ("DEBUG LISTITNG MARKER==>",file)

    #=========== Detect tyoe and transaction

    current_tx = current_type = current_cat = None
    rows = []
    for i, ln in enumerate(listings, 1):

        tx, ty, cat = detect_section_context(ln, cfg)
        if tx or ty or cat:
                current_tx  = tx  or current_tx
                current_type= ty  or current_type
                current_cat = cat or current_cat
                continue

        raw_line, text_for_parse = split_raw_and_parse_line(ln)
#=================
###### START PHASE 3==PARSING
#==================
        
        
        parsed = parse_record(
            text_for_parse, cfg,
            agency=agency, date=date, listing_no=i,
            default_transaction=current_tx,
            default_type=current_type,
            default_category=current_cat,
        )
        # 
        # --- price: strip per-unit & normalize currency spacing, then prefer higher ---
   
        clean_for_price = clean_text_for_price(text_for_parse)
        try_amount, try_curr = extract_price(clean_for_price, cfg)
        cur_amount = parsed.get("price") or ""
         
        if try_amount and (not cur_amount or float(try_amount) > float(cur_amount or 0)):
            parsed["price"], parsed["currency"] = try_amount, try_curr

        

    

        # --- area/AT mapping (construction m² preferred; terrain v² as fallback) ---
        ac = parsed.get("area_construction_m2") or parsed.get("area_m2") or ""
        at = parsed.get("area_terrain_v2")      or parsed.get("terrain_v2") or ""
        area_val, area_unit = ("", "")


        if ac:
            area_val, area_unit = ac, "m²"
        elif at:
            area_val, area_unit = at, "v²"
        AT_val, AT_unit = (at or "", "v²" if at else "")


        # line to display in notes

        final_line =  ln

        #####
        

        row = {
            "Listing ID": i,
            "title": final_line[:60],
            "neighborhood": parsed.get("neighborhood",""),
            "bedrooms": parsed.get("bedrooms",""),
            "bathrooms": parsed.get("bathrooms",""),

        # land size
            "AT": parsed.get("AT",""),
            "AT_unit": parsed.get("AT_unit",""),

        # built/general area
            "area": parsed.get("area",""),
            "area_unit": parsed.get("area_unit",""),
            "area_m2": parsed.get("area_m2",""),

            "price": parsed.get("price",""),
            "currency": parsed.get("currency",""),
            "transaction": parsed.get("transaction",""),
            "property_type": parsed.get("property_type",""),
            "agency": parsed.get("agency","") or agency,
            "date": parsed.get("date","") or date,
            "raw": final_line,
            "source_type": 'ocr_manual',
            "ingestion_id": os.path.basename(file),
            "pipeline_version": cfg.get("pipeline_version", "v1.0"),
        }

        ###debug
        
        row = format_listing_row(
        parsed, raw_line, i,
        source_type="ocr_manual",
        ingestion_id=os.path.basename(file),
        pipeline_version="v1.0",)
        
        
        if row and isinstance(row, dict):
            rows.append(row)
             
            
        output_fields = [
        "Listing ID", "title", "neighborhood", "bedrooms", "bathrooms",
        "AT", "AT_unit",
        "area", "area_unit", "area_m2",
        "price", "currency", "transaction", "property_type",
        "agency", "date", "notes", "source_type", "ingestion_id", "pipeline_version",
        ]

        

     
 #================ FOR END========
 # Ensure agency comes from args
    agency="simar"

    # Derive date from prefile if not already set
    #if "date" not in locals() or not date:
    file_name = os.path.basename(args.file)
    m = re.search(r'(\d{8})', file_name)  # look for 20151028
    date = m.group(1) if m else "unknown"

    # Extract year from date if possible
    year = date[:4] if date and date != "unknown" else "unknown"

    # Build directory: output/Agency/Year
    outdir = os.path.join(args.output_dir, "Simar", year)
    print("outdoe==>",outdir)
#=========
    if rows:
        os.makedirs(args.output_dir, exist_ok=True)
        dateprint=date

        outpath = outdir+"/"+agency+"_"+dateprint+".csv"
        with open(outpath, "w", newline="", encoding="utf-8-sig") as f:
            print("[SANITY] type(rows):", type(rows), "len(rows):", len(rows))
            if rows:
                #print("[SANITY] first row keys:", list(rows[0].keys()))
                print("[SANITY] sample last row title:", rows[-1].get("title"))

            writer = csv.DictWriter(f, fieldnames=output_fields)
            writer.writeheader()
            for r in rows:
            # make sure all fields exist
                for k in output_fields:
                    r.setdefault(k, "")
                writer.writerow(r)

        print(f"✅ Exported {len(rows)} listings to {outpath}")
    else:
        print(f"⚠️ No listings parsed. Check header detection and marker in {args.file}.")
   
       
        
if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", required=True)
    ap.add_argument("--config", required=True)
    ap.add_argument("--output-dir", required=True)
    ap.add_argument("--debug", action="store_true")
    args = ap.parse_args()

    print("[entry] starting parse_Simar_listings_v2.py")
    main(args.file, args.config, args.output_dir)

  
