from __future__ import annotations

import time

from .locks import FileLock
from .logging_utils import RunLogger
from .scheduler import run_due_accounts


def run_scheduler_loop(*, interval_seconds: int = 60, once: bool = False, logger: RunLogger | None = None):
    active_logger = logger or RunLogger()
    active_logger.setup("scheduler-runner")
    with FileLock("scheduler"):
        while True:
            active_logger.append("scheduler tick start")
            run_due_accounts(logger=active_logger)
            active_logger.append("scheduler tick end")
            if once:
                break
            time.sleep(interval_seconds)
