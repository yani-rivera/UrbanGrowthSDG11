import re, csv
from typing import List, Dict, Any, Tuple, Optional

# ---------- config (tweak per region if needed) ----------
V2_TO_M2 = 0.6989       # vara cuadrada -> m² (override per agency if needed)
MANZANA_TO_M2 = 6987.0  # manzana -> m² (override per agency if needed)

# ---------- regex ----------
HEADER_RE = re.compile(r'^\s*#\s*(.+?)\s*$', re.I)
BULLET_RE = re.compile(r'^\s*[\*\-\u2022]\s*(.+)$')
CURR_ANY  = r'(?:LPS\.?|L\.?|\$)'
AMT_ANY   = r'\d[\d\.,\s]*'
MONEY_ALL_RE = re.compile(rf'({CURR_ANY})?\s*({AMT_ANY})', re.I)
PRICE_PER_V2_RE = re.compile(rf'({CURR_ANY})\s*({AMT_ANY})\s*(?:LA\s*)?V[²2]\b', re.I)

BED_RE  = re.compile(r'(?i)\b(\d{1,2})\s*(?:HABIT|HAB|HABS|DORM)\b')
BATH_RE = re.compile(r'(?i)\b(\d{1,2}(?:\.\d)?)\s*(?:BAÑO|BAÑO|BANO|BANOS|BAÑOS)\b')
V2_RE   = re.compile(r'(?i)\b(\d+(?:[¼½¾]|/\d+)?)\s*V[²2]\b')
MANZ_RE = re.compile(r'(?i)\b(\d+(?:[¼½¾]|/\d+)?)\s*MANZANA(S)?\b')

SPACED_CAPS_SEQ = re.compile(r'(?:\b[A-ZÁÉÍÓÚÜÑ]\b[.\s]*){2,}')
CONNECTOR_START = re.compile(r'^\s*(y|e|con|incluye|cerca de|sobre|entre)\b', re.I)
TRAIL_WRAP = re.compile(r'[,\+/\-&]\s*$')

def _norm(s:str)->str:
    return re.sub(r'\s+',' ', s).strip()

def _undisperse_caps(s:str)->str:
    def compact(m):
        letters = re.findall(r'[A-ZÁÉÍÓÚÜÑ]', m.group(0))
        return ''.join(letters)
    return SPACED_CAPS_SEQ.sub(compact, s)

def _fix_number(s: str) -> float:
    s2 = re.sub(r'(?<=\d)\s+(?=[\d,\.])', '', s)  # "6, 000.00" -> "6,000.00"
    last_sep = max(s2.rfind(','), s2.rfind('.'))
    if last_sep != -1 and re.fullmatch(r'\d{2}', re.sub(r'\D','', s2[last_sep+1:])):
        int_part = re.sub(r'[^\d]', '', s2[:last_sep]) or '0'
        dec_part = re.sub(r'[^\d]', '', s2[last_sep+1:])
        return float(f"{int_part}.{dec_part}")
    return float(re.sub(r'[^\d]', '', s2) or '0')

def _money_tokens(s: str) -> List[Tuple[str,float,Tuple[int,int]]]:
    out=[]
    for m in MONEY_ALL_RE.finditer(s):
        amt_raw = m.group(2)
        if not amt_raw: continue
        cur_raw = (m.group(1) or '').upper()
        val = _fix_number(amt_raw)
        if val <= 0: continue
        cur = 'USD' if '$' in cur_raw else ('HNL' if 'L' in cur_raw else '')
        out.append((cur, val, m.span()))
    # inherit first explicit currency
    first_cur = next((c for c,_,_ in out if c), '')
    if first_cur:
        out = [(c or first_cur, v, span) for (c,v,span) in out]
    return out

def _price_per_v2(s: str) -> Optional[Tuple[str,float]]:
    m = PRICE_PER_V2_RE.search(s)
    if not m: return None
    cur = 'USD' if '$' in m.group(1) else 'HNL'
    val = _fix_number(m.group(2))
    return (cur, val)

def _fract_to_float(tok: str) -> Optional[float]:
    tok = tok.replace('¼',' 1/4').replace('½',' 1/2').replace('¾',' 3/4')
    tok = _norm(tok)
    if '/' in tok:
        a,b = tok.split('/',1)
        try: return float(a) / float(b)
        except: return None
    try: return float(tok)
    except: return None

def _areas(s: str) -> Tuple[Optional[float], Optional[float], Optional[float]]:
    v2 = None
    manz = None
    m = V2_RE.search(s)
    if m:
        v2 = _fract_to_float(m.group(1))
    m2 = MANZ_RE.search(s)
    if m2:
        manz = _fract_to_float(m2.group(1))
    area_m2 = None
    if v2 is not None:
        area_m2 = v2 * V2_TO_M2
    elif manz is not None:
        area_m2 = manz * MANZANA_TO_M2
    return (manz, v2, area_m2)

def _title_before_first_money(s: str, monies: List[Tuple[str,float,Tuple[int,int]]]) -> str:
    if not monies: return s
    start = monies[0][2][0]
    return _norm(s[:start].strip(' ,.-'))

def _neighborhood_from_title(title: str) -> str:
    tu = title.upper()
    for lead in ('CASA ', 'APTO ', 'APARTAMENTO ', 'APART ', 'LOCAL ', 'OFICINA ', 'OFICINAS '):
        if tu.startswith(lead): return title[len(lead):].strip()
    return title

def _property_type(title_up:str)->str:
    if title_up.startswith('CASA '): return 'House'
    if title_up.startswith('APTO ') or title_up.startswith('APART'): return 'Apartment'
    if 'LOCAL' in title_up or 'OFICINA' in title_up: return 'Commercial'
    return 'House' if 'CASA' in title_up.split()[:2] else ''

# ---------- bullet parser ----------
def _parse_bullet_line(raw: str, category: str) -> Dict[str,Any]:
    s = _norm(_undisperse_caps(raw))
    monies = _money_tokens(s)
    title  = _title_before_first_money(s, monies)
    ppv2   = _price_per_v2(s)
    manz, v2, area_m2 = _areas(s)
    beds = BED_RE.search(s)
    baths = BATH_RE.search(s)
    return {
        "category": category,
        "title": title,
        "raw": s,
        "prices": [{"currency": c, "amount": v} for (c,v,_) in monies],
        "price_per_v2": {"currency": ppv2[0], "amount": ppv2[1]} if ppv2 else None,
        "area_manzanas": manz,
        "area_v2": v2,
        "area_m2": area_m2,
        "bedrooms": beds.group(1) if beds else "",
        "bathrooms": baths.group(1) if baths else "",
    }

def parse_bullets_or_headers(lines: List[str]) -> List[Dict[str,Any]]:
    out=[]; category=""
    for raw in lines:
        if not raw.strip(): continue
        h = HEADER_RE.match(raw)
        if h:
            category = _norm(h.group(1).upper())
            continue
        b = BULLET_RE.match(raw)
        if b:
            out.append(_parse_bullet_line(b.group(1), category))
        else:
            # continuation line for last bullet
            if out:
                s = _norm(_undisperse_caps(raw))
                out[-1]["raw"] = _norm(out[-1]["raw"] + " " + s)
    return out

# ---------- no-bullet fallback (cheap heuristic) ----------
def parse_no_bullets(lines: List[str]) -> List[Dict[str,Any]]:
    out=[]; category=""; cur=[]
    def flush():
        nonlocal cur
        if not cur: return
        s = _norm(_undisperse_caps(' '.join(cur)))
        monies = _money_tokens(s)
        title  = _title_before_first_money(s, monies)
        ppv2   = _price_per_v2(s)
        manz, v2, area_m2 = _areas(s)
        beds = BED_RE.search(s); baths = BATH_RE.search(s)
        out.append({
            "category": category,
            "title": title, "raw": s,
            "prices": [{"currency": c, "amount": v} for (c,v,_) in monies],
            "price_per_v2": {"currency": ppv2[0], "amount": ppv2[1]} if ppv2 else None,
            "area_manzanas": manz, "area_v2": v2, "area_m2": area_m2,
            "bedrooms": beds.group(1) if beds else "",
            "bathrooms": baths.group(1) if baths else "",
        })
        cur=[]
    prev=""
    for raw in lines:
        if not raw.strip(): continue
        h = HEADER_RE.match(raw)
        if h:
            flush(); category = _norm(h.group(1).upper()); prev=raw; continue
        line = raw.rstrip("\r\n")
        # start a new block if we see currency and some letters before it
        m = MONEY_ALL_RE.search(line)
        start = False
        if m:
            if re.search(r'[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]', line[:m.start()] or ''):
                start = True
        if start: flush()
        cur.append(line)
        prev=line
    flush()
    return out

# ---------- choose strategy automatically ----------
def parse_any(lines: List[str]) -> List[Dict[str,Any]]:
    if any(BULLET_RE.match(x or "") for x in lines):
        return parse_bullets_or_headers(lines)
    return parse_no_bullets(lines)

# ---------- map to your schema ----------
COLUMNS = [
  "ListingID","title","neighborhood","bedrooms","bathrooms","AT","AT_unit",
  "area","area_unit","area_m2","price","currency","transaction","property_type",
  "agency","date","notes","source_type","ingestion_id","pipeline_version"
]

def to_schema(rows: List[Dict[str,Any]], *, agency:str, date_str:str,
              source_type:str, ingestion_id:str, pipeline_version:str) -> List[Dict[str,Any]]:
    mapped=[]
    # infer transaction from category header
    def trans_from_cat(cat:str)->str:
        u = (cat or '').upper()
        return "Rent" if "ALQUILER" in u else "Sale"
    for i, r in enumerate(rows, start=1):
        title = r["title"]
        prices = r.get("prices", [])
        price = prices[0]["amount"] if prices else ""
        currency = prices[0]["currency"] if prices else ""
        title_up = title.upper()
        ptype = _property_type(title_up)
        neighborhood = _neighborhood_from_title(title)
        # AT from price-per-V2 if present
        at = ""; at_unit = ""
        if r.get("price_per_v2"):
            at = r["price_per_v2"]["amount"]
            at_unit = "V2"
        mapped.append({
            "ListingID": i,
            "title": title,
            "neighborhood": neighborhood,
            "bedrooms": r.get("bedrooms",""),
            "bathrooms": r.get("bathrooms",""),
            "AT": at,
            "AT_unit": at_unit,
            "area": r.get("area_v2","") or r.get("area_manzanas",""),
            "area_unit": "V2" if r.get("area_v2") else ("MANZANA" if r.get("area_manzanas") else ""),
            "area_m2": f"{r.get('area_m2'):.2f}" if r.get("area_m2") else "",
            "price": int(price) if isinstance(price, float) and price.is_integer() else price,
            "currency": currency,
            "transaction": trans_from_cat(r.get("category","")),
            "property_type": ptype,
            "agency": agency,
            "date": date_str,
            "notes": r.get("raw",""),
            "source_type": source_type,
            "ingestion_id": ingestion_id,
            "pipeline_version": pipeline_version,
        })
    return mapped

def write_csv(path: str, rows: List[Dict[str,Any]]) -> None:
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS)
        w.writeheader(); w.writerows(rows)

# convenience: one-call client
def parse_any_and_map(lines: List[str], *, agency:str, date_str:str,
                      source_type:str, ingestion_id:str, pipeline_version:str) -> List[Dict[str,Any]]:
    return to_schema(parse_any(lines), agency=agency, date_str=date_str,
                     source_type=source_type, ingestion_id=ingestion_id,
                     pipeline_version=pipeline_version)
