"""World Graph recap projection — pure helpers + service + HTTP boundary (PR380A)."""

from __future__ import annotations

import json
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
    WorldGraphProjectionDiagnostic,
    WorldGraphProjectionNodeView,
    WorldGraphProjectionRequest,
)
from graph_memory.projection.world_recap_projection import (
    AMBIGUOUS_MENTION_DIAGNOSTIC,
    RECAP_PROJECTION_RESPONSE_SCHEMA,
    WorldGraphRecapMention,
    WorldGraphRecapProjection,
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


# Linker coverage moved: the CommonMark scanner and mention splicer now live in
# src/graph_memory/projection/markdown_mentions.py, and their owning tests plus
# the base-generated characterization fixture live in tests/test_markdown_mentions.py.
# What remains here is adapter-level — the recap types this module returns and
# the binding order it constructs.


def test_recap_adapter_returns_recap_mention_and_diagnostic_types() -> None:
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
    assert all(isinstance(m, WorldGraphRecapMention) for m in mentions)
    # Node evidence is never copied onto a navigation-only mention.
    assert all(m.evidence_ref_ids == [] for m in mentions)
    assert diagnostics == []


def test_recap_adapter_maps_diagnostics_to_world_projection_type() -> None:
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
    assert len(diagnostics) == 1
    assert isinstance(diagnostics[0], WorldGraphProjectionDiagnostic)
    assert diagnostics[0].code == AMBIGUOUS_MENTION_DIAGNOSTIC
    assert diagnostics[0].severity == "warning"


def test_recap_adapter_binding_order_is_node_order_label_first() -> None:
    """Node-iteration order, label before aliases, duplicates preserved.

    The ambiguity diagnostic quotes the first bound surface with its original
    casing, so this ordering is observable behavior, not an implementation
    detail. Reversing the node list must reverse which casing is quoted.
    """
    nodes = [
        WorldGraphProjectionNodeView(
            node_id="npc:first",
            label="cAeLyNn",
            kind="npc",
            role="character",
            aliases=["CaElYnN"],
        ),
        WorldGraphProjectionNodeView(
            node_id="npc:second",
            label="CAELYNN",
            kind="npc",
            role="character",
            aliases=["caelynn"],
        ),
    ]
    _projected, _mentions, diagnostics = project_world_markdown_mentions(
        "Then CAELYNN spoke.", nodes
    )
    assert "'cAeLyNn'" in diagnostics[0].message

    _projected, _mentions, reversed_diagnostics = project_world_markdown_mentions(
        "Then CAELYNN spoke.", list(reversed(nodes))
    )
    assert "'CAELYNN'" in reversed_diagnostics[0].message


def test_recap_adapter_preserves_protection_at_the_surface_boundary() -> None:
    """Smoke: the adapter still runs protection. Full corpus lives in the
    neutral module's characterization fixture."""
    nodes = [
        WorldGraphProjectionNodeView(
            node_id="pc:caelynn",
            label="Caelynn",
            kind="pc",
            role="character",
            aliases=["Caelynn"],
        ),
    ]
    markdown = "Inline `Caelynn` stays.\n\n```\nCaelynn\n```\n"
    projected, mentions, _diagnostics = project_world_markdown_mentions(
        markdown, nodes
    )
    assert projected == markdown
    assert mentions == []


def test_recap_node_views_reuse_generic_world_node_models() -> None:
    """Recap nested nodes are the generic model — not a parallel class tree."""
    import typing

    hints = typing.get_type_hints(WorldGraphRecapProjection)
    node_views_type = hints["node_views"]
    args = typing.get_args(node_views_type)
    assert args[0] is str
    assert args[1] is WorldGraphProjectionNodeView


def test_recap_node_json_equals_generic_node_json_exactly() -> None:
    from graph_memory.projection.world_projection import (
        WorldGraphProjectionAdjacencyCandidate,
        WorldGraphProjectionEvidenceBadge,
        WorldGraphProjectionSuggestedExpansion,
        WorldGraphProjectionTextHighlightSpan,
    )

    node = WorldGraphProjectionNodeView(
        node_id="pc:fixture",
        label="Fixture Hero",
        kind="pc",
        role="character",
        aliases=["Hero"],
        source_domains=["recap"],
        summary="A fixture hero.",
        anchored_to_focus_session=True,
        campaign_scope="longmont-c2",
        evidence_badges=[
            WorldGraphProjectionEvidenceBadge(
                evidence_ref_id="ev:1",
                source_artifact_id="art:1",
                source_domain="recap",
                evidence_role="mention",
                is_focus_session_evidence=True,
                can_open_source=True,
                can_highlight_span=True,
                label="badge",
                session_id="session-23",
                source_span_ref_id="span:1",
            )
        ],
        adjacency=[
            WorldGraphProjectionAdjacencyCandidate(
                edge_id="e:out",
                node_id="npc:other",
                label="Other",
                kind="npc",
                predicate="allied_with",
                direction="outgoing",
                anchored_to_focus_session=True,
                source_domains=["recap"],
                evidence_ref_ids=["ev:1"],
                edge_label="allied with",
                session_ids=["session-23"],
                campaign_scope="longmont-c2",
                related_summary="Allies",
                source_excerpt="Fixture Hero allied with Other at the ford.",
                source_excerpt_is_full_paragraph=True,
                source_excerpt_highlight_spans=[
                    WorldGraphProjectionTextHighlightSpan(start=0, end=12)
                ],
            )
        ],
        suggested_expansions=[
            WorldGraphProjectionSuggestedExpansion(
                edge_id="e:out",
                node_id="npc:other",
                label="Other",
                kind="npc",
                predicate="allied_with",
                direction="outgoing",
                rank=1,
                rank_reason="connected thread",
                source_excerpt="Fixture Hero allied with Other at the ford.",
                source_excerpt_is_full_paragraph=True,
                source_excerpt_highlight_spans=[
                    WorldGraphProjectionTextHighlightSpan(start=0, end=12)
                ],
            )
        ],
        evidence_ref_ids=["ev:1", "ev:2"],
        source_artifact_ids=["art:1", "art:2"],
    )
    # Direct reuse: the recap map stores the same model instance/type.
    node_views = {node.node_id: node}
    recap_node = node_views[node.node_id]
    assert type(recap_node) is WorldGraphProjectionNodeView
    assert recap_node.model_dump(mode="json", by_alias=True) == node.model_dump(
        mode="json", by_alias=True
    )
    # Additive inherited fields previously omitted by the recap fork.
    payload = recap_node.model_dump(mode="json", by_alias=True)
    assert payload["evidenceRefIds"] == ["ev:1", "ev:2"]
    assert payload["sourceArtifactIds"] == ["art:1", "art:2"]
    assert payload["adjacency"][0]["sourceExcerptIsFullParagraph"] is True
    assert payload["adjacency"][0]["sourceExcerptHighlightSpans"] == [
        {"start": 0, "end": 12}
    ]



COMPAT_BASELINE_PATH = Path(
    "tests/fixtures/graph_memory/recap_compat_baseline_v1.json"
)
ADDITIVE_RECAP_NODE_FIELDS = ("evidenceRefIds", "sourceArtifactIds")


def _strip_additive_recap_node_fields(node_payload: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in node_payload.items()
        if key not in ADDITIVE_RECAP_NODE_FIELDS
    }


def test_recap_compatibility_replays_prechange_baseline() -> None:
    """Replay the committed pre-change recap expectation.

    Proves preservation of every prior nested/envelope field against the
    base-captured fixture (not head-vs-head equality), with directions already
    normalized and additive generic fields asserted separately.
    """
    baseline = json.loads(COMPAT_BASELINE_PATH.read_text(encoding="utf-8"))
    before_node = baseline["recap_node_before"]
    before_envelope = baseline["recap_envelope_before"]
    generic_node = baseline["generic_node"]
    assert baseline["additive_fields_omitted_by_recap_fork"] == list(
        ADDITIVE_RECAP_NODE_FIELDS
    )
    assert "evidenceRefIds" not in before_node
    assert "sourceArtifactIds" not in before_node
    assert [row["direction"] for row in before_node["adjacency"]] == [
        "outgoing",
        "incoming",
        "related",
    ]

    head_node_payload = {
        **before_node,
        "evidenceRefIds": generic_node["evidenceRefIds"],
        "sourceArtifactIds": generic_node["sourceArtifactIds"],
    }
    head_node = WorldGraphProjectionNodeView.model_validate(head_node_payload)
    node_views = {head_node.node_id: head_node}

    head_envelope = WorldGraphRecapProjection.model_validate(
        {
            **{key: value for key, value in before_envelope.items() if key != "nodeViews"},
            "nodeViews": {
                node_id: node.model_dump(mode="json", by_alias=True)
                for node_id, node in node_views.items()
            },
        }
    )
    head_dump = head_envelope.model_dump(mode="json", by_alias=True)
    head_node_dump = head_dump["nodeViews"][head_node.node_id]

    # Pre-existing nested fields (excluding declared additive inheritance).
    assert _strip_additive_recap_node_fields(head_node_dump) == before_node
    # Directions remain the closed vocabulary recorded in the baseline.
    assert [row["direction"] for row in head_node_dump["adjacency"]] == [
        "outgoing",
        "incoming",
        "related",
    ]
    assert head_node_dump["suggestedExpansions"][0]["direction"] == "outgoing"
    # Additive inherited fields come verbatim from the generic source node.
    assert head_node_dump["evidenceRefIds"] == generic_node["evidenceRefIds"]
    assert head_node_dump["sourceArtifactIds"] == generic_node["sourceArtifactIds"]
    # Mentions remain navigation-only (empty evidenceRefIds) in the baseline envelope.
    assert head_dump["mentions"][0]["evidenceRefIds"] == []

    for key, value in before_envelope.items():
        if key == "nodeViews":
            continue
        assert head_dump[key] == value, f"envelope field drifted: {key}"

    for node_id, prior in before_envelope["nodeViews"].items():
        assert _strip_additive_recap_node_fields(head_dump["nodeViews"][node_id]) == prior

def test_deleted_recap_adapters_are_absent() -> None:
    import graph_memory.projection.world_recap_projection as recap_mod
    import graph_memory.projection as projection_pkg

    for name in (
        "WorldGraphRecapNodeView",
        "WorldGraphRecapEvidenceBadge",
        "WorldGraphRecapTextHighlightSpan",
        "WorldGraphRecapAdjacencyCandidate",
        "WorldGraphRecapSuggestedExpansion",
        "adapt_world_node_to_recap_view",
        "adapt_relationship_direction",
        "_adapt_evidence_badge",
        "_adapt_highlight_spans",
        "_adapt_adjacency",
        "_adapt_suggested_expansion",
    ):
        assert not hasattr(recap_mod, name)
    assert not hasattr(projection_pkg, "adapt_world_node_to_recap_view")


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
    # Exact generic↔recap node payload equality on the service boundary.
    from apps.live_control_server.services.world_graph_projection import (
        project_world_graph,
    )

    world = project_world_graph(_session_request(), root=tmp_path)
    for node in world.nodes:
        recap_node = projection.node_views[node.node_id]
        assert type(recap_node) is WorldGraphProjectionNodeView
        assert recap_node.model_dump(mode="json", by_alias=True) == node.model_dump(
            mode="json", by_alias=True
        )
        assert recap_node.evidence_ref_ids == node.evidence_ref_ids
        assert recap_node.source_artifact_ids == node.source_artifact_ids
        for candidate in recap_node.adjacency:
            assert candidate.direction in {"outgoing", "incoming", "related"}
    assert all(m.evidence_ref_ids == [] for m in projection.mentions)
    payload = build_world_graph_recap_projection_payload(
        _session_request(),
        root=tmp_path,
        corpus_markdown=markdown,
    )
    assert payload["schema"] == RECAP_PROJECTION_RESPONSE_SCHEMA
    assert "graphId" in payload
    assert "nodeViews" in payload
    assert "session_id" not in payload
    # Additive inherited fields appear on the wire.
    sample_id = next(iter(payload["nodeViews"]))
    assert "evidenceRefIds" in payload["nodeViews"][sample_id]
    assert "sourceArtifactIds" in payload["nodeViews"][sample_id]


def test_ambiguous_recap_source_fails_closed_across_padded_and_unpadded(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Padded + unpadded Session N files must both count toward ambiguity."""
    _initialize(tmp_path)
    from apps.live_control_server.services.union_supergraph_projection_adapter import (
        CorpusNormalizedRecapLoadError,
        load_corpus_normalized_recap_markdown,
    )

    corpus = tmp_path / "corpus"
    normalized = (
        corpus
        / "Longmont Campaign"
        / "Campaign 2"
        / "Session Recaps"
        / "_normalized"
    )
    normalized.mkdir(parents=True)
    (normalized / "Session 03 - Alpha.md").write_text("# Alpha\n", encoding="utf-8")
    (normalized / "Session 3 - Bravo.md").write_text("# Bravo\n", encoding="utf-8")
    monkeypatch.setattr(
        "apps.live_control_server.services.union_supergraph_projection_adapter.corpus_root",
        lambda: corpus,
    )

    with pytest.raises(WorldGraphProjectionServiceError) as exc_info:
        build_world_graph_recap_projection(
            _session_request(session_id="session-3"),
            root=tmp_path,
        )
    assert exc_info.value.code == "recap_source_ambiguous"
    assert exc_info.value.status_code == 422

    with pytest.raises(CorpusNormalizedRecapLoadError) as load_exc:
        load_corpus_normalized_recap_markdown(
            campaign_id=CAMPAIGN_ID,
            session_id="session-3",
            on_ambiguous="fail",
        )
    assert load_exc.value.code == "recap_source_ambiguous"


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


CAELYNN_NODE_ID = "pc:caelynn"
CAELYNN_CONTRIBUTION_ID = "contribution:33d7cdb0ff623f28"
HEAD_ONLY_LABEL = "CaelynnRenamedHead"


def _load_contribution_json(root: Path, contribution_id: str) -> dict[str, Any]:
    safe = contribution_id.replace(":", "__")
    path = (
        root
        / "graph_memory"
        / "worlds"
        / WORLD_ID
        / "contributions"
        / f"{safe}.json"
    )
    return json.loads(path.read_text(encoding="utf-8"))


def _publish_caelynn_label_revision(root: Path) -> tuple[str, str]:
    """Supersede Caelynn so head B no longer matches surface 'Caelynn'. Return (A, B)."""
    revision_a = kernel.open_world_graph_head(root, WORLD_ID).head_revision_id
    original_payload = _load_contribution_json(root, CAELYNN_CONTRIBUTION_ID)
    replacement_assertions = [
        kernel.GraphContributionAssertion.model_validate(assertion)
        for assertion in original_payload["accepted_assertions"]
    ]
    for assertion in replacement_assertions:
        if (
            assertion.assertion_kind != "node"
            or assertion.subject_node_id != CAELYNN_NODE_ID
        ):
            continue
        value = dict(assertion.value)
        assertion.label = HEAD_ONLY_LABEL
        assertion.value = {
            **value,
            "label": HEAD_ONLY_LABEL,
            "aliases": [HEAD_ONLY_LABEL],
        }

    replacement_contribution = kernel.create_graph_contribution(
        world_id=WORLD_ID,
        source_kind="manual_import",
        source_artifact_id=original_payload["source_artifact_id"],
        source_revision_id="recap-pin-caelynn-1",
        accepted_assertions=replacement_assertions,
        supersedes_contribution_id=CAELYNN_CONTRIBUTION_ID,
    )
    superseded = kernel.supersede_graph_contribution(
        root,
        world_id=WORLD_ID,
        new_contribution=replacement_contribution,
        superseded_contribution_id=CAELYNN_CONTRIBUTION_ID,
    )
    assert superseded.published is True
    revision_b = kernel.open_world_graph_head(root, WORLD_ID).head_revision_id
    assert revision_b != revision_a
    return revision_a, revision_b


def test_revision_pin_survives_recap_service_boundary(tmp_path: Path) -> None:
    _initialize(tmp_path)
    revision_a, revision_b = _publish_caelynn_label_revision(tmp_path)

    markdown = "Caelynn stood at the gate."
    pinned = build_world_graph_recap_projection(
        _session_request(revision_pin=revision_a),
        root=tmp_path,
        corpus_markdown=markdown,
    )
    head_proj = build_world_graph_recap_projection(
        _session_request(),
        root=tmp_path,
        corpus_markdown=markdown,
    )

    assert pinned.graph_id == revision_a
    assert pinned.snapshot.revision_id == revision_a
    assert pinned.snapshot.is_head is False
    assert pinned.snapshot.head_revision_id == revision_b
    caelynn_a = pinned.node_views[CAELYNN_NODE_ID]
    assert caelynn_a.label == "Caelynn"
    assert HEAD_ONLY_LABEL not in caelynn_a.label
    assert any(m.node_id == CAELYNN_NODE_ID for m in pinned.mentions)
    assert "[Caelynn](dmb-node:pc:caelynn)" in pinned.markdown

    assert head_proj.graph_id == revision_b
    assert head_proj.snapshot.is_head is True
    caelynn_b = head_proj.node_views[CAELYNN_NODE_ID]
    assert caelynn_b.label == HEAD_ONLY_LABEL
    assert not any(m.node_id == CAELYNN_NODE_ID for m in head_proj.mentions)
    assert "[Caelynn](dmb-node:" not in head_proj.markdown
    assert head_proj.markdown == markdown


def test_revision_pin_survives_recap_route_boundary(
    client: TestClient,
    tmp_path: Path,
) -> None:
    _initialize(tmp_path)
    revision_a, revision_b = _publish_caelynn_label_revision(tmp_path)

    import apps.live_control_server.services.world_graph_recap_projection as service

    original = service.load_corpus_normalized_recap_markdown
    service.load_corpus_normalized_recap_markdown = (  # type: ignore[assignment]
        lambda **_kwargs: "Caelynn stood at the gate."
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
                "revisionPin": revision_a,
            },
        )
    finally:
        service.load_corpus_normalized_recap_markdown = original  # type: ignore[assignment]

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["graphId"] == revision_a
    assert payload["snapshot"]["revisionId"] == revision_a
    assert payload["snapshot"]["isHead"] is False
    assert payload["snapshot"]["headRevisionId"] == revision_b
    assert payload["nodeViews"][CAELYNN_NODE_ID]["label"] == "Caelynn"
    assert any(m["nodeId"] == CAELYNN_NODE_ID for m in payload["mentions"])
    assert "[Caelynn](dmb-node:pc:caelynn)" in payload["markdown"]
