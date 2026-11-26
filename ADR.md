# Architecture Decision Records

## 1. Python + Flask for the backend
Date: 2026-10-03
Status: Decided

Context: The app needs two small feature domains, a few HTML pages and SQLite. Python is the language I'm most comfortable explaining without notes.

Decision: Use Python 3 with Flask, Jinja templates for the pages, and the built-in `sqlite3` module instead of an ORM.

Alternatives considered: Django, rejected because its ORM, admin, auth and migrations are far more than two small domains need, and its project layout adds a lot I'd have to explain.

Consequences: Only one runtime dependency (Flask), and blueprints give each domain its own folder. The cost is that I write the SQL and the input validation myself, with no library to help.

## 2. Expenses and budgets as two separate modules with one seam
Date: 2026-10-04
Status: Decided
Context: The brief says each domain should be able to become its own service later. Budgets can't do anything useful without knowing what was spent, so the two domains have to exchange data somehow, and I want that to happen in exactly one place.
Decision: Each domain is its own package (`expenses/`, `budgets/`) with a `service.py` (logic plus SQL for its own table only) and a `routes.py` (a Flask blueprint). The budgets domain gets spending only by calling `expenses.service.totals_by_category(conn, month)`, and the same data is exposed as JSON at `GET /api/expenses/totals?month=YYYY-MM`.
Alternatives considered: One `models.py` and one `routes.py` for the whole app. It's less code today, but budget code would end up querying the expenses table directly, and splitting it later would mean untangling it. I also considered having budgets call the expenses HTTP API even now, but making HTTP calls from the app to itself adds error handling and slowness with no benefit while it's one process.
Consequences: Splitting later means replacing one function call in `budgets/service.py` with an HTTP call to `/api/expenses/totals`; the rest of budgets stays the same. The cost is that helpers both domains need (`utils.py`) will have to be copied into each service.

## 3. Each domain owns one table, linked only by category name
Date: 2026-10-03
Status: Superseded by 7
Context: Budgets need to know how much was spent per category, and that information lives in the expenses data. If the two tables were tied together with foreign keys, the budgets domain could never move to its own service later without dragging the expenses table along.
Decision: `expenses` and `budgets` are two separate tables in the same SQLite file, with no foreign key between them; they relate only through the `category` text, which both domains normalise to lowercase. Money is stored as integer cents (`amount_cents`, `monthly_limit_cents`).
Alternatives considered: A shared `categories` table referenced by a `category_id` foreign key from both tables. It would prevent near-duplicates like "Food" and "food", but it couples both domains to a third table and needs its own create/edit screens. I also rejected storing amounts as `REAL`, because floats give rounding errors on money (0.1 + 0.2 is not exactly 0.3).
Consequences: Either table can later move to its own database without changing the schema. The cost is that SQLite can't check that a budget's category matches real expenses, so a typo just creates a new category; lowercasing and trimming the name, plus a suggestion list in the form, keep that rare.

## 4. Unit-test the service layer hard, smoke-test the routes
Date: 2026-10-04
Status: Decided
Context: The brief asks for at least 70% coverage of the core business logic, and I had limited time. The logic that can actually get money wrong (parsing amounts, monthly totals, the 80% / over-budget rules) lives in `expenses/service.py`, `budgets/service.py` and `utils.py`, not in the Flask routes.
Decision: Write pytest unit tests that call the service functions directly against a fresh in-memory SQLite database (the `conn` fixture), aiming at full coverage there, including edge cases like exactly 80%, exactly at the limit, and "0.29" not becoming 28 cents. Routes only get a handful of smoke tests through Flask's test client.
Alternatives considered: Testing everything through HTTP requests with the test client. It would cover the routes as well, but every failure would be harder to trace, the tests would be slower, and checking a threshold like 80% through rendered HTML is clumsy. Mocking the database was also rejected: an in-memory SQLite runs the real SQL and is just as fast.
Consequences: Coverage on the services is close to 100% and the tests run in under a second. Thinner areas: templates and the `if __name__ == "__main__"` block aren't tested, and some error branches in the routes (a bad `month` on the HTML pages, an invalid budget form, deleting something that's already gone) are only checked by hand.

## 5. No login or user accounts (for now)
Date: 2026-10-04
Status: Decided
Context: Realistically, several flatmates would each want their own expenses. But adding accounts means a `users` table, password hashing, sessions, and a `user_id` column on both `expenses` and `budgets`, which would tie both domains to a third one before the first version works.
Decision: Don't build authentication. The first version is a single-user app that each person runs for themselves.
Alternatives considered: Flask-Login with a simple users table, rejected because it adds dependencies, a third domain both others would depend on, and security work (password storage, CSRF on every form) that I couldn't do properly in this assignment. HTTP basic auth through one environment variable password, rejected because it protects the app but still doesn't separate one flatmate's data from another's.
Consequences: Anyone who can reach the app can see and change all data, so it must not be exposed publicly until auth exists. Adding it later means a `user_id` column on both tables and a users service; I'd probably do that once the domains are split in Assignment 2.

## 6. The split: two services along the ADR-2 seam
Date: 2026-11-25

Status: Decided

Context: Assignment 2 turns the monolith into two services, each with its own container and its own database, talking over HTTP. In A1 (ADR-2) I put the seam at one function, `expenses.service.totals_by_category(conn, month)`, and already exposed the same data at `GET /api/expenses/totals`. The question was whether that seam still works once the two sides are separate processes, and what the budgets page should do when expenses is down.

Decision: Split exactly along ADR-2. The expenses service owns the `expenses` table and the budgets service owns the `budgets` table; each has its own database. The only thing that crosses the seam is one call from the budgets service to `GET {EXPENSES_URL}/api/expenses/totals?month=YYYY-MM`, which returns `{"month": ..., "totals": {category: cents}}`. This flow is server side: the browser asks budgets for the status, and budgets asks expenses for the spending (`expenses_client.py`). The call has a 3 second timeout (`EXPENSES_TIMEOUT_S`). If it fails or times out, budgets still answers 200 with the limits, `spending_available: false` and no spending figures, and the UI shows a notice with a "Try again" link. The UI calls each service directly for that service's own data (add/list/delete), with both URLs from `ui/config.js`. The seam held: the endpoint, its path and its response shape are the same as in A1, and inside budgets the function call became `fetch_totals()`.

Alternatives considered: Doing the combination in the browser (UI fetches totals from expenses and budgets from budgets, then works out the status), rejected because the 80% / over rules would move into JavaScript, and the brief wants at least one flow to cross the seam on the server. Returning 503 for the whole budgets status when expenses is down, rejected because the limits are budgets' own data and still useful on their own. Retrying the call to expenses inside budgets, rejected for now: with scale to zero the first call can take much longer than a few retries would cover, and the UI already retries GETs while a service is waking up. Keeping a copy of the expenses totals in the budgets database, rejected because it needs some way to keep the copy up to date (events or a broker, out of scope) and two copies that can disagree.

Consequences: The budgets page shows spending only when both services are up; with expenses stopped it degrades instead of failing. Each status request now costs one extra HTTP call. Nothing checks across the seam that a budget's category matches real expenses, as in A1 (ADR-3), because the two databases can't have a foreign key between them. `utils.py` is now copied into both services, which ADR-2 predicted; each copy keeps only the helpers that service uses. The money and month formatting moved from Jinja filters to `ui/api.js`, since the services only return JSON now.

## 7. Data and migrations: one SQL Server database per service
Date: 2026-11-26

Status: Decided

Context: In A1 both tables lived in one SQLite file and `schema.sql` ran with `CREATE TABLE IF NOT EXISTS` on every start (ADR-3). A2 needs one serverless Azure SQL database per service, each service reaching only its own, and a schema that changes in place once it holds data. This replaces ADR-3: the "two tables, one file" part no longer holds, while integer cents and the category-text link stay.

Decision: Each service has its own database (`expenses`, `budgets`) and its own login, which is a user in that database only. The schema is a folder of numbered SQL files per service (`services/<name>/migrations/001_init.sql`, ...), applied by my own small runner (`migrate.py`) when the service starts: it creates `schema_migrations` if needed, runs every file that isn't recorded there in name order, each file in one transaction, and records the file name. Applied files are never edited; a fix is a new file. The SQLite types were ported by hand: `INTEGER PRIMARY KEY` to `INT IDENTITY`, `TEXT` to `NVARCHAR(n)`, the ISO date text to `DATE`, so a month is now a date range instead of `substr()`. I did not import the A1 data: it was only test data in a SQLite file on my laptop, and there was no seed data. If there had been real data, I'd have exported each table and loaded it through each service's own POST endpoint, so the validation runs again. Recovery plan for a bad migration in production: migrations are forward-only. A file that fails is rolled back and not recorded, the new container doesn't start, and the CD health check fails the run, so I fix it in a new commit. A migration that ran but is wrong gets a corrective migration (the next number). If data was lost, Azure SQL keeps automatic backups, so I'd restore a copy of the database to a point in time just before the deploy and copy the rows back. To keep rolling back the image safe, migrations only add things (a new column with a default, a new table) and never drop or rename in the same release as the code that stops using them.

Alternatives considered: Alembic, rejected because it brings SQLAlchemy and an ORM-style setup to two services that use raw SQL with pymssql (ADR-1), and my runner is about 50 lines I can explain line by line. Recreating the tables on every deploy, rejected because it loses data, which the brief forbids. One shared database with two schemas, rejected because the brief requires a database per service and a login that can't see the other service's data. A foreign key from budgets to a categories table, rejected for the same reason as in ADR-3: it can't cross two databases.

Consequences: Referential integrity across the seam is gone completely. Nothing stops a budget for a category that has no expenses, or an expense in a category with no budget, and deleting every expense of a category leaves its budget in place. This is compensated in code rather than enforced: both services normalise the category the same way (`normalize_category()`), the expense form suggests existing categories, and the budgets page lists "spending without a budget" so mismatches are visible. Migrations run at startup, so a container that can't reach the database doesn't start (connections retry while a paused database resumes). Two copies of the runner must never run at once; that holds because each service runs with one gunicorn worker and at most one replica (ADR-8).
