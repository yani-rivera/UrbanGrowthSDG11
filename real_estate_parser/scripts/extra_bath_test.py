
# scripts/extra_bath_test.py
# Quick, self-contained checks for bathrooms extraction (numeric, slash, y medio, half, ensuite inference)
import sys
sys.path.insert(0, "modules")  # ensure modules/ on path

from parser_utils import extract_bathrooms

GREEN = "PASS"
RED = "FAIL"

def run_case(text, cfg, expected, note):
    got = extract_bathrooms(text, cfg)
    ok = (got == expected)
    print(f"{GREEN if ok else RED}: {note} | input={text!r} -> got={got} expected={expected}")
    return ok

def main():
    # Base cfg: you can adjust to load from your JSON later
    base_cfg = {
        "allow_slash_bed_bath": True,
        "bathroom_keywords": ["baño","baños","bano","banos","bafios","ba√±o","ba√±os"],
        # your corrected key + regex flag:
        "bathroom_ensuite_markers": [
            r"cada\sun[oa].{0,40}bañ",   # regex: "cada uno/una ... bañ" within 40 chars
            "cada una con su baño",
            "cada uno con su baño",
            "cada habitacion con su baño",
            "cada habitación con su baño",
            "cada recamara con su baño",
            "cada recámara con su baño",
            "todas con baño",
            "todas con bano",
        ],
        "bathroom_ensuite_regex": True,
        "bathroom_infer_from_bedrooms": True,
    }

    passed = 0; total = 0

    # 1) Simple numeric
    total += 1; passed += run_case(
        "Casa 3 hab 2 baños, L. 1,250,000",
        base_cfg, 2.0, "numeric baños"
    )

    # 2) Slash bed/bath
    total += 1; passed += run_case(
        "Apto 3/2 en Lomas",
        base_cfg, 2.0, "slash 3/2"
    )

    # 3) Y medio (2.5)
    total += 1; passed += run_case(
        "Casa 2 baños y medio, patio amplio",
        base_cfg, 2.5, "y medio"
    )

    # 4) Half-bath only
    total += 1; passed += run_case(
        "Local con ½ baño",
        base_cfg, 0.5, "half unicode ½"
    )

    # 5) Ensuite inference == bedrooms (no numeric near baño)
    cfg5 = dict(base_cfg); cfg5["hint_bedrooms"] = 3
    total += 1; passed += run_case(
        "3 habitaciones cada una con su baño, sala y comedor",
        cfg5, 3.0, "ensuite inference = bedrooms"
    )

    # 6) Ensuite + half visitors -> bedrooms + 0.5
    cfg6 = dict(base_cfg); cfg6["hint_bedrooms"] = 3
    total += 1; passed += run_case(
        "3 habitaciones cada una con su baño, medio bañod e visitas",
        cfg6, 3.5, "ensuite + half visitors (typo tolerant)"
    )

    # 7) No baths at all
    total += 1; passed += run_case(
        "Apto estudio, cocina equipada, precio 650$",
        base_cfg, None, "no bathrooms present"
    )

    print(f"\nSummary: {passed}/{total} tests passed.")

if __name__ == "__main__":
    main()
