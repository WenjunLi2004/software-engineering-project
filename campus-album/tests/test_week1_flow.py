"""Week 1 end-to-end verification tests for Campus Album (校园影集)."""

from __future__ import annotations

import contextlib
import hashlib
import json
import os
import re
import socket
import sqlite3
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = PROJECT_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

ISO_UTC_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return int(sock.getsockname()[1])


def _http_json(
    url: str,
    method: str = "GET",
    payload: dict | None = None,
    token: str | None = None,
    timeout: float = 5.0,
) -> tuple[int, dict]:
    """Perform an HTTP JSON request bypassing any system proxy settings."""
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    headers = {"Accept": "application/json"}
    data: bytes | None = None
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json"
    if token is not None:
        headers["Authorization"] = f"Bearer {token}"

    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with opener.open(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8")
            return resp.status, json.loads(body)
    except urllib.error.HTTPError as err:
        body = err.read().decode("utf-8")
        return err.code, json.loads(body)


class Week1ApiTestCase(unittest.TestCase):
    """API contract, auth, validation, ordering, and init-db tests."""

    def setUp(self) -> None:
        from campus_album import create_app

        self._tmp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self._tmp_dir.name) / "campus-album-test.sqlite3"
        self._old_db_env = os.environ.get("CAMPUS_ALBUM_DATABASE")
        os.environ["CAMPUS_ALBUM_DATABASE"] = str(self.db_path)

        self.app = create_app()
        runner = self.app.test_cli_runner()
        with self.app.app_context():
            result = runner.invoke(args=["init-db"])
        self.assertEqual(result.exit_code, 0, msg=f"init-db failed: {result.output}")
        self.client = self.app.test_client()

    def tearDown(self) -> None:
        if self._old_db_env is None:
            os.environ.pop("CAMPUS_ALBUM_DATABASE", None)
        else:
            os.environ["CAMPUS_ALBUM_DATABASE"] = self._old_db_env
        self._tmp_dir.cleanup()

    @contextlib.contextmanager
    def _connect_db(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def assert_error_response(
        self,
        response,
        expected_status: int,
        expected_code: str | None = None,
    ) -> dict:
        self.assertEqual(
            response.status_code,
            expected_status,
            msg=f"Expected HTTP {expected_status}, got {response.status_code}: {response.get_data(as_text=True)}",
        )
        data = response.get_json()
        self.assertIsInstance(data, dict, msg="Error response must be a JSON object")
        self.assertIn("error", data, msg=f"Missing unified 'error' key: {data}")
        err = data["error"]
        self.assertIsInstance(err, dict, msg=f"'error' must be an object: {data}")
        self.assertIsInstance(err.get("code"), str)
        self.assertTrue(err["code"].strip(), msg=f"'error.code' must be non-empty: {data}")
        self.assertIsInstance(err.get("message"), str)
        self.assertTrue(err["message"].strip(), msg=f"'error.message' must be non-empty: {data}")
        if expected_code is not None:
            self.assertEqual(err["code"], expected_code)
        return err

    def _register_and_login(
        self, username: str = "campus_demo", password: str = "szu2026!"
    ) -> tuple[str, dict]:
        reg = self.client.post(
            "/api/auth/register",
            json={"username": username, "password": password},
        )
        self.assertEqual(reg.status_code, 201, msg=reg.get_data(as_text=True))
        login = self.client.post(
            "/api/auth/login",
            json={"username": username, "password": password},
        )
        self.assertEqual(login.status_code, 200, msg=login.get_data(as_text=True))
        body = login.get_json()
        return body["token"], body["user"]

    def test_health_endpoint(self) -> None:
        resp = self.client.get("/api/health")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json(), {"status": "ok"})

    def test_list_posts_empty_on_fresh_db(self) -> None:
        resp = self.client.get("/api/posts")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json(), {"posts": []})

    def test_register_success_duplicate_and_db_storage(self) -> None:
        resp = self.client.post(
            "/api/auth/register",
            json={"username": "campus_demo", "password": "secret_password"},
        )
        self.assertEqual(resp.status_code, 201, msg=resp.get_data(as_text=True))
        body = resp.get_json()
        self.assertIn("user", body)
        user = body["user"]
        self.assertIsInstance(user["id"], int)
        self.assertEqual(user["username"], "campus_demo")
        self.assertNotIn("password", user)
        self.assertNotIn("password_hash", user)

        with self._connect_db() as conn:
            row = conn.execute(
                "SELECT id, username, password_hash, role FROM users WHERE id = ?",
                (user["id"],),
            ).fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row["role"], "user")
        self.assertNotEqual(row["password_hash"], "secret_password")

        dup = self.client.post(
            "/api/auth/register",
            json={"username": "campus_demo", "password": "another_password"},
        )
        self.assert_error_response(dup, 409)

    def test_register_validation_errors(self) -> None:
        bad_payloads = [
            {"username": "", "password": "secret"},
            {"username": "   ", "password": "secret"},
            {"username": "alice", "password": ""},
            {"username": "alice", "password": "   "},
            {"username": "alice"},
            {"password": "secret"},
            {},
            {"username": 123, "password": "secret"},
            {"username": "alice", "password": 456},
        ]
        for payload in bad_payloads:
            with self.subTest(payload=payload):
                resp = self.client.post("/api/auth/register", json=payload)
                self.assert_error_response(resp, 400)

        malformed = self.client.post(
            "/api/auth/register",
            data="{not-valid-json",
            content_type="application/json",
        )
        self.assert_error_response(malformed, 400)

    def test_login_success_wrong_password_and_nonexistent_user(self) -> None:
        reg = self.client.post(
            "/api/auth/register",
            json={"username": "student_a", "password": "correct_password"},
        )
        self.assertEqual(reg.status_code, 201)
        registered_user = reg.get_json()["user"]

        ok = self.client.post(
            "/api/auth/login",
            json={"username": "student_a", "password": "correct_password"},
        )
        self.assertEqual(ok.status_code, 200, msg=ok.get_data(as_text=True))
        ok_body = ok.get_json()
        self.assertIsInstance(ok_body.get("token"), str)
        self.assertTrue(len(ok_body["token"]) >= 16)
        self.assertEqual(ok_body.get("user"), registered_user)

        expected_digest = hashlib.sha256(ok_body["token"].encode("utf-8")).hexdigest()
        with self._connect_db() as conn:
            sess = conn.execute(
                "SELECT token_digest, user_id, expires_at FROM sessions WHERE user_id = ?",
                (registered_user["id"],),
            ).fetchone()
        self.assertIsNotNone(sess)
        self.assertEqual(sess["token_digest"], expected_digest)
        self.assertRegex(sess["expires_at"], ISO_UTC_RE)

        wrong_pw = self.client.post(
            "/api/auth/login",
            json={"username": "student_a", "password": "wrong_password"},
        )
        self.assert_error_response(wrong_pw, 401)

        missing_user = self.client.post(
            "/api/auth/login",
            json={"username": "no_such_student", "password": "any_password"},
        )
        self.assert_error_response(missing_user, 401)

        empty_fields = self.client.post(
            "/api/auth/login",
            json={"username": "", "password": ""},
        )
        self.assert_error_response(empty_fields, 400)

    def test_create_post_auth_guards(self) -> None:
        token, user = self._register_and_login("auth_guard_user", "pass1234")

        no_header = self.client.post("/api/posts", json={"text": "hello"})
        self.assert_error_response(no_header, 401)

        for bad_header in [
            "Token " + token,
            "Bearer",
            "Bearer   ",
            "Bearer definitely-not-a-valid-token",
        ]:
            with self.subTest(authorization=bad_header):
                resp = self.client.post(
                    "/api/posts",
                    json={"text": "hello"},
                    headers={"Authorization": bad_header},
                )
                self.assert_error_response(resp, 401)

        # Expired session must be rejected with 401.
        digest = hashlib.sha256(token.encode("utf-8")).hexdigest()
        with self._connect_db() as conn:
            conn.execute(
                "UPDATE sessions SET expires_at = '2020-01-01T00:00:00Z' WHERE token_digest = ?",
                (digest,),
            )
            conn.commit()
        expired = self.client.post(
            "/api/posts",
            json={"text": "expired session test"},
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assert_error_response(expired, 401)

        # Re-login to get fresh token, then soft-delete user -> must be rejected with 401.
        fresh_login = self.client.post(
            "/api/auth/login",
            json={"username": "auth_guard_user", "password": "pass1234"},
        )
        self.assertEqual(fresh_login.status_code, 200)
        fresh_token = fresh_login.get_json()["token"]
        with self._connect_db() as conn:
            conn.execute(
                "UPDATE users SET deleted_at = '2026-11-20T00:00:00Z' WHERE id = ?",
                (user["id"],),
            )
            conn.commit()
        deleted_resp = self.client.post(
            "/api/posts",
            json={"text": "deleted user test"},
            headers={"Authorization": f"Bearer {fresh_token}"},
        )
        self.assert_error_response(deleted_resp, 401)

    def test_create_post_rejects_blank_and_whitespace(self) -> None:
        token, _ = self._register_and_login("blank_tester", "pass1234")
        headers = {"Authorization": f"Bearer {token}"}

        for payload in [{"text": ""}, {"text": "   "}, {"text": "\t\n  "}, {}, {"text": 999}]:
            with self.subTest(payload=payload):
                resp = self.client.post("/api/posts", json=payload, headers=headers)
                self.assert_error_response(resp, 400)

        listing = self.client.get("/api/posts")
        self.assertEqual(listing.status_code, 200)
        self.assertEqual(listing.get_json(), {"posts": []})

    def test_create_post_trims_whitespace_and_returns_expected_shape(self) -> None:
        token, user = self._register_and_login("campus_demo", "pass1234")
        resp = self.client.post(
            "/api/posts",
            json={"text": "  \n 今天在校运会上认识了新朋友。  \t "},
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(resp.status_code, 201, msg=resp.get_data(as_text=True))
        body = resp.get_json()
        self.assertIn("post", body)
        post = body["post"]
        self.assertIsInstance(post["id"], int)
        self.assertEqual(post["text"], "今天在校运会上认识了新朋友。")
        self.assertEqual(post["author"], {"id": user["id"], "username": "campus_demo"})
        self.assertRegex(post["createdAt"], ISO_UTC_RE)

        feed = self.client.get("/api/posts")
        self.assertEqual(feed.status_code, 200)
        self.assertEqual(feed.get_json(), {"posts": [post]})

    def test_list_posts_ordering_and_visibility_filtering(self) -> None:
        token1, user1 = self._register_and_login("author_one", "pass1234")
        token2, user2 = self._register_and_login("author_two", "pass1234")

        p1 = self.client.post(
            "/api/posts",
            json={"text": "第一条较早的作品"},
            headers={"Authorization": f"Bearer {token1}"},
        ).get_json()["post"]
        p2 = self.client.post(
            "/api/posts",
            json={"text": "同秒较早 ID 的作品"},
            headers={"Authorization": f"Bearer {token1}"},
        ).get_json()["post"]
        p3 = self.client.post(
            "/api/posts",
            json={"text": "同秒较大 ID 的作品"},
            headers={"Authorization": f"Bearer {token1}"},
        ).get_json()["post"]
        p_removed = self.client.post(
            "/api/posts",
            json={"text": "将被管理员移除的作品"},
            headers={"Authorization": f"Bearer {token1}"},
        ).get_json()["post"]
        p_deleted_author = self.client.post(
            "/api/posts",
            json={"text": "已删除用户的作品"},
            headers={"Authorization": f"Bearer {token2}"},
        ).get_json()["post"]

        with self._connect_db() as conn:
            conn.execute(
                "UPDATE posts SET created_at = '2026-11-20T10:00:00Z' WHERE id = ?",
                (p1["id"],),
            )
            conn.execute(
                "UPDATE posts SET created_at = '2026-11-20T12:00:00Z' WHERE id IN (?, ?)",
                (p2["id"], p3["id"]),
            )
            conn.execute(
                "UPDATE posts SET status = 'removed' WHERE id = ?",
                (p_removed["id"],),
            )
            conn.execute(
                "UPDATE users SET deleted_at = '2026-11-20T13:00:00Z' WHERE id = ?",
                (user2["id"],),
            )
            conn.commit()

        feed = self.client.get("/api/posts")
        self.assertEqual(feed.status_code, 200)
        posts = feed.get_json()["posts"]
        returned_ids = [item["id"] for item in posts]
        self.assertEqual(returned_ids, [p3["id"], p2["id"], p1["id"]])
        self.assertNotIn(p_removed["id"], returned_ids)
        self.assertNotIn(p_deleted_author["id"], returned_ids)
        for item in posts:
            self.assertEqual(set(item.keys()), {"id", "text", "author", "createdAt"})
            self.assertEqual(item["author"], {"id": user1["id"], "username": "author_one"})

    def test_init_db_rerun_preserves_existing_rows(self) -> None:
        token, _ = self._register_and_login("persist_user", "pass1234")
        created = self.client.post(
            "/api/posts",
            json={"text": "重复 init-db 后仍然保留"},
            headers={"Authorization": f"Bearer {token}"},
        ).get_json()["post"]

        with self.app.app_context():
            rerun = self.app.test_cli_runner().invoke(args=["init-db"])
        self.assertEqual(rerun.exit_code, 0, msg=rerun.output)

        feed = self.client.get("/api/posts")
        self.assertEqual(feed.status_code, 200)
        self.assertEqual(feed.get_json()["posts"], [created])


class Week1LiveRestartPersistenceTestCase(unittest.TestCase):
    """Live Flask subprocess test verifying SQLite persistence across server restart."""

    def _run_init_db(self, db_path: Path) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        env["CAMPUS_ALBUM_DATABASE"] = str(db_path)
        proc = subprocess.run(
            [sys.executable, "-m", "flask", "--app", "backend/campus_album", "init-db"],
            cwd=str(PROJECT_ROOT),
            env=env,
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
        self.assertEqual(
            proc.returncode,
            0,
            msg=f"init-db failed (rc={proc.returncode}): stdout={proc.stdout} stderr={proc.stderr}",
        )
        return proc

    def _start_flask_server(self, db_path: Path, port: int) -> subprocess.Popen[str]:
        env = os.environ.copy()
        env["CAMPUS_ALBUM_DATABASE"] = str(db_path)
        proc = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "flask",
                "--app",
                "backend/campus_album",
                "run",
                "--host",
                "127.0.0.1",
                "--port",
                str(port),
            ],
            cwd=str(PROJECT_ROOT),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        deadline = time.monotonic() + 12.0
        health_url = f"http://127.0.0.1:{port}/api/health"
        last_error: Exception | None = None
        while time.monotonic() < deadline:
            if proc.poll() is not None:
                output = proc.stdout.read() if proc.stdout else ""
                self.fail(f"Flask server exited early (rc={proc.returncode}): {output}")
            try:
                status, body = _http_json(health_url, timeout=1.0)
                if status == 200 and body == {"status": "ok"}:
                    return proc
            except Exception as exc:  # noqa: BLE001
                last_error = exc
            time.sleep(0.15)

        self._stop_flask_server(proc)
        self.fail(f"Timed out waiting for Flask server on port {port}: {last_error}")

    def _stop_flask_server(self, proc: subprocess.Popen[str]) -> None:
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=5.0)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=5.0)
        if proc.stdout is not None:
            proc.stdout.close()

    def test_post_persists_across_flask_restart_and_init_db_rerun(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = Path(tmp_dir) / "live-restart.sqlite3"
            self._run_init_db(db_path)

            port_before = _find_free_port()
            proc1 = self._start_flask_server(db_path, port_before)
            base_before = f"http://127.0.0.1:{port_before}"
            try:
                status, health = _http_json(f"{base_before}/api/health")
                self.assertEqual(status, 200)
                self.assertEqual(health, {"status": "ok"})

                status, empty_feed = _http_json(f"{base_before}/api/posts")
                self.assertEqual(status, 200)
                self.assertEqual(empty_feed, {"posts": []})

                status, reg = _http_json(
                    f"{base_before}/api/auth/register",
                    method="POST",
                    payload={"username": "szu_week1", "password": "campus_pass_2026"},
                )
                self.assertEqual(status, 201)
                self.assertEqual(reg["user"]["username"], "szu_week1")

                status, login = _http_json(
                    f"{base_before}/api/auth/login",
                    method="POST",
                    payload={"username": "szu_week1", "password": "campus_pass_2026"},
                )
                self.assertEqual(status, 200)
                token = login["token"]

                status, created = _http_json(
                    f"{base_before}/api/posts",
                    method="POST",
                    payload={"text": "  今天在校运会上认识了新朋友，荔园晚风很舒服！  "},
                    token=token,
                )
                self.assertEqual(status, 201)
                created_post = created["post"]
                self.assertEqual(created_post["text"], "今天在校运会上认识了新朋友，荔园晚风很舒服！")
                self.assertEqual(created_post["author"]["username"], "szu_week1")
                self.assertRegex(created_post["createdAt"], ISO_UTC_RE)

                status, feed_before = _http_json(f"{base_before}/api/posts")
                self.assertEqual(status, 200)
                self.assertEqual(feed_before["posts"], [created_post])
            finally:
                self._stop_flask_server(proc1)

            # Confirm first server process is completely terminated.
            self.assertIsNotNone(proc1.poll())
            with self.assertRaises(OSError):
                _http_json(f"{base_before}/api/health", timeout=1.0)

            # Re-run init-db against the same database file to prove rows are preserved.
            self._run_init_db(db_path)

            # Start a brand-new Flask subprocess pointing at the same SQLite DB.
            port_after = _find_free_port()
            proc2 = self._start_flask_server(db_path, port_after)
            base_after = f"http://127.0.0.1:{port_after}"
            try:
                status, feed_after = _http_json(f"{base_after}/api/posts")
                self.assertEqual(status, 200)
                self.assertEqual(len(feed_after["posts"]), 1)
                persisted = feed_after["posts"][0]
                self.assertEqual(persisted["id"], created_post["id"])
                self.assertEqual(persisted["text"], created_post["text"])
                self.assertEqual(persisted["author"], created_post["author"])
                self.assertEqual(persisted["createdAt"], created_post["createdAt"])

                # Session token from before restart also remains valid in SQLite.
                status, second_post = _http_json(
                    f"{base_after}/api/posts",
                    method="POST",
                    payload={"text": "重启后端后使用旧令牌再次发布成功"},
                    token=token,
                )
                self.assertEqual(status, 201)
                status, feed_after_second = _http_json(f"{base_after}/api/posts")
                self.assertEqual(status, 200)
                self.assertEqual(
                    [p["id"] for p in feed_after_second["posts"]],
                    [second_post["post"]["id"], created_post["id"]],
                )
            finally:
                self._stop_flask_server(proc2)


if __name__ == "__main__":
    unittest.main()
