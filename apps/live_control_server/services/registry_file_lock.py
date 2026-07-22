"""Exclusive mutation locks for whole-file JSON registries."""

from __future__ import annotations

import fcntl
import hashlib
import re
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

_SAFE_LOCK_NAME_RE = re.compile(r"[^A-Za-z0-9._-]+")


def registry_token(path: Path) -> str:
    """Opaque token for compare-and-swap over a registry document file."""
    if not path.is_file():
        return "absent"
    return hashlib.sha256(path.read_bytes()).hexdigest()


@contextmanager
def registry_mutation_lock(registry_path: Path) -> Iterator[None]:
    """Serialize load/check/mutate/replace for one registry document."""
    lock_path = registry_path.with_name(f".{registry_path.name}.lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a+", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


@contextmanager
def workspace_document_mutation_lock(root: Path, document_id: str) -> Iterator[None]:
    """Serialize Markdown commit and SourceArtifact snapshot for one workspace document.

    Hold across load/verify/read-or-write target bytes and any registry transition that
    binds those bytes to a workspace revision.
    """
    cleaned = (document_id or "").strip()
    if not cleaned:
        raise ValueError("document_id is required for workspace document mutation lock")
    safe_name = _SAFE_LOCK_NAME_RE.sub("_", cleaned)
    lock_path = root / "out" / "registries" / ".locks" / f"workspace_document.{safe_name}.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a+", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
