
# scripts/generate_qc_report.py
import os, json, argparse, csv
from modules.record_parser import parse_record
from modules.output_utils import format_listing_row
from modules.qa_utils import is_multi_offer, missing_fields

OUTPUT_FIELDS = [
    "Listing ID","Title","Neighborhood","Bedrooms","Bathrooms",
    "AT","Area","Price","Currency","Transaction","Type","Agency","Date","Notes"
]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", required=True)
    ap.add_argument("--config", required=True)
    ap.add_argument("--agency", required=True)
    ap.add_argument("--date", required=True)
    ap.add_argument("--out", default="qc_reports")
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)
    base = os.path.splitext(os.path.basename(args.file))[0]
    txt_report = os.path.join(args.out, f"{base}_QC_report.txt")
    flags_csv  = os.path.join(args.out, f"{base}_QC_flags.csv")

    # Load config as DICT
    with open(args.config, "r", encoding="utf-8") as f:
        config = json.load(f)

    with open(args.file, "r", encoding="utf-8") as f:
        listings = [ln.rstrip("\n") for ln in f if ln.strip()]

    total = 0
    missing_counts = {k:0 for k in ["Price","Currency","Bedrooms","Bathrooms","AT","Area","Transaction","Type","Neighborhood"]}
    multi_candidates = []
    flagged_rows = []

    for idx, listing in enumerate(listings, 1):
        # Keep same gating as your parser (skip non-listing lines if needed)
        total += 1
        parsed = parse_record(listing, config, agency=args.agency, date=args.date, listing_no=idx)
        if not isinstance(parsed, dict):
            continue
        row = format_listing_row(parsed, listing, idx)

        # Missing fields
        mf = missing_fields(row)
        for k in mf:
            missing_counts[k] += 1

        # Multi-offer detection (does not split, only flags)
        multi = is_multi_offer(listing)
        if multi["multi_price"] or multi["multi_bedrooms"]:
            multi_candidates.append((idx, multi["bedrooms_found"], multi["prices_found"]))

        # Save per-row flags to CSV
        flagged_rows.append({
            "Listing ID": row["Listing ID"],
            "Title": row["Title"],
            "Missing Fields": "; ".join(mf),
            "Multi Offer": "YES" if (multi["multi_price"] or multi["multi_bedrooms"]) else "NO",
            "Prices Found": " / ".join(multi["prices_found"]),
            "Bedrooms Found": " / ".join(map(str, multi["bedrooms_found"])),
            "Notes": row["Notes"][:150]
        })

    # Write text summary
    with open(txt_report, "w", encoding="utf-8") as out:
        out.write(f"QC SUMMARY for {args.agency} on {total} listings\n\n")
        out.write("Missing fields counts:\n")
        for k,v in missing_counts.items():
            out.write(f" - {k:12}: {v}\n")
        out.write("\nMulti-offer candidates (ListingID: beds | prices):\n")
        if not multi_candidates:
            out.write(" - none\n")
        else:
            for lid, beds, prices in multi_candidates:
                out.write(f" - #{lid}: beds={beds} | prices={prices}\n")

    # Write flag details CSV
    with open(flags_csv, "w", newline="", encoding="utf-8") as fcsv:
        writer = csv.DictWriter(fcsv, fieldnames=[
            "Listing ID","Title","Missing Fields","Multi Offer","Prices Found","Bedrooms Found","Notes"
        ])
        writer.writeheader()
        writer.writerows(flagged_rows)

    print(f"\n✅ QC summary: {txt_report}")
    print(f"✅ QC flags  : {flags_csv}")

if __name__ == "__main__":
    main()
