from __future__ import annotations

import os
import ssl
from pathlib import Path

from sqlalchemy import Column, Integer, MetaData, String, Table, Text, create_engine, inspect, text
from sqlalchemy.engine import Connection, Engine

from .settings import DB_FILE


metadata = MetaData()

messages_table = Table(
    "messages",
    metadata,
    Column("uidl", Text, primary_key=True),
    Column("status", String(32)),
    Column("gmail_id", Text),
    Column("updated_at", Text),
)

accounts_table = Table(
    "accounts",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("email", Text, nullable=False, unique=True),
    Column("pop_host", Text, nullable=False),
    Column("source_username", Text),
    Column("pop_password", Text),
    Column("secret_ref", Text),
    Column("source_protocol", Text, nullable=False, server_default="pop3"),
    Column("source_folder", Text),
    Column("pop_port", Integer, nullable=False, server_default="995"),
    Column("use_ssl", Integer, nullable=False, server_default="1"),
    Column("destination_email", Text),
    Column("smtp_host", Text),
    Column("smtp_port", Integer, nullable=False, server_default="465"),
    Column("smtp_use_ssl", Integer, nullable=False, server_default="1"),
    Column("smtp_username", Text),
    Column("smtp_password", Text),
    Column("smtp_secret_ref", Text),
    Column("leave_copy", Integer, nullable=False, server_default="1"),
    Column("delete_after_days", Integer),
    Column("check_interval_minutes", Integer, nullable=False, server_default="5"),
    Column("max_per_run", Integer, nullable=False, server_default="10"),
    Column("enabled", Integer, nullable=False, server_default="1"),
    Column("last_checked_at", Text),
    Column("next_check_at", Text),
    Column("created_at", Text, nullable=False),
    Column("updated_at", Text, nullable=False),
)

account_execution_locks_table = Table(
    "account_execution_locks",
    metadata,
    Column("account_id", Integer, primary_key=True),
    Column("owner", Text, nullable=False),
    Column("expires_at", Text, nullable=False),
    Column("created_at", Text, nullable=False),
)


_ENGINE: Engine | None = None


def get_database_url() -> str:
    url = os.environ.get("DATABASE_URL") or f"sqlite:///{Path(DB_FILE).resolve().as_posix()}"
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+pg8000://", 1)
    if "pg8000" in url:
        url = url.split("?sslmode=")[0]
    return url


def _needs_ssl(url: str) -> bool:
    return "pg8000" in url and "/cloudsql/" not in url


def get_engine() -> Engine:
    global _ENGINE
    if _ENGINE is None:
        url = get_database_url()
        if url.startswith("sqlite:"):
            connect_args = {"check_same_thread": False}
        elif _needs_ssl(url):
            connect_args = {"ssl_context": ssl.create_default_context()}
        else:
            connect_args = {}
        _ENGINE = create_engine(url, future=True, connect_args=connect_args)
    return _ENGINE


def reset_engine():
    global _ENGINE
    if _ENGINE is not None:
        _ENGINE.dispose()
        _ENGINE = None


def ensure_schema() -> Engine:
    engine = get_engine()
    metadata.create_all(engine)
    _migrate_accounts_table(engine)
    return engine


def connect() -> Connection:
    engine = ensure_schema()
    return engine.connect()


def _migrate_accounts_table(engine: Engine):
    inspector = inspect(engine)
    if "accounts" not in inspector.get_table_names():
        return
    columns = {column["name"] for column in inspector.get_columns("accounts")}
    migration_sql = {
        "pop_password": "ALTER TABLE accounts ADD COLUMN pop_password TEXT",
        "source_username": "ALTER TABLE accounts ADD COLUMN source_username TEXT",
        "secret_ref": "ALTER TABLE accounts ADD COLUMN secret_ref TEXT",
        "source_protocol": "ALTER TABLE accounts ADD COLUMN source_protocol TEXT NOT NULL DEFAULT 'pop3'",
        "source_folder": "ALTER TABLE accounts ADD COLUMN source_folder TEXT",
        "destination_email": "ALTER TABLE accounts ADD COLUMN destination_email TEXT",
        "smtp_host": "ALTER TABLE accounts ADD COLUMN smtp_host TEXT",
        "smtp_port": "ALTER TABLE accounts ADD COLUMN smtp_port INTEGER NOT NULL DEFAULT 465",
        "smtp_use_ssl": "ALTER TABLE accounts ADD COLUMN smtp_use_ssl INTEGER NOT NULL DEFAULT 1",
        "smtp_username": "ALTER TABLE accounts ADD COLUMN smtp_username TEXT",
        "smtp_password": "ALTER TABLE accounts ADD COLUMN smtp_password TEXT",
        "smtp_secret_ref": "ALTER TABLE accounts ADD COLUMN smtp_secret_ref TEXT",
        "max_per_run": "ALTER TABLE accounts ADD COLUMN max_per_run INTEGER NOT NULL DEFAULT 10",
    }
    with engine.begin() as con:
        for name, sql in migration_sql.items():
            if name not in columns:
                con.execute(text(sql))
        con.execute(
            text(
                "UPDATE accounts SET source_username = email "
                "WHERE source_username IS NULL OR source_username = ''"
            )
        )
