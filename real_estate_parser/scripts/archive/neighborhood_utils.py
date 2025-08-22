
import re
import json

def load_neighborhoods(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def normalize_text(text):
    return re.sub(r"[^\w\s]", "", text.lower())

def preprocess_segment(text):
    stop_chars = [":", ",", "."]
    for char in stop_chars:
        if char in text:
            return text.split(char)[0]
    return text

def match_neighborhood(text, neighborhoods):
    text_segment = preprocess_segment(text.strip().split()[0])
    text_norm = normalize_text(text_segment)
    for entry in neighborhoods:
        names = [entry["Neighborhood"]] + entry.get("Aliases", [])
        for name in names:
            name_norm = normalize_text(name)
            if name_norm == text_norm:
                return entry["Neighborhood"]
    return ""
