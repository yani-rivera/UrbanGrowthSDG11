#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ValidateTransaction_v2.py
import pandas as pd
import re
import argparse,json

# ============================================================
# CONFIG
# ============================================================



VALID_PROPERTY_TYPES = None
MIN_PRICE = None
PRICE_BANDS = None
SALE_TOKENS = None
RENT_TOKENS = None
AMBIGUOUS_PATTERNS = None


def load_semantic_config(path):
    with open(path, "r", encoding="utf-8-sig") as f:
        return json.load(f)



def load_transaction_rules(config_path):

    global VALID_PROPERTY_TYPES
    global MIN_PRICE
    global PRICE_BANDS
    global SALE_TOKENS
    global RENT_TOKENS
    global AMBIGUOUS_PATTERNS

    CONFIG = load_semantic_config(config_path)

    if "transaction_rules" not in CONFIG:
        raise ValueError(
            "Missing transaction_rules section in config."
        )

    TRX = CONFIG["transaction_rules"]

    VALID_PROPERTY_TYPES = set(TRX["valid_property_types"])
    MIN_PRICE = TRX["minimum_price"]
    PRICE_BANDS = TRX["transaction_boundaries"]
    SALE_TOKENS = TRX["sale_tokens"]
    RENT_TOKENS = TRX["rent_tokens"]

    AMBIGUOUS_PATTERNS = [
        re.compile(p, re.I)
        for p in TRX["ambiguous_patterns"]
    ]



# ============================================================
# HELPERS
# ============================================================

def norm(txt):
    return "" if pd.isna(txt) else str(txt).lower().strip()


def detect_notes_signal(notes):
    txt = norm(notes)

    for p in AMBIGUOUS_PATTERNS:
        if re.search(p, txt):
            return "AMBIGUOUS"

    sale_hit = any(re.search(rf"\b{re.escape(t)}\b", txt) for t in SALE_TOKENS)
    rent_hit = any(re.search(rf"\b{re.escape(t)}\b", txt) for t in RENT_TOKENS)

    if sale_hit and not rent_hit:
        return "SALE"
    if rent_hit and not sale_hit:
        return "RENT"
    if sale_hit and rent_hit:
        return "AMBIGUOUS"

    return "NONE"


def normalize_price(val):
    if pd.isna(val):
        return None
    try:
        return float(val)
    except Exception:
        s = str(val).replace(",", "")
        m = re.search(r"(\d+\.?\d*)", s)
        return float(m.group(1)) if m else None

# ============================================================
# ROW VALIDATION
# ============================================================

def validate_row(row):
    ptype = str(row.get("property_type_new", "")).strip().upper()
    declared = str(row.get("transaction", "")).strip().upper()
    notes = row.get("notes", "")
    price = normalize_price(row.get("price_usd"))

    # --------------------------------------------------------
    # 1. Scope enforcement
    # --------------------------------------------------------
    if ptype not in VALID_PROPERTY_TYPES:
        return [None, "FLAG_OUT_OF_SCOPE", "NEGATIVE", "scope", "NONE"]

    # --------------------------------------------------------
    # 2. Hard minimum price
    # --------------------------------------------------------
    min_price = MIN_PRICE.get(ptype)
    if price is None or price < min_price:
        return [None, "REMOVED_INVALID_PRICE", "NEGATIVE", "price_min", "NONE"]

    # --------------------------------------------------------
    # 3. Resolve declared / notes transaction
    # --------------------------------------------------------
    transaction_hint = declared if declared in {"SALE", "RENT"} else None
    source = "declared" if transaction_hint else "none"
    confidence = "HIGH" if transaction_hint else "LOW"

    notes_signal = detect_notes_signal(notes)

    if transaction_hint is None and notes_signal in {"SALE", "RENT"}:
        transaction_hint = notes_signal
        source = "notes"
        confidence = "MEDIUM"

    # --------------------------------------------------------
    # 4. PRICE × TYPE × TRANSACTION DECISION (AUTHORITATIVE)
    # --------------------------------------------------------
    band = PRICE_BANDS.get(ptype)
    rent_ok = price <= band["rent_max"]
    sale_ok = price >= band["sale_min"]

    # ---- Declared / hinted transaction valid
    if transaction_hint == "RENT" and rent_ok:
        return ["RENT", "OK_DECLARED", "POSITIVE", source, confidence]

    if transaction_hint == "SALE" and sale_ok:
        return ["SALE", "OK_DECLARED", "POSITIVE", source, confidence]

    # ---- Declared invalid → try flipped
    if transaction_hint == "SALE" and rent_ok:
        return ["RENT", "CORRECTED_PRICE_BOUNDARY", "POSITIVE", "price+ptype", "HIGH"]

    if transaction_hint == "RENT" and sale_ok:
        return ["SALE", "CORRECTED_PRICE_BOUNDARY", "POSITIVE", "price+ptype", "HIGH"]

    # ---- No feasible transaction
    return [None, "REMOVED_PRICE_OUT_OF_RANGE", "NEGATIVE", "price+ptype", "HIGH"]

# ============================================================
# CLI
# ============================================================

def main():
    ap = argparse.ArgumentParser(
        description="Resolve transaction as a result of price × property type feasibility"
    )
    ap.add_argument("--input", required=True, help="Input CSV")
    ap.add_argument("--output", required=True, help="Output CSV")
    ap.add_argument(
        "--config",
        default="config/price_semantic_config.json"
    )
    args = ap.parse_args()

    df = pd.read_csv(args.input, encoding="utf-8-sig")
    load_transaction_rules(args.config)



    required = {"transaction", "price_usd", "property_type_new", "notes"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing columns: {missing}")

    result = df.apply(validate_row, axis=1, result_type="expand")
    print("=" * 60)
    print("RESULT SHAPE:", result.shape)
    print("CURRENT COLUMNS:")
    print(list(result.columns))
    print("=" * 60)
    result.columns = [
        "transaction_final",
        "transaction_flag",
        "flag_polarity",
        "transaction_decision_source",
        "transaction_confidence",
    ]

    df = pd.concat([df, result], axis=1)
    df.to_csv(args.output, index=False, encoding="utf-8-sig")

    print("[OK] Transaction resolution complete")
    print(df["transaction_flag"].value_counts())
    flag_counts = (
    df["transaction_flag"]
    .value_counts()
    .to_dict()
    )

    print(flag_counts)

if __name__ == "__main__":
    main()
