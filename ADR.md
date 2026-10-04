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

## 4. Unit-test the service layer hard, smoke-test the routes
Date: 2026-10-04
Status: Decided
Context: The brief asks for at least 70% coverage of the core business logic, and I had limited time. The logic that can actually get money wrong (parsing amounts, monthly totals, the 80% / over-budget rules) lives in `expenses/service.py`, `budgets/service.py` and `utils.py`, not in the Flask routes.
Decision: Write pytest unit tests that call the service functions directly against a fresh in-memory SQLite database (the `conn` fixture), aiming at full coverage there, including edge cases like exactly 80%, exactly at the limit, and "0.29" not becoming 28 cents. Routes only get a handful of smoke tests through Flask's test client.
Alternatives considered: Testing everything through HTTP requests with the test client. It would cover the routes as well, but every failure would be harder to trace, the tests would be slower, and checking a threshold like 80% through rendered HTML is clumsy. Mocking the database was also rejected: an in-memory SQLite runs the real SQL and is just as fast.
Consequences: Coverage on the services is close to 100% and the tests run in under a second. Thinner areas: templates and the `if __name__ == "__main__"` block aren't tested, and some error branches in the routes (a bad `month` on the HTML pages, an invalid budget form, deleting something that's already gone) are only checked by hand.
