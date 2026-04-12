from datetime import datetime
import os
import unittest
from pathlib import Path

from biztogmail_app import accounts, state
from biztogmail_app.db import reset_engine


TEST_TMP_DIR = Path(__file__).resolve().parent / ".tmp"
TEST_TMP_DIR.mkdir(exist_ok=True)


class AccountPersistenceTests(unittest.TestCase):
    def setUp(self):
        reset_engine()

    def tearDown(self):
        reset_engine()

    def test_create_and_list_accounts(self):
        db_path = TEST_TMP_DIR / "accounts-create.db"
        if db_path.exists():
            db_path.unlink()
        self.addCleanup(lambda: db_path.unlink(missing_ok=True))
        os.environ["DATABASE_URL"] = f"sqlite:///{db_path.as_posix()}"
        self.addCleanup(lambda: os.environ.pop("DATABASE_URL", None))
        try:
            created = accounts.create_saved_account(
                email="user@example.com",
                pop_host="pop.example.com",
                source_username="user@example.com",
                pop_password=None,
                secret_ref="env:POP_SECRET",
                source_protocol="pop3",
                source_folder=None,
                pop_port=995,
                use_ssl=True,
                destination_email="dest@gmail.com",
                smtp_host="smtp.example.com",
                smtp_port=465,
                smtp_use_ssl=True,
                smtp_username="user@example.com",
                smtp_password=None,
                smtp_secret_ref="env:SMTP_SECRET",
                leave_copy=True,
                delete_after_days=30,
                check_interval_minutes=10,
                enabled=True,
            )
            listed = accounts.list_saved_accounts()
        finally:
            reset_engine()

        self.assertEqual(created["email"], "user@example.com")
        self.assertEqual(created["destination_email"], "dest@gmail.com")
        self.assertEqual(created["source_username"], "user@example.com")
        self.assertEqual(created["source_protocol"], "pop3")
        self.assertIsNone(created["pop_password"])
        self.assertEqual(created["secret_ref"], "env:POP_SECRET")
        self.assertEqual(len(listed), 1)
        self.assertEqual(listed[0]["check_interval_minutes"], 10)

    def test_update_account_changes_interval_and_enabled(self):
        db_path = TEST_TMP_DIR / "accounts-update.db"
        if db_path.exists():
            db_path.unlink()
        self.addCleanup(lambda: db_path.unlink(missing_ok=True))
        os.environ["DATABASE_URL"] = f"sqlite:///{db_path.as_posix()}"
        self.addCleanup(lambda: os.environ.pop("DATABASE_URL", None))
        try:
            created = accounts.create_saved_account(
                email="user@example.com",
                pop_host="pop.example.com",
                source_username="user@example.com",
                pop_password="secret",
                secret_ref=None,
                source_protocol="pop3",
                source_folder=None,
                pop_port=995,
                use_ssl=True,
                destination_email="dest@gmail.com",
                smtp_host="smtp.example.com",
                smtp_port=465,
                smtp_use_ssl=True,
                smtp_username="user@example.com",
                smtp_password=None,
                smtp_secret_ref=None,
                leave_copy=True,
                delete_after_days=None,
                check_interval_minutes=10,
                enabled=True,
            )
            updated = accounts.update_saved_account(
                created["id"],
                {"check_interval_minutes": 30, "enabled": False},
            )
        finally:
            reset_engine()

        self.assertEqual(updated["check_interval_minutes"], 30)
        self.assertFalse(updated["enabled"])
        self.assertEqual(updated["pop_password"], "secret")
        self.assertIsNone(updated["next_check_at"])

    def test_update_account_recomputes_next_check_at_when_interval_changes(self):
        db_path = TEST_TMP_DIR / "accounts-nextcheck.db"
        if db_path.exists():
            db_path.unlink()
        self.addCleanup(lambda: db_path.unlink(missing_ok=True))
        os.environ["DATABASE_URL"] = f"sqlite:///{db_path.as_posix()}"
        self.addCleanup(lambda: os.environ.pop("DATABASE_URL", None))
        try:
            created = accounts.create_saved_account(
                email="user@example.com",
                pop_host="pop.example.com",
                source_username="user@example.com",
                pop_password="secret",
                secret_ref=None,
                source_protocol="pop3",
                source_folder=None,
                pop_port=995,
                use_ssl=True,
                destination_email="dest@gmail.com",
                smtp_host="smtp.example.com",
                smtp_port=465,
                smtp_use_ssl=True,
                smtp_username="user@example.com",
                smtp_password=None,
                smtp_secret_ref=None,
                leave_copy=True,
                delete_after_days=None,
                check_interval_minutes=10,
                enabled=True,
            )
            with_last_checked = accounts.update_saved_account(
                created["id"],
                {"last_checked_at": "2026-01-01T00:00:00+00:00"},
            )
            updated = accounts.update_saved_account(
                created["id"],
                {"check_interval_minutes": 30},
            )
        finally:
            reset_engine()

        self.assertEqual(with_last_checked["last_checked_at"], "2026-01-01T00:00:00+00:00")
        self.assertEqual(updated["next_check_at"], "2026-01-01T00:30:00+00:00")

    def test_list_due_accounts_returns_only_enabled_due_rows(self):
        db_path = TEST_TMP_DIR / "accounts-due.db"
        if db_path.exists():
            db_path.unlink()
        self.addCleanup(lambda: db_path.unlink(missing_ok=True))
        os.environ["DATABASE_URL"] = f"sqlite:///{db_path.as_posix()}"
        self.addCleanup(lambda: os.environ.pop("DATABASE_URL", None))
        try:
            due = accounts.create_saved_account(
                email="due@example.com",
                pop_host="pop.example.com",
                source_username="due@example.com",
                pop_password="pw",
                secret_ref=None,
                source_protocol="pop3",
                source_folder=None,
                pop_port=995,
                use_ssl=True,
                destination_email="dest@gmail.com",
                smtp_host="smtp.example.com",
                smtp_port=465,
                smtp_use_ssl=True,
                smtp_username="user@example.com",
                smtp_password=None,
                smtp_secret_ref=None,
                leave_copy=True,
                delete_after_days=None,
                check_interval_minutes=10,
                enabled=True,
            )
            later = accounts.create_saved_account(
                email="later@example.com",
                pop_host="pop.example.com",
                source_username="later@example.com",
                pop_password="pw",
                secret_ref=None,
                source_protocol="pop3",
                source_folder=None,
                pop_port=995,
                use_ssl=True,
                destination_email="dest@gmail.com",
                smtp_host="smtp.example.com",
                smtp_port=465,
                smtp_use_ssl=True,
                smtp_username="user@example.com",
                smtp_password=None,
                smtp_secret_ref=None,
                leave_copy=True,
                delete_after_days=None,
                check_interval_minutes=10,
                enabled=True,
            )
            accounts.update_saved_account(due["id"], {"next_check_at": "2026-01-01T00:00:00+00:00"})
            accounts.update_saved_account(later["id"], {"next_check_at": "2030-01-01T00:00:00+00:00"})

            due_accounts = accounts.list_due_accounts(
                now=datetime.fromisoformat("2026-01-01T00:05:00+00:00")
            )
        finally:
            reset_engine()

        self.assertEqual([item["email"] for item in due_accounts], ["due@example.com"])

    def test_account_lock_allows_single_holder(self):
        db_path = TEST_TMP_DIR / "accounts-lock.db"
        if db_path.exists():
            db_path.unlink()
        self.addCleanup(lambda: db_path.unlink(missing_ok=True))
        os.environ["DATABASE_URL"] = f"sqlite:///{db_path.as_posix()}"
        self.addCleanup(lambda: os.environ.pop("DATABASE_URL", None))
        try:
            created = accounts.create_saved_account(
                email="lock@example.com",
                pop_host="pop.example.com",
                source_username="lock@example.com",
                pop_password="pw",
                secret_ref=None,
                source_protocol="pop3",
                source_folder=None,
                pop_port=995,
                use_ssl=True,
                destination_email="dest@gmail.com",
                smtp_host="smtp.example.com",
                smtp_port=465,
                smtp_use_ssl=True,
                smtp_username="user@example.com",
                smtp_password=None,
                smtp_secret_ref=None,
                leave_copy=True,
                delete_after_days=None,
                check_interval_minutes=10,
                enabled=True,
            )
            first = accounts.acquire_saved_account_lock(created["id"], "owner-1")
            second = accounts.acquire_saved_account_lock(created["id"], "owner-2")
            accounts.release_saved_account_lock(created["id"], "owner-1")
            third = accounts.acquire_saved_account_lock(created["id"], "owner-3")
        finally:
            reset_engine()

        self.assertTrue(first)
        self.assertFalse(second)
        self.assertTrue(third)
