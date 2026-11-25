from typing import Any

from flask import Blueprint, request

from .auth import require_auth
from .db import get_db
from .errors import error_response
from .serializers import serialize_post

bp = Blueprint("posts_publish", __name__)


@bp.post("/api/posts")
def create_post() -> tuple[dict[str, Any], int]:
    user, err = require_auth()
    if err is not None:
        return err

    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return error_response("INVALID_INPUT", "请求格式无效", 400)

    raw_text = payload.get("text")
    if not isinstance(raw_text, str):
        return error_response("INVALID_INPUT", "请输入作品内容", 400)

    text = raw_text.strip()
    if text == "":
        return error_response("INVALID_INPUT", "请输入作品内容", 400)

    db = get_db()
    cursor = db.execute(
        "INSERT INTO posts (author_id, body, status) VALUES (?, ?, ?)",
        (user["id"], text, "visible"),
    )
    post_id = cursor.lastrowid
    db.commit()

    row = db.execute(
        """
        SELECT
            p.id,
            p.body,
            p.created_at,
            u.id AS author_id,
            u.username AS author_username
        FROM posts p
        JOIN users u ON u.id = p.author_id
        WHERE p.id = ?
        """,
        (post_id,),
    ).fetchone()

    return {"post": serialize_post(row)}, 201
