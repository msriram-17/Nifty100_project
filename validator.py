"""Data Quality Validator - implements DQ-01 through DQ-16.

Runs against the loaded nifty100.db and produces output/validation_failures.csv
with columns: rule_id, table, company_id, year, field, issue, severity.
"""

import os
import sqlite3

import pandas as pd

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DB_PATH = os.path.join(BASE_DIR, "db", "nifty100.db")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")

failures = []


def _flag(rule_id, table, company_id, year, field, issue, severity):
    failures.append({
        "rule_id": rule_id, "table": table, "company_id": company_id,
        "year": year, "field": field, "issue": issue, "severity": severity,
    })


def run_validation(conn):
    companies = pd.read_sql("SELECT * FROM companies", conn)
    pl = pd.read_sql("SELECT * FROM profitandloss", conn)
    bs = pd.read_sql("SELECT * FROM balancesheet", conn)
    cf = pd.read_sql("SELECT * FROM cashflow", conn)
    docs = pd.read_sql("SELECT * FROM documents", conn)

    # DQ-01: Company PK uniqueness
    if len(companies) != companies["id"].nunique():
        _flag("DQ-01", "companies", None, None, "id",
              "Duplicate company id found", "CRITICAL")

    # DQ-02: Annual PK uniqueness (already enforced by loader dedup, verify here)
    for name, df in [("profitandloss", pl), ("balancesheet", bs), ("cashflow", cf)]:
        dup = df.duplicated(subset=["company_id", "year"]).sum()
        if dup > 0:
            _flag("DQ-02", name, None, None, "company_id,year",
                  f"{dup} duplicate (company_id, year) pairs remain", "CRITICAL")

    # DQ-03: FK Integrity (already enforced at load; verify with PRAGMA)
    fk_violations = conn.execute("PRAGMA foreign_key_check").fetchall()
    if fk_violations:
        for v in fk_violations:
            _flag("DQ-03", v[0], None, None, "company_id",
                  f"Orphan row referencing rowid {v[1]}", "CRITICAL")

    # DQ-04: Balance Sheet Balance — |assets - liabilities| / assets < 1%
    bs_chk = bs.copy()
    bs_chk["diff_pct"] = (bs_chk["total_assets"] - bs_chk["total_liabilities"]).abs() / bs_chk["total_assets"].replace(0, pd.NA)
    bad = bs_chk[bs_chk["diff_pct"] >= 0.01]
    for _, r in bad.iterrows():
        _flag("DQ-04", "balancesheet", r["company_id"], r["year"],
              "total_assets/total_liabilities",
              f"BS imbalance {r['diff_pct']*100:.2f}%", "WARNING")

    # DQ-05: OPM cross-check — |opm - (op_profit/sales*100)| < 1.0
    pl_chk = pl.copy()
    pl_chk["computed_opm"] = pl_chk["operating_profit"] / pl_chk["sales"].replace(0, pd.NA) * 100
    pl_chk["opm_diff"] = (pl_chk["opm_percentage"] - pl_chk["computed_opm"]).abs()
    bad = pl_chk[pl_chk["opm_diff"] >= 1.0]
    for _, r in bad.iterrows():
        _flag("DQ-05", "profitandloss", r["company_id"], r["year"],
              "opm_percentage", f"OPM mismatch: source={r['opm_percentage']}, computed={r['computed_opm']:.2f}", "WARNING")

    # DQ-06: Positive Sales
    bad = pl[pl["sales"] <= 0]
    for _, r in bad.iterrows():
        _flag("DQ-06", "profitandloss", r["company_id"], r["year"],
              "sales", f"Non-positive sales: {r['sales']}", "WARNING")

    # DQ-07: Year format (post-normalisation, should already match YYYY-MM)
    import re
    pattern = re.compile(r"^\d{4}-\d{2}$")
    for name, df in [("profitandloss", pl), ("balancesheet", bs), ("cashflow", cf)]:
        bad = df[~df["year"].astype(str).str.match(pattern)]
        for _, r in bad.iterrows():
            _flag("DQ-07", name, r["company_id"], r["year"],
                  "year", f"Year not in YYYY-MM format: {r['year']}", "CRITICAL")

    # DQ-08: Ticker format — already normalised at load; verify length 2-12
    bad = companies[~companies["id"].str.len().between(2, 12)]
    for _, r in bad.iterrows():
        _flag("DQ-08", "companies", r["id"], None, "id",
              f"Ticker length out of range: {r['id']}", "CRITICAL")

    # DQ-09: Net cash check — |net_cash_flow - (CFO+CFI+CFF)| <= 10 Cr
    cf_chk = cf.copy()
    cf_chk["computed_net"] = cf_chk["operating_activity"] + cf_chk["investing_activity"] + cf_chk["financing_activity"]
    cf_chk["diff"] = (cf_chk["net_cash_flow"] - cf_chk["computed_net"]).abs()
    bad = cf_chk[cf_chk["diff"] > 10]
    for _, r in bad.iterrows():
        _flag("DQ-09", "cashflow", r["company_id"], r["year"],
              "net_cash_flow", f"Net cash mismatch by {r['diff']:.1f} Cr", "WARNING")

    # DQ-10: Non-negative fixed assets
    bad = bs[bs["fixed_assets"] < 0]
    for _, r in bad.iterrows():
        _flag("DQ-10", "balancesheet", r["company_id"], r["year"],
              "fixed_assets", f"Negative fixed_assets: {r['fixed_assets']}", "WARNING")

    # DQ-11: Tax rate range 0-60
    bad = pl[~pl["tax_percentage"].between(0, 60) & pl["tax_percentage"].notna()]
    for _, r in bad.iterrows():
        _flag("DQ-11", "profitandloss", r["company_id"], r["year"],
              "tax_percentage", f"Tax rate out of range: {r['tax_percentage']}", "WARNING")

    # DQ-12: Dividend payout cap <= 200
    bad = pl[pl["dividend_payout"] > 200]
    for _, r in bad.iterrows():
        _flag("DQ-12", "profitandloss", r["company_id"], r["year"],
              "dividend_payout", f"Dividend payout >200%: {r['dividend_payout']}", "WARNING")

    # DQ-13: URL validity (documents) — SKIPPED (no network calls in this offline run);
    # flagged as informational placeholder so the rule is visible in the report.
    null_urls = docs[docs["annual_report"].isna() | (docs["annual_report"] == "")]
    for _, r in null_urls.iterrows():
        _flag("DQ-13", "documents", r["company_id"], r["year"],
              "annual_report", "Missing/blank URL (live HTTP check not run offline)", "WARNING")

    # DQ-14: EPS sign consistency — eps > 0 if net_profit > 0
    bad = pl[(pl["net_profit"] > 0) & (pl["eps"] <= 0) & pl["eps"].notna()]
    for _, r in bad.iterrows():
        _flag("DQ-14", "profitandloss", r["company_id"], r["year"],
              "eps", f"EPS<=0 but net_profit>0: eps={r['eps']}, net_profit={r['net_profit']}", "WARNING")

    # DQ-15: Strict BS balance (informational, post DQ-04)
    strict_bad = bs[bs["total_assets"] != bs["total_liabilities"]]
    _flag("DQ-15", "balancesheet", None, None, "total_assets/total_liabilities",
          f"{len(strict_bad)} rows not exactly balanced (informational only)", "INFO")

    # DQ-16: Coverage check — each company should have >= 5 years
    for name, df in [("profitandloss", pl), ("balancesheet", bs), ("cashflow", cf)]:
        coverage = df.groupby("company_id")["year"].nunique()
        low = coverage[coverage < 5]
        for cid, n in low.items():
            _flag("DQ-16", name, cid, None, "year",
                  f"Only {n} year(s) of coverage (<5)", "WARNING")

    return pd.DataFrame(failures)


if __name__ == "__main__":
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    df = run_validation(conn)
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    df.to_csv(os.path.join(OUTPUT_DIR, "validation_failures.csv"), index=False)
    conn.close()

    print(f"Total DQ violations: {len(df)}")
    if len(df):
        print(df["severity"].value_counts())
        print("\nCRITICAL failures:")
        print(df[df["severity"] == "CRITICAL"])
