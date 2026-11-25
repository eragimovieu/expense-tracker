"""Budgets service: owns the budgets table and nothing else. It gets
spending from the expenses service over HTTP (expenses_client.py).

gunicorn starts it (see the Dockerfile and gunicorn.conf.py):
    gunicorn --config gunicorn.conf.py "app:create_app()"
"""
import logging
import sys
import time

from flask import Flask, g, jsonify, request
from werkzeug.exceptions import HTTPException

import db
from config import load_config
from migrate import run_migrations
from routes import bp

log = logging.getLogger("budgets")


def create_app(config=None, run_startup_migrations=True):
    # Logs go to stdout, where Docker and Container Apps collect them.
    logging.basicConfig(
        level=logging.INFO,
        stream=sys.stdout,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    app = Flask(__name__)
    app.config.update(config or load_config())

    if run_startup_migrations:
        # Bring the schema up to date before serving anything (ADR-7).
        conn = db.connect(app.config["DATABASE_URL"], attempts=db.STARTUP_ATTEMPTS)
        try:
            run_migrations(conn)
        finally:
            conn.close()

    app.register_blueprint(bp)
    app.teardown_appcontext(db.close_db)
    add_request_log(app)
    add_cors(app)
    add_error_handlers(app)

    @app.get("/health")
    def health():
        """200 when this service can read and write its own database, 503 if
        not. It doesn't call the expenses service at all."""
        body = {"status": "ok", "db": "ok", "version": app.config["GIT_SHA"]}
        try:
            conn = db.connect(app.config["DATABASE_URL"], attempts=1)
            try:
                db.check_read_write(conn)
            finally:
                conn.close()
        except Exception as err:
            log.warning("Health check failed: %s", err)
            body.update(status="error", db="error")
            return jsonify(body), 503
        return jsonify(body)

    return app


def add_request_log(app):
    """One line per request on stdout: method, path, status, duration."""

    @app.before_request
    def start_timer():
        g.started = time.perf_counter()

    @app.after_request
    def log_request(response):
        duration_ms = (time.perf_counter() - g.get("started", time.perf_counter())) * 1000
        log.info("%s %s %s %.0fms", request.method, request.path, response.status_code, duration_ms)
        return response


def add_cors(app):
    """The browser calls this service from the UI's origin (localhost:8080, or
    the storage static website on Azure). Only origins in CORS_ORIGINS get the
    headers that let the browser read the answer. Preflight OPTIONS requests
    are answered by Flask automatically and get the same headers here."""

    @app.after_request
    def cors_headers(response):
        origin = request.headers.get("Origin")
        if origin and origin in app.config["CORS_ORIGINS"]:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, DELETE, OPTIONS"
            response.headers["Access-Control-Allow-Headers"] = "Content-Type"
            response.headers["Access-Control-Max-Age"] = "600"
        response.vary.add("Origin")
        return response


def add_error_handlers(app):
    """Errors come back as JSON with a short message, never an HTML stack trace."""

    @app.errorhandler(HTTPException)
    def http_error(err):
        return jsonify(error=err.description), err.code

    @app.errorhandler(db.DatabaseUnavailable)
    def database_unavailable(err):
        log.warning("Database unavailable: %s", err)
        return jsonify(error="The database is starting up. Try again in a few seconds."), 503

    @app.errorhandler(Exception)
    def unexpected_error(err):
        log.exception("Unexpected error")
        return jsonify(error="Something went wrong on our side."), 500
