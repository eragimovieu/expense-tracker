# Expense Tracker with Monthly Budgets

A small web app for logging everyday expenses and checking them against a
monthly budget per category ("groceries: 300 € a month, how much is left?").
It's built for students who share a flat and want a quick answer to "where did
the money go this month?".

In Assignment 1 it was one Flask app with one SQLite file. In Assignment 2 it
is split along the seam from ADR-2 into two services, each with its own SQL
Server database, plus a static UI.

| Part | What it does | Folder | Owns |
|---|---|---|---|
| expenses service | Add / list / delete expenses, totals per category per month | `services/expenses/` | `expenses` database |
| budgets service | Monthly limit per category, % used, ok / warning (≥ 80%) / over, spending with no budget | `services/budgets/` | `budgets` database |
| UI | Two static pages that call both services from the browser | `ui/` | nothing |

The only call between the services: the budgets service asks
`GET /api/expenses/totals?month=YYYY-MM` on the expenses service, with a 3 s
timeout. If expenses doesn't answer, budgets still shows the limits and says
spending is unavailable (`ADR.md`, entry 6).

## Run everything locally

You need Docker Desktop. On an Apple Silicon Mac, turn on
*Settings → General → Use Rosetta for x86_64/amd64 emulation*, because SQL
Server only has an amd64 image.

```bash
git clone https://github.com/eragimovieu/expense-tracker
cd expense-tracker
docker compose up --build
```

Then open http://localhost:8080. The first start takes a minute or two (SQL
Server image, then the two service images).

What happens on `docker compose up`:

1. `sqlserver` starts and becomes healthy.
2. `db-init` runs `db/init.sql` once: it creates the `expenses` and `budgets`
   databases and one login per service, then exits.
3. `expenses` and `budgets` start. Each one applies its own migrations from
   `services/<name>/migrations/` and records them in `schema_migrations`.
4. `ui` (stock `nginx:alpine`, no Dockerfile) serves the files in `ui/`.

Data is kept in the `sqldata` volume, so `docker compose down` and `up` again
keeps it. `docker compose down -v` deletes it.

To see what happens when one service is down:

```bash
docker compose stop expenses     # budgets page: limits only, with a notice
docker compose start expenses
```

The passwords in `docker-compose.yml` only exist in this local container.
Azure uses different ones, stored as GitHub secrets.

## Run a single service

With compose (it also starts SQL Server and `db-init`, which it depends on):

```bash
docker compose up --build expenses     # http://localhost:8001/health
docker compose up --build budgets      # works without expenses, see above
```

Without Docker for the service itself (SQL Server still from compose):

```bash
docker compose up -d sqlserver db-init
cd services/expenses
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export DATABASE_URL="mssql://expenses_app:LocalDev-Expenses-1@localhost:1433/expenses"
gunicorn --config gunicorn.conf.py "app:create_app()"
```

## Configuration (environment variables)

expenses service:

| Variable | Default | Meaning |
|---|---|---|
| `PORT` | `8001` | Port gunicorn listens on |
| `DATABASE_URL` | none (secret) | `mssql://user:password@host:1433/database` |
| `CORS_ORIGINS` | `http://localhost:8080,http://127.0.0.1:8080` | Origins allowed to call it from a browser (the UI) |
| `GIT_SHA` | `dev` | Version shown by `/health` |

budgets service: the same four (default `PORT` is `8002`), plus

| Variable | Default | Meaning |
|---|---|---|
| `EXPENSES_URL` | `http://localhost:8001` | Base URL of the expenses service |
| `EXPENSES_TIMEOUT_S` | `3` | Timeout of the call to expenses, in seconds |

The UI reads the two service URLs from `ui/config.js`.

## API

expenses service (`services/expenses`):

| Method | Path | What it does |
|---|---|---|
| GET | `/api/expenses?month=YYYY-MM` | Expenses of the month |
| POST | `/api/expenses` | Add one: `{"amount": "12.50", "category": "groceries", "description": "", "spent_on": "2026-11-25"}` |
| DELETE | `/api/expenses/<id>` | Delete one (204, or 404) |
| GET | `/api/expenses/totals?month=YYYY-MM` | `{category: cents}` for the month (called by budgets) |
| GET | `/api/expenses/categories` | Categories used so far |
| GET | `/health` | 200 `{"status": "ok", "db": "ok", "version": "<sha>"}`, or 503 |

budgets service (`services/budgets`):

| Method | Path | What it does |
|---|---|---|
| GET | `/api/budgets/status?month=YYYY-MM` | Budgets with spent / remaining / status, plus unbudgeted spending |
| POST | `/api/budgets` | Create or update: `{"category": "groceries", "monthly_limit": "300"}` |
| DELETE | `/api/budgets/<id>` | Remove one (204, or 404) |
| GET | `/health` | Same as above, for the budgets database |

`month` is optional and defaults to the current month. Amounts in answers are
in cents. Errors come back as `{"error": "message"}` with a 4xx/5xx status.
Every request is logged to stdout as one line: method, path, status, duration.

## Project structure

```
services/expenses/   expenses service: app.py, routes.py, service.py, db.py,
                     migrate.py, migrations/, Dockerfile, requirements.txt
services/budgets/    budgets service: same layout, plus expenses_client.py
ui/                  static pages (index.html, budgets.html), config.js
db/init.sql          local only: databases and logins for compose
docker-compose.yml   the whole system locally
ADR.md               architecture decision log
AI_USAGE.md          AI usage log
```

## Known limitations

- No login: anyone who can open the app sees all data (`ADR.md`, entry 5).
