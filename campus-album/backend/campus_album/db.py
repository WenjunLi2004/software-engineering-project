import sqlite3

import click
from flask import Flask, current_app, g


def get_db() -> sqlite3.Connection:
    if "db" not in g:
        connection = sqlite3.connect(current_app.config["DATABASE"])
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        g.db = connection
    return g.db


def close_db(_error: BaseException | None) -> None:
    connection = g.pop("db", None)
    if connection is not None:
        connection.close()


@click.command("init-db")
def init_db() -> None:
    """Create the initial tables and preserve existing rows."""
    with current_app.open_resource("schema.sql", mode="r", encoding="utf-8") as schema:
        get_db().executescript(schema.read())
    click.echo("Campus Album database is ready.")


def init_app(app: Flask) -> None:
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db)
