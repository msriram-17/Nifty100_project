"""
Sprint 3 - Financial Screener Engine

Features:
1. Loads latest financial data per company
2. Supports all Sprint 3 filter metrics
3. Financial-sector D/E exception
4. Debt-Free ICR handling
5. Six preset screeners
6. Composite quality score
7. P10/P90 winsorisation
8. Sector-relative scoring
9. Turnaround Watch YoY D/E decline
10. Safe handling of missing data
11. Custom threshold support
"""

import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd


# =========================================================
# PATHS
# =========================================================

BASE_DIR = Path(__file__).resolve().parents[2]

DB_PATH = BASE_DIR / "db" / "nifty100.db"


# =========================================================
# PRESET DEFINITIONS
# =========================================================

PRESETS = {

    "Quality Compounder": {

        "roe_min": 15,

        "de_max": 1.0,

        "fcf_min": 0,

        "revenue_cagr_5yr_min": 10,

    },


    "Value Pick": {

        "pe_max": 20,

        "pb_max": 3.0,

        "de_max": 2.0,

        "dividend_yield_min": 1,

    },


    "Growth Accelerator": {

        "pat_cagr_5yr_min": 20,

        "revenue_cagr_5yr_min": 15,

        "de_max": 2.0,

    },


    "Dividend Champion": {

        "dividend_yield_min": 2,

        "dividend_payout_max": 80,

        "fcf_min": 0,

    },


    "Debt-Free Blue Chip": {

        "de_max": 0,

        "roe_min": 12,

        "sales_min": 5000,

    },


    "Turnaround Watch": {

        "revenue_cagr_3yr_min": 10,

        "fcf_min": 0,

        "de_declining_yoy": True,

    },

}


# =========================================================
# FILTER MAPPING
# =========================================================

FILTER_COLUMNS = {

    "roe_min":
        "return_on_equity_pct",

    "roce_min":
        "return_on_capital_employed_pct",

    "npm_min":
        "net_profit_margin_pct",

    "opm_min":
        "operating_profit_margin_pct",

    "de_max":
        "debt_to_equity",

    "fcf_min":
        "free_cash_flow_cr",

    "revenue_cagr_3yr_min":
        "revenue_cagr_3yr",

    "revenue_cagr_5yr_min":
        "revenue_cagr_5yr",

    "pat_cagr_5yr_min":
        "pat_cagr_5yr",

    "eps_cagr_min":
        "eps_cagr_5yr",

    "icr_min":
        "interest_coverage",

    "asset_turnover_min":
        "asset_turnover",

    "pe_max":
        "pe_ratio",

    "pb_max":
        "pb_ratio",

    "dividend_yield_min":
        "dividend_yield_pct",

    "dividend_payout_max":
        "dividend_payout_ratio_pct",

    "market_cap_min":
        "market_cap_cr",

    "net_profit_min":
        "net_profit_cr",

    "sales_min":
        "sales_cr",

}


# =========================================================
# REQUIRED OUTPUT COLUMNS
# =========================================================

OUTPUT_COLUMNS = [

    "company_id",

    "year",

    "broad_sector",

    "return_on_equity_pct",

    "return_on_capital_employed_pct",

    "net_profit_margin_pct",

    "operating_profit_margin_pct",

    "debt_to_equity",

    "interest_coverage",

    "icr_label",

    "free_cash_flow_cr",

    "cash_from_operations_cr",

    "cfo_quality_score",

    "revenue_cagr_3yr",

    "revenue_cagr_5yr",

    "pat_cagr_5yr",

    "eps_cagr_5yr",

    "asset_turnover",

    "pe_ratio",

    "pb_ratio",

    "dividend_yield_pct",

    "dividend_payout_ratio_pct",

    "market_cap_cr",

    "net_profit_cr",

    "sales_cr",

    "composite_quality_score",

    "sector_relative_score",

]


# =========================================================
# DATABASE HELPERS
# =========================================================

def get_table_columns(
    conn,
    table_name
):

    rows = conn.execute(

        f"PRAGMA table_info({table_name})"

    ).fetchall()

    return [

        row[1]

        for row in rows

    ]


# =========================================================
# LOAD LATEST DATA
# =========================================================

def load_latest_financial_data(

    db_path=DB_PATH

):

    """
    Load the latest available financial record
    for each company.

    Uses financial_ratios as the main table.

    Adds:

    - P/E
    - P/B
    - Dividend Yield
    - Market Cap
    - Net Profit
    - Sales
    """

    conn = sqlite3.connect(

        str(db_path)

    )


    query = """

    WITH latest_ratios AS (

        SELECT *

        FROM (

            SELECT

                fr.*,

                ROW_NUMBER() OVER (

                    PARTITION BY
                        fr.company_id

                    ORDER BY
                        fr.year DESC

                ) AS rn

            FROM financial_ratios fr

        )

        WHERE rn = 1

    ),

    latest_market AS (

        SELECT *

        FROM (

            SELECT

                mc.*,

                ROW_NUMBER() OVER (

                    PARTITION BY
                        mc.company_id

                    ORDER BY
                        mc.year DESC

                ) AS rn

            FROM market_cap mc

        )

        WHERE rn = 1

    ),

    latest_pnl AS (

        SELECT *

        FROM (

            SELECT

                pl.*,

                ROW_NUMBER() OVER (

                    PARTITION BY
                        pl.company_id

                    ORDER BY
                        pl.year DESC

                ) AS rn

            FROM profitandloss pl

        )

        WHERE rn = 1

    )

    SELECT

        fr.*,

        mc.market_cap_crore
            AS market_cap_cr,

        mc.pe_ratio
            AS pe_ratio,

        mc.pb_ratio
            AS pb_ratio,

        mc.dividend_yield_pct
            AS dividend_yield_pct,

        pl.sales
            AS sales_cr,

        pl.net_profit
            AS net_profit_cr,

        pl.dividend_payout
            AS pnl_dividend_payout

    FROM latest_ratios fr

    LEFT JOIN latest_market mc

        ON fr.company_id =
           mc.company_id

    LEFT JOIN latest_pnl pl

        ON fr.company_id =
           pl.company_id

    """

    df = pd.read_sql_query(

        query,

        conn

    )


    conn.close()


    if df.empty:

        raise ValueError(

            "financial_ratios contains "
            "no records."

        )


    # -----------------------------------------------------
    # DIVIDEND PAYOUT FALLBACK
    # -----------------------------------------------------

    if "dividend_payout_ratio_pct" not in df.columns:

        df[
            "dividend_payout_ratio_pct"
        ] = df[
            "pnl_dividend_payout"
        ]

    else:

        df[
            "dividend_payout_ratio_pct"
        ] = df[
            "dividend_payout_ratio_pct"
        ].fillna(

            df[
                "pnl_dividend_payout"
            ]

        )


    return df.reset_index(

        drop=True

    )


# =========================================================
# LOAD HISTORICAL DATA
# =========================================================

def load_historical_ratios(

    db_path=DB_PATH

):

    """
    Load all historical financial ratio records.

    Used specifically for:

    Turnaround Watch

    D/E declining year-over-year.
    """

    conn = sqlite3.connect(

        str(db_path)

    )


    df = pd.read_sql_query(

        """

        SELECT

            company_id,

            year,

            debt_to_equity,

            revenue_cagr_3yr,

            free_cash_flow_cr

        FROM financial_ratios

        ORDER BY

            company_id,

            year

        """,

        conn

    )


    conn.close()


    return df


# =========================================================
# DEBT-FREE ICR NORMALISATION
# =========================================================

def normalise_icr(

    df

):

    """
    Debt Free companies should pass any
    positive ICR minimum.

    Their ICR is treated as infinity.
    """

    df = df.copy()


    if "icr_label" not in df.columns:

        return df


    if "interest_coverage" not in df.columns:

        return df


    debt_free_mask = (

        df[
            "icr_label"
        ]

        .astype(str)

        .str.strip()

        .str.lower()

        .isin(

            [

                "debt free",

                "debt_free",

                "debt-free",

            ]

        )

    )


    df.loc[

        debt_free_mask,

        "interest_coverage"

    ] = np.inf


    return df


# =========================================================
# PERCENTILE NORMALISATION
# =========================================================

def winsorised_normalise(

    series,

    higher_is_better=True

):

    """
    P10/P90 winsorisation.

    Output:

    0 to 100.
    """

    numeric = pd.to_numeric(

        series,

        errors="coerce"

    )


    valid = numeric.dropna()


    result = pd.Series(

        np.nan,

        index=series.index,

        dtype=float

    )


    if len(valid) == 0:

        return result


    p10 = valid.quantile(

        0.10

    )

    p90 = valid.quantile(

        0.90

    )


    if p10 == p90:

        result.loc[
            valid.index
        ] = 50.0

        return result


    clipped = numeric.clip(

        lower=p10,

        upper=p90

    )


    score = (

        (

            clipped - p10

        )

        /

        (

            p90 - p10

        )

    ) * 100


    if not higher_is_better:

        score = 100 - score


    result.loc[
        score.index
    ] = score


    return result


# =========================================================
# COMPOSITE QUALITY SCORE
# =========================================================

def calculate_composite_score(

    df

):

    """
    Sprint 3 composite score.

    Profitability 35%:

    ROE 15%
    ROCE 10%
    NPM 10%

    Cash Quality 30%:

    FCF 15%
    CFO/PAT 10%
    FCF positive 5%

    Growth 20%:

    Revenue CAGR 10%
    PAT CAGR 10%

    Leverage 15%:

    D/E 10%
    ICR 5%

    All continuous metrics use
    P10/P90 winsorisation.
    """

    df = df.copy()


    score = pd.DataFrame(

        index=df.index

    )


    # -----------------------------------------------------
    # PROFITABILITY
    # -----------------------------------------------------

    score[
        "roe"
    ] = winsorised_normalise(

        df[
            "return_on_equity_pct"
        ]

    )


    score[
        "roce"
    ] = winsorised_normalise(

        df[
            "return_on_capital_employed_pct"
        ]

    )


    score[
        "npm"
    ] = winsorised_normalise(

        df[
            "net_profit_margin_pct"
        ]

    )


    # -----------------------------------------------------
    # FCF
    # -----------------------------------------------------

    score[
        "fcf"
    ] = winsorised_normalise(

        df[
            "free_cash_flow_cr"
        ]

    )


    # -----------------------------------------------------
    # CFO / PAT
    # -----------------------------------------------------

    if (

        "cash_from_operations_cr"

        in df.columns

        and

        "net_profit_cr"

        in df.columns

    ):

        pat = pd.to_numeric(

            df[
                "net_profit_cr"
            ],

            errors="coerce"

        )


        cfo = pd.to_numeric(

            df[
                "cash_from_operations_cr"
            ],

            errors="coerce"

        )


        cfo_pat = cfo.divide(

            pat.replace(

                0,

                np.nan

            )

        )


        score[
            "cfo_pat"
        ] = winsorised_normalise(

            cfo_pat

        )

    else:

        score[
            "cfo_pat"
        ] = 50.0


    # -----------------------------------------------------
    # FCF POSITIVE FLAG
    # -----------------------------------------------------

    fcf_positive = (

        pd.to_numeric(

            df[
                "free_cash_flow_cr"
            ],

            errors="coerce"

        )

        >

        0

    ).astype(float) * 100


    score[
        "fcf_positive"
    ] = fcf_positive


    # -----------------------------------------------------
    # GROWTH
    # -----------------------------------------------------

    score[
        "revenue_growth"
    ] = winsorised_normalise(

        df[
            "revenue_cagr_5yr"
        ]

    )


    score[
        "pat_growth"
    ] = winsorised_normalise(

        df[
            "pat_cagr_5yr"
        ]

    )


    # -----------------------------------------------------
    # LEVERAGE
    # -----------------------------------------------------

    score[
        "de"
    ] = winsorised_normalise(

        df[
            "debt_to_equity"
        ],

        higher_is_better=False

    )


    score[
        "icr"
    ] = winsorised_normalise(

        df[
            "interest_coverage"
        ]

    )


    # -----------------------------------------------------
    # WEIGHTED COMPOSITE
    # -----------------------------------------------------

    weights = {

        "roe":
            0.15,

        "roce":
            0.10,

        "npm":
            0.10,

        "fcf":
            0.15,

        "cfo_pat":
            0.10,

        "fcf_positive":
            0.05,

        "revenue_growth":
            0.10,

        "pat_growth":
            0.10,

        "de":
            0.10,

        "icr":
            0.05,

    }


    weighted_sum = pd.Series(

        0.0,

        index=df.index

    )


    weight_sum = pd.Series(

        0.0,

        index=df.index

    )


    for column, weight in weights.items():

        values = score[
            column
        ]


        valid = values.notna()


        weighted_sum.loc[
            valid
        ] += (

            values.loc[
                valid
            ]

            *

            weight

        )


        weight_sum.loc[
            valid
        ] += weight


    df[
        "composite_quality_score"
    ] = (

        weighted_sum.divide(

            weight_sum.replace(

                0,

                np.nan

            )

        )

    ).fillna(

        0

    ).clip(

        0,

        100

    )


    return df


# =========================================================
# SECTOR-RELATIVE SCORE
# =========================================================

def calculate_sector_relative_score(

    df

):

    df = df.copy()


    df[
        "sector_relative_score"
    ] = np.nan


    if "broad_sector" not in df.columns:

        df[
            "sector_relative_score"
        ] = df[
            "composite_quality_score"
        ]

        return df


    for sector, group in df.groupby(

        "broad_sector",

        dropna=False

    ):

        scores = group[
            "composite_quality_score"
        ]


        if len(scores) < 2:

            df.loc[

                group.index,

                "sector_relative_score"

            ] = scores

            continue


        sector_score = winsorised_normalise(

            scores

        )


        df.loc[

            group.index,

            "sector_relative_score"

        ] = sector_score


    return df


# =========================================================
# APPLY NORMAL FILTER
# =========================================================

def apply_standard_filter(

    df,

    filter_name,

    threshold

):

    if filter_name not in FILTER_COLUMNS:

        raise ValueError(

            f"Unsupported filter metric: "
            f"{filter_name}"

        )


    column = FILTER_COLUMNS[
        filter_name
    ]


    if column not in df.columns:

        raise ValueError(

            f"Required column '{column}' "
            f"for filter '{filter_name}' "
            f"does not exist."

        )


    values = pd.to_numeric(

        df[column],

        errors="coerce"

    )


    # -----------------------------------------------------
    # MINIMUM
    # -----------------------------------------------------

    if filter_name.endswith(

        "_min"

    ):

        return df[

            values.notna()

            &

            (

                values

                >=

                threshold

            )

        ].copy()


    # -----------------------------------------------------
    # MAXIMUM
    # -----------------------------------------------------

    if filter_name.endswith(

        "_max"

    ):

        return df[

            values.notna()

            &

            (

                values

                <=

                threshold

            )

        ].copy()


    return df


# =========================================================
# APPLY D/E FILTER WITH FINANCIALS EXCEPTION
# =========================================================

def apply_de_filter(

    df,

    threshold

):

    """
    D/E filter is skipped for Financials.

    Non-Financial companies must satisfy
    the requested D/E threshold.

    For Debt-Free Blue Chip:

    D/E <= 0.01
    """

    if "broad_sector" not in df.columns:

        return apply_standard_filter(

            df,

            "de_max",

            threshold

        )


    sector = (

        df[
            "broad_sector"
        ]

        .astype(str)

        .str.strip()

        .str.lower()

    )


    financial_mask = sector.eq(

        "financials"

    )


    numeric_de = pd.to_numeric(

        df[
            "debt_to_equity"
        ],

        errors="coerce"

    )


    passing_non_financial = (

        numeric_de.notna()

        &

        (

            numeric_de

            <=

            threshold

        )

    )


    return df[

        financial_mask

        |

        passing_non_financial

    ].copy()


# =========================================================
# TURNAROUND WATCH
# =========================================================

def apply_turnaround_watch(

    df,

    db_path=DB_PATH

):

    """
    Requirements:

    1. Revenue CAGR 3yr > 10%
    2. FCF positive
    3. D/E declining YoY

    D/E declining means:

    Current year D/E < previous
    available year D/E.
    """

    result = df.copy()


    # -----------------------------------------------------
    # REVENUE CAGR
    # -----------------------------------------------------

    revenue = pd.to_numeric(

        result[
            "revenue_cagr_3yr"
        ],

        errors="coerce"

    )


    result = result[

        revenue.notna()

        &

        (

            revenue

            >

            10

        )

    ].copy()


    # -----------------------------------------------------
    # FCF POSITIVE
    # -----------------------------------------------------

    fcf = pd.to_numeric(

        result[
            "free_cash_flow_cr"
        ],

        errors="coerce"

    )


    result = result[

        fcf.notna()

        &

        (

            fcf

            >

            0

        )

    ].copy()


    if result.empty:

        return result


    # -----------------------------------------------------
    # HISTORICAL D/E
    # -----------------------------------------------------

    history = load_historical_ratios(

        db_path

    )


    history[
        "debt_to_equity"
    ] = pd.to_numeric(

        history[
            "debt_to_equity"
        ],

        errors="coerce"

    )


    history = history.sort_values(

        [

            "company_id",

            "year"

        ]

    )


    history[
        "previous_de"
    ] = history.groupby(

        "company_id"

    )[

        "debt_to_equity"

    ].shift(

        1

    )


    history[
        "de_declining_yoy"
    ] = (

        history[
            "debt_to_equity"
        ]

        <

        history[
            "previous_de"
        ]

    )


    declining_ids = set(

        history.loc[

            history[
                "de_declining_yoy"
            ]

            ==

            True,

            "company_id"

        ].tolist()

    )


    result = result[

        result[
            "company_id"
        ].isin(

            declining_ids

        )

    ].copy()


    return result


# =========================================================
# RUN CUSTOM SCREENER
# =========================================================

def run_screener(

    filters,

    db_path=DB_PATH

):

    df = load_latest_financial_data(

        db_path

    )


    df = normalise_icr(

        df

    )


    # -----------------------------------------------------
    # SPECIAL TURNAROUND
    # -----------------------------------------------------

    if filters.get(

        "de_declining_yoy",

        False

    ):

        df = apply_turnaround_watch(

            df,

            db_path

        )


    # -----------------------------------------------------
    # APPLY FILTERS
    # -----------------------------------------------------

    for filter_name, threshold in filters.items():

        if filter_name == "de_declining_yoy":

            continue


        if filter_name == "de_max":

            df = apply_de_filter(

                df,

                threshold

            )

        else:

            df = apply_standard_filter(

                df,

                filter_name,

                threshold

            )


        if df.empty:

            break


    # -----------------------------------------------------
    # COMPOSITE SCORE
    # -----------------------------------------------------

    if not df.empty:

        df = calculate_composite_score(

            df

        )


        df = calculate_sector_relative_score(

            df

        )


        df = df.sort_values(

            [

                "composite_quality_score",

                "sector_relative_score"

            ],

            ascending=False

        )


    return df.reset_index(

        drop=True

    )


# =========================================================
# RUN PRESET
# =========================================================

def run_preset(

    preset_name,

    db_path=DB_PATH

):

    if preset_name not in PRESETS:

        raise ValueError(

            f"Unknown preset: "
            f"{preset_name}. "

            f"Available presets: "
            f"{list(PRESETS.keys())}"

        )


    return run_screener(

        PRESETS[
            preset_name
        ],

        db_path

    )


# =========================================================
# RUN ALL PRESETS
# =========================================================

def run_all_presets(

    db_path=DB_PATH

):

    results = {}


    for preset_name in PRESETS:

        try:

            results[
                preset_name
            ] = run_preset(

                preset_name,

                db_path

            )

        except Exception as exc:

            print(

                f"{preset_name} | ERROR | "

                f"{type(exc).__name__}: "

                f"{exc}"

            )


            results[
                preset_name
            ] = pd.DataFrame()


    return results


# =========================================================
# VALIDATE PRESETS
# =========================================================

def validate_presets(

    results

):

    print()

    print(

        "=" * 60

    )

    print(

        "PRESET VALIDATION"

    )

    print(

        "=" * 60

    )


    all_valid = True


    for preset_name, df in results.items():

        count = len(df)


        valid_count = (

            5

            <=

            count

            <=

            50

        )


        status = (

            "PASS"

            if valid_count

            else

            "REVIEW"

        )


        if not valid_count:

            all_valid = False


        print(

            f"{preset_name}: "

            f"{count} companies | "

            f"{status}"

        )


    print()

    if all_valid:

        print(

            "All presets satisfy "
            "the 5-50 company range."

        )

    else:

        print(

            "Some presets are outside "
            "the required 5-50 range."

        )

        print(

            "Do NOT artificially add companies. "

            "Review the thresholds or "
            "underlying source data."

        )


    return all_valid


# =========================================================
# MAIN
# =========================================================

if __name__ == "__main__":

    print(

        "=" * 60

    )

    print(

        "SPRINT 3 SCREENER ENGINE TEST"

    )

    print(

        "=" * 60

    )


    results = run_all_presets()


    for preset_name, result in results.items():

        print()

        print(

            preset_name

        )

        print(

            "Companies returned:",

            len(result)

        )


        if not result.empty:

            display_columns = [

                "company_id",

                "year",

                "composite_quality_score",

                "sector_relative_score",

            ]


            available = [

                col

                for col in display_columns

                if col in result.columns

            ]


            print(

                result[
                    available
                ].head(5).to_string(

                    index=False

                )

            )


    validate_presets(

        results

    )