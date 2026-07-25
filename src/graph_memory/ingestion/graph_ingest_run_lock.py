"""Exclusive mutation lock + content-token CAS for graph-ingest run manifests."""

from __future__ import annotations

import fcntl
import hashlib
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator


def manifest_content_token(path: Path) -> str:
    if not path.is_file():
        return "absent"
    return hashlib.sha256(path.read_bytes()).hexdigest()


@contextmanager
def graph_ingest_manifest_mutation_lock(manifest_path: Path) -> Iterator[None]:
    lock_path = manifest_path.with_name(f".{manifest_path.name}.lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a+", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
