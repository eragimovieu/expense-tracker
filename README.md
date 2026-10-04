# Expense Tracker with Monthly Budgets

A small web app for logging everyday expenses and checking them against a
monthly budget per category ("groceries: 300 € a month, how much is left?").

It's built for students who share a flat and want a quick answer to "where did
the money go this month?" without a banking app or a spreadsheet.

**Two feature domains:**

| Domain | What it does | Code | Table |
|---|---|---|---|
| Expenses | Add / list / delete expenses, totals per category per month | `expenses/` | `expenses` |
| Budgets | Monthly limit per category, % used, ok / warning (≥ 80%) / over, spending with no budget | `budgets/` | `budgets` |

Budgets gets spending data only through `expenses.service.totals_by_category()`,
the one seam between the two domains (see `ADR.md`, entry 2).

## Requirements

- Python 3.10 or newer
- Nothing else: the database is SQLite, which ships with Python

## Setup and run

```bash
git clone <your-repo-url>
cd expense-tracker

python -m venv .venv
# macOS / Linux:
source .venv/bin/activate
# Windows (PowerShell):
.venv\Scripts\Activate.ps1

pip install -r requirements.txt
python app.py
```

Open http://localhost:8000. The database file and its tables are created
automatically on first start; there is no setup or migration step.

## Configuration (environment variables)

All settings are optional; the defaults work locally.

| Variable | Default | Meaning |
|---|---|---|
| `PORT` | `8000` | Port the app listens on |
| `HOST` | `0.0.0.0` | Address to bind (all interfaces, so it works inside a container) |
| `DATA_DIR` | `./data` | Folder for the SQLite file |
| `SECRET_KEY` | `dev-only-change-me` | Signs the flash-message cookie; set a real one when deployed |

The SQLite database is always at **`$DATA_DIR/expenses.db`** (by default
`./data/expenses.db`).

Example: `PORT=5050 DATA_DIR=/tmp/expdata python app.py`
(PowerShell: `$env:PORT=5050; python app.py`)

## Tests and coverage

```bash
pytest --cov=expenses --cov=budgets --cov=utils --cov-report=term-missing
```

Result on my machine (2026-10-04): **66 passed, TOTAL coverage 93%**

`expenses/service.py`, `budgets/service.py` and `utils.py` hold the business
logic and have dedicated unit tests; routes only have smoke tests
(see `ADR.md`, entry 4).

## Pages and API

| Method | Path | What it does |
|---|---|---|
| GET | `/` | Redirects to `/expenses` |
| GET | `/expenses?month=YYYY-MM` | Expense list, add form, totals per category |
| POST | `/expenses` | Add an expense (form) |
| POST | `/expenses/<id>/delete` | Delete an expense |
| GET | `/budgets?month=YYYY-MM` | Budget status for the month, set-budget form |
| POST | `/budgets` | Create or update a budget (form) |
| POST | `/budgets/<id>/delete` | Remove a budget |
| GET | `/api/expenses?month=YYYY-MM` | Expenses as JSON |
| GET | `/api/expenses/totals?month=YYYY-MM` | `{category: cents}` for the month as JSON |
| GET | `/api/budgets/status?month=YYYY-MM` | Budget status + unbudgeted spending as JSON |
| GET | `/health` | `{"status": "ok"}`, for the deployment script |

`month` is optional everywhere and defaults to the current month. Amounts in
the API are in cents.

## Project structure

```
app.py              entry point: create_app(), registers both blueprints
config.py           reads all settings from environment variables
db.py               SQLite connection helpers, runs schema.sql on startup
schema.sql          the two tables
utils.py            shared helpers (parsing amounts/months, formatting money)
expenses/           expenses domain: service.py (logic + SQL), routes.py (blueprint)
budgets/            budgets domain:  service.py (logic + SQL), routes.py (blueprint)
templates/          Jinja pages (base, expenses, budgets)
static/style.css    styles
tests/              pytest tests (conftest.py has the in-memory DB fixture)
ADR.md              architecture decision log
AI_USAGE.md         AI usage log
```

## Deployment contract (Assignment 2)

- One process, started with `python app.py`
- Binds to `0.0.0.0`, port from `PORT`
- No interactive setup: tables are created on startup
- SQLite file at `$DATA_DIR/expenses.db`
- One dependency manifest: `requirements.txt`
- Configured only through environment variables; no `.env` file needed

## Known limitations

- No login: anyone who can open the app sees all data (`ADR.md`, entry 5).
- Uses Flask's built-in server; a production WSGI server comes with deployment.
