import pytest

from src.analytics.ratios import (
    calculate_net_profit_margin,
    calculate_operating_profit_margin,
    check_opm_mismatch,
    calculate_roe,
    calculate_roce,
    calculate_roa,
    calculate_debt_to_equity,
    calculate_interest_coverage,
    calculate_net_debt,
    calculate_asset_turnover,
)

from src.analytics.cagr import calculate_cagr

from src.analytics.cashflow_kpis import (
    calculate_free_cash_flow,
    calculate_capex_intensity,
    calculate_fcf_conversion_rate,
    classify_capital_allocation,
)


# =========================================================
# PROFITABILITY RATIOS
# =========================================================

def test_net_profit_margin_normal():
    assert calculate_net_profit_margin(200, 1000) == 20.0


def test_net_profit_margin_zero_sales():
    assert calculate_net_profit_margin(200, 0) is None


def test_operating_profit_margin_normal():
    assert calculate_operating_profit_margin(250, 1000) == 25.0


def test_opm_mismatch_detected():
    calculated = calculate_operating_profit_margin(250, 1000)
    assert check_opm_mismatch(calculated, 20.0) is True


def test_roe_normal():
    assert calculate_roe(200, 500, 500) == 20.0


def test_roe_negative_equity():
    assert calculate_roe(200, -600, 500) is None


def test_roce_normal():
    assert calculate_roce(
        200,
        50,
        500,
        500,
        500
    ) == pytest.approx(16.6666666667)


def test_roa_zero_assets():
    assert calculate_roa(200, 0) is None


# =========================================================
# LEVERAGE & EFFICIENCY
# =========================================================

def test_debt_to_equity_debt_free():
    assert calculate_debt_to_equity(
        0,
        500,
        500
    ) == 0


def test_debt_to_equity_normal():
    assert calculate_debt_to_equity(
        500,
        500,
        500
    ) == 0.5


def test_high_leverage_flag():
    debt_to_equity = calculate_debt_to_equity(
        6000,
        500,
        500
    )

    assert debt_to_equity > 5


def test_interest_coverage_normal():
    assert calculate_interest_coverage(
        200,
        50,
        50
    ) == 5.0


def test_interest_coverage_zero_interest():
    assert calculate_interest_coverage(
        200,
        50,
        0
    ) is None


def test_net_debt():
    assert calculate_net_debt(
        500,
        100
    ) == 400


def test_asset_turnover_normal():
    assert calculate_asset_turnover(
        1000,
        500
    ) == 2.0


# =========================================================
# CAGR ENGINE
# =========================================================

def test_cagr_normal():
    result, flag = calculate_cagr(
        100,
        121,
        2
    )

    assert result == pytest.approx(10.0)
    assert flag == "NORMAL"


def test_cagr_turnaround():
    result, flag = calculate_cagr(
        -100,
        100,
        2
    )

    assert result is None
    assert flag == "TURNAROUND"


def test_cagr_decline_to_loss():
    result, flag = calculate_cagr(
        100,
        -100,
        2
    )

    assert result is None
    assert flag == "DECLINE_TO_LOSS"


def test_cagr_both_negative():
    result, flag = calculate_cagr(
        -100,
        -50,
        2
    )

    assert result is None
    assert flag == "BOTH_NEGATIVE"


def test_cagr_zero_base():
    result, flag = calculate_cagr(
        0,
        100,
        2
    )

    assert result is None
    assert flag == "ZERO_BASE"


# =========================================================
# CASH FLOW
# =========================================================

def test_free_cash_flow():
    assert calculate_free_cash_flow(
        500,
        -200
    ) == 300


def test_capex_intensity():
    result, label = calculate_capex_intensity(
        -50,
        1000
    )

    assert result == pytest.approx(5.0)
    assert label == "Moderate"


def test_fcf_conversion_rate():
    assert calculate_fcf_conversion_rate(
        300,
        500
    ) == pytest.approx(60.0)


def test_capital_allocation_pattern():
    assert classify_capital_allocation(
        100,
        -50,
        -25
    ) == "Reinvestor"