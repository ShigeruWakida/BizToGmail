import unittest
from unittest.mock import patch
import poplib

from biztogmail_app.logging_utils import RunLogger
from biztogmail_app.scheduler import AccountExecutionLockedError, run_account_now, run_due_accounts


class SchedulerTests(unittest.TestCase):
    def test_run_account_now_requires_stored_password(self):
        logger = RunLogger()
        logger.setup("test")
        with patch("biztogmail_app.scheduler.get_saved_account", return_value={"id": 1, "pop_password": None, "smtp_password": None, "secret_ref": None, "smtp_secret_ref": None}):
            with self.assertRaises(ValueError):
                run_account_now(1, logger=logger)

    def test_run_account_now_uses_secret_ref(self):
        logger = RunLogger()
        logger.setup("test")
        account = {
            "id": 1,
            "email": "user@example.com",
            "source_username": "source-user@example.com",
            "pop_host": "pop.example.com",
            "pop_password": None,
            "secret_ref": "env:POP_SECRET",
            "source_protocol": "pop3",
            "source_folder": None,
            "pop_port": 995,
            "use_ssl": True,
            "destination_email": "dest@gmail.com",
            "smtp_host": "smtp.example.com",
            "smtp_port": 465,
            "smtp_use_ssl": True,
            "smtp_username": "user@example.com",
            "smtp_password": "smtp-secret",
            "smtp_secret_ref": None,
            "leave_copy": True,
            "delete_after_days": None,
        }
        with patch("biztogmail_app.scheduler.get_saved_account", return_value=account), \
             patch("biztogmail_app.scheduler.acquire_saved_account_lock", return_value=True), \
             patch("biztogmail_app.scheduler.release_saved_account_lock"), \
             patch("biztogmail_app.scheduler.resolve_account_password", return_value="resolved-secret"), \
             patch("biztogmail_app.scheduler.run_smtp_forward_workflow", return_value={"events": [], "summary": {"imported": 0, "skipped": 0, "errors": 0}}) as workflow, \
             patch("biztogmail_app.scheduler.mark_account_checked", return_value=account):
            run_account_now(1, logger=logger)

        self.assertEqual(workflow.call_args.kwargs["password"], "resolved-secret")
        self.assertEqual(workflow.call_args.kwargs["user"], "source-user@example.com")
        self.assertEqual(workflow.call_args.kwargs["destination_email"], "dest@gmail.com")

    def test_run_account_now_invalidates_and_retries_on_pop_auth_error(self):
        logger = RunLogger()
        logger.setup("test")
        account = {
            "id": 1,
            "email": "user@example.com",
            "source_username": "user@example.com",
            "pop_host": "pop.example.com",
            "pop_password": None,
            "secret_ref": "env:POP_SECRET",
            "source_protocol": "pop3",
            "source_folder": None,
            "pop_port": 995,
            "use_ssl": True,
            "destination_email": "dest@gmail.com",
            "smtp_host": "smtp.example.com",
            "smtp_port": 465,
            "smtp_use_ssl": True,
            "smtp_username": "user@example.com",
            "smtp_password": None,
            "smtp_secret_ref": None,
            "leave_copy": True,
            "delete_after_days": None,
        }
        with patch("biztogmail_app.scheduler.get_saved_account", return_value=account), \
             patch("biztogmail_app.scheduler.acquire_saved_account_lock", return_value=True), \
             patch("biztogmail_app.scheduler.release_saved_account_lock"), \
             patch("biztogmail_app.scheduler.resolve_account_password", side_effect=["old-secret", "new-secret"]), \
             patch("biztogmail_app.scheduler.invalidate_secret_ref") as invalidate, \
             patch("biztogmail_app.scheduler._run_account_workflow", side_effect=[poplib.error_proto("auth failed"), {"events": [], "summary": {"imported": 0, "skipped": 0, "errors": 0}}]) as workflow, \
             patch("biztogmail_app.scheduler.mark_account_checked", return_value=account):
            result = run_account_now(1, logger=logger)

        invalidate.assert_called_once_with("env:POP_SECRET")
        self.assertEqual(workflow.call_count, 2)
        self.assertEqual(result["result"]["summary"]["errors"], 0)

    def test_run_due_accounts_runs_only_due_accounts(self):
        logger = RunLogger()
        logger.setup("test")
        due_accounts = [
            {
                "id": 1,
                "email": "user@example.com",
                "source_username": "user@example.com",
                "pop_host": "pop.example.com",
                "pop_password": "pw",
                "source_protocol": "pop3",
                "source_folder": None,
                "pop_port": 995,
                "use_ssl": True,
                "destination_email": "dest@gmail.com",
                "smtp_host": "smtp.example.com",
                "smtp_port": 465,
                "smtp_use_ssl": True,
                "smtp_username": "user@example.com",
                "smtp_password": None,
                "smtp_secret_ref": None,
                "leave_copy": True,
                "delete_after_days": None,
                "check_interval_minutes": 5,
                "max_per_run": 10,
                "enabled": True,
            }
        ]
        with patch("biztogmail_app.scheduler.list_due_accounts", return_value=due_accounts), \
             patch("biztogmail_app.scheduler.run_account_now", return_value={"account": due_accounts[0], "result": {"events": [], "summary": {"imported": 1, "skipped": 0, "errors": 0}}}):
            results = run_due_accounts(logger=logger)

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["result"]["summary"]["imported"], 1)

    def test_run_due_accounts_doubles_max_when_batch_hits_limit(self):
        logger = RunLogger()
        logger.setup("test")
        due_account = {
            "id": 1,
            "email": "user@example.com",
            "max_per_run": 10,
        }
        with patch("biztogmail_app.scheduler.list_due_accounts", return_value=[due_account]), \
             patch("biztogmail_app.scheduler.run_account_now", return_value={"account": due_account, "result": {"events": [], "summary": {"imported": 10, "skipped": 0, "errors": 0}, "batch_size": 10, "hit_max": True, "max_items": 10}}), \
             patch("biztogmail_app.scheduler.update_account_max_per_run") as update_max:
            run_due_accounts(logger=logger)

        update_max.assert_called_once_with(1, 20)

    def test_run_due_accounts_shrinks_max_to_batch_floor_10_when_not_hitting_limit(self):
        logger = RunLogger()
        logger.setup("test")
        due_account = {
            "id": 1,
            "email": "user@example.com",
            "max_per_run": 40,
        }
        with patch("biztogmail_app.scheduler.list_due_accounts", return_value=[due_account]), \
             patch("biztogmail_app.scheduler.run_account_now", return_value={"account": due_account, "result": {"events": [], "summary": {"imported": 12, "skipped": 0, "errors": 0}, "batch_size": 12, "hit_max": False, "max_items": 40}}), \
             patch("biztogmail_app.scheduler.update_account_max_per_run") as update_max:
            run_due_accounts(logger=logger)

        update_max.assert_called_once_with(1, 12)

    def test_run_account_now_uses_smtp_forward_settings(self):
        logger = RunLogger()
        logger.setup("test")
        account = {
            "id": 1,
            "email": "user@example.com",
            "source_username": "user@example.com",
            "pop_host": "pop.example.com",
            "pop_password": "pw",
            "secret_ref": None,
            "source_protocol": "pop3",
            "source_folder": None,
            "pop_port": 995,
            "use_ssl": True,
            "destination_email": "dest@gmail.com",
            "smtp_host": "smtp.example.com",
            "smtp_port": 465,
            "smtp_use_ssl": True,
            "smtp_username": "user@example.com",
            "smtp_password": "smtp-pw",
            "smtp_secret_ref": None,
            "leave_copy": True,
            "delete_after_days": None,
        }
        with patch("biztogmail_app.scheduler.get_saved_account", return_value=account), \
             patch("biztogmail_app.scheduler.acquire_saved_account_lock", return_value=True), \
             patch("biztogmail_app.scheduler.release_saved_account_lock"), \
             patch("biztogmail_app.scheduler.resolve_account_password", return_value="pop-secret"), \
             patch("biztogmail_app.scheduler.run_smtp_forward_workflow", return_value={"events": [], "summary": {"imported": 1, "skipped": 0, "errors": 0}}) as workflow, \
             patch("biztogmail_app.scheduler.mark_account_checked", return_value=account):
            result = run_account_now(1, logger=logger)

        self.assertEqual(workflow.call_args.kwargs["destination_email"], "dest@gmail.com")
        self.assertEqual(workflow.call_args.kwargs["smtp_password"], "smtp-pw")
        self.assertEqual(result["result"]["summary"]["imported"], 1)

    def test_run_account_now_supports_imap_source(self):
        logger = RunLogger()
        logger.setup("test")
        account = {
            "id": 1,
            "email": "user@example.com",
            "source_username": "user@example.com",
            "pop_host": "imap.example.com",
            "pop_password": "pw",
            "secret_ref": None,
            "source_protocol": "imap",
            "source_folder": "INBOX",
            "pop_port": 993,
            "use_ssl": True,
            "destination_email": "dest@gmail.com",
            "smtp_host": "smtp.example.com",
            "smtp_port": 465,
            "smtp_use_ssl": True,
            "smtp_username": "user@example.com",
            "smtp_password": "smtp-pw",
            "smtp_secret_ref": None,
            "leave_copy": True,
            "delete_after_days": None,
        }
        with patch("biztogmail_app.scheduler.get_saved_account", return_value=account), \
             patch("biztogmail_app.scheduler.acquire_saved_account_lock", return_value=True), \
             patch("biztogmail_app.scheduler.release_saved_account_lock"), \
             patch("biztogmail_app.scheduler.resolve_account_password", return_value="pop-secret"), \
             patch("biztogmail_app.scheduler.run_smtp_forward_workflow", return_value={"events": [], "summary": {"imported": 1, "skipped": 0, "errors": 0}}) as workflow, \
             patch("biztogmail_app.scheduler.mark_account_checked", return_value=account):
            run_account_now(1, logger=logger)

        self.assertEqual(workflow.call_args.kwargs["source_protocol"], "imap")
        self.assertEqual(workflow.call_args.kwargs["source_folder"], "INBOX")

    def test_run_account_now_raises_when_lock_is_held(self):
        logger = RunLogger()
        logger.setup("test")
        account = {"id": 1, "pop_password": "pw", "secret_ref": None, "smtp_secret_ref": None}
        with patch("biztogmail_app.scheduler.get_saved_account", return_value=account), \
             patch("biztogmail_app.scheduler.acquire_saved_account_lock", return_value=False):
            with self.assertRaises(AccountExecutionLockedError):
                run_account_now(1, logger=logger)

    def test_run_due_accounts_marks_locked_account_as_locked(self):
        logger = RunLogger()
        logger.setup("test")
        due_account = {"id": 1, "email": "user@example.com", "max_per_run": 10}
        with patch("biztogmail_app.scheduler.list_due_accounts", return_value=[due_account]), \
             patch("biztogmail_app.scheduler.run_account_now", side_effect=AccountExecutionLockedError("Account 1 is already running")):
            results = run_due_accounts(logger=logger)

        self.assertEqual(results[0]["status"], "locked")
        self.assertEqual(results[0]["error"], "Account 1 is already running")
