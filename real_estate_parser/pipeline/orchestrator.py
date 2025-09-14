
from __future__ import annotations
import re
import csv
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional
import yaml

@dataclass
class ParsedRow:
    agency: str
    neighborhood: str
    price_total: Optional[str]
    price_per_unit: Optional[str]
    listing_count: Optional[int]
    raw_row: str
    notes: Optional[str] = None

class BaseAgencyParser:
    def __init__(self, agency: str, cfg: dict):
        self.agency = agency
        self.cfg = cfg

    # All preprocessing hooks live here
    def preprocess(self, text: str) -> str:
        t = text
        # Example: Fenix needs star bullets
        if self.agency.lower() == "fenix":
            lines = [l.strip() for l in t.splitlines() if l.strip()]
            t = "\n".join(["* " + l if not l.startswith("*") else l for l in lines])
        return t

    def parse(self, text: str) -> List[ParsedRow]:
        if self.cfg.get("mode") == "manual":
            return []
        t = self.preprocess(text)
        mode = self.cfg.get("listings_delimiter")

        def split_listings(body: str) -> List[str]:
            if mode == "star":
                return [x.strip() for x in body.split("*") if x.strip()]
            if mode == "dash":
                return [x.strip() for x in body.split("-") if x.strip()]
            if mode == "numbered":
                parts = re.split(r"(?=\b\d+[\.)]\s*)", body)
                return [p.strip() for p in parts if p.strip()]
            if mode == "start_with_uppercase":
                parts = re.split(r"(?=\b[A-ZÁÉÍÓÚÑ][\wÁÉÍÓÚÑ]+)", body)
                return [p.strip() for p in parts if p.strip()]
            return [body.strip()] if body.strip() else []

        def extract_neighborhood(chunk: str) -> str:
            strat = self.cfg.get("neighborhood")
            rule = self.cfg.get("neighborhood_rule")
            if not strat and rule:
                strat = rule.get("strategy", "before_comma_or_dot")
            if strat == "before_first_comma":
                return chunk.split(",")[0].strip()
            if strat == "before_colon":
                return chunk.split(":")[0].strip()
            if strat == "before_comma_or_dot":
                m = re.search(r"[,\.]", chunk)
                return chunk[:m.start()].strip() if m else chunk.strip()
            if strat == "words_before_dot":
                return chunk.split(".")[0].strip()
            return chunk.strip()

        def extract_prices(chunk: str):
            money = re.findall(r"\$\s?([\d\.,]+)", chunk)
            tot = money[0] if money else None
            pu = money[1] if len(money) > 1 else None
            return tot, pu

        def guess_count(chunk: str):
            m = re.search(r"(\d+)\s*(?:u|unidades|units|deptos|aptos)", chunk, flags=re.I)
            return int(m.group(1)) if m else None

        rows: List[ParsedRow] = []
        for part in split_listings(t):
            n = extract_neighborhood(part)
            pt, ppu = extract_prices(part)
            lc = guess_count(part)
            rows.append(ParsedRow(self.agency, n, pt, ppu, lc, part, self.cfg.get("obs")))
        return rows

REGISTRY = {}

def get_parser(agency: str, cfg: dict) -> BaseAgencyParser:
    cls = REGISTRY.get(agency, BaseAgencyParser)
    return cls(agency, cfg)


def run_orchestrator(raw_dir: str, cfg_path: str, out_csv: str) -> None:
    config = yaml.safe_load(Path(cfg_path).read_text(encoding="utf-8"))
    out: List[ParsedRow] = []
    for agency, a_cfg in config.get("agencies", {}).items():
        p = Path(raw_dir) / f"{agency}.txt"
        if not p.exists():
            continue
        text = p.read_text(encoding="utf-8", errors="ignore")
        parser = get_parser(agency, a_cfg)
        out.extend(parser.parse(text))

    Path(out_csv).parent.mkdir(parents=True, exist_ok=True)
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["agency","neighborhood","price_total","price_per_unit","listing_count","raw_row","notes"])
        for r in out:
            w.writerow([r.agency, r.neighborhood, r.price_total, r.price_per_unit, r.listing_count, r.raw_row, r.notes])

if __name__ == "__main__":
    run_orchestrator("raw_agencies", "agencies.yml", "out/cleaned_listings.csv")