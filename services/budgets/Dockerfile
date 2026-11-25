# Image for the budgets service. The build context is services/budgets/,
# so nothing from the other service or the repo root can end up in here.
FROM python:3.12.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Dependencies first: this layer is reused until requirements.txt changes.
COPY requirements.txt .
RUN pip install -r requirements.txt

# Then only what the service needs to run. No tests, no .env, no secrets.
COPY app.py config.py db.py expenses_client.py migrate.py routes.py service.py utils.py gunicorn.conf.py ./
COPY migrations/ migrations/

# Don't run as root inside the container.
RUN useradd --create-home --uid 10001 appuser
USER appuser

EXPOSE 8002
CMD ["gunicorn", "--config", "gunicorn.conf.py", "app:create_app()"]
