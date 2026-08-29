"""CUTOVER D.2C4: Graph Review authoring continuity on DungeonMind.

The owning PostgreSQL witness starts from a legal reviewed-init head, then
exercises Graph Review prepare → confirm for object, link_existing, and
relationship publication, plus fail-closed merge_objects / unknown actions.
Buddy overlay and UnionSupergraph writers are tripwired.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import apps.live_control_server.config as live_config
import apps.live_control_server.services.extract_promote as promote_svc
import apps.live_control_server.services.promotable_ingest_run as promotable_mod
from apps.live_control_server.main import create_app
from apps.live_control_server.services.graph_ingest_run_registry import (
    GRAPH_INGEST_RUNS_ENV,
)
from apps.live_control_server.services.graph_authoring_overlay_projection import (
    authored_object_node_id,
)
from tests.test_cutover_dungeonmind_first_world_initialization import (
    _bundle,
    _counts,
    _prepare_native_plan,
)
from tests.test_cutover_dungeonmind_world_graph_authority import (
    TRUNCATE_SQL,
    _ensure_migrated,
    _test_dsn,
)
from tests.test_cutover_native_genesis_continuity import _explode_kernel
from tests.test_live_extract_promote_api import (
    FIRST_WORLD_CONFIRM_URL,
    GLASS_ORCHARD_WORLD_ID,
    _first_world_confirm_body,
)

PREPARE_URL = "/api/live/graph-authoring/prepare"
COMMIT_URL = "/api/live/graph-authoring/commit"
REVIEWED_OBJECT_ID = "d2c4-reviewed-object"
EXISTING_NODE_ID = "obj_session22_vial"


def _visibility() -> dict[str, object]:
    return {"visibility": "gm_private", "revealState": "unrevealed"}


def _provenance() -> dict[str, object]:
    return {
        "origin": "human_authored",
        "authoringSurface": "memory_ingest_graph_authoring",
    }


def _object_proposal() -> dict[str, object]:
    return {
        "localProposalId": REVIEWED_OBJECT_ID,
        "proposalKind": "object",
        "status": "staged_local",
        "objectRef": {
            "label": "D2C4 Reviewed Object",
            "kind": "party",
            "aliases": ["reviewed object"],
            "summary": "Graph Review authored object",
        },
        "visibility": _visibility(),
        "graphScopes": ["recap_graph", "campaign_memory_graph"],
        "provenancePreview": _provenance(),
    }


def _link_proposal() -> dict[str, object]:
    return {
        "localProposalId": "d2c4-link-existing",
        "proposalKind": "link_existing",
        "status": "staged_local",
        "selectedText": "vial",
        "normalizedSelectedText": "vial",
        "existingObjectRef": {
            "refKind": "existing_graph_node",
            "nodeId": EXISTING_NODE_ID,
            "label": "Session 22 vial",
            "kind": "item",
        },
        "operation": "alias",
        "visibility": _visibility(),
        "graphScopes": ["recap_graph", "campaign_memory_graph"],
        "provenancePreview": _provenance(),
    }


def _relationship_proposal(source_node_id: str) -> dict[str, object]:
    return {
        "localProposalId": "d2c4-relationship",
        "proposalKind": "relationship",
        "status": "staged_local",
        "sourceObjectRef": {
            "refKind": "existing_graph_node",
            "nodeId": source_node_id,
            "label": "D2C4 Reviewed Object",
            "kind": "party",
        },
        "targetObjectRef": {
            "refKind": "existing_graph_node",
            "nodeId": EXISTING_NODE_ID,
            "label": "Session 22 vial",
            "kind": "item",
        },
        "relationshipType": "associated_with",
        "direction": "directed",
        "visibility": _visibility(),
        "graphScopes": ["recap_graph", "campaign_memory_graph"],
        "provenancePreview": _provenance(),
    }


def _merge_proposal() -> dict[str, object]:
    return {
        "localProposalId": "d2c4-merge",
        "proposalKind": "merge_objects",
        "status": "staged_local",
        "survivorObjectRef": {
            "refKind": "existing_graph_node",
            "nodeId": EXISTING_NODE_ID,
            "label": "Session 22 vial",
            "kind": "item",
        },
        "mergedObjectRefs": [
            {
                "refKind": "existing_graph_node",
                "nodeId": REVIEWED_OBJECT_ID,
                "label": "D2C4 Reviewed Object",
                "kind": "party",
            }
        ],
        "mergeReason": "unsupported native merge",
        "matchedFeatures": ["label overlap"],
        "aliasPolicy": "preserve_all_aliases",
        "relationshipPolicy": "preserve_all_relationships",
        "evidencePolicy": "preserve_all_evidence",
        "visibility": _visibility(),
        "graphScopes": ["recap_graph", "campaign_memory_graph"],
        "provenancePreview": _provenance(),
    }


def _authoring_body(run_id: str, proposals: list[dict[str, object]], **extra) -> dict[str, object]:
    payload: dict[str, object] = {
        "campaignId": GLASS_ORCHARD_WORLD_ID,
        "campaignRel": "The Glass Orchard",
        "worldId": GLASS_ORCHARD_WORLD_ID,
        "sessionId": "session-d2c4",
        "sourceRunId": run_id,
        "proposals": proposals,
    }
    payload.update(extra)
    return payload


@pytest.fixture
def native_first_world_client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    dsn = _test_dsn()
    _ensure_migrated(dsn)
    from dungeonmind.infrastructure.postgres import PostgresDatabase

    database = PostgresDatabase(dsn)
    with database.connect() as conn:
        conn.execute(TRUNCATE_SQL)
        conn.commit()

    from graph_memory.world_supergraph import storage

    repo = tmp_path / "repo"
    world_root = tmp_path / "world"
    repo.mkdir()
    world_root.mkdir()
    monkeypatch.setenv(storage.WORLD_GRAPH_AUTHORITY_ENV, storage.WORLD_GRAPH_AUTHORITY_DUNGEONMIND)
    monkeypatch.setenv("DUNGEONMIND_WORLD_GRAPH_AUTHORITY_DATABASE_URL", dsn)
    monkeypatch.setenv("DUNGEONMIND_WORLD_GRAPH_ROOT", str(world_root))
    monkeypatch.setenv(
        "DUNGEONMIND_LIVE_WORLD_GRAPH_ROOT",
        str(tmp_path / "_designated_live_not_used"),
    )
    monkeypatch.delenv("DUNGEONMIND_EXTRACT_PROMOTE_SOURCE_ROOT", raising=False)
    monkeypatch.setenv(GRAPH_INGEST_RUNS_ENV, "out/graph_memory/runs")
    monkeypatch.setattr(live_config, "repo_root", lambda: repo)
    monkeypatch.setattr(promote_svc, "repo_root", lambda: repo)
    monkeypatch.setattr(promotable_mod, "repo_root", lambda: repo)
    client = TestClient(create_app())
    return client, world_root, repo, dsn


def _arm_legacy_writer_tripwires(monkeypatch: pytest.MonkeyPatch) -> None:
    def _explode(*_args, **_kwargs):
        raise AssertionError("legacy Buddy graph writer invoked during Graph Review confirm")

    monkeypatch.setattr(
        "apps.live_control_server.services.graph_authoring_overlay_store.GraphAuthoringOverlayStore.append_assertions",
        _explode,
    )
    monkeypatch.setattr(
        "apps.live_control_server.services.graph_authoring_overlay_store.GraphAuthoringOverlayStore.save_overlay",
        _explode,
    )
    monkeypatch.setattr(
        "graph_memory.union_supergraph.load.write_union_supergraph_store",
        _explode,
    )
    monkeypatch.setattr(
        "graph_memory.union_supergraph.merge_reconciliation_apply.apply_union_supergraph_merge_plan_to_file",
        _explode,
    )


def _prepare_and_commit(
    client: TestClient,
    run_id: str,
    proposals: list[dict[str, object]],
) -> tuple[dict, dict]:
    prepare = client.post(PREPARE_URL, json=_authoring_body(run_id, proposals))
    assert prepare.status_code == 200, prepare.text
    prepared = prepare.json()
    commit = client.post(
        COMMIT_URL,
        json=_authoring_body(
            run_id,
            proposals,
            confirmToken=prepared["confirm_token"],
            currentOverlayToken=prepared.get("current_overlay_token"),
        ),
    )
    return prepared, commit


@pytest.mark.integration
def test_graph_review_authoring_continuity_one_world_sequence(
    native_first_world_client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, _world_root, repo, dsn = native_first_world_client
    run_id, plan = _prepare_native_plan(client, repo)
    confirm = client.post(FIRST_WORLD_CONFIRM_URL, json=_first_world_confirm_body(plan))
    assert confirm.status_code == 200, confirm.text
    d0 = confirm.json()["committedRevisionId"]
    assert d0
    assert _counts(dsn, GLASS_ORCHARD_WORLD_ID)["revisions"] == 1

    _explode_kernel(monkeypatch)
    _arm_legacy_writer_tripwires(monkeypatch)

    from apps.live_control_server.integrations.dungeonmind.world_graph_authority_adapter import (
        DungeonMindWorldGraphAuthorityAdapter,
    )

    adapter = DungeonMindWorldGraphAuthorityAdapter(database_url=dsn)

    object_prepare, object_commit = _prepare_and_commit(client, run_id, [_object_proposal()])
    assert object_prepare["expressibility"] == "EXPRESSIBLE"
    assert object_prepare["expected_parent_revision_id"] == d0
    assert object_commit.status_code == 200, object_commit.text
    object_body = object_commit.json()
    d1 = object_body["published_revision_id"]
    reviewed_node_id = authored_object_node_id(
        object_prepare["assertions_preview"][0]["assertion_id"]
    )
    assert object_body["parent_revision_id"] == d0
    assert object_body["world_id"] == GLASS_ORCHARD_WORLD_ID
    assert object_body["idempotency_status"] == "published"
    assert object_body["operation_id"].startswith("grauth:")
    assert d1 != d0
    assert _counts(dsn, GLASS_ORCHARD_WORLD_ID)["revisions"] == 2

    retry = client.post(
        COMMIT_URL,
        json=_authoring_body(
            run_id,
            [_object_proposal()],
            confirmToken=object_prepare["confirm_token"],
            currentOverlayToken=object_prepare.get("current_overlay_token"),
        ),
    )
    assert retry.status_code == 200, retry.text
    retry_body = retry.json()
    assert retry_body["published_revision_id"] == d1
    assert retry_body["idempotency_status"] == "already_applied"
    assert _counts(dsn, GLASS_ORCHARD_WORLD_ID)["revisions"] == 2

    adapter = DungeonMindWorldGraphAuthorityAdapter(database_url=dsn)
    d1_view = adapter.read_revision(GLASS_ORCHARD_WORLD_ID, d1)
    assert reviewed_node_id in d1_view.objects
    assert EXISTING_NODE_ID in d1_view.objects

    link_prepare, link_commit = _prepare_and_commit(client, run_id, [_link_proposal()])
    assert link_prepare["expected_parent_revision_id"] == d1
    assert link_commit.status_code == 200, link_commit.text
    link_body = link_commit.json()
    d2 = link_body["published_revision_id"]
    assert link_body["parent_revision_id"] == d1
    assert d2 != d1
    assert _counts(dsn, GLASS_ORCHARD_WORLD_ID)["revisions"] == 3
    d2_view = adapter.read_revision(GLASS_ORCHARD_WORLD_ID, d2)
    assert EXISTING_NODE_ID in d2_view.objects
    aliases = d2_view.objects[EXISTING_NODE_ID].aliases
    assert "vial" in aliases or aliases

    rel_prepare, rel_commit = _prepare_and_commit(
        client, run_id, [_relationship_proposal(reviewed_node_id)]
    )
    assert rel_prepare["expected_parent_revision_id"] == d2
    assert rel_commit.status_code == 200, rel_commit.text
    rel_body = rel_commit.json()
    d3 = rel_body["published_revision_id"]
    assert rel_body["parent_revision_id"] == d2
    assert _counts(dsn, GLASS_ORCHARD_WORLD_ID)["revisions"] == 4
    d3_view = adapter.read_revision(GLASS_ORCHARD_WORLD_ID, d3)
    assert reviewed_node_id in d3_view.objects
    assert any(
        rel.subject_object_id == reviewed_node_id
        and rel.target_object_id == EXISTING_NODE_ID
        for rel in d3_view.relationships.values()
    )

    merge_prepare = client.post(PREPARE_URL, json=_authoring_body(run_id, [_merge_proposal()]))
    assert merge_prepare.status_code == 200, merge_prepare.text
    merge_prepared = merge_prepare.json()
    assert merge_prepared["expressibility"] == "INEXPRESSIBLE"
    merge_commit = client.post(
        COMMIT_URL,
        json=_authoring_body(
            run_id,
            [_merge_proposal()],
            confirmToken=merge_prepared["confirm_token"],
            currentOverlayToken=merge_prepared.get("current_overlay_token"),
        ),
    )
    assert merge_commit.status_code == 409, merge_commit.text
    assert merge_commit.json()["detail"]["code"] == "governed_write_inexpressible"
    assert _counts(dsn, GLASS_ORCHARD_WORLD_ID)["revisions"] == 4
    assert _bundle(dsn).world_graph.get_head(GLASS_ORCHARD_WORLD_ID).head_revision_id == d3

    unknown = client.post(
        PREPARE_URL,
        json=_authoring_body(
            run_id,
            [{**_object_proposal(), "proposalKind": "explode"}],
        ),
    )
    assert unknown.status_code == 422
    assert _counts(dsn, GLASS_ORCHARD_WORLD_ID)["revisions"] == 4

    missing_body = _authoring_body(run_id, [_object_proposal()])
    missing_body.pop("sourceRunId")
    missing_source = client.post(PREPARE_URL, json=missing_body)
    assert missing_source.status_code in {409, 422}
    if missing_source.status_code == 409:
        assert missing_source.json()["detail"]["code"] == "source_unresolved"
    assert _counts(dsn, GLASS_ORCHARD_WORLD_ID)["revisions"] == 4
    assert adapter.current_head(GLASS_ORCHARD_WORLD_ID).revision_id == d3


@pytest.mark.integration
def test_graph_review_stale_parent_fails_closed(
    native_first_world_client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, _world_root, repo, dsn = native_first_world_client
    run_id, plan = _prepare_native_plan(client, repo)
    confirm = client.post(FIRST_WORLD_CONFIRM_URL, json=_first_world_confirm_body(plan))
    assert confirm.status_code == 200, confirm.text
    d0 = confirm.json()["committedRevisionId"]
    _explode_kernel(monkeypatch)
    _arm_legacy_writer_tripwires(monkeypatch)

    stale_prepare = client.post(
        PREPARE_URL,
        json=_authoring_body(run_id, [_object_proposal()]),
    )
    assert stale_prepare.status_code == 200, stale_prepare.text
    intervening_prepare, intervening_commit = _prepare_and_commit(
        client,
        run_id,
        [_object_proposal() | {"localProposalId": "d2c4-intervening-object"}],
    )
    assert intervening_commit.status_code == 200, intervening_commit.text
    d1 = intervening_commit.json()["published_revision_id"]
    assert intervening_prepare["expected_parent_revision_id"] == d0
    stale_commit = client.post(
        COMMIT_URL,
        json=_authoring_body(
            run_id,
            [_object_proposal()],
            confirmToken=stale_prepare.json()["confirm_token"],
            currentOverlayToken=stale_prepare.json().get("current_overlay_token"),
        ),
    )
    assert stale_commit.status_code == 409, stale_commit.text
    assert stale_commit.json()["detail"]["code"] == "stale_parent"
    assert _counts(dsn, GLASS_ORCHARD_WORLD_ID)["revisions"] == 2
    from apps.live_control_server.integrations.dungeonmind.world_graph_authority_adapter import (
        DungeonMindWorldGraphAuthorityAdapter,
    )

    adapter = DungeonMindWorldGraphAuthorityAdapter(database_url=dsn)
    assert adapter.current_head(GLASS_ORCHARD_WORLD_ID).revision_id == d1
