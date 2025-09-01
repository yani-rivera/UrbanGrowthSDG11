
from modules.agency_preprocess import configure_preprocess, preprocess_listings
from modules.record_parser import parse_record
import os

def make_prefile(input_path, agency, tmp_root="output"):
    base = os.path.basename(input_path)
    pre_dir = os.path.join(tmp_root, agency, "pre", agency.lower())
    os.makedirs(pre_dir, exist_ok=True)
    pre_path = os.path.join(pre_dir, f"pre_{base}")
    # simple masquerade: turn inline/line-start 'NN.' into '*'
    with open(input_path, "r", encoding="utf-8", errors="ignore") as fi, \
         open(pre_path, "w", encoding="utf-8") as fo:
        for ln in fi:
            fo.write(re.sub(r"(?<!\\d)(\\d{1,3})\\.(?=\\s*\\S)", "* ", ln))
    return pre_path

def load_lines(path):
    with open(path, "r", encoding="utf-8", errors="ignore") as fh:
        for ln in fh:
            yield ln.rstrip("\\n")

def run_pipeline(input_path, cfg):
    agency = cfg.get("agency", "")
    # step 0: masquerade if needed
    if cfg.get("listing_marker") == "NUMBERED" and cfg.get("auto_masquerade_numdot"):
        input_path = make_prefile(input_path, agency)

    # step 1: preprocess to one-line listings
    configure_preprocess(cfg)
    marker = cfg.get("listing_marker")
    # map config token to actual splitter
    marker_map = {"NUMBERED": "#NUM", "UPPERCASE": "UPPERCASE"}
    eff_marker = marker_map.get(marker, marker)  # "*", "-", "#NUM", or "UPPERCASE"
    listings = preprocess_listings(load_lines(input_path), marker=eff_marker)

    return listings
