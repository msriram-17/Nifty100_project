import sqlite3

DB_PATH = "db/nifty100.db"


def main():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    print("=" * 60)
    print("SPRINT 2 - DATABASE CHECK")
    print("=" * 60)

    # 1. Check companies
    companies = cursor.execute(
        "SELECT COUNT(*) FROM companies"
    ).fetchone()[0]

    print("\nCompanies:", companies)

    # 2. Check Profit & Loss rows
    pnl = cursor.execute(
        "SELECT COUNT(*) FROM profitandloss"
    ).fetchone()[0]

    print("Profit & Loss rows:", pnl)

    # 3. Check Balance Sheet rows
    balance = cursor.execute(
        "SELECT COUNT(*) FROM balancesheet"
    ).fetchone()[0]

    print("Balance Sheet rows:", balance)

    # 4. Check Cash Flow rows
    cashflow = cursor.execute(
        "SELECT COUNT(*) FROM cashflow"
    ).fetchone()[0]

    print("Cash Flow rows:", cashflow)

    # 5. Check Sector rows
    sectors = cursor.execute(
        "SELECT COUNT(*) FROM sectors"
    ).fetchone()[0]

    print("Sector rows:", sectors)

    # 6. Check financial years
    years = cursor.execute("""
        SELECT MIN(year), MAX(year), COUNT(DISTINCT year)
        FROM profitandloss
    """).fetchone()

    print("\nFinancial Data:")
    print("First year:", years[0])
    print("Last year:", years[1])
    print("Number of years:", years[2])

    # 7. Check Financials sector
    financials = cursor.execute("""
        SELECT COUNT(*)
        FROM sectors
        WHERE LOWER(broad_sector) = 'financials'
    """).fetchone()[0]

    print("\nFinancials sector companies:", financials)

    # 8. Check important missing values
    print("\nMissing Values:")

    checks = {
        "Sales": "SELECT COUNT(*) FROM profitandloss WHERE sales IS NULL",
        "Net Profit": "SELECT COUNT(*) FROM profitandloss WHERE net_profit IS NULL",
        "Operating Profit": "SELECT COUNT(*) FROM profitandloss WHERE operating_profit IS NULL",
        "Interest": "SELECT COUNT(*) FROM profitandloss WHERE interest IS NULL",
        "Total Assets": "SELECT COUNT(*) FROM balancesheet WHERE total_assets IS NULL",
        "Borrowings": "SELECT COUNT(*) FROM balancesheet WHERE borrowings IS NULL",
        "CFO": "SELECT COUNT(*) FROM cashflow WHERE operating_activity IS NULL",
    }

    for name, query in checks.items():
        result = cursor.execute(query).fetchone()[0]
        print(f"{name}: {result}")

    conn.close()

    print("\n" + "=" * 60)
    print("DATABASE CHECK COMPLETED")
    print("=" * 60)


if __name__ == "__main__":
    main()