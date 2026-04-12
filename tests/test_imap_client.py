import unittest

from biztogmail_app.imap_client import imap_fetch_raw, imap_uid_list


class FakeImap:
    def __init__(self):
        self.selected = None

    def select(self, mailbox):
        self.selected = mailbox
        return ("OK", [b"1"])

    def uid(self, command, *args):
        if command == "search":
            return ("OK", [b"101 102"])
        if command == "fetch":
            return ("OK", [(b"1 (RFC822 {12})", b"Subject: Hi\r\n\r\nbody"), b")"])
        raise AssertionError(f"Unexpected command: {command}")


class ImapClientTests(unittest.TestCase):
    def test_imap_uid_list_returns_uid_entries(self):
        client = FakeImap()

        entries = imap_uid_list(client, mailbox="INBOX")

        self.assertEqual(client.selected, "INBOX")
        self.assertEqual(entries, [("101", "101"), ("102", "102")])

    def test_imap_fetch_raw_returns_message_bytes(self):
        client = FakeImap()

        raw = imap_fetch_raw(client, "101")

        self.assertEqual(raw, b"Subject: Hi\r\n\r\nbody")
