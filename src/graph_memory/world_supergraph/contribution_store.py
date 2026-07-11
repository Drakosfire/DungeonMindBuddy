"""Internal durable contribution ledger (PR005).

Apps must not import this module. Use ``graph_memory.kernel`` contribution APIs.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from graph_memory.kernel.contribution_models import GraphContribution
from graph_memory.world_supergraph import paths as world_paths


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


def load_contribution_index(root: Path, world_id: str) -> ContributionIndex:
    path = world_paths.contribution_index_path(root, world_id)
    if not path.is_file():
        return ContributionIndex(world_id=world_id)
    payload = json.loads(path.read_text(encoding="utf-8"))
    return ContributionIndex.model_validate(payload)


def save_contribution_index(root: Path, world_id: str, index: ContributionIndex) -> None:
    path = world_paths.contribution_index_path(root, world_id)
    _atomic_write_json(path, index.model_dump(mode="json"))


def write_contribution_record(
    root: Path, world_id: str, contribution: GraphContribution
) -> Path:
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


def write_rebuild_report(root: Path, world_id: str, report: dict[str, Any]) -> Path:
    path = world_paths.contribution_rebuild_latest_path(root, world_id)
    _atomic_write_json(path, report)
    return path
