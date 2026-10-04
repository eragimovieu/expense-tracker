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
Status: Decided
Context: Budgets need to know how much was spent per category, and that information lives in the expenses data. If the two tables were tied together with foreign keys, the budgets domain could never move to its own service later without dragging the expenses table along.
Decision: `expenses` and `budgets` are two separate tables in the same SQLite file, with no foreign key between them; they relate only through the `category` text, which both domains normalise to lowercase. Money is stored as integer cents (`amount_cents`, `monthly_limit_cents`).
Alternatives considered: A shared `categories` table referenced by a `category_id` foreign key from both tables. It would prevent near-duplicates like "Food" and "food", but it couples both domains to a third table and needs its own create/edit screens. I also rejected storing amounts as `REAL`, because floats give rounding errors on money (0.1 + 0.2 is not exactly 0.3).
Consequences: Either table can later move to its own database without changing the schema. The cost is that SQLite can't check that a budget's category matches real expenses, so a typo just creates a new category; lowercasing and trimming the name, plus a suggestion list in the form, keep that rare.
