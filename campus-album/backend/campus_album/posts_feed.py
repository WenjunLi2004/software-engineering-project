from typing import Any

from flask import Blueprint

from .db import get_db
from .serializers import serialize_post

bp = Blueprint("posts_feed", __name__)


@bp.get("/api/posts")
def list_posts() -> tuple[dict[str, list[dict[str, Any]]], int]:
    """Return visible posts from active authors in reverse chronological order."""
    rows = get_db().execute(
        """
        SELECT p.id, p.body, p.created_at, u.id AS author_id, u.username AS author_username
        FROM posts p
        JOIN users u ON u.id = p.author_id
        WHERE p.status = 'visible' AND u.deleted_at IS NULL
        ORDER BY p.created_at DESC, p.id DESC
        """
    ).fetchall()
    return {"posts": [serialize_post(row) for row in rows]}, 200
