import os
from pathlib import Path
from typing import Any

from flask import Flask
from werkzeug.exceptions import BadRequest

from . import db
from .auth import bp as auth_bp
from .errors import error_response
from .posts_feed import bp as posts_feed_bp
from .posts_publish import bp as posts_publish_bp


def create_app() -> Flask:
    app = Flask(__name__, instance_relative_config=True)
    app.json.ensure_ascii = False
    default_database = Path(app.instance_path) / "campus-album.sqlite3"
    database_path = Path(os.environ.get("CAMPUS_ALBUM_DATABASE") or default_database)
    database_path.parent.mkdir(parents=True, exist_ok=True)
    app.config["DATABASE"] = database_path

    db.init_app(app)

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.errorhandler(BadRequest)
    def handle_bad_request(_error: BadRequest) -> tuple[dict[str, Any], int]:
        return error_response("INVALID_INPUT", "请求体必须是合法 JSON", 400)

    app.register_blueprint(auth_bp)
    app.register_blueprint(posts_publish_bp)
    app.register_blueprint(posts_feed_bp)

    return app
