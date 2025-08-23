
import json, argparse
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from modules.agency_preprocess import serpecal_preprocess
from modules.record_parser import parse_record

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", required=True)
    ap.add_argument("--config", required=True)
    args = ap.parse_args()

    with open(args.config, "r", encoding="utf-8") as f:
        cfg = json.load(f)

    with open(args.file, "r", encoding="utf-8") as f:
        lines = [ln.strip() for ln in f if ln.strip()]

    missing = {"price":0,"currency":0,"bedrooms":0,"bathrooms":0,"ac":0,"at":0,"type":0}
    total=0
    for i, raw in enumerate(lines, 1):
        if raw.startswith("*"):
            total += 1
            parsed = parse_record(raw, cfg, agency="SERPECAL", date="2015-12-28", listing_no=i)
            # Count missing fields
            if not parsed.get("price"): missing["price"]+=1
            if not parsed.get("currency"): missing["currency"]+=1
            if parsed.get("bedrooms","")=="": missing["bedrooms"]+=1
            if parsed.get("bathrooms","")=="": missing["bathrooms"]+=1
            if parsed.get("area_construction","")=="": missing["ac"]+=1
            if parsed.get("area_terrain","")=="": missing["at"]+=1
            if parsed.get("property_type","") in ("","other"): missing["type"]+=1

    print(f"\nSERPECAL summary on {total} listings:")
    for k,v in missing.items():
        print(f" - missing {k}: {v}")

if __name__ == "__main__":
    main()
