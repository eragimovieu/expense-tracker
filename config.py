"""App settings. Everything comes from environment variables, with defaults
that work on a laptop, so nothing in the source has to be edited to deploy."""
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def load_config():
    data_dir = os.environ.get("DATA_DIR", os.path.join(BASE_DIR, "data"))
    return {
        "HOST": os.environ.get("HOST", "0.0.0.0"),
        "PORT": int(os.environ.get("PORT", "8000")),
        "DATA_DIR": data_dir,
        "DATABASE": os.path.join(data_dir, "expenses.db"),
        "SECRET_KEY": os.environ.get("SECRET_KEY", "dev-only-change-me"),
    }
