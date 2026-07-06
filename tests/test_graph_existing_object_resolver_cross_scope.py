from pathlib import Path

from apps.live_control_server.services.graph_existing_object_resolver import (
    GraphReviewExistingObjectResolverRequest,
    GraphReviewResolverSelectedNode,
    resolve_existing_object_candidates,
)
from apps.live_control_server.services.graph_object_candidate_sources import (
    GraphObjectCandidateScope,
    normalize_candidate_text,
    score_query_match,
    search_cross_scope_candidates,
    GraphObjectCandidateSearchContext,
)


def _request(**overrides):
    node = {
        "node_id": "selected-gang",
        "label": "gang",
        "kind": "unknown",
        "role": "mention",
        "aliases": [],
        "summary": None,
        "source_domains": ["recap"],
        "adjacent_labels": [],
        "evidence_ref_ids": [],
    }
    payload = {
        "campaign_id": "longmont-c2",
        "session_id": "session-23",
        "lane_role": "live",
        "selected_node": GraphReviewResolverSelectedNode(**node),
        "query": "Caelynn",
        "include_gm_private": False,
    }
    payload.update(overrides)
    if "selected_node" in overrides and isinstance(overrides["selected_node"], dict):
        payload["selected_node"] = GraphReviewResolverSelectedNode(**overrides["selected_node"])
    return GraphReviewExistingObjectResolverRequest(**payload)


def test_score_query_exact_label_outranks_substring():
    exact = score_query_match("Mirathorn", label="Mirathorn")
    substring = score_query_match("Mirath", label="Mirathorn")
    assert exact is not None and substring is not None
    assert exact[0] > substring[0]


def test_score_query_alias_match_has_clear_reason():
    scored = score_query_match("gang", label="Questionable Company", aliases=["gang"])
    assert scored == (0.95, "Alias match: gang")


def test_same_node_id_within_scope_is_deduped():
    context = GraphObjectCandidateSearchContext(
        campaign_id="longmont-c2",
        session_id="session-23",
        query="Mirathorn",
        scopes=[GraphObjectCandidateScope.worldbuilding],
        include_current_projection=False,
        include_authored_overlay=False,
        include_party_pc=False,
        include_campaign_memory=False,
        include_gm_private=False,
        repo_root=Path("."),
    )
    candidates, _, _ = search_cross_scope_candidates(context)
    node_ids = [candidate.node_id for candidate in candidates]
    assert len(node_ids) == len(set(node_ids))


def test_same_label_across_scopes_is_not_deduped():
    response = resolve_existing_object_candidates(_request(query="Caelynn"))
    scopes = {
        candidate.graph_scope
        for candidate in response.candidates
        if candidate.label.lower() == "caelynn"
    }
    assert len(scopes) >= 1


def test_worldbuilding_candidate_returns_with_source_label():
    response = resolve_existing_object_candidates(_request(query="Mirathorn"))
    worldbuilding = [
        candidate
        for candidate in response.candidates
        if candidate.graph_scope == GraphObjectCandidateScope.worldbuilding
    ]
    assert worldbuilding
    assert worldbuilding[0].source_label == "Worldbuilding"


def test_party_pc_candidate_returns_when_fixture_exists():
    response = resolve_existing_object_candidates(_request(query="Caelynn"))
    party_candidates = [
        candidate
        for candidate in response.candidates
        if candidate.graph_scope == GraphObjectCandidateScope.party_pc
    ]
    assert party_candidates
    assert party_candidates[0].source_label == "Party / PCs"


def test_missing_optional_scope_returns_diagnostic_not_failure():
    response = resolve_existing_object_candidates(
        _request(
            campaign_id="longmont-c1",
            session_id="session-1",
            query="Mirathorn",
            include_party_pc=False,
        )
    )
    assert response.diagnostics
    assert any(
        diagnostic.code in {"worldbuilding_graph_missing", "candidate_scope_empty", "candidate_scope_unavailable"}
        for diagnostic in response.diagnostics
    )


def test_current_recap_candidates_still_return_for_legacy_request():
    response = resolve_existing_object_candidates(
        GraphReviewExistingObjectResolverRequest(
            campaign_id="longmont-c1",
            session_id="session-1",
            lane_role="live",
            selected_node=GraphReviewResolverSelectedNode(
                node_id="selected-stone-bridge",
                label="Stone Bridge",
                kind="location",
                role="source_evidence",
            ),
            query=None,
            include_authored_overlay=False,
            include_worldbuilding=False,
            include_party_pc=False,
            include_campaign_memory=False,
            include_gm_private=False,
            include_current_projection=False,
        )
    )
    assert response.candidates
    assert response.candidates[0].confidence == "high"


def test_authored_overlay_scope_search_reports_source_label(monkeypatch, tmp_path):
    from apps.live_control_server.models.graph_authoring_overlay import (
        create_empty_authored_graph_overlay,
    )
    from apps.live_control_server.services.graph_authoring_overlay_projection import (
        AuthoredOverlayProjectionSummary,
    )
    from apps.live_control_server.services import graph_object_candidate_sources as sources_module
    from tests.test_graph_authoring_overlay_models import CAMPAIGN_ID, STAMP, object_assertion

    overlay = create_empty_authored_graph_overlay(CAMPAIGN_ID, created_at=STAMP).model_copy(
        update={
            "assertions": [
                object_assertion(
                    assertion_id="obj-1",
                    object_ref={
                        "ref_kind": "manual_ref",
                        "label": "Questionable Company",
                        "kind": "party",
                    },
                    aliases=["gang"],
                )
            ]
        }
    )

    monkeypatch.setattr(
        sources_module,
        "load_authored_overlay_for_review",
        lambda **kwargs: (
            overlay,
            AuthoredOverlayProjectionSummary(loaded=True, assertion_count=1),
        ),
    )
    candidates, diagnostics, scopes = search_cross_scope_candidates(
        GraphObjectCandidateSearchContext(
            campaign_id="longmont-c2",
            session_id="session-23",
            query="gang",
            scopes=[GraphObjectCandidateScope.authored_overlay],
            include_current_projection=False,
            include_worldbuilding=False,
            include_party_pc=False,
            include_campaign_memory=False,
            include_gm_private=False,
            repo_root=tmp_path,
        )
    )
    assert GraphObjectCandidateScope.authored_overlay in scopes
    assert candidates
    assert candidates[0].source.source_label == "Authored memory"
    assert not diagnostics or all(item.severity != "error" for item in diagnostics)


def test_resolver_search_does_not_mutate_overlay_file(monkeypatch, tmp_path):
    overlay_path = tmp_path / "overlay.json"
    overlay_path.write_text('{"schema":"authored_graph_overlay_v1","campaign_id":"x"}', encoding="utf-8")
    before = overlay_path.read_bytes()
    resolve_existing_object_candidates(
        _request(query="gang", campaign_id="longmont-c2", session_id="session-23")
    )
    assert overlay_path.read_bytes() == before


def test_normalize_candidate_text():
    assert normalize_candidate_text("  Bonogo ") == "bonogo"
