"""
Sprint 2 - CAGR Engine

Handles:
- Revenue CAGR
- PAT / Net Profit CAGR
- EPS CAGR
- 3-year, 5-year and 10-year periods
- All required CAGR edge cases
"""

import math


# ---------------------------------------------------------
# CAGR FLAG CONSTANTS
# ---------------------------------------------------------

NORMAL = "NORMAL"
DECLINE_TO_LOSS = "DECLINE_TO_LOSS"
TURNAROUND = "TURNAROUND"
BOTH_NEGATIVE = "BOTH_NEGATIVE"
ZERO_BASE = "ZERO_BASE"
INSUFFICIENT = "INSUFFICIENT"


# ---------------------------------------------------------
# CORE CAGR CALCULATION
# ---------------------------------------------------------

def calculate_cagr(start_value, end_value, years):
    """
    Calculate CAGR.

    Formula:
        ((end / start) ** (1 / years) - 1) * 100

    Returns:
        (cagr_value, flag)
    """

    # Missing values
    if start_value is None or end_value is None or years is None:
        return None, INSUFFICIENT

    # Invalid number of years
    if years <= 0:
        return None, INSUFFICIENT

    # Zero starting value
    if start_value == 0:
        return None, ZERO_BASE

    # Positive -> Positive
    if start_value > 0 and end_value > 0:
        try:
            cagr = ((end_value / start_value) ** (1 / years) - 1) * 100
            return cagr, NORMAL
        except (ValueError, ZeroDivisionError, OverflowError):
            return None, None

    # Positive -> Negative
    if start_value > 0 and end_value < 0:
        return None, DECLINE_TO_LOSS

    # Negative -> Positive
    if start_value < 0 and end_value > 0:
        return None, TURNAROUND

    # Negative -> Negative
    if start_value < 0 and end_value < 0:
        return None, BOTH_NEGATIVE

    # End value = 0
    # A positive/negative start reaching zero cannot produce
    # a meaningful standard CAGR.
    return None, ZERO_BASE


# ---------------------------------------------------------
# WINDOW VALIDATION
# ---------------------------------------------------------

def get_cagr_for_window(values_by_year, end_year, window):
    """
    Calculate CAGR for a specific historical window.

    Parameters:
        values_by_year:
            Dictionary like:
            {
                "2019-03": 100,
                "2020-03": 120,
                "2021-03": 150,
                ...
            }

        end_year:
            Latest year, e.g. "2022-03"

        window:
            3, 5 or 10

    Returns:
        (cagr_value, flag)
    """

    if not values_by_year or end_year is None:
        return None, INSUFFICIENT

    # Convert year strings into year numbers
    try:
        end_year_number = int(str(end_year)[:4])
    except (ValueError, TypeError):
        return None, INSUFFICIENT

    target_start_year = end_year_number - window

    start_year = None
    start_value = None

    # Find exact historical year
    for year, value in values_by_year.items():

        try:
            year_number = int(str(year)[:4])
        except (ValueError, TypeError):
            continue

        if year_number == target_start_year:
            start_year = year
            start_value = value
            break

    # Required start year does not exist
    if start_year is None:
        return None, INSUFFICIENT

    end_value = values_by_year.get(end_year)

    if end_value is None:
        return None, INSUFFICIENT

    return calculate_cagr(
        start_value,
        end_value,
        window
    )


# ---------------------------------------------------------
# ALL CAGR WINDOWS
# ---------------------------------------------------------

def calculate_all_cagr_windows(values_by_year, end_year):
    """
    Calculate 3-year, 5-year and 10-year CAGR.

    Returns dictionary containing:
        cagr_3yr
        cagr_3yr_flag
        cagr_5yr
        cagr_5yr_flag
        cagr_10yr
        cagr_10yr_flag
    """

    result = {}

    for window in (3, 5, 10):

        value, flag = get_cagr_for_window(
            values_by_year,
            end_year,
            window
        )

        result[f"cagr_{window}yr"] = value
        result[f"cagr_{window}yr_flag"] = flag

    return result


# ---------------------------------------------------------
# METRIC-SPECIFIC CAGR
# ---------------------------------------------------------

def calculate_metric_cagr(
    records,
    value_key,
    end_year
):
    """
    Calculate 3Y, 5Y and 10Y CAGR for one metric.

    Example:
        value_key = "sales"
        value_key = "net_profit"
        value_key = "eps"

    records:
        List of dictionaries containing year and metric values.
    """

    values_by_year = {}

    for record in records:

        year = record.get("year")
        value = record.get(value_key)

        if year is not None:
            values_by_year[year] = value

    result = calculate_all_cagr_windows(
        values_by_year,
        end_year
    )

    return {
        f"{value_key}_cagr_3yr":
            result["cagr_3yr"],

        f"{value_key}_cagr_3yr_flag":
            result["cagr_3yr_flag"],

        f"{value_key}_cagr_5yr":
            result["cagr_5yr"],

        f"{value_key}_cagr_5yr_flag":
            result["cagr_5yr_flag"],

        f"{value_key}_cagr_10yr":
            result["cagr_10yr"],

        f"{value_key}_cagr_10yr_flag":
            result["cagr_10yr_flag"],
    }


# ---------------------------------------------------------
# REVENUE CAGR
# ---------------------------------------------------------

def calculate_revenue_cagr(records, end_year):
    """
    Calculate Revenue CAGR for 3Y, 5Y and 10Y.
    """

    return calculate_metric_cagr(
        records,
        "sales",
        end_year
    )


# ---------------------------------------------------------
# PAT CAGR
# ---------------------------------------------------------

def calculate_pat_cagr(records, end_year):
    """
    Calculate PAT / Net Profit CAGR for 3Y, 5Y and 10Y.
    """

    return calculate_metric_cagr(
        records,
        "net_profit",
        end_year
    )


# ---------------------------------------------------------
# EPS CAGR
# ---------------------------------------------------------

def calculate_eps_cagr(records, end_year):
    """
    Calculate EPS CAGR for 3Y, 5Y and 10Y.
    """

    return calculate_metric_cagr(
        records,
        "eps",
        end_year
    )