#!/usr/bin/env python3
import argparse

def keep_bullet(content: str, n_words: int) -> bool:
    """
    Return True if the first n_words in content are all uppercase.
    """
    words = content.strip().split()

    if len(words) < n_words:
        return False

    for w in words[:n_words]:
        if not w.isupper():
            return False

    return True


def process_file(input_path: str, output_path: str, n_words: int) -> None:
    with open(input_path, "r", encoding="utf-8-sig") as fin, \
         open(output_path, "w", encoding="utf-8-sig") as fout:

        for line in fin:
            line = line.rstrip("\n")

            if not line.startswith("* "):
                fout.write(line + "\n")
                continue

            content = line[2:]  # remove "* "

            if not content.strip():
                fout.write(line + "\n")
                continue

            if keep_bullet(content, n_words):
                fout.write("* " + content + "\n")
            else:
                fout.write(content + "\n")


def main():
    parser = argparse.ArgumentParser(
        description="Keep '*' only if the first N words are ALL UPPERCASE."
    )
    parser.add_argument("-i", "--input", required=True, help="Input UTF-8 txt file")
    parser.add_argument("-o", "--output", required=True, help="Output UTF-8 txt file")
    parser.add_argument(
        "-n", "--n-words",
        type=int,
        default=1,
        help="Number of leading words that must be ALL UPPERCASE (default: 1)"
    )

    args = parser.parse_args()

    if args.n_words < 1:
        raise ValueError("n-words must be >= 1")

    process_file(args.input, args.output, args.n_words)


if __name__ == "__main__":
    main()
