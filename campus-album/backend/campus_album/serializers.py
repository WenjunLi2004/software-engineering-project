from collections.abc import Mapping
import sqlite3
from typing import Any


def serialize_user(row: sqlite3.Row | Mapping[str, Any]) -> dict[str, Any]:
    """Serialize a user row to the public API shape."""
    return {
        "id": row["id"],
        "username": row["username"],
    }


def serialize_post(row: sqlite3.Row | Mapping[str, Any]) -> dict[str, Any]:
    """Serialize a joined post+author row to the public API shape."""
    return {
        "id": row["id"],
        "text": row["body"],
        "author": {
            "id": row["author_id"],
            "username": row["author_username"],
        },
        "createdAt": row["created_at"],
    }
