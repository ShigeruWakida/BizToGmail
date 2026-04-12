import contextlib
import io
import unittest

from biztogmail_app.cli import build_parser


class CliTests(unittest.TestCase):
    def test_run_parser_defaults(self):
        parser = build_parser()
        args = parser.parse_args(
            ["run", "--host", "pop.example.com", "--user", "user@example.com", "--destination", "dest@gmail.com"]
        )

        self.assertEqual(args.cmd, "run")
        self.assertEqual(args.host, "pop.example.com")
        self.assertEqual(args.user, "user@example.com")
        self.assertEqual(args.protocol, "pop3")
        self.assertIsNone(args.folder)
        self.assertEqual(args.port, 995)
        self.assertTrue(args.ssl)
        self.assertEqual(args.max, 3)
        self.assertEqual(args.destination, "dest@gmail.com")
        self.assertEqual(args.smtp_port, 465)
        self.assertTrue(args.smtp_ssl)
        self.assertFalse(args.dry_run)

    def test_run_parser_accepts_optional_flags(self):
        parser = build_parser()
        args = parser.parse_args(
            [
                "run",
                "--host",
                "pop.example.com",
                "--user",
                "user@example.com",
                "--protocol",
                "imap",
                "--folder",
                "INBOX",
                "--destination",
                "dest@gmail.com",
                "--smtp-host",
                "smtp.example.com",
                "--smtp-port",
                "465",
                "--smtp-user",
                "smtp-user",
                "--smtp-password",
                "smtp-secret",
                "--no-leave-copy",
                "--delete-after-days",
                "30",
                "--dry-run",
            ]
        )

        self.assertEqual(args.destination, "dest@gmail.com")
        self.assertEqual(args.protocol, "imap")
        self.assertEqual(args.folder, "INBOX")
        self.assertEqual(args.smtp_host, "smtp.example.com")
        self.assertEqual(args.smtp_port, 465)
        self.assertEqual(args.smtp_user, "smtp-user")
        self.assertEqual(args.smtp_password, "smtp-secret")
        self.assertTrue(args.no_leave_copy)
        self.assertEqual(args.delete_after_days, 30)
        self.assertTrue(args.dry_run)

    def test_seed_parser_defaults(self):
        parser = build_parser()
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                parser.parse_args(["seed"])
