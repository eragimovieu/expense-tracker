-- 001: the budgets table, ported from the A1 SQLite schema.sql.
-- SQLite -> SQL Server: INTEGER PRIMARY KEY -> INT IDENTITY, TEXT -> NVARCHAR,
-- CURRENT_TIMESTAMP -> SYSUTCDATETIME().
-- category is UNIQUE, so saving a budget for the same category again updates
-- its limit. It is plain text with no link to the expenses database (ADR-6).

CREATE TABLE budgets (
    id                  INT IDENTITY(1, 1) PRIMARY KEY,
    category            NVARCHAR(40) NOT NULL CONSTRAINT uq_budgets_category UNIQUE,
    monthly_limit_cents INT          NOT NULL CONSTRAINT ck_budgets_limit CHECK (monthly_limit_cents > 0),
    created_at          DATETIME2    NOT NULL CONSTRAINT df_budgets_created_at DEFAULT SYSUTCDATETIME()
);
