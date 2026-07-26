"""
SPRINT 2 - FINANCIAL RATIO ENGINE
=================================

Single execution pipeline.

Run:
    python run_sprint2.py

Outputs:
    1. db/nifty100.db -> financial_ratios table
    2. output/capital_allocation.csv
    3. output/ratio_edge_cases.log

Uses:
    src.analytics.ratios
    src.analytics.cagr
    src.analytics.cashflow_kpis
"""

import csv
import os
import sqlite3
from collections import defaultdict

from src.analytics.ratios import (
    calculate_all_ratios
)

from src.analytics.cagr import (
    calculate_revenue_cagr,
    calculate_pat_cagr,
    calculate_eps_cagr
)

from src.analytics.cashflow_kpis import (
    calculate_cashflow_kpis,
    calculate_cfo_quality_score
)


# =========================================================
# CONFIGURATION
# =========================================================

DB_PATH = "db/nifty100.db"

OUTPUT_DIR = "output"

CAPITAL_ALLOCATION_FILE = (
    os.path.join(
        OUTPUT_DIR,
        "capital_allocation.csv"
    )
)

EDGE_CASE_LOG = (
    os.path.join(
        OUTPUT_DIR,
        "ratio_edge_cases.log"
    )
)


# =========================================================
# DATABASE CONNECTION
# =========================================================

def get_connection():
    return sqlite3.connect(DB_PATH)


# =========================================================
# CREATE OUTPUT DIRECTORY
# =========================================================

def create_output_directory():

    os.makedirs(
        OUTPUT_DIR,
        exist_ok=True
    )


# =========================================================
# LOAD SOURCE DATA
# =========================================================

def load_source_data(conn):

    query = """
        SELECT
            bs.company_id,
            bs.year,

            bs.equity_capital,
            bs.reserves,
            bs.borrowings,
            bs.investments,
            bs.total_assets,

            pl.sales,
            pl.operating_profit,
            pl.opm_percentage,
            pl.other_income,
            pl.interest,
            pl.net_profit,
            pl.eps,
            pl.dividend_payout,

            cf.operating_activity,
            cf.investing_activity,
            cf.financing_activity,

            c.book_value,
            c.roce_percentage AS source_roce,
            c.roe_percentage AS source_roe,

            s.broad_sector

        FROM balancesheet bs

        LEFT JOIN profitandloss pl
            ON bs.company_id = pl.company_id
            AND bs.year = pl.year

        LEFT JOIN cashflow cf
            ON bs.company_id = cf.company_id
            AND bs.year = cf.year

        LEFT JOIN companies c
            ON bs.company_id = c.id

        LEFT JOIN sectors s
            ON bs.company_id = s.company_id

        ORDER BY
            bs.company_id,
            bs.year
    """

    rows = conn.execute(
        query
    ).fetchall()

    columns = [
        "company_id",
        "year",

        "equity_capital",
        "reserves",
        "borrowings",
        "investments",
        "total_assets",

        "sales",
        "operating_profit",
        "opm_percentage",
        "other_income",
        "interest",
        "net_profit",
        "eps",
        "dividend_payout",

        "operating_activity",
        "investing_activity",
        "financing_activity",

        "book_value",
        "source_roce",
        "source_roe",

        "broad_sector"
    ]

    return [
        dict(
            zip(
                columns,
                row
            )
        )
        for row in rows
    ]


# =========================================================
# BUILD COMPANY HISTORY
# =========================================================

def build_company_history(rows):

    history = defaultdict(list)

    for row in rows:

        history[
            row["company_id"]
        ].append(row)

    return history


# =========================================================
# CREATE FINANCIAL RATIOS TABLE
# =========================================================

def create_financial_ratios_table(conn):

    conn.execute(
        "DROP TABLE IF EXISTS financial_ratios"
    )

    conn.execute(
        """
        CREATE TABLE financial_ratios (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            company_id TEXT NOT NULL,
            year TEXT NOT NULL,

            broad_sector TEXT,

            net_profit_margin_pct REAL,

            operating_profit_margin_pct REAL,

            opm_mismatch_flag INTEGER,

            return_on_equity_pct REAL,

            return_on_capital_employed_pct REAL,

            return_on_assets_pct REAL,

            debt_to_equity REAL,

            high_leverage_flag INTEGER,

            interest_coverage REAL,

            icr_label TEXT,

            icr_warning_flag INTEGER,

            net_debt_cr REAL,

            asset_turnover REAL,

            free_cash_flow_cr REAL,

            capex_cr REAL,

            capex_intensity_pct REAL,

            capex_intensity_label TEXT,

            cfo_quality_score REAL,

            cfo_quality_label TEXT,

            fcf_conversion_rate REAL,

            capital_allocation_pattern TEXT,

            earnings_per_share REAL,

            book_value_per_share REAL,

            dividend_payout_ratio_pct REAL,

            total_debt_cr REAL,

            cash_from_operations_cr REAL,

            revenue_cagr_3yr REAL,

            revenue_cagr_3yr_flag TEXT,

            revenue_cagr_5yr REAL,

            revenue_cagr_5yr_flag TEXT,

            revenue_cagr_10yr REAL,

            revenue_cagr_10yr_flag TEXT,

            pat_cagr_3yr REAL,

            pat_cagr_3yr_flag TEXT,

            pat_cagr_5yr REAL,

            pat_cagr_5yr_flag TEXT,

            pat_cagr_10yr REAL,

            pat_cagr_10yr_flag TEXT,

            eps_cagr_3yr REAL,

            eps_cagr_3yr_flag TEXT,

            eps_cagr_5yr REAL,

            eps_cagr_5yr_flag TEXT,

            eps_cagr_10yr REAL,

            eps_cagr_10yr_flag TEXT,

            roce_benchmark_flag INTEGER,

            composite_quality_score REAL,

            UNIQUE(company_id, year)
        )
        """
    )

    conn.commit()


# =========================================================
# SAFE DIFFERENCE
# =========================================================

def percentage_difference(
    calculated,
    source
):

    if (
        calculated is None
        or source is None
    ):
        return None

    return abs(
        calculated - source
    )


# =========================================================
# ROCE SECTOR BENCHMARK
# =========================================================

def calculate_sector_roce_benchmark(
    rows
):

    financial_roce = []

    for row in rows:

        if (
            row["broad_sector"]
            == "Financials"
        ):

            operating_profit = (
                row["operating_profit"]
            )

            other_income = (
                row["other_income"]
            )

            equity = (
                row["equity_capital"]
            )

            reserves = (
                row["reserves"]
            )

            borrowings = (
                row["borrowings"]
            )

            roce = calculate_all_ratios(
                row["net_profit"],
                row["sales"],
                operating_profit,
                other_income,
                equity,
                reserves,
                borrowings,
                row["total_assets"],
                row["investments"],
                row["interest"],
                row["opm_percentage"],
                row["broad_sector"]
            )[
                "return_on_capital_employed_pct"
            ]

            if roce is not None:

                financial_roce.append(
                    roce
                )

    if not financial_roce:

        return None

    return sum(
        financial_roce
    ) / len(
        financial_roce
    )


# =========================================================
# COMPOSITE QUALITY SCORE
# =========================================================

def calculate_composite_quality_score(
    roe,
    roce,
    debt_to_equity,
    npm,
    cfo_quality_score
):

    score = 0.0

    components = 0

    if roe is not None:

        if roe > 15:

            score += 1

        components += 1

    if roce is not None:

        if roce > 10:

            score += 1

        components += 1

    if debt_to_equity is not None:

        if debt_to_equity < 1:

            score += 1

        components += 1

    if npm is not None:

        if npm > 10:

            score += 1

        components += 1

    if cfo_quality_score is not None:

        if cfo_quality_score > 1:

            score += 1

        components += 1

    if components == 0:

        return None

    return (
        score / components
    ) * 100


# =========================================================
# PROCESS ONE ROW
# =========================================================

def process_row(
    row,
    company_history,
    edge_cases
):

    ratios = calculate_all_ratios(

        row["net_profit"],

        row["sales"],

        row["operating_profit"],

        row["other_income"],

        row["equity_capital"],

        row["reserves"],

        row["borrowings"],

        row["total_assets"],

        row["investments"],

        row["interest"],

        row["opm_percentage"],

        row["broad_sector"]
    )


    # -----------------------------------------------------
    # CAGR
    # -----------------------------------------------------

    history = company_history[
        row["company_id"]
    ]

    revenue_cagr = calculate_revenue_cagr(
        history,
        row["year"]
    )

    pat_cagr = calculate_pat_cagr(
        history,
        row["year"]
    )

    eps_cagr = calculate_eps_cagr(
        history,
        row["year"]
    )


    # -----------------------------------------------------
    # CFO / PAT HISTORY
    # -----------------------------------------------------

    cfo_values = []

    pat_values = []

    for historical_row in history[-5:]:

        cfo = (
            historical_row[
                "operating_activity"
            ]
        )

        pat = (
            historical_row[
                "net_profit"
            ]
        )

        if (
            cfo is not None
            and pat is not None
        ):

            cfo_values.append(
                cfo
            )

            pat_values.append(
                pat
            )


    cfo_quality_score = None

    cfo_quality_label = None

    if cfo_values and pat_values:

        (
            cfo_quality_score,
            cfo_quality_label
        ) = calculate_cfo_quality_score(

            cfo_values,

            pat_values
        )


    # -----------------------------------------------------
    # CASH FLOW KPIs
    # -----------------------------------------------------

    cashflow = calculate_cashflow_kpis(

        row["operating_activity"],

        row["investing_activity"],

        row["financing_activity"],

        row["sales"],

        row["operating_profit"],

        cfo_values,

        pat_values
    )


    # -----------------------------------------------------
    # ROCE SOURCE CHECK
    # -----------------------------------------------------
    # -----------------------------------------------------
    # ROCE SOURCE CHECK
    # -----------------------------------------------------

    calculated_roce = ratios[
        "return_on_capital_employed_pct"
    ]

    source_roce = row[
        "source_roce"
    ]

    roce_difference = percentage_difference(
        calculated_roce,
        source_roce
    )

    if (
        roce_difference is not None
        and roce_difference > 5
    ):

        # Categorize ROCE difference
        if (
            calculated_roce is None
            or source_roce is None
        ):
            category = "DATA_SOURCE_ISSUE"

        elif (
            abs(source_roce) < 1
            and abs(calculated_roce) > 5
        ):
            category = "DATA_SOURCE_ISSUE"

        elif (
            roce_difference > 20
        ):
            category = "VERSION_DIFFERENCE"

        else:
            category = "FORMULA_DISCREPANCY"

        edge_cases.append(
            f"{row['company_id']} | "
            f"{row['year']} | "
            f"ROCE difference = "
            f"{roce_difference:.2f}% | "
            f"Category: {category}"
        )


    # -----------------------------------------------------
    # ROE SOURCE CHECK
    # -----------------------------------------------------

    calculated_roe = ratios[
        "return_on_equity_pct"
    ]

    source_roe = row[
        "source_roe"
    ]

    roe_difference = percentage_difference(
        calculated_roe,
        source_roe
    )

    if (
        roe_difference is not None
        and roe_difference > 5
    ):

        # Categorize ROE difference
        if (
            abs(source_roe) < 1
            and abs(calculated_roe) > 5
        ):
            category = "DATA_SOURCE_ISSUE"

        elif (
            roe_difference > 20
        ):
            category = "VERSION_DIFFERENCE"

        else:
            category = "FORMULA_DISCREPANCY"

        edge_cases.append(
            f"{row['company_id']} | "
            f"{row['year']} | "
            f"ROE difference = "
            f"{roe_difference:.2f}% | "
            f"Category: {category}"
        )

    # -----------------------------------------------------
    # SECTOR ROCE BENCHMARK
    # -----------------------------------------------------

    roce_benchmark_flag = 0

    if (
        row["broad_sector"]
        == "Financials"
    ):

        roce_benchmark_flag = 1


    # -----------------------------------------------------
    # BOOK VALUE PER SHARE
    # -----------------------------------------------------

    book_value_per_share = (
        row["book_value"]
    )


    # -----------------------------------------------------
    # COMPOSITE QUALITY
    # -----------------------------------------------------

    composite_quality_score = (
        calculate_composite_quality_score(

            ratios[
                "return_on_equity_pct"
            ],

            ratios[
                "return_on_capital_employed_pct"
            ],

            ratios[
                "debt_to_equity"
            ],

            ratios[
                "net_profit_margin_pct"
            ],

            cfo_quality_score
        )
    )


    return {

        "company_id":
            row["company_id"],

        "year":
            row["year"],

        "broad_sector":
            row["broad_sector"],

        **ratios,

        "free_cash_flow_cr":
            cashflow[
                "free_cash_flow"
            ],

        "capex_cr":
            (
                abs(
                    row[
                        "investing_activity"
                    ]
                )
                if row[
                    "investing_activity"
                ] is not None
                else None
            ),

        "capex_intensity_pct":
            cashflow[
                "capex_intensity_pct"
            ],

        "capex_intensity_label":
            cashflow[
                "capex_intensity_label"
            ],

        "cfo_quality_score":
            cfo_quality_score,

        "cfo_quality_label":
            cfo_quality_label,

        "fcf_conversion_rate":
            cashflow[
                "fcf_conversion_rate"
            ],

        "capital_allocation_pattern":
            cashflow[
                "capital_allocation_pattern"
            ],

        "earnings_per_share":
            row["eps"],

        "book_value_per_share":
            book_value_per_share,

        "dividend_payout_ratio_pct":
            row[
                "dividend_payout"
            ],

        "total_debt_cr":
            row[
                "borrowings"
            ],

        "cash_from_operations_cr":
            row[
                "operating_activity"
            ],

        "revenue_cagr_3yr":
            revenue_cagr[
                "sales_cagr_3yr"
            ],

        "revenue_cagr_3yr_flag":
            revenue_cagr[
                "sales_cagr_3yr_flag"
            ],

        "revenue_cagr_5yr":
            revenue_cagr[
                "sales_cagr_5yr"
            ],

        "revenue_cagr_5yr_flag":
            revenue_cagr[
                "sales_cagr_5yr_flag"
            ],

        "revenue_cagr_10yr":
            revenue_cagr[
                "sales_cagr_10yr"
            ],

        "revenue_cagr_10yr_flag":
            revenue_cagr[
                "sales_cagr_10yr_flag"
            ],

        "pat_cagr_3yr":
            pat_cagr[
                "net_profit_cagr_3yr"
            ],

        "pat_cagr_3yr_flag":
            pat_cagr[
                "net_profit_cagr_3yr_flag"
            ],

        "pat_cagr_5yr":
            pat_cagr[
                "net_profit_cagr_5yr"
            ],

        "pat_cagr_5yr_flag":
            pat_cagr[
                "net_profit_cagr_5yr_flag"
            ],

        "pat_cagr_10yr":
            pat_cagr[
                "net_profit_cagr_10yr"
            ],

        "pat_cagr_10yr_flag":
            pat_cagr[
                "net_profit_cagr_10yr_flag"
            ],

        "eps_cagr_3yr":
            eps_cagr[
                "eps_cagr_3yr"
            ],

        "eps_cagr_3yr_flag":
            eps_cagr[
                "eps_cagr_3yr_flag"
            ],

        "eps_cagr_5yr":
            eps_cagr[
                "eps_cagr_5yr"
            ],

        "eps_cagr_5yr_flag":
            eps_cagr[
                "eps_cagr_5yr_flag"
            ],

        "eps_cagr_10yr":
            eps_cagr[
                "eps_cagr_10yr"
            ],

        "eps_cagr_10yr_flag":
            eps_cagr[
                "eps_cagr_10yr_flag"
            ],

        "roce_benchmark_flag":
            roce_benchmark_flag,

        "composite_quality_score":
            composite_quality_score
    }


# =========================================================
# INSERT RESULTS
# =========================================================

def insert_results(
    conn,
    results
):

    columns = [

        "company_id",
        "year",
        "broad_sector",

        "net_profit_margin_pct",
        "operating_profit_margin_pct",
        "opm_mismatch_flag",

        "return_on_equity_pct",
        "return_on_capital_employed_pct",
        "return_on_assets_pct",

        "debt_to_equity",
        "high_leverage_flag",

        "interest_coverage",
        "icr_label",
        "icr_warning_flag",

        "net_debt_cr",
        "asset_turnover",

        "free_cash_flow_cr",
        "capex_cr",

        "capex_intensity_pct",
        "capex_intensity_label",

        "cfo_quality_score",
        "cfo_quality_label",

        "fcf_conversion_rate",

        "capital_allocation_pattern",

        "earnings_per_share",
        "book_value_per_share",
        "dividend_payout_ratio_pct",

        "total_debt_cr",
        "cash_from_operations_cr",

        "revenue_cagr_3yr",
        "revenue_cagr_3yr_flag",
        "revenue_cagr_5yr",
        "revenue_cagr_5yr_flag",
        "revenue_cagr_10yr",
        "revenue_cagr_10yr_flag",

        "pat_cagr_3yr",
        "pat_cagr_3yr_flag",
        "pat_cagr_5yr",
        "pat_cagr_5yr_flag",
        "pat_cagr_10yr",
        "pat_cagr_10yr_flag",

        "eps_cagr_3yr",
        "eps_cagr_3yr_flag",
        "eps_cagr_5yr",
        "eps_cagr_5yr_flag",
        "eps_cagr_10yr",
        "eps_cagr_10yr_flag",

        "roce_benchmark_flag",

        "composite_quality_score"
    ]


    placeholders = ", ".join(
        ["?"] * len(columns)
    )

    column_sql = ", ".join(
        columns
    )

    query = f"""
        INSERT OR REPLACE INTO
        financial_ratios
        ({column_sql})
        VALUES
        ({placeholders})
    """


    values = []

    for result in results:

        values.append(
            tuple(
                result.get(
                    column
                )
                for column in columns
            )
        )


    conn.executemany(
        query,
        values
    )

    conn.commit()


# =========================================================
# CAPITAL ALLOCATION CSV
# =========================================================

def create_capital_allocation_csv(
    results
):

    with open(
        CAPITAL_ALLOCATION_FILE,
        "w",
        newline="",
        encoding="utf-8"
    ) as file:

        writer = csv.writer(
            file
        )

        writer.writerow(
            [
                "company_id",
                "year",
                "cfo_sign",
                "cfi_sign",
                "cff_sign",
                "pattern_label"
            ]
        )


        for result in results:

            cfo = result.get(
                "cash_from_operations_cr"
            )

            cfi = result.get(
                "capex_cr"
            )

            pattern = result.get(
                "capital_allocation_pattern"
            )


            def sign(value):

                if value is None:
                    return None

                if value > 0:
                    return "+"

                if value < 0:
                    return "-"

                return "0"


            writer.writerow(
                [
                    result[
                        "company_id"
                    ],

                    result[
                        "year"
                    ],

                    sign(cfo),

                    sign(
                        -cfi
                        if cfi is not None
                        else None
                    ),

                    None,

                    pattern
                ]
            )


# =========================================================
# EDGE CASE LOG
# =========================================================

def write_edge_case_log(
    edge_cases
):

    with open(
        EDGE_CASE_LOG,
        "w",
        encoding="utf-8"
    ) as file:

        file.write(
            "SPRINT 2 RATIO EDGE CASE LOG\n"
        )

        file.write(
            "=" * 60
            + "\n\n"
        )

        if not edge_cases:

            file.write(
                "No ratio anomalies detected.\n"
            )

            return


        for item in edge_cases:

            file.write(
                item
                + "\n"
            )


# =========================================================
# VALIDATE DATABASE
# =========================================================

def validate_database(
    conn
):

    row_count = conn.execute(
        """
        SELECT COUNT(*)
        FROM financial_ratios
        """
    ).fetchone()[0]


    print(
        f"\nfinancial_ratios rows: "
        f"{row_count}"
    )


    required_columns = [

        "net_profit_margin_pct",

        "operating_profit_margin_pct",

        "return_on_equity_pct",

        "debt_to_equity",

        "interest_coverage",

        "asset_turnover",

        "free_cash_flow_cr",

        "capex_cr",

        "earnings_per_share",

        "book_value_per_share",

        "dividend_payout_ratio_pct",

        "total_debt_cr",

        "cash_from_operations_cr",

        "revenue_cagr_5yr",

        "pat_cagr_5yr",

        "eps_cagr_5yr",

        "composite_quality_score"
    ]


    print(
        "\nRequired KPI column validation:"
    )


    for column in required_columns:

        count = conn.execute(
            f"""
            SELECT COUNT(*)
            FROM financial_ratios
            WHERE "{column}" IS NOT NULL
            """
        ).fetchone()[0]


        status = (
            "OK"
            if count > 0
            else "NULL ONLY"
        )


        print(
            f"{column}: "
            f"{count} populated "
            f"[{status}]"
        )


# =========================================================
# MAIN PIPELINE
# =========================================================

def main():

    print(
        "\n"
        + "=" * 60
    )

    print(
        "SPRINT 2 - FINANCIAL RATIO ENGINE"
    )

    print(
        "=" * 60
    )


    create_output_directory()


    conn = get_connection()


    print(
        "\nLoading source data..."
    )


    rows = load_source_data(
        conn
    )


    print(
        f"Loaded {len(rows)} "
        f"company-year records."
    )


    if not rows:

        print(
            "ERROR: No source records found."
        )

        conn.close()

        return


    history = build_company_history(
        rows
    )


    print(
        "\nCreating financial_ratios table..."
    )


    create_financial_ratios_table(
        conn
    )


    edge_cases = []

    results = []


    print(
        "\nCalculating Sprint 2 KPIs..."
    )


    for index, row in enumerate(
        rows,
        start=1
    ):

        try:

            result = process_row(

                row,

                history,

                edge_cases
            )


            results.append(
                result
            )


        except Exception as error:

            edge_cases.append(

                f"{row['company_id']} | "
                f"{row['year']} | "
                f"Processing Error | "
                f"{type(error).__name__}: "
                f"{error}"
            )


        if index % 100 == 0:

            print(
                f"Processed "
                f"{index}/{len(rows)}"
            )


    print(
        f"\nSuccessfully calculated "
        f"{len(results)} records."
    )


    print(
        "\nInserting into financial_ratios..."
    )


    insert_results(

        conn,

        results
    )


    print(
        "Creating capital_allocation.csv..."
    )


    create_capital_allocation_csv(
        results
    )


    print(
        "Creating ratio_edge_cases.log..."
    )


    write_edge_case_log(
        edge_cases
    )


    print(
        "\nRunning database validation..."
    )


    validate_database(
        conn
    )


    conn.close()


    print(
        "\n"
        + "=" * 60
    )

    print(
        "SPRINT 2 PIPELINE COMPLETED"
    )

    print(
        "=" * 60
    )

    print(
        f"\nOutput files:"
    )

    print(
        f"  - {CAPITAL_ALLOCATION_FILE}"
    )

    print(
        f"  - {EDGE_CASE_LOG}"
    )

    print(
        f"  - db/nifty100.db"
    )

    print(
        "\nNext step:"
    )

    print(
        "Review the validation results above."
    )


if __name__ == "__main__":

    main()