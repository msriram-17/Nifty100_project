"""Normalisation utilities for the Nifty100 ETL pipeline.

normalize_year(): standardises every observed year-label format in the
    source files (e.g. 'Mar-23', 'Dec 2012', 'FY24', '2023') to 'YYYY-MM'.
normalize_ticker(): standardises company_id values to a clean uppercase
    NSE ticker with no leading/trailing whitespace.
"""

import re

MONTH_MAP = {
    "jan": "01", "feb": "02", "mar": "03", "apr": "04",
    "may": "05", "jun": "06", "jul": "07", "aug": "08",
    "sep": "09", "oct": "10", "nov": "11", "dec": "12",
}

PARSE_ERROR = "PARSE_ERROR"


def normalize_year(raw_year) -> str:
    """Standardise a raw year label to 'YYYY-MM' format.

    Handles the documented format variants:
        'Mar-23'      -> '2023-03'
        'Mar 23'      -> '2023-03'
        'Mar 2014'    -> '2014-03'
        'March-2023'  -> '2023-03'
        '2023'        -> '2023-03'   (bare year -> assume March FY close)
        'FY23'        -> '2023-03'
        'Dec-22'      -> '2022-12'
        'Jun-23'      -> '2023-06'
        '2023-03'     -> '2023-03'   (already normalised -> pass through)
        unparseable   -> 'PARSE_ERROR'
    """
    if raw_year is None:
        return PARSE_ERROR

    s = str(raw_year).strip()
    if not s:
        return PARSE_ERROR

    # Already normalised: YYYY-MM
    m = re.match(r"^(\d{4})-(\d{2})$", s)
    if m:
        return s

    # FY prefix: FY23, FY2023
    m = re.match(r"^FY[\s\-]?(\d{2,4})$", s, flags=re.IGNORECASE)
    if m:
        yr = m.group(1)
        yr = _expand_2digit_year(yr)
        return f"{yr}-03"

    # Bare 4-digit year -> assume March FY close
    m = re.match(r"^(\d{4})$", s)
    if m:
        return f"{m.group(1)}-03"

    # Month name/abbrev + separator (space/hyphen) + year (2 or 4 digit)
    m = re.match(r"^([A-Za-z]+)[\s\-]+(\d{2,4})$", s)
    if m:
        mon_raw, yr_raw = m.group(1).lower()[:3], m.group(2)
        if mon_raw in MONTH_MAP:
            yr = _expand_2digit_year(yr_raw)
            return f"{yr}-{MONTH_MAP[mon_raw]}"

    return PARSE_ERROR


def _expand_2digit_year(yr: str) -> str:
    """Expand a 2-digit year to 4 digits; pass through 4-digit years."""
    if len(yr) == 4:
        return yr
    if len(yr) == 2:
        # All data in this project is 2010-2024 range -> 20xx
        return f"20{yr}"
    return yr


def normalize_ticker(raw_ticker) -> str:
    """Standardise a company_id / ticker value.

    - Strips leading/trailing whitespace
    - Upper-cases
    - Preserves valid NSE ticker characters: letters, digits, '&', '-'
    - Returns empty string for missing/None/blank input (caller should
      treat empty string as a rejected row -- no FK match possible)
    """
    if raw_ticker is None:
        return ""
    s = str(raw_ticker).strip().upper()
    if s in ("", "NAN", "NONE", "MISSING"):
        return ""
    return s
