from __future__ import annotations

import poplib
from uuid import uuid4

from .accounts import (
    acquire_saved_account_lock,
    get_saved_account,
    list_due_accounts,
    mark_account_checked,
    release_saved_account_lock,
    update_account_max_per_run,
)
from .logging_utils import RunLogger
from .secrets import invalidate_secret_ref, resolve_account_password, resolve_account_smtp_password
from .workflows import run_smtp_forward_workflow


class AccountExecutionLockedError(RuntimeError):
    pass


def run_account_now(account_id: int, logger: RunLogger | None = None):
    active_logger = logger or RunLogger()
    active_logger.setup(f"account-{account_id}")
    account = get_saved_account(account_id)
    if account is None:
        raise ValueError(f"Account not found: {account_id}")
    lock_owner = str(uuid4())
    if not acquire_saved_account_lock(account_id, lock_owner):
        raise AccountExecutionLockedError(f"Account {account_id} is already running")
    password = resolve_account_password(account)
    try:
        if not password:
            raise ValueError(f"Account {account_id} has no usable POP password")

        try:
            result = _run_account_workflow(account, password, active_logger)
        except poplib.error_proto:
            if not account.get("secret_ref"):
                raise
            invalidate_secret_ref(account["secret_ref"])
            refreshed_password = resolve_account_password(account)
            if not refreshed_password or refreshed_password == password:
                raise
            active_logger.append(f"account_id={account_id} POP auth failed; refreshed secret and retrying", error=True)
            result = _run_account_workflow(account, refreshed_password, active_logger)
        updated = mark_account_checked(account_id)
        return {"account": updated or account, "result": result}
    finally:
        release_saved_account_lock(account_id, lock_owner)


def run_due_accounts(logger: RunLogger | None = None):
    active_logger = logger or RunLogger()
    active_logger.setup("scheduler")
    due_accounts = list_due_accounts()
    results = []
    for account in due_accounts:
        try:
            result = run_account_now(account["id"], logger=active_logger)
            _adjust_account_max_per_run(account["id"], result["result"])
            results.append(result)
        except AccountExecutionLockedError as e:
            active_logger.append(f"scheduler skipped locked account_id={account['id']} error={e}")
            results.append({"account": account, "status": "locked", "error": str(e)})
        except Exception as e:
            active_logger.append(f"scheduler failed account_id={account['id']} error={e}", error=True)
            results.append({"account": account, "error": str(e)})
    return results


def _run_account_workflow(account: dict, password: str, logger: RunLogger):
    destination_email = account.get("destination_email")
    if not destination_email:
        raise ValueError(f"Account {account['id']} has no destination_email for SMTP forwarding")
    smtp_host = account.get("smtp_host")
    if not smtp_host:
        raise ValueError(f"Account {account['id']} has no SMTP host")
    smtp_username = account.get("smtp_username")
    if not smtp_username:
        raise ValueError(f"Account {account['id']} has no SMTP username")
    source_host = account.get("pop_host") or smtp_host
    source_username = account.get("source_username") or account.get("smtp_username") or account["email"]
    source_port = account.get("pop_port") or account.get("smtp_port") or 993
    source_use_ssl = account.get("use_ssl")
    if source_use_ssl is None:
        source_use_ssl = account.get("smtp_use_ssl", True)
    smtp_password = resolve_account_smtp_password(account, password)
    if not smtp_password:
        raise ValueError(f"Account {account['id']} has no usable SMTP password")
    return run_smtp_forward_workflow(
        source_protocol=account.get("source_protocol") or "pop3",
        source_folder=account.get("source_folder"),
        host=source_host,
        user=source_username,
        password=password,
        port=source_port,
        use_ssl=source_use_ssl,
        max_items=account.get("max_per_run") or 10,
        destination_email=destination_email,
        smtp_host=smtp_host,
        smtp_port=account.get("smtp_port") or 465,
        smtp_use_ssl=account.get("smtp_use_ssl", True),
        smtp_username=smtp_username,
        smtp_password=smtp_password,
        no_leave_copy=not account["leave_copy"],
        delete_after_days=account["delete_after_days"],
        dry_run=False,
        logger=logger,
        account_id=account["id"],
    )


def _adjust_account_max_per_run(account_id: int, result: dict):
    current_max = int(result.get("max_items") or 10)
    batch_size = int(result.get("batch_size") or 0)
    hit_max = bool(result.get("hit_max"))
    if hit_max:
        next_max = min(current_max * 2, 100)
    else:
        next_max = max(batch_size, 10)
    update_account_max_per_run(account_id, next_max)
