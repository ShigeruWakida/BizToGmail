import unittest
from unittest.mock import patch

from biztogmail_app.workflows import _source_message_key, run_smtp_forward_workflow


class DummyLogger:
    def append(self, message: str, *, error: bool = False):
        return None


class DummyConnection:
    def __init__(self):
        self.closed = False

    def close(self):
        self.closed = True


class DummyPopClient:
    def quit(self):
        return None

    def close(self):
        return None


class WorkflowTests(unittest.TestCase):
    def test_run_smtp_forward_workflow_closes_db_connection_when_no_messages(self):
        con = DummyConnection()
        logger = DummyLogger()

        with patch("biztogmail_app.workflows.ensure_db", return_value=con), \
             patch("biztogmail_app.workflows.pop_connect", return_value=DummyPopClient()), \
             patch("biztogmail_app.workflows.pop_uidl_list", return_value=[]), \
             patch("biztogmail_app.workflows.select_pending_entries", return_value=[]):
            result = run_smtp_forward_workflow(
                source_protocol="pop3",
                source_folder=None,
                host="pop.example.com",
                user="user@example.com",
                password="secret",
                port=995,
                use_ssl=True,
                max_items=10,
                destination_email="dest@example.com",
                smtp_host="smtp.example.com",
                smtp_port=465,
                smtp_use_ssl=True,
                smtp_username="user@example.com",
                smtp_password="smtp-secret",
                no_leave_copy=False,
                delete_after_days=None,
                dry_run=False,
                logger=logger,
            )

        self.assertEqual(result["summary"]["errors"], 0)
        self.assertTrue(con.closed)


class SourceMessageKeyTests(unittest.TestCase):
    def test_imap_key_without_account_is_legacy_format(self):
        self.assertEqual(_source_message_key("imap", "INBOX", "1501"), "imap:INBOX:1501")

    def test_pop3_key_without_account_is_legacy_format(self):
        self.assertEqual(_source_message_key("pop3", None, "abc"), "pop3:abc")

    def test_imap_key_is_namespaced_per_account(self):
        # 同一サーバの別アカウントで同じ IMAP UID が来ても衝突しないこと
        self.assertEqual(
            _source_message_key("imap", "INBOX", "1501", account_id=1),
            "imap:acct1:INBOX:1501",
        )
        self.assertNotEqual(
            _source_message_key("imap", "INBOX", "1501", account_id=1),
            _source_message_key("imap", "INBOX", "1501", account_id=4),
        )

    def test_empty_folder_defaults_to_inbox(self):
        self.assertEqual(
            _source_message_key("imap", "", "42", account_id=2),
            "imap:acct2:INBOX:42",
        )
