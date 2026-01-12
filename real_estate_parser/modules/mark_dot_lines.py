"""
mark_dot_lines.py
-------------------
Replaces the *first dot (.) between positions 5–30* with a colon (:)
and prefixes modified lines with '* '.

Rules:
1️⃣ Replace the first '.' between positions 5–30 → ':'
2️⃣ Skip the line if a currency (US$, USD, Lps, L, or $) appears *before* that dot.
3️⃣ Preserve line breaks exactly — no merging, no extra newlines.

🧩 Usage (CLI):
    python mark_dot_lines.py input.txt output.txt

🧠 Usage (API):
    from mark_dot_lines import mark_lines_with_dot
    lines = mark_lines_with_dot("input.txt")
"""

import re
import sys
from pathlib import Path
from typing import List, Union, Optional

# Currency pattern — skip line if found before the dot

# Currency pattern — now supports both '.' and ':' after currency code
import re

# Match real currency patterns (US$, USD, Lps., L., $) followed by a number
CURRENCY_RE = re.compile(r"(?i)\b(?:US\$|USD|LPS[:.]?|L[:.]?|\$)\s*[\d.,]+")



# def process_line(line: str, start_pos: int = 5, end_pos: int = 30, debug=False) -> str:
#     """Replace first '.' between start_pos–end_pos with ':' and prefix '* '.
#        Skip the line if the dot is part of a currency expression.
#        If the line already starts with '* ', don't add another prefix.
#     """
#     has_nl = line.endswith("\n")
#     content = line[:-1] if has_nl else line

#     # find the first dot within window
#     idx = content.find(".", start_pos, end_pos + 1)
#     if idx == -1:
#         return line  # no candidate dot → unchanged

#     # If this dot is part of a currency token → stop here, skip line
#     if CURRENCY_RE.search(content[idx - 6:idx + 8]):  # small window around the dot
#         if debug:
#             print("STOP after currency:", content)
#         return line

#     # If any currency appears before this dot → skip as well
#     if CURRENCY_RE.search(content[:idx + 1]):
#         if debug:
#             print("SKIP currency before dot:", content)
#         return line

#     # Only add '* ' if it’s not already there
#     prefix = "" if content.lstrip().startswith("* ") else "* "
#     modified = prefix + content[:idx] + ":" + content[idx + 1:]
    
#     if debug:
#         print("CHANGED:", content, "→", modified)

#     return modified + ("\n" if has_nl else "")

def process_line(line: str, start_pos: int = 5, end_pos: int = 30, debug=False) -> str:
    """Replace first '.' between start_pos–end_pos with ':' and prefix '* '.
       Skip the line if the dot is part of a currency expression.
       If the line already starts with '* ', don't add another prefix.
    """
    has_nl = line.endswith("\n")
    content = line[:-1] if has_nl else line

    # Find the first dot within window
    idx = content.find(".", start_pos, end_pos + 1)
    if idx == -1:
        return line  # no candidate dot → unchanged

    # Currency checks
    if CURRENCY_RE.search(content[max(0, idx - 6):idx + 8]):
        if debug:
            print("STOP after currency:", content)
        return line

    if CURRENCY_RE.search(content[:idx + 1]):
        if debug:
            print("SKIP currency before dot:", content)
        return line

    # Replace the first dot with a colon
    replaced = content[:idx] + ":" + content[idx + 1:]

    # Add prefix only if the line does NOT already start with '* '
    stripped = replaced.lstrip()
    if stripped.startswith("* "):
        modified = replaced  # no extra prefix
    else:
        # Preserve leading spaces if they exist
        leading_spaces = replaced[:len(replaced) - len(stripped)]
        modified = f"{leading_spaces}* {stripped}"

    if debug:
        print("CHANGED:", content, "→", modified)

    return modified + ("\n" if has_nl else "")




def mark_lines_with_dot(
    source: Union[str, Path, List[str]],
    output_path: Optional[Union[str, Path]] = None,
    start_pos: int = 5,
    end_pos: int = 30,
) -> List[str]:
    """Main processor — simple, safe, clean."""
    processed: List[str] = []

    # Read lines from file or list
    if isinstance(source, (str, Path)):
        with Path(source).open("r", encoding="utf-8-sig") as fin:
            for line in fin:
                processed.append(process_line(line, start_pos, end_pos))
    elif isinstance(source, list):
        for line in source:
            processed.append(process_line(line, start_pos, end_pos))
    else:
        raise TypeError("source must be a file path or a list of strings")

    # Write results
    if output_path:
        with Path(output_path).open("w", encoding="utf-8-sig") as fout:
            fout.writelines(processed)

    return processed


def main():
    if len(sys.argv) != 3:
        print("Usage: python mark_dot_lines.py input.txt output.txt")
        sys.exit(1)

    input_file, output_file = sys.argv[1], sys.argv[2]
    result = mark_lines_with_dot(input_file, output_file)
    print(f"✅ Done. Processed {len(result)} lines → {output_file}")


if __name__ == "__main__":
    main()
