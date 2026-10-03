"""Entry point. `python app.py` starts the whole app as a single process."""
from flask import Flask

from config import load_config


def create_app():
    app = Flask(__name__)
    app.config.update(load_config())

    @app.get("/health")
    def health():
        return {"status": "ok"}

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host=app.config["HOST"], port=app.config["PORT"])
