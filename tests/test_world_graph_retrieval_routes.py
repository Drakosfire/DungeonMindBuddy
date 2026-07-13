"""HTTP-boundary tests for PR010A world graph retrieval + source-anchor read."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

import graph_memory.kernel as kernel
from apps.live_control_server.main import create_app
from apps.live_control_server.services.world_graph_retrieval import (
    WorldGraphRetrievalServiceError,
    get_campaign_object,
    get_object_evidence,
    get_object_neighborhood,
    read_source_anchor,
    search_campaign_graph,
)
from graph_memory.contribution_bundles import load_contribution_bundle
from graph_memory.kernel.world_initialization import initialize_world_from_contributions
from graph_memory.kernel.world_initialization_models import (
    PLAN_SCHEMA,
    WorldInitializationApprovalAttestation,
    WorldInitializationContribution,
    WorldInitializationPlan,
)
from graph_memory.projection.world_projection import WorldGraphProjectionFocus
from graph_memory.retrieval.models import (
    WorldGraphEvidenceRequest,
    WorldGraphEvidenceTarget,
    WorldGraphNeighborhoodRequest,
    WorldGraphObjectRequest,
    WorldGraphRetrievalBounds,
    WorldGraphRetrievalErrorResponse,
    WorldGraphRetrievalResult,
    WorldGraphSearchRequest,
    WorldGraphSourceAnchorReadRequest,
    WorldGraphSourceAnchorReadResult,
)

RETRIEVAL_URL = "/api/live/world-graph/retrieval"
FIXTURE_PATH = Path("tests/fixtures/world_graph_retrieval/api-contract-v1.json")
WORLD_ID = "eldyrwild"
CAMPAIGN_ID = "longmont-c2"
FOCUS_SESSION_ID = "session-23"
BUNDLE_PATH = Path(
    "graph_data/approved_contribution_bundles/eldyrwild-longmont-c2-initial-v1"
)
BUNDLE_DIGEST = "c8eb7e6ca7e735c40822cb1e6835f9949f2cd915b57f5704e7b4daeb72cf2fca"
APPROVED_MERGE_SHA = "f69c69f271c427209860d902636347b70fea5920"
ORDERED_CONTRIBUTION_IDS = [
    "contribution:82f23934d8eaca8a",
    "contribution:43782369bd717d32",
    "contribution:33d7cdb0ff623f28",
    "contribution:c086a0b72324ff16",
    "contribution:1227841724520c18",
    "contribution:022187fdefdf4557",
]
TRIPOD_ID = "threat:tripod-null-calf"
MIRATHORN_ID = "location:mirathorn"
MIRATHORN_EVIDENCE_REF_ID = "evidence:corpus:worldbuilding:mirathorn"


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("DUNGEONMIND_WORLD_GRAPH_ROOT", str(tmp_path))
    return TestClient(create_app())


def _initialize(root: Path) -> None:
    bundle = load_contribution_bundle(BUNDLE_PATH)
    by_id = {item.contribution_id: item for item in bundle.contributions}
    plan = WorldInitializationPlan(
        schema=PLAN_SCHEMA,
        world_id=WORLD_ID,
        campaign_id=CAMPAIGN_ID,
        focus_session_id=FOCUS_SESSION_ID,
        ordered_contributions=[
            WorldInitializationContribution(
                contribution_id=contribution_id,
                payload_sha256=kernel.compute_contribution_payload_sha256(
                    by_id[contribution_id]
                ),
            )
            for contribution_id in ORDERED_CONTRIBUTION_IDS
        ],
        approval_attestation=WorldInitializationApprovalAttestation(
            bundle_id="eldyrwild-longmont-c2-initial-v1",
            bundle_digest=BUNDLE_DIGEST,
            approved_bundle_merge_sha=APPROVED_MERGE_SHA,
        ),
    )
    initialize_world_from_contributions(
        root,
        plan=plan,
        contributions=list(bundle.contributions),
        actor="gm",
    )


def _base_request(**overrides) -> dict:
    payload = {
        "worldId": WORLD_ID,
        "campaignId": CAMPAIGN_ID,
    }
    payload.update(overrides)
    return payload


# --- Contract shape / query params / malformed bodies -----------------------


@pytest.mark.parametrize(
    "route,schema_name",
    [
        ("/search", "dmb_world_graph_search_request_v1"),
        ("/object", "dmb_world_graph_object_request_v1"),
        ("/neighborhood", "dmb_world_graph_neighborhood_request_v1"),
        ("/evidence", "dmb_world_graph_evidence_request_v1"),
        ("/source-anchor/read", "dmb_world_graph_source_anchor_read_request_v1"),
    ],
)
def test_routes_reject_query_params(client: TestClient, route: str, schema_name: str) -> None:
    response = client.post(
        f"{RETRIEVAL_URL}{route}?worldId=foreign",
        json={"schema": schema_name, **_base_request()},
    )
    assert response.status_code == 422
    payload = response.json()
    assert payload["schema"] == "dmb_world_graph_retrieval_error_v1"
    assert payload["code"] == "invalid_request"


def test_search_route_rejects_forbidden_fields(client: TestClient) -> None:
    response = client.post(
        f"{RETRIEVAL_URL}/search",
        json={
            "schema": "dmb_world_graph_search_request_v1",
            **_base_request(queryText="anything"),
            "previewUnionStorePath": "/tmp/forbidden",
        },
    )
    assert response.status_code == 422
    assert response.json()["code"] == "invalid_request"


def test_source_anchor_read_route_rejects_path_field(client: TestClient) -> None:
    response = client.post(
        f"{RETRIEVAL_URL}/source-anchor/read",
        json={
            "schema": "dmb_world_graph_source_anchor_read_request_v1",
            **_base_request(anchorId="source-anchor:v1:" + "0" * 64),
            "path": "/etc/passwd",
        },
    )
    assert response.status_code == 422
    assert response.json()["code"] == "invalid_request"


def test_search_route_missing_required_field_is_422(client: TestClient) -> None:
    response = client.post(
        f"{RETRIEVAL_URL}/search",
        json={"schema": "dmb_world_graph_search_request_v1", **_base_request()},
    )
    assert response.status_code == 422
    assert response.json()["schema"] == "dmb_world_graph_retrieval_error_v1"


# --- Successful round-trips ---------------------------------------------------


def test_search_route_returns_camel_case_result_after_init(
    client: TestClient, tmp_path: Path
) -> None:
    _initialize(tmp_path)
    response = client.post(
        f"{RETRIEVAL_URL}/search",
        json={
            "schema": "dmb_world_graph_search_request_v1",
            **_base_request(queryText="positional controller"),
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["schema"] == "dmb_world_graph_retrieval_result_v1"
    assert payload["operation"] == "search"
    assert payload["matchedNodeIds"][0] == TRIPOD_ID
    assert payload["snapshot"]["worldId"] == WORLD_ID
    raw = json.dumps(payload)
    assert "revision_id" not in raw
    assert "matched_node_ids" not in raw


def test_object_route_returns_tripod(client: TestClient, tmp_path: Path) -> None:
    _initialize(tmp_path)
    response = client.post(
        f"{RETRIEVAL_URL}/object",
        json={"schema": "dmb_world_graph_object_request_v1", **_base_request(nodeId=TRIPOD_ID)},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["resolvedNodeId"] == TRIPOD_ID
    assert payload["nodes"][0]["nodeId"] == TRIPOD_ID


def test_neighborhood_route_returns_event(client: TestClient, tmp_path: Path) -> None:
    _initialize(tmp_path)
    response = client.post(
        f"{RETRIEVAL_URL}/neighborhood",
        json={
            "schema": "dmb_world_graph_neighborhood_request_v1",
            **_base_request(seedNodeIds=[TRIPOD_ID], maxDepth=1),
        },
    )
    assert response.status_code == 200
    payload = response.json()
    node_ids = {node["nodeId"] for node in payload["nodes"]}
    assert TRIPOD_ID in node_ids


def test_evidence_route_returns_opaque_anchors(client: TestClient, tmp_path: Path) -> None:
    _initialize(tmp_path)
    response = client.post(
        f"{RETRIEVAL_URL}/evidence",
        json={
            "schema": "dmb_world_graph_evidence_request_v1",
            **_base_request(target={"kind": "node", "id": TRIPOD_ID}),
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["sourceAnchors"]
    anchor = payload["sourceAnchors"][0]
    assert anchor["anchorId"].startswith("source-anchor:v1:")
    assert "uri" not in anchor
    assert "path" not in anchor


def test_source_anchor_read_route_round_trip(client: TestClient, tmp_path: Path) -> None:
    _initialize(tmp_path)
    evidence_response = client.post(
        f"{RETRIEVAL_URL}/evidence",
        json={
            "schema": "dmb_world_graph_evidence_request_v1",
            **_base_request(target={"kind": "node", "id": TRIPOD_ID}),
        },
    )
    anchor_id = evidence_response.json()["sourceAnchors"][0]["anchorId"]

    read_response = client.post(
        f"{RETRIEVAL_URL}/source-anchor/read",
        json={
            "schema": "dmb_world_graph_source_anchor_read_request_v1",
            **_base_request(anchorId=anchor_id),
        },
    )
    assert read_response.status_code == 200
    payload = read_response.json()
    assert payload["schema"] == "dmb_world_graph_source_anchor_read_v1"
    assert payload["outcome"] in ("enough", "truncated")
    assert payload["content"]


# --- Unavailable vs integrity distinctions -----------------------------------


def test_search_route_returns_200_unavailable_for_uninitialized_world(
    client: TestClient,
) -> None:
    response = client.post(
        f"{RETRIEVAL_URL}/search",
        json={"schema": "dmb_world_graph_search_request_v1", **_base_request(queryText="x")},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["outcome"] == "unavailable"
    assert payload["snapshot"] is None


def test_search_route_returns_409_for_campaign_mismatch(
    client: TestClient, tmp_path: Path
) -> None:
    _initialize(tmp_path)
    response = client.post(
        f"{RETRIEVAL_URL}/search",
        json={
            "schema": "dmb_world_graph_search_request_v1",
            **_base_request(queryText="x", campaignId="foreign-campaign"),
        },
    )
    assert response.status_code == 409
    payload = response.json()
    assert payload["schema"] == "dmb_world_graph_retrieval_error_v1"


def test_search_route_returns_422_for_unsupported_admissibility(
    client: TestClient, tmp_path: Path
) -> None:
    _initialize(tmp_path)
    response = client.post(
        f"{RETRIEVAL_URL}/search",
        json={
            "schema": "dmb_world_graph_search_request_v1",
            **_base_request(queryText="x", admissibility="player"),
        },
    )
    assert response.status_code == 422


def test_source_anchor_read_route_returns_200_unavailable_for_uninitialized_world(
    client: TestClient,
) -> None:
    response = client.post(
        f"{RETRIEVAL_URL}/source-anchor/read",
        json={
            "schema": "dmb_world_graph_source_anchor_read_request_v1",
            **_base_request(anchorId="source-anchor:v1:" + "0" * 64),
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["outcome"] == "unavailable"


# --- API contract fixture: generated from real temporary-root operations ----


def _context(**overrides) -> dict[str, Any]:
    payload = {
        "world_id": WORLD_ID,
        "campaign_id": CAMPAIGN_ID,
        "focus": WorldGraphProjectionFocus(),
        "admissibility": "gm",
        "revision_pin": None,
    }
    payload.update(overrides)
    return payload


def _dump(model) -> dict[str, Any]:
    return model.model_dump(mode="json", by_alias=True)


def build_retrieval_api_contract(root: Path) -> dict[str, Any]:
    """Build the PR010A retrieval API contract from real service calls.

    Every example is a genuine response captured from a temporary,
    bootstrapped world graph (or a genuinely uninitialized one for the
    ``*Unavailable`` cases) -- never a hand-written approximation.
    """
    _initialize(root)

    search_enough = search_campaign_graph(
        WorldGraphSearchRequest(query_text="positional controller", **_context()), root=root
    )
    search_empty = search_campaign_graph(
        WorldGraphSearchRequest(
            query_text="completely unrelated phrase not present in the graph",
            **_context(),
        ),
        root=root,
    )
    object_found = get_campaign_object(
        WorldGraphObjectRequest(node_id=TRIPOD_ID, **_context()), root=root
    )
    object_empty = get_campaign_object(
        WorldGraphObjectRequest(node_id="threat:does-not-exist", **_context()), root=root
    )
    neighborhood_depth_1 = get_object_neighborhood(
        WorldGraphNeighborhoodRequest(seed_node_ids=[TRIPOD_ID], max_depth=1, **_context()),
        root=root,
    )
    neighborhood_partial = get_object_neighborhood(
        WorldGraphNeighborhoodRequest(
            seed_node_ids=[TRIPOD_ID, "threat:does-not-exist"],
            max_depth=1,
            **_context(),
        ),
        root=root,
    )
    neighborhood_truncated = get_object_neighborhood(
        WorldGraphNeighborhoodRequest(
            seed_node_ids=[TRIPOD_ID],
            max_depth=2,
            bounds=WorldGraphRetrievalBounds(max_nodes=1),
            **_context(),
        ),
        root=root,
    )
    evidence_for_node = get_object_evidence(
        WorldGraphEvidenceRequest(
            target=WorldGraphEvidenceTarget(kind="node", id=TRIPOD_ID), **_context()
        ),
        root=root,
    )
    anchor_id = evidence_for_node.source_anchors[0].anchor_id
    source_anchor_read = read_source_anchor(
        WorldGraphSourceAnchorReadRequest(anchor_id=anchor_id, **_context()), root=root
    )
    source_anchor_read_unknown = read_source_anchor(
        WorldGraphSourceAnchorReadRequest(
            anchor_id="source-anchor:v1:" + "0" * 64, **_context()
        ),
        root=root,
    )

    evidence_for_mirathorn = get_object_evidence(
        WorldGraphEvidenceRequest(
            target=WorldGraphEvidenceTarget(kind="node", id=MIRATHORN_ID), **_context()
        ),
        root=root,
    )
    mirathorn_anchor_id = next(
        anchor.anchor_id
        for anchor in evidence_for_mirathorn.source_anchors
        if anchor.evidence_ref_id == MIRATHORN_EVIDENCE_REF_ID
    )
    try:
        read_source_anchor(
            WorldGraphSourceAnchorReadRequest(anchor_id=mirathorn_anchor_id, **_context()),
            root=root,
        )
        source_anchor_read_integrity_error: WorldGraphRetrievalServiceError | None = None
    except WorldGraphRetrievalServiceError as exc:
        source_anchor_read_integrity_error = exc

    empty_root = root / "uninitialized"
    search_unavailable = search_campaign_graph(
        WorldGraphSearchRequest(query_text="anything", **_context()), root=empty_root
    )

    try:
        search_campaign_graph(
            WorldGraphSearchRequest(
                query_text="anything", **_context(campaign_id="foreign-campaign")
            ),
            root=root,
        )
        campaign_mismatch_error: WorldGraphRetrievalServiceError | None = None
    except WorldGraphRetrievalServiceError as exc:
        campaign_mismatch_error = exc

    try:
        search_campaign_graph(
            WorldGraphSearchRequest(query_text="anything", **_context(admissibility="player")),
            root=root,
        )
        invalid_admissibility_error: WorldGraphRetrievalServiceError | None = None
    except WorldGraphRetrievalServiceError as exc:
        invalid_admissibility_error = exc

    assert campaign_mismatch_error is not None
    assert invalid_admissibility_error is not None
    assert source_anchor_read_integrity_error is not None

    examples = {
        "searchEnough": _dump(search_enough),
        "searchEmpty": _dump(search_empty),
        "searchUnavailable": _dump(search_unavailable),
        "objectFound": _dump(object_found),
        "objectEmpty": _dump(object_empty),
        "neighborhoodDepth1": _dump(neighborhood_depth_1),
        "neighborhoodPartial": _dump(neighborhood_partial),
        "neighborhoodTruncated": _dump(neighborhood_truncated),
        "evidenceForNode": _dump(evidence_for_node),
        "sourceAnchorRead": _dump(source_anchor_read),
        "sourceAnchorReadUnknown": _dump(source_anchor_read_unknown),
        "sourceAnchorReadIntegrityError": _dump(
            source_anchor_read_integrity_error.response()
        ),
        "campaignMismatchError": _dump(campaign_mismatch_error.response()),
        "invalidAdmissibilityError": _dump(invalid_admissibility_error.response()),
    }
    schemas = {
        "searchRequest": WorldGraphSearchRequest.model_json_schema(by_alias=True),
        "objectRequest": WorldGraphObjectRequest.model_json_schema(by_alias=True),
        "neighborhoodRequest": WorldGraphNeighborhoodRequest.model_json_schema(by_alias=True),
        "evidenceRequest": WorldGraphEvidenceRequest.model_json_schema(by_alias=True),
        "sourceAnchorReadRequest": WorldGraphSourceAnchorReadRequest.model_json_schema(
            by_alias=True
        ),
        "retrievalResult": WorldGraphRetrievalResult.model_json_schema(by_alias=True),
        "sourceAnchorReadResult": WorldGraphSourceAnchorReadResult.model_json_schema(
            by_alias=True
        ),
        "errorResponse": WorldGraphRetrievalErrorResponse.model_json_schema(by_alias=True),
    }
    return {
        "version": "1.0",
        "schemas": schemas,
        "examples": examples,
    }


def test_api_contract_fixture_matches_real_generated_operations(tmp_path: Path) -> None:
    generated = build_retrieval_api_contract(tmp_path)
    fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    assert fixture == generated
