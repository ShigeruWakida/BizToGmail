from __future__ import annotations

from datetime import datetime, timedelta, timezone
from sqlalchemy import text

from .state import create_account, delete_account, ensure_db, get_account, list_accounts, update_account
from .state import acquire_account_execution_lock, release_account_execution_lock


def list_saved_accounts():
    con = ensure_db()
    try:
        return list_accounts(con)
    finally:
        con.close()


def create_saved_account(**kwargs):
    con = ensure_db()
    try:
        return create_account(con, **kwargs)
    finally:
        con.close()


def update_saved_account(account_id: int, updates: dict):
    con = ensure_db()
    try:
        current = get_account(con, account_id)
        if current is None:
            return None
        normalized = dict(updates)

        enabled = normalized.get("enabled", current["enabled"])
        interval = normalized.get("check_interval_minutes", current["check_interval_minutes"])
        if "enabled" in normalized or "check_interval_minutes" in normalized:
            if enabled:
                base = current["last_checked_at"]
                if base:
                    next_check = datetime.fromisoformat(base) + timedelta(minutes=int(interval))
                else:
                    next_check = datetime.now(timezone.utc)
                normalized["next_check_at"] = next_check.isoformat()
            else:
                normalized["next_check_at"] = None

        return update_account(con, account_id, normalized)
    finally:
        con.close()


def get_saved_account(account_id: int):
    con = ensure_db()
    try:
        return get_account(con, account_id)
    finally:
        con.close()


def delete_saved_account(account_id: int):
    con = ensure_db()
    try:
        current = get_account(con, account_id)
        if current is None:
            return None
        delete_account(con, account_id)
        return current
    finally:
        con.close()


def list_due_accounts(now: datetime | None = None):
    current = (now or datetime.now(timezone.utc)).isoformat()
    con = ensure_db()
    try:
        rows = con.execute(
            text(
                """
                SELECT id FROM accounts
                WHERE enabled = 1
                  AND next_check_at IS NOT NULL
                  AND next_check_at <= :current
                ORDER BY next_check_at, email
                """
            ),
            {"current": current},
        ).fetchall()
        return [get_account(con, row[0]) for row in rows]
    finally:
        con.close()


def mark_account_checked(account_id: int, *, now: datetime | None = None):
    current = now or datetime.now(timezone.utc)
    con = ensure_db()
    try:
        account = get_account(con, account_id)
        if account is None:
            return None
        next_check_at = current + timedelta(minutes=int(account["check_interval_minutes"]))
        return update_account(
            con,
            account_id,
            {
                "last_checked_at": current.isoformat(),
                "next_check_at": next_check_at.isoformat() if account["enabled"] else None,
            },
        )
    finally:
        con.close()


def update_account_max_per_run(account_id: int, max_per_run: int):
    con = ensure_db()
    try:
        return update_account(con, account_id, {"max_per_run": max(10, min(100, int(max_per_run)))})
    finally:
        con.close()


def acquire_saved_account_lock(account_id: int, owner: str, *, ttl_seconds: int = 900):
    con = ensure_db()
    try:
        return acquire_account_execution_lock(con, account_id, owner, ttl_seconds=ttl_seconds)
    finally:
        con.close()


def release_saved_account_lock(account_id: int, owner: str | None = None):
    con = ensure_db()
    try:
        release_account_execution_lock(con, account_id, owner)
    finally:
        con.close()
