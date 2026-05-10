from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Any

from src.lexicon_phase_b.route_equivalence_loader import (
    load_route_equivalence_manifests,
)
from src.lexicon_phase_b.schemas import RouteEquivalenceRecord

ROUTE_EQUIVALENCE_SHADOW_SCHEMA_V1 = "dmb_route_equivalence_shadow_v1"


def load_route_equivalence_shadow_records(
    paths: Sequence[Path],
) -> list[RouteEquivalenceRecord]:
    """Resolve each path to a real file, then call the lexicon-loader concat.

    Raises ``FileNotFoundError`` for any missing path. Order-preserving;
    delegates dedup + record sort to ``load_route_equivalence_manifests``.
    """
    resolved_paths = [Path(p).resolve() for p in paths]
    for path in resolved_paths:
        if not path.is_file():
            raise FileNotFoundError(f"route equivalence manifest not found: {path}")
    return load_route_equivalence_manifests(resolved_paths)


def _workspace_relative_posix(path: Path, workspace_root: Path) -> str:
    """Render ``path`` as a workspace-relative POSIX string when possible."""
    try:
        return path.resolve().relative_to(workspace_root.resolve()).as_posix()
    except ValueError:
        return path.name


def build_route_equivalence_shadow_payload(
    *,
    scenario_campaign_id: str,
    records: Sequence[RouteEquivalenceRecord],
    source_paths: Sequence[Path],
    workspace_root: Path,
) -> dict[str, Any]:
    """Build the per-scenario shadow diagnostic."""
    normalized_campaign_id = scenario_campaign_id.strip()
    campaign_ids = sorted({r.campaign_id for r in records})
    edges_for_scenario = sum(1 for r in records if r.campaign_id == normalized_campaign_id)
    return {
        "schema": ROUTE_EQUIVALENCE_SHADOW_SCHEMA_V1,
        "scenario_campaign_id": normalized_campaign_id,
        "edges_total": len(records),
        "edges_for_scenario_campaign": edges_for_scenario,
        "campaign_ids": campaign_ids,
        "source_paths": [_workspace_relative_posix(p, workspace_root) for p in source_paths],
    }
