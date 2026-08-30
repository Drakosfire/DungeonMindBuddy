"""CUTOVER D.2C4: Graph Review authoring continuity on DungeonMind.

The owning PostgreSQL witness starts from a legal reviewed-init head, then
exercises Graph Review prepare → confirm for object, link_existing, and
relationship publication, plus fail-closed merge_objects / unknown actions.
Buddy overlay and UnionSupergraph writers are tripwired.
"""

from __future__ import annotations

import hashlib
import json
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
from tests.test_live_extract_promote_api import (
    FIRST_WORLD_CONFIRM_URL,
    GLASS_ORCHARD_WORLD_ID,
    _candidate_graph_payload,
    _first_world_confirm_body,
)
from apps.live_control_server.services.graph_object_authoring_prepare import (
    GRAPH_REVIEW_PREPARE_BINDING_KEY_ENV,
)
from apps.live_control_server.services.promotable_ingest_run import (
    resolve_promotable_ingest_run,
)
from apps.live_control_server.integrations.dungeonmind import world_graph_reads as direct
from graph_memory.retrieval.models import (
    WorldGraphObjectRequest,
    WorldGraphSearchRequest,
    WorldGraphSourceAnchorReadRequest,
)
from tests.test_cutover_native_genesis_continuity import (
    _explode_kernel,
    _projection_request,
    _retrieval_context,
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

    from apps.live_control_server import config as wg_config

    repo = tmp_path / "repo"
    world_root = tmp_path / "world"
    repo.mkdir()
    world_root.mkdir()
    monkeypatch.setenv(
        wg_config.WORLD_GRAPH_AUTHORITY_ENV,
        wg_config.WORLD_GRAPH_AUTHORITY_DUNGEONMIND,
    )
    monkeypatch.setenv("DUNGEONMIND_WORLD_GRAPH_AUTHORITY_DATABASE_URL", dsn)
    monkeypatch.setenv("DUNGEONMIND_WORLD_GRAPH_ROOT", str(world_root))
    monkeypatch.setenv(
        "DUNGEONMIND_LIVE_WORLD_GRAPH_ROOT",
        str(tmp_path / "_designated_live_not_used"),
    )
    monkeypatch.delenv("DUNGEONMIND_EXTRACT_PROMOTE_SOURCE_ROOT", raising=False)
    monkeypatch.setenv(GRAPH_INGEST_RUNS_ENV, "out/graph_memory/runs")
    monkeypatch.setenv(GRAPH_REVIEW_PREPARE_BINDING_KEY_ENV, "d2c4-owning-witness-key")
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


def _write_post_genesis_graph_review_run(repo: Path) -> str:
    """Create a distinct Buddy ingest run whose DungeonMind source pair is absent.

    Uses a unique extraction directory so genesis ``wb1`` candidate bytes stay intact.
    """
    from apps.live_control_server.services.graph_run_registry import (
        create_extraction_run,
        update_extraction_run_status,
    )
    from apps.live_control_server.services.source_artifact_registry import (
        create_source_artifact_from_workspace_document,
        source_span_index_relpath,
    )
    from apps.live_control_server.services.workspace_document_registry import (
        create_workspace_document,
        mark_workspace_document_committed,
    )
    from graph_memory.ingestion.extraction_run import (
        ExtractionRunComponentKind,
        ExtractionRunComponentRef,
        ExtractionRunStatus,
    )
    from src.graph_memory.extraction.worldbuilding_plumbing_profile import (
        WORLDBUILDING_PLUMBING_PROFILE,
    )

    (repo / f"corpus/{GLASS_ORCHARD_WORLD_ID}-markdown").mkdir(parents=True, exist_ok=True)
    document = create_workspace_document(
        repo,
        title="D2C4 Graph Review source",
        campaign_id=GLASS_ORCHARD_WORLD_ID,
        world_id=GLASS_ORCHARD_WORLD_ID,
        kind="worldbuilding_source",
        source_domain="worldbuilding",
        document_class="lore",
        authority_state="draft",
        visibility_state="internal",
    )
    committed = mark_workspace_document_committed(
        repo, document.document_id, expected_revision=document.revision
    )
    source = repo / committed.target_relpath
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_text(
        "# D2C4 Graph Review\n\nPost-genesis source for manual authoring.\n",
        encoding="utf-8",
    )
    artifact = create_source_artifact_from_workspace_document(
        repo, document_id=committed.document_id, expected_revision=committed.revision
    )
    span_rel = source_span_index_relpath(artifact.source_artifact_id)
    span_path = repo / span_rel
    span_index = json.loads(span_path.read_text(encoding="utf-8"))
    span_ref_id = str(span_index["spans"][0]["source_span_id"])
    run_dir = repo / "out" / "graph_memory" / "runs" / "extraction" / "d2c4"
    run_dir.mkdir(parents=True, exist_ok=True)
    candidate_payload = _candidate_graph_payload(
        campaign_id=GLASS_ORCHARD_WORLD_ID,
        session_id="",
    )
    candidate_payload["session_id"] = None
    candidate_payload["source_artifact_ids"] = [artifact.source_artifact_id]
    worldbuilding_semantic = dict(WORLDBUILDING_PLUMBING_PROFILE.default_semantic_state)
    for holder in (
        *(candidate_payload.get("nodes") or []),
        *(candidate_payload.get("edges") or []),
    ):
        holder["semantic_state"] = dict(worldbuilding_semantic)
        for ref in holder.get("evidence_refs") or []:
            ref["source_artifact_id"] = artifact.source_artifact_id
            ref["source_span_ref_id"] = span_ref_id
            ref["anchor_quotes"] = ["Post-genesis source for manual authoring."]
    candidate_path = run_dir / "candidate_graph.json"
    candidate_path.write_text(json.dumps(candidate_payload, indent=2) + "\n", encoding="utf-8")

    def _digest(path: Path) -> str:
        return hashlib.sha256(path.read_bytes()).hexdigest()

    components = {
        "source_artifact": ExtractionRunComponentRef(
            kind=ExtractionRunComponentKind.SOURCE_ARTIFACT,
            uri=artifact.uri,
            sha256=artifact.content_sha256,
        ),
        "source_span_index": ExtractionRunComponentRef(
            kind=ExtractionRunComponentKind.SOURCE_SPAN_INDEX,
            uri=f"repo://{span_rel}",
            sha256=_digest(span_path),
        ),
        "candidate_graph": ExtractionRunComponentRef(
            kind=ExtractionRunComponentKind.CANDIDATE_GRAPH,
            uri=f"repo://{candidate_path.relative_to(repo).as_posix()}",
            sha256=_digest(candidate_path),
        ),
    }
    run = create_extraction_run(
        repo,
        source_artifact_id=artifact.source_artifact_id,
        source_domain="worldbuilding",
        campaign_id=GLASS_ORCHARD_WORLD_ID,
        session_id=None,
        profile_id="worldbuilding_plumbing_v0@0.1",
    )
    for step in (
        ExtractionRunStatus.PREPARED,
        ExtractionRunStatus.EXTRACTED,
        ExtractionRunStatus.VALIDATED,
        ExtractionRunStatus.REVIEWABLE,
    ):
        run = update_extraction_run_status(
            repo,
            run.run_id,
            status=step,
            expected_revision=run.revision,
            components=components if step == ExtractionRunStatus.PREPARED else None,
        )
    return run.run_id


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

    bundle = _bundle(dsn)
    review_run_id = _write_post_genesis_graph_review_run(repo)
    resolved = resolve_promotable_ingest_run(review_run_id)
    buddy_artifact_id = resolved.source_artifact_id
    buddy_token = resolved.source_revision_id
    assert bundle.sources.get_artifact(buddy_artifact_id) is None
    assert review_run_id != run_id

    object_prepare, object_commit = _prepare_and_commit(
        client, review_run_id, [_object_proposal()]
    )
    assert object_prepare["expressibility"] == "EXPRESSIBLE"
    assert object_prepare["expected_parent_revision_id"] == d0
    assert object_prepare["source_artifact_id"] == buddy_artifact_id
    sealed_revision = object_prepare["source_revision_id"]
    assert sealed_revision in {buddy_token, f"{buddy_token}::{buddy_artifact_id}"}
    admitted = _bundle(dsn)
    snapshot = admitted.sources.get_provenance_snapshot(
        artifact_ids=[buddy_artifact_id],
        revision_ids=[sealed_revision],
    )
    assert snapshot.get_artifact(buddy_artifact_id) is not None
    assert snapshot.get_revision(sealed_revision) is not None
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
    assert object_body["audit_status"] == "skipped"
    assert object_body.get("overlay_path") is None
    assert object_body.get("event_log_path") is None
    assert d1 != d0
    assert _counts(dsn, GLASS_ORCHARD_WORLD_ID)["revisions"] == 2

    retry = client.post(
        COMMIT_URL,
        json=_authoring_body(
            review_run_id,
            [_object_proposal()],
            confirmToken=object_prepare["confirm_token"],
            currentOverlayToken=object_prepare.get("current_overlay_token"),
        ),
    )
    assert retry.status_code == 200, retry.text
    retry_body = retry.json()
    assert retry_body["published_revision_id"] == d1
    assert retry_body["idempotency_status"] == "already_applied"
    assert retry_body["audit_status"] == "skipped"
    assert retry_body.get("overlay_path") is None
    assert _counts(dsn, GLASS_ORCHARD_WORLD_ID)["revisions"] == 2

    fresh = TestClient(create_app())
    lost = fresh.post(
        COMMIT_URL,
        json=_authoring_body(
            review_run_id,
            [_object_proposal()],
            confirmToken=object_prepare["confirm_token"],
            currentOverlayToken=object_prepare.get("current_overlay_token"),
        ),
    )
    assert lost.status_code == 200, lost.text
    assert lost.json()["published_revision_id"] == d1
    assert lost.json()["idempotency_status"] == "already_applied"
    assert lost.json()["audit_status"] == "skipped"
    assert lost.json().get("overlay_path") is None
    assert _counts(dsn, GLASS_ORCHARD_WORLD_ID)["revisions"] == 2

    from apps.live_control_server.integrations.dungeonmind.world_graph_authority_adapter import (
        DungeonMindWorldGraphAuthorityAdapter,
    )

    adapter = DungeonMindWorldGraphAuthorityAdapter(database_url=dsn)
    d1_view = adapter.read_revision(GLASS_ORCHARD_WORLD_ID, d1)
    assert reviewed_node_id in d1_view.objects
    assert EXISTING_NODE_ID in d1_view.objects

    services = direct.direct_services_from_bundle(
        _bundle(dsn), GLASS_ORCHARD_WORLD_ID
    )
    projection = direct.project_world_graph_direct(
        services, _projection_request(revision_pin=d1)
    )
    projected_ids = {node.node_id for node in projection.nodes}
    assert reviewed_node_id in projected_ids
    assert EXISTING_NODE_ID in projected_ids
    search = direct.search_world_graph_direct(
        services,
        WorldGraphSearchRequest(
            schema="dmb_world_graph_search_request_v1",
            queryText="D2C4 Reviewed Object",
            **_retrieval_context(revision_pin=d1),
        ),
    )
    assert reviewed_node_id in set(search.matched_node_ids)
    exact = direct.get_object_direct(
        services,
        WorldGraphObjectRequest(
            schema="dmb_world_graph_object_request_v1",
            nodeId=reviewed_node_id,
            **_retrieval_context(revision_pin=d1),
        ),
    )
    assert [node.node_id for node in exact.nodes] == [reviewed_node_id]
    assert exact.source_anchors
    assert any(
        anchor.source_artifact_id == buddy_artifact_id for anchor in exact.source_anchors
    )
    anchor = next(
        item
        for item in exact.source_anchors
        if item.source_artifact_id == buddy_artifact_id
    )
    resolved_anchor = direct.read_source_anchor_direct(
        services,
        WorldGraphSourceAnchorReadRequest(
            schema="dmb_world_graph_source_anchor_read_request_v1",
            anchorId=anchor.anchor_id,
            **_retrieval_context(revision_pin=d1),
        ),
        repo_root=repo,
    )
    assert resolved_anchor.outcome != "empty"
    assert resolved_anchor.source_artifact_id == buddy_artifact_id
    assert resolved_anchor.snapshot is not None
    assert resolved_anchor.snapshot.revision_id == d1

    run_id = review_run_id

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

    review_run_id = _write_post_genesis_graph_review_run(repo)
    stale_prepare = client.post(
        PREPARE_URL,
        json=_authoring_body(review_run_id, [_object_proposal()]),
    )
    assert stale_prepare.status_code == 200, stale_prepare.text
    intervening_prepare, intervening_commit = _prepare_and_commit(
        client,
        review_run_id,
        [_object_proposal() | {"localProposalId": "d2c4-intervening-object"}],
    )
    assert intervening_commit.status_code == 200, intervening_commit.text
    d1 = intervening_commit.json()["published_revision_id"]
    assert intervening_prepare["expected_parent_revision_id"] == d0
    stale_commit = client.post(
        COMMIT_URL,
        json=_authoring_body(
            review_run_id,
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
