"""Entry point. `python app.py` starts the whole app as a single process."""
import os

from flask import Flask

import db
from config import load_config


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

    @app.get("/health")
    def health():
        return {"status": "ok"}

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host=app.config["HOST"], port=app.config["PORT"])
