"""
insert_colon_before_currency.py
-------------------------------
Inserts ':' before the first occurrence of a currency symbol or alias
defined in the agency config (currency_aliases).

CLI usage:
    python insert_colon_before_currency.py input.txt output.txt config.json

API usage:
    from insert_colon_before_currency import insert_colon_before_currency
    lines = insert_colon_before_currency(["BLVD. SUYAPA. $300.0 x v2"], config_path="config.json")
"""

import sys
import re
import json
import yaml
from pathlib import Path
from typing import List, Union, Optional


def load_config(config_path: Union[str, Path]) -> dict:
    """Loads JSON or YAML config and returns a dict."""
    path = Path(config_path)
    with path.open("r", encoding="utf-8") as f:
        if path.suffix.lower() in [".yaml", ".yml"]:
            return yaml.safe_load(f)
        return json.load(f)


def insert_colon_before_currency(
    source: Union[str, Path, List[str]],
    config_path: Union[str, Path],
    output_path: Optional[Union[str, Path]] = None,
) -> List[str]:
    """
    Inserts ':' before the FIRST occurrence of any currency alias from config.
    Stops after the first match and moves to the next line.

    Parameters:
        source (str | Path | list[str]): Input file path or list of lines
        config_path (str | Path): Path to config JSON/YAML
        output_path (str | Path | None): Optional output file path

    Returns:
        list[str]: Processed lines
    """
    # --- Load config and currency list ---
    config = load_config(config_path)
    currency_aliases = config.get("currency_aliases", {})
    currencies = list(currency_aliases.keys())

    if not currencies:
        raise ValueError(f"No 'currency_aliases' found in config: {config_path}")

    # --- Build regex for first match ---
    currency_pattern = re.compile(r"(" + "|".join(map(re.escape, currencies)) + r")")

    # --- Load input lines ---
    if isinstance(source, (str, Path)):
        with Path(source).open("r", encoding="utf-8") as fin:
            lines = [line.rstrip("\n") for line in fin]
    elif isinstance(source, list):
        lines = [str(line).rstrip("\n") for line in source]
    else:
        raise TypeError("source must be a file path or a list of strings")

    # --- Process each line ---
    processed = []
    for line in lines:
        # Skip if colon already appears before any currency
        match = currency_pattern.search(line)
        if match:
            idx = match.start()
            # Only add colon if not already present before the currency
            if ":" not in line[:idx]:
                new_line = line[:idx].rstrip() + ": " + line[idx:]
            else:
                new_line = line
            processed.append(new_line)
        else:
            processed.append(line)

    # --- Optional file output ---
    if output_path:
        with Path(output_path).open("w", encoding="utf-8") as fout:
            fout.write("\n".join(processed))

    return processed


def main():
    if len(sys.argv) < 4:
        print("Usage: python insert_colon_before_currency.py input.txt output.txt config.json")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2]
    config_file = sys.argv[3]

    insert_colon_before_currency(input_file, config_file, output_file)
    print(f"✅ Done. Output written to: {output_file}")


if __name__ == "__main__":
    main()
