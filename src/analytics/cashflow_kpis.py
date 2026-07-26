"""
Sprint 2 - Cash Flow KPIs and Capital Allocation Engine

Implements:
- Free Cash Flow
- CFO Quality Score
- CapEx Intensity
- FCF Conversion Rate
- Capital Allocation Pattern Classification
"""


# ---------------------------------------------------------
# FREE CASH FLOW
# ---------------------------------------------------------

def calculate_free_cash_flow(
    operating_activity,
    investing_activity
):
    """
    Calculate Free Cash Flow.

    Formula:
        FCF = Operating Activity + Investing Activity

    Negative FCF is allowed.
    """

    if operating_activity is None or investing_activity is None:
        return None

    return operating_activity + investing_activity


# ---------------------------------------------------------
# CFO QUALITY SCORE
# ---------------------------------------------------------

def calculate_cfo_quality_score(
    cfo_values,
    pat_values
):
    """
    Calculate average CFO / PAT ratio over available years.

    Classification:
        > 1.0       = High Quality
        0.5 - 1.0   = Moderate
        < 0.5       = Accrual Risk

    Returns:
        (average_ratio, quality_label)

    If PAT is zero for all available periods:
        (None, None)
    """

    if not cfo_values or not pat_values:
        return None, None

    ratios = []

    for cfo, pat in zip(cfo_values, pat_values):

        if cfo is None or pat is None:
            continue

        if pat == 0:
            continue

        ratios.append(cfo / pat)

    if not ratios:
        return None, None

    average_ratio = sum(ratios) / len(ratios)

    if average_ratio > 1.0:
        quality_label = "High Quality"

    elif average_ratio >= 0.5:
        quality_label = "Moderate"

    else:
        quality_label = "Accrual Risk"

    return average_ratio, quality_label


# ---------------------------------------------------------
# CAPEX INTENSITY
# ---------------------------------------------------------

def calculate_capex_intensity(
    investing_activity,
    sales
):
    """
    Calculate CapEx Intensity.

    Formula:
        abs(Investing Activity) / Sales * 100

    Classification:
        < 3%      = Asset Light
        3% - 8%   = Moderate
        > 8%      = Capital Intensive

    Returns:
        (capex_intensity_pct, label)
    """

    if investing_activity is None or sales is None:
        return None, None

    if sales == 0:
        return None, None

    capex_intensity = (
        abs(investing_activity) / sales
    ) * 100

    if capex_intensity < 3:
        label = "Asset Light"

    elif capex_intensity <= 8:
        label = "Moderate"

    else:
        label = "Capital Intensive"

    return capex_intensity, label


# ---------------------------------------------------------
# FCF CONVERSION RATE
# ---------------------------------------------------------

def calculate_fcf_conversion_rate(
    free_cash_flow,
    operating_profit
):
    """
    Calculate FCF Conversion Rate.

    Formula:
        FCF / Operating Profit * 100

    Returns None if operating profit is zero.
    """

    if free_cash_flow is None or operating_profit is None:
        return None

    if operating_profit == 0:
        return None

    return (
        free_cash_flow / operating_profit
    ) * 100


# ---------------------------------------------------------
# SIGN HELPER
# ---------------------------------------------------------

def get_cash_flow_sign(value):
    """
    Convert cash flow value into:
        + : Positive
        - : Negative
        0 : Zero
        None : Missing
    """

    if value is None:
        return None

    if value > 0:
        return "+"

    if value < 0:
        return "-"

    return "0"


# ---------------------------------------------------------
# CAPITAL ALLOCATION CLASSIFIER
# ---------------------------------------------------------

def classify_capital_allocation(
    cfo,
    cfi,
    cff,
    cfo_pat_ratio=None
):
    """
    Classify capital allocation pattern based on
    CFO, CFI and CFF signs.

    Patterns:

        (+,-,-) = Reinvestor

        (+,-,-) with high CFO/PAT
                 = Shareholder Returns

        (+,+,-) = Liquidating Assets

        (-,+,+) = Distress Signal

        (-,-,+) = Growth Funded by Debt

        (+,+,+) = Cash Accumulator

        (-,-,-) = Pre-Revenue

        (+,-,+) = Mixed

    Priority:
        For (+,-,-), if CFO/PAT > 1.0,
        classify as Shareholder Returns.
    """

    cfo_sign = get_cash_flow_sign(cfo)
    cfi_sign = get_cash_flow_sign(cfi)
    cff_sign = get_cash_flow_sign(cff)

    if (
        cfo_sign is None
        or cfi_sign is None
        or cff_sign is None
    ):
        return None

    pattern = (
        cfo_sign,
        cfi_sign,
        cff_sign
    )

    # (+,-,-)
    if pattern == ("+", "-", "-"):

        if (
            cfo_pat_ratio is not None
            and cfo_pat_ratio > 1.0
        ):
            return "Shareholder Returns"

        return "Reinvestor"

    # (+,+,-)
    if pattern == ("+", "+", "-"):
        return "Liquidating Assets"

    # (-,+,+)
    if pattern == ("-", "+", "+"):
        return "Distress Signal"

    # (-,-,+)
    if pattern == ("-", "-", "+"):
        return "Growth Funded by Debt"

    # (+,+,+)
    if pattern == ("+", "+", "+"):
        return "Cash Accumulator"

    # (-,-,-)
    if pattern == ("-", "-", "-"):
        return "Pre-Revenue"

    # (+,-,+)
    if pattern == ("+", "-", "+"):
        return "Mixed"

    # Remaining pattern:
    # (-,+,-)
    if pattern == ("-", "+", "-"):
        return "Mixed"

    # Any other unexpected pattern
    return "Mixed"


# ---------------------------------------------------------
# COMPLETE CASH FLOW KPI CALCULATION
# ---------------------------------------------------------

def calculate_cashflow_kpis(
    operating_activity,
    investing_activity,
    financing_activity,
    sales,
    operating_profit,
    cfo_values=None,
    pat_values=None
):
    """
    Calculate all cash flow KPIs for a company-year.
    """

    free_cash_flow = calculate_free_cash_flow(
        operating_activity,
        investing_activity
    )

    cfo_quality_score = None
    cfo_quality_label = None

    if cfo_values is not None and pat_values is not None:

        (
            cfo_quality_score,
            cfo_quality_label
        ) = calculate_cfo_quality_score(
            cfo_values,
            pat_values
        )

    capex_intensity_pct = None
    capex_intensity_label = None

    (
        capex_intensity_pct,
        capex_intensity_label
    ) = calculate_capex_intensity(
        investing_activity,
        sales
    )

    fcf_conversion_rate = (
        calculate_fcf_conversion_rate(
            free_cash_flow,
            operating_profit
        )
    )

    capital_allocation_pattern = (
        classify_capital_allocation(
            operating_activity,
            investing_activity,
            financing_activity,
            cfo_quality_score
        )
    )

    return {
        "free_cash_flow": free_cash_flow,

        "cfo_quality_score":
            cfo_quality_score,

        "cfo_quality_label":
            cfo_quality_label,

        "capex_intensity_pct":
            capex_intensity_pct,

        "capex_intensity_label":
            capex_intensity_label,

        "fcf_conversion_rate":
            fcf_conversion_rate,

        "capital_allocation_pattern":
            capital_allocation_pattern
    }