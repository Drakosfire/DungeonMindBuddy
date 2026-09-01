#!/usr/bin/env python3
"""Operator-driven reviewed first-world initialization for the Of Conks & Cons module world.

Dogfood ingestion step: initializes world ``of-conks-cons`` on the local
DungeonMind Postgres authority from the manufactured gold contribution package
(local-only, copyrighted module; package path passed by arg, never committed).

This calls the same authority seam the product first-world confirm route calls
(``WorldGraphInitializationAuthority.initialize``). It does NOT run the
extract/review UI pipeline; that omission is recorded in the dogfood report.

Usage:
    uv run python evals/of_conks_end_to_end_dogfood/initialize_of_conks_world.py \
        --gold-package /path/to/of-conks-cons-v21-gold [--probe-only]
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from types import SimpleNamespace

REPO_ROOT = Path(__file__).resolve().parents[2]
for path in (REPO_ROOT / "src", REPO_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

WORLD_ID = "of-conks-cons"
CAMPAIGN_ID = "of-conks-cons"
INITIALIZATION_ID = "dmb:first-world:of-conks-cons:gold-v0"
ACTOR = "operator:of-conks-end-to-end-dogfood"


def _load_database_url() -> str:
    url = os.environ.get("DUNGEONMIND_WORLD_GRAPH_AUTHORITY_DATABASE_URL")
    if url:
        return url
    env_path = REPO_ROOT / ".env"
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith("DUNGEONMIND_WORLD_GRAPH_AUTHORITY_DATABASE_URL="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise SystemExit("DUNGEONMIND_WORLD_GRAPH_AUTHORITY_DATABASE_URL not found in env or .env")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gold-package", required=True, type=Path)
    parser.add_argument("--probe-only", action="store_true")
    args = parser.parse_args()

    gold = args.gold_package.resolve()
    manifest = json.loads((gold / "graph" / "manifest.json").read_text(encoding="utf-8"))
    contribution_path = gold / "graph" / manifest["ordered_contributions"][0]["path"]
    contribution_raw = json.loads(contribution_path.read_text(encoding="utf-8"))

    if manifest["world_id"] != WORLD_ID:
        raise SystemExit(f"unexpected world_id {manifest['world_id']!r}")

    # The top-level MANIFEST.json pins the prepared specimen digest.
    top_manifest = json.loads((gold / "MANIFEST.json").read_text(encoding="utf-8"))
    prepared_sha = None
    for entry in top_manifest["pinned"]:
        if entry["path"] == "specimens/02-prepared.md":
            prepared_sha = entry["sha256"]
    if not prepared_sha:
        raise SystemExit("prepared specimen sha256 not pinned in MANIFEST.json")
    expected_revision = f"sha256:{prepared_sha}"
    if contribution_raw["source_revision_id"] != expected_revision:
        raise SystemExit(
            f"contribution source_revision_id {contribution_raw['source_revision_id']} != {expected_revision}"
        )

    from apps.live_control_server.models.world_graph_contribution_models import (
        GraphContribution,
    )
    from apps.live_control_server.integrations.dungeonmind.world_graph_initialization_adapter import (
        DungeonMindWorldGraphInitializationAdapter,
    )
    from apps.live_control_server.ports.world_graph_initialization import (
        WorldGraphInitializationRequest,
    )

    contribution = GraphContribution.model_validate(contribution_raw)
    accepted = len(contribution.accepted_assertions)
    print(f"contribution {contribution.contribution_id}: {accepted} accepted assertions")

    # Vocabulary normalization (dogfood finding OC-010): gold v0 spells the
    # Jove parent-child edge as `child_of`, which the mounted v4 predicate map
    # intentionally does not resolve. Express it as reversed `parent_of`.
    normalized = 0
    for assertion in contribution.accepted_assertions:
        if assertion.assertion_kind == "edge" and assertion.predicate == "child_of":
            subject, target = assertion.subject_node_id, assertion.target_node_id
            assertion.predicate = "parent_of"
            assertion.label = "parent of"
            assertion.subject_node_id = target
            assertion.target_node_id = subject
            if isinstance(assertion.value, dict):
                assertion.value = {
                    **assertion.value,
                    "edge_id": f"edge:{target}:parent_of:{subject}",
                }
            normalized += 1
    if normalized:
        print(f"normalized {normalized} child_of edge(s) to reversed parent_of (OC-010)")

    source_artifact = SimpleNamespace(
        source_artifact_id=contribution.source_artifact_id,
        source_domain="worldbuilding",
        world_id=WORLD_ID,
        campaign_id=CAMPAIGN_ID,
        session_id=None,
        uri=f"file://{gold / 'specimens' / '02-prepared.md'}",
        content_sha256=prepared_sha,
        created_at="2026-08-12T00:00:00Z",
        workspace_document_id=None,
        workspace_document_revision=None,
        authority_state="draft",
        artifact_kind="adventure_module",
        document_class="adventure_module",
        visibility_state="gm",
        status="active",
        updated_at="2026-08-12T00:00:00Z",
        lineage={
            "dogfood": "of-conks-end-to-end",
            "gold_bundle_id": manifest["bundle_id"],
            "gold_bundle_digest": manifest["bundle_digest"],
        },
    )

    adapter = DungeonMindWorldGraphInitializationAdapter(database_url=_load_database_url())

    state = adapter.probe(WORLD_ID)
    print(f"probe: state={state.state} initialization_id={state.initialization_id} head={state.published_revision_id}")
    if args.probe_only:
        return 0

    request = WorldGraphInitializationRequest(
        world_id=WORLD_ID,
        campaign_id=CAMPAIGN_ID,
        initialization_id=INITIALIZATION_ID,
        source_plan_schema="dmb_first_world_graph_plan_v1",
        source_plan_id=manifest["bundle_id"],
        source_plan_sha256=manifest["bundle_digest"],
        actor=ACTOR,
        source_artifact=source_artifact,
        source_revision_token=expected_revision,
        source_uri=source_artifact.uri,
        reviewed_contribution=contribution,
    )
    receipt = adapter.initialize(request)
    print("initialize: outcome=", receipt.outcome)
    print("  published_revision_id:", receipt.published_revision_id)
    print("  reviewed_contribution_id:", receipt.reviewed_contribution_id)
    print("  accepted_assertion_ids:", len(receipt.accepted_assertion_ids))
    print("  initialized_at:", receipt.initialized_at)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
