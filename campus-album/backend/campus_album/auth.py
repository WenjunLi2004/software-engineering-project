from datetime import datetime, timedelta, timezone
import hashlib
import secrets
import sqlite3
from typing import Any

from flask import Blueprint, request
from werkzeug.security import check_password_hash, generate_password_hash

from .db import get_db
from .errors import error_response
from .serializers import serialize_user

bp = Blueprint("auth", __name__)

SESSION_TTL_DAYS = 7
UTC_TIME_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _format_utc(dt: datetime) -> str:
    return dt.strftime(UTC_TIME_FORMAT)


def _digest_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _parse_credentials() -> tuple[tuple[str, str] | None, tuple[dict[str, Any], int] | None]:
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return None, error_response("INVALID_INPUT", "请求体必须是合法 JSON", 400)

    username_raw = payload.get("username")
    password_raw = payload.get("password")

    if not isinstance(username_raw, str) or not username_raw.strip():
        return None, error_response("INVALID_INPUT", "请输入用户名", 400)
    if not isinstance(password_raw, str) or not password_raw.strip():
        return None, error_response("INVALID_INPUT", "请输入密码", 400)

    return (username_raw.strip(), password_raw), None


def get_current_user() -> sqlite3.Row | None:
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        return None

    parts = auth_header.strip().split(None, 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None

    token = parts[1].strip()
    if not token:
        return None

    token_digest = _digest_token(token)
    now_iso = _format_utc(_utc_now())

    row = get_db().execute(
        """
        SELECT u.id, u.username, u.role, u.created_at, u.deleted_at, s.expires_at
        FROM sessions AS s
        JOIN users AS u ON u.id = s.user_id
        WHERE s.token_digest = ? AND u.deleted_at IS NULL
        """,
        (token_digest,),
    ).fetchone()

    if row is None or not row["expires_at"] or row["expires_at"] <= now_iso:
        return None

    return row


def require_auth() -> tuple[sqlite3.Row, None] | tuple[None, tuple[dict[str, Any], int]]:
    user = get_current_user()
    if user is not None:
        return user, None
    return None, error_response("UNAUTHORIZED", "登录状态无效或已过期，请重新登录", 401)


@bp.post("/api/auth/register")
def register() -> tuple[dict[str, Any], int]:
    credentials, error = _parse_credentials()
    if error is not None:
        return error
    assert credentials is not None

    username, password = credentials
    password_hash = generate_password_hash(password)
    db = get_db()

    try:
        cursor = db.execute(
            "INSERT INTO users (username, password_hash, role) VALUES (?, ?, 'user')",
            (username, password_hash),
        )
        db.commit()
    except sqlite3.IntegrityError:
        db.rollback()
        return error_response("USERNAME_TAKEN", "用户名已被注册", 409)

    row = db.execute(
        "SELECT id, username, role, created_at FROM users WHERE id = ?",
        (cursor.lastrowid,),
    ).fetchone()
    return {"user": serialize_user(row)}, 201


@bp.post("/api/auth/login")
def login() -> tuple[dict[str, Any], int]:
    credentials, error = _parse_credentials()
    if error is not None:
        return error
    assert credentials is not None

    username, password = credentials
    db = get_db()
    row = db.execute(
        """
        SELECT id, username, password_hash, role, created_at
        FROM users
        WHERE username = ? AND deleted_at IS NULL
        """,
        (username,),
    ).fetchone()

    if row is None or not check_password_hash(row["password_hash"], password):
        return error_response("INVALID_CREDENTIALS", "用户名或密码错误", 401)

    token = secrets.token_urlsafe(32)
    token_digest = _digest_token(token)
    expires_at = _format_utc(_utc_now() + timedelta(days=SESSION_TTL_DAYS))

    db.execute(
        "INSERT INTO sessions (token_digest, user_id, expires_at) VALUES (?, ?, ?)",
        (token_digest, row["id"], expires_at),
    )
    db.commit()

    return {"token": token, "user": serialize_user(row)}, 200
