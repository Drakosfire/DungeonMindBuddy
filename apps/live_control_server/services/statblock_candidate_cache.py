"""Bounded non-authoritative candidate response cache."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from src.live_play.live_store import load_json, write_json

DEFAULT_CACHE_REL = "out/statblock_candidates"


class CandidateCacheError(ValueError):
    status_code: int = 500

    def __init__(self, message: str, *, status_code: int = 500) -> None:
        super().__init__(message)
        self.status_code = status_code


def candidate_cache_root(repo_root: Path) -> Path:
    return repo_root / DEFAULT_CACHE_REL


def _candidate_path(root: Path, candidate_id: str) -> Path:
    return candidate_cache_root(root) / f"{candidate_id}.json"


def store_candidate_payload(root: Path, candidate_id: str, payload: dict[str, Any]) -> None:
    path = _candidate_path(root, candidate_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    write_json(
        path,
        {
            "schema": "dmb_statblock_candidate_cache_v1",
            "candidate_id": candidate_id,
            "payload": payload,
        },
    )


def read_candidate_payload(root: Path, candidate_id: str) -> dict[str, Any] | None:
    path = _candidate_path(root, candidate_id)
    if not path.is_file():
        return None
    try:
        document = load_json(path)
    except Exception as exc:
        raise CandidateCacheError("corrupt candidate cache record") from exc
    payload = document.get("payload")
    if not isinstance(payload, dict):
        raise CandidateCacheError("corrupt candidate cache payload")
    return payload
