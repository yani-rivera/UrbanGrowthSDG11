import re
import sys

def bulletize(text_lines):
    text = ' '.join(line.strip() for line in text_lines if line.strip())

    # Normalize spacing around asterisks and punctuation
    text = re.sub(r'\s*\*\s*', ' * ', text)
    text = re.sub(r'\s{2,}', ' ', text)

    # Split on asterisk markers (each denotes a new listing)
    entries = [e.strip() for e in text.split(' * ') if e.strip()]

    # Regexes
    price_regex = re.compile(r'(\$|Lps\.?)\s?[0-9,.]+(?:\s?/\s?[Vv]2)?')
    area_regex = re.compile(r'[0-9,.]+\s*(V2|M2)', re.IGNORECASE)

    results = []
    for entry in entries:
        price_match = list(price_regex.finditer(entry))
        area_match = list(area_regex.finditer(entry))

        price = price_match[-1].group().strip() if price_match else ''
        area = area_match[-1].group().strip() if area_match else ''

        if price:
            entry = entry[:price_match[-1].start()].strip()
        if area:
            entry = entry[:area_match[-1].start()].strip()

        glued = f"* {entry}"
        if area:
            glued += f" {area}"
        if price:
            glued += f" {price}"

        results.append(glued)
    return results

if __name__ == '__main__':
    rows = sys.stdin.read().splitlines()
    for row in bulletize(rows):
        print(row)
