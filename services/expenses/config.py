"""Settings for the expenses service. Everything comes from environment
variables, so nothing in the code changes between my laptop, compose and
Azure. PORT is read by gunicorn.conf.py, not here."""
import os

DEFAULT_CORS_ORIGINS = "http://localhost:8080,http://127.0.0.1:8080"


def split_origins(value):
    """'http://a, http://b' -> ['http://a', 'http://b']"""
    return [origin.strip() for origin in value.split(",") if origin.strip()]


def load_config():
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        # No default on purpose: it contains a password (secret in system.yaml).
        raise RuntimeError("DATABASE_URL is not set. See the README, section Configuration.")
    return {
        "DATABASE_URL": database_url,
        # Only the UI's origin may call this service from a browser.
        "CORS_ORIGINS": split_origins(os.environ.get("CORS_ORIGINS", DEFAULT_CORS_ORIGINS)),
        # Set by the deploy workflow to the commit SHA, shown by /health.
        "GIT_SHA": os.environ.get("GIT_SHA", "dev"),
    }
