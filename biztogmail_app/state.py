from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.engine import Connection

from .db import connect, reset_engine


def ensure_db() -> Connection:
    return connect()


def uidl_seen(con: Connection, uidl: str) -> bool:
    row = con.execute(
        text("SELECT 1 FROM messages WHERE uidl = :uidl AND status = 'imported'"),
        {"uidl": uidl},
    ).first()
    return row is not None


def uidl_mark_imported(con: Connection, uidl: str, gmail_id: str | None):
    con.execute(
        text(
            """
            INSERT INTO messages (uidl, status, gmail_id, updated_at)
            VALUES (:uidl, 'imported', :gmail_id, :updated_at)
            ON CONFLICT (uidl) DO UPDATE
            SET status = 'imported',
                gmail_id = EXCLUDED.gmail_id,
                updated_at = EXCLUDED.updated_at
            """
        ),
        {
            "uidl": uidl,
            "gmail_id": gmail_id,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    con.commit()


def list_accounts(con: Connection):
    rows = con.execute(
        text(
            """
            SELECT id, email, pop_host, pop_port, use_ssl, leave_copy,
                   delete_after_days, check_interval_minutes, max_per_run, enabled, last_checked_at,
                   next_check_at, created_at, updated_at, source_username, pop_password, secret_ref,
                   source_protocol, source_folder, destination_email, smtp_host, smtp_port,
                   smtp_use_ssl, smtp_username, smtp_password, smtp_secret_ref
            FROM accounts
            ORDER BY email
            """
        )
    ).mappings().all()
    return [_account_row_to_dict(row) for row in rows]


def get_account(con: Connection, account_id: int):
    row = con.execute(
        text(
            """
            SELECT id, email, pop_host, pop_port, use_ssl, leave_copy,
                   delete_after_days, check_interval_minutes, max_per_run, enabled, last_checked_at,
                   next_check_at, created_at, updated_at, source_username, pop_password, secret_ref,
                   source_protocol, source_folder, destination_email, smtp_host, smtp_port,
                   smtp_use_ssl, smtp_username, smtp_password, smtp_secret_ref
            FROM accounts
            WHERE id = :account_id
            """
        ),
        {"account_id": account_id},
    ).mappings().first()
    return _account_row_to_dict(row) if row else None


def create_account(
    con: Connection,
    *,
    email: str,
    pop_host: str,
    source_username: str | None,
    pop_password: str | None,
    secret_ref: str | None,
    source_protocol: str,
    source_folder: str | None,
    pop_port: int,
    use_ssl: bool,
    destination_email: str | None = None,
    smtp_host: str | None = None,
    smtp_port: int = 465,
    smtp_use_ssl: bool = True,
    smtp_username: str | None = None,
    smtp_password: str | None = None,
    smtp_secret_ref: str | None = None,
    leave_copy: bool = True,
    delete_after_days: int | None = None,
    check_interval_minutes: int = 5,
    max_per_run: int = 10,
    enabled: bool = True,
):
    now = datetime.now(timezone.utc).isoformat()
    next_check_at = now if enabled else None
    account_id = con.execute(
        text(
            """
            INSERT INTO accounts (
                email, pop_host, source_username, pop_port, use_ssl, source_protocol, source_folder,
                destination_email, smtp_host, smtp_port, smtp_use_ssl, smtp_username, smtp_password,
                smtp_secret_ref, leave_copy, delete_after_days, check_interval_minutes, max_per_run,
                enabled, last_checked_at, next_check_at, created_at, updated_at, pop_password, secret_ref
            ) VALUES (
                :email, :pop_host, :source_username, :pop_port, :use_ssl, :source_protocol, :source_folder,
                :destination_email, :smtp_host, :smtp_port, :smtp_use_ssl, :smtp_username, :smtp_password,
                :smtp_secret_ref, :leave_copy, :delete_after_days, :check_interval_minutes, :max_per_run,
                :enabled, :last_checked_at, :next_check_at, :created_at, :updated_at, :pop_password, :secret_ref
            )
            RETURNING id
            """
        ),
        {
            "email": email,
            "pop_host": pop_host,
            "source_username": source_username,
            "pop_port": pop_port,
            "use_ssl": int(use_ssl),
            "source_protocol": source_protocol,
            "source_folder": source_folder,
            "destination_email": destination_email,
            "smtp_host": smtp_host,
            "smtp_port": smtp_port,
            "smtp_use_ssl": int(smtp_use_ssl),
            "smtp_username": smtp_username,
            "smtp_password": smtp_password,
            "smtp_secret_ref": smtp_secret_ref,
            "leave_copy": int(leave_copy),
            "delete_after_days": delete_after_days,
            "check_interval_minutes": check_interval_minutes,
            "max_per_run": max_per_run,
            "enabled": int(enabled),
            "last_checked_at": None,
            "next_check_at": next_check_at,
            "created_at": now,
            "updated_at": now,
            "pop_password": pop_password,
            "secret_ref": secret_ref,
        },
    ).scalar_one()
    con.commit()
    return get_account(con, account_id)


def update_account(con: Connection, account_id: int, updates: dict):
    if not updates:
        return get_account(con, account_id)

    allowed = {
        "email",
        "pop_host",
        "source_username",
        "pop_password",
        "secret_ref",
        "source_protocol",
        "source_folder",
        "pop_port",
        "use_ssl",
        "destination_email",
        "smtp_host",
        "smtp_port",
        "smtp_use_ssl",
        "smtp_username",
        "smtp_password",
        "smtp_secret_ref",
        "leave_copy",
        "delete_after_days",
        "check_interval_minutes",
        "max_per_run",
        "enabled",
        "last_checked_at",
        "next_check_at",
    }
    normalized = {}
    for key, value in updates.items():
        if key not in allowed:
            continue
        if key in {"use_ssl", "smtp_use_ssl", "leave_copy", "enabled"} and value is not None:
            value = int(bool(value))
        normalized[key] = value

    set_sql = ", ".join(f"{key} = :{key}" for key in normalized)
    normalized["updated_at"] = datetime.now(timezone.utc).isoformat()
    normalized["account_id"] = account_id
    con.execute(
        text(f"UPDATE accounts SET {set_sql}, updated_at = :updated_at WHERE id = :account_id"),
        normalized,
    )
    con.commit()
    return get_account(con, account_id)


def delete_account(con: Connection, account_id: int):
    con.execute(text("DELETE FROM accounts WHERE id = :account_id"), {"account_id": account_id})
    con.commit()


def acquire_account_execution_lock(
    con: Connection,
    account_id: int,
    owner: str,
    *,
    ttl_seconds: int = 900,
) -> bool:
    now = datetime.now(timezone.utc)
    expires_at = (now + timedelta(seconds=ttl_seconds)).isoformat()
    now_iso = now.isoformat()
    con.execute(
        text(
            """
            DELETE FROM account_execution_locks
            WHERE account_id = :account_id
              AND expires_at <= :now
            """
        ),
        {"account_id": account_id, "now": now_iso},
    )
    try:
        con.execute(
            text(
                """
                INSERT INTO account_execution_locks (account_id, owner, expires_at, created_at)
                VALUES (:account_id, :owner, :expires_at, :created_at)
                """
            ),
            {
                "account_id": account_id,
                "owner": owner,
                "expires_at": expires_at,
                "created_at": now_iso,
            },
        )
        con.commit()
        return True
    except IntegrityError:
        con.rollback()
        return False


def release_account_execution_lock(con: Connection, account_id: int, owner: str | None = None):
    params = {"account_id": account_id}
    if owner is None:
        con.execute(
            text("DELETE FROM account_execution_locks WHERE account_id = :account_id"),
            params,
        )
    else:
        params["owner"] = owner
        con.execute(
            text("DELETE FROM account_execution_locks WHERE account_id = :account_id AND owner = :owner"),
            params,
        )
    con.commit()


def _account_row_to_dict(row):
    if row is None:
        return None
    return {
        "id": row["id"],
        "email": row["email"],
        "pop_host": row["pop_host"],
        "pop_port": row["pop_port"],
        "use_ssl": bool(row["use_ssl"]),
        "leave_copy": bool(row["leave_copy"]),
        "delete_after_days": row["delete_after_days"],
        "check_interval_minutes": row["check_interval_minutes"],
        "max_per_run": row["max_per_run"],
        "enabled": bool(row["enabled"]),
        "last_checked_at": row["last_checked_at"],
        "next_check_at": row["next_check_at"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "source_username": row["source_username"] or row["email"],
        "pop_password": row["pop_password"],
        "secret_ref": row["secret_ref"],
        "source_protocol": row["source_protocol"],
        "source_folder": row["source_folder"],
        "destination_email": row["destination_email"],
        "smtp_host": row["smtp_host"],
        "smtp_port": row["smtp_port"],
        "smtp_use_ssl": bool(row["smtp_use_ssl"]),
        "smtp_username": row["smtp_username"],
        "smtp_password": row["smtp_password"],
        "smtp_secret_ref": row["smtp_secret_ref"],
    }


__all__ = [
    "ensure_db",
    "uidl_seen",
    "uidl_mark_imported",
    "list_accounts",
    "get_account",
    "create_account",
    "update_account",
    "delete_account",
    "acquire_account_execution_lock",
    "release_account_execution_lock",
    "reset_engine",
]
