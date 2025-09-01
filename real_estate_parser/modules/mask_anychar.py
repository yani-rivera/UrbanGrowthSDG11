
# mask_anychar.py
import re
from typing import Iterable, Union

def normalize_listing_leader(line: str, cfg: dict) -> str:
    """
    Normalize an agency's leading listing marker(s) into the canonical listing_marker.
    
    Config options:
      - cfg["listing_marker"]: canonical marker (e.g., "*")
      - cfg["listing_marker_tochange"]: str or list of markers to normalize (e.g., "-" or ["-", "•"])
    
    Behavior:
      - Only changes markers if they occur at the very beginning of the line (ignoring spaces).
      - Leaves internal uses of the character untouched (e.g., "Casa 2-3 hab" or "Centro-El Jazmin").
      - If listing_marker_tochange is missing, empty, or equal to listing_marker → no-op.
    
    Examples:
      " - Casa amplia"    -> "* Casa amplia"
      "-- Casa amplia"    -> "* Casa amplia"
      "  -  Casa amplia"  -> "* Casa amplia"
      "Casa 2-3 hab"      -> "Casa 2-3 hab"
      "(Centro-El Jazmin)"-> "(Centro-El Jazmin)"
    """
    if not line:
        return line

    marker = (cfg or {}).get("listing_marker", "*").strip()
    tochange: Union[str, Iterable[str], None] = (cfg or {}).get("listing_marker_tochange")

    # Normalize config into a list of candidates
    if not tochange:
        return line.strip()

    if isinstance(tochange, str):
        candidates = [tochange.strip()] if tochange.strip() else []
    else:
        candidates = [s.strip() for s in tochange if isinstance(s, str) and s.strip()]

    # Remove duplicates / identical to canonical
    candidates = [c for c in candidates if c and c != marker]

    if not candidates:
        return line.strip()

    # Regex: match any of the unwanted markers at the line start
    parts = [f"(?:{re.escape(c)}+)" for c in candidates]
    pattern = r"^\s*(?:" + "|".join(parts) + r")\s*"

    if re.match(pattern, line):
        return re.sub(pattern, f"{marker} ", line, count=1).strip()

    return line.strip()
