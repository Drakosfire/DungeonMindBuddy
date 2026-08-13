"""Explicit whole-world analysis against DungeonMind world-object-v5 / property-v3.

Thin target entrypoints over the parameterized v4 analyzer core. Does not duplicate
classification logic and never infers "latest"/"current"/"default".
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from graph_memory.union_supergraph.model import UnionSupergraphStore

from apps.live_control_server.integrations.dungeonmind_kernel.whole_world_conformance_v4 import (
    CURRENT_V5_TARGET,
    LEGACY_SOURCE_HISTORY_POLICY,
    WholeWorldConformanceReportV4,
    WholeWorldSourceHistoryPolicy,
    _analyze_loaded_buddy_world_store_v4,
    _load_exact_buddy_revision,
    compact_whole_world_conformance_report_v4,
)


def analyze_exact_buddy_world_revision_v5(
    *,
    root: Path,
    world_id: str,
    revision_id: str,
) -> WholeWorldConformanceReportV4:
    """Inventory and classify one exact Buddy revision against CURRENT_V5_TARGET."""
    manifest, store = _load_exact_buddy_revision(
        root=root,
        world_id=world_id,
        revision_id=revision_id,
    )
    return _analyze_loaded_buddy_world_store_v4(
        root=root,
        world_id=world_id,
        revision_id=revision_id,
        manifest=manifest,
        store=store,
        target=CURRENT_V5_TARGET,
    )


def _analyze_loaded_buddy_world_store_v5(
    *,
    root: Path,
    world_id: str,
    revision_id: str,
    manifest: Any,
    store: UnionSupergraphStore,
    classified_out: list[Any] | None = None,
    source_history_policy: WholeWorldSourceHistoryPolicy = LEGACY_SOURCE_HISTORY_POLICY,
) -> WholeWorldConformanceReportV4:
    """Private loaded-store path for in-memory migration projections under v5."""
    return _analyze_loaded_buddy_world_store_v4(
        root=root,
        world_id=world_id,
        revision_id=revision_id,
        manifest=manifest,
        store=store,
        target=CURRENT_V5_TARGET,
        source_history_policy=source_history_policy,
        classified_out=classified_out,
    )


def compact_whole_world_conformance_report_v5(
    report: WholeWorldConformanceReportV4,
) -> dict[str, Any]:
    """Reuse the durable v4 report compaction shape for v5-target reports."""
    return compact_whole_world_conformance_report_v4(report)
