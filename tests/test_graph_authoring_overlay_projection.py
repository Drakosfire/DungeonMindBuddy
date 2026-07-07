"""Tests for authored overlay projection into graph review payloads."""

from __future__ import annotations

from pathlib import Path

import pytest

from apps.live_control_server.models.graph_authoring_overlay import (
    GraphAuthoringSourceAnchor,
    create_empty_authored_graph_overlay,
)
from apps.live_control_server.services.graph_authoring_overlay_projection import (
    AuthoredOverlayProjectionSummary,
    apply_authored_overlay_to_graph_review_projection,
    authored_manual_node_id,
    authored_object_node_id,
    build_authored_projection_node_views,
    enrich_projection_payload_with_authored_overlay,
    load_authored_overlay_for_review,
)
from apps.live_control_server.services.graph_authoring_visibility import GraphAudience
from apps.live_control_server.services.graph_authoring_overlay_store import GraphAuthoringOverlayStore
from graph_memory.projection.focus_overlay import GraphFocusOverlay
from graph_memory.projection.node_view import GraphProjectionNodeView
from graph_memory.projection.recap_projection import RecapGraphProjection
from tests.test_graph_authoring_overlay_models import (
    CAMPAIGN_ID,
    STAMP,
    link_existing_assertion,
    object_assertion,
    relationship_assertion,
)

TEST_CAMPAIGN_REL = "Test Campaign/A6"


@pytest.fixture
def corpus_root(tmp_path: Path) -> Path:
    return tmp_path / "corpus"


@pytest.fixture
def store(corpus_root: Path) -> GraphAuthoringOverlayStore:
    return GraphAuthoringOverlayStore(corpus_root)


def _empty_projection() -> RecapGraphProjection:
    return RecapGraphProjection(
        campaign_id=CAMPAIGN_ID,
        session_id="session-1",
        graph_id="graph-1",
        markdown="# Recap",
        focus=GraphFocusOverlay(focus_session_id="session-1"),
        node_views={
            "pc_bonogo": GraphProjectionNodeView(
                node_id="pc_bonogo",
                label="Bonogo",
                kind="pc",
                role="candidate",
                aliases=[],
                source_domains=["live_projection"],
                evidence_badges=[],
                adjacency=[],
            )
        },
        mentions=[],
        source_spans=[],
    )


def test_missing_overlay_is_safe(store: GraphAuthoringOverlayStore) -> None:
    overlay, summary = load_authored_overlay_for_review(
        campaign_id=CAMPAIGN_ID,
        campaign_rel=TEST_CAMPAIGN_REL,
        corpus_root=store.corpus_root,
    )
    assert overlay is None
    assert summary.loaded is False
    assert any(item.code == "authored_overlay_missing" for item in summary.diagnostics)


def test_object_assertion_becomes_node_view(store: GraphAuthoringOverlayStore) -> None:
    assertion = object_assertion(
        assertion_id="assert-qc",
        object_ref={
            "ref_kind": "local_proposal",
            "local_proposal_id": "local-qc",
            "label": "Questionable Company",
            "kind": "party",
            "role": "authored",
        },
        aliases=["gang"],
    )
    overlay = create_empty_authored_graph_overlay(CAMPAIGN_ID, created_at=STAMP).model_copy(
        update={"assertions": [assertion]}
    )
    store.save_overlay(overlay, campaign_rel=TEST_CAMPAIGN_REL)

    projection = _empty_projection()
    loaded, summary = load_authored_overlay_for_review(
        campaign_id=CAMPAIGN_ID,
        campaign_rel=TEST_CAMPAIGN_REL,
        corpus_root=store.corpus_root,
    )
    assert loaded is not None
    assert summary.loaded is True
    enriched, overlay_summary = apply_authored_overlay_to_graph_review_projection(
        projection,
        loaded,
        summary=summary,
    )
    node_id = authored_object_node_id("assert-qc")
    assert node_id in enriched.node_views
    node = enriched.node_views[node_id]
    assert node.label == "Questionable Company"
    assert node.kind == "party"
    assert "gang" in node.aliases
    assert node.source_domains == ["authored_overlay"]
    assert getattr(node, "authored") is True
    assert overlay_summary.projected_node_count >= 1


def test_retracted_assertion_not_projected(store: GraphAuthoringOverlayStore) -> None:
    active = object_assertion(assertion_id="assert-active")
    retracted = object_assertion(
        assertion_id="assert-retracted",
        status="retracted",
        object_ref={
            "ref_kind": "local_proposal",
            "local_proposal_id": "local-hidden",
            "label": "Hidden Object",
            "kind": "entity",
        },
    )
    overlay = create_empty_authored_graph_overlay(CAMPAIGN_ID, created_at=STAMP).model_copy(
        update={"assertions": [active, retracted]}
    )
    store.save_overlay(overlay, campaign_rel=TEST_CAMPAIGN_REL)
    loaded, _ = load_authored_overlay_for_review(
        campaign_id=CAMPAIGN_ID,
        campaign_rel=TEST_CAMPAIGN_REL,
        corpus_root=store.corpus_root,
    )
    enriched, summary = apply_authored_overlay_to_graph_review_projection(
        _empty_projection(),
        loaded,
    )
    assert authored_object_node_id("assert-active") in enriched.node_views
    assert authored_object_node_id("assert-retracted") not in enriched.node_views
    assert summary.assertion_count == 1


def test_link_existing_attaches_alias_to_existing_node(store: GraphAuthoringOverlayStore) -> None:
    link = link_existing_assertion(
        existing_object_ref={
            "ref_kind": "existing_graph_node",
            "node_id": "pc_bonogo",
            "label": "Bonogo",
            "kind": "pc",
        },
        alias_text="Bono",
    )
    overlay = create_empty_authored_graph_overlay(CAMPAIGN_ID, created_at=STAMP).model_copy(
        update={"assertions": [link]}
    )
    node_views = build_authored_projection_node_views(
        overlay,
        base_node_views=_empty_projection().node_views,
        existing_node_ids=set(_empty_projection().node_views.keys()),
    )
    assert "pc_bonogo" in node_views
    assert "Bono" in node_views["pc_bonogo"].aliases
    assert "authored_overlay" in node_views["pc_bonogo"].source_domains


def test_manual_link_existing_becomes_authored_manual_node() -> None:
    link = link_existing_assertion(
        existing_object_ref={
            "ref_kind": "manual_ref",
            "label": "Mystery Group",
            "kind": "party",
        }
    )
    overlay = create_empty_authored_graph_overlay(CAMPAIGN_ID, created_at=STAMP).model_copy(
        update={"assertions": [link]}
    )
    node_views = build_authored_projection_node_views(overlay)
    manual_id = authored_manual_node_id("Mystery Group", "party")
    assert manual_id in node_views
    assert node_views[manual_id].label == "Mystery Group"


def test_relationship_assertion_adds_adjacency(store: GraphAuthoringOverlayStore) -> None:
    object_a = object_assertion(
        assertion_id="assert-qc",
        object_ref={
            "ref_kind": "local_proposal",
            "local_proposal_id": "local-qc",
            "label": "Questionable Company",
            "kind": "party",
        },
    )
    rel = relationship_assertion(
        source_object_ref={
            "ref_kind": "local_proposal",
            "local_proposal_id": "local-qc",
            "label": "Questionable Company",
            "kind": "party",
        },
        target_object_ref={
            "ref_kind": "existing_graph_node",
            "node_id": "pc_bonogo",
            "label": "Bonogo",
            "kind": "pc",
        },
    )
    overlay = create_empty_authored_graph_overlay(CAMPAIGN_ID, created_at=STAMP).model_copy(
        update={"assertions": [object_a, rel]}
    )
    store.save_overlay(overlay, campaign_rel=TEST_CAMPAIGN_REL)
    payload = enrich_projection_payload_with_authored_overlay(
        _empty_projection().model_dump(mode="json"),
        campaign_id=CAMPAIGN_ID,
        campaign_rel=TEST_CAMPAIGN_REL,
        corpus_root=store.corpus_root,
    )
    source_id = authored_object_node_id("assert-qc")
    source_node = payload["node_views"][source_id]
    assert source_node["adjacency"]
    assert source_node["adjacency"][0]["node_id"] == "pc_bonogo"
    assert source_node["adjacency"][0]["predicate"] == "has_member"
    assert payload["authored_overlay"]["projected_relationship_count"] == 1


def test_existing_extracted_nodes_preserved(store: GraphAuthoringOverlayStore) -> None:
    overlay = create_empty_authored_graph_overlay(CAMPAIGN_ID, created_at=STAMP).model_copy(
        update={"assertions": [object_assertion(assertion_id="assert-new")]}
    )
    store.save_overlay(overlay, campaign_rel=TEST_CAMPAIGN_REL)
    payload = enrich_projection_payload_with_authored_overlay(
        _empty_projection().model_dump(mode="json"),
        campaign_id=CAMPAIGN_ID,
        campaign_rel=TEST_CAMPAIGN_REL,
        corpus_root=store.corpus_root,
    )
    assert "pc_bonogo" in payload["node_views"]
    assert payload["node_views"]["pc_bonogo"]["label"] == "Bonogo"


def test_authored_node_ids_are_stable() -> None:
    assertion = object_assertion(assertion_id="assert-stable-id")
    overlay = create_empty_authored_graph_overlay(CAMPAIGN_ID, created_at=STAMP).model_copy(
        update={"assertions": [assertion]}
    )
    first = build_authored_projection_node_views(overlay)
    second = build_authored_projection_node_views(overlay)
    assert list(first.keys()) == list(second.keys()) == [authored_object_node_id("assert-stable-id")]


def test_link_existing_materializes_external_existing_graph_node() -> None:
    link = link_existing_assertion(
        existing_object_ref={
            "ref_kind": "existing_graph_node",
            "node_id": "node:lysandro",
            "label": "Lysandro",
            "kind": "character",
        },
        selected_text="well dressed man in his mid 50s",
        normalized_selected_text="well dressed man in his mid 50s",
    )
    overlay = create_empty_authored_graph_overlay(CAMPAIGN_ID, created_at=STAMP).model_copy(
        update={"assertions": [link]}
    )
    diagnostics: list = []
    node_views = build_authored_projection_node_views(
        overlay,
        base_node_views={},
        existing_node_ids=set(),
        diagnostics=diagnostics,
    )
    assert "node:lysandro" in node_views
    assert node_views["node:lysandro"].label == "Lysandro"
    assert "well dressed man in his mid 50s" in node_views["node:lysandro"].aliases
    assert not any(item.code == "authored_overlay_assertion_unresolved_ref" for item in diagnostics)


def test_unresolved_link_existing_without_node_id_does_not_create_phantom_node() -> None:
    link = link_existing_assertion(
        existing_object_ref={
            "ref_kind": "existing_graph_node",
            "node_id": None,
            "label": "Ghost",
            "kind": "entity",
        },
    )
    overlay = create_empty_authored_graph_overlay(CAMPAIGN_ID, created_at=STAMP).model_copy(
        update={"assertions": [link]}
    )
    diagnostics: list = []
    node_views = build_authored_projection_node_views(
        overlay,
        base_node_views={},
        existing_node_ids=set(),
        diagnostics=diagnostics,
    )
    assert node_views == {}
    assert any(item.code == "authored_overlay_assertion_unresolved_ref" for item in diagnostics)


def test_malformed_overlay_returns_schema_error_diagnostic(store: GraphAuthoringOverlayStore) -> None:
    overlay_path = store.overlay_path(CAMPAIGN_ID, campaign_rel=TEST_CAMPAIGN_REL)
    overlay_path.parent.mkdir(parents=True, exist_ok=True)
    overlay_path.write_text(
        (
            '{"schema_version":"dmb.authored_graph_overlay.v1",'
            '"campaign_id":"longmont-c1",'
            '"created_at":"2026-07-06T12:00:00Z",'
            '"updated_at":"2026-07-06T12:00:00Z",'
            '"assertions":[{"assertion_id":"bad","status":"not-valid"}]}'
        ),
        encoding="utf-8",
    )
    overlay, summary = load_authored_overlay_for_review(
        campaign_id=CAMPAIGN_ID,
        campaign_rel=TEST_CAMPAIGN_REL,
        corpus_root=store.corpus_root,
    )
    assert overlay is None
    assert summary.loaded is False
    assert any(item.code == "authored_overlay_schema_error" for item in summary.diagnostics)


def _gang_projection() -> RecapGraphProjection:
    return RecapGraphProjection(
        campaign_id=CAMPAIGN_ID,
        session_id="session-2",
        graph_id="graph-1",
        markdown="# Session 2 Recap\n\nThe gang survived.",
        focus=GraphFocusOverlay(focus_session_id="session-2"),
        node_views={
            "group_the_group": GraphProjectionNodeView(
                node_id="group_the_group",
                label="the group",
                kind="group",
                role="group",
                aliases=["the group"],
                source_domains=["live_projection"],
                evidence_badges=[],
                adjacency=[],
            )
        },
        mentions=[],
        source_spans=[],
    )


def test_object_source_anchor_adds_authored_projection_mention() -> None:
    assertion = object_assertion(
        assertion_id="assert-well-dressed",
        object_ref={
            "ref_kind": "local_proposal",
            "local_proposal_id": "local-well-dressed",
            "label": "well dressed man in his mid 50s",
            "kind": "npc",
            "role": "npc",
        },
        aliases=["Lysandro"],
        source_anchor={
            "anchor_kind": "text_span",
            "selected_text": "well dressed man in his mid 50s",
            "normalized_selected_text": "well dressed man in his mid 50s",
            "surrounding_text_before": "A ",
            "surrounding_text_after": " arrived.",
        },
    )
    projection = RecapGraphProjection(
        campaign_id=CAMPAIGN_ID,
        session_id="session-2",
        graph_id="graph-1",
        markdown="# Recap\n\nA well dressed man in his mid 50s arrived.",
        focus=GraphFocusOverlay(focus_session_id="session-2"),
        node_views={
            "lysandro": GraphProjectionNodeView(
                node_id="lysandro",
                label="Lysandro",
                kind="npc",
                role="npc",
                aliases=[],
                source_domains=["live_projection"],
                evidence_badges=[],
                adjacency=[],
            )
        },
        mentions=[],
        source_spans=[],
    )
    overlay = create_empty_authored_graph_overlay(CAMPAIGN_ID, created_at=STAMP).model_copy(
        update={"assertions": [assertion]}
    )
    enriched, summary = apply_authored_overlay_to_graph_review_projection(projection, overlay)
    node_id = authored_object_node_id("assert-well-dressed")
    assert node_id in enriched.node_views
    assert any(item.node_id == node_id for item in enriched.mentions)
    assert enriched.markdown is not None
    assert f"dmb-node:{node_id}" in enriched.markdown
    assert summary.projected_node_count == 1


def test_link_existing_alias_adds_authored_projection_mention() -> None:
    link = link_existing_assertion(
        assertion_id="assert-gang",
        selected_text="gang",
        normalized_selected_text="gang",
        existing_object_ref={
            "ref_kind": "existing_graph_node",
            "node_id": "group_the_group",
            "label": "the group",
            "kind": "group",
        },
        source_anchor={
            "anchor_kind": "text_span",
            "selected_text": "gang",
            "normalized_selected_text": "gang",
            "surrounding_text_before": "The ",
            "surrounding_text_after": " survived.",
        },
    )
    overlay = create_empty_authored_graph_overlay(CAMPAIGN_ID, created_at=STAMP).model_copy(
        update={"assertions": [link]}
    )
    enriched, summary = apply_authored_overlay_to_graph_review_projection(
        _gang_projection(),
        overlay,
    )
    assert enriched.markdown is not None
    assert "[gang](dmb-node:group_the_group)" in enriched.markdown
    assert enriched.markdown.startswith("# Session 2 Recap")
    assert any(
        mention.label == "gang" and mention.node_id == "group_the_group"
        for mention in enriched.mentions
    )
    assert summary.projected_link_existing_count == 1
    assert summary.projected_node_count == 0


def test_link_existing_alias_mention_materializes_external_existing_node() -> None:
    markdown = (
        "# Session 23 Recap\n\n"
        "On top of the wall is a well dressed man in his mid 50s with an old worn military coat."
    )
    projection = RecapGraphProjection(
        campaign_id=CAMPAIGN_ID,
        session_id="session-23",
        graph_id="graph-1",
        markdown=markdown,
        focus=GraphFocusOverlay(focus_session_id="session-23"),
        node_views={},
        mentions=[],
        source_spans=[],
    )
    link = link_existing_assertion(
        assertion_id="assert-lysandro-alias",
        selected_text="well dressed man in his mid 50s",
        normalized_selected_text="well dressed man in his mid 50s",
        existing_object_ref={
            "ref_kind": "existing_graph_node",
            "node_id": "node:lysandro",
            "label": "Lysandro",
            "kind": "character",
        },
        source_anchor={
            "anchor_kind": "text_span",
            "selected_text": "well dressed man in his mid 50s",
            "normalized_selected_text": "well dressed man in his mid 50s",
            "surrounding_text_before": "On top of the wall is a ",
            "surrounding_text_after": " with an old worn military coat.",
            "paragraph_ordinal": 2,
        },
    )
    overlay = create_empty_authored_graph_overlay(CAMPAIGN_ID, created_at=STAMP).model_copy(
        update={"assertions": [link]}
    )
    enriched, summary = apply_authored_overlay_to_graph_review_projection(projection, overlay)
    assert enriched.markdown is not None
    assert "[well dressed man in his mid 50s](dmb-node:node:lysandro)" in enriched.markdown
    assert "node:lysandro" in enriched.node_views
    assert any(
        mention.label == "well dressed man in his mid 50s" and mention.node_id == "node:lysandro"
        for mention in enriched.mentions
    )
    assert not any(
        item.code == "authored_overlay_assertion_unresolved_ref"
        and "node:lysandro" in item.message
        for item in summary.diagnostics
    )


def test_link_existing_alias_mention_targets_existing_node() -> None:
    link = link_existing_assertion(
        existing_object_ref={
            "ref_kind": "existing_graph_node",
            "node_id": "group_the_group",
            "label": "the group",
            "kind": "group",
        },
    )
    overlay = create_empty_authored_graph_overlay(CAMPAIGN_ID, created_at=STAMP).model_copy(
        update={"assertions": [link]}
    )
    enriched, _ = apply_authored_overlay_to_graph_review_projection(_gang_projection(), overlay)
    mention = next(item for item in enriched.mentions if item.node_id == "group_the_group")
    assert mention.label == "gang"
    assert getattr(mention, "authored") is True
    assert getattr(mention, "source") == "authored_overlay"
    assert getattr(mention, "target_label") == "the group"


def test_link_existing_alias_mention_preserves_source_markdown_semantics() -> None:
    projection = _gang_projection()
    original = projection.markdown
    link = link_existing_assertion(
        existing_object_ref={
            "ref_kind": "existing_graph_node",
            "node_id": "group_the_group",
            "label": "the group",
            "kind": "group",
        },
    )
    overlay = create_empty_authored_graph_overlay(CAMPAIGN_ID, created_at=STAMP).model_copy(
        update={"assertions": [link]}
    )
    enriched, _ = apply_authored_overlay_to_graph_review_projection(projection, overlay)
    assert original is not None
    assert "The gang survived." in original.replace("\n\n", " ").replace("\n", " ") or "gang" in original
    assert enriched.markdown is not None
    assert "gang" in enriched.markdown
    assert "The " in enriched.markdown
    assert "survived." in enriched.markdown


def test_link_existing_alias_mention_respects_visibility_audience() -> None:
    from apps.live_control_server.models.graph_authoring_overlay import GraphVisibilityPolicy

    link = link_existing_assertion(
        visibility=GraphVisibilityPolicy(visibility="gm_private").model_dump(),
        existing_object_ref={
            "ref_kind": "existing_graph_node",
            "node_id": "group_the_group",
            "label": "the group",
            "kind": "group",
        },
    )
    overlay = create_empty_authored_graph_overlay(CAMPAIGN_ID, created_at=STAMP).model_copy(
        update={"assertions": [link]}
    )
    gm_enriched, gm_summary = apply_authored_overlay_to_graph_review_projection(
        _gang_projection(),
        overlay,
        audience=GraphAudience(audience_kind="gm"),
    )
    table_enriched, table_summary = apply_authored_overlay_to_graph_review_projection(
        _gang_projection(),
        overlay,
        audience=GraphAudience(audience_kind="table"),
    )
    assert any(item.node_id == "group_the_group" for item in gm_enriched.mentions)
    assert not any(item.node_id == "group_the_group" for item in table_enriched.mentions)
    assert gm_summary.projected_link_existing_count == 1
    assert table_summary.projected_link_existing_count == 0


def test_link_existing_alias_mention_does_not_duplicate_existing_same_span_same_node() -> None:
    projection = RecapGraphProjection(
        campaign_id=CAMPAIGN_ID,
        session_id="session-2",
        graph_id="graph-1",
        markdown="# Session 2 Recap\n\nThe [gang](dmb-node:group_the_group) survived.",
        focus=GraphFocusOverlay(focus_session_id="session-2"),
        node_views={
            "group_the_group": GraphProjectionNodeView(
                node_id="group_the_group",
                label="the group",
                kind="group",
                role="group",
                aliases=["the group"],
                source_domains=["live_projection"],
                evidence_badges=[],
                adjacency=[],
            )
        },
        mentions=[
            {
                "mention_id": "mention:group_the_group:0",
                "node_id": "group_the_group",
                "label": "gang",
                "start_offset": 0,
                "end_offset": 0,
            }
        ],
        source_spans=[],
    )
    link = link_existing_assertion(
        existing_object_ref={
            "ref_kind": "existing_graph_node",
            "node_id": "group_the_group",
            "label": "the group",
            "kind": "group",
        },
    )
    overlay = create_empty_authored_graph_overlay(CAMPAIGN_ID, created_at=STAMP).model_copy(
        update={"assertions": [link]}
    )
    enriched, _ = apply_authored_overlay_to_graph_review_projection(projection, overlay)
    assert enriched.markdown == projection.markdown
    assert len(enriched.mentions) == len(projection.mentions)


def test_link_existing_alias_mention_skips_conflicting_overlap() -> None:
    projection = RecapGraphProjection(
        campaign_id=CAMPAIGN_ID,
        session_id="session-2",
        graph_id="graph-1",
        markdown="# Session 2 Recap\n\nThe [gang](dmb-node:other_node) survived.",
        focus=GraphFocusOverlay(focus_session_id="session-2"),
        node_views={
            "group_the_group": GraphProjectionNodeView(
                node_id="group_the_group",
                label="the group",
                kind="group",
                role="group",
                aliases=["the group"],
                source_domains=["live_projection"],
                evidence_badges=[],
                adjacency=[],
            ),
            "other_node": GraphProjectionNodeView(
                node_id="other_node",
                label="Other",
                kind="entity",
                role="entity",
                aliases=[],
                source_domains=["live_projection"],
                evidence_badges=[],
                adjacency=[],
            ),
        },
        mentions=[],
        source_spans=[],
    )
    link = link_existing_assertion(
        existing_object_ref={
            "ref_kind": "existing_graph_node",
            "node_id": "group_the_group",
            "label": "the group",
            "kind": "group",
        },
    )
    overlay = create_empty_authored_graph_overlay(CAMPAIGN_ID, created_at=STAMP).model_copy(
        update={"assertions": [link]}
    )
    diagnostics: list = []
    enriched, summary = apply_authored_overlay_to_graph_review_projection(
        projection,
        overlay,
        summary=AuthoredOverlayProjectionSummary(loaded=True, diagnostics=diagnostics),
    )
    assert enriched.markdown == projection.markdown
    assert not any(item.node_id == "group_the_group" for item in enriched.mentions)
    assert any(item.code == "authored_alias_mention_conflict" for item in summary.diagnostics)


def _double_gang_projection() -> RecapGraphProjection:
    return RecapGraphProjection(
        campaign_id=CAMPAIGN_ID,
        session_id="session-2",
        graph_id="graph-1",
        markdown="# Recap\n\nThe gang met again. Later the gang returned.",
        focus=GraphFocusOverlay(focus_session_id="session-2"),
        node_views={
            "group_the_group": GraphProjectionNodeView(
                node_id="group_the_group",
                label="the group",
                kind="group",
                role="group",
                aliases=["the group"],
                source_domains=["live_projection"],
                evidence_badges=[],
                adjacency=[],
            )
        },
        mentions=[],
        source_spans=[],
    )


def test_link_existing_alias_mention_selects_second_occurrence_with_source_anchor() -> None:
    link = link_existing_assertion(
        selected_text="gang",
        normalized_selected_text="gang",
        existing_object_ref={
            "ref_kind": "existing_graph_node",
            "node_id": "group_the_group",
            "label": "the group",
            "kind": "group",
        },
        source_anchor={
            "anchor_kind": "text_span",
            "selected_text": "gang",
            "normalized_selected_text": "gang",
            "surrounding_text_before": "Later the ",
            "surrounding_text_after": " returned.",
        },
    )
    overlay = create_empty_authored_graph_overlay(CAMPAIGN_ID, created_at=STAMP).model_copy(
        update={"assertions": [link]}
    )
    enriched, _ = apply_authored_overlay_to_graph_review_projection(
        _double_gang_projection(),
        overlay,
    )
    assert enriched.markdown is not None
    assert enriched.markdown.count("[gang](dmb-node:group_the_group)") == 1
    assert "The gang met again." in enriched.markdown
    assert "[gang](dmb-node:group_the_group) returned." in enriched.markdown


def test_link_existing_alias_mention_ungrounded_when_source_anchor_matches_none() -> None:
    link = link_existing_assertion(
        selected_text="gang",
        normalized_selected_text="gang",
        existing_object_ref={
            "ref_kind": "existing_graph_node",
            "node_id": "group_the_group",
            "label": "the group",
            "kind": "group",
        },
        source_anchor={
            "anchor_kind": "text_span",
            "selected_text": "gang",
            "normalized_selected_text": "gang",
            "surrounding_text_before": "Nowhere prefix ",
            "surrounding_text_after": " impossible suffix",
        },
    )
    overlay = create_empty_authored_graph_overlay(CAMPAIGN_ID, created_at=STAMP).model_copy(
        update={"assertions": [link]}
    )
    enriched, summary = apply_authored_overlay_to_graph_review_projection(
        _double_gang_projection(),
        overlay,
    )
    assert enriched.markdown == _double_gang_projection().markdown
    assert not enriched.mentions
    assert any(item.code == "authored_alias_mention_ungrounded" for item in summary.diagnostics)


def test_context_scoring_disambiguates_duplicate_selected_text() -> None:
    from apps.live_control_server.models.graph_authoring_overlay import GraphAuthoringSourceAnchor
    from apps.live_control_server.services.graph_authoring_overlay_projection import (
        _find_authored_alias_span_in_markdown,
    )

    markdown = (
        "# Recap\n\n"
        "The gate opens so that the group of heroes can enter the town. Lysandra waves.\n\n"
        "Later along the wall the heroes can feel magic in the air."
    )
    span, code = _find_authored_alias_span_in_markdown(
        markdown,
        "heroes",
        source_anchor=GraphAuthoringSourceAnchor(
            anchor_kind="text_span",
            selected_text="heroes",
            normalized_selected_text="heroes",
            surrounding_text_before="The gate opens so that the group of",
            surrounding_text_after="can enter the town. Lysandra waves.",
        ),
        occupied=[],
    )
    assert code is None
    assert span is not None
    assert markdown[span[0] : span[1]] == "heroes"
    assert markdown[span[0] - 21 : span[0]] == "so that the group of "


def test_link_existing_alias_mention_ambiguous_without_source_anchor_context() -> None:
    link = link_existing_assertion(
        selected_text="gang",
        normalized_selected_text="gang",
        existing_object_ref={
            "ref_kind": "existing_graph_node",
            "node_id": "group_the_group",
            "label": "the group",
            "kind": "group",
        },
        source_anchor=None,
    )
    overlay = create_empty_authored_graph_overlay(CAMPAIGN_ID, created_at=STAMP).model_copy(
        update={"assertions": [link]}
    )
    enriched, summary = apply_authored_overlay_to_graph_review_projection(
        _double_gang_projection(),
        overlay,
    )
    assert enriched.markdown == _double_gang_projection().markdown
    assert not enriched.mentions
    assert any(item.code == "authored_alias_mention_ambiguous" for item in summary.diagnostics)


def test_gold_projection_does_not_enrich_with_authored_overlay(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from apps.live_control_server.services import graph_gold_review

    def _fail_if_called(*_args, **_kwargs) -> None:
        raise AssertionError("gold fixture projection must not load authored overlay")

    monkeypatch.setattr(
        "apps.live_control_server.services.graph_authoring_overlay_projection.enrich_projection_payload_with_authored_overlay",
        _fail_if_called,
    )

    response = graph_gold_review.build_gold_graph_projection(
        campaign_id="longmont-c1",
        session_id="session-1",
    )
    dumped = response.model_dump(mode="json")
    assert "authored_overlay" not in dumped
