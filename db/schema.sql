-- Nifty100 Financial Intelligence Platform
-- Sprint 1 - Data Foundation Schema
-- 10 tables: companies, profitandloss, balancesheet, cashflow, analysis,
--            documents, prosandcons, sectors, stock_prices, market_cap
-- Note: financial_ratios and peer_groups loaded as supporting/reference data
--       per Sprint 1 spec (computed table proper is Sprint 2 scope, but we
--       load the raw provided file now since it's part of the 12 input files).

PRAGMA foreign_keys = ON;

DROP TABLE IF EXISTS companies;
CREATE TABLE companies (
    id                  TEXT PRIMARY KEY,        -- NSE ticker
    company_logo        TEXT,
    company_name        TEXT NOT NULL,
    chart_link           TEXT,
    about_company       TEXT,
    website             TEXT,
    nse_profile         TEXT,
    bse_profile         TEXT,
    face_value          REAL,
    book_value          REAL,
    roce_percentage     REAL,
    roe_percentage      REAL
);

DROP TABLE IF EXISTS profitandloss;
CREATE TABLE profitandloss (
    id                  INTEGER,
    company_id          TEXT NOT NULL,
    year                TEXT NOT NULL,           -- normalised YYYY-MM
    sales               REAL,
    expenses            REAL,
    operating_profit    REAL,
    opm_percentage      REAL,
    other_income        REAL,
    interest            REAL,
    depreciation        REAL,
    profit_before_tax   REAL,
    tax_percentage      REAL,
    net_profit          REAL,
    eps                 REAL,
    dividend_payout     REAL,
    PRIMARY KEY (company_id, year),
    FOREIGN KEY (company_id) REFERENCES companies(id)
);

DROP TABLE IF EXISTS balancesheet;
CREATE TABLE balancesheet (
    id                  INTEGER,
    company_id          TEXT NOT NULL,
    year                TEXT NOT NULL,
    equity_capital       REAL,
    reserves            REAL,
    borrowings          REAL,
    other_liabilities   REAL,
    total_liabilities   REAL,
    fixed_assets        REAL,
    cwip                REAL,
    investments         REAL,
    other_asset         REAL,
    total_assets        REAL,
    PRIMARY KEY (company_id, year),
    FOREIGN KEY (company_id) REFERENCES companies(id)
);

DROP TABLE IF EXISTS cashflow;
CREATE TABLE cashflow (
    id                  INTEGER,
    company_id          TEXT NOT NULL,
    year                TEXT NOT NULL,
    operating_activity  REAL,
    investing_activity  REAL,
    financing_activity  REAL,
    net_cash_flow       REAL,
    PRIMARY KEY (company_id, year),
    FOREIGN KEY (company_id) REFERENCES companies(id)
);

DROP TABLE IF EXISTS analysis;
CREATE TABLE analysis (
    id                          INTEGER PRIMARY KEY,
    company_id                  TEXT NOT NULL,
    compounded_sales_growth     TEXT,
    compounded_profit_growth    TEXT,
    stock_price_cagr            TEXT,
    roe                          TEXT,
    FOREIGN KEY (company_id) REFERENCES companies(id)
);

DROP TABLE IF EXISTS documents;
CREATE TABLE documents (
    id                  INTEGER PRIMARY KEY,
    company_id          TEXT NOT NULL,
    year                INTEGER NOT NULL,
    annual_report       TEXT,
    FOREIGN KEY (company_id) REFERENCES companies(id)
);

DROP TABLE IF EXISTS prosandcons;
CREATE TABLE prosandcons (
    id                  INTEGER PRIMARY KEY,
    company_id          TEXT NOT NULL,
    pros                TEXT,
    cons                TEXT,
    FOREIGN KEY (company_id) REFERENCES companies(id)
);

DROP TABLE IF EXISTS sectors;
CREATE TABLE sectors (
    id                      INTEGER PRIMARY KEY,
    company_id              TEXT NOT NULL UNIQUE,
    broad_sector            TEXT,
    sub_sector              TEXT,
    index_weight_pct        REAL,
    market_cap_category     TEXT,
    FOREIGN KEY (company_id) REFERENCES companies(id)
);

DROP TABLE IF EXISTS stock_prices;
CREATE TABLE stock_prices (
    id                  INTEGER PRIMARY KEY,
    company_id          TEXT NOT NULL,
    date                TEXT NOT NULL,
    open_price          REAL,
    high_price          REAL,
    low_price           REAL,
    close_price         REAL,
    volume              INTEGER,
    adjusted_close      REAL,
    FOREIGN KEY (company_id) REFERENCES companies(id)
);

DROP TABLE IF EXISTS market_cap;
CREATE TABLE market_cap (
    id                      INTEGER PRIMARY KEY,
    company_id              TEXT NOT NULL,
    year                    INTEGER NOT NULL,
    market_cap_crore        REAL,
    enterprise_value_crore  REAL,
    pe_ratio                REAL,
    pb_ratio                REAL,
    ev_ebitda               REAL,
    dividend_yield_pct      REAL,
    FOREIGN KEY (company_id) REFERENCES companies(id)
);

-- Indexes for common joins / lookups
CREATE INDEX idx_pl_company ON profitandloss(company_id);
CREATE INDEX idx_bs_company ON balancesheet(company_id);
CREATE INDEX idx_cf_company ON cashflow(company_id);
CREATE INDEX idx_sp_company ON stock_prices(company_id);
CREATE INDEX idx_mc_company ON market_cap(company_id);
CREATE INDEX idx_doc_company ON documents(company_id);
