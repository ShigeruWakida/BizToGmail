import unittest
from unittest.mock import patch

from biztogmail_app.workflows import run_smtp_forward_workflow


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
