"""Complete selected-object projection: authority mapping, fingerprint, batch join."""

from __future__ import annotations

from types import SimpleNamespace
from typing import cast
from uuid import UUID

from dungeonmind.application.graph_snapshot import GraphRelationshipView
from dungeonmind.application.world_graph_retrieval import AdmittedAssertionValue
from dungeonmind.contracts.projection import Admissibility
from dungeonmind.contracts.projection_v2 import ScopeModeV2

from apps.live_control_server.integrations.dungeonmind.world_graph_reads import (
    DirectAuthorityBinding,
    _complete_object_attribute_view,
    _complete_object_relationship_view,
    _map_complete_object_context,
)
from apps.live_control_server.models.world_graph_object_projection import (
    SelectedObjectCompletenessView,
    WorldGraphObjectProjectionAssertion,
    WorldGraphObjectProjectionRelationship,
    WorldGraphObjectProjectionRequest,
    WorldGraphObjectProjectionResult,
    WorldGraphObjectProjectionSourceBinding,
    object_projection_semantic_fingerprint,
)
from apps.live_control_server.services.world_graph_object_projection import (
    _apply_durable_bindings,
)
from application_state.source.service import (
    get_source_markdown_batch,
    persist_source_markdown,
)
from apps.live_control_server.services.agent_world_graph_query_context import (
    AgentWorldGraphQueryContextRequest,
    render_world_graph_prompt_block,
    resolve_agent_world_graph_query_context,
)
from graph_memory.projection.world_projection import (
    WorldGraphProjectionFocus,
    WorldGraphProjectionNodeView,
    WorldGraphProjectionSnapshot,
)


def _request(**overrides):
    payload = {
        "schema": "dmb_world_graph_object_projection_request_v1",
        "worldId": "eldyrwild",
        "campaignId": "longmont-c2",
        "nodeId": "pc:karsemine",
        "admissibility": "gm",
    }
    payload.update(overrides)
    return WorldGraphObjectProjectionRequest.model_validate(payload)


def test_complete_object_request_forces_world_cross_campaign_scope():
    binding = DirectAuthorityBinding(
        world_id="eldyrwild",
        dungeonmind_first_revision_id="rev:da",
        dungeonmind_head_revision_id="rev:head",
        legacy_buddy_revision_id=None,
        genesis="reviewed_world_initialization",
    )
    mapped = _map_complete_object_context(_request(), binding)
    assert mapped.scope_mode is ScopeModeV2.WORLD_CROSS_CAMPAIGN
    assert mapped.campaign_id is None
    assert mapped.world_id == "eldyrwild"


def test_assertion_view_preserves_non_property_kinds_and_temporal_payload():
    metadata = SimpleNamespace(
        epistemic_kind="asserted",
        visibility="gm",
        campaign_scope=None,
        temporal_scope=SimpleNamespace(
            model_dump=lambda mode="json": {
                "schema_version": "dm_temporal_scope_ref_v1",
                "kind": "world_timeless",
            }
        ),
    )
    existence = AdmittedAssertionValue(
        assertion_id="asrt:exists",
        subject_object_id="pc:karsemine",
        assertion_kind="existence",
        evidence_ref_ids=("ev:s25",),
        assertion_metadata=metadata,  # type: ignore[arg-type]
    )
    alias = AdmittedAssertionValue(
        assertion_id="asrt:alias",
        subject_object_id="pc:karsemine",
        assertion_kind="alias",
        evidence_ref_ids=("ev:s25",),
        assertion_metadata=metadata,  # type: ignore[arg-type]
        alias="Karsemine",
    )
    existence_view = _complete_object_attribute_view(existence, evidence_by_id={})
    alias_view = _complete_object_attribute_view(alias, evidence_by_id={})
    assert existence_view.assertion_kind == "existence"
    assert existence_view.temporal_scope == {
        "schema_version": "dm_temporal_scope_ref_v1",
        "kind": "world_timeless",
    }
    assert alias_view.assertion_kind == "alias"
    assert alias_view.alias == "Karsemine"
    assert alias_view.text_value == "Karsemine"


def _assertion(*, assertion_id: str, temporal_kind: str) -> WorldGraphObjectProjectionAssertion:
    return WorldGraphObjectProjectionAssertion(
        assertion_id=assertion_id,
        subject_node_id="pc:karsemine",
        assertion_kind="property",
        temporal_scope={
            "schema_version": "dm_temporal_scope_ref_v1",
            "kind": temporal_kind,
        },
    )


def _relationship(*, temporal_kind: str) -> WorldGraphObjectProjectionRelationship:
    return WorldGraphObjectProjectionRelationship(
        edge_id="rel:holds",
        source_node_id="pc:karsemine",
        target_node_id="item:hunters-mark",
        predicate="holds",
        label="holds",
        direction="outgoing",
        temporal_scope={
            "schema_version": "dm_temporal_scope_ref_v1",
            "kind": temporal_kind,
        },
    )


def test_semantic_fingerprint_changes_when_temporal_payload_differs():
    first = object_projection_semantic_fingerprint(
        revision_id="rev:1",
        node_id="pc:karsemine",
        admissibility="gm",
        related_node_ids=["item:hunters-mark"],
        source_bindings=[],
        assertions=[_assertion(assertion_id="asrt:a", temporal_kind="unknown")],
        relationships=[_relationship(temporal_kind="unknown")],
    )
    second = object_projection_semantic_fingerprint(
        revision_id="rev:1",
        node_id="pc:karsemine",
        admissibility="gm",
        related_node_ids=["item:hunters-mark"],
        source_bindings=[],
        assertions=[_assertion(assertion_id="asrt:a", temporal_kind="world_timeless")],
        relationships=[_relationship(temporal_kind="world_timeless")],
    )
    assert first != second


def test_apply_durable_bindings_hydrates_exact_digest_not_latest():
    result = WorldGraphObjectProjectionResult(
        found=True,
        completeness=SelectedObjectCompletenessView(status="complete"),
        requested_node_id="pc:karsemine",
        source_bindings=[
            WorldGraphObjectProjectionSourceBinding(
                evidence_ref_id="ev:s24",
                source_artifact_id="artifact:s24",
                content_sha256="aaa",
                source_span_ref_id="src:s24:paragraph:1",
                provenance_status="span_unresolvable",
            ),
            WorldGraphObjectProjectionSourceBinding(
                evidence_ref_id="ev:s25",
                source_artifact_id="artifact:s25",
                content_sha256="bbb",
                source_span_ref_id="src:s25:paragraph:1",
                provenance_status="span_unresolvable",
            ),
        ],
    )

    class _Record:
        def __init__(self, markdown: str, media_type: str = "text/markdown") -> None:
            self.markdown = markdown
            self.media_type = media_type

    records = {
        ("artifact:s24", "aaa"): _Record("S24 Hunter's Mark paragraph.\n\nMore."),
        ("artifact:s25", "bbb"): _Record("S25 Lysandra paragraph.\n\nMore."),
    }
    updated = _apply_durable_bindings(result, records=records)
    by_id = {row.evidence_ref_id: row for row in updated}
    assert by_id["ev:s24"].provenance_status == "excerpt_ready"
    assert by_id["ev:s25"].provenance_status == "excerpt_ready"
    assert by_id["ev:s24"].excerpt == "S24 Hunter's Mark paragraph."
    assert by_id["ev:s25"].excerpt == "S25 Lysandra paragraph."


def test_source_markdown_batch_is_one_query_for_multiple_bindings(
    application_state_dsn: str,
) -> None:
    s24 = persist_source_markdown(
        source_artifact_id="artifact:recap:longmont-c2:session-24:objproj",
        source_domain="recap",
        campaign_id="longmont-c2",
        session_id="session-24",
        world_id="eldyrwild",
        markdown="# S24\n\nHunter's Mark.\n",
    )
    s25 = persist_source_markdown(
        source_artifact_id="artifact:recap:longmont-c2:session-25:objproj",
        source_domain="recap",
        campaign_id="longmont-c2",
        session_id="session-25",
        world_id="eldyrwild",
        markdown="# S25\n\nLysandra.\n",
    )
    loaded = get_source_markdown_batch(
        bindings=[
            (s24.source_artifact_id, s24.content_sha256),
            (s25.source_artifact_id, s25.content_sha256),
            (s24.source_artifact_id, s24.content_sha256),
            ("artifact:missing", "0" * 64),
        ]
    )
    assert len(loaded) == 2
    assert loaded[(s24.source_artifact_id, s24.content_sha256)].session_id == "session-24"
    assert loaded[(s25.source_artifact_id, s25.content_sha256)].session_id == "session-25"
    assert ( "artifact:missing", "0" * 64) not in loaded
    assert UUID(str(s24.source_revision_id))


def test_agent_generic_scope_mode_default_remains_campaign():
    request = AgentWorldGraphQueryContextRequest.model_validate(
        {
            "schema": "dmb_agent_world_graph_query_context_request_v1",
            "world_id": "eldyrwild",
            "campaign_id": "longmont-c2",
        }
    )
    assert request.scope_mode == "campaign"
    assert request.selected_node_id is None


def test_agent_selected_node_id_does_not_change_generic_scope_default():
    request = AgentWorldGraphQueryContextRequest.model_validate(
        {
            "schema": "dmb_agent_world_graph_query_context_request_v1",
            "world_id": "eldyrwild",
            "campaign_id": "longmont-c2",
            "selected_node_id": "pc:karsemine",
        }
    )
    assert request.selected_node_id == "pc:karsemine"
    assert request.scope_mode == "campaign"


def test_complete_object_player_admissibility_maps_fail_closed():
    binding = DirectAuthorityBinding(
        world_id="eldyrwild",
        dungeonmind_first_revision_id="rev:da",
        dungeonmind_head_revision_id="rev:head",
        legacy_buddy_revision_id=None,
        genesis="reviewed_world_initialization",
    )
    mapped = _map_complete_object_context(
        _request(admissibility="player"),
        binding,
    )
    assert mapped.admissibility is Admissibility.PLAYER
    assert mapped.scope_mode is ScopeModeV2.WORLD_CROSS_CAMPAIGN
    assert mapped.campaign_id is None


def test_complete_object_relationship_direction_incoming_and_outgoing():
    temporal = SimpleNamespace(
        model_dump=lambda mode="json": {
            "schema_version": "dm_temporal_scope_ref_v1",
            "kind": "unknown",
            "source_time": {"kind": "session", "session_id": "session-24"},
            "occurrence_time": None,
            "valid_time": None,
        }
    )
    metadata = SimpleNamespace(
        visibility="gm",
        campaign_scope="longmont-c1",
        epistemic_kind="asserted",
        temporal_scope=temporal,
        session_refs=(),
    )
    outgoing = _complete_object_relationship_view(
        cast(
            GraphRelationshipView,
            SimpleNamespace(
                relationship_id="rel:out",
                subject_object_id="pc:karsemine",
                object_object_id="item:hunters-mark",
                predicate="holds",
                evidence_ref_ids=("ev:s24",),
                assertion_metadata=metadata,
            ),
        ),
        selected_object_id="pc:karsemine",
        evidence_by_id={},
    )
    incoming = _complete_object_relationship_view(
        cast(
            GraphRelationshipView,
            SimpleNamespace(
                relationship_id="rel:in",
                subject_object_id="npc:lysandra",
                object_object_id="pc:karsemine",
                predicate="allied_with",
                evidence_ref_ids=("ev:s25",),
                assertion_metadata=metadata,
            ),
        ),
        selected_object_id="pc:karsemine",
        evidence_by_id={},
    )
    assert outgoing.direction == "outgoing"
    assert incoming.direction == "incoming"
    assert outgoing.temporal_scope is not None
    assert outgoing.temporal_scope["source_time"]["session_id"] == "session-24"
    assert incoming.campaign_scope == "longmont-c1"


def test_partial_completeness_cannot_masquerade_as_complete():
    result = WorldGraphObjectProjectionResult(
        found=True,
        completeness=SelectedObjectCompletenessView(
            status="partial",
            reason="relationships_truncated",
            truncated_fields=["relationships"],
        ),
        requested_node_id="pc:karsemine",
    )
    assert result.completeness.status == "partial"
    assert result.completeness.truncated_fields == ["relationships"]
    dumped = result.model_dump(mode="json", by_alias=True)
    assert dumped["completeness"]["status"] == "partial"
    assert dumped["completeness"]["truncatedFields"] == ["relationships"]


def test_missing_durable_source_leaves_fact_visible_without_excerpt():
    result = WorldGraphObjectProjectionResult(
        found=True,
        completeness=SelectedObjectCompletenessView(status="complete"),
        requested_node_id="pc:karsemine",
        source_bindings=[
            WorldGraphObjectProjectionSourceBinding(
                evidence_ref_id="ev:manual",
                source_artifact_id="artifact:manual-seed",
                content_sha256="ccc",
                source_span_ref_id="src:manual:paragraph:1",
                provenance_status="span_unresolvable",
            ),
            WorldGraphObjectProjectionSourceBinding(
                evidence_ref_id="ev:no-span",
                source_artifact_id="artifact:s25",
                content_sha256="bbb",
                source_span_ref_id=None,
                provenance_status="no_source_span",
            ),
        ],
    )
    updated = _apply_durable_bindings(
        result,
        records={
            ("artifact:s25", "bbb"): SimpleNamespace(
                markdown="S25 Lysandra paragraph.\n",
                media_type="text/markdown",
            ),
        },
    )
    by_id = {row.evidence_ref_id: row for row in updated}
    assert by_id["ev:manual"].provenance_status == "source_not_durable"
    assert by_id["ev:manual"].excerpt is None
    assert by_id["ev:no-span"].provenance_status == "no_source_span"
    assert by_id["ev:no-span"].excerpt is None


def _snapshot() -> WorldGraphProjectionSnapshot:
    return WorldGraphProjectionSnapshot(
        world_id="eldyrwild",
        campaign_id="longmont-c2",
        revision_id="rev:1",
        head_revision_id="rev:1",
        is_head=True,
        focus=WorldGraphProjectionFocus(kind="none", session_id=None),
        admissibility="gm",
        scope_mode="world",
    )


def _node(node_id: str = "pc:karsemine") -> WorldGraphProjectionNodeView:
    return WorldGraphProjectionNodeView(
        node_id=node_id,
        label="Karsemine",
        kind="pc",
        role="pc",
    )


def test_semantic_fingerprint_is_origin_surface_neutral():
    ingest = object_projection_semantic_fingerprint(
        revision_id="rev:1",
        node_id="pc:karsemine",
        admissibility="gm",
        assertions=[_assertion(assertion_id="asrt:a", temporal_kind="unknown")],
        relationships=[_relationship(temporal_kind="unknown")],
        related_node_ids=["item:hunters-mark"],
        source_bindings=[],
    )
    plan = object_projection_semantic_fingerprint(
        revision_id="rev:1",
        node_id="pc:karsemine",
        admissibility="gm",
        assertions=[_assertion(assertion_id="asrt:a", temporal_kind="unknown")],
        relationships=[_relationship(temporal_kind="unknown")],
        related_node_ids=["item:hunters-mark"],
        source_bindings=[],
    )
    assert ingest == plan


def test_agent_selected_object_uses_complete_object_not_generic_projection(monkeypatch):
    complete = WorldGraphObjectProjectionResult(
        found=True,
        completeness=SelectedObjectCompletenessView(
            status="partial",
            reason="assertions_truncated",
            truncated_fields=["assertions"],
        ),
        snapshot=_snapshot(),
        requested_node_id="pc:karsemine",
        resolved_node_id="pc:karsemine",
        node=_node(),
        relationships=[
            _relationship(temporal_kind="unknown").model_copy(
                update={
                    "evidence_ref_ids": ["ev:s24"],
                    "temporal_scope": {
                        "schema_version": "dm_temporal_scope_ref_v1",
                        "kind": "unknown",
                        "valid_time": {"kind": "open"},
                    },
                }
            )
        ],
        assertions=[
            _assertion(assertion_id="asrt:a", temporal_kind="unknown").model_copy(
                update={"evidence_ref_ids": ["ev:s24"]}
            )
        ],
        source_bindings=[
            WorldGraphObjectProjectionSourceBinding(
                evidence_ref_id="ev:s24",
                source_artifact_id="artifact:s24",
                source_revision_id="rev-src-24",
                content_sha256="aaa",
                session_id="session-24",
                provenance_status="excerpt_ready",
                excerpt="Hunter's Mark is visible in S24.",
            ),
            WorldGraphObjectProjectionSourceBinding(
                evidence_ref_id="ev:manual",
                source_artifact_id="artifact:manual-seed",
                provenance_status="source_not_durable",
            ),
        ],
        semantic_fingerprint="fp-selected",
    )
    calls = {"complete": 0, "generic": 0}

    def fake_complete(request, *, root=None, source_batch_fn=None):
        calls["complete"] += 1
        assert request.node_id == "pc:karsemine"
        assert request.origin_surface == "agent"
        return complete

    def fake_generic(*_args, **_kwargs):
        calls["generic"] += 1
        raise AssertionError("generic projection must not run for selected-object context")

    monkeypatch.setattr(
        "apps.live_control_server.services.agent_world_graph_query_context.project_complete_world_object",
        fake_complete,
    )
    envelope = resolve_agent_world_graph_query_context(
        AgentWorldGraphQueryContextRequest.model_validate(
            {
                "schema": "dmb_agent_world_graph_query_context_request_v1",
                "world_id": "eldyrwild",
                "campaign_id": "longmont-c2",
                "selected_node_id": "pc:karsemine",
                "scope_mode": "campaign",
            }
        ),
        outer_text="What does the World know about Karsemine?",
        outer_campaign_id="longmont-c2",
        project_fn=fake_generic,
    )
    assert calls == {"complete": 1, "generic": 0}
    assert envelope["scope_mode"] == "world"
    assert envelope["retrieval_scope_mode"] == "campaign"
    assert envelope["completeness"] == "partial"
    assert envelope["truncated_fields"] == ["assertions"]
    assert envelope["semantic_fingerprint"] == "fp-selected"
    assert envelope["relationships"][0]["temporal_scope"]["valid_time"] == {
        "kind": "open"
    }
    assert envelope["relationships"][0]["evidence_ref_ids"] == ["ev:s24"]
    assert envelope["attributes"][0]["evidence_ref_ids"] == ["ev:s24"]
    assert envelope["source_bindings"][0]["provenance_status"] == "excerpt_ready"
    assert envelope["source_bindings"][0]["excerpt_included"] is True
    assert envelope["source_bindings"][1]["excerpt_included"] is False
    assert envelope["source_bindings"][1]["excerpt_omission_reason"] == "excerpt_not_ready"
    assert envelope["excerpt_policy"] == "provenance_context_not_citation"

    prompt = render_world_graph_prompt_block(envelope)
    assert "temporal_scope=" in prompt
    assert '"valid_time": {"kind": "open"}' in prompt
    assert "evidence_ref_ids=ev:s24" in prompt
    assert "status=excerpt_ready" in prompt
    assert "Hunter's Mark is visible in S24." in prompt
    assert "excerpt_omitted=excerpt_not_ready" in prompt
    assert "retrieval_scope_mode: campaign" in prompt
    assert "scope_mode: world" in prompt
    assert "completeness: partial" in prompt
    assert "provenance context, not citation authority" in prompt


def test_agent_without_selected_node_keeps_generic_projection(monkeypatch):
    calls = {"complete": 0}

    def fake_complete(*_args, **_kwargs):
        calls["complete"] += 1
        raise AssertionError("complete-object must not run without selected_node_id")

    monkeypatch.setattr(
        "apps.live_control_server.services.agent_world_graph_query_context.project_complete_world_object",
        fake_complete,
    )

    class _Projection:
        snapshot = SimpleNamespace(
            world_id="eldyrwild",
            campaign_id="longmont-c2",
            revision_id="rev:1",
            head_revision_id="rev:1",
            is_head=True,
            focus=SimpleNamespace(kind="none", session_id=None, campaign_id=None),
            admissibility="gm",
            scope_mode="campaign",
        )
        nodes = []
        relationships = []
        attributes = []
        summary = SimpleNamespace(
            node_count=0,
            relationship_count=0,
            attribute_count=0,
            projection_truncated=False,
        )
        diagnostics = []
        query_context = None

    envelope = resolve_agent_world_graph_query_context(
        AgentWorldGraphQueryContextRequest.model_validate(
            {
                "schema": "dmb_agent_world_graph_query_context_request_v1",
                "world_id": "eldyrwild",
                "campaign_id": "longmont-c2",
            }
        ),
        outer_text="Where is the tavern?",
        outer_campaign_id="longmont-c2",
        project_fn=lambda *_args, **_kwargs: _Projection(),
    )
    assert calls["complete"] == 0
    assert envelope["scope_mode"] == "campaign"
    assert envelope["status"] in {"empty", "ready", "unavailable"}

