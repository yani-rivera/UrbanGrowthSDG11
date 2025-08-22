
import re
import json

def load_neighborhoods(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def normalize_text(text):
    return re.sub(r"[^\w\s]", "", text.lower())

def match_neighborhood(text, neighborhoods):
    text_norm = normalize_text(text)
    for entry in neighborhoods:
        name = entry["Neighborhood"] if isinstance(entry, dict) else entry
        aliases = entry.get("Aliases", []) if isinstance(entry, dict) else []
        all_names = [name] + aliases
        for n in all_names:
            if normalize_text(n) in text_norm:
                return name.upper()

    # Fallback pattern matching for common neighborhood markers
    fallback_patterns = [
        r'Col\.\s?[A-Za-zÁÉÍÓÚÑñ ]+',
        r'Loma\s+[A-Za-z]+',
        r'Altos\s+de\s+[A-Za-z]+',
        r'San\s+[A-Za-z]+',
        r'Res\.\s?[A-Za-z ]+'
    ]
    for pattern in fallback_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group().strip().upper()

    return ""
