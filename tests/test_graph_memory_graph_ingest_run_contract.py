from __future__ import annotations

import json
from pathlib import Path

from graph_memory.ingestion import (
    GRAPH_INGEST_RUN_MANIFEST_SCHEMA,
    GraphIngestArtifactKind,
    GraphIngestRunManifest,
    GraphIngestRunStatus,
)

FIXTURE_DIR = Path("tests/fixtures/graph_memory/ingestion")


def load_fixture(name: str) -> dict:
    return json.loads((FIXTURE_DIR / name).read_text())


def test_valid_minimal_manifest_parses() -> None:
    manifest = GraphIngestRunManifest.model_validate(
        load_fixture("graph_ingest_run_manifest_minimal.json")
    )

    assert manifest.schema == GRAPH_INGEST_RUN_MANIFEST_SCHEMA
    assert manifest.status == GraphIngestRunStatus.SOURCE_READY
    assert manifest.campaign_id == "longmont-c2"
    assert manifest.session_id == "session-24"
    assert manifest.source.normalized_recap_sha256 is not None
    assert manifest.health.node_count == 0
    assert manifest.diagnostics.preview_only is True
    assert manifest.diagnostics.canon_promotion is False


def test_ready_for_projection_manifest_parses() -> None:
    manifest = GraphIngestRunManifest.model_validate(
        load_fixture("graph_ingest_run_manifest_ready_for_projection.json")
    )

    assert manifest.status == GraphIngestRunStatus.READY_FOR_PROJECTION
    assert (
        manifest.artifacts["preview_union_store"].kind
        == GraphIngestArtifactKind.PREVIEW_UNION_STORE
    )
    assert (
        manifest.artifacts["preview_union_store"].schema
        == "dmb_union_supergraph_store_v0"
    )
    assert manifest.projection is not None
    assert manifest.projection.projection_ready is True
    assert manifest.projection.query["session_id"] == "session-24"


def test_manifest_model_dump_is_json_safe() -> None:
    manifest = GraphIngestRunManifest.model_validate(
        load_fixture("graph_ingest_run_manifest_ready_for_projection.json")
    )

    dumped = manifest.model_dump(mode="json", by_alias=True)

    json.dumps(dumped, sort_keys=True)
    assert dumped["schema"] == GRAPH_INGEST_RUN_MANIFEST_SCHEMA
    assert (
        dumped["artifacts"]["preview_union_store"]["schema"]
        == "dmb_union_supergraph_store_v0"
    )
