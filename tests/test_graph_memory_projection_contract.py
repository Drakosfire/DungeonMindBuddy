from __future__ import annotations

import ast
import inspect
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from graph_memory.projection import (
    GraphProjectionEvidenceBadge,
    RecapGraphProjection,
    build_focus_overlay,
    build_node_view,
    build_recap_graph_projection,
)
from graph_memory.projection import recap_projection as recap_projection_module
from graph_memory.union_supergraph.load import (
    DEFAULT_FIXTURE_PATH,
    load_union_supergraph_payload,
    load_union_supergraph_store,
    parse_union_supergraph_store,
)
from graph_memory.union_supergraph.model import UnionSupergraphStore

UNION_MENTION_FIXTURE_PATH = (
    Path(__file__).parent / "fixtures" / "graph_memory" / "union_mention_characterization_v1.json"
)


@pytest.fixture
def store() -> UnionSupergraphStore:
    return load_union_supergraph_store()


def test_build_focus_overlay_uses_focus_session_id(store: UnionSupergraphStore) -> None:
    overlay = build_focus_overlay(store)

    assert overlay.focus_session_id == "session-23"


def test_focus_overlay_collects_focus_evidence_and_edges(
    store: UnionSupergraphStore,
) -> None:
    overlay = build_focus_overlay(store)

    assert overlay.focused_evidence_ref_ids == [
        "evidence:session-23:caelynn:recap-mention"
    ]
    assert overlay.focused_edge_ids == [
        "edge:pc_caelynn:participated_in:event_session_23_mireward_gate"
    ]
    assert "pc_caelynn" in overlay.focused_node_ids
    assert "event_session_23_mireward_gate" in overlay.focused_node_ids


def test_build_node_view_returns_global_caelynn_view(
    store: UnionSupergraphStore,
) -> None:
    node_view = build_node_view(store, "pc_caelynn")

    assert node_view.node_id == "pc_caelynn"
    assert node_view.label == "Caelynn"
    assert node_view.kind == "pc"
    assert node_view.role == "pc"
    assert node_view.source_domains == ["recap", "worldbuilding"]
    assert node_view.summary == (
        "Read-model example global PC node; not proof of Session 23 extraction."
    )


def test_node_view_evidence_badges_include_session_metadata(
    store: UnionSupergraphStore,
) -> None:
    node_view = build_node_view(store, "pc_caelynn", focus_session_id="session-23")
    recap_badge = next(
        badge
        for badge in node_view.evidence_badges
        if badge.evidence_ref_id == "evidence:session-23:caelynn:recap-mention"
    )

    assert recap_badge.session_id == "session-23"
    assert recap_badge.source_span_ref_id == "spref:session-23:p014"
    assert recap_badge.label == "focus session recap mention"


def test_node_view_adjacency_includes_edge_label_and_session_ids(
    store: UnionSupergraphStore,
) -> None:
    node_view = build_node_view(store, "pc_caelynn", focus_session_id="session-23")
    gate_candidate = next(
        candidate
        for candidate in node_view.adjacency
        if candidate.node_id == "event_session_23_mireward_gate"
    )

    assert gate_candidate.edge_label == "participated in"
    assert gate_candidate.session_ids == ["session-23"]


def test_node_view_adjacency_includes_related_summary_and_source_excerpt() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    source = (
        repo_root
        / "out/graph_memory/runs/longmont-c2/session-23/20260629T183113Z/preview_union_supergraph.json"
    )
    if not source.is_file():
        return

    store = load_union_supergraph_store(source)
    node_view = build_node_view(
        store,
        "party:captain_lysandra_ironveil",
        focus_session_id="session-23",
    )
    inn = next(
        candidate
        for candidate in node_view.adjacency
        if candidate.node_id == "location_inn_mireward_reach"
    )

    assert inn.source_excerpt
    assert "inn" in inn.source_excerpt.casefold()


def test_node_view_adjacency_resolves_full_paragraph_and_highlights_label_fragments() -> None:
    """When a paragraph text index is available, source_excerpt should resolve
    to the verbatim paragraph (not the pre-abridged evidence label), with
    highlight spans covering the label's verbatim fragments."""
    payload = json.loads(json.dumps(load_union_supergraph_payload(DEFAULT_FIXTURE_PATH)))
    payload["evidence"]["evidence:session-23:caelynn:recap-mention"]["label"] = (
        "Caelynn arrives at the gate ... to help defend the town"
    )
    store = parse_union_supergraph_store(payload)

    full_paragraph = (
        "Caelynn arrives at the gate just as the horde crashes through the outer wall, "
        "and she draws her blade to help defend the town alongside the others."
    )
    node_view = build_node_view(
        store,
        "pc_caelynn",
        focus_session_id="session-23",
        paragraph_text_by_span_id={"spref:session-23:p014": full_paragraph},
    )
    gate_candidate = next(
        candidate
        for candidate in node_view.adjacency
        if candidate.node_id == "event_session_23_mireward_gate"
    )

    assert gate_candidate.source_excerpt == full_paragraph
    assert gate_candidate.source_excerpt_is_full_paragraph is True
    fragments = [
        full_paragraph[span.start : span.end]
        for span in gate_candidate.source_excerpt_highlight_spans
    ]
    assert "Caelynn arrives at the gate" in fragments
    assert "to help defend the town" in fragments


def test_node_view_adjacency_falls_back_to_label_without_paragraph_index() -> None:
    """Without a paragraph text index, the (possibly abridged) label remains
    the excerpt and no highlight spans are produced."""
    payload = json.loads(json.dumps(load_union_supergraph_payload(DEFAULT_FIXTURE_PATH)))
    payload["evidence"]["evidence:session-23:caelynn:recap-mention"]["label"] = (
        "Caelynn arrives at the gate ... to help defend the town"
    )
    store = parse_union_supergraph_store(payload)

    node_view = build_node_view(store, "pc_caelynn", focus_session_id="session-23")
    gate_candidate = next(
        candidate
        for candidate in node_view.adjacency
        if candidate.node_id == "event_session_23_mireward_gate"
    )

    assert gate_candidate.source_excerpt == (
        "Caelynn arrives at the gate ... to help defend the town"
    )
    assert gate_candidate.source_excerpt_is_full_paragraph is False
    assert gate_candidate.source_excerpt_highlight_spans == []


def test_node_view_adjacency_filters_placeholder_related_summary() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    source = (
        repo_root
        / "out/graph_memory/runs/longmont-c2/session-23/20260629T183113Z/preview_union_supergraph.json"
    )
    if not source.is_file():
        return

    store = load_union_supergraph_store(source)
    node_view = build_node_view(
        store,
        "party:captain_lysandra_ironveil",
        focus_session_id="session-23",
    )

    for candidate in node_view.adjacency:
        assert candidate.related_summary != "Deterministic party context anchor"


def test_node_view_suggested_expansions_are_ranked_focus_first(
    store: UnionSupergraphStore,
) -> None:
    node_view = build_node_view(store, "pc_caelynn", focus_session_id="session-23")

    assert len(node_view.suggested_expansions) == len(node_view.adjacency)
    assert node_view.suggested_expansions[0].node_id == "event_session_23_mireward_gate"
    assert node_view.suggested_expansions[0].rank == 1
    assert node_view.suggested_expansions[0].rank_reason == "current session"
    assert node_view.suggested_expansions[1].node_id == "loc_mirathorn"
    assert node_view.suggested_expansions[1].rank == 2


def test_node_view_includes_focus_and_non_focus_evidence_badges(
    store: UnionSupergraphStore,
) -> None:
    node_view = build_node_view(store, "pc_caelynn", focus_session_id="session-23")

    badges = {badge.evidence_ref_id: badge for badge in node_view.evidence_badges}
    assert (
        badges["evidence:session-23:caelynn:recap-mention"].is_focus_session_evidence
        is True
    )
    assert (
        badges[
            "evidence:worldbuilding:caelynn:character-note"
        ].is_focus_session_evidence
        is False
    )
    assert {badge.source_domain for badge in node_view.evidence_badges} == {
        "recap",
        "worldbuilding",
    }


def test_node_view_marks_caelynn_as_focus_anchored_for_session_23(
    store: UnionSupergraphStore,
) -> None:
    node_view = build_node_view(store, "pc_caelynn", focus_session_id="session-23")

    assert node_view.anchored_to_focus_session is True


def test_node_view_includes_focus_and_non_focus_adjacency_candidates(
    store: UnionSupergraphStore,
) -> None:
    node_view = build_node_view(store, "pc_caelynn", focus_session_id="session-23")

    candidates = {candidate.node_id: candidate for candidate in node_view.adjacency}
    assert (
        candidates["event_session_23_mireward_gate"].anchored_to_focus_session is True
    )
    assert candidates["event_session_23_mireward_gate"].predicate == "participated_in"
    assert candidates["loc_mirathorn"].anchored_to_focus_session is False
    assert candidates["loc_mirathorn"].source_domains == ["worldbuilding"]


def test_build_recap_graph_projection_returns_backend_neutral_payload(
    store: UnionSupergraphStore,
) -> None:
    projection = build_recap_graph_projection(store, session_id="session-23")

    assert isinstance(projection, RecapGraphProjection)
    assert projection.campaign_id == "longmont-c2"
    assert projection.session_id == "session-23"
    assert projection.graph_id == "longmont-c2:union-supergraph"
    assert projection.mentions == []


def test_build_recap_graph_projection_projects_markdown_mentions(
    store: UnionSupergraphStore,
) -> None:
    projection = build_recap_graph_projection(
        store,
        session_id="session-23",
        markdown="Caelynn looked toward Mirathorn.",
    )

    assert "[Caelynn](dmb-node:pc_caelynn)" in (projection.markdown or "")
    assert "[Mirathorn](dmb-node:loc_mirathorn)" in (projection.markdown or "")
    assert [mention.node_id for mention in projection.mentions] == [
        "pc_caelynn",
        "loc_mirathorn",
    ]


def test_build_recap_graph_projection_mention_offsets_match_projected_markdown(
    store: UnionSupergraphStore,
) -> None:
    """Regression: mention offsets must describe positions in the returned
    markdown, not the pre-replacement text. Repeated aliases previously drifted
    further out of alignment with every earlier `[label](dmb-node:id)` splice."""

    projection = build_recap_graph_projection(
        store,
        session_id="session-23",
        markdown=(
            "Caelynn looked toward Mirathorn. Then Caelynn walked with "
            "Mirathorn to the gate near Mirathorn again."
        ),
    )

    assert len(projection.mentions) == 5
    for mention in projection.mentions:
        assert mention.start_offset is not None
        assert mention.end_offset is not None
        slice_ = (projection.markdown or "")[mention.start_offset : mention.end_offset]
        assert slice_ == f"[{mention.label}](dmb-node:{mention.node_id})"


def test_recap_projection_contains_global_pc_caelynn_node_view(
    store: UnionSupergraphStore,
) -> None:
    projection = build_recap_graph_projection(store, session_id="session-23")

    caelynn = projection.node_views["pc_caelynn"]
    assert caelynn.label == "Caelynn"
    assert caelynn.anchored_to_focus_session is True
    assert {candidate.node_id for candidate in caelynn.adjacency} == {
        "event_session_23_mireward_gate",
        "loc_mirathorn",
    }


def test_projection_models_reject_invalid_basic_types() -> None:
    with pytest.raises(ValidationError, match="can_open_source"):
        GraphProjectionEvidenceBadge.model_validate(
            {
                "evidence_ref_id": "evidence:1",
                "source_artifact_id": "artifact:1",
                "source_domain": "recap",
                "evidence_role": "recap_mention",
                "can_open_source": "true",
            }
        )


def _load_union_mention_fixture() -> dict:
    return json.loads(UNION_MENTION_FIXTURE_PATH.read_text(encoding="utf-8"))


def _projection_from_union_case(case: dict) -> RecapGraphProjection:
    store = UnionSupergraphStore.model_validate(case["store"])
    kwargs: dict = {
        "session_id": case.get("session_id", "session-23"),
        "markdown": case["markdown"],
    }
    if case.get("paragraph_text_by_span_id"):
        kwargs["paragraph_text_by_span_id"] = case["paragraph_text_by_span_id"]
    if case.get("known_entity_mentions"):
        kwargs["known_entity_mentions"] = case["known_entity_mentions"]
    return build_recap_graph_projection(store, **kwargs)


# Operator-authorized exception for destination protection enabling post-pass
# rewrite diagnostics. Only this case may declare non-mention field deltas.
_AUTHORIZED_NON_MENTION_DELTAS_BY_CASE = {
    "alias_existing_dmb_link_plus_plain": frozenset({"union_identity_diagnostics"}),
}


def test_union_mention_characterization_fixture_provenance() -> None:
    fixture = _load_union_mention_fixture()
    assert fixture["schema"] == "dmb_union_mention_migration_characterization_v1"
    # Generation base must be the pre-change parent of the fixture-only commit,
    # not the fixture commit itself or any amended orphan.
    expected_base = "da553bcf0bea902cccc32e6c8f1a9e8de4cff2a4"
    assert fixture["base_sha"] == expected_base
    assert fixture.get("fixture_parent_sha", expected_base) == expected_base
    assert len(fixture["cases"]) >= 30
    sidecar = sum(1 for case in fixture["cases"] if case.get("known_entity_mentions"))
    assert sidecar >= 10
    assert sum(1 for case in fixture["cases"] if not case.get("known_entity_mentions")) >= 10
    assert sum(1 for case in fixture["cases"] if case["category"] == "protected_skip") >= 10
    assert any(case["case_id"] == "alias_equal_length_first_win" for case in fixture["cases"])
    assert any(
        case["case_id"] == "alias_existing_dmb_link_plus_plain" for case in fixture["cases"]
    )
    assert not (fixture.get("deferred_stop_conditions") or [])
    for case in fixture["cases"]:
        allowed = set(case.get("authorized_non_mention_field_deltas") or [])
        expected_allowed = set(_AUTHORIZED_NON_MENTION_DELTAS_BY_CASE.get(case["case_id"], ()))
        assert allowed == expected_allowed, (
            f"{case['case_id']} authorized_non_mention_field_deltas={allowed!r}; "
            f"expected {expected_allowed!r}"
        )
        assert isinstance(case["base_projection"], dict)
        assert "markdown" in case["base_projection"]
        assert "mentions" in case["base_projection"]
        assert "node_views" in case["base_projection"]
        assert "focus" in case["base_projection"]
        assert "union_identity_diagnostics" in case["base_projection"]


def test_existing_dmb_link_destination_protection_authorizes_redirect_diagnostic() -> None:
    """Operator option 1: destination protection may add mention_target_resolved.

    Live-replay proves production emits the authorized diagnostic delta; other
    non-mention fields remain exact.
    """
    fixture = _load_union_mention_fixture()
    case = next(
        item
        for item in fixture["cases"]
        if item["case_id"] == "alias_existing_dmb_link_plus_plain"
    )
    assert case["authorized_non_mention_field_deltas"] == ["union_identity_diagnostics"]

    head = _projection_from_union_case(case).model_dump(mode="json")
    assert head == case["expected_head"]

    base = case["base_projection"]
    assert base["union_identity_diagnostics"] != head["union_identity_diagnostics"]
    assert any(
        d.get("code") == "union_identity_mention_target_resolved"
        for d in head["union_identity_diagnostics"]
    )
    assert not any(
        d.get("code") == "union_identity_mention_target_resolved"
        for d in base["union_identity_diagnostics"]
    )
    for key, value in base.items():
        if key in {"markdown", "mentions", "union_identity_diagnostics"}:
            continue
        assert head.get(key) == value, f"unauthorized non-mention field drifted: {key}"


@pytest.mark.parametrize(
    "case",
    _load_union_mention_fixture()["cases"],
    ids=[case["case_id"] for case in _load_union_mention_fixture()["cases"]],
)
def test_union_mention_migration_characterization(case: dict) -> None:
    projection = _projection_from_union_case(case)
    head = projection.model_dump(mode="json")
    base = case["base_projection"]
    if case["category"] == "unchanged":
        assert head == base
        return

    expected = case["expected_head"]
    assert head == expected
    allowed = set(case.get("authorized_non_mention_field_deltas") or [])
    expected_allowed = set(_AUTHORIZED_NON_MENTION_DELTAS_BY_CASE.get(case["case_id"], ()))
    assert allowed == expected_allowed, (
        f"{case['case_id']} authorized_non_mention_field_deltas={allowed!r}; "
        f"expected {expected_allowed!r}"
    )
    for key, value in base.items():
        if key in {"markdown", "mentions"}:
            continue
        if key in allowed:
            assert head.get(key) != value, (
                f"{case['case_id']} authorized delta {key!r} must actually differ from base"
            )
            continue
        assert head.get(key) == value, f"non-mention field drifted: {key}"


def test_equal_length_overlapping_aliases_preserve_insertion_order_winner() -> None:
    """Equal-length overlapping aliases must keep stable length-only first-win order.

    Insertion order B-C then A-B over the surface A-B-C must link B-C, not A-B.
    """
    store_payload = {
        "schema": "dmb_union_supergraph_store_v0",
        "version": "0.1",
        "campaign_id": "longmont-c2",
        "graph_id": None,
        "graph_domains": [],
        "source_domains": [],
        "focus_session_id": "session-23",
        "nodes": {
            "n_bc": {
                "node_id": "n_bc",
                "label": "BC",
                "kind": "npc",
                "role": "npc",
                "aliases": ["B-C"],
                "source_domains": ["recap"],
                "evidence_ref_ids": ["evidence:equal:bc"],
                "state": {"memory_state": "graph_read_model"},
            },
            "n_ab": {
                "node_id": "n_ab",
                "label": "AB",
                "kind": "npc",
                "role": "npc",
                "aliases": ["A-B"],
                "source_domains": ["recap"],
                "evidence_ref_ids": ["evidence:equal:ab"],
                "state": {"memory_state": "graph_read_model"},
            },
        },
        "edges": {},
        "evidence": {},
        "source_artifacts": {},
        "aliases": {"B-C": "n_bc", "A-B": "n_ab"},
        "identity_redirects": [],
        "identity_merge_records": [],
        "identity_decisions": [],
        "assertion_support": {},
        "contribution_source_payload_sha256": {},
        "contribution_replay_manifest": [],
        "initialization_contribution_ids": [],
        "initialization_plan_digest": None,
        "initialization_attestation_digest": None,
        "adjacency": {},
        "diagnostics": {
            "canon_promotion": False,
            "approved_memory_write": False,
            "corpus_mutation": False,
            "production_retrieval": False,
        },
    }
    store = UnionSupergraphStore.model_validate(store_payload)
    assert list(store.aliases.items()) == [("B-C", "n_bc"), ("A-B", "n_ab")]
    projection = build_recap_graph_projection(
        store,
        session_id="session-23",
        markdown="See A-B-C today.",
    )
    assert projection.markdown == "See A-[B-C](dmb-node:n_bc) today."
    assert [m.node_id for m in projection.mentions] == ["n_bc"]
    assert [m.label for m in projection.mentions] == ["B-C"]


def test_project_markdown_mentions_union_adapter_has_no_duplicate_matcher() -> None:
    source = inspect.getsource(recap_projection_module._project_markdown_mentions)
    tree = ast.parse(source)
    assert "re.compile" not in source
    assert ".finditer" not in source
    assert "splice_node_link_spans(" not in source
    calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(getattr(node.func, "id", None), str)
        and node.func.id == "project_markdown_mentions"
    ]
    assert len(calls) == 1
