from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from .settings import LOG_DIR


@dataclass
class RunLogger:
    log_file_path: Path | None = None

    def setup(self, command_name: str):
        LOG_DIR.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        self.log_file_path = LOG_DIR / f"{command_name}-{timestamp}.log"

    def append(self, message: str, *, error: bool = False):
        if self.log_file_path is None:
            return
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        level = "ERROR" if error else "INFO"
        with self.log_file_path.open("a", encoding="utf-8") as f:
            f.write(f"{timestamp} [{level}] {message}\n")
