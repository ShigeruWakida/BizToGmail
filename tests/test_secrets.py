import os
import unittest
from unittest.mock import patch

from biztogmail_app import secrets
from biztogmail_app.secrets import (
    build_gcp_secret_ref,
    build_smtp_secret_ref,
    build_source_secret_ref,
    invalidate_secret_ref,
    resolve_account_password,
    resolve_account_smtp_password,
    resolve_secret_ref,
    store_secret_value,
)


class SecretResolutionTests(unittest.TestCase):
    def setUp(self):
        secrets._SECRET_CACHE.clear()

    def test_resolve_account_password_prefers_secret_ref(self):
        account = {"secret_ref": "env:POP_SECRET", "pop_password": "fallback"}
        with patch.dict(os.environ, {"POP_SECRET": "from-env"}, clear=False):
            self.assertEqual(resolve_account_password(account), "from-env")

    def test_resolve_account_password_falls_back_to_stored_password(self):
        account = {"secret_ref": "env:MISSING", "pop_password": "fallback"}
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(resolve_account_password(account), "fallback")

    def test_resolve_account_smtp_password_prefers_smtp_secret_ref(self):
        account = {"smtp_secret_ref": "env:SMTP_SECRET", "smtp_password": "fallback"}
        with patch.dict(os.environ, {"SMTP_SECRET": "smtp-from-env"}, clear=False):
            self.assertEqual(resolve_account_smtp_password(account), "smtp-from-env")

    def test_resolve_secret_ref_supports_gcp_secret_manager(self):
        payload = type("Payload", (), {"data": b"from-gcp"})()
        response = type("Response", (), {"payload": payload})()
        fake_client = type(
            "FakeClient",
            (),
            {"access_secret_version": lambda self, request: response},
        )()
        fake_sm = type("FakeSM", (), {"SecretManagerServiceClient": lambda: fake_client})
        with patch("biztogmail_app.secrets.secretmanager", fake_sm):
            value = resolve_secret_ref("gcp:projects/demo/secrets/pop-password/versions/latest")

        self.assertEqual(value, "from-gcp")

    def test_resolve_secret_ref_uses_cache_until_invalidated(self):
        with patch("biztogmail_app.secrets.get_secret_value", side_effect=["first", "second"]):
            first = resolve_secret_ref("env:POP_SECRET")
            second = resolve_secret_ref("env:POP_SECRET")
            invalidate_secret_ref("env:POP_SECRET")
            third = resolve_secret_ref("env:POP_SECRET")

        self.assertEqual(first, "first")
        self.assertEqual(second, "first")
        self.assertEqual(third, "second")

    def test_build_gcp_secret_ref_uses_email_slug_and_project(self):
        with patch.dict(os.environ, {"BIZTOGMAIL_GCP_PROJECT": "demo-project"}, clear=False):
            value = build_gcp_secret_ref("Sales.Team+JP@example.com")
            source_value = build_source_secret_ref("Sales.Team+JP@example.com")
            smtp_value = build_smtp_secret_ref("Sales.Team+JP@example.com")

        self.assertEqual(
            value,
            "gcp:projects/demo-project/secrets/source-password-sales-team-jp-example-com/versions/latest",
        )
        self.assertEqual(value, source_value)
        self.assertEqual(
            smtp_value,
            "gcp:projects/demo-project/secrets/smtp-password-sales-team-jp-example-com/versions/latest",
        )

    def test_store_secret_value_supports_gcp_secret_manager(self):
        fake_client = type(
            "FakeClient",
            (),
            {
                "get_secret": lambda self, request: (_ for _ in ()).throw(Exception("missing")),
                "create_secret": lambda self, request: None,
                "add_secret_version": lambda self, request: request,
            },
        )()
        fake_sm = type("FakeSM", (), {"SecretManagerServiceClient": lambda: fake_client})
        with patch("biztogmail_app.secrets.secretmanager", fake_sm), \
             patch("biztogmail_app.secrets.NotFound", Exception):
            value = store_secret_value(
                "gcp:projects/demo-project/secrets/source-password-user-example-com/versions/latest",
                "from-gcp",
            )

        self.assertEqual(
            value,
            "gcp:projects/demo-project/secrets/source-password-user-example-com/versions/latest",
        )
