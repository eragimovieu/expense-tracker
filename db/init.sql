-- Local only. The one-off db-init service in docker-compose.yml runs this
-- with sqlcmd every time the stack starts, so it must be safe to run again.
--
-- One database and one login per service. Each login is a user in its own
-- database only, so the expenses service can't open the budgets database and
-- the other way round. Tables are not created here: each service creates its
-- own with its migrations when it starts.
--
-- $(EXPENSES_DB_PASSWORD) and $(BUDGETS_DB_PASSWORD) are sqlcmd variables,
-- filled in from the db-init service's environment.
-- On Azure the same users are created once by the setup in the README.

IF DB_ID('expenses') IS NULL CREATE DATABASE expenses;
GO
IF DB_ID('budgets') IS NULL CREATE DATABASE budgets;
GO

IF SUSER_ID('expenses_app') IS NULL
    CREATE LOGIN expenses_app WITH PASSWORD = '$(EXPENSES_DB_PASSWORD)', DEFAULT_DATABASE = expenses;

IF SUSER_ID('budgets_app') IS NULL
    CREATE LOGIN budgets_app WITH PASSWORD = '$(BUDGETS_DB_PASSWORD)', DEFAULT_DATABASE = budgets;
GO

-- ddladmin so the service can run its own migrations,
-- datareader + datawriter for normal reads and writes.
USE expenses;
IF USER_ID('expenses_app') IS NULL
BEGIN
    CREATE USER expenses_app FOR LOGIN expenses_app;
    ALTER ROLE db_ddladmin ADD MEMBER expenses_app;
    ALTER ROLE db_datareader ADD MEMBER expenses_app;
    ALTER ROLE db_datawriter ADD MEMBER expenses_app;
END
GO

USE budgets;
IF USER_ID('budgets_app') IS NULL
BEGIN
    CREATE USER budgets_app FOR LOGIN budgets_app;
    ALTER ROLE db_ddladmin ADD MEMBER budgets_app;
    ALTER ROLE db_datareader ADD MEMBER budgets_app;
    ALTER ROLE db_datawriter ADD MEMBER budgets_app;
END
GO

PRINT 'db-init: databases and logins are ready';
