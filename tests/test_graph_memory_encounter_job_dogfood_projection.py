from __future__ import annotations

from pathlib import Path

from evals.graph_memory_layer.encounter_job_dogfood_fixture import dogfood_result_to_payload, run_glowkindle_encounter_job_dogfood
from evals.graph_memory_layer.report_encounter_job_dogfood_projection import render_report
from evals.graph_memory_layer.validate_encounter_job_dogfood_projection import EXPECTED_FALSE, validate_payload


def _payload():
    return dogfood_result_to_payload(run_glowkindle_encounter_job_dogfood())


def _edge(payload, source, target, rel):
    for edge in payload["candidate_graph"]["edges"]:
        if edge["from_node_id"] == source and edge["to_node_id"] == target and edge["relationship_type"] == rel:
            return edge
    raise AssertionError((source, target, rel))


def test_fixture_runner_produces_required_nodes():
    node_ids = {n["node_id"] for n in _payload()["candidate_graph"]["nodes"]}
    assert {
        "quest_clear_glowkindle_rats",
        "enc_glowkindle_cellar_rats",
        "npc_glowkindle",
        "creature_rat_swarm",
        "loc_glowkindle_cellar",
        "loc_glowkindle_brewery",
        "node:heroes-party",
    } <= node_ids


def test_fixture_runner_produces_required_deterministic_party_edges():
    payload = _payload()
    for source, target, rel in (
        ("node:heroes-party", "quest_clear_glowkindle_rats", "pursues"),
        ("node:heroes-party", "enc_glowkindle_cellar_rats", "participates_in"),
    ):
        edge = _edge(payload, source, target, rel)
        assert edge["context_anchor"] is True
        assert "deterministic_party_participation" in edge["warnings"]


def test_fixture_runner_produces_source_supported_encounter_job_edges():
    payload = _payload()
    _edge(payload, "enc_glowkindle_cellar_rats", "loc_glowkindle_cellar", "located_in")
    _edge(payload, "creature_rat_swarm", "enc_glowkindle_cellar_rats", "participates_in")
    _edge(payload, "quest_clear_glowkindle_rats", "creature_rat_swarm", "mission_targets")
    _edge(payload, "quest_clear_glowkindle_rats", "loc_glowkindle_cellar", "mission_focus")


def test_diagnostics_are_present_in_payload_and_report():
    payload = _payload()
    result_diag = payload["diagnostics"]["result_diagnostics"]
    cons_diag = payload["diagnostics"]["consolidation_diagnostics"]
    for key in ("dynamic_node_vocabulary_packet", "node_vocabulary_ablation", "encounter_job_edge_guidance"):
        assert key in result_diag
    for key in ("party_participation_attachment", "encounter_job_pass", "edge_predicate_issues", "dropped_edges_missing_endpoints"):
        assert key in cons_diag
    report = render_report(payload)
    for text in ("dynamic_node_vocabulary_packet", "node_vocabulary_ablation", "encounter_job_edge_guidance", "party_participation_attachment", "encounter_job_pass", "edge_predicate_issues", "dropped_edges_missing_endpoints"):
        assert text in report


def test_checks_object_has_expected_happy_path_values():
    checks = _payload()["checks"]
    for key, value in checks.items():
        assert value is (False if key in EXPECTED_FALSE else True)


def test_report_contains_required_sections_and_non_goal_language():
    report = render_report(_payload())
    for text in (
        "# Encounter/Job Dogfood Projection Report",
        "This is a deterministic fixture dogfood report.",
        "It does not call an LLM",
        "No corpus mutation",
        "Known limitations",
        "Next review step",
    ):
        assert text in report


def test_validator_default_does_not_write(tmp_path: Path):
    artifact_path = tmp_path / "missing.json"
    validate_payload(_payload(), compare_artifact=True, artifact_path=artifact_path)
    assert not artifact_path.exists()
