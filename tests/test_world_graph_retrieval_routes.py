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
from graph_memory.retrieval.models import (
    RETRIEVAL_EVIDENCE_REQUEST_SCHEMA,
    RETRIEVAL_NEIGHBORHOOD_REQUEST_SCHEMA,
    RETRIEVAL_OBJECT_REQUEST_SCHEMA,
    RETRIEVAL_SEARCH_REQUEST_SCHEMA,
    RETRIEVAL_SOURCE_ANCHOR_READ_REQUEST_SCHEMA,
    WorldGraphEvidenceRequest,
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
BUNDLE_DIGEST = "5f8288d3052a9e59192884f2c35a13d51f665095d84cca2081a56638108d3fa5"
APPROVED_MERGE_SHA = "65ae001e0852d827ecd680200a965a576c705b1d"
ORDERED_CONTRIBUTION_IDS = [
    "contribution:82f23934d8eaca8a",
    "contribution:43782369bd717d32",
    "contribution:33d7cdb0ff623f28",
    "contribution:c086a0b72324ff16",
    "contribution:1227841724520c18",
    "contribution:022187fdefdf4557",
]
TRIPOD_ID = "threat:tripod-null-calf"
TRIPOD_CONTRIBUTION_ID = "contribution:022187fdefdf4557"
TRIPOD_NODE_EVIDENCE_REF_ID = "evidence:bundle:v1:statblock:tripod-null-calf"
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


def test_search_route_rejects_snake_case_wire_keys(client: TestClient) -> None:
    response = client.post(
        f"{RETRIEVAL_URL}/search",
        json={
            "schema": "dmb_world_graph_search_request_v1",
            "world_id": WORLD_ID,
            "campaign_id": CAMPAIGN_ID,
            "query_text": "anything",
        },
    )
    assert response.status_code == 422
    assert response.json()["code"] == "invalid_request"


def test_search_route_rejects_schema_underscore_key(client: TestClient) -> None:
    response = client.post(
        f"{RETRIEVAL_URL}/search",
        json={
            "schema_": "dmb_world_graph_search_request_v1",
            **_base_request(queryText="anything"),
        },
    )
    assert response.status_code == 422
    assert response.json()["code"] == "invalid_request"


def test_search_route_rejects_omitted_schema(client: TestClient) -> None:
    response = client.post(
        f"{RETRIEVAL_URL}/search",
        json=_base_request(queryText="anything"),
    )
    assert response.status_code == 422
    assert response.json()["code"] == "invalid_request"


def test_search_route_rejects_nested_session_id_snake_case(client: TestClient) -> None:
    response = client.post(
        f"{RETRIEVAL_URL}/search",
        json={
            "schema": "dmb_world_graph_search_request_v1",
            **_base_request(queryText="anything"),
            "focus": {"kind": "session", "session_id": FOCUS_SESSION_ID},
        },
    )
    assert response.status_code == 422
    assert response.json()["code"] == "invalid_request"


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


def test_search_route_foreign_campaign_excludes_c2_scoped_matches(
    client: TestClient, tmp_path: Path
) -> None:
    """Model B: a non-matching campaign is a visibility lens, not a 409."""
    _initialize(tmp_path)
    response = client.post(
        f"{RETRIEVAL_URL}/search",
        json={
            "schema": "dmb_world_graph_search_request_v1",
            **_base_request(
                queryText="positional controller", campaignId="longmont-c1"
            ),
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["schema"] == "dmb_world_graph_retrieval_result_v1"
    assert payload["snapshot"]["campaignId"] == "longmont-c1"
    assert TRIPOD_ID not in payload["matchedNodeIds"]


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


def test_source_anchor_read_route_contribution_drift_returns_409_envelope(
    client: TestClient, tmp_path: Path
) -> None:
    _initialize(tmp_path)
    evidence_response = client.post(
        f"{RETRIEVAL_URL}/evidence",
        json={
            "schema": "dmb_world_graph_evidence_request_v1",
            **_base_request(target={"kind": "node", "id": TRIPOD_ID}),
        },
    )
    assert evidence_response.status_code == 200
    anchors = evidence_response.json()["sourceAnchors"]
    anchor_id = next(
        anchor["anchorId"]
        for anchor in anchors
        if anchor["evidenceRefId"] == TRIPOD_NODE_EVIDENCE_REF_ID
    )

    ledger_path = (
        tmp_path
        / "graph_memory"
        / "worlds"
        / WORLD_ID
        / "contributions"
        / "contribution__022187fdefdf4557.json"
    )
    ledger_payload = json.loads(ledger_path.read_text(encoding="utf-8"))
    ledger_payload["source_revision_id"] = "tampered-pr010a"
    ledger_path.write_text(
        json.dumps(ledger_payload, indent=2, sort_keys=True, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )

    read_response = client.post(
        f"{RETRIEVAL_URL}/source-anchor/read",
        json={
            "schema": "dmb_world_graph_source_anchor_read_request_v1",
            **_base_request(anchorId=anchor_id),
        },
    )
    assert read_response.status_code == 409
    payload = read_response.json()
    assert payload["schema"] == "dmb_world_graph_retrieval_error_v1"
    assert payload["code"] == "source_integrity_error"
    assert "content" not in payload


def test_source_anchor_read_route_mirathorn_heading_exact_match(
    client: TestClient, tmp_path: Path
) -> None:
    _initialize(tmp_path)
    evidence_response = client.post(
        f"{RETRIEVAL_URL}/evidence",
        json={
            "schema": "dmb_world_graph_evidence_request_v1",
            **_base_request(target={"kind": "node", "id": MIRATHORN_ID}),
        },
    )
    assert evidence_response.status_code == 200
    anchors = evidence_response.json()["sourceAnchors"]
    anchor_id = next(
        anchor["anchorId"]
        for anchor in anchors
        if anchor["evidenceRefId"] == MIRATHORN_EVIDENCE_REF_ID
    )

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
    assert payload["outcome"] == "enough"
    assert payload["mediaType"] == "text/markdown"
    assert "Mirathorn Overview" in payload["content"]
    assert payload["contentSha256"]
    assert "code" not in payload

def test_source_anchor_read_route_malformed_receipt_returns_409_envelope(
    client: TestClient, tmp_path: Path
) -> None:
    _initialize(tmp_path)
    evidence_response = client.post(
        f"{RETRIEVAL_URL}/evidence",
        json={
            "schema": "dmb_world_graph_evidence_request_v1",
            **_base_request(target={"kind": "node", "id": TRIPOD_ID}),
        },
    )
    assert evidence_response.status_code == 200
    anchors = evidence_response.json()["sourceAnchors"]
    anchor_id = next(
        anchor["anchorId"]
        for anchor in anchors
        if anchor["evidenceRefId"] == TRIPOD_NODE_EVIDENCE_REF_ID
    )

    receipt_path = (
        tmp_path / "graph_memory" / "worlds" / WORLD_ID / "initialization" / "initial.json"
    )
    receipt_path.write_text("{not-valid-json", encoding="utf-8")

    read_response = client.post(
        f"{RETRIEVAL_URL}/source-anchor/read",
        json={
            "schema": "dmb_world_graph_source_anchor_read_request_v1",
            **_base_request(anchorId=anchor_id),
        },
    )
    assert read_response.status_code == 409
    payload = read_response.json()
    assert payload["schema"] == "dmb_world_graph_retrieval_error_v1"
    assert payload["code"] == "source_integrity_error"


def test_source_anchor_read_route_receipt_plan_digest_mutation_returns_409(
    client: TestClient, tmp_path: Path
) -> None:
    _initialize(tmp_path)
    evidence_response = client.post(
        f"{RETRIEVAL_URL}/evidence",
        json={
            "schema": "dmb_world_graph_evidence_request_v1",
            **_base_request(target={"kind": "node", "id": TRIPOD_ID}),
        },
    )
    assert evidence_response.status_code == 200
    anchors = evidence_response.json()["sourceAnchors"]
    anchor_id = next(
        anchor["anchorId"]
        for anchor in anchors
        if anchor["evidenceRefId"] == TRIPOD_NODE_EVIDENCE_REF_ID
    )

    receipt_path = (
        tmp_path / "graph_memory" / "worlds" / WORLD_ID / "initialization" / "initial.json"
    )
    receipt_payload = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt_payload["plan_digest"] = "deadbeef" * 8
    receipt_path.write_text(
        json.dumps(receipt_payload, indent=2, sort_keys=True, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )

    read_response = client.post(
        f"{RETRIEVAL_URL}/source-anchor/read",
        json={
            "schema": "dmb_world_graph_source_anchor_read_request_v1",
            **_base_request(anchorId=anchor_id),
        },
    )
    assert read_response.status_code == 409
    assert read_response.json()["code"] == "source_integrity_error"


# --- API contract fixture: generated from real temporary-root operations ----


def _context(**overrides) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "worldId": WORLD_ID,
        "campaignId": CAMPAIGN_ID,
        "focus": {"kind": "none", "sessionId": None},
        "admissibility": "gm",
        "revisionPin": None,
    }
    alias_map = {
        "world_id": "worldId",
        "campaign_id": "campaignId",
        "revision_pin": "revisionPin",
        "admissibility": "admissibility",
        "focus": "focus",
    }
    for key, value in overrides.items():
        wire_key = alias_map.get(key, key)
        if hasattr(value, "model_dump"):
            payload[wire_key] = value.model_dump(mode="json", by_alias=True)
        else:
            payload[wire_key] = value
    return payload


def _dump(model) -> dict[str, Any]:
    return model.model_dump(mode="json", by_alias=True)


def _bounds(**overrides) -> WorldGraphRetrievalBounds:
    payload = {
        "maxNodes": 8,
        "maxRelationships": 16,
        "maxAttributes": 24,
        "maxSourceAnchors": 24,
        **{
            {
                "max_nodes": "maxNodes",
                "max_relationships": "maxRelationships",
                "max_attributes": "maxAttributes",
                "max_source_anchors": "maxSourceAnchors",
            }.get(key, key): value
            for key, value in overrides.items()
        },
    }
    return WorldGraphRetrievalBounds.model_validate(payload)


def build_retrieval_api_contract(root: Path) -> dict[str, Any]:
    """Build the PR010A retrieval API contract from real service calls.

    Every example is a genuine response captured from a temporary,
    bootstrapped world graph (or a genuinely uninitialized one for the
    ``*Unavailable`` cases) -- never a hand-written approximation.
    """
    _initialize(root)

    search_enough = search_campaign_graph(
        WorldGraphSearchRequest.model_validate(
            {
                "schema": RETRIEVAL_SEARCH_REQUEST_SCHEMA,
                "queryText": "positional controller",
                **_context(),
            }
        ),
        root=root,
    )
    search_empty = search_campaign_graph(
        WorldGraphSearchRequest.model_validate(
            {
                "schema": RETRIEVAL_SEARCH_REQUEST_SCHEMA,
                "queryText": "completely unrelated phrase not present in the graph",
                **_context(),
            }
        ),
        root=root,
    )
    object_found = get_campaign_object(
        WorldGraphObjectRequest.model_validate(
            {
                "schema": RETRIEVAL_OBJECT_REQUEST_SCHEMA,
                "nodeId": TRIPOD_ID,
                **_context(),
            }
        ),
        root=root,
    )
    object_empty = get_campaign_object(
        WorldGraphObjectRequest.model_validate(
            {
                "schema": RETRIEVAL_OBJECT_REQUEST_SCHEMA,
                "nodeId": "threat:does-not-exist",
                **_context(),
            }
        ),
        root=root,
    )
    neighborhood_depth_1 = get_object_neighborhood(
        WorldGraphNeighborhoodRequest.model_validate(
            {
                "schema": RETRIEVAL_NEIGHBORHOOD_REQUEST_SCHEMA,
                "seedNodeIds": [TRIPOD_ID],
                "maxDepth": 1,
                **_context(),
            }
        ),
        root=root,
    )
    neighborhood_partial = get_object_neighborhood(
        WorldGraphNeighborhoodRequest.model_validate(
            {
                "schema": RETRIEVAL_NEIGHBORHOOD_REQUEST_SCHEMA,
                "seedNodeIds": [TRIPOD_ID, "threat:does-not-exist"],
                "maxDepth": 1,
                **_context(),
            }
        ),
        root=root,
    )
    neighborhood_truncated = get_object_neighborhood(
        WorldGraphNeighborhoodRequest.model_validate(
            {
                "schema": RETRIEVAL_NEIGHBORHOOD_REQUEST_SCHEMA,
                "seedNodeIds": [TRIPOD_ID],
                "maxDepth": 2,
                "bounds": _bounds(max_nodes=1).model_dump(mode="json", by_alias=True),
                **_context(),
            }
        ),
        root=root,
    )
    evidence_for_node = get_object_evidence(
        WorldGraphEvidenceRequest.model_validate(
            {
                "schema": RETRIEVAL_EVIDENCE_REQUEST_SCHEMA,
                "target": {"kind": "node", "id": TRIPOD_ID},
                **_context(),
            }
        ),
        root=root,
    )
    anchor_id = evidence_for_node.source_anchors[0].anchor_id
    source_anchor_read = read_source_anchor(
        WorldGraphSourceAnchorReadRequest.model_validate(
            {
                "schema": RETRIEVAL_SOURCE_ANCHOR_READ_REQUEST_SCHEMA,
                "anchorId": anchor_id,
                **_context(),
            }
        ),
        root=root,
    )
    source_anchor_read_unknown = read_source_anchor(
        WorldGraphSourceAnchorReadRequest.model_validate(
            {
                "schema": RETRIEVAL_SOURCE_ANCHOR_READ_REQUEST_SCHEMA,
                "anchorId": "source-anchor:v1:" + "0" * 64,
                **_context(),
            }
        ),
        root=root,
    )

    evidence_for_mirathorn = get_object_evidence(
        WorldGraphEvidenceRequest.model_validate(
            {
                "schema": RETRIEVAL_EVIDENCE_REQUEST_SCHEMA,
                "target": {"kind": "node", "id": MIRATHORN_ID},
                **_context(),
            }
        ),
        root=root,
    )
    mirathorn_anchor_id = next(
        anchor.anchor_id
        for anchor in evidence_for_mirathorn.source_anchors
        if anchor.evidence_ref_id == MIRATHORN_EVIDENCE_REF_ID
    )
    source_anchor_read_repo_heading = read_source_anchor(
        WorldGraphSourceAnchorReadRequest.model_validate(
            {
                "schema": RETRIEVAL_SOURCE_ANCHOR_READ_REQUEST_SCHEMA,
                "anchorId": mirathorn_anchor_id,
                **_context(),
            }
        ),
        root=root,
    )

    receipt_path = root / "graph_memory" / "worlds" / WORLD_ID / "initialization" / "initial.json"
    receipt_payload = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt_payload["plan_digest"] = "deadbeef" * 8
    receipt_path.write_text(
        json.dumps(receipt_payload, indent=2, sort_keys=True, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
    try:
        read_source_anchor(
            WorldGraphSourceAnchorReadRequest.model_validate(
                {
                    "schema": RETRIEVAL_SOURCE_ANCHOR_READ_REQUEST_SCHEMA,
                    "anchorId": anchor_id,
                    **_context(),
                }
            ),
            root=root,
        )
        source_anchor_read_integrity_error: WorldGraphRetrievalServiceError | None = None
    except WorldGraphRetrievalServiceError as exc:
        source_anchor_read_integrity_error = exc

    empty_root = root / "uninitialized"
    search_unavailable = search_campaign_graph(
        WorldGraphSearchRequest.model_validate(
            {
                "schema": RETRIEVAL_SEARCH_REQUEST_SCHEMA,
                "queryText": "anything",
                **_context(),
            }
        ),
        root=empty_root,
    )

    search_foreign_campaign = search_campaign_graph(
        WorldGraphSearchRequest.model_validate(
            {
                "schema": RETRIEVAL_SEARCH_REQUEST_SCHEMA,
                "queryText": "positional controller",
                **_context(campaign_id="longmont-c1"),
            }
        ),
        root=root,
    )
    assert search_foreign_campaign.snapshot is not None
    assert search_foreign_campaign.snapshot.campaign_id == "longmont-c1"
    assert TRIPOD_ID not in search_foreign_campaign.matched_node_ids

    try:
        search_campaign_graph(
            WorldGraphSearchRequest.model_validate(
                {
                    "schema": RETRIEVAL_SEARCH_REQUEST_SCHEMA,
                    "queryText": "anything",
                    **_context(admissibility="player"),
                }
            ),
            root=root,
        )
        invalid_admissibility_error: WorldGraphRetrievalServiceError | None = None
    except WorldGraphRetrievalServiceError as exc:
        invalid_admissibility_error = exc

    assert invalid_admissibility_error is not None
    assert source_anchor_read_integrity_error is not None

    examples = {
        "searchEnough": _dump(search_enough),
        "searchEmpty": _dump(search_empty),
        "searchForeignCampaign": _dump(search_foreign_campaign),
        "searchUnavailable": _dump(search_unavailable),
        "objectFound": _dump(object_found),
        "objectEmpty": _dump(object_empty),
        "neighborhoodDepth1": _dump(neighborhood_depth_1),
        "neighborhoodPartial": _dump(neighborhood_partial),
        "neighborhoodTruncated": _dump(neighborhood_truncated),
        "evidenceForNode": _dump(evidence_for_node),
        "sourceAnchorRead": _dump(source_anchor_read),
        "sourceAnchorReadRepoHeading": _dump(source_anchor_read_repo_heading),
        "sourceAnchorReadUnknown": _dump(source_anchor_read_unknown),
        "sourceAnchorReadIntegrityError": _dump(
            source_anchor_read_integrity_error.response()
        ),
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


# --- CUTOVER R.3: mounted direct DungeonMind read path ----------------------
#
# In ``dungeonmind`` authority mode the HTTP routes dispatch to the direct
# DungeonMind read adapter. These tests mount the app against in-memory
# DungeonMind repositories and prove the legacy kernel/hydration machinery is
# never invoked (explosion stubs).


@pytest.fixture
def direct_services():
    from tests.test_cutover_direct_dungeonmind_world_graph_reads import (
        NOW,
        _FakeBundle,
        _payload,
        _receipt,
        _seed_sources,
    )
    from tests.test_cutover_direct_dungeonmind_world_graph_reads import (
        WORLD_ID as DIRECT_WORLD_ID,
    )

    from dungeonmind.contracts.graph import PublishRevisionCommand
    from dungeonmind.infrastructure.memory import InMemoryWorldGraphRepository

    world_graph = InMemoryWorldGraphRepository()
    published = world_graph.publish_revision(
        PublishRevisionCommand(
            world_id=DIRECT_WORLD_ID,
            parent_revision_id=None,
            expected_parent_revision_id=None,
            operation_ids=["op:mounted-r3"],
            graph_schema="dm_union_graph_v6",
            graph_payload=_payload(),
            created_at=NOW,
        )
    )
    bundle = _FakeBundle(
        world_graph,
        _seed_sources(),
        _receipt(DIRECT_WORLD_ID, published.revision_id),
    )
    from apps.live_control_server.integrations.dungeonmind import (
        world_graph_reads as direct,
    )

    return direct.direct_services_from_bundle(bundle, DIRECT_WORLD_ID)


@pytest.fixture
def direct_client(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, direct_services
) -> TestClient:
    from graph_memory.world_supergraph import storage

    monkeypatch.setenv(
        storage.WORLD_GRAPH_AUTHORITY_ENV, storage.WORLD_GRAPH_AUTHORITY_DUNGEONMIND
    )
    monkeypatch.setenv(
        "DUNGEONMIND_WORLD_GRAPH_AUTHORITY_DATABASE_URL", "postgresql://unused"
    )
    monkeypatch.setenv("DUNGEONMIND_WORLD_GRAPH_ROOT", str(tmp_path / "graph-root"))
    storage.clear_world_graph_cache_roots()

    from apps.live_control_server.integrations.dungeonmind import (
        world_graph_reads as direct,
    )

    monkeypatch.setattr(
        direct, "direct_services_from_config", lambda world_id: direct_services
    )

    def _explode(*_args, **_kwargs):
        raise AssertionError("legacy kernel must not run on the direct read path")

    monkeypatch.setattr(kernel, "search_campaign_graph", _explode)
    monkeypatch.setattr(kernel, "get_campaign_object", _explode)
    monkeypatch.setattr(kernel, "get_object_neighborhood", _explode)
    monkeypatch.setattr(kernel, "get_object_evidence", _explode)
    monkeypatch.setattr(kernel, "resolve_admitted_anchor_match", _explode)
    return TestClient(create_app())


def _direct_base_request(**overrides) -> dict:
    from tests.test_cutover_direct_dungeonmind_world_graph_reads import (
        CAMPAIGN_ONE,
    )
    from tests.test_cutover_direct_dungeonmind_world_graph_reads import (
        WORLD_ID as DIRECT_WORLD_ID,
    )

    payload = {"worldId": DIRECT_WORLD_ID, "campaignId": CAMPAIGN_ONE}
    payload.update(overrides)
    return payload


def test_direct_search_route_returns_200_with_results(direct_client: TestClient) -> None:
    response = direct_client.post(
        f"{RETRIEVAL_URL}/search",
        json={
            "schema": RETRIEVAL_SEARCH_REQUEST_SCHEMA,
            **_direct_base_request(queryText="tavern"),
        },
    )
    assert response.status_code == 200
    body = response.json()
    labels = [node["label"] for node in body["nodes"]]
    assert "The Prancing Tavern" in labels


def test_direct_object_route_returns_200(direct_client: TestClient) -> None:
    response = direct_client.post(
        f"{RETRIEVAL_URL}/object",
        json={
            "schema": RETRIEVAL_OBJECT_REQUEST_SCHEMA,
            **_direct_base_request(nodeId="obj:tavern"),
        },
    )
    assert response.status_code == 200
    assert [n["nodeId"] for n in response.json()["nodes"]] == ["obj:tavern"]


def test_direct_unknown_revision_pin_is_404_envelope(direct_client: TestClient) -> None:
    response = direct_client.post(
        f"{RETRIEVAL_URL}/search",
        json={
            "schema": RETRIEVAL_SEARCH_REQUEST_SCHEMA,
            **_direct_base_request(queryText="tavern", revisionPin="rev:never-existed"),
        },
    )
    assert response.status_code == 404
    payload = response.json()
    assert payload["schema"] == "dmb_world_graph_retrieval_error_v1"
    assert payload["code"] == "revision_not_bridged"


def test_direct_non_gm_admissibility_is_422_envelope(direct_client: TestClient) -> None:
    response = direct_client.post(
        f"{RETRIEVAL_URL}/search",
        json={
            "schema": RETRIEVAL_SEARCH_REQUEST_SCHEMA,
            **_direct_base_request(queryText="tavern", admissibility="player"),
        },
    )
    assert response.status_code == 422
    assert response.json()["code"] == "unsupported_admissibility"


def test_direct_anchor_read_route_revalidates(direct_client: TestClient) -> None:
    evidence = direct_client.post(
        f"{RETRIEVAL_URL}/evidence",
        json={
            "schema": RETRIEVAL_EVIDENCE_REQUEST_SCHEMA,
            **_direct_base_request(target={"kind": "node", "id": "obj:tavern"}),
        },
    )
    assert evidence.status_code == 200
    anchors = evidence.json()["sourceAnchors"]
    assert anchors
    response = direct_client.post(
        f"{RETRIEVAL_URL}/source-anchor/read",
        json={
            "schema": RETRIEVAL_SOURCE_ANCHOR_READ_REQUEST_SCHEMA,
            **_direct_base_request(anchorId=anchors[0]["anchorId"]),
        },
    )
    assert response.status_code == 200
    # The anchor revalidates against DungeonMind authority; the product-local
    # content join degrades because no repo files exist in this fixture.
    assert response.json()["outcome"] in {"enough", "partial", "unavailable"}
