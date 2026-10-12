"""Atomic local progress observations; never source, review or graph authority."""

from __future__ import annotations

from contextlib import contextmanager
import fcntl
import hashlib
import json
import os
from pathlib import Path
import tempfile
from typing import Any, Iterator


class ProgressConflict(RuntimeError):
    pass


class PublicationProgressStore:
    def __init__(self, directory: Path) -> None:
        self.directory = Path(directory)

    def _path(self, operation_id: str) -> Path:
        key = hashlib.sha256(operation_id.encode()).hexdigest()
        return self.directory / (key + ".json")

    def read(self, operation_id: str) -> dict[str, Any] | None:
        """Inspection creates no directory, lock, journal or stage observation."""
        path = self._path(operation_id)
        if not path.exists():
            return None
        if path.is_symlink() or path.stat().st_size > 1_048_576:
            raise ProgressConflict("progress_invalid")
        try:
            value = json.loads(path.read_text())
        except (OSError, ValueError) as exc:
            raise ProgressConflict("progress_unavailable") from exc
        if (
            not isinstance(value, dict)
            or value.get("schema") != "dmb_reviewed_corpus_progress_v1"
            or value.get("operation_id") != operation_id
            or not isinstance(value.get("stages"), dict)
        ):
            raise ProgressConflict("progress_invalid")
        return value

    @contextmanager
    def exclusive(self, operation_id: str) -> Iterator[None]:
        """One local executor; Core separately fences cross-host durable effects."""
        if self.directory.is_symlink():
            raise ProgressConflict("progress_directory_invalid")
        self.directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        lock_path = self._path(operation_id).with_suffix(".lock")
        descriptor = os.open(lock_path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        try:
            try:
                fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as exc:
                raise ProgressConflict("operation_busy") from exc
            yield
        finally:
            os.close(descriptor)

    def write(self, operation_id: str, value: dict[str, Any]) -> None:
        """Caller holds exclusive(); fsync precedes atomic publication of the file."""
        encoded = json.dumps(
            value, sort_keys=True, separators=(",", ":"), allow_nan=False
        )
        if len(encoded.encode()) > 1_048_576:
            raise ProgressConflict("progress_over_budget")
        descriptor, temporary = tempfile.mkstemp(
            prefix=".progress-", dir=self.directory
        )
        try:
            with os.fdopen(descriptor, "w") as stream:
                stream.write(encoded)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, self._path(operation_id))
            directory = os.open(self.directory, os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
        finally:
            Path(temporary).unlink(missing_ok=True)
