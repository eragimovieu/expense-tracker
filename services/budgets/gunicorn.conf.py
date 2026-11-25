"""gunicorn settings for the budgets service (the Dockerfile's CMD uses them)."""
import os

bind = f"0.0.0.0:{os.environ.get('PORT', '8002')}"

# Load the app (and run the migrations) once in the main process, before any
# worker starts. With one worker and at most one replica on Azure (ADR-8),
# two copies of the migrations can never run at the same time.
preload_app = True
workers = 1
threads = 4

# A request can wait for a paused Azure SQL database to resume.
timeout = 120

accesslog = None  # app.py writes its own line per request
errorlog = "-"
