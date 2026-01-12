"""
mark_colon_lines.py
-------------------
Prefixes lines containing ':' in the first 60 characters with '* '.

🧩 Usage (CLI):
    python mark_colon_lines.py input.txt output.txt

🧠 Usage (API with file path):
    from mark_colon_lines import mark_lines_with_colon
    lines = mark_lines_with_colon("input.txt")

🧠 Usage (API with list of lines):
    lines = ["Location: New York", "Price 1200 USD"]
    result = mark_lines_with_colon(lines)
"""

import sys
from pathlib import Path
from typing import List, Union, Optional

def mark_lines_with_colon(
    source: Union[str, Path, List[str]],
    output_path: Optional[Union[str, Path]] = None,
    limit: int = 60
) -> List[str]:
    """
    Marks lines that contain ':' within the first `limit` characters by
    prefixing them with '* '. Accepts either a file path or a list of strings.

    Parameters:
        source (str | Path | list[str]): Input file path or list of lines
        output_path (str | Path | None): Optional output file path
        limit (int): Character limit to check for ':'

    Returns:
        list[str]: The processed lines
    """
    # Read lines from file or use provided list
    if isinstance(source, (str, Path)):
        with Path(source).open("r", encoding="utf-8") as fin:
            lines = [line.rstrip("\n") for line in fin]
    elif isinstance(source, list):
        lines = [str(line).rstrip("\n") for line in source]
    else:
        raise TypeError("source must be a file path or a list of strings")

    # Process lines
    processed = []
    for line in lines:
        if ":" in line[:limit]:
            processed.append(f"* {line}")
        else:
            processed.append(line)

    # Optionally write to file
    if output_path:
        with Path(output_path).open("w", encoding="utf-8") as fout:
            fout.write("\n".join(processed))

    return processed


def main():
    if len(sys.argv) != 3:
        print("Usage: python mark_colon_lines.py input.txt output.txt")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2]
    processed = mark_lines_with_colon(input_file, output_file)
    print(f"✅ Done. Processed {len(processed)} lines.")
    print(f"Output written to: {output_file}")


if __name__ == "__main__":
    main()
