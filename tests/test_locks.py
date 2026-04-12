import unittest
from pathlib import Path
from unittest.mock import patch

from biztogmail_app import locks


TEST_TMP_DIR = Path(__file__).resolve().parent / ".tmp"
TEST_TMP_DIR.mkdir(exist_ok=True)


class FileLockTests(unittest.TestCase):
    def test_acquire_and_release_lock(self):
        run_dir = TEST_TMP_DIR / "locks"
        run_dir.mkdir(exist_ok=True)
        lock_path = run_dir / "scheduler.lock"
        if lock_path.exists():
            lock_path.unlink()
        self.addCleanup(lambda: lock_path.unlink(missing_ok=True))
        with patch.object(locks, "RUN_DIR", run_dir):
            lock = locks.FileLock("scheduler")
            self.assertTrue(lock.acquire())
            self.assertFalse(locks.FileLock("scheduler").acquire())
            lock.release()
            self.assertFalse(lock.path.exists())
