"""World Graph recap projection — pure helpers + service + HTTP boundary (PR380A)."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

import graph_memory.kernel as kernel
from apps.live_control_server.main import create_app
from apps.live_control_server.services.world_graph_projection import (
    WorldGraphProjectionServiceError,
)
from apps.live_control_server.services.world_graph_recap_projection import (
    build_world_graph_recap_projection,
    build_world_graph_recap_projection_payload,
)
from graph_memory.contribution_bundles import load_contribution_bundle
from graph_memory.kernel.world_initialization import initialize_world_from_contributions
from graph_memory.kernel.world_initialization_models import (
    PLAN_SCHEMA,
    WorldInitializationApprovalAttestation,
    WorldInitializationContribution,
    WorldInitializationPlan,
)
from graph_memory.projection.world_projection import (
    WorldGraphProjectionNodeView,
    WorldGraphProjectionRequest,
)
from graph_memory.projection.world_recap_projection import (
    AMBIGUOUS_MENTION_DIAGNOSTIC,
    RECAP_PROJECTION_RESPONSE_SCHEMA,
    adapt_world_node_to_recap_view,
    project_world_markdown_mentions,
)

RECAP_PROJECTION_URL = "/api/live/world-graph/recap-projection"
WORLD_ID = "eldyrwild"
CAMPAIGN_ID = "longmont-c2"
FOCUS_SESSION_ID = "session-23"
BUNDLE_PATH = Path(
    "graph_data/approved_contribution_bundles/eldyrwild-longmont-c2-initial-v1"
)
BUNDLE_DIGEST = (
    "5f8288d3052a9e59192884f2c35a13d51f665095d84cca2081a56638108d3fa5"
)
APPROVED_MERGE_SHA = "65ae001e0852d827ecd680200a965a576c705b1d"
ORDERED_CONTRIBUTION_IDS = [
    "contribution:82f23934d8eaca8a",
    "contribution:43782369bd717d32",
    "contribution:33d7cdb0ff623f28",
    "contribution:c086a0b72324ff16",
    "contribution:1227841724520c18",
    "contribution:022187fdefdf4557",
]


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


def _session_request(
    session_id: str = FOCUS_SESSION_ID,
    **overrides: Any,
) -> WorldGraphProjectionRequest:
    payload = {
        "schema": "dmb_world_graph_projection_request_v1",
        "world_id": WORLD_ID,
        "campaign_id": CAMPAIGN_ID,
        "focus": {
            "kind": "session",
            "session_id": session_id,
            "campaign_id": CAMPAIGN_ID,
        },
        "admissibility": "gm",
        "scope_mode": "campaign",
    }
    payload.update(overrides)
    return WorldGraphProjectionRequest.model_validate(payload)


def test_project_world_markdown_mentions_uses_durable_node_ids() -> None:
    nodes = [
        WorldGraphProjectionNodeView(
            node_id="pc:caelynn",
            label="Caelynn",
            kind="pc",
            role="character",
            aliases=["Caelynn Leafwhisper"],
            evidence_ref_ids=["ev:1"],
        ),
        WorldGraphProjectionNodeView(
            node_id="location:mireward",
            label="Mireward Reach",
            kind="location",
            role="place",
            aliases=["Mireward"],
            evidence_ref_ids=["ev:2"],
        ),
    ]
    markdown = "Caelynn reached Mireward before nightfall."
    projected, mentions, diagnostics = project_world_markdown_mentions(markdown, nodes)

    assert "[Caelynn](dmb-node:pc:caelynn)" in projected
    assert "[Mireward](dmb-node:location:mireward)" in projected
    assert {m.node_id for m in mentions} == {"pc:caelynn", "location:mireward"}
    assert all(m.evidence_ref_ids == [] for m in mentions)
    assert diagnostics == []


def test_ambiguous_alias_does_not_first_win() -> None:
    nodes = [
        WorldGraphProjectionNodeView(
            node_id="npc:river-guide",
            label="River",
            kind="npc",
            role="character",
            aliases=["River"],
        ),
        WorldGraphProjectionNodeView(
            node_id="location:river",
            label="River",
            kind="location",
            role="place",
            aliases=["River"],
        ),
    ]
    markdown = "River flooded overnight."
    projected, mentions, diagnostics = project_world_markdown_mentions(markdown, nodes)
    assert projected == markdown
    assert mentions == []
    assert any(d.code == AMBIGUOUS_MENTION_DIAGNOSTIC for d in diagnostics)


def test_longest_unique_surface_wins() -> None:
    nodes = [
        WorldGraphProjectionNodeView(
            node_id="location:mireward-reach",
            label="Mireward Reach",
            kind="location",
            role="place",
            aliases=["Mireward"],
        ),
    ]
    markdown = "They entered Mireward Reach at dusk."
    projected, mentions, _diagnostics = project_world_markdown_mentions(markdown, nodes)
    assert "[Mireward Reach](dmb-node:location:mireward-reach)" in projected
    assert "[Mireward](dmb-node:" not in projected
    assert len(mentions) == 1


def test_protected_markdown_and_code_ranges_untouched() -> None:
    nodes = [
        WorldGraphProjectionNodeView(
            node_id="pc:caelynn",
            label="Caelynn",
            kind="pc",
            role="character",
            aliases=["Caelynn"],
        ),
    ]
    markdown = (
        "See [Caelynn](https://example.test) and `Caelynn` and "
        "```\nCaelynn\n``` and [prior](dmb-node:pc:other)."
    )
    projected, mentions, _diagnostics = project_world_markdown_mentions(markdown, nodes)
    assert projected == markdown
    assert mentions == []


def test_adapt_world_node_maps_direction_vocabulary_only() -> None:
    from graph_memory.projection.world_projection import (
        WorldGraphProjectionAdjacencyCandidate,
    )

    node = WorldGraphProjectionNodeView(
        node_id="pc:stafl",
        label="Stafl",
        kind="pc",
        role="character",
        adjacency=[
            WorldGraphProjectionAdjacencyCandidate(
                edge_id="e1",
                node_id="node:heroes-party",
                label="Heroes",
                kind="party",
                predicate="member_of",
                direction="outbound",
                session_ids=["session-23"],
            )
        ],
    )
    adapted = adapt_world_node_to_recap_view(node)
    assert adapted.adjacency[0].direction == "outgoing"
    assert adapted.adjacency[0].session_ids == ["session-23"]
    assert adapted.node_id == "pc:stafl"


def test_build_requires_session_focus(tmp_path: Path) -> None:
    _initialize(tmp_path)
    request = WorldGraphProjectionRequest(
        schema="dmb_world_graph_projection_request_v1",
        world_id=WORLD_ID,
        campaign_id=CAMPAIGN_ID,
        focus={"kind": "none", "session_id": None},
        admissibility="gm",
    )
    with pytest.raises(WorldGraphProjectionServiceError) as exc_info:
        build_world_graph_recap_projection(request, root=tmp_path, corpus_markdown="x")
    assert exc_info.value.code == "invalid_request"
    assert exc_info.value.status_code == 422


def test_build_rejects_world_scope_and_query_text(tmp_path: Path) -> None:
    _initialize(tmp_path)
    with pytest.raises(WorldGraphProjectionServiceError) as exc_info:
        build_world_graph_recap_projection(
            _session_request(scope_mode="world"),
            root=tmp_path,
            corpus_markdown="x",
        )
    assert exc_info.value.code == "invalid_request"

    with pytest.raises(WorldGraphProjectionServiceError) as exc_info:
        build_world_graph_recap_projection(
            _session_request(query_text="Caelynn"),
            root=tmp_path,
            corpus_markdown="x",
        )
    assert exc_info.value.code == "invalid_request"


def test_build_rejects_focus_campaign_mismatch(tmp_path: Path) -> None:
    _initialize(tmp_path)
    with pytest.raises(WorldGraphProjectionServiceError) as exc_info:
        build_world_graph_recap_projection(
            _session_request(
                focus={
                    "kind": "session",
                    "session_id": FOCUS_SESSION_ID,
                    "campaign_id": "longmont-c1",
                }
            ),
            root=tmp_path,
            corpus_markdown="x",
        )
    assert exc_info.value.code == "invalid_request"


def test_build_fails_closed_without_markdown(tmp_path: Path) -> None:
    _initialize(tmp_path)
    with pytest.raises(WorldGraphProjectionServiceError) as exc_info:
        build_world_graph_recap_projection(
            _session_request(),
            root=tmp_path,
            corpus_markdown="   ",
        )
    assert exc_info.value.code == "recap_markdown_unavailable"
    assert exc_info.value.status_code == 404


def test_build_calls_generic_projection_once_with_campaign_scope(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _initialize(tmp_path)
    calls: list[WorldGraphProjectionRequest] = []
    import apps.live_control_server.services.world_graph_recap_projection as service

    real = service.project_world_graph

    def _spy(request: WorldGraphProjectionRequest, *, root: Path | None = None):
        calls.append(request)
        return real(request, root=root)

    monkeypatch.setattr(service, "project_world_graph", _spy)
    build_world_graph_recap_projection(
        _session_request(),
        root=tmp_path,
        corpus_markdown="Caelynn stood watch.",
    )
    assert len(calls) == 1
    assert calls[0].scope_mode == "campaign"


def test_build_never_calls_forbidden_selectors(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _initialize(tmp_path)
    banned = MagicMock(side_effect=AssertionError("forbidden selector consulted"))
    monkeypatch.setattr(
        "apps.live_control_server.services.graph_ingest_run_registry."
        "resolve_latest_graph_ingest_run",
        banned,
        raising=False,
    )
    projection = build_world_graph_recap_projection(
        _session_request(),
        root=tmp_path,
        corpus_markdown="The positional controller failed near the Tripod Null-Calf.",
    )
    assert projection.schema_ == RECAP_PROJECTION_RESPONSE_SCHEMA
    assert projection.graph_id == projection.snapshot.revision_id
    assert projection.source_spans == []
    assert "mention spans are evidence bindings" in projection.trust_boundary.cannot_trust
    banned.assert_not_called()


def test_build_splices_world_ids_into_injected_markdown(tmp_path: Path) -> None:
    _initialize(tmp_path)
    markdown = "The positional controller failed near the Tripod Null-Calf."
    projection = build_world_graph_recap_projection(
        _session_request(),
        root=tmp_path,
        corpus_markdown=markdown,
    )
    assert projection.session_id == FOCUS_SESSION_ID
    assert projection.campaign_id == CAMPAIGN_ID
    assert projection.graph_id
    assert projection.node_views
    assert projection.snapshot.revision_id == projection.graph_id
    payload = build_world_graph_recap_projection_payload(
        _session_request(),
        root=tmp_path,
        corpus_markdown=markdown,
    )
    assert payload["schema"] == RECAP_PROJECTION_RESPONSE_SCHEMA
    assert "graphId" in payload
    assert "nodeViews" in payload
    assert "session_id" not in payload


def test_ambiguous_recap_source_fails_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _initialize(tmp_path)
    import apps.live_control_server.services.world_graph_recap_projection as service
    from apps.live_control_server.services.union_supergraph_projection_adapter import (
        CorpusNormalizedRecapLoadError,
    )

    def _boom(**_kwargs: Any) -> str:
        raise CorpusNormalizedRecapLoadError(
            "Ambiguous normalized recap identity",
            code="recap_source_ambiguous",
            status_code=422,
        )

    monkeypatch.setattr(service, "load_corpus_normalized_recap_markdown", _boom)
    with pytest.raises(WorldGraphProjectionServiceError) as exc_info:
        build_world_graph_recap_projection(_session_request(), root=tmp_path)
    assert exc_info.value.code == "recap_source_ambiguous"
    assert exc_info.value.status_code == 422


def test_recap_projection_route_rejects_query_params(client: TestClient) -> None:
    response = client.post(
        f"{RECAP_PROJECTION_URL}?worldId=foreign",
        json={
            "schema": "dmb_world_graph_projection_request_v1",
            "worldId": WORLD_ID,
            "campaignId": CAMPAIGN_ID,
            "focus": {
                "kind": "session",
                "sessionId": FOCUS_SESSION_ID,
                "campaignId": CAMPAIGN_ID,
            },
            "admissibility": "gm",
        },
    )
    assert response.status_code == 422
    assert response.json()["code"] == "invalid_request"


def test_recap_projection_route_returns_camel_case_payload(
    client: TestClient,
    tmp_path: Path,
) -> None:
    _initialize(tmp_path)
    import apps.live_control_server.services.world_graph_recap_projection as service

    original = service.load_corpus_normalized_recap_markdown
    service.load_corpus_normalized_recap_markdown = (  # type: ignore[assignment]
        lambda **_kwargs: "Caelynn stood at Mireward Reach."
    )
    try:
        response = client.post(
            RECAP_PROJECTION_URL,
            json={
                "schema": "dmb_world_graph_projection_request_v1",
                "worldId": WORLD_ID,
                "campaignId": CAMPAIGN_ID,
                "focus": {
                    "kind": "session",
                    "sessionId": FOCUS_SESSION_ID,
                    "campaignId": CAMPAIGN_ID,
                },
                "admissibility": "gm",
                "scopeMode": "campaign",
            },
        )
    finally:
        service.load_corpus_normalized_recap_markdown = original  # type: ignore[assignment]

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["schema"] == RECAP_PROJECTION_RESPONSE_SCHEMA
    assert payload["sessionId"] == FOCUS_SESSION_ID
    assert payload["campaignId"] == CAMPAIGN_ID
    assert payload["graphId"]
    assert payload["graphId"] == payload["snapshot"]["revisionId"]
    assert "nodeViews" in payload
    assert "mentions" in payload
    assert payload["sourceSpans"] == []
    assert "trustBoundary" in payload
    assert "use_latest_graph_ingest" not in response.text
    assert "session_id" not in payload


def test_recap_projection_route_requires_session_focus(
    client: TestClient,
    tmp_path: Path,
) -> None:
    _initialize(tmp_path)
    response = client.post(
        RECAP_PROJECTION_URL,
        json={
            "schema": "dmb_world_graph_projection_request_v1",
            "worldId": WORLD_ID,
            "campaignId": CAMPAIGN_ID,
            "focus": {"kind": "none", "sessionId": None},
            "admissibility": "gm",
        },
    )
    assert response.status_code == 422
    assert response.json()["code"] == "invalid_request"


def test_missing_graph_root_fails_closed_without_fixture_fallback(
    client: TestClient,
    tmp_path: Path,
) -> None:
    empty_root = tmp_path / "empty-world-root"
    empty_root.mkdir()
    import apps.live_control_server.services.world_graph_recap_projection as service

    original = service.load_corpus_normalized_recap_markdown
    service.load_corpus_normalized_recap_markdown = (  # type: ignore[assignment]
        lambda **_kwargs: "unused"
    )
    try:
        response = client.post(
            RECAP_PROJECTION_URL,
            json={
                "schema": "dmb_world_graph_projection_request_v1",
                "worldId": WORLD_ID,
                "campaignId": CAMPAIGN_ID,
                "focus": {
                    "kind": "session",
                    "sessionId": FOCUS_SESSION_ID,
                    "campaignId": CAMPAIGN_ID,
                },
                "admissibility": "gm",
                "scopeMode": "campaign",
            },
        )
    finally:
        service.load_corpus_normalized_recap_markdown = original  # type: ignore[assignment]

    assert response.status_code >= 400
    assert response.status_code != 200
