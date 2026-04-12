from __future__ import annotations

from pathlib import Path

from .settings import RUN_DIR


class FileLock:
    def __init__(self, name: str):
        self.path = RUN_DIR / f"{name}.lock"
        self.acquired = False

    def acquire(self):
        RUN_DIR.mkdir(exist_ok=True)
        try:
            fd = self.path.open("x", encoding="utf-8")
            fd.write("locked\n")
            fd.close()
            self.acquired = True
            return True
        except FileExistsError:
            return False

    def release(self):
        if self.acquired and self.path.exists():
            self.path.unlink()
        self.acquired = False

    def __enter__(self):
        if not self.acquire():
            raise RuntimeError(f"Lock already held: {self.path}")
        return self

    def __exit__(self, exc_type, exc, tb):
        self.release()
