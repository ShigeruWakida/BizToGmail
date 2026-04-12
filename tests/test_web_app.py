import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from biztogmail_web.app import app


class WebAppTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.user = {"email": "signed-in@gmail.com", "name": "Tester"}

    def test_health_endpoint_is_public(self):
        response = self.client.get("/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    def test_auth_session_returns_authenticated_user(self):
        with patch("biztogmail_web.app.get_google_user", return_value=self.user):
            response = self.client.get("/auth/session")

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["authenticated"])
        self.assertEqual(response.json()["user"]["email"], "signed-in@gmail.com")

    def test_accounts_endpoint_returns_only_owned_accounts(self):
        fake_accounts = [
            {
                "id": 1,
                "email": "user@example.com",
                "source_username": "user@example.com",
                "source_protocol": "pop3",
                "source_folder": None,
                "pop_host": "pop.example.com",
                "pop_port": 995,
                "use_ssl": True,
                "destination_email": "signed-in@gmail.com",
                "smtp_host": "smtp.example.com",
                "smtp_port": 465,
                "smtp_use_ssl": True,
                "smtp_username": "user@example.com",
                "smtp_password": None,
                "smtp_secret_ref": "gcp:projects/demo/secrets/smtp-password-user-example-com/versions/latest",
                "leave_copy": True,
                "delete_after_days": None,
                "check_interval_minutes": 5,
                "enabled": True,
                "last_checked_at": None,
                "next_check_at": None,
                "created_at": "2026-01-01T00:00:00+00:00",
                "updated_at": "2026-01-01T00:00:00+00:00",
            },
            {
                "id": 2,
                "email": "other@example.com",
                "source_username": "other@example.com",
                "source_protocol": "pop3",
                "source_folder": None,
                "pop_host": "pop.example.com",
                "pop_port": 995,
                "use_ssl": True,
                "destination_email": "other@gmail.com",
                "smtp_host": "smtp.example.com",
                "smtp_port": 465,
                "smtp_use_ssl": True,
                "smtp_username": "other@example.com",
                "smtp_password": None,
                "smtp_secret_ref": "gcp:projects/demo/secrets/smtp-password-other-example-com/versions/latest",
                "leave_copy": True,
                "delete_after_days": None,
                "check_interval_minutes": 5,
                "enabled": True,
                "last_checked_at": None,
                "next_check_at": None,
                "created_at": "2026-01-01T00:00:00+00:00",
                "updated_at": "2026-01-01T00:00:00+00:00",
            },
        ]
        with patch("biztogmail_web.app.require_google_user", return_value=self.user), \
             patch("biztogmail_web.app.list_saved_accounts", return_value=fake_accounts):
            response = self.client.get("/accounts")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 1)
        self.assertEqual(response.json()[0]["email"], "user@example.com")

    def test_create_account_returns_created_payload(self):
        created_account = {
            "id": 2,
            "email": "user@example.com",
            "source_username": "user@example.com",
            "source_protocol": "pop3",
            "source_folder": None,
            "pop_host": "pop.example.com",
            "pop_port": 995,
            "use_ssl": True,
            "destination_email": "signed-in@gmail.com",
            "smtp_host": "smtp.example.com",
            "smtp_port": 465,
            "smtp_use_ssl": True,
            "smtp_username": "user@example.com",
            "smtp_password": None,
            "smtp_secret_ref": "gcp:projects/demo/secrets/smtp-password-user-example-com/versions/latest",
            "leave_copy": True,
            "delete_after_days": None,
            "check_interval_minutes": 10,
            "enabled": True,
            "last_checked_at": None,
            "next_check_at": None,
            "created_at": "2026-01-01T00:00:00+00:00",
            "updated_at": "2026-01-01T00:00:00+00:00",
        }
        payload = {
            "email": "user@example.com",
            "source_username": "user@example.com",
            "source_protocol": "pop3",
            "source_folder": None,
            "pop_host": "pop.example.com",
            "pop_password": "secret",
            "pop_port": 995,
            "use_ssl": True,
            "smtp_host": "smtp.example.com",
            "smtp_port": 465,
            "smtp_use_ssl": True,
            "smtp_username": "user@example.com",
            "smtp_password": "smtp-secret",
            "leave_copy": True,
            "delete_after_days": None,
            "check_interval_minutes": 10,
            "enabled": True,
        }
        with patch("biztogmail_web.app.require_google_user", return_value=self.user), \
             patch("biztogmail_web.app.build_source_secret_ref", return_value="gcp:projects/demo/secrets/source-password-user-example-com/versions/latest"), \
             patch("biztogmail_web.app.build_smtp_secret_ref", return_value="gcp:projects/demo/secrets/smtp-password-user-example-com/versions/latest"), \
             patch("biztogmail_web.app.store_secret_value"), \
             patch("biztogmail_web.app.create_saved_account", return_value=created_account):
            response = self.client.post("/accounts", json=payload)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["id"], 2)
        self.assertEqual(response.json()["check_interval_minutes"], 10)

    def test_create_account_stores_passwords_in_secret_manager(self):
        created_account = {
            "id": 2,
            "email": "user@example.com",
            "source_username": "user@example.com",
            "source_protocol": "pop3",
            "source_folder": None,
            "pop_host": "pop.example.com",
            "pop_port": 995,
            "use_ssl": True,
            "destination_email": "signed-in@gmail.com",
            "smtp_host": "smtp.example.com",
            "smtp_port": 465,
            "smtp_use_ssl": True,
            "smtp_username": "user@example.com",
            "smtp_password": None,
            "smtp_secret_ref": "gcp:projects/demo/secrets/smtp-password-user-example-com/versions/latest",
            "leave_copy": True,
            "delete_after_days": None,
            "check_interval_minutes": 10,
            "enabled": True,
            "secret_ref": "gcp:projects/demo/secrets/source-password-user-example-com/versions/latest",
            "last_checked_at": None,
            "next_check_at": None,
            "created_at": "2026-01-01T00:00:00+00:00",
            "updated_at": "2026-01-01T00:00:00+00:00",
        }
        payload = {
            "email": "user@example.com",
            "source_username": "user@example.com",
            "source_protocol": "pop3",
            "source_folder": None,
            "pop_host": "pop.example.com",
            "pop_password": "pop-secret",
            "pop_port": 995,
            "use_ssl": True,
            "smtp_host": "smtp.example.com",
            "smtp_port": 465,
            "smtp_use_ssl": True,
            "smtp_username": "user@example.com",
            "smtp_password": "smtp-secret",
            "leave_copy": True,
            "delete_after_days": None,
            "check_interval_minutes": 10,
            "enabled": True,
        }
        with patch("biztogmail_web.app.require_google_user", return_value=self.user), \
             patch("biztogmail_web.app.build_source_secret_ref", return_value=created_account["secret_ref"]) as build_source_secret_ref, \
             patch("biztogmail_web.app.build_smtp_secret_ref", return_value=created_account["smtp_secret_ref"]) as build_smtp_secret_ref, \
             patch("biztogmail_web.app.store_secret_value") as store_secret_value, \
             patch("biztogmail_web.app.create_saved_account", return_value=created_account) as create_saved_account:
            response = self.client.post("/accounts", json=payload)

        self.assertEqual(response.status_code, 200)
        build_source_secret_ref.assert_called_once_with("user@example.com")
        build_smtp_secret_ref.assert_called_once_with("user@example.com")
        self.assertEqual(store_secret_value.call_count, 2)
        create_saved_account.assert_called_once_with(
            email="user@example.com",
            source_username="user@example.com",
            pop_host="pop.example.com",
            pop_password=None,
            secret_ref="gcp:projects/demo/secrets/source-password-user-example-com/versions/latest",
            source_protocol="pop3",
            source_folder=None,
            pop_port=995,
            use_ssl=True,
            destination_email="signed-in@gmail.com",
            smtp_host="smtp.example.com",
            smtp_port=465,
            smtp_use_ssl=True,
            smtp_username="user@example.com",
            smtp_password=None,
            smtp_secret_ref="gcp:projects/demo/secrets/smtp-password-user-example-com/versions/latest",
            leave_copy=True,
            delete_after_days=None,
            check_interval_minutes=10,
            enabled=True,
        )

    def test_scheduler_tick_returns_payload(self):
        due_account = {"id": 1, "email": "user@example.com", "destination_email": "signed-in@gmail.com"}
        scheduler_result = {
            "account": due_account,
            "result": {"summary": {"imported": 1, "skipped": 0, "errors": 0}},
        }
        with patch("biztogmail_web.app.require_google_user", return_value=self.user), \
             patch("biztogmail_web.app.list_due_accounts", return_value=[due_account]), \
             patch("biztogmail_web.app.run_account_now", return_value=scheduler_result):
            response = self.client.post("/scheduler/tick")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()[0]["status"], "ok")
        self.assertEqual(response.json()[0]["summary"]["imported"], 1)

    def test_scheduler_tick_accepts_scheduler_token_without_google_session(self):
        due_account = {"id": 1, "email": "user@example.com", "destination_email": "signed-in@gmail.com"}
        scheduler_result = {
            "account": due_account,
            "result": {"summary": {"imported": 1, "skipped": 0, "errors": 0}},
        }
        with patch("biztogmail_web.app.get_scheduler_token", return_value="scheduler-secret"), \
             patch("biztogmail_web.app.list_due_accounts", return_value=[due_account]), \
             patch("biztogmail_web.app.run_account_now", return_value=scheduler_result):
            response = self.client.post("/scheduler/tick", headers={"X-Scheduler-Token": "scheduler-secret"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()[0]["status"], "ok")

    def test_scheduler_tick_returns_locked_status_when_account_is_running(self):
        due_account = {"id": 1, "email": "user@example.com", "destination_email": "signed-in@gmail.com"}
        with patch("biztogmail_web.app.require_google_user", return_value=self.user), \
             patch("biztogmail_web.app.list_due_accounts", return_value=[due_account]), \
             patch("biztogmail_web.app.run_account_now", side_effect=RuntimeError("Account 1 is already running")), \
             patch("biztogmail_web.app.AccountExecutionLockedError", RuntimeError):
            response = self.client.post("/scheduler/tick")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()[0]["status"], "locked")

    def test_run_account_returns_409_when_account_is_running(self):
        account = {"id": 2, "email": "user@example.com", "destination_email": "signed-in@gmail.com"}
        with patch("biztogmail_web.app.require_google_user", return_value=self.user), \
             patch("biztogmail_web.app.get_saved_account", return_value=account), \
             patch("biztogmail_web.app.run_account_now", side_effect=RuntimeError("Account 2 is already running")), \
             patch("biztogmail_web.app.AccountExecutionLockedError", RuntimeError):
            response = self.client.post("/accounts/2/run")

        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["detail"], "Account 2 is already running")

    def test_delete_account_returns_deleted_payload(self):
        account = {"id": 2, "email": "user@example.com", "destination_email": "signed-in@gmail.com"}
        with patch("biztogmail_web.app.require_google_user", return_value=self.user), \
             patch("biztogmail_web.app.get_saved_account", return_value=account), \
             patch("biztogmail_web.app.delete_saved_account", return_value=account):
            response = self.client.delete("/accounts/2")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "deleted", "account_id": 2})

    def test_patch_account_updates_payload(self):
        current_account = {
            "id": 2,
            "email": "user@example.com",
            "source_username": "user@example.com",
            "source_protocol": "imap",
            "source_folder": "INBOX",
            "pop_host": "imap.example.com",
            "pop_port": 993,
            "use_ssl": True,
            "destination_email": "signed-in@gmail.com",
            "smtp_host": "smtp.example.com",
            "smtp_port": 465,
            "smtp_use_ssl": True,
            "smtp_username": "user@example.com",
            "smtp_password": None,
            "smtp_secret_ref": "gcp:projects/demo/secrets/smtp-password-user-example-com/versions/latest",
            "leave_copy": True,
            "delete_after_days": None,
            "check_interval_minutes": 10,
            "enabled": True,
            "secret_ref": "gcp:projects/demo/secrets/source-password-user-example-com/versions/latest",
            "last_checked_at": None,
            "next_check_at": None,
            "created_at": "2026-01-01T00:00:00+00:00",
            "updated_at": "2026-01-01T00:00:00+00:00",
        }
        updated_account = dict(current_account)
        updated_account["smtp_host"] = "smtp2.example.com"
        payload = {
            "smtp_host": "smtp2.example.com",
            "smtp_password": "smtp-secret-2",
        }
        with patch("biztogmail_web.app.require_google_user", return_value=self.user), \
             patch("biztogmail_web.app.get_saved_account", return_value=current_account), \
             patch("biztogmail_web.app.store_secret_value") as store_secret_value, \
             patch("biztogmail_web.app.update_saved_account", return_value=updated_account) as update_saved_account:
            response = self.client.patch("/accounts/2", json=payload)

        self.assertEqual(response.status_code, 200)
        store_secret_value.assert_called_once_with(
            "gcp:projects/demo/secrets/smtp-password-user-example-com/versions/latest",
            "smtp-secret-2",
        )
        update_saved_account.assert_called_once()
        self.assertEqual(response.json()["smtp_host"], "smtp2.example.com")
