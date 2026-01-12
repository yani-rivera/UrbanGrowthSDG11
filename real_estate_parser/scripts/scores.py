import argparse
import os
import sys
import pandas as pd

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from L1clean.ptype_l1_clean_v7 import classify_structure


def export_scores(input_csv, output_csv):
    df = pd.read_csv(input_csv)

    rows = []

    for _, row in df.iterrows():
        out = classify_structure(row)

        # ---- Normalize classifier output ----
        if isinstance(out, tuple) and len(out) == 2:
            final_type, second = out
        else:
            raise ValueError(f"Unexpected return from classify_structure: {out}")

        # New-style: (final_type, scores_dict)
        if isinstance(second, dict):
            scores = second
            reason_code = f"POINTS:{final_type}({scores.get(final_type, 0)})"

        # Legacy-style: (final_type, reason_string)
        elif isinstance(second, str):
            scores = {
                "House": 0,
                "Apartment": 0,
                "Commercial": 0,
                "Land": 0,
            }
            reason_code = second

        else:
            raise TypeError(f"Unexpected second return type: {type(second)}")

        # ---- Append audit row ----
        rows.append({
            "listing_id": row.get("listing_id"),
            "source": row.get("source"),
            "date": row.get("date"),
            "original_type": row.get("property_type"),
            "final_type": final_type,
            "reason_code": reason_code,
            "notes": row.get("notes", ""),

            "score_house": scores.get("House", 0),
            "score_apartment": scores.get("Apartment", 0),
            "score_commercial": scores.get("Commercial", 0),
            "score_land": scores.get("Land", 0),

            "score_max": max(scores.values()),
            "score_winner": max(scores, key=scores.get),
        })

    pd.DataFrame(rows).to_csv(output_csv, index=False)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, help="Input CSV (unchanged main output)")
    ap.add_argument("--output", required=True, help="Audit CSV with scores")
    args = ap.parse_args()

    export_scores(args.input, args.output)
