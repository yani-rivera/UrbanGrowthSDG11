
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
        names = [entry["Neighborhood"]] + entry.get("Aliases", [])
        for name in names:
            pattern = r"\b" + re.escape(normalize_text(name)) + r"\b"
            if re.search(pattern, text_norm):
                return entry["Neighborhood"]
    return ""
