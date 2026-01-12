#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ptype_l1_clean_v8.py

Property Type L1 classification (v8)

Key properties:
- Points-based scoring (highest bid wins)
- Residential dominance over land signals
- Explicit commercial use wins
- Original type gets weak prior (+3)
- Dorms is inherited only (never inferred)
- Classifier is PURE (no I/O, no globals)
- Optional audit file with per-category scores

Returns:
- property_type_l1
- property_type_reason
- property_type_changed
"""

import argparse
import re
import unicodedata
import pandas as pd

# -----------------------
# Normalization
# -----------------------

def normalize_text(text: str) -> str:
    if not isinstance(text, str):
        return ""
    t = unicodedata.normalize("NFKD", text)
    t = "".join(c for c in t if not unicodedata.combining(c))
    t = t.lower()
    return re.sub(r"\s+", " ", t).strip()

# -----------------------
# Keyword patterns
# -----------------------

# RESIDENCIAL

HOUSE_KW = re.compile(
    r"\b(casa(s)?|residencia(s)?|familiar(es)?|vivienda(s)?)\b",
    re.I
)


APT_KW = re.compile(
    r"\b(apartamento|apartamentos|departamento|apto|aptos|condominio|penthouse)\b",
    re.I,
)

BEDROOM_KW = re.compile(
    r"\b(habitacion(?:es)?|recamara(?:s)?|dormitorio(?:s)?|alcoba(?:s)?|\d+\s*hab)\b",
    re.I,
)

ZERO_BEDROOMS_KW = re.compile(
    r"\b("
    r"habitaciones?|hab(?:s)?|bedrooms?"
    r")\s*(?:=|:)?\s*0\b",
    re.I,
)


RESIDENTIAL_ROOMS_KW = re.compile(
    r"\b(sala|comedor|cocina|terraza|familiar|oficina|lavanderia|patio|jardin|piscina|estudio|amueblado)\b",
    re.I,
)


AMENITY_KW = re.compile(
    r"\b(balcon|piscina|gimnasio|areas?\s+comunes?|walk\s*closet|cuarto\s+de\s+empleada)\b",
    re.I,
)

CONSTRUCTION_KW = re.compile(
    r"\b(construccion|construida|construido|area\s+construida|edificado|edificada)\b",
    re.I,
)
PRICE_PER_M2_KW = re.compile(
    r"\$\s*\d+(?:[.,]\d+)?\s*(?:x|por)\s*m(?:2|²)",
    re.I
)
# inside classify_structure(), after text normalization


# LAND

LAND_KW = re.compile(r"\b(terreno|lote|solar|parcela|finca|lotes|manzanas|topografía)\b", re.I)
AREA_KW = re.compile(r"\b(m2|mts2|mts|metros|m²|vrs2|vrs²|varas)\b", re.I)
LAND_VARAS_UNIT = re.compile(
    r"\b("
    r"v(?:rs)?\s*[²2]|"                 # v2, v², vrs2, vrs²
    r"vara(?:s)?\s*(?:cuadrada(?:s)?|[²2])"
    r")\b",
    re.I,
)
UNIT_PRICE_POR_VARAS = re.compile(
    r"\b\d+(?:[.,]\d+)?\s*(?:por|\/)\s*"
    r"(?:v(?:rs)?\s*[²2]|vara(?:s)?\s*(?:cuadrada(?:s)?|[²2]))\b",
    re.I,
)




#COMERCIAL

COMM_UNIT_KW = re.compile(
    r"\b("
    r"local(?:es)?(?:\s+comercial(?:es)?)?|"
    r"sal[oó]n(?:es)?|"
    r"oficina(?:s)?(?:\s+m[eé]dica(?:s)?)?|"
    r"colegio(?:s)?|"
    r"hotel(?:es)?|"
    r"cl[ií]nica(?:s)?|"
    r"galer[ií]a(?:s)?|"
    r"nave(?:s)?\s+industrial(?:es)?|"
    r"plaza(?:s)?\s+comercial(?:es)?|"
    r"kiosk[oó]s?|kiosc[oó]s?"
    r")\b",
    re.I,
)

DIM_X_MTS = re.compile(
    r"\b\d{1,3}\s*[x×]\s*\d{1,3}\s*m(?:t|ts|trs)?\b",
    re.I,
)

UNIT_PRICE_X = re.compile(
    r"\b(?:u\$|usd|\$)\s*\d+(?:[.,]\d+)?"
    r"(?:\s*\+\s*[a-z]{1,10})?"      # allow "+ IS", "+ imp", "+ mtto"
    r"\s*[x×]\s*"
    r"(?:m|mt|mts|metros|m\s*2|mt\s*2|m2|mt2|m²|mts?\s*2|metros?\s*2)\.?\b",
    re.I,
)







PLANTEL_KW = re.compile(r"\bplantel\b", re.I)

BODEGA_KW = re.compile(
    r"(?<!\w)(ofi[-\s]?bodega(?:s)?|bodega(?:s)?)(?!\w)",
    re.I
)



CORPORATE_KW = re.compile(
    r"""
    \b(
        corporativo(?:s)? |
        edificio(?:s)?\s+corporativo(?:s)? |
        edificio(?:s)?\s+comercial(?:es)? |
        por\s+metro\s+cuadrado
    )\b
    """,
    re.IGNORECASE | re.VERBOSE
)


COMM_USE_ADJ_KW = re.compile(
    r"\b(comercial|coworking|co-working)\b",
    re.I,
)


COMM_USE_KW = re.compile(
    r"\b("
    r"(ideal|excelente|apto)\s+para\s+"
    r"(oficina|oficinas|clinica(?:s)?|"
    r"negocio(?:s)?|comercio|comercial|corporativo)"
    r")\b",
    re.I,
)


COMM_AMENITY_KW = re.compile(
    r"\b("
    # Vertical / access
    r"ascensor(?:es)?|elevador(?:es)?|"
    r"tarjeta\s+electronica|control\s+de\s+acceso|"
    r"recepcion|lobby|"
    
    # Security / operations
    r"seguridad|vigilancia|cctv|camara(?:s)?|"
    
    # Office infrastructure
    r"aire\s+acondicionado(?:\s+central)?|"
    r"conexion\s+de\s+aire\s+acondicionado|"
    r"fibra\s+optica|red\s+de\s+datos|"
    r"planta\s+electrica|generador|"
    
    # Parking (commercial context)
    r"parqueo(?:s)?\s+(?:asignado(?:s)?|techado(?:s)?|privado(?:s)?)|"
    r"estacionamiento(?:s)?"
    r")\b",
    re.I,
)


PARTIAL_KW = re.compile(
    r"\b(obra\s+gris|media\s+construccion|sin\s+terminar)\b",
    re.I,
)



# -----------------------
# Core classifier (PURE)
# -----------------------

def classify_structure(row):
    original = str(row.get("property_type", "")).strip().capitalize()

    # Dorms is inherited only
    if original.lower() == "dorms":
        return "Dorms", "KEEP:ORIGINAL_DORMS", {}

    text_raw = " ".join(
        str(row.get(c, "")) for c in ["title", "notes", "description"]
    )
    text = normalize_text(text_raw)

    # Explicit non-residential layout
 

    if PARTIAL_KW.search(text):
        return "Partial_Construction", "KEEP:PARTIAL_CONSTRUCTION", {}

    scores = {"House": 0, "Apartment": 0, "Commercial": 0, "Land": 0}

    # Weak prior
    if original in scores:
        scores[original] += 3
  
    if PRICE_PER_M2_KW.search(text):
        scores["House"] -= 5
        scores["Apartment"] -= 5
        scores["Commercial"] += 3
        scores["Land"] += 2

    if PLANTEL_KW.search(text):
        scores["House"] = 0
        scores["Apartment"] = 0

    # Apartment
    if APT_KW.search(text): scores["Apartment"] += 8
    if BEDROOM_KW.search(text): scores["Apartment"] += 2
    if AMENITY_KW.search(text): scores["Apartment"] += 3
    if AREA_KW.search(text): scores["Apartment"] += 3

    #Penalty Apartment
    if LAND_KW.search(text): scores["Apartment"] -= 5
    if DIM_X_MTS.search(text): scores["Apartment"] -= 5

    # House
    if HOUSE_KW.search(text): scores["House"] += 8
    if BEDROOM_KW.search(text): scores["House"] += 5
    if RESIDENTIAL_ROOMS_KW.search(text): scores["House"] += 2
    if AMENITY_KW.search(text): scores["House"] += 1
    if AREA_KW.search(text) and HOUSE_KW.search(text): scores["House"] += 5
   
    #PENALTY HOUSE
    if HOUSE_KW.search(text) and COMM_USE_ADJ_KW.search(text):
        scores["House"] -= 8
    if ZERO_BEDROOMS_KW.search(text): scores["House"] -= 5
    if BODEGA_KW.search(text): scores["House"] -= 5
    if UNIT_PRICE_X.search(text): scores["House"] -= 5
    if DIM_X_MTS.search(text): scores["House"] -= 5
    if UNIT_PRICE_POR_VARAS.search(text): scores["House"] -= 5

    # Commercial
    if COMM_USE_KW.search(text): scores["Commercial"] += 5
    if COMM_UNIT_KW.search(text): scores["Commercial"] += 8
    if CORPORATE_KW.search(text): scores["Commercial"] += 2
    if COMM_AMENITY_KW.search(text): scores["Commercial"] += 2
    if AMENITY_KW.search(text): scores["Commercial"] -= 3
    if BEDROOM_KW.search(text): scores["Commercial"] -= 3
    if BODEGA_KW.search(text): scores["Commercial"] += 5
    if DIM_X_MTS.search(text): scores["Commercial"] += 5
    if UNIT_PRICE_X.search(text): scores["Commercial"] += 5

    if re.search(r"\bbodega\b", text, re.I):
        scores["Commercial"] += 5
    if PLANTEL_KW.search(text):
        scores["Commercial"] += 8

    # Commercial use / adaptive reuse
    if COMM_USE_ADJ_KW.search(text):    
        scores["Commercial"] += 3
        if ZERO_BEDROOMS_KW.search(text): scores["Commercial"] += 8

    # Land
    if CONSTRUCTION_KW.search(text): scores["Land"] -= 2
    if LAND_KW.search(text): scores["Land"] += 5
    if AREA_KW.search(text) and not HOUSE_KW.search(text): scores["Land"] += 3
    if LAND_VARAS_UNIT.search(text) and not HOUSE_KW.search(text): scores["Land"] += 5
    if UNIT_PRICE_POR_VARAS.search(text): scores["Land"] += 5
    max_score = max(scores.values())
    if max_score == 0:
        return original, "KEEP:NO_CUES", scores

    winner = max(scores, key=scores.get)
    # --- Commercial override: explicit contradiction ---



    return winner, f"POINTS:{winner}({scores[winner]})", scores

# -----------------------
# CSV pipeline
# -----------------------

def process_csv(input_csv, output_csv, scores_output=None):
    df = pd.read_csv(input_csv, encoding="utf-8-sig")
    debug_rows = []

    def _apply(row):
        final_type, reason, scores = classify_structure(row)

        if scores_output:
            debug_rows.append({
                "Listing_uid": row.get("Listing_uid"),
                "original_type": row.get("property_type"),
                "winner": final_type,
                "score_house": scores.get("House", 0),
                "score_apartment": scores.get("Apartment", 0),
                "score_commercial": scores.get("Commercial", 0),
                "score_land": scores.get("Land", 0),
                "text_sample": normalize_text(
                    " ".join(str(row.get(c, "")) for c in ["title","notes","description"])
                )[:100],
            })

        return final_type, reason

    out = df.apply(_apply, axis=1, result_type="expand")
    out.columns = ["property_type_l1", "property_type_reason"]

    df["property_type_original"] = df["property_type"]
    df["property_type_new"] = out["property_type_l1"]
    df["property_type_reason"] = out["property_type_reason"]
    df["property_type_changed"] = (
        df["property_type_original"].str.lower()
        != df["property_type_new"].str.lower()
    ).map(lambda x: "TRUE" if x else "FALSE")

    df.to_csv(output_csv, index=False, encoding="utf-8-sig")

    if scores_output:
        pd.DataFrame(debug_rows).to_csv(scores_output, index=False, encoding="utf-8-sig")

# -----------------------
# CLI
# -----------------------

def main():
    ap = argparse.ArgumentParser("ptype_l1_clean v8")
    ap.add_argument("--input", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--scores-output", default=None)
    args = ap.parse_args()

    process_csv(args.input, args.output, args.scores_output)
    print("[OK] v8 completed")

if __name__ == "__main__":
    main()
