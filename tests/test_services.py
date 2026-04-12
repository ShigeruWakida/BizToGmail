import unittest

from biztogmail_app.services import evaluate_deletion, select_pending_entries


class ServicesTests(unittest.TestCase):
    def test_select_pending_entries_keeps_latest_unseen_items_in_order(self):
        entries = [(1, "uid-1"), (2, "uid-2"), (3, "uid-3"), (4, "uid-4")]
        seen = {"uid-2"}

        result = select_pending_entries(entries, lambda uidl: uidl in seen, 2)

        self.assertEqual(result, [(3, "uid-3"), (4, "uid-4")])

    def test_evaluate_deletion_without_leave_copy_deletes_immediately(self):
        should_delete, reason = evaluate_deletion(None, leave_copy=False, delete_after_days=None)

        self.assertTrue(should_delete)
        self.assertEqual(reason, "no-leave-copy")

    def test_evaluate_deletion_without_date_reports_no_date(self):
        should_delete, reason = evaluate_deletion(None, leave_copy=True, delete_after_days=30)

        self.assertFalse(should_delete)
        self.assertEqual(reason, "no Date")
