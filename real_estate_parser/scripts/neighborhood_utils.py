
import re
import json

def load_neighborhoods(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def normalize_text(text):
    return re.sub(r"[^\w\s]", "", text.lower())

def apply_strategy(text, strategy):
    if strategy == "first_comma":
        return text.split(",")[0].strip()
    elif strategy == "before_colon":
        return text.split(":")[0].strip()
    elif strategy == "first_line":
        return text.splitlines()[0].strip()
    return ""

def match_neighborhood(text, neighborhoods, strategy=None, debug=False):
    text_norm = normalize_text(text)

    # 1. Strategy-based override (highest priority)
    if strategy:
        fallback = apply_strategy(text, strategy)
        if fallback:
            if debug:
                print(f"[Strategy Match: {strategy}] → {fallback}")
            return fallback.upper()

    # 2. Exact match or alias match
    for entry in neighborhoods:
        name = entry["Neighborhood"] if isinstance(entry, dict) else entry
        aliases = entry.get("Aliases", []) if isinstance(entry, dict) else []
        all_names = [name] + aliases
        for n in all_names:
            if normalize_text(n) in text_norm:
                if debug:
                    print(f"[Alias Match] Found: {n}")
                return name.upper()

    # 3. Regex-based fallback (e.g., Col., Loma)
    fallback_patterns = [
        r'Col\.?\s?[A-Za-zÁÉÍÓÚÑñ ]+',
        r'Loma\s+[A-Za-z]+',
        r'Altos\s+de\s+[A-Za-z]+',
        r'San\s+[A-Za-z]+',
        r'Res\.?\s?[A-Za-z ]+'
    ]

    for pattern in fallback_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            result = match.group().strip().upper()
            if debug:
                print(f"[Regex Match] → {result}")
            return result

    if debug:
        print("[No Match] Unable to detect neighborhood.")
    return ""
