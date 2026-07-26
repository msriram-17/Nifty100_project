"""
Sprint 2 - Financial Ratio Engine

Implements:
- Net Profit Margin (NPM)
- Operating Profit Margin (OPM)
- OPM mismatch check
- Return on Equity (ROE)
- Return on Capital Employed (ROCE)
- Return on Assets (ROA)
- Debt-to-Equity (D/E)
- High leverage flag
- Interest Coverage Ratio (ICR)
- Debt Free label
- ICR warning
- Net Debt
- Asset Turnover
"""


# =========================================================
# PROFITABILITY RATIOS
# =========================================================

def calculate_net_profit_margin(net_profit, sales):
    """
    NPM = Net Profit / Sales * 100
    """

    if net_profit is None or sales is None:
        return None

    if sales == 0:
        return None

    return (net_profit / sales) * 100


def calculate_operating_profit_margin(
    operating_profit,
    sales
):
    """
    OPM = Operating Profit / Sales * 100
    """

    if operating_profit is None or sales is None:
        return None

    if sales == 0:
        return None

    return (operating_profit / sales) * 100


def check_opm_mismatch(
    calculated_opm,
    source_opm,
    threshold=1.0
):
    """
    Returns True if calculated OPM differs from
    source OPM by more than threshold percentage points.
    """

    if calculated_opm is None or source_opm is None:
        return None

    difference = abs(
        calculated_opm - source_opm
    )

    return difference > threshold


def calculate_roe(
    net_profit,
    equity_capital,
    reserves
):
    """
    ROE = Net Profit /
          (Equity Capital + Reserves) * 100

    Returns None when total equity <= 0.
    """

    if (
        net_profit is None
        or equity_capital is None
        or reserves is None
    ):
        return None

    total_equity = (
        equity_capital
        + reserves
    )

    if total_equity <= 0:
        return None

    return (
        net_profit
        / total_equity
    ) * 100


def calculate_roce(
    operating_profit,
    other_income,
    equity_capital,
    reserves,
    borrowings
):
    """
    EBIT = Operating Profit + Other Income

    Capital Employed =
        Equity Capital + Reserves + Borrowings

    ROCE = EBIT / Capital Employed * 100

    Note:
    Financial-sector benchmark handling is performed
    by the engine using sector-relative comparisons.
    """

    if (
        operating_profit is None
        or other_income is None
        or equity_capital is None
        or reserves is None
        or borrowings is None
    ):
        return None

    ebit = (
        operating_profit
        + other_income
    )

    capital_employed = (
        equity_capital
        + reserves
        + borrowings
    )

    if capital_employed <= 0:
        return None

    return (
        ebit
        / capital_employed
    ) * 100


def calculate_roa(
    net_profit,
    total_assets
):
    """
    ROA = Net Profit / Total Assets * 100
    """

    if (
        net_profit is None
        or total_assets is None
    ):
        return None

    if total_assets == 0:
        return None

    return (
        net_profit
        / total_assets
    ) * 100


# =========================================================
# LEVERAGE RATIOS
# =========================================================

def calculate_debt_to_equity(
    borrowings,
    equity_capital,
    reserves
):
    """
    D/E = Borrowings /
          (Equity Capital + Reserves)

    Debt-free companies return 0.

    Negative or zero equity returns None.
    """

    if borrowings is None:
        return None

    # Required Sprint 2 behaviour:
    # Debt-free company -> 0, not None
    if borrowings == 0:
        return 0.0

    if (
        equity_capital is None
        or reserves is None
    ):
        return None

    total_equity = (
        equity_capital
        + reserves
    )

    if total_equity <= 0:
        return None

    return (
        borrowings
        / total_equity
    )


def calculate_high_leverage_flag(
    debt_to_equity,
    broad_sector,
    threshold=5.0
):
    """
    High leverage flag:

    D/E > 5 AND company is NOT in Financials sector
    """

    if debt_to_equity is None:
        return False

    if broad_sector == "Financials":
        return False

    return debt_to_equity > threshold


# =========================================================
# INTEREST COVERAGE RATIO
# =========================================================

def calculate_interest_coverage(
    operating_profit,
    other_income,
    interest
):
    """
    ICR = (Operating Profit + Other Income) / Interest

    Returns None when interest = 0.
    """

    if (
        operating_profit is None
        or other_income is None
        or interest is None
    ):
        return None

    if interest == 0:
        return None

    ebit = (
        operating_profit
        + other_income
    )

    return ebit / interest


def get_icr_label(interest_coverage):
    """
    Debt-free companies are represented by:
        Debt Free
    """

    if interest_coverage is None:
        return "Debt Free"

    return None


def calculate_icr_warning(
    interest_coverage,
    threshold=1.5
):
    """
    True when ICR < 1.5.
    """

    if interest_coverage is None:
        return False

    return interest_coverage < threshold


# =========================================================
# NET DEBT
# =========================================================

def calculate_net_debt(
    borrowings,
    investments
):
    """
    Net Debt = Borrowings - Investments

    Investments are used as liquid asset proxy.
    """

    if (
        borrowings is None
        or investments is None
    ):
        return None

    return (
        borrowings
        - investments
    )


# =========================================================
# ASSET TURNOVER
# =========================================================

def calculate_asset_turnover(
    sales,
    total_assets
):
    """
    Asset Turnover = Sales / Total Assets
    """

    if (
        sales is None
        or total_assets is None
    ):
        return None

    if total_assets == 0:
        return None

    return (
        sales
        / total_assets
    )


# =========================================================
# COMPLETE RATIO CALCULATION
# =========================================================

def calculate_all_ratios(
    net_profit,
    sales,
    operating_profit,
    other_income,
    equity_capital,
    reserves,
    borrowings,
    total_assets,
    investments,
    interest,
    source_opm=None,
    broad_sector=None
):
    """
    Calculate all Sprint 2 profitability,
    leverage and efficiency ratios.
    """

    npm = calculate_net_profit_margin(
        net_profit,
        sales
    )

    opm = calculate_operating_profit_margin(
        operating_profit,
        sales
    )

    opm_mismatch = check_opm_mismatch(
        opm,
        source_opm
    )

    roe = calculate_roe(
        net_profit,
        equity_capital,
        reserves
    )

    roce = calculate_roce(
        operating_profit,
        other_income,
        equity_capital,
        reserves,
        borrowings
    )

    roa = calculate_roa(
        net_profit,
        total_assets
    )

    debt_to_equity = calculate_debt_to_equity(
        borrowings,
        equity_capital,
        reserves
    )

    high_leverage_flag = calculate_high_leverage_flag(
        debt_to_equity,
        broad_sector
    )

    interest_coverage = calculate_interest_coverage(
        operating_profit,
        other_income,
        interest
    )

    icr_label = get_icr_label(
        interest_coverage
    )

    icr_warning = calculate_icr_warning(
        interest_coverage
    )

    net_debt = calculate_net_debt(
        borrowings,
        investments
    )

    asset_turnover = calculate_asset_turnover(
        sales,
        total_assets
    )

    return {
        "net_profit_margin_pct": npm,
        "operating_profit_margin_pct": opm,
        "opm_mismatch_flag": opm_mismatch,
        "return_on_equity_pct": roe,
        "return_on_capital_employed_pct": roce,
        "return_on_assets_pct": roa,
        "debt_to_equity": debt_to_equity,
        "high_leverage_flag": high_leverage_flag,
        "interest_coverage": interest_coverage,
        "icr_label": icr_label,
        "icr_warning_flag": icr_warning,
        "net_debt_cr": net_debt,
        "asset_turnover": asset_turnover
    }