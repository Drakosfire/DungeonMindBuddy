"""World Graph recap projection — service + HTTP boundary."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import graph_memory.kernel as kernel
from apps.live_control_server.main import create_app
from apps.live_control_server.services.world_graph_projection import (
    WorldGraphProjectionServiceError,
)
from apps.live_control_server.services.world_graph_recap_projection import (
    build_world_graph_recap_projection,
    project_world_markdown_mentions,
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


def _session_request(session_id: str = FOCUS_SESSION_ID) -> WorldGraphProjectionRequest:
    return WorldGraphProjectionRequest(
        schema="dmb_world_graph_projection_request_v1",
        world_id=WORLD_ID,
        campaign_id=CAMPAIGN_ID,
        focus={"kind": "session", "session_id": session_id, "campaign_id": CAMPAIGN_ID},
        admissibility="gm",
        scope_mode="campaign",
    )


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
    projected, mentions = project_world_markdown_mentions(markdown, nodes)

    assert "[Caelynn](dmb-node:pc:caelynn)" in projected
    assert "[Mireward](dmb-node:location:mireward)" in projected
    assert {m.node_id for m in mentions} == {"pc:caelynn", "location:mireward"}


def test_registry_standing_chips_pcs_omitted_from_campaign_projection(
    tmp_path: Path,
) -> None:
    """C1 campaign scope can omit C2-scoped standing PCs; roster still chips."""
    from apps.live_control_server.services.world_graph_recap_projection import (
        _merge_registry_standing_into_nodes,
    )

    # No PC nodes in the campaign-scoped projection payload.
    nodes = [
        WorldGraphProjectionNodeView(
            node_id="npc_pippa",
            label="Pippa",
            kind="npc",
            role="character",
            aliases=["Pippa"],
            evidence_ref_ids=[],
        ),
    ]
    merged = _merge_registry_standing_into_nodes(
        nodes,
        campaign_id="longmont-c1",
        session_id="session-3",
    )
    pc_ids = {node.node_id for node in merged if node.kind == "pc"}
    assert "pc:stafl" in pc_ids
    assert "pc:caelynn" in pc_ids

    markdown = (
        "Stafl wrote a song. Caelynn uses ice. Bonogo dives. "
        "Baergrom loses the rope. Ephanna lassos Bubbles. Karsemine uses Zephyr strike."
    )
    projected, mentions = project_world_markdown_mentions(markdown, merged)
    assert "[Stafl](dmb-node:pc:stafl)" in projected
    assert "[Caelynn](dmb-node:pc:caelynn)" in projected
    assert "[Bonogo](dmb-node:pc:bonogo)" in projected
    assert "[Baergrom](dmb-node:pc:baergrom)" in projected
    assert "[Ephanna](dmb-node:pc:ephanna)" in projected
    assert "[Karsemine](dmb-node:pc:karsemine)" in projected
    assert {m.node_id for m in mentions} >= {
        "pc:stafl",
        "pc:caelynn",
        "pc:bonogo",
        "pc:baergrom",
        "pc:ephanna",
        "pc:karsemine",
    }


def test_thread_aliases_chip_prose_surfaces_not_full_summary_labels() -> None:
    from apps.live_control_server.services.world_graph_recap_projection import (
        _enrich_thread_aliases_from_markdown,
    )

    nodes = [
        WorldGraphProjectionNodeView(
            node_id="mystery:session3:bubbles_scare",
            label="Bubbles the Float Goat panic during flood rescue",
            kind="mystery",
            role="thread",
            aliases=["Bubbles the Float Goat panic during flood rescue"],
            evidence_ref_ids=[],
        ),
        WorldGraphProjectionNodeView(
            node_id="mystery:session3:mirathorn_festival",
            label="Possible next destination: Mirathorn festival",
            kind="mystery",
            role="thread",
            aliases=["Possible next destination: Mirathorn festival"],
            evidence_ref_ids=[],
        ),
        WorldGraphProjectionNodeView(
            node_id="pc:stafl",
            label="Stafl",
            kind="pc",
            role="character",
            aliases=["Stafl"],
            evidence_ref_ids=[],
        ),
    ]
    markdown = (
        "Players heard Pippa yelling and immediately ran out to help find Bubbles. "
        "Possible next destination mentions Mirathorn after Stone Bridge."
    )
    enriched = _enrich_thread_aliases_from_markdown(nodes, markdown)
    projected, mentions = project_world_markdown_mentions(markdown, enriched)
    assert "[Bubbles](dmb-node:mystery:session3:bubbles_scare)" in projected or (
        "[Float Goat](dmb-node:mystery:session3:bubbles_scare)" in projected
    )
    assert "[Mirathorn](dmb-node:mystery:session3:mirathorn_festival)" in projected
    assert any(m.node_id.startswith("mystery:") for m in mentions)


def test_thread_aliases_do_not_steal_pc_name_surfaces() -> None:
    from apps.live_control_server.services.world_graph_recap_projection import (
        _enrich_thread_aliases_from_markdown,
    )

    nodes = [
        WorldGraphProjectionNodeView(
            node_id="pc:ephanna",
            label="Ephanna",
            kind="pc",
            role="character",
            aliases=["Ephanna"],
            evidence_ref_ids=[],
        ),
        WorldGraphProjectionNodeView(
            node_id="mystery:session7:ephanna_capture",
            label="Ephanna capture by river cultists",
            kind="mystery",
            role="thread",
            aliases=["Ephanna capture by river cultists"],
            evidence_ref_ids=[],
        ),
    ]
    markdown = "Ephanna lassos Bubbles near the bridge."
    enriched = _enrich_thread_aliases_from_markdown(nodes, markdown)
    projected, _mentions = project_world_markdown_mentions(markdown, enriched)
    assert "[Ephanna](dmb-node:pc:ephanna)" in projected
    assert "[Ephanna](dmb-node:mystery:session7:ephanna_capture)" not in projected


def test_mentioned_standing_pc_stamps_focus_session_on_party_membership() -> None:
    from apps.live_control_server.services.world_graph_recap_projection import (
        _stamp_focus_session_on_mentioned_standing,
    )
    from graph_memory.projection.world_projection import (
        WorldGraphProjectionAdjacencyCandidate,
    )

    nodes = [
        WorldGraphProjectionNodeView(
            node_id="pc:stafl",
            label="Stafl",
            kind="pc",
            role="character",
            aliases=["Stafl"],
            evidence_ref_ids=[],
            adjacency=[
                WorldGraphProjectionAdjacencyCandidate(
                    edge_id="e-party",
                    node_id="node:heroes-party",
                    label="Heroes / party",
                    kind="party",
                    predicate="member_of",
                    direction="outbound",
                    session_ids=["session-3", "session-4"],
                ),
                WorldGraphProjectionAdjacencyCandidate(
                    edge_id="e-item",
                    node_id="item:nets",
                    label="Nets",
                    kind="item",
                    predicate="holds",
                    direction="outbound",
                    session_ids=["session-3"],
                ),
            ],
        )
    ]
    stamped = _stamp_focus_session_on_mentioned_standing(
        nodes,
        session_id="session-1",
        campaign_id="longmont-c1",
        markdown="Stafl the 'Human' Bard joins the table.",
    )
    stafl = stamped[0]
    party = next(a for a in stafl.adjacency if a.node_id == "node:heroes-party")
    assert "session-1" in party.session_ids
    assert party.anchored_to_focus_session is True
    nets = next(a for a in stafl.adjacency if a.node_id == "item:nets")
    assert nets.session_ids == ["session-3"]


def test_unmentioned_standing_pc_does_not_get_focus_session_stamp() -> None:
    from apps.live_control_server.services.world_graph_recap_projection import (
        _stamp_focus_session_on_mentioned_standing,
    )
    from graph_memory.projection.world_projection import (
        WorldGraphProjectionAdjacencyCandidate,
    )

    nodes = [
        WorldGraphProjectionNodeView(
            node_id="pc:stafl",
            label="Stafl",
            kind="pc",
            role="character",
            aliases=["Stafl"],
            evidence_ref_ids=[],
            adjacency=[
                WorldGraphProjectionAdjacencyCandidate(
                    edge_id="e-party",
                    node_id="node:heroes-party",
                    label="Heroes / party",
                    kind="party",
                    predicate="member_of",
                    direction="outbound",
                    session_ids=["session-3"],
                )
            ],
        )
    ]
    stamped = _stamp_focus_session_on_mentioned_standing(
        nodes,
        session_id="session-1",
        campaign_id="longmont-c1",
        markdown="Pippa yells about Bubbles near Stone Bridge.",
    )
    party = stamped[0].adjacency[0]
    assert party.session_ids == ["session-3"]


def test_mentioned_pc_without_party_edge_gets_synthetic_focus_presence() -> None:
    from apps.live_control_server.services.world_graph_recap_projection import (
        _stamp_focus_session_on_mentioned_standing,
    )

    nodes = [
        WorldGraphProjectionNodeView(
            node_id="pc:stafl",
            label="Stafl",
            kind="pc",
            role="character",
            aliases=["Stafl"],
            evidence_ref_ids=[],
            adjacency=[],
        )
    ]
    stamped = _stamp_focus_session_on_mentioned_standing(
        nodes,
        session_id="session-1",
        campaign_id="longmont-c1",
        markdown="Stafl plays a song.",
    )
    assert stamped[0].adjacency
    assert stamped[0].adjacency[0].session_ids == ["session-1"]
    assert stamped[0].adjacency[0].node_id == "node:heroes-party"


def test_world_standing_nodes_preserve_adjacency_on_merged_pcs() -> None:
    from apps.live_control_server.services.world_graph_recap_projection import (
        _merge_registry_standing_into_nodes,
    )
    from graph_memory.projection.world_projection import (
        WorldGraphProjectionAdjacencyCandidate,
    )

    standing = [
        WorldGraphProjectionNodeView(
            node_id="pc:stafl",
            label="Stafl",
            kind="pc",
            role="character",
            aliases=["Stafl"],
            evidence_ref_ids=[],
            adjacency=[
                WorldGraphProjectionAdjacencyCandidate(
                    edge_id="e1",
                    node_id="mystery:session3:bubbles_scare",
                    label="Bubbles scare",
                    kind="mystery",
                    predicate="involved_in",
                    direction="outbound",
                )
            ],
        )
    ]
    merged = _merge_registry_standing_into_nodes(
        [],
        campaign_id="longmont-c1",
        session_id="session-3",
        world_standing_nodes=standing,
    )
    stafl = next(node for node in merged if node.node_id == "pc:stafl")
    assert stafl.adjacency
    assert stafl.adjacency[0].node_id == "mystery:session3:bubbles_scare"


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


def test_build_splices_world_ids_into_injected_markdown(tmp_path: Path) -> None:
    _initialize(tmp_path)
    # Use a label known to exist in the initialized world bundle.
    markdown = "The positional controller failed near the Tripod Null-Calf."
    projection = build_world_graph_recap_projection(
        _session_request(),
        root=tmp_path,
        corpus_markdown=markdown,
    )
    assert projection.session_id == FOCUS_SESSION_ID
    assert projection.campaign_id == CAMPAIGN_ID
    assert projection.graph_id  # world revision id
    assert projection.node_views
    # At least one durable world id appears in chips or node_views.
    assert any(node_id.startswith(("pc:", "npc:", "location:", "threat:", "object:"))
               for node_id in projection.node_views)
    assert "dmb-node:" in (projection.markdown or "") or projection.mentions == []


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


def test_recap_projection_route_returns_recap_payload(
    client: TestClient,
    tmp_path: Path,
) -> None:
    _initialize(tmp_path)
    # Monkeypatch markdown load via service injection is not available on the route;
    # stub the loader used by the service.
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
    assert payload["session_id"] == FOCUS_SESSION_ID
    assert payload["campaign_id"] == CAMPAIGN_ID
    assert payload["graph_id"]
    assert "node_views" in payload
    assert "mentions" in payload
    assert "markdown" in payload
    assert "use_latest_graph_ingest" not in response.text


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
