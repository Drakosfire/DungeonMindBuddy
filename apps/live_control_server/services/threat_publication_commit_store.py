"""SBW09c2b: path-safe atomic Threat publication-commit ledger storage.

Owns no lock and must not import the proposal service. Callers hold the shared
proposal lifecycle lock before read/write.
"""
from __future__ import annotations

from pathlib import Path
from typing import Literal

from apps.live_control_server.models.threat_draft import require_draft_id
from apps.live_control_server.models.threat_publication import validate_publication_operation_id
from apps.live_control_server.models.threat_publication_commit import (
    LEDGER_SCHEMA,
    ThreatPublicationCommitLedgerV1,
)
from src.live_play.live_store import load_json, write_json

DEFAULT_COMMIT_REL = "out/threat_publication_commits"
LEDGER_NAME = "ledger.json"


class ThreatPublicationCommitStorageError(Exception):
    def __init__(self, message: str, *, kind: Literal["unavailable", "integrity"]) -> None:
        super().__init__(message)
        self.kind = kind


def commit_root(repo_root: Path) -> Path:
    return repo_root / DEFAULT_COMMIT_REL


def _storage_unavailable() -> ThreatPublicationCommitStorageError:
    return ThreatPublicationCommitStorageError(
        "publication commit ledger storage unavailable", kind="unavailable"
    )


def _integrity_failure(message: str) -> ThreatPublicationCommitStorageError:
    return ThreatPublicationCommitStorageError(message, kind="integrity")


def _operation_directory(root: Path, draft_id: str, operation_id: str) -> Path:
    safe_draft = require_draft_id(draft_id)
    safe_op = validate_publication_operation_id(operation_id)
    store_root = commit_root(root).resolve()
    directory = (store_root / safe_draft / safe_op).resolve()
    expected_parent = (store_root / safe_draft).resolve()
    if directory.parent != expected_parent or not str(directory).startswith(str(store_root)):
        raise _integrity_failure("commit path escape")
    return directory


def _ledger_path(root: Path, draft_id: str, operation_id: str) -> Path:
    return _operation_directory(root, draft_id, operation_id) / LEDGER_NAME


def threat_publication_commit_ledger_exists(
    root: Path, draft_id: str, operation_id: str
) -> bool:
    path = _ledger_path(root, draft_id, operation_id)
    return path.is_file()


def load_threat_publication_commit_ledger_unlocked(
    root: Path, draft_id: str, operation_id: str
) -> ThreatPublicationCommitLedgerV1 | None:
    path = _ledger_path(root, draft_id, operation_id)
    if not path.is_file():
        return None
    try:
        payload = load_json(path)
    except OSError:
        raise _storage_unavailable() from None
    except Exception:
        raise _integrity_failure("corrupt publication commit ledger") from None
    if not isinstance(payload, dict):
        raise _integrity_failure("corrupt publication commit ledger")
    if payload.get("schema") != LEDGER_SCHEMA:
        raise _integrity_failure("corrupt publication commit ledger")
    try:
        ledger = ThreatPublicationCommitLedgerV1.model_validate(payload)
    except Exception:
        raise _integrity_failure("corrupt publication commit ledger") from None
    if ledger.draft_id != require_draft_id(draft_id):
        raise _integrity_failure("commit ledger identity mismatch")
    if ledger.operation_id != validate_publication_operation_id(operation_id):
        raise _integrity_failure("commit ledger identity mismatch")
    return ledger


def save_threat_publication_commit_ledger_unlocked(
    root: Path, ledger: ThreatPublicationCommitLedgerV1
) -> None:
    path = _ledger_path(root, ledger.draft_id, ledger.operation_id)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        write_json(path, ledger.model_dump(mode="json", by_alias=True))
    except OSError:
        raise _storage_unavailable() from None
