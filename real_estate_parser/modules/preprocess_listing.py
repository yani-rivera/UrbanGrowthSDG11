def preprocess_listings(lines: list[str], marker: str = "-") -> list[str]:
    """
    Merge multiline listings into a single row based on a start marker.

    Args:
        lines (list[str]): Raw lines from the input text.
        marker (str): The symbol/string that marks the beginning of a new listing (e.g., "-").

    Returns:
        list[str]: List of full listings, each as a single space-joined string.
    """
    merged = []
    current_listing = []

    for line in lines:
        clean_line = line.strip()
        if not clean_line:
            continue

        if clean_line.startswith(marker) and current_listing:
            merged.append(" ".join(current_listing).strip())
            current_listing = [clean_line]
        else:
            current_listing.append(clean_line)

    if current_listing:
        merged.append(" ".join(current_listing).strip())

    return merged
