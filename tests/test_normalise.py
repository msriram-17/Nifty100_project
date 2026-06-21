"""Unit tests for normaliser.py — 35+ test cases.

20 normalize_year() tests + 15 normalize_ticker() tests, per Sprint 1 spec.
Run with: pytest tests/etl/test_normalise.py -v
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src", "etl"))

from normaliser import normalize_year, normalize_ticker, PARSE_ERROR


# ---------------------------------------------------------------------------
# normalize_year() — 20 test cases
# ---------------------------------------------------------------------------

def test_year_mar_hyphen_2digit():
    assert normalize_year("Mar-23") == "2023-03"


def test_year_mar_space_4digit():
    assert normalize_year("Mar 2014") == "2014-03"


def test_year_mar_space_2digit():
    assert normalize_year("Mar 23") == "2023-03"


def test_year_full_month_hyphen():
    assert normalize_year("March-2023") == "2023-03"


def test_year_bare_4digit():
    assert normalize_year("2023") == "2023-03"


def test_year_fy_prefix_2digit():
    assert normalize_year("FY23") == "2023-03"


def test_year_fy_prefix_4digit():
    assert normalize_year("FY2023") == "2023-03"


def test_year_dec_hyphen():
    assert normalize_year("Dec-22") == "2022-12"


def test_year_jun_hyphen():
    assert normalize_year("Jun-23") == "2023-06"


def test_year_already_normalised():
    assert normalize_year("2023-03") == "2023-03"


def test_year_garbage():
    assert normalize_year("garbage") == PARSE_ERROR


def test_year_ttm():
    assert normalize_year("TTM") == PARSE_ERROR


def test_year_none():
    assert normalize_year(None) == PARSE_ERROR


def test_year_empty_string():
    assert normalize_year("") == PARSE_ERROR


def test_year_whitespace_only():
    assert normalize_year("   ") == PARSE_ERROR


def test_year_mar_with_extra_tokens():
    assert normalize_year("Mar 2016 9m") == PARSE_ERROR


def test_year_dec_4digit():
    assert normalize_year("Dec-2022") == "2022-12"


def test_year_lowercase_month():
    assert normalize_year("mar-23") == "2023-03"


def test_year_mixed_case_month():
    assert normalize_year("MaR-23") == "2023-03"


def test_year_sep_fy():
    assert normalize_year("FY-23") == "2023-03"


# ---------------------------------------------------------------------------
# normalize_ticker() — 15 test cases
# ---------------------------------------------------------------------------

def test_ticker_strip_whitespace():
    assert normalize_ticker("  TCS  ") == "TCS"


def test_ticker_lowercase_to_upper():
    assert normalize_ticker("tcs") == "TCS"


def test_ticker_mixed_case():
    assert normalize_ticker("TcS") == "TCS"


def test_ticker_hyphenated():
    assert normalize_ticker("bajaj-auto") == "BAJAJ-AUTO"


def test_ticker_ampersand():
    assert normalize_ticker("m&m") == "M&M"


def test_ticker_none():
    assert normalize_ticker(None) == ""


def test_ticker_missing_string():
    assert normalize_ticker("MISSING") == ""


def test_ticker_nan_string():
    assert normalize_ticker("nan") == ""


def test_ticker_empty_string():
    assert normalize_ticker("") == ""


def test_ticker_already_normalised():
    assert normalize_ticker("TCS") == "TCS"


def test_ticker_leading_whitespace():
    assert normalize_ticker("   wipro") == "WIPRO"


def test_ticker_trailing_whitespace():
    assert normalize_ticker("wipro   ") == "WIPRO"


def test_ticker_numeric_chars():
    assert normalize_ticker("m&m") != ""


def test_ticker_none_string_literal():
    assert normalize_ticker("None") == ""


def test_ticker_single_char_preserved():
    # Edge case: short tickers should still normalise (length validation
    # happens in the DQ validator, not here).
    assert normalize_ticker("lt") == "LT"
