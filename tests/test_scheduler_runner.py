import unittest
from unittest.mock import patch

from biztogmail_app.logging_utils import RunLogger
from biztogmail_app.scheduler_runner import run_scheduler_loop


class SchedulerRunnerTests(unittest.TestCase):
    def test_run_scheduler_loop_once_runs_single_tick(self):
        logger = RunLogger()
        logger.setup("test")
        with patch("biztogmail_app.scheduler_runner.FileLock") as lock_cls, \
             patch("biztogmail_app.scheduler_runner.run_due_accounts") as run_due_accounts:
            lock_instance = lock_cls.return_value
            lock_instance.__enter__.return_value = lock_instance
            run_scheduler_loop(interval_seconds=1, once=True, logger=logger)

        run_due_accounts.assert_called_once()
