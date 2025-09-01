## Versio 1.0

from typing import List

__all__ = ["read_lines_safely"]

def read_lines_safely(path: str) -> List[str]:
    for enc in ("utf-8", "utf-8-sig", "cp1252", "latin-1"):
        try:
            with open(path, "r", encoding=enc) as f:
                return [ln.rstrip("\n") for ln in f]
        except UnicodeDecodeError:
            continue
    with open(path, "rb") as f:
        return f.read().decode("utf-8", "ignore").splitlines()

