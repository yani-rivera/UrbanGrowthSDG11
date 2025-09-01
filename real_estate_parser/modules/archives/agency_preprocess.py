
# modules/agency_preprocess.py
import re


def serpecal_preprocess(t: str) -> str:
    t = t.strip()
    t = re.sub(r'^\*+\s*', '', t)               # drop bullet
    t = re.sub(r'\s+', ' ', t)
    t = t.replace('Vr²','vrs²').replace('Vr2','vrs²').replace('Vrs2','vrs²').replace('Vrs','vrs')
    t = t.replace('Mts2','m²').replace('mts2','m²').replace('mt2','m²').replace('m2','m²')
    t = re.sub(r'(Lps\.?|L\.|\$)(\d)', r'\1 \2', t)  # ensure space after currency
    return t.lower()



def extract_neighborhood_serpecal(text: str) -> str:
    """
    Looks for patterns like:
      'col. palmira: ...'
      'res. monseñor fiallos: ...'
      'anillo periferico: ...' (treat as neighborhood as well)
    """
    m = re.search(r'^(col\.|res\.|barrio|anillo periferico)\s*([^\:,]+)', text)
    if m:
        # If matched 'col.' or 'res.' the next token may already be the name,
        # for 'anillo periferico' keep as-is.
        if m.group(1) in ('col.', 'res.', 'barrio'):
            name = f"{m.group(1)} {m.group(2).strip()}"
        else:
            name = m.group(0).strip(': ').strip()
        return name.strip()
    # Fallback: take token up to first colon if present
    m2 = re.match(r'^([^:]{3,40}):', text)
    return m2.group(1).strip() if m2 else ""
