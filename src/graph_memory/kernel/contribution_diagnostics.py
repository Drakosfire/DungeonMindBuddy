"""Contribution integrity diagnostics (PR005)."""

from __future__ import annotations

from pathlib import Path

from graph_memory.kernel.contribution_merge import _support_map
from apps.live_control_server.models.world_graph_contribution_models import ContributionIntegrityReport
from graph_memory.kernel.contribution_rebuild import (
    _canonical_graph_fingerprint,
    rebuild_from_contributions,
)
from graph_memory.kernel.world_graph import (
    WorldGraphNotFoundError,
    load_current_world_graph,
)
from graph_memory.world_supergraph.contribution_store import (
    load_contribution_index,
    load_contribution_record,
)


def build_contribution_integrity_report(
    root: Path,
    *,
    world_id: str,
    check_rebuild: bool = False,
) -> ContributionIntegrityReport:
    index = load_contribution_index(root, world_id)
    diagnostics: list[str] = []
    head_revision_id: str | None = None
    unsupported: list[str] = []
    introduced_by: dict[str, str] = {}
    active_support: dict[str, list[str]] = {}
    rebuild_equivalent: bool | None = None

    try:
        head, _rev, store = load_current_world_graph(root, world_id)
        head_revision_id = head.head_revision_id
        support = _support_map(store)
        for assertion_id, record in support.items():
            if record.introduced_by_contribution_id:
                introduced_by[assertion_id] = record.introduced_by_contribution_id
            active_support[assertion_id] = list(record.active_contribution_ids)
            if record.support_state in {"unsupported", "retracted"} or not record.active_contribution_ids:
                unsupported.append(assertion_id)
                if record.graph_object_id:
                    diagnostics.append(
                        f"unsupported_assertion:{assertion_id}:object={record.graph_object_id}"
                    )
    except WorldGraphNotFoundError:
        diagnostics.append("no_world_graph_head")

    for cid in index.failed_contribution_ids:
        try:
            failed = load_contribution_record(root, world_id, cid)
            diagnostics.extend(failed.diagnostics)
        except FileNotFoundError:
            diagnostics.append(f"failed_contribution_missing_record:{cid}")

    if check_rebuild and head_revision_id is not None and index.active_contribution_ids:
        result = rebuild_from_contributions(root, world_id=world_id, publish=False)
        rebuild_equivalent = "rebuild_equivalent_to_head" in result.diagnostics
        diagnostics.extend(
            d for d in result.diagnostics if d.startswith("rebuild_")
        )

    return ContributionIntegrityReport(
        world_id=world_id,
        head_revision_id=head_revision_id,
        contribution_count=len(index.all_contribution_ids),
        active_contribution_count=len(index.active_contribution_ids),
        superseded_contribution_count=len(index.superseded_contribution_ids),
        retracted_contribution_count=len(index.retracted_contribution_ids),
        failed_contribution_ids=list(index.failed_contribution_ids),
        unsupported_assertion_ids=unsupported,
        assertion_introduced_by=introduced_by,
        assertion_active_support=active_support,
        rebuild_equivalent_to_head=rebuild_equivalent,
        diagnostics=diagnostics,
    )


# Re-export for callers that want fingerprint comparison without rebuild.
graph_fingerprint = _canonical_graph_fingerprint
