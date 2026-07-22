"""Fail-closed non-authoritative candidate response cache."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from apps.live_control_server.integrations.dungeonmind_statblocks.config import (
    validate_candidate_id,
)
from apps.live_control_server.integrations.dungeonmind_statblocks.models import (
    GeneratedStatblockCandidateV1,
)
from src.live_play.live_store import load_json, write_json

DEFAULT_CACHE_REL = "out/statblock_candidates"
CACHE_SCHEMA = "dmb_statblock_candidate_cache_v1"
MAX_CACHE_BYTES = 1_048_576


class CandidateCacheError(ValueError):
    status_code: int = 500

    def __init__(self, message: str, *, status_code: int = 500) -> None:
        super().__init__(message)
        self.status_code = status_code


def candidate_cache_root(repo_root: Path) -> Path:
    return repo_root / DEFAULT_CACHE_REL


def _candidate_path(root: Path, candidate_id: str) -> Path:
    try:
        cleaned = validate_candidate_id(candidate_id)
    except ValueError as exc:
        raise CandidateCacheError(str(exc), status_code=422) from None
    store_root = candidate_cache_root(root).resolve()
    path = (store_root / f"{cleaned}.json").resolve()
    if path.parent != store_root:
        raise CandidateCacheError("candidate cache path escape", status_code=500)
    return path


def _payload_digest(candidate: GeneratedStatblockCandidateV1) -> str:
    canonical = json.dumps(
        candidate.model_dump(mode="json"),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def store_candidate_payload(
    root: Path,
    candidate: GeneratedStatblockCandidateV1,
) -> None:
    path = _candidate_path(root, candidate.candidate_id)
    document = {
        "schema": CACHE_SCHEMA,
        "candidate_id": candidate.candidate_id,
        "payload_digest": _payload_digest(candidate),
        "payload": candidate.model_dump(mode="json"),
    }
    encoded = json.dumps(document, indent=2, ensure_ascii=False) + "\n"
    if len(encoded.encode("utf-8")) > MAX_CACHE_BYTES:
        raise CandidateCacheError("candidate cache payload exceeds bound", status_code=500)

    if path.is_file():
        existing = read_candidate_payload(root, candidate.candidate_id)
        if existing.model_dump(mode="json") != candidate.model_dump(mode="json"):
            raise CandidateCacheError(
                "candidate cache identity conflict",
                status_code=409,
            )
        return

    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        write_json(path, document)
    except OSError as exc:
        raise CandidateCacheError(
            "candidate cache storage unavailable",
            status_code=500,
        ) from None


def read_candidate_payload(root: Path, candidate_id: str) -> GeneratedStatblockCandidateV1:
    path = _candidate_path(root, candidate_id)
    try:
        if not path.is_file():
            raise CandidateCacheError("candidate cache miss", status_code=404)
        if path.stat().st_size > MAX_CACHE_BYTES:
            raise CandidateCacheError(
                "candidate cache record exceeds bound",
                status_code=500,
            )
        document = load_json(path)
    except CandidateCacheError:
        raise
    except OSError:
        raise CandidateCacheError(
            "candidate cache storage unavailable",
            status_code=500,
        ) from None
    except Exception:
        raise CandidateCacheError("corrupt candidate cache record") from None

    if document.get("schema") != CACHE_SCHEMA:
        raise CandidateCacheError("corrupt candidate cache record")
    envelope_id = document.get("candidate_id")
    payload = document.get("payload")
    digest = document.get("payload_digest")
    if not isinstance(envelope_id, str) or not isinstance(payload, dict):
        raise CandidateCacheError("corrupt candidate cache record")
    try:
        if envelope_id != validate_candidate_id(candidate_id):
            raise CandidateCacheError("candidate cache identity mismatch")
        candidate = GeneratedStatblockCandidateV1.model_validate(payload)
    except CandidateCacheError:
        raise
    except Exception:
        raise CandidateCacheError("corrupt candidate cache payload") from None
    if candidate.candidate_id != envelope_id:
        raise CandidateCacheError("candidate cache identity mismatch")
    if digest != _payload_digest(candidate):
        raise CandidateCacheError("candidate cache digest mismatch")
    return candidate


def read_candidate_payload_or_none(
    root: Path, candidate_id: str
) -> GeneratedStatblockCandidateV1 | None:
    try:
        return read_candidate_payload(root, candidate_id)
    except CandidateCacheError as exc:
        if exc.status_code == 404:
            return None
        raise
