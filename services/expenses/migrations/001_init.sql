-- 001: the expenses table, ported from the A1 SQLite schema.sql.
-- SQLite -> SQL Server: INTEGER PRIMARY KEY -> INT IDENTITY, TEXT -> NVARCHAR,
-- the ISO date text -> DATE, CURRENT_TIMESTAMP -> SYSUTCDATETIME().
-- Money is still whole cents in an integer column (ADR-3).

CREATE TABLE expenses (
    id           INT IDENTITY(1, 1) PRIMARY KEY,
    amount_cents INT           NOT NULL CONSTRAINT ck_expenses_amount CHECK (amount_cents > 0),
    category     NVARCHAR(40)  NOT NULL,
    description  NVARCHAR(200) NOT NULL CONSTRAINT df_expenses_description DEFAULT '',
    spent_on     DATE          NOT NULL,
    created_at   DATETIME2     NOT NULL CONSTRAINT df_expenses_created_at DEFAULT SYSUTCDATETIME()
);
GO

-- Every page and the totals endpoint filter by month.
CREATE INDEX ix_expenses_spent_on ON expenses (spent_on);
