from __future__ import annotations

from email import policy
from email.parser import BytesParser

from .imap_client import imap_close, imap_connect, imap_delete, imap_fetch_raw, imap_uid_list
from .logging_utils import RunLogger
from .pop3_client import pop_connect, pop_fetch_raw, pop_uidl_list
from .services import evaluate_deletion, select_pending_entries
from .smtp_client import send_raw_via_smtp
from .state import ensure_db, uidl_mark_imported, uidl_seen


def run_smtp_forward_workflow(
    *,
    source_protocol: str,
    source_folder: str | None,
    host: str,
    user: str,
    password: str,
    port: int,
    use_ssl: bool,
    max_items: int,
    destination_email: str,
    smtp_host: str,
    smtp_port: int,
    smtp_use_ssl: bool,
    smtp_username: str | None,
    smtp_password: str | None,
    no_leave_copy: bool,
    delete_after_days: int | None,
    dry_run: bool,
    logger: RunLogger,
):
    logger.append(
        f"smtp-forward start protocol={source_protocol} host={host} user={user} max={max_items} dry_run={dry_run} destination={destination_email}"
    )
    con = ensure_db()

    client = None
    events: list[str] = []
    imported = 0
    skipped = 0
    errors = 0
    normalized_protocol = (source_protocol or "pop3").lower()
    mailbox = source_folder or "INBOX"
    try:
        if normalized_protocol == "imap":
            client = imap_connect(host, port, use_ssl, user, password)
            entries = imap_uid_list(client, mailbox=mailbox)
        else:
            client = pop_connect(host, port, use_ssl, user, password)
            entries = pop_uidl_list(client)
        selections = select_pending_entries(
            entries,
            lambda source_id: uidl_seen(con, _source_message_key(normalized_protocol, mailbox, source_id)),
            max_items,
        )
        if not selections:
            return {
                "events": ["No pending messages."],
                "summary": {"imported": 0, "skipped": 0, "errors": 0},
                "batch_size": 0,
                "hit_max": False,
                "max_items": max_items,
            }

        events.append(f"to forward: {len(selections)} (max {max_items})")
        for message_ref, source_id in selections:
            try:
                if normalized_protocol == "imap":
                    raw = imap_fetch_raw(client, message_ref)
                else:
                    raw = pop_fetch_raw(client, message_ref)
                if len(raw) > 35 * 1024 * 1024:
                    events.append(f"- ID={source_id}: skip (size {len(raw)} bytes)")
                    skipped += 1
                    continue
                try:
                    msg = BytesParser(policy=policy.default).parsebytes(raw)
                    subject = msg.get("Subject", "(no subject)")
                except Exception:
                    msg = None
                    subject = "(parse error)"

                if dry_run:
                    events.append(f"- [DRY-RUN] ID={source_id}: {subject}")
                    skipped += 1
                    continue

                send_raw_via_smtp(
                    smtp_host=smtp_host,
                    smtp_port=smtp_port,
                    use_ssl=smtp_use_ssl,
                    username=smtp_username,
                    password=smtp_password,
                    destination_email=destination_email,
                    raw_bytes=raw,
                )

                should_delete = False
                if msg is not None:
                    should_delete, _ = evaluate_deletion(msg.get("Date"), not no_leave_copy, delete_after_days)
                elif no_leave_copy:
                    should_delete = True

                note = ""
                if should_delete:
                    try:
                        if normalized_protocol == "imap":
                            imap_delete(client, message_ref)
                            note = " (mailbox deleted)"
                        else:
                            client.dele(message_ref)
                            note = " (server deleted)"
                    except Exception:
                        note = " (server delete failed)"

                uidl_mark_imported(con, _source_message_key(normalized_protocol, mailbox, source_id), None)
                events.append(f"- ID={source_id}: Forwarded via SMTP{note} | {subject}")
                imported += 1
            except Exception as e:
                events.append(f"- ID={source_id}: failed {e}")
                logger.append(f"smtp forward failed source_id={source_id} error={e}", error=True)
                errors += 1
    finally:
        if client is not None:
            if normalized_protocol == "imap":
                imap_close(client)
            else:
                try:
                    client.quit()
                except Exception:
                    client.close()

    summary = {"imported": imported, "skipped": skipped, "errors": errors}
    logger.append(f"smtp-forward done imported={imported} skipped={skipped} errors={errors}")
    return {
        "events": events,
        "summary": summary,
        "batch_size": len(selections),
        "hit_max": len(selections) >= max_items,
        "max_items": max_items,
    }


def _source_message_key(source_protocol: str, source_folder: str | None, source_id: str) -> str:
    normalized_protocol = (source_protocol or "pop3").lower()
    if normalized_protocol == "imap":
        return f"imap:{source_folder or 'INBOX'}:{source_id}"
    return f"pop3:{source_id}"
