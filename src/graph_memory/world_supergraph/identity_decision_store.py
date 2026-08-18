"""Internal durable identity-decision ledger (PR005).

Apps must not import this module. Use ``graph_memory.kernel`` identity / rebuild APIs.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from graph_memory.kernel.identity_models import IdentityDecisionRecord
from graph_memory.world_supergraph import paths as world_paths


def _assert_mutation_allowed(root: Path, world_id: str, operation: str) -> None:
    # Lazy import: storage -> union_supergraph.load reaches back into the
    # contribution merge path, so a module-level import would cycle.
    from graph_memory.world_supergraph.storage import (
        assert_local_world_graph_mutation_allowed,
    )

    assert_local_world_graph_mutation_allowed(root, world_id, operation=operation)


class IdentityDecisionIndex(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    world_id: str
    all_decision_ids: list[str] = Field(default_factory=list)


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


def load_identity_decision_index(root: Path, world_id: str) -> IdentityDecisionIndex:
    path = world_paths.identity_decision_index_path(root, world_id)
    if not path.is_file():
        return IdentityDecisionIndex(world_id=world_id)
    payload = json.loads(path.read_text(encoding="utf-8"))
    return IdentityDecisionIndex.model_validate(payload)


def save_identity_decision_index(
    root: Path, world_id: str, index: IdentityDecisionIndex
) -> None:
    _assert_mutation_allowed(root, world_id, "save_identity_decision_index")
    path = world_paths.identity_decision_index_path(root, world_id)
    _atomic_write_json(path, index.model_dump(mode="json"))


def write_identity_decision_record(
    root: Path, world_id: str, decision: IdentityDecisionRecord
) -> Path:
    _assert_mutation_allowed(root, world_id, "write_identity_decision_record")
    path = world_paths.identity_decision_path(root, world_id, decision.decision_id)
    _atomic_write_json(path, decision.model_dump(mode="json"))
    return path


def load_identity_decision_record(
    root: Path, world_id: str, decision_id: str
) -> IdentityDecisionRecord:
    path = world_paths.identity_decision_path(root, world_id, decision_id)
    if not path.is_file():
        raise FileNotFoundError(
            f"identity decision {decision_id!r} not found for world {world_id!r}"
        )
    payload = json.loads(path.read_text(encoding="utf-8"))
    return IdentityDecisionRecord.model_validate(payload)


def list_identity_decision_records(
    root: Path, world_id: str
) -> list[IdentityDecisionRecord]:
    index = load_identity_decision_index(root, world_id)
    records: list[IdentityDecisionRecord] = []
    for decision_id in index.all_decision_ids:
        path = world_paths.identity_decision_path(root, world_id, decision_id)
        if path.is_file():
            records.append(load_identity_decision_record(root, world_id, decision_id))
    return records


def upsert_identity_decision_in_index(
    index: IdentityDecisionIndex,
    decision: IdentityDecisionRecord,
) -> IdentityDecisionIndex:
    decision_id = decision.decision_id
    all_ids = list(index.all_decision_ids)
    if decision_id not in all_ids:
        all_ids.append(decision_id)
    return index.model_copy(update={"all_decision_ids": all_ids})


def sync_identity_decisions_from_store(
    root: Path,
    world_id: str,
    store: Any,
) -> list[str]:
    """Persist full identity-decision payloads from a published graph store.

    Returns the decision ids written/updated. This is the durable replay source
    for rebuild — independent of the current graph head.
    """
    raw_decisions = getattr(store, "identity_decisions", None) or []
    if not raw_decisions:
        return []

    index = load_identity_decision_index(root, world_id)
    written: list[str] = []
    for raw in raw_decisions:
        decision = IdentityDecisionRecord.model_validate(raw)
        write_identity_decision_record(root, world_id, decision)
        index = upsert_identity_decision_in_index(index, decision)
        written.append(decision.decision_id)
    save_identity_decision_index(root, world_id, index)
    return written
