"""ETL loader for the Nifty100 Financial Intelligence Platform.

Loads all 12 source Excel files (7 core + 5 supplementary), normalises
fields, applies dedup, and writes into nifty100.db (10 tables).
Generates output/load_audit.csv summarising the load.
"""

import os
import sqlite3
import sys
import time

import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))
from normaliser import normalize_year, normalize_ticker, PARSE_ERROR

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "nifty100_project"))
# Fallback for direct execution from project root
if not os.path.isdir(BASE_DIR):
    BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

DATA_RAW = os.path.join(BASE_DIR, "data", "raw")
DATA_SUPPORTING = os.path.join(BASE_DIR, "data", "supporting")
DB_PATH = os.path.join(BASE_DIR, "db", "nifty100.db")
SCHEMA_PATH = os.path.join(BASE_DIR, "db", "schema.sql")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")

CORE_SHEET_MAP = {
    "companies": "Companies",
    "profitandloss": "Profit & Loss",
    "balancesheet": "Balance Sheet",
    "cashflow": "Cash Flow",
    "analysis": "Analysis",
    "documents": "Documents",
    "prosandcons": "Pros & Cons",
}

audit_rows = []


def _audit(table, rows_in, rows_out, rejected, runtime_s):
    audit_rows.append({
        "table": table,
        "rows_in": rows_in,
        "rows_out": rows_out,
        "rejected": rejected,
        "timestamp": pd.Timestamp.now().isoformat(timespec="seconds"),
        "runtime_s": round(runtime_s, 3),
    })


def load_companies():
    t0 = time.time()
    path = os.path.join(DATA_RAW, "companies.xlsx")
    df = pd.read_excel(path, sheet_name=CORE_SHEET_MAP["companies"], header=1)
    rows_in = len(df)

    df["id"] = df["id"].apply(normalize_ticker)
    df["company_name"] = df["company_name"].astype(str).str.replace("\n", " ", regex=False).str.strip()

    rejected = int((df["id"] == "").sum())
    df = df[df["id"] != ""]
    df = df.drop_duplicates(subset=["id"], keep="last")

    _audit("companies", rows_in, len(df), rejected, time.time() - t0)
    return df


def load_timeseries(name, value_cols):
    """Generic loader for profitandloss / balancesheet / cashflow."""
    t0 = time.time()
    path = os.path.join(DATA_RAW, f"{name}.xlsx")
    df = pd.read_excel(path, sheet_name=CORE_SHEET_MAP[name], header=1)
    rows_in = len(df)

    df["company_id"] = df["company_id"].apply(normalize_ticker)
    df["year"] = df["year"].apply(normalize_year)

    rejected = 0
    bad_ticker = df["company_id"] == ""
    bad_year = df["year"] == PARSE_ERROR
    rejected_mask = bad_ticker | bad_year
    rejected = int(rejected_mask.sum())
    df = df[~rejected_mask].copy()

    # Dedup on (company_id, year): keep last occurrence
    before = len(df)
    df = df.drop_duplicates(subset=["company_id", "year"], keep="last")
    dup_dropped = before - len(df)

    _audit(name, rows_in, len(df), rejected + dup_dropped, time.time() - t0)
    return df


def load_analysis():
    t0 = time.time()
    path = os.path.join(DATA_RAW, "analysis.xlsx")
    df = pd.read_excel(path, sheet_name=CORE_SHEET_MAP["analysis"], header=1)
    rows_in = len(df)
    df["company_id"] = df["company_id"].apply(normalize_ticker)
    rejected = int((df["company_id"] == "").sum())
    df = df[df["company_id"] != ""]
    _audit("analysis", rows_in, len(df), rejected, time.time() - t0)
    return df


def load_documents():
    t0 = time.time()
    path = os.path.join(DATA_RAW, "documents.xlsx")
    df = pd.read_excel(path, sheet_name=CORE_SHEET_MAP["documents"], header=1)
    rows_in = len(df)
    df = df.rename(columns={"Year": "year", "Annual_Report": "annual_report"})
    df["company_id"] = df["company_id"].apply(normalize_ticker)
    rejected = int((df["company_id"] == "").sum())
    df = df[df["company_id"] != ""]
    _audit("documents", rows_in, len(df), rejected, time.time() - t0)
    return df


def load_prosandcons():
    t0 = time.time()
    path = os.path.join(DATA_RAW, "prosandcons.xlsx")
    df = pd.read_excel(path, sheet_name=CORE_SHEET_MAP["prosandcons"], header=1)
    rows_in = len(df)
    df["company_id"] = df["company_id"].apply(normalize_ticker)
    rejected = int((df["company_id"] == "").sum())
    df = df[df["company_id"] != ""]
    _audit("prosandcons", rows_in, len(df), rejected, time.time() - t0)
    return df


def load_supporting(name):
    """Generic loader for supplementary files (header=0, already clean)."""
    t0 = time.time()
    path = os.path.join(DATA_SUPPORTING, f"{name}.xlsx")
    df = pd.read_excel(path, sheet_name="Sheet1", header=0)
    rows_in = len(df)
    if "company_id" in df.columns:
        df["company_id"] = df["company_id"].apply(normalize_ticker)
        rejected = int((df["company_id"] == "").sum())
        df = df[df["company_id"] != ""]
    else:
        rejected = 0
    _audit(name, rows_in, len(df), rejected, time.time() - t0)
    return df


def build_database(valid_companies=None):
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = OFF")  # off during bulk load, verify after
    with open(SCHEMA_PATH, "r") as f:
        conn.executescript(f.read())

    # --- Core files ---
    companies_df = load_companies()
    companies_df.to_sql("companies", conn, if_exists="append", index=False)
    valid_ids = set(companies_df["id"])

    pl_df = load_timeseries("profitandloss", None)
    pl_df = _enforce_fk(pl_df, valid_ids, "profitandloss")
    pl_df.to_sql("profitandloss", conn, if_exists="append", index=False)

    bs_df = load_timeseries("balancesheet", None)
    bs_df = _enforce_fk(bs_df, valid_ids, "balancesheet")
    bs_df.to_sql("balancesheet", conn, if_exists="append", index=False)

    cf_df = load_timeseries("cashflow", None)
    cf_df = _enforce_fk(cf_df, valid_ids, "cashflow")
    cf_df.to_sql("cashflow", conn, if_exists="append", index=False)

    an_df = load_analysis()
    an_df = _enforce_fk(an_df, valid_ids, "analysis")
    an_df.to_sql("analysis", conn, if_exists="append", index=False)

    doc_df = load_documents()
    doc_df = _enforce_fk(doc_df, valid_ids, "documents")
    doc_df.to_sql("documents", conn, if_exists="append", index=False)

    pc_df = load_prosandcons()
    pc_df = _enforce_fk(pc_df, valid_ids, "prosandcons")
    pc_df.to_sql("prosandcons", conn, if_exists="append", index=False)

    # --- Supplementary files ---
    sectors_df = load_supporting("sectors")
    sectors_df = _enforce_fk(sectors_df, valid_ids, "sectors")
    sectors_df.to_sql("sectors", conn, if_exists="append", index=False)

    sp_df = load_supporting("stock_prices")
    sp_df = _enforce_fk(sp_df, valid_ids, "stock_prices")
    sp_df.to_sql("stock_prices", conn, if_exists="append", index=False)

    mc_df = load_supporting("market_cap")
    mc_df = _enforce_fk(mc_df, valid_ids, "market_cap")
    mc_df.to_sql("market_cap", conn, if_exists="append", index=False)

    conn.commit()

    # Re-enable FK and verify
    conn.execute("PRAGMA foreign_keys = ON")
    fk_check = conn.execute("PRAGMA foreign_key_check").fetchall()
    conn.close()

    # Write load_audit.csv
    audit_df = pd.DataFrame(audit_rows)
    audit_df.to_csv(os.path.join(OUTPUT_DIR, "load_audit.csv"), index=False)

    return audit_df, fk_check


def _enforce_fk(df, valid_ids, table_name):
    """Drop rows whose company_id is not in the companies table; log to audit."""
    before = len(df)
    mask = df["company_id"].isin(valid_ids)
    dropped = before - int(mask.sum())
    if dropped > 0:
        # update the audit row's rejected count for this table
        for row in audit_rows:
            if row["table"] == table_name:
                row["rejected"] += dropped
                row["rows_out"] = row["rows_out"] - dropped
                break
    return df[mask].copy()


if __name__ == "__main__":
    audit_df, fk_check = build_database()
    print(audit_df.to_string(index=False))
    print(f"\nForeign key check violations: {len(fk_check)}")
    if fk_check:
        print(fk_check)
    print(f"\nDatabase written to: {DB_PATH}")
