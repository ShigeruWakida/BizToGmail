from __future__ import annotations

import imaplib


def imap_connect(host: str, port: int, use_ssl: bool, user: str, password: str) -> imaplib.IMAP4:
    if use_ssl:
        client = imaplib.IMAP4_SSL(host, port)
    else:
        client = imaplib.IMAP4(host, port)
    client.login(user, password)
    return client


def imap_uid_list(client: imaplib.IMAP4, mailbox: str = "INBOX"):
    status, _ = client.select(mailbox)
    if status != "OK":
        raise RuntimeError(f"Failed to select mailbox: {mailbox}")
    status, data = client.uid("search", None, "ALL")
    if status != "OK":
        raise RuntimeError("Failed to search mailbox")
    raw_uids = data[0].decode("utf-8", "replace").split() if data and data[0] else []
    return [(uid, uid) for uid in raw_uids]


def imap_fetch_raw(client: imaplib.IMAP4, uid: str) -> bytes:
    status, data = client.uid("fetch", uid, "(RFC822)")
    if status != "OK" or not data:
        raise RuntimeError(f"Failed to fetch UID {uid}")
    for item in data:
        if isinstance(item, tuple) and len(item) >= 2 and isinstance(item[1], bytes):
            return item[1]
    raise RuntimeError(f"No message content for UID {uid}")


def imap_delete(client: imaplib.IMAP4, uid: str):
    status, _ = client.uid("store", uid, "+FLAGS.SILENT", r"(\Deleted)")
    if status != "OK":
        raise RuntimeError(f"Failed to mark UID {uid} deleted")
    status, _ = client.expunge()
    if status != "OK":
        raise RuntimeError(f"Failed to expunge UID {uid}")


def imap_close(client: imaplib.IMAP4):
    try:
        client.close()
    except Exception:
        pass
    client.logout()
