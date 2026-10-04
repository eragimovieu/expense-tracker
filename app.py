"""Entry point. `python app.py` starts the whole app as a single process."""
import os

from flask import Flask, redirect, url_for

import db
from config import load_config
from expenses.routes import bp as expenses_bp
from utils import format_money, month_label, shift_month


def create_app():
    app = Flask(__name__)
    app.config.update(load_config())

    # Create the data folder and tables on startup, so there is no manual
    # setup or migration step after clone + install.
    os.makedirs(app.config["DATA_DIR"], exist_ok=True)
    conn = db.connect(app.config["DATABASE"])
    db.init_db(conn)
    conn.close()
    app.teardown_appcontext(db.close_db)

    # Each feature domain is a blueprint with its own routes.
    app.register_blueprint(expenses_bp)

    # Helpers the templates can use: {{ cents|money }}, {{ month|month_label }}
    app.add_template_filter(format_money, "money")
    app.add_template_filter(month_label, "month_label")
    app.add_template_global(shift_month, "shift_month")

    @app.get("/")
    def index():
        return redirect(url_for("expenses.expenses_page"))

    @app.get("/health")
    def health():
        return {"status": "ok"}

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host=app.config["HOST"], port=app.config["PORT"])
