from __future__ import annotations

import poplib
from email import policy
from email.parser import BytesParser


def pop_connect(host: str, port: int, use_ssl: bool, user: str, password: str) -> poplib.POP3:
    if use_ssl:
        pop = poplib.POP3_SSL(host, port, timeout=60)
    else:
        pop = poplib.POP3(host, port, timeout=60)
    pop.user(user)
    pop.pass_(password)
    return pop


def pop_uidl_list(pop: poplib.POP3):
    _, items, _ = pop.uidl()
    entries = []
    for item in items:
        decoded = item.decode("utf-8", "replace")
        parts = decoded.split()
        if len(parts) != 2:
            continue
        try:
            msg_num = int(parts[0])
        except ValueError:
            continue
        entries.append((msg_num, parts[1]))
    return entries


def pop_fetch_raw(pop: poplib.POP3, msg_num: int) -> bytes:
    _, lines, _ = pop.retr(msg_num)
    return b"\r\n".join(lines) + b"\r\n"


def pop_fetch_headers(pop: poplib.POP3, msg_num: int) -> bytes:
    _, lines, _ = pop.top(msg_num, 0)
    return b"\r\n".join(lines) + b"\r\n\r\n"


def extract_message_id(header_bytes: bytes) -> str | None:
    try:
        msg = BytesParser(policy=policy.default).parsebytes(header_bytes)
        message_id = msg.get("Message-ID") or msg.get("Message-Id")
        if not message_id:
            return None
        message_id = str(message_id).strip()
        if message_id.startswith("<") and message_id.endswith(">"):
            return message_id[1:-1]
        return message_id
    except Exception:
        return None
