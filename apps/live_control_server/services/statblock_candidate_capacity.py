"""Shared draft-scoped candidate-history capacity admission.

Generation and revise journals each reserve slots against
``ThreatDraftV1.candidate_refs`` ``max_length=64``. Admission for a *new*
reservation must hold ``draft_candidate_capacity_lock`` and count:

- attached candidate refs;
- unbound generation-journal reservations;
- unbound revise-journal reservations;

as one atomic boundary so the two claim paths cannot overbook.

Lock order (new claims):
- Generation (with ThreatDraft gates): store → capacity → reconciliation
- Generation (journal-only claim helper): capacity → reconciliation
- Revise (new claim): capacity → revise
"""
from __future__ import annotations

import fcntl
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from apps.live_control_server.models.threat_draft import MAX_CANDIDATE_REFS, require_draft_id

DEFAULT_CAPACITY_REL = "out/statblock_candidate_capacity"
LOCK_NAME = ".capacity.lock"


class CandidateCapacityError(ValueError):
    status_code: int = 500

    def __init__(self, message: str, *, status_code: int = 500) -> None:
        super().__init__(message)
        self.status_code = status_code


def capacity_root(repo_root: Path) -> Path:
    return repo_root / DEFAULT_CAPACITY_REL


def _draft_directory(root: Path, draft_id: str) -> Path:
    safe = require_draft_id(draft_id)
    store_root = capacity_root(root).resolve()
    directory = (store_root / safe).resolve()
    if directory.parent != store_root:
        raise CandidateCapacityError("capacity path escape", status_code=500)
    return directory


@contextmanager
def draft_candidate_capacity_lock(root: Path, draft_id: str) -> Iterator[None]:
    """Exclusive per-draft lock for candidate-history admission."""
    directory = _draft_directory(root, draft_id)
    try:
        directory.mkdir(parents=True, exist_ok=True)
        lock_path = directory / LOCK_NAME
        with lock_path.open("a+", encoding="utf-8") as lock_file:
            try:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
            except OSError as exc:
                raise CandidateCapacityError(
                    "candidate capacity storage unavailable",
                    status_code=500,
                ) from exc
            try:
                yield
            finally:
                try:
                    fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
                except OSError:
                    pass
    except CandidateCapacityError:
        raise
    except OSError as exc:
        raise CandidateCapacityError(
            "candidate capacity storage unavailable",
            status_code=500,
        ) from exc


def total_candidate_capacity_usage(
    root: Path,
    *,
    draft_id: str,
    ref_candidate_ids: set[str],
) -> int:
    """Attached refs + unbound gen + unbound revise reservations.

    Caller must hold ``draft_candidate_capacity_lock`` for the draft.
    """
    # Lazy imports avoid circular module load with journal packages.
    from apps.live_control_server.services.statblock_generation_reconciliation import (
        count_generation_capacity_usage,
    )
    from apps.live_control_server.services.statblock_revise_reconciliation import (
        count_revise_capacity_reservations,
    )

    gen_usage = count_generation_capacity_usage(
        root,
        draft_id=draft_id,
        ref_candidate_ids=ref_candidate_ids,
    )
    revise_reserved = count_revise_capacity_reservations(
        root,
        draft_id=draft_id,
        ref_candidate_ids=ref_candidate_ids,
    )
    return gen_usage + revise_reserved


def capacity_remaining(
    root: Path,
    *,
    draft_id: str,
    ref_candidate_ids: set[str],
) -> int:
    """Slots left before ``MAX_CANDIDATE_REFS``. Caller holds capacity lock."""
    return MAX_CANDIDATE_REFS - total_candidate_capacity_usage(
        root,
        draft_id=draft_id,
        ref_candidate_ids=ref_candidate_ids,
    )


__all__ = [
    "CandidateCapacityError",
    "DEFAULT_CAPACITY_REL",
    "MAX_CANDIDATE_REFS",
    "capacity_remaining",
    "capacity_root",
    "draft_candidate_capacity_lock",
    "total_candidate_capacity_usage",
]
