import os
from pathlib import Path

from flask import Flask

from . import db


def create_app() -> Flask:
    app = Flask(__name__, instance_relative_config=True)
    default_database = Path(app.instance_path) / "campus-album.sqlite3"
    database_path = Path(os.environ.get("CAMPUS_ALBUM_DATABASE") or default_database)
    database_path.parent.mkdir(parents=True, exist_ok=True)
    app.config["DATABASE"] = database_path

    db.init_app(app)

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app
