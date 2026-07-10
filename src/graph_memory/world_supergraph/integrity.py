"""Integrity reporting for World SuperGraph stores (PR002 stub)."""

from __future__ import annotations

from pathlib import Path

from graph_memory.union_supergraph.load import dump_union_supergraph_store
from graph_memory.union_supergraph.validate import (
    UnionSupergraphValidationError,
    validate_union_supergraph_fixture,
)
from graph_memory.world_supergraph.errors import WorldGraphNotFoundError
from graph_memory.world_supergraph.model import WorldGraphIntegrityReport
from graph_memory.world_supergraph import paths as world_paths
from graph_memory.world_supergraph.storage import (
    canonicalize_graph_payload,
    list_revision_ids,
    load_current_world_graph,
    load_world_graph_revision,
    load_world_graph_revision_manifest,
    open_world_graph_head,
    sha256_hex,
    try_open_world_graph_head,
    _write_json_atomic,
)


def build_world_graph_integrity_report(
    root: Path, world_id: str, *, persist: bool = True
) -> WorldGraphIntegrityReport:
    """Build a machine-readable health report for the world graph head.

    PR002 stub fields: head revision, parent, load/validate status, revision count.
    Optionally writes ``integrity/latest.json``.
    """
    world_paths.assert_safe_world_id(world_id)
    errors: list[str] = []
    warnings: list[str] = []

    head = try_open_world_graph_head(root, world_id)
    revision_ids = list_revision_ids(root, world_id)
    revision_count = len(revision_ids)

    if head is None:
        report = WorldGraphIntegrityReport(
            world_id=world_id,
            head_revision_id=None,
            parent_revision_id=None,
            load_ok=False,
            validation_ok=False,
            revision_count=revision_count,
            graph_payload_sha256=None,
            errors=[f"no world graph head for world_id={world_id!r}"],
            warnings=warnings,
        )
        if persist and world_paths.world_dir(root, world_id).exists():
            _persist_report(root, world_id, report)
        return report

    head_revision_id = head.head_revision_id
    parent_revision_id: str | None = None
    payload_sha: str | None = None
    load_ok = False
    validation_ok = False

    try:
        open_world_graph_head(root, world_id)
        revision = load_world_graph_revision_manifest(root, world_id, head_revision_id)
        store = load_world_graph_revision(root, world_id, head_revision_id)
        parent_revision_id = revision.parent_revision_id
        payload = dump_union_supergraph_store(store)
        canonical = canonicalize_graph_payload(payload)
        payload_sha = sha256_hex(canonical)
        if payload_sha != revision.graph_payload_sha256:
            errors.append(
                "graph_payload_sha256 mismatch between revision manifest and loaded graph"
            )
        load_ok = True
        try:
            validate_union_supergraph_fixture(payload)
            validation_ok = True
        except UnionSupergraphValidationError as exc:
            errors.append(str(exc))
            validation_ok = False
        # Cross-check load_current convenience path.
        load_current_world_graph(root, world_id)
    except WorldGraphNotFoundError as exc:
        errors.append(str(exc))
        load_ok = False
        validation_ok = False
    except Exception as exc:  # pragma: no cover - unexpected I/O / parse
        errors.append(f"integrity load failed: {exc}")
        load_ok = False
        validation_ok = False

    if head_revision_id not in revision_ids:
        warnings.append(
            f"head_revision_id {head_revision_id!r} not found under revisions/"
        )

    report = WorldGraphIntegrityReport(
        world_id=world_id,
        head_revision_id=head_revision_id,
        parent_revision_id=parent_revision_id,
        load_ok=load_ok,
        validation_ok=validation_ok,
        revision_count=revision_count,
        graph_payload_sha256=payload_sha,
        errors=errors,
        warnings=warnings,
    )
    if persist:
        _persist_report(root, world_id, report)
    return report


def _persist_report(
    root: Path, world_id: str, report: WorldGraphIntegrityReport
) -> None:
    world_paths.integrity_dir(root, world_id).mkdir(parents=True, exist_ok=True)
    _write_json_atomic(
        world_paths.integrity_latest_path(root, world_id),
        report.model_dump(mode="json"),
    )
