# Architecture Decision Records

## 1. Python + Flask for the backend
Date: 2026-10-03
Status: Decided
Context: The app needs two small feature domains, a few HTML pages and SQLite. Python is the language I'm most comfortable explaining without notes.
Decision: Use Python 3 with Flask, Jinja templates for the pages, and the built-in `sqlite3` module instead of an ORM.
Alternatives considered: Django, rejected because its ORM, admin, auth and migrations are far more than two small domains need, and its project layout adds a lot I'd have to explain.
Consequences: Only one runtime dependency (Flask), and blueprints give each domain its own folder. The cost is that I write the SQL and the input validation myself, with no library to help.
