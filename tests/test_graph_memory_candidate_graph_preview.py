from __future__ import annotations

from src.graph_memory.candidate_graph_preview import (
    CANDIDATE_GRAPH_PREVIEW_SCHEMA,
    CANDIDATE_GRAPH_PREVIEW_VERSION,
    candidate_graph_preview_from_dict,
    candidate_graph_preview_to_dict,
    validate_candidate_graph_preview,
)


def _semantic_state() -> dict[str, str]:
    return {
        "canon_state": "candidate_extraction",
        "lifecycle_state": "candidate",
        "evidence_role": "source_evidence",
        "authority_state": "llm_generated",
        "visibility_state": "internal_diagnostic",
    }


def _evidence_ref(suffix: str) -> dict[str, object]:
    return {
        "source_ref_id": f"ref:c1s1:{suffix}",
        "source_artifact_id": "artifact:c1s1",
        "source_anchor_id": f"anchor:c1s1:{suffix}",
        "label": "C1S1 source span",
        "evidence_role": "source_evidence",
        "can_open_source": True,
        "can_highlight_span": True,
        "source_span_ref_id": f"spref:c1s1:{suffix}",
    }


def _node(node_type: str, label: str, suffix: str = "001") -> dict[str, object]:
    return {
        "node_id": f"node:{node_type}:{suffix}",
        "label": label,
        "node_type": node_type,
        "description": f"Candidate {label}",
        "importance": "medium",
        "semantic_state": _semantic_state(),
        "evidence_refs": [_evidence_ref(suffix)],
        "proposed_action": "create",
        "confidence": "medium",
        "warnings": [],
    }


def _preview_payload(nodes: list[dict[str, object]]) -> dict[str, object]:
    return {
        "schema": CANDIDATE_GRAPH_PREVIEW_SCHEMA,
        "version": CANDIDATE_GRAPH_PREVIEW_VERSION,
        "preview_id": "preview:encounter-job-contract-test",
        "campaign_id": "campaign:c1",
        "session_id": "session:c1s1",
        "source_artifact_ids": ["artifact:c1s1"],
        "status": "preview",
        "nodes": nodes,
        "edges": [],
        "beats": [],
        "proposed_writes": [],
        "ignored_items": [],
        "deferred_items": [],
        "diagnostics": {
            "preview_only": True,
            "extraction_performed": False,
            "llm_used": False,
            "runtime_connected": False,
            "plan_connected": False,
            "agent_interaction_connected": False,
            "corpus_scanned": False,
            "corpus_mutated": False,
            "facts_promoted": False,
            "canon_promoted": False,
            "unresolved_evidence_refs": 0,
            "missing_evidence_objects": 0,
            "warning_count": 0,
        },
    }


def _node_type_issues(report):
    return [issue for issue in report.issues if issue.field == "node_type"]


def test_combat_encounter_candidate_node_type_validates():
    preview = candidate_graph_preview_from_dict(
        _preview_payload([_node("combat_encounter", "Glowkindle cellar rat fight")])
    )

    report = validate_candidate_graph_preview(preview)

    assert report.issue_counts.get("invalid_semantic_state", 0) == 0
    assert _node_type_issues(report) == []


def test_quest_candidate_node_type_validates():
    preview = candidate_graph_preview_from_dict(
        _preview_payload([_node("quest", "Clear rats from Glowkindle's cellar")])
    )

    report = validate_candidate_graph_preview(preview)

    assert report.issue_counts.get("invalid_semantic_state", 0) == 0
    assert _node_type_issues(report) == []


def test_creature_candidate_node_type_validates():
    preview = candidate_graph_preview_from_dict(
        _preview_payload([_node("creature", "Bubbles the Float Goat")])
    )

    report = validate_candidate_graph_preview(preview)

    assert report.issue_counts.get("invalid_semantic_state", 0) == 0
    assert _node_type_issues(report) == []


def test_rejected_encounter_job_adjacent_node_types_remain_invalid():
    for node_type in ("job", "adversary", "monster"):
        preview = candidate_graph_preview_from_dict(
            _preview_payload([_node(node_type, f"Rejected {node_type} node")])
        )

        report = validate_candidate_graph_preview(preview)

        issues = _node_type_issues(report)
        assert report.issue_counts.get("invalid_semantic_state", 0) == 1
        assert len(issues) == 1
        assert issues[0].object_id == f"node:{node_type}:001"


def test_candidate_node_parses_party_claimed_fill_fields_and_ignores_unknown_keys():
    node_payload = {
        **_node("character", "Filled PC", "fill"),
        "description": "Party claimed-fill enriched description",
        "session_actions": ["cast Fireball", "  ", "negotiate"],
        "enriched_by": "party_claimed_fill",
        "future_field": "should be ignored",
    }
    preview = candidate_graph_preview_from_dict(_preview_payload([node_payload]))
    node = preview.nodes[0]

    assert node.description == "Party claimed-fill enriched description"
    assert node.session_actions == ("cast Fireball", "negotiate")
    assert node.enriched_by == "party_claimed_fill"
    assert not hasattr(node, "future_field")


def test_encounter_and_quest_candidate_preview_round_trips_and_validates():
    preview = candidate_graph_preview_from_dict(
        _preview_payload(
            [
                _node("combat_encounter", "Glowkindle cellar rat fight", "001"),
                _node("quest", "Clear rats from Glowkindle's cellar", "002"),
            ]
        )
    )

    round_tripped = candidate_graph_preview_from_dict(
        candidate_graph_preview_to_dict(preview)
    )
    report = validate_candidate_graph_preview(round_tripped)

    assert round_tripped == preview
    assert {node.node_type for node in round_tripped.nodes} == {"combat_encounter", "quest"}
    assert report.issue_counts == {}
    assert report.issues == ()
