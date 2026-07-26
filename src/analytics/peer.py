"""
Sprint 3 - Peer Percentile Ranking Engine

Calculates percentile rankings for 10 metrics across all peer groups.

Important:
The financial_ratios table may contain a recent period such as 2024-09
with NULL KPI values. Therefore, this engine selects the latest
AVAILABLE non-null value for EACH metric separately.

D/E is inverted:
Lower D/E = Better = Higher percentile.
"""

from pathlib import Path
import sqlite3
import numpy as np
import pandas as pd


# ============================================================
# PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

DB_PATH = PROJECT_ROOT / "db" / "nifty100.db"

PEER_GROUPS_PATH = (
    PROJECT_ROOT
    / "Data"
    / "supporting"
    / "peer_groups.xlsx"
)


# ============================================================
# METRICS
# ============================================================

METRICS = {
    "ROE": "return_on_equity_pct",
    "ROCE": "return_on_capital_employed_pct",
    "Net Profit Margin": "net_profit_margin_pct",
    "D/E": "debt_to_equity",
    "FCF": "free_cash_flow_cr",
    "PAT CAGR 5yr": "pat_cagr_5yr",
    "Revenue CAGR 5yr": "revenue_cagr_5yr",
    "EPS CAGR 5yr": "eps_cagr_5yr",
    "Interest Coverage": "interest_coverage",
    "Asset Turnover": "asset_turnover",
}


# ============================================================
# DATABASE
# ============================================================

def get_connection():
    return sqlite3.connect(DB_PATH)


def create_peer_percentiles_table(conn):
    """
    Create peer_percentiles table.
    """

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS peer_percentiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id TEXT NOT NULL,
            peer_group_name TEXT NOT NULL,
            metric TEXT NOT NULL,
            value REAL,
            percentile_rank REAL,
            year TEXT,
            UNIQUE(
                company_id,
                peer_group_name,
                metric,
                year
            )
        )
        """
    )

    conn.commit()


# ============================================================
# LOAD PEER GROUPS
# ============================================================

def load_peer_groups():
    """
    Load peer group assignments.

    Required columns:
        peer_group_name
        company_id
        is_benchmark
    """

    if not PEER_GROUPS_PATH.exists():
        raise FileNotFoundError(
            f"Peer groups file not found: {PEER_GROUPS_PATH}"
        )

    df = pd.read_excel(
        PEER_GROUPS_PATH
    )

    required = {
        "peer_group_name",
        "company_id",
        "is_benchmark",
    }

    missing = required - set(df.columns)

    if missing:
        raise ValueError(
            f"Missing columns: {sorted(missing)}"
        )

    df["company_id"] = (
        df["company_id"]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    df["peer_group_name"] = (
        df["peer_group_name"]
        .astype(str)
        .str.strip()
    )

    return df


# ============================================================
# LOAD FINANCIAL DATA
# ============================================================

def load_financial_data(conn):
    """
    Load all required metrics from financial_ratios.
    """

    columns = [
        "company_id",
        "year",
        *METRICS.values(),
    ]

    query = f"""
        SELECT
            {", ".join(columns)}
        FROM financial_ratios
    """

    df = pd.read_sql_query(
        query,
        conn
    )

    df["company_id"] = (
        df["company_id"]
        .astype(str)
        .str.strip()
        .str.upper()
    )

    # Convert all metric columns to numeric
    for column in METRICS.values():

        df[column] = pd.to_numeric(
            df[column],
            errors="coerce"
        )

    return df


# ============================================================
# YEAR SORTING
# ============================================================

def add_year_sort_column(df):
    """
    Convert year strings into sortable dates.

    Example:
        2024-09
        2024-03
        2023-03
    """

    result = df.copy()

    result["_year_sort"] = pd.to_datetime(
        result["year"],
        format="%Y-%m",
        errors="coerce"
    )

    return result


# ============================================================
# LATEST AVAILABLE VALUE PER METRIC
# ============================================================

def select_latest_available_values(
    financial_df
):
    """
    For each company and EACH metric, select the latest
    non-null value.

    This is the key fix.

    Example:

    MARUTI:

    2024-09:
        ROE = NULL

    2024-03:
        ROE = 15.75

    Result:

        ROE = 15.75
        year = 2024-03

    The same logic is applied independently to every metric.
    """

    df = add_year_sort_column(
        financial_df
    )

    results = []

    for company_id, company_df in df.groupby(
        "company_id",
        sort=False
    ):

        company_df = company_df.sort_values(
            "_year_sort",
            ascending=False
        )

        for metric_name, column in METRICS.items():

            valid = company_df[
                company_df[column].notna()
            ]

            if valid.empty:
                continue

            latest = valid.iloc[0]

            results.append(
                {
                    "company_id": company_id,
                    "metric": metric_name,
                    "value": float(
                        latest[column]
                    ),
                    "year": latest["year"],
                }
            )

    if not results:
        return pd.DataFrame(
            columns=[
                "company_id",
                "metric",
                "value",
                "year",
            ]
        )

    return pd.DataFrame(
        results
    )


# ============================================================
# PERCENTILE CALCULATION
# ============================================================

def calculate_percentile(
    series
):
    """
    Calculate percentile rank from 0 to 100.

    Highest value receives highest percentile.

    For a single valid value:
        100 percentile.
    """

    values = pd.to_numeric(
        series,
        errors="coerce"
    )

    result = pd.Series(
        np.nan,
        index=series.index,
        dtype=float
    )

    valid = values.notna()

    count = valid.sum()

    if count == 0:
        return result

    if count == 1:

        result.loc[valid] = 100.0

        return result

    ranks = (
        values.loc[valid]
        .rank(
            method="average",
            pct=True
        )
        * 100
    )

    result.loc[valid] = ranks

    return result


# ============================================================
# COMPUTE PEER PERCENTILES
# ============================================================

def compute_peer_percentiles(
    financial_df,
    peer_df
):
    """
    Compute percentile ranks within each peer group.

    D/E:
        Lower value = Better.
        Therefore percentile is inverted.
    """

    latest_values = (
        select_latest_available_values(
            financial_df
        )
    )

    if latest_values.empty:
        return pd.DataFrame(
            columns=[
                "company_id",
                "peer_group_name",
                "metric",
                "value",
                "percentile_rank",
                "year",
            ]
        )

    # Join peer groups with latest available metrics
    merged = peer_df.merge(
        latest_values,
        on="company_id",
        how="left"
    )

    results = []

    for peer_group_name, group in merged.groupby(
        "peer_group_name",
        sort=True
    ):

        for metric_name in METRICS:

            metric_data = group[
                group["metric"]
                == metric_name
            ].copy()

            if metric_data.empty:
                continue

            percentile = calculate_percentile(
                metric_data["value"]
            )

            # ----------------------------------------------
            # D/E INVERSE RANKING
            # ----------------------------------------------

            if metric_name == "D/E":

                percentile = (
                    100 - percentile
                )

                percentile.loc[
                    metric_data["value"].isna()
                ] = np.nan

            metric_data[
                "percentile_rank"
            ] = percentile.values

            metric_data[
                "peer_group_name"
            ] = peer_group_name

            results.append(
                metric_data[
                    [
                        "company_id",
                        "peer_group_name",
                        "metric",
                        "value",
                        "percentile_rank",
                        "year",
                    ]
                ]
            )

    if not results:

        return pd.DataFrame(
            columns=[
                "company_id",
                "peer_group_name",
                "metric",
                "value",
                "percentile_rank",
                "year",
            ]
        )

    result = pd.concat(
        results,
        ignore_index=True
    )

    return result


# ============================================================
# SAVE TO DATABASE
# ============================================================

def save_peer_percentiles(
    conn,
    percentile_df
):
    """
    Replace old peer percentile results
    with newly calculated results.
    """

    create_peer_percentiles_table(
        conn
    )

    # Clear old incorrect results
    conn.execute(
        "DELETE FROM peer_percentiles"
    )

    if percentile_df.empty:

        conn.commit()

        print(
            "WARNING: No peer percentile data."
        )

        return

    records = []

    for _, row in percentile_df.iterrows():

        value = (
            None
            if pd.isna(row["value"])
            else float(row["value"])
        )

        percentile = (
            None
            if pd.isna(
                row["percentile_rank"]
            )
            else float(
                row["percentile_rank"]
            )
        )

        year = (
            None
            if pd.isna(row["year"])
            else str(row["year"])
        )

        records.append(
            (
                str(row["company_id"]),
                str(
                    row["peer_group_name"]
                ),
                str(row["metric"]),
                value,
                percentile,
                year,
            )
        )

    conn.executemany(
        """
        INSERT INTO peer_percentiles
        (
            company_id,
            peer_group_name,
            metric,
            value,
            percentile_rank,
            year
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        records
    )

    conn.commit()

    print(
        f"Saved {len(records)} peer percentile records."
    )


# ============================================================
# FIND UNASSIGNED COMPANIES
# ============================================================

def find_unassigned_companies(
    financial_df,
    peer_df
):
    """
    Find companies without peer group.

    No error is raised.
    """

    all_companies = set(
        financial_df[
            "company_id"
        ]
        .dropna()
        .unique()
    )

    assigned_companies = set(
        peer_df[
            "company_id"
        ]
        .dropna()
        .unique()
    )

    return sorted(
        all_companies
        - assigned_companies
    )


# ============================================================
# VALIDATE PEER GROUP
# ============================================================

def validate_peer_rankings(
    percentile_df,
    peer_group_name
):
    """
    Validate ROE ranking.

    Highest ROE should have highest ROE percentile.
    """

    subset = percentile_df[
        (
            percentile_df[
                "peer_group_name"
            ]
            == peer_group_name
        )
        &
        (
            percentile_df[
                "metric"
            ]
            == "ROE"
        )
    ].copy()

    subset = subset.dropna(
        subset=[
            "value",
            "percentile_rank",
        ]
    )

    print(
        f"\n{peer_group_name} ROE Validation"
    )

    if subset.empty:

        print(
            "No valid ROE data."
        )

        return

    highest_roe = subset.loc[
        subset["value"].idxmax()
    ]

    highest_percentile = subset.loc[
        subset[
            "percentile_rank"
        ].idxmax()
    ]

    print(
        f"Highest ROE: "
        f"{highest_roe['company_id']} "
        f"= "
        f"{highest_roe['value']:.2f}"
    )

    print(
        f"Highest ROE percentile: "
        f"{highest_percentile['company_id']} "
        f"= "
        f"{highest_percentile['percentile_rank']:.2f}"
    )

    if (
        highest_roe["company_id"]
        == highest_percentile[
            "company_id"
        ]
    ):

        print(
            "PASS: Highest ROE has highest percentile."
        )

    else:

        print(
            "FAIL: ROE ranking mismatch."
        )


# ============================================================
# MAIN
# ============================================================

def run_peer_engine():

    print("=" * 60)

    print(
        "SPRINT 3 PEER PERCENTILE ENGINE"
    )

    print("=" * 60)

    # --------------------------------------------------------
    # LOAD PEER GROUPS
    # --------------------------------------------------------

    peer_df = load_peer_groups()

    print(
        f"\nPeer groups loaded: "
        f"{peer_df['peer_group_name'].nunique()}"
    )

    print(
        f"Peer assignments: "
        f"{len(peer_df)}"
    )

    # --------------------------------------------------------
    # DATABASE
    # --------------------------------------------------------

    conn = get_connection()

    try:

        # ----------------------------------------------------
        # LOAD FINANCIAL DATA
        # ----------------------------------------------------

        financial_df = load_financial_data(
            conn
        )

        print(
            f"Financial records loaded: "
            f"{len(financial_df)}"
        )

        # ----------------------------------------------------
        # FIND UNASSIGNED
        # ----------------------------------------------------

        unassigned = (
            find_unassigned_companies(
                financial_df,
                peer_df
            )
        )

        print(
            f"\nCompanies without peer group: "
            f"{len(unassigned)}"
        )

        if unassigned:

            print(
                "No peer group assigned:"
            )

            print(
                ", ".join(
                    unassigned
                )
            )

        # ----------------------------------------------------
        # CALCULATE
        # ----------------------------------------------------

        print(
            "\nCalculating peer percentile rankings..."
        )

        percentile_df = (
            compute_peer_percentiles(
                financial_df,
                peer_df
            )
        )

        print(
            f"Percentile records generated: "
            f"{len(percentile_df)}"
        )

        # ----------------------------------------------------
        # SAVE
        # ----------------------------------------------------

        save_peer_percentiles(
            conn,
            percentile_df
        )

        # ----------------------------------------------------
        # GROUP SUMMARY
        # ----------------------------------------------------

        print(
            "\nPeer Group Summary"
        )

        print(
            "-" * 60
        )

        summary = (
            percentile_df
            .groupby(
                "peer_group_name"
            )
            ["company_id"]
            .nunique()
            .sort_values(
                ascending=False
            )
        )

        for group_name, count in summary.items():

            print(
                f"{group_name}: "
                f"{count} companies"
            )

        # ----------------------------------------------------
        # VALIDATIONS
        # ----------------------------------------------------

        validate_peer_rankings(
            percentile_df,
            "IT Services"
        )

        validate_peer_rankings(
            percentile_df,
            "FMCG"
        )

        # ----------------------------------------------------
        # SAMPLE
        # ----------------------------------------------------

        print(
            "\nSample Results"
        )

        print(
            "-" * 60
        )

        print(
            percentile_df
            .head(20)
            .to_string(
                index=False
            )
        )

        # ----------------------------------------------------
        # DATABASE COUNT
        # ----------------------------------------------------

        db_count = conn.execute(
            """
            SELECT COUNT(*)
            FROM peer_percentiles
            """
        ).fetchone()[0]

        # ----------------------------------------------------
        # NON-NULL COUNT
        # ----------------------------------------------------

        non_null_count = conn.execute(
            """
            SELECT COUNT(*)
            FROM peer_percentiles
            WHERE value IS NOT NULL
            AND percentile_rank IS NOT NULL
            """
        ).fetchone()[0]

        # ----------------------------------------------------
        # FINAL
        # ----------------------------------------------------

        print(
            "\n" + "=" * 60
        )

        print(
            "PEER ENGINE COMPLETED"
        )

        print(
            f"Database records: "
            f"{db_count}"
        )

        print(
            f"Valid percentile records: "
            f"{non_null_count}"
        )

        print(
            f"Peer groups: "
            f"{peer_df['peer_group_name'].nunique()}"
        )

        print(
            f"Metrics: "
            f"{len(METRICS)}"
        )

        print(
            "=" * 60
        )

    finally:

        conn.close()


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    run_peer_engine()