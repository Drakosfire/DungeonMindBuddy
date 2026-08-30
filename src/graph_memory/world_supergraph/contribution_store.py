"""Internal durable contribution ledger (PR005).

Apps must not import this module. Use ``graph_memory.kernel`` contribution APIs.
"""

from __future__ import annotations

import fcntl
import json
import os
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from pydantic import BaseModel, ConfigDict, Field

from apps.live_control_server.models.world_graph_contribution_models import GraphContribution
from graph_memory.world_supergraph import paths as world_paths


def _assert_mutation_allowed(root: Path, world_id: str, operation: str) -> None:
    # Lazy import: storage -> union_supergraph.load reaches back into the
    # contribution merge path, so a module-level import would cycle.
    from graph_memory.world_supergraph.storage import (
        assert_local_world_graph_mutation_allowed,
    )

    assert_local_world_graph_mutation_allowed(root, world_id, operation=operation)


class ContributionIndex(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    world_id: str
    baseline_revision_id: str | None = None
    all_contribution_ids: list[str] = Field(default_factory=list)
    active_contribution_ids: list[str] = Field(default_factory=list)
    superseded_contribution_ids: list[str] = Field(default_factory=list)
    retracted_contribution_ids: list[str] = Field(default_factory=list)
    failed_contribution_ids: list[str] = Field(default_factory=list)


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=str(path.parent), prefix=".tmp-", suffix=".json")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True, ensure_ascii=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_name, path)
    except Exception:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise


@contextmanager
def _exclusive_contribution_index_lock(root: Path, world_id: str) -> Iterator[None]:
    """Serialize contribution-index read-modify-write with world publish CAS.

    Uses the same per-world write lock as ``publish_world_graph_revision`` so
    concurrent merges cannot clobber each other's committed index entries via
    stale in-memory snapshots.
    """
    world_paths.assert_safe_world_id(world_id)
    world_paths.world_dir(root, world_id).mkdir(parents=True, exist_ok=True)
    lock_path = world_paths.write_lock_path(root, world_id)
    with open(lock_path, "a+", encoding="utf-8") as lock_file:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)


def load_contribution_index(root: Path, world_id: str) -> ContributionIndex:
    path = world_paths.contribution_index_path(root, world_id)
    if not path.is_file():
        return ContributionIndex(world_id=world_id)
    payload = json.loads(path.read_text(encoding="utf-8"))
    return ContributionIndex.model_validate(payload)


def save_contribution_index(root: Path, world_id: str, index: ContributionIndex) -> None:
    _assert_mutation_allowed(root, world_id, "save_contribution_index")
    path = world_paths.contribution_index_path(root, world_id)
    _atomic_write_json(path, index.model_dump(mode="json"))


def write_contribution_record(
    root: Path, world_id: str, contribution: GraphContribution
) -> Path:
    _assert_mutation_allowed(root, world_id, "write_contribution_record")
    path = world_paths.contribution_path(root, world_id, contribution.contribution_id)
    _atomic_write_json(path, contribution.model_dump(mode="json"))
    return path


def load_contribution_record(
    root: Path, world_id: str, contribution_id: str
) -> GraphContribution:
    path = world_paths.contribution_path(root, world_id, contribution_id)
    if not path.is_file():
        raise FileNotFoundError(
            f"contribution {contribution_id!r} not found for world {world_id!r}"
        )
    payload = json.loads(path.read_text(encoding="utf-8"))
    return GraphContribution.model_validate(payload)


def list_contribution_records(root: Path, world_id: str) -> list[GraphContribution]:
    index = load_contribution_index(root, world_id)
    records: list[GraphContribution] = []
    for contribution_id in index.all_contribution_ids:
        path = world_paths.contribution_path(root, world_id, contribution_id)
        if path.is_file():
            records.append(load_contribution_record(root, world_id, contribution_id))
    return records


def upsert_contribution_in_index(
    index: ContributionIndex,
    contribution: GraphContribution,
) -> ContributionIndex:
    cid = contribution.contribution_id
    all_ids = list(index.all_contribution_ids)
    if cid not in all_ids:
        all_ids.append(cid)

    active = [x for x in index.active_contribution_ids if x != cid]
    superseded = [x for x in index.superseded_contribution_ids if x != cid]
    retracted = [x for x in index.retracted_contribution_ids if x != cid]
    failed = [x for x in index.failed_contribution_ids if x != cid]

    if contribution.status == "active":
        active.append(cid)
    elif contribution.status == "superseded":
        superseded.append(cid)
    elif contribution.status == "retracted":
        retracted.append(cid)
    elif contribution.status == "failed":
        failed.append(cid)

    return index.model_copy(
        update={
            "all_contribution_ids": all_ids,
            "active_contribution_ids": active,
            "superseded_contribution_ids": superseded,
            "retracted_contribution_ids": retracted,
            "failed_contribution_ids": failed,
        }
    )


def upsert_and_save_contribution_index(
    root: Path,
    world_id: str,
    *contributions: GraphContribution,
    baseline_revision_id: str | None = None,
) -> ContributionIndex:
    """Atomically reload, upsert one or more contributions, and persist the index.

    Concurrent callers cannot replace the index with a stale snapshot: each
    update reloads under the world write lock before merging its entries.
    """
    if not contributions and baseline_revision_id is None:
        raise ValueError("upsert_and_save_contribution_index requires contributions")
    with _exclusive_contribution_index_lock(root, world_id):
        index = load_contribution_index(root, world_id)
        if baseline_revision_id is not None and index.baseline_revision_id is None:
            index = index.model_copy(
                update={"baseline_revision_id": baseline_revision_id}
            )
        for contribution in contributions:
            index = upsert_contribution_in_index(index, contribution)
        save_contribution_index(root, world_id, index)
        return index


def write_rebuild_report(root: Path, world_id: str, report: dict[str, Any]) -> Path:
    path = world_paths.contribution_rebuild_latest_path(root, world_id)
    _atomic_write_json(path, report)
    return path
