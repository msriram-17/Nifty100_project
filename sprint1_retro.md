# Sprint 1 Retrospective — Data Foundation & ETL

**Sprint:** Days 01-07 | **Completed:** 2 days (June 20-21, 2026) — compressed timeline
**Author:** Sriram

## What was delivered

- `nifty100.db` — 10-table SQLite database (companies, profitandloss, balancesheet,
  cashflow, analysis, documents, prosandcons, sectors, stock_prices, market_cap)
- `db/schema.sql` — full schema with PK/FK constraints
- `src/etl/loader.py`, `validator.py`, `normaliser.py`
- `output/load_audit.csv` — per-table load statistics
- `output/validation_failures.csv` — 372 DQ violations logged (0 CRITICAL)
- `tests/etl/test_normalise.py` — 35 unit tests, all passing
- `notebooks/exploratory_queries.sql` — 10 queries

## Exit criteria check

| Criterion | Result |
|---|---|
| `SELECT COUNT(*) FROM companies` = 92 | ✅ Pass |
| `PRAGMA foreign_key_check` → 0 rows | ✅ Pass |
| `load_audit.csv` → zero CRITICAL rejections | ✅ Pass |
| 35+ ETL unit tests pass | ✅ Pass (35/35) |
| Manual review: 5 companies correct | ✅ Pass (SUNPHARMA, BAJFINANCE, ADANIGREEN, HAL, EICHERMOT) |

## Key findings during the sprint

1. **8 orphan tickers** (ULTRACEMCO, UNIONBANK, UNITDSPR, VBL, VEDL, WIPRO, ZOMATO,
   ZYDUSLIFE) appear in profitandloss/balancesheet/cashflow but are absent from
   `companies.xlsx`. These rows were correctly rejected by DQ-03 (FK Integrity).
   Flagged for team lead — likely a gap in the companies master file versus the
   full Nifty 100 universe.
2. **~100 "TTM" (trailing-twelve-month) rows** in profitandloss are not standard
   fiscal-year entries and were rejected by DQ-07 (Year Format) rather than
   force-fitted into the annual time series.
3. **Year label formats varied** across source files — `Mar-23` (cashflow) vs
   `Mar 2014` (profitandloss). `normalize_year()` handles both plus FY-prefix and
   bare-year variants.
4. Only **1 company (JIOFIN)** has under 5 years of history — expected, since
   it's a comparatively newer listing.

## What went well
- Schema matched the spec's data dictionary almost exactly once real files were
  inspected — no guesswork needed after checking actual column headers.
- DQ rules caught real, meaningful data issues (orphan tickers, TTM rows) rather
  than false positives.

## What to improve next sprint
- DQ-13 (URL validity) was not run against live HTTP in this offline environment;
  Sprint 2+ should add an actual `requests.head()` check with timeout/retry handling.
- Confirm with team lead whether the 8 orphan tickers should be added to
  `companies.xlsx` or whether their time-series data should simply remain excluded.
