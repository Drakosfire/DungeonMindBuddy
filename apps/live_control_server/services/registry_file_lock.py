"""Exclusive mutation locks for whole-file JSON registries."""

from __future__ import annotations

import fcntl
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

@contextmanager
def registry_mutation_lock(registry_path: Path) -> Iterator[None]:
    """Serialize load/check/mutate/replace for one registry document."""
    lock_path = registry_path.with_name(f".{registry_path.name}.lock")
    if lock_path.is_symlink():
        raise ValueError("registry lock path must not be a symlink")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a+", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
