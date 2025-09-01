
# modules/pars_tls_compat.py
# Backward-compatible façade so old record_parser calls still work.

from typing import Tuple, Union, Dict
from .parser_utils import (
    normalize_ocr_text,
    extract_price as _extract_price,
    extract_bedrooms as _extract_bedrooms,
    extract_bathrooms as _extract_bathrooms,
    extract_area as _extract_area,
)
from .neighborhood_utils import extract_neighborhood as _extract_neighborhood

Number = Union[int, float]

def normalize(text: object) -> str:
    return normalize_ocr_text(text)

def price(text: str, config: dict) -> Tuple[Union[Number, str], str]:
    # matches old (amount, currency)
    amt, cur = _extract_price(text, config)
    return amt, cur

def bedrooms(text: str) -> Union[int, str]:
    return _extract_bedrooms(text)

def bathrooms(text: str) -> Union[float, int, str]:
    return _extract_bathrooms(text)

def area(text: str, config: dict) -> Dict[str, Union[Number, str]]:
    # returns dict equivalent to old area payload
    # new utils already give: built_value/unit & land_value/unit
    return _extract_area(text, config)

def neighborhood(text: str, config: dict, agency: str = None) -> str:
    return _extract_neighborhood(text, config, agency=agency)

def property_type(text: str, config: dict) -> str:
    # if you had pars_tls.property_type, we map to the new keyword fallback
    from .parser_utils import extract_property_type as _extract_property_type
    return _extract_property_type(text, config)
