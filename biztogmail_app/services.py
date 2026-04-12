from __future__ import annotations

from datetime import datetime, timezone
from email.utils import parsedate_to_datetime


def select_pending_entries(entries, uidl_seen_fn, max_items: int):
    selections = []
    for msg_num, uidl in reversed(entries):
        if uidl_seen_fn(uidl):
            continue
        selections.append((msg_num, uidl))
        if len(selections) >= max_items:
            break
    selections.reverse()
    return selections


def evaluate_deletion(date_header: str | None, leave_copy: bool, delete_after_days: int | None):
    if not leave_copy:
        return True, "no-leave-copy"
    if delete_after_days is None:
        return False, ""
    try:
        dt = parsedate_to_datetime(date_header) if date_header else None
        if dt is None:
            return False, "no Date"
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        age_days = (datetime.now(timezone.utc) - dt.astimezone(timezone.utc)).days
        if age_days >= int(delete_after_days):
            return True, f"age={age_days}d>=N"
        return False, f"age={age_days}d<N"
    except Exception:
        return False, "date-parse-error"
