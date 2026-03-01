-- =============================================
-- Schema do Simulador de Independência Financeira
-- =============================================

CREATE TABLE IF NOT EXISTS user (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    email TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS asset_classes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    type TEXT NOT NULL CHECK(type IN ('FII', 'Ações', 'ETF', 'Renda Fixa', 'Fundos')),
    invested_value REAL NOT NULL DEFAULT 0,
    current_value REAL NOT NULL DEFAULT 0,
    monthly_income REAL NOT NULL DEFAULT 0,
    expected_annual_return REAL NOT NULL DEFAULT 0,
    admin_fee REAL NOT NULL DEFAULT 0,
    tax_type TEXT NOT NULL DEFAULT 'regressivo',
    has_come_cotas INTEGER NOT NULL DEFAULT 0,
    cdi_percentage REAL NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS scenarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'editavel' CHECK(status IN ('editavel', 'congelado')),
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    based_on INTEGER,
    FOREIGN KEY (based_on) REFERENCES scenarios(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS scenario_parameters (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scenario_id INTEGER NOT NULL UNIQUE,
    inflation REAL NOT NULL DEFAULT 4.5,
    selic REAL NOT NULL DEFAULT 13.75,
    cdi REAL NOT NULL DEFAULT 13.65,
    ipca REAL NOT NULL DEFAULT 4.5,
    salary_growth REAL NOT NULL DEFAULT 3.0,
    monthly_contribution REAL NOT NULL DEFAULT 0,
    extra_contribution REAL NOT NULL DEFAULT 0,
    extra_contribution_month INTEGER,
    extra_contribution_target TEXT NOT NULL DEFAULT 'proporcional',
    desired_monthly_income REAL NOT NULL DEFAULT 5000,
    safe_withdrawal_rate REAL NOT NULL DEFAULT 4.0,
    withdrawal_start_month INTEGER,
    monthly_withdrawal REAL NOT NULL DEFAULT 0,
    crisis_year INTEGER,
    crisis_drop_percent REAL NOT NULL DEFAULT 0,
    projection_months INTEGER NOT NULL DEFAULT 360,
    FOREIGN KEY (scenario_id) REFERENCES scenarios(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS scenario_projections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scenario_id INTEGER NOT NULL,
    month INTEGER NOT NULL,
    total_assets REAL NOT NULL DEFAULT 0,
    passive_income REAL NOT NULL DEFAULT 0,
    net_income REAL NOT NULL DEFAULT 0,
    benchmark_cdi REAL NOT NULL DEFAULT 0,
    benchmark_ipca REAL NOT NULL DEFAULT 0,
    benchmark_ibov REAL NOT NULL DEFAULT 0,
    benchmark_ifix REAL NOT NULL DEFAULT 0,
    benchmark_selic REAL NOT NULL DEFAULT 0,
    FOREIGN KEY (scenario_id) REFERENCES scenarios(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS historical_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    month TEXT NOT NULL,
    total_assets REAL NOT NULL DEFAULT 0,
    passive_income REAL NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS smtp_config (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    smtp_server TEXT NOT NULL DEFAULT 'smtp.gmail.com',
    smtp_port INTEGER NOT NULL DEFAULT 587,
    smtp_email TEXT NOT NULL DEFAULT '',
    smtp_password TEXT NOT NULL DEFAULT '',
    use_tls INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS app_settings (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    ir_renda_fixa REAL NOT NULL DEFAULT 17.5
);
