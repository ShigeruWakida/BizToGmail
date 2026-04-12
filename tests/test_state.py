import os
import unittest
from pathlib import Path

from biztogmail_app import state
from biztogmail_app.db import reset_engine
from sqlalchemy import inspect, text


TEST_TMP_DIR = Path(__file__).resolve().parent / ".tmp"
TEST_TMP_DIR.mkdir(exist_ok=True)


class StateTests(unittest.TestCase):
    def setUp(self):
        reset_engine()

    def tearDown(self):
        reset_engine()

    def test_ensure_db_creates_messages_table(self):
        db_path = TEST_TMP_DIR / "state-test.db"
        if db_path.exists():
            db_path.unlink()
        self.addCleanup(lambda: db_path.unlink(missing_ok=True))
        os.environ["DATABASE_URL"] = f"sqlite:///{db_path.as_posix()}"
        self.addCleanup(lambda: os.environ.pop("DATABASE_URL", None))
        try:
            con = state.ensure_db()
            inspector = inspect(con)
            tables = inspector.get_table_names()
            con.close()
        finally:
            reset_engine()

        self.assertIn("messages", tables)

    def test_uidl_mark_imported_and_seen(self):
        os.environ["DATABASE_URL"] = "sqlite:///:memory:"
        self.addCleanup(lambda: os.environ.pop("DATABASE_URL", None))
        con = state.ensure_db()

        self.assertFalse(state.uidl_seen(con, "uid-1"))
        state.uidl_mark_imported(con, "uid-1", "gmail-1")
        self.assertTrue(state.uidl_seen(con, "uid-1"))

        row = con.execute(
            text("SELECT status, gmail_id FROM messages WHERE uidl = :uidl"),
            {"uidl": "uid-1"},
        ).first()
        con.close()

        self.assertEqual(row, ("imported", "gmail-1"))

    def test_uidl_mark_imported_updates_existing_row(self):
        os.environ["DATABASE_URL"] = "sqlite:///:memory:"
        self.addCleanup(lambda: os.environ.pop("DATABASE_URL", None))
        con = state.ensure_db()
        state.uidl_mark_imported(con, "uid-1", "gmail-1")
        state.uidl_mark_imported(con, "uid-1", "gmail-2")

        row = con.execute(
            text("SELECT status, gmail_id FROM messages WHERE uidl = :uidl"),
            {"uidl": "uid-1"},
        ).first()
        con.close()

        self.assertEqual(row, ("imported", "gmail-2"))
