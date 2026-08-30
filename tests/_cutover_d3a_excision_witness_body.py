"""D.3A owning-witness body: imported only AFTER the legacy import blocker."""

from __future__ import annotations

import ast
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

FORBIDDEN = (
    "graph_memory.kernel",
    "graph_memory.world_supergraph",
    "graph_memory.union_supergraph",
)

REPO_ROOT = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 8, 22, 18, 0, tzinfo=UTC)
WORLD_ID = "world:d3a-witness"
CAMPAIGN_ID = "camp:one"


def _assert_no_forbidden_loaded() -> None:
    loaded = [
        name
        for name in sys.modules
        if any(name == f or name.startswith(f + ".") for f in FORBIDDEN)
    ]
    assert loaded == [], f"forbidden modules loaded: {loaded}"


def _assert_mounted_services_have_no_kernel_escape() -> None:
    targets = [
        REPO_ROOT
        / "apps/live_control_server/services/world_graph_projection.py",
        REPO_ROOT
        / "apps/live_control_server/services/world_graph_retrieval.py",
    ]
    banned_substrings = (
        "graph_memory.kernel",
        "route_service_read",
        "dungeonmind_kernel",
        "_kernel",
    )
    for path in targets:
        source = path.read_text(encoding="utf-8")
        for banned in banned_substrings:
            assert banned not in source, f"{path.name} still contains {banned!r}"
        tree = ast.parse(source, filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert not alias.name.startswith("graph_memory.kernel")
            if isinstance(node, ast.ImportFrom) and node.module:
                assert not node.module.startswith("graph_memory.kernel")
                assert "dungeonmind_kernel" not in node.module



def _seed_sources():
    import hashlib

    from dungeonmind.contracts.evidence import (
        SourceArtifactV2,
        SourceDomain,
        SourceRevision,
        SourceStatus,
    )
    from dungeonmind.contracts.vocabulary import Visibility
    from dungeonmind.infrastructure.memory import InMemorySourceRepository

    digest = hashlib.sha256(b"d3a-witness").hexdigest()
    sources = InMemorySourceRepository()
    sources.put_artifact(
        SourceArtifactV2(
            source_artifact_id="src:one-recap",
            source_domain_key="buddy.worldbuilding",
            source_domain=SourceDomain.WORLDBUILDING,
            world_id=WORLD_ID,
            campaign_id=CAMPAIGN_ID,
            session_id=None,
            uri=None,
            current_revision_id="srcrev:one-recap-v1",
            authority=None,
            visibility=Visibility.GM,
            artifact_kind=None,
            document_class=None,
            review_state=None,
            source_visibility_state=None,
            workspace_document_ref=None,
            lineage={},
            status=SourceStatus.ACTIVE,
            created_at=NOW,
            updated_at=NOW,
        )
    )
    sources.put_revision(
        SourceRevision(
            source_revision_id="srcrev:one-recap-v1",
            source_artifact_id="src:one-recap",
            content_sha256=digest,
            body_storage="external",
            locator="test://src:one-recap",
            created_at=NOW,
        )
    )
    return sources



def _seed_direct_services():
    from dungeonmind.contracts.graph import PublishRevisionCommand
    from dungeonmind.infrastructure.memory import (
        InMemoryWorldGraphRepository,
    )
    from apps.live_control_server.integrations.dungeonmind import (
        world_graph_reads as direct,
    )

    def meta(assertion_id: str, *, evidence: tuple[str, ...], visibility: str = "gm"):
        return {
            "schema_version": "dm_knowledge_assertion_metadata_v1",
            "assertion_id": assertion_id,
            "campaign_scope": None,
            "visibility": visibility,
            "epistemic_kind": "fact",
            "canon_state": "canonical",
            "evidence_ref_ids": list(evidence),
            "session_refs": [],
            "temporal_scope": {
                "schema_version": "dm_temporal_scope_ref_v1",
                "kind": "unknown",
            },
        }

    from dungeonmind.application.semantic_profiles import descriptor_sha256
    from dungeonmind_dnd.application.world_object_vocabulary import (
        load_builtin_v3_descriptor,
    )

    descriptor = load_builtin_v3_descriptor()
    payload = {
        "world_id": WORLD_ID,
        "semantic_profile": {
            "schema_version": "dm_semantic_profile_ref_v1",
            "profile_id": descriptor.profile_id,
            "profile_revision": descriptor.profile_revision,
            "descriptor_sha256": descriptor_sha256(descriptor),
        },
        "relationship_endpoint_aspect_schema": "dm_relationship_endpoint_aspect_v1",
        "objects": [
            {
                "object_id": "obj:tavern",
                "kind": "dnd5e:location",
                "label": "The Prancing Tavern",
                "assertion_metadata": meta("asrt:obj:tavern", evidence=("ev:tavern",)),
                "aliases": [],
                "summary": None,
                "properties": [],
                "aspects": [],
            }
        ],
        "relationships": [],
        "evidence_refs": [
            {
                "schema_version": "dm_evidence_ref_v2",
                "evidence_ref_id": "ev:tavern",
                "source_artifact_id": "src:one-recap",
                "source_revision_id": "srcrev:one-recap-v1",
                "source_domain_key": "buddy.worldbuilding",
                "source_domain": "worldbuilding",
                "evidence_role": "support",
                "can_open_source": True,
                "can_highlight_span": False,
                "session_id": "session-9",
                "source_span_ref_id": None,
                "locator": "heading:Tavern",
                "uri": None,
                "source_locator": None,
                "line_ref": None,
            }
        ],
    }

    world_graph = InMemoryWorldGraphRepository()
    published = world_graph.publish_revision(
        PublishRevisionCommand(
            world_id=WORLD_ID,
            parent_revision_id=None,
            expected_parent_revision_id=None,
            operation_ids=["op:d3a-witness"],
            graph_schema="dm_union_graph_v6",
            graph_payload=payload,
            created_at=NOW,
        )
    )
    class _FakeReviewedInitReceipt:
        def __init__(self, world_id: str, published_revision_id: str) -> None:
            self.world_id = world_id
            self.published_revision_id = published_revision_id
            self.published_graph_schema = "dm_union_graph_v6"
            self.published_graph_payload_sha256 = published.graph_payload_sha256
            self.source_plan_schema = "test_reviewed_init_plan"
            self.initialization_id = "init:d3a-witness"
            self.actor = "d3a-witness@local"

    class _Adoption:
        def get_for_world(self, world_id: str):
            return None

    class _Init:
        def __init__(self, receipt: _FakeReviewedInitReceipt) -> None:
            self._receipt = receipt

        def get_for_world(self, world_id: str):
            return self._receipt if world_id == WORLD_ID else None

    class _Bundle:
        def __init__(self) -> None:
            self.world_graph = world_graph
            self.sources = _seed_sources()
            self.existing_world_adoptions = _Adoption()
            self.reviewed_world_initializations = _Init(
                _FakeReviewedInitReceipt(WORLD_ID, published.revision_id)
            )

    return direct.direct_services_from_bundle(_Bundle(), WORLD_ID), published.revision_id


def _exercise_projection_and_retrieval() -> None:
    from apps.live_control_server.integrations.dungeonmind import (
        world_graph_reads as direct,
    )
    from apps.live_control_server.services import world_graph_projection as projection
    from apps.live_control_server.services import world_graph_retrieval as retrieval
    from graph_memory.projection.world_projection import WorldGraphProjectionRequest
    from graph_memory.retrieval.models import (
        WorldGraphEvidenceRequest,
        WorldGraphNeighborhoodRequest,
        WorldGraphObjectRequest,
        WorldGraphSearchRequest,
        WorldGraphSourceAnchorReadRequest,
    )

    services, head = _seed_direct_services()
    direct.direct_services_from_config = lambda world_id: services  # type: ignore[assignment]

    other = Path(os.environ["DUNGEONMIND_WORLD_GRAPH_ROOT"]) / "alternate-root"
    other.mkdir(parents=True, exist_ok=True)
    request = WorldGraphProjectionRequest(
        schema="dmb_world_graph_projection_request_v1",
        world_id=WORLD_ID,
        campaign_id=CAMPAIGN_ID,
        admissibility="gm",
        scope_mode="campaign",
    )
    try:
        projection.project_world_graph(request, root=other)
        raise AssertionError("alternate root must fail closed")
    except projection.WorldGraphProjectionServiceError as exc:
        assert exc.code == "world_graph_authority_configuration_invalid"

    projected = projection.project_world_graph(request)
    assert any(n.node_id == "obj:tavern" for n in projected.nodes)
    assert projected.snapshot.revision_id == head

    ctx = {
        "worldId": WORLD_ID,
        "campaignId": CAMPAIGN_ID,
        "admissibility": "gm",
        "scopeMode": "campaign",
    }
    search = retrieval.search_campaign_graph(
        WorldGraphSearchRequest(
            schema="dmb_world_graph_search_request_v1",
            queryText="Tavern",
            **ctx,
        )
    )
    assert any(n.label == "The Prancing Tavern" for n in search.nodes)
    obj = retrieval.get_campaign_object(
        WorldGraphObjectRequest(
            schema="dmb_world_graph_object_request_v1",
            nodeId="obj:tavern",
            **ctx,
        )
    )
    assert [n.node_id for n in obj.nodes] == ["obj:tavern"]
    neighborhood = retrieval.get_object_neighborhood(
        WorldGraphNeighborhoodRequest(
            schema="dmb_world_graph_neighborhood_request_v1",
            seedNodeIds=["obj:tavern"],
            maxDepth=1,
            **ctx,
        )
    )
    assert any(n.node_id == "obj:tavern" for n in neighborhood.nodes)
    evidence = retrieval.get_object_evidence(
        WorldGraphEvidenceRequest(
            schema="dmb_world_graph_evidence_request_v1",
            target={"kind": "node", "id": "obj:tavern"},
            **ctx,
        )
    )
    assert evidence is not None
    if evidence.source_anchors:
        anchor = retrieval.read_source_anchor(
            WorldGraphSourceAnchorReadRequest(
                schema="dmb_world_graph_source_anchor_read_request_v1",
                anchorId=evidence.source_anchors[0].anchor_id,
                **ctx,
            ),
            repo_root=Path("/nonexistent-d3a-witness-repo"),
        )
        assert anchor.outcome in {"enough", "partial", "unavailable"}
    _assert_no_forbidden_loaded()


def _exercise_source_admission() -> None:
    from apps.live_control_server.integrations.dungeonmind.world_graph_source_admission_adapter import (
        DungeonMindWorldGraphSourceAdmissionAdapter,
    )
    from apps.live_control_server.ports.world_graph_source_admission import (
        WorldGraphSourceAdmissionRequest,
    )
    from dungeonmind.infrastructure.memory.repositories import InMemorySourceRepository

    token = "sha256:" + ("ab" * 32)
    artifact = SimpleNamespace(
        source_artifact_id="artifact:worldbuilding:a",
        source_domain="worldbuilding",
        campaign_id=CAMPAIGN_ID,
        session_id=None,
        uri="object://artifact:worldbuilding:a",
        content_sha256="ab" * 32,
        artifact_kind="markdown",
        document_class="lore",
        authority_state="reviewed",
        visibility_state="internal",
        world_id=WORLD_ID,
        workspace_document_id=None,
        workspace_document_revision=None,
        lineage={},
        status="active",
        created_at=NOW,
        updated_at=NOW,
    )
    adapter = DungeonMindWorldGraphSourceAdmissionAdapter(
        sources=InMemorySourceRepository()
    )
    admitted = adapter.prove_or_admit(
        WorldGraphSourceAdmissionRequest(
            world_id=WORLD_ID,
            campaign_id=CAMPAIGN_ID,
            source_artifact=artifact,
            source_revision_token=token,
            source_uri="object://artifact:worldbuilding:a",
        )
    )
    assert admitted.source_artifact_id == artifact.source_artifact_id
    _assert_no_forbidden_loaded()


def _exercise_hermes_and_mounted_modules() -> None:
    from apps.live_control_server.services.hermes_graph_query import (
        HERMES_GRAPH_READ_TOOL_NAMES,
        classify_hermes_graph_result,
    )
    from apps.live_control_server.services import threat_publication_commits
    from apps.live_control_server.services import worldbuilding_graph_publication
    from apps.live_control_server.services import graph_object_authoring_prepare
    from apps.live_control_server.services import graph_object_authoring_commit

    assert "expand_graph_retrieval" in HERMES_GRAPH_READ_TOOL_NAMES
    assert classify_hermes_graph_result is not None
    assert threat_publication_commits is not None
    assert worldbuilding_graph_publication is not None
    assert graph_object_authoring_prepare is not None
    assert graph_object_authoring_commit is not None
    _assert_no_forbidden_loaded()


def run_witness() -> None:
    root = Path(os.environ["DMB_D3A_WITNESS_ROOT"])
    legacy = root / "graph_memory" / "worlds"
    assert not legacy.exists(), "legacy graph filesystem must be absent before boot"

    _assert_mounted_services_have_no_kernel_escape()

    from apps.live_control_server.main import create_app
    from fastapi.testclient import TestClient

    app = create_app()
    with TestClient(app) as client:
        assert client.get("/health").status_code == 200

        union = client.get("/api/live/graph-preview/union-supergraph/projection")
        assert union.status_code == 410
        assert union.json()["detail"]["code"] == "union_supergraph_preview_retired"
        boot = client.get("/api/live/world-graph-bootstrap/status")
        assert boot.status_code == 410
        merge = client.post(
            "/api/live/graph-authoring/merge-reconciliation/prepare", json={}
        )
        assert merge.status_code == 410

        # Retained graph-preview + Graph Review + native World Graph routes stay mounted.
        route_paths = {getattr(route, "path", "") for route in app.routes}
        for required in (
            "/api/live/graph-preview/gold-review/projection",
            "/api/live/graph-preview/recap",
            "/api/live/graph-authoring/prepare",
            "/api/live/graph-authoring/commit",
            "/api/live/world-graph/projection",
            "/api/live/world-graph/retrieval/search",
            "/api/live/world-graph/retrieval/object",
            "/api/live/world-graph/retrieval/neighborhood",
            "/api/live/world-graph/retrieval/evidence",
            "/api/live/world-graph/retrieval/source-anchor/read",
        ):
            assert required in route_paths, f"missing mounted route: {required}"

        gold = client.get(
            "/api/live/graph-preview/gold-review/projection",
            params={"campaign_id": "c", "session_id": "s"},
        )
        assert gold.status_code != 410
        prep = client.post("/api/live/graph-authoring/prepare", json={})
        assert prep.status_code != 404
        assert prep.status_code != 410
        commit = client.post("/api/live/graph-authoring/commit", json={})
        assert commit.status_code != 404
        assert commit.status_code != 410
        projection_route = client.post("/api/live/world-graph/projection", json={})
        assert projection_route.status_code not in {404, 410}
        search_route = client.post("/api/live/world-graph/retrieval/search", json={})
        assert search_route.status_code not in {404, 410}

        _exercise_projection_and_retrieval()
        _exercise_source_admission()
        from tests._cutover_d3a_blocker_safe_exec import (
            exercise_all_owning_workflows,
        )

        exercise_all_owning_workflows(client, root)

    assert not legacy.exists(), "legacy graph filesystem must remain absent after boot"
    _assert_no_forbidden_loaded()
    print("WITNESS_OK")


if __name__ == "__main__":
    run_witness()
