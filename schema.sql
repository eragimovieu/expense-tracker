-- Runs on every start; IF NOT EXISTS makes it safe to run again.
-- Each feature domain owns one table. There is no foreign key or JOIN between
-- them: they only share the category name, stored in lowercase (see ADR-3).
-- Money is stored as whole cents (INTEGER), never as floating point.

-- Expenses domain
CREATE TABLE IF NOT EXISTS expenses (
    id           INTEGER PRIMARY KEY,
    amount_cents INTEGER NOT NULL CHECK (amount_cents > 0),
    category     TEXT    NOT NULL,
    description  TEXT    NOT NULL DEFAULT '',
    spent_on     TEXT    NOT NULL,              -- ISO date, e.g. 2026-10-03
    created_at   TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Budgets domain
CREATE TABLE IF NOT EXISTS budgets (
    id                  INTEGER PRIMARY KEY,
    category            TEXT    NOT NULL UNIQUE,
    monthly_limit_cents INTEGER NOT NULL CHECK (monthly_limit_cents > 0),
    created_at          TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP
);
