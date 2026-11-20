"""Local native-admission executor exclusion; APP/Core own durable state."""

from __future__ import annotations

from contextlib import contextmanager
import fcntl
import hashlib
import os
from pathlib import Path
from typing import Iterator


class NativeRecapExecutionConflict(RuntimeError):
    pass


class NativeRecapExecutionLock:
    def __init__(self, directory: Path) -> None:
        self.directory = Path(directory)

    @contextmanager
    def exclusive(self, admission_id: str) -> Iterator[None]:
        """Exclude local executors; Core fences durable effects across hosts."""
        if self.directory.is_symlink():
            raise NativeRecapExecutionConflict("execution_lock_directory_invalid")
        self.directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        lock_path = self.directory / (
            hashlib.sha256(admission_id.encode()).hexdigest() + ".lock"
        )
        descriptor = os.open(lock_path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        try:
            try:
                fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as exc:
                raise NativeRecapExecutionConflict("operation_busy") from exc
            yield
        finally:
            os.close(descriptor)
