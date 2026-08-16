#!/usr/bin/env -S uv run python
"""Build or check the sealed Eldyrwild DungeonMind v6 adoption bundle v2."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from apps.live_control_server.integrations.dungeonmind_kernel.eldyrwild_existing_world_adoption_bundle_v2 import (  # noqa: E402
    EldyrwildAdoptionBundleV2Error,
    check_eldyrwild_existing_world_adoption_bundle_v2,
    write_eldyrwild_existing_world_adoption_bundle_v2,
)


def _path(value: str | None) -> Path | None:
    return Path(value).resolve() if value else None


def _summary(built: object) -> dict[str, object]:
    return {
        "schema_version": built.bundle.schema_version,
        "adoption_id": built.bundle.adoption_id,
        "raw_node_count": built.raw_node_count,
        "raw_edge_count": built.raw_edge_count,
        "current_semantic_count": built.current_semantic_count,
        "mechanics_count": len(built.mechanics_proofs),
        "history_only_count": built.history_only_count,
        "represented_before_projections": built.represented_before_projections,
        "residual_before_projections": built.residual_before_projections,
        "represented_after_kind_repair": built.represented_after_kind_repair,
        "residual_after_kind_repair": built.residual_after_kind_repair,
        "v6_object_count": built.v6_object_count,
        "v6_relationship_count": built.v6_relationship_count,
        "secondary_aspect_count": built.secondary_aspect_count,
        "aspect_selected_relationship_count": built.aspect_selected_relationship_count,
        "current_unrepresentable_count": built.current_unrepresentable_count,
        "false_stop_history": f"{len(built.false_stop_reports)} / {len(built.false_stop_reports)} SOURCE_MIGRATION_HISTORY",
        "contribution_count": built.contribution_count,
        "assertion_count": built.assertion_count,
        "correction_count": built.correction_count,
        "identity_decision_count": built.identity_decision_count,
        "expected_published_revision_id": built.expected_published_revision_id,
        "canonical_bytes": len(built.canonical_bytes),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Seal or verify the Eldyrwild dm_existing_world_adoption_bundle_v2 artifact."
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true", help="Verify the artifact without writing.")
    mode.add_argument("--write", action="store_true", help="Atomically write the canonical artifact.")
    parser.add_argument("--root", help="world graph root (defaults to environment/out)")
    parser.add_argument("--repo", help="repository root (defaults to this repository)")
    args = parser.parse_args(argv)
    try:
        if args.write:
            built = write_eldyrwild_existing_world_adoption_bundle_v2(
                root=_path(args.root),
                repo=_path(args.repo),
            )
        else:
            built = check_eldyrwild_existing_world_adoption_bundle_v2(
                root=_path(args.root),
                repo=_path(args.repo),
            )
    except EldyrwildAdoptionBundleV2Error as exc:
        print(json.dumps({"error": str(exc), "code": exc.code}, indent=2), file=sys.stderr)
        return 2
    print(json.dumps(_summary(built), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
