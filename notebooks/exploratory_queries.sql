-- exploratory_queries.sql
-- Sprint 1 Day 07 — Exploratory queries for sprint review / sanity checks
-- Run with: sqlite3 db/nifty100.db < notebooks/exploratory_queries.sql

-- 1. Row counts per table (sanity check against load_audit.csv)
SELECT 'companies' AS tbl, COUNT(*) AS rows FROM companies
UNION ALL SELECT 'profitandloss', COUNT(*) FROM profitandloss
UNION ALL SELECT 'balancesheet', COUNT(*) FROM balancesheet
UNION ALL SELECT 'cashflow', COUNT(*) FROM cashflow
UNION ALL SELECT 'analysis', COUNT(*) FROM analysis
UNION ALL SELECT 'documents', COUNT(*) FROM documents
UNION ALL SELECT 'prosandcons', COUNT(*) FROM prosandcons
UNION ALL SELECT 'sectors', COUNT(*) FROM sectors
UNION ALL SELECT 'stock_prices', COUNT(*) FROM stock_prices
UNION ALL SELECT 'market_cap', COUNT(*) FROM market_cap;

-- 2. Companies with fewer than 5 years of P&L history (coverage gap — DQ-16)
SELECT company_id, COUNT(DISTINCT year) AS years_covered
FROM profitandloss
GROUP BY company_id
HAVING years_covered < 5
ORDER BY years_covered ASC;

-- 3. Year coverage range per company (earliest / latest year on file)
SELECT company_id, MIN(year) AS earliest_year, MAX(year) AS latest_year,
       COUNT(DISTINCT year) AS num_years
FROM profitandloss
GROUP BY company_id
ORDER BY num_years ASC;

-- 4. Null / missing-value audit across companies table (key display fields)
SELECT
    SUM(CASE WHEN website IS NULL THEN 1 ELSE 0 END) AS missing_website,
    SUM(CASE WHEN about_company IS NULL THEN 1 ELSE 0 END) AS missing_about,
    SUM(CASE WHEN book_value IS NULL THEN 1 ELSE 0 END) AS missing_book_value
FROM companies;

-- 5. Companies present in profitandloss but missing from companies master (orphan check)
--    Should return 0 rows post-load (FK enforcement already strips these,
--    this query is a defensive re-check directly against raw distinct ids)
SELECT DISTINCT p.company_id
FROM profitandloss p
LEFT JOIN companies c ON p.company_id = c.id
WHERE c.id IS NULL;

-- 6. Sector distribution — number of companies per broad sector
SELECT broad_sector, COUNT(*) AS company_count
FROM sectors
GROUP BY broad_sector
ORDER BY company_count DESC;

-- 7. Balance sheet imbalance check (DQ-04 spot-check): top 10 worst mismatches
SELECT company_id, year, total_assets, total_liabilities,
       ROUND(ABS(total_assets - total_liabilities) * 100.0 / total_assets, 2) AS pct_diff
FROM balancesheet
WHERE total_assets > 0
ORDER BY pct_diff DESC
LIMIT 10;

-- 8. Companies with negative net_profit in latest available year
SELECT company_id, year, net_profit
FROM profitandloss
WHERE year = (SELECT MAX(year) FROM profitandloss p2 WHERE p2.company_id = profitandloss.company_id)
  AND net_profit < 0;

-- 9. Stock price record count per company (should be ~60 each for 5yr monthly)
SELECT company_id, COUNT(*) AS price_records
FROM stock_prices
GROUP BY company_id
HAVING price_records <> 60
ORDER BY price_records ASC;

-- 10. Documents with missing or blank annual report URLs (DQ-13 related)
SELECT company_id, COUNT(*) AS missing_url_count
FROM documents
WHERE annual_report IS NULL OR TRIM(annual_report) = ''
GROUP BY company_id
ORDER BY missing_url_count DESC;
