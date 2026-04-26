"""``route_sentence_units_to_hubs`` hub routing grader + manifest validation (legacy: Stage B)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]
_SLICE = _REPO / "evals" / "sentence_routing_retrieval_falsification"
_SCENARIO = _SLICE / "gold" / "scenario_mini.json"
_SCENARIO_TEMPLATE = _SLICE / "gold" / "scenario_real_recap_template.json"
_PC_SCENARIOS = [
    _SLICE / "gold" / "scenario_c1_session1_pc.json",
    _SLICE / "gold" / "scenario_c1_session2_pc.json",
    _SLICE / "gold" / "scenario_c1_session3_pc.json",
    _SLICE / "gold" / "scenario_c2_session20_pc.json",
]


def test_manifest_rejects_duplicate_slugs() -> None:
    from evals.sentence_routing_retrieval_falsification.route_schema import validate_hub_manifest

    entries = [
        {"slug": "a", "path": "x.md", "subject_class": "npc"},
        {"slug": "a", "path": "y.md", "subject_class": "npc"},
    ]
    v = validate_hub_manifest(entries, corpus_root=_REPO, validate_paths=False)
    assert any("duplicate manifest slug" in x for x in v)


def test_collect_stage_b_must_route_subset() -> None:
    from evals.sentence_routing_retrieval_falsification.grader import collect_stage_b_violations
    from evals.sentence_routing_retrieval_falsification.route_schema import RouteRow

    manifest = {"hub_a", "hub_b"}
    expected = {"u1", "u2"}
    routes = [
        RouteRow(
            unit_id="u1",
            assigned_hubs=["hub_a"],
            confidence="high",
            rationale="x",
            needs_new_hub_candidate=False,
        ),
        RouteRow(
            unit_id="u2",
            assigned_hubs=[],
            confidence="low",
            rationale="y",
            needs_new_hub_candidate=False,
        ),
    ]
    gold = {"must_route": [{"unit_id": "u1", "expected_hubs": ["hub_a", "hub_b"]}]}
    viol, _ = collect_stage_b_violations(
        routes, gold, manifest_slugs=manifest, expected_unit_ids=expected
    )
    assert any("missing expected hubs" in x for x in viol)


def test_collect_stage_b_must_abstain() -> None:
    from evals.sentence_routing_retrieval_falsification.grader import collect_stage_b_violations
    from evals.sentence_routing_retrieval_falsification.route_schema import RouteRow

    manifest = {"hub_a"}
    expected = {"u1"}
    routes = [
        RouteRow(
            unit_id="u1",
            assigned_hubs=["hub_a"],
            confidence="high",
            rationale="z",
            needs_new_hub_candidate=False,
        ),
    ]
    gold = {"must_abstain": [{"unit_id": "u1", "max_assigned_hubs": 0, "needs_new_hub_candidate": False}]}
    viol, _ = collect_stage_b_violations(
        routes, gold, manifest_slugs=manifest, expected_unit_ids=expected
    )
    assert any("must_abstain" in x or "max_assigned_hubs" in x for x in viol)


def test_parse_routes_envelope_rejects_bad_schema() -> None:
    from pydantic import ValidationError

    from evals.sentence_routing_retrieval_falsification.route_schema import parse_routes_envelope

    with pytest.raises(ValidationError):
        parse_routes_envelope({"schema": "wrong", "routes": []})


def test_normalize_gold_match_resolves_line_index() -> None:
    from evals.sentence_routing_retrieval_falsification.grader import normalize_gold_routing_matches

    units = [
        {"unit_id": "u-L0003-01", "line_start": 3, "line_end": 3, "text": "First."},
        {"unit_id": "u-L0003-02", "line_start": 3, "line_end": 3, "text": "Second."},
    ]
    gold = {
        "must_route": [
            {"match": {"line_start": 3, "index_on_line": 2}, "expected_hubs": ["hub_b"]},
        ]
    }
    out, err = normalize_gold_routing_matches(gold, units)
    assert not err
    assert out["must_route"][0]["unit_id"] == "u-L0003-02"
    assert "match" not in out["must_route"][0]


def test_normalize_gold_match_text_substring_filter() -> None:
    from evals.sentence_routing_retrieval_falsification.grader import normalize_gold_routing_matches

    units = [
        {"unit_id": "a", "line_start": 1, "line_end": 1, "text": "Alpha"},
        {"unit_id": "b", "line_start": 1, "line_end": 1, "text": "Beta only"},
    ]
    gold = {"must_route": [{"match": {"line_start": 1, "index_on_line": 1, "text_substring": "Beta"}, "expected_hubs": ["h"]}]}
    out, err = normalize_gold_routing_matches(gold, units)
    assert not err
    assert out["must_route"][0]["unit_id"] == "b"


def test_normalize_gold_unit_id_disagrees_with_match_errors() -> None:
    from evals.sentence_routing_retrieval_falsification.grader import normalize_gold_routing_matches

    units = [{"unit_id": "u1", "line_start": 2, "line_end": 2, "text": "x"}]
    gold = {"must_route": [{"unit_id": "wrong", "match": {"line_start": 2, "index_on_line": 1}, "expected_hubs": ["h"]}]}
    _out, err = normalize_gold_routing_matches(gold, units)
    assert any("disagrees" in e for e in err)


def test_step2_no_llm_passes_mini_scenario() -> None:
    cmd = [
        sys.executable,
        "-m",
        "evals.sentence_routing_retrieval_falsification.step2_route_run",
        "--scenario-json",
        str(_SCENARIO),
        "--corpus-root",
        str(_REPO),
        "--no-llm",
        "--no-writes",
    ]
    proc = subprocess.run(cmd, cwd=str(_REPO), capture_output=True, text=True, check=False)
    assert proc.returncode == 0, proc.stderr + proc.stdout


def test_step2_no_llm_passes_real_recap_template_scenario() -> None:
    cmd = [
        sys.executable,
        "-m",
        "evals.sentence_routing_retrieval_falsification.step2_route_run",
        "--scenario-json",
        str(_SCENARIO_TEMPLATE),
        "--corpus-root",
        str(_REPO),
        "--no-llm",
        "--no-writes",
    ]
    proc = subprocess.run(cmd, cwd=str(_REPO), capture_output=True, text=True, check=False)
    assert proc.returncode == 0, proc.stderr + proc.stdout


@pytest.mark.parametrize("scenario_path", _PC_SCENARIOS, ids=lambda p: p.stem)
def test_step2_no_llm_passes_pc_gold_scenarios(scenario_path: Path) -> None:
    cmd = [
        sys.executable,
        "-m",
        "evals.sentence_routing_retrieval_falsification.step2_route_run",
        "--scenario-json",
        str(scenario_path),
        "--corpus-root",
        str(_REPO),
        "--no-llm",
        "--no-writes",
    ]
    proc = subprocess.run(cmd, cwd=str(_REPO), capture_output=True, text=True, check=False)
    assert proc.returncode == 0, proc.stderr + proc.stdout


def test_step2_cohort_n2_no_llm_writes_summary() -> None:
    cmd = [
        sys.executable,
        "-m",
        "evals.sentence_routing_retrieval_falsification.step2_route_run",
        "--scenario-json",
        str(_SCENARIO),
        "--corpus-root",
        str(_REPO),
        "--n",
        "2",
        "--no-llm",
    ]
    proc = subprocess.run(cmd, cwd=str(_REPO), capture_output=True, text=True, check=False)
    assert proc.returncode == 0, proc.stderr + proc.stdout
    assert "sentence_routing_stage_b_cohort_summary" in proc.stderr, proc.stderr
