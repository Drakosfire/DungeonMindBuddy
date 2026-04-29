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
    _SLICE / "gold" / "scenario_c2_session20_pc_bucket_sentinel.json",
    _SLICE / "gold" / "scenario_rule3_locus_line16.json",
    _SLICE / "gold" / "scenario_c2_session20_pc_edge_slice_b1_multipc_recall.json",
    _SLICE / "gold" / "scenario_c2_session20_pc_edge_slice_party_boundary.json",
    _SLICE / "gold" / "scenario_c2_session20_pc_edge_slice_b2_abstain_pronoun.json",
    _SLICE / "gold" / "scenario_c2_session20_pc_edge_slice_b2_abstain_pronoun_context.json",
    _SLICE / "gold" / "scenario_c2_session20_pc_edge_slice_h1_h2_sentinel.json",
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


def test_collect_stage_b_diagnostic_bucket_expectation_soft_no_bd_violation() -> None:
    """BD mismatches are telemetry-only unless ``enforce_diagnostic_buckets``."""
    from evals.sentence_routing_retrieval_falsification.grader import collect_stage_b_violations
    from evals.sentence_routing_retrieval_falsification.route_schema import RouteRow

    manifest = {"hub_a"}
    expected = {"u1"}
    routes = [
        RouteRow(
            unit_id="u1",
            assigned_hubs=[],
            confidence="high",
            rationale="x",
            needs_new_hub_candidate=False,
            routing_diagnostic_bucket="true_empty",
        ),
    ]
    gold = {
        "diagnostic_buckets": {"u1": "npc_placeholder"},
        "enforce_diagnostic_buckets": False,
    }
    viol, telem = collect_stage_b_violations(
        routes, gold, manifest_slugs=manifest, expected_unit_ids=expected
    )
    assert not any(v.startswith("BD:") for v in viol)
    db = telem["stage_b_unit_breakdown"]["diagnostic_bucket_expectations"]
    assert db["defined"] == 1 and db["pass"] == 0 and db["fail"] == 1 and db["enforce"] is False


def test_stage_b_violation_only_telemetry_counts_diagnostic_null_b0() -> None:
    from evals.sentence_routing_retrieval_falsification.grader import (
        stage_b_violation_only_telemetry,
    )

    violations = [
        (
            "B0: routes JSON invalid: 1 validation error for RoutesEnvelope\n"
            "routes.6\n"
            "  Value error, routing_diagnostic_bucket must be null when assigned_hubs is "
            "non-empty [type=value_error]"
        )
    ]

    telem = stage_b_violation_only_telemetry(violations, expected_unit_ids={"u1", "u2"})
    bd = telem["stage_b_unit_breakdown"]
    assert bd["sentence_unit_count"] == 2
    assert bd["must_route"] is None
    assert bd["violation_line_count"] == 1
    buckets = bd["violation_failure_buckets"]
    assert buckets["b0_schema_row_integrity"] == 1
    assert buckets["b0_invalid_diagnostic_with_assigned_hubs"] == 1
    assert buckets["b0_diagnostic_null_when_assigned"] == 1
    assert buckets["non_gate"] == 0


def test_stage_b_violation_only_telemetry_counts_gold_gates_when_no_routes() -> None:
    """When wire JSON cannot be parsed at all, gold gate totals still appear (all fail vs empty map)."""
    from evals.sentence_routing_retrieval_falsification.grader import (
        stage_b_violation_only_telemetry,
    )

    violations = ["B0: routes JSON invalid: totally broken"]
    gold = {
        "must_route": [{"unit_id": "u1", "expected_hubs": ["hub_a"]}],
        "must_abstain": [{"unit_id": "u2", "max_assigned_hubs": 0}],
    }
    telem = stage_b_violation_only_telemetry(
        violations,
        expected_unit_ids={"u1", "u2"},
        gold_routing=gold,
        party_expansion_slugs=None,
    )
    bd = telem["stage_b_unit_breakdown"]
    assert bd["gold_gate_checks_total"] == 2
    assert bd["gold_gate_checks_pass"] == 0
    assert bd["gold_gate_checks_fail"] == 2
    assert bd["must_route"]["gold_checks"] == 1
    assert bd["must_abstain"]["gold_checks"] == 1
    assert bd["gold_gates_from_empty_routes"] is True


def test_coerce_wire_routes_payload_allows_parse_after_illegal_diagnostic_with_hubs() -> None:
    from evals.sentence_routing_retrieval_falsification.route_schema import (
        SCHEMA_SENTENCE_HUB_ROUTES_V1,
        coerce_wire_routes_payload_for_grading,
        parse_routes_envelope,
    )

    raw = {
        "schema": SCHEMA_SENTENCE_HUB_ROUTES_V1,
        "routes": [
            {
                "unit_id": "u1",
                "assigned_hubs": ["some_npc"],
                "confidence": "high",
                "rationale": "x",
                "needs_new_hub_candidate": False,
                "routing_diagnostic_bucket": "event_or_object_placeholder",
            },
        ],
    }
    manifest = [{"slug": "some_npc", "subject_class": "npc", "path": "x.md"}]
    with pytest.raises(Exception):
        parse_routes_envelope(raw, manifest_jsonable=manifest)
    fixed = coerce_wire_routes_payload_for_grading(raw, manifest_jsonable=manifest)
    env = parse_routes_envelope(fixed, manifest_jsonable=manifest)
    assert env.routes[0].routing_diagnostic_bucket is None
    assert env.routes[0].assigned_hubs == ["some_npc"]


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


def test_iter_stage_b_gold_check_results_matches_aggregate_counts() -> None:
    from evals.sentence_routing_retrieval_falsification.grader import (
        _gold_row_pass_fail,
        iter_stage_b_gold_check_results,
        stage_b_routes_by_id_normalized,
    )
    from evals.sentence_routing_retrieval_falsification.route_schema import RouteRow

    manifest = {"hub_a", "hub_b"}
    routes = [
        RouteRow(
            unit_id="u1",
            assigned_hubs=["hub_a"],
            confidence="high",
            rationale="r1",
            needs_new_hub_candidate=False,
        ),
        RouteRow(
            unit_id="u2",
            assigned_hubs=["hub_a", "hub_b"],
            confidence="high",
            rationale="r2",
            needs_new_hub_candidate=False,
        ),
    ]
    gold = {
        "must_route": [{"unit_id": "u1", "expected_hubs": ["hub_a", "hub_b"]}],
        "must_abstain": [{"unit_id": "u2", "max_assigned_hubs": 0, "needs_new_hub_candidate": False}],
    }
    by_id = stage_b_routes_by_id_normalized(routes, manifest)
    checks = iter_stage_b_gold_check_results(by_id, gold)
    assert len(checks) == 2
    mr_pass, mr_fail, ma_pass, ma_fail, pinned = _gold_row_pass_fail(by_id, gold)
    assert sum(1 for c in checks if c["gate"] == "must_route" and c["passed"]) == mr_pass
    assert sum(1 for c in checks if c["gate"] == "must_route" and not c["passed"]) == mr_fail
    assert sum(1 for c in checks if c["gate"] == "must_abstain" and c["passed"]) == ma_pass
    assert sum(1 for c in checks if c["gate"] == "must_abstain" and not c["passed"]) == ma_fail
    assert pinned == {"u1", "u2"}


def test_collect_stage_b_unit_breakdown_telemetry() -> None:
    from evals.sentence_routing_retrieval_falsification.grader import collect_stage_b_violations
    from evals.sentence_routing_retrieval_falsification.route_schema import RouteRow

    manifest = {"hub_a", "hub_b"}
    expected = {"u1", "u2", "u3"}
    routes = [
        RouteRow(
            unit_id="u1",
            assigned_hubs=["hub_a"],
            confidence="high",
            rationale="r1",
            needs_new_hub_candidate=False,
        ),
        RouteRow(
            unit_id="u2",
            assigned_hubs=["hub_a", "hub_b"],
            confidence="high",
            rationale="r2",
            needs_new_hub_candidate=False,
        ),
        RouteRow(
            unit_id="u3",
            assigned_hubs=[],
            confidence="high",
            rationale="r3",
            needs_new_hub_candidate=False,
        ),
    ]
    gold = {
        "must_route": [{"unit_id": "u1", "expected_hubs": ["hub_a", "hub_b"]}],
        "must_abstain": [{"unit_id": "u2", "max_assigned_hubs": 0, "needs_new_hub_candidate": False}],
    }
    viol, telem = collect_stage_b_violations(
        routes, gold, manifest_slugs=manifest, expected_unit_ids=expected
    )
    bd = telem["stage_b_unit_breakdown"]
    assert bd["sentence_unit_count"] == 3
    assert bd["gold_pinned_distinct_unit_count"] == 2
    assert bd["unpinned_sentence_unit_count"] == 1
    assert bd["must_route"] == {"gold_checks": 1, "pass": 0, "fail": 1}
    assert bd["must_abstain"] == {"gold_checks": 1, "pass": 0, "fail": 1}
    assert bd["gold_gate_checks_total"] == 2
    assert bd["gold_gate_checks_pass"] == 0
    assert bd["gold_gate_checks_fail"] == 2
    assert bd["violation_line_count"] == len(viol)
    bk = bd["violation_failure_buckets"]
    assert bk["b1_missing_expected_hub"] == 1
    assert bk["b2_over_assigned"] == 1


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


def test_normalize_assigned_hubs_karesmine_alias() -> None:
    from evals.sentence_routing_retrieval_falsification.route_schema import normalize_assigned_hubs_for_manifest

    m = {"karsemine", "caelynn"}
    assert normalize_assigned_hubs_for_manifest(["karesmine", "caelynn"], m) == ["karsemine", "caelynn"]
    assert normalize_assigned_hubs_for_manifest(["karsemine", "karesmine"], m) == ["karsemine"]


def test_normalize_sentence_units_text_karesmine() -> None:
    from evals.sentence_routing_retrieval_falsification.route_schema import (
        normalize_sentence_units_text_for_manifest,
    )

    units = [{"unit_id": "u1", "line_start": 1, "line_end": 1, "text": "Ephanna and Karesmine fight."}]
    out = normalize_sentence_units_text_for_manifest(units, {"karsemine", "ephanna"})
    assert out[0]["text"] == "Ephanna and Karsemine fight."
    assert units[0]["text"] == "Ephanna and Karesmine fight."


def test_normalize_sentence_units_text_baergrom_typos() -> None:
    from evals.sentence_routing_retrieval_falsification.route_schema import (
        normalize_sentence_units_text_for_manifest,
    )

    units = [
        {
            "unit_id": "u1",
            "line_start": 1,
            "line_end": 1,
            "text": "Beargrom and Baegrom see Baergom; Baergorm nods.",
        }
    ]
    out = normalize_sentence_units_text_for_manifest(units, {"baergrom", "bonogo"})
    assert out[0]["text"] == "Baergrom and Baergrom see Baergrom; Baergrom nods."


def test_normalize_assigned_hubs_baergrom_slug_typos() -> None:
    from evals.sentence_routing_retrieval_falsification.route_schema import normalize_assigned_hubs_for_manifest

    m = {"baergrom", "caelynn"}
    assert normalize_assigned_hubs_for_manifest(["baergorm", "baegrom", "baergom"], m) == ["baergrom"]


def test_collect_stage_b_accepts_karesmine_slug_alias() -> None:
    from evals.sentence_routing_retrieval_falsification.grader import collect_stage_b_violations
    from evals.sentence_routing_retrieval_falsification.route_schema import RouteRow

    manifest = {"karsemine", "caelynn"}
    expected = {"u1", "u2"}
    routes = [
        RouteRow(
            unit_id="u1",
            assigned_hubs=["karesmine"],
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
    gold = {"must_route": [{"unit_id": "u1", "expected_hubs": ["karsemine"]}]}
    viol, _ = collect_stage_b_violations(
        routes, gold, manifest_slugs=manifest, expected_unit_ids=expected
    )
    assert not any("missing expected hubs" in x for x in viol)
    assert not any("B0b" in x for x in viol)


def test_load_sentence_units_prefers_scenario_embedded_list() -> None:
    from evals.sentence_routing_retrieval_falsification.step2_route_run import _load_sentence_units

    scenario = {
        "sentence_units": [
            {
                "unit_id": "u-embedded-01",
                "path": "corpus/x.md",
                "line_start": 1,
                "line_end": 1,
                "text": "Slice-only unit.",
            }
        ],
        "input": {
            "recap_relative_path": "corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md",
        },
    }
    units = _load_sentence_units(scenario, _REPO, None)
    assert len(units) == 1
    assert units[0]["unit_id"] == "u-embedded-01"


def test_build_messages_includes_routing_context_for_pc_party_names() -> None:
    from evals.sentence_routing_retrieval_falsification.step2_route_run import _build_messages

    msgs, _rid = _build_messages(
        inp={
            "campaign_id": "longmont-c2",
            "session": 20,
            "recap_relative_path": "corpus/x.md",
            "pc_party_names": ["  Questionable Company  ", ""],
        },
        manifest=[{"slug": "a", "path": "a.md", "subject_class": "pc"}],
        units_json=[{"unit_id": "u1", "text": "noop"}],
    )
    user = json.loads(msgs[1]["content"])
    assert user["routing_context"]["pc_party_names"] == ["Questionable Company"]
    assert user["routing_context"]["pc_roster_slugs"] == ["a"]
    assert "session_pc_roster_slugs" not in user["routing_context"]
    assert "routing_context.pc_party_names" in msgs[0]["content"]
    assert "routing_context.session_pc_roster_slugs" in msgs[0]["content"]
    assert "Roster copy rule" in msgs[0]["content"]
    assert "Previous-unit pronoun binding" in msgs[0]["content"]
    assert "quote both the binding phrase from the previous unit" in msgs[0]["content"]


def test_build_messages_omits_routing_context_without_pc_party_names() -> None:
    from evals.sentence_routing_retrieval_falsification.step2_route_run import _build_messages

    msgs, _rid = _build_messages(
        inp={
            "campaign_id": "x",
            "session": 1,
            "recap_relative_path": "p.md",
        },
        manifest=[],
        units_json=[],
    )
    user = json.loads(msgs[1]["content"])
    assert "routing_context" not in user


def test_build_messages_loads_pc_party_names_from_party_registry() -> None:
    from evals.sentence_routing_retrieval_falsification.step2_route_run import _build_messages

    recap = (
        "corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/"
        "Session Recaps/Session 20 - Recap.md"
    )
    msgs, _rid = _build_messages(
        inp={
            "campaign_id": "longmont-c2",
            "session": 20,
            "recap_relative_path": recap,
        },
        manifest=[{"slug": "a", "path": "a.md", "subject_class": "pc"}],
        units_json=[{"unit_id": "u1", "text": "noop"}],
        corpus_root=_REPO,
    )
    user = json.loads(msgs[1]["content"])
    assert user["routing_context"]["pc_party_names"] == ["Questionable Company"]
    assert user["routing_context"]["pc_roster_slugs"] == ["a"]
    assert user["routing_context"]["session_pc_roster_slugs"] == ["a"]


def test_expand_the_party_sentinel_replaces_with_session_roster() -> None:
    from evals.sentence_routing_retrieval_falsification.route_schema import (
        RouteRow,
        THE_PARTY_ROUTE_SENTINEL,
        expand_the_party_sentinel,
    )

    routes = [
        RouteRow(
            unit_id="u1",
            assigned_hubs=[THE_PARTY_ROUTE_SENTINEL],
            confidence="high",
            rationale="group beat",
            needs_new_hub_candidate=False,
        )
    ]
    out = expand_the_party_sentinel(routes, ["alpha", "beta"])
    assert out[0].assigned_hubs == ["alpha", "beta"]


def test_strip_pc_slugs_when_party_drops_only_manifest_pcs() -> None:
    from evals.sentence_routing_retrieval_falsification.route_schema import (
        THE_PARTY_ROUTE_SENTINEL,
        manifest_pc_slug_set,
        strip_pc_slugs_when_the_party_present,
    )

    manifest = [
        {"slug": "baergrom", "subject_class": "pc", "path": "x"},
        {"slug": "captain_lysandra", "subject_class": "npc", "path": "y"},
    ]
    pcs = manifest_pc_slug_set(manifest)
    assert strip_pc_slugs_when_the_party_present(
        ["the_party", "baergrom", "captain_lysandra"], pcs
    ) == ["the_party", "captain_lysandra"]
    assert strip_pc_slugs_when_the_party_present(["the_party", "baergrom"], pcs) == [
        THE_PARTY_ROUTE_SENTINEL
    ]


def test_strip_pc_slugs_when_party_no_manifest_falls_back_to_sentinel_only() -> None:
    from evals.sentence_routing_retrieval_falsification.route_schema import (
        THE_PARTY_ROUTE_SENTINEL,
        strip_pc_slugs_when_the_party_present,
    )

    assert strip_pc_slugs_when_the_party_present(["the_party", "captain_lysandra"], set()) == [
        THE_PARTY_ROUTE_SENTINEL
    ]


def test_parse_routes_envelope_strips_pc_slugs_using_manifest() -> None:
    from evals.sentence_routing_retrieval_falsification.route_schema import parse_routes_envelope

    manifest = [
        {"slug": "a", "subject_class": "pc", "path": "p"},
        {"slug": "npc_x", "subject_class": "npc", "path": "n"},
    ]
    env = parse_routes_envelope(
        {
            "schema": "sentence_hub_routes_v1",
            "routes": [
                {
                    "unit_id": "u1",
                    "assigned_hubs": ["the_party", "a", "npc_x"],
                    "confidence": "high",
                    "rationale": "x",
                    "needs_new_hub_candidate": False,
                }
            ],
        },
        manifest_jsonable=manifest,
    )
    assert env.routes[0].assigned_hubs == ["the_party", "npc_x"]


def test_parse_routes_envelope_rejects_npc_placeholder_without_pc_assignment() -> None:
    from pytest import raises

    from evals.sentence_routing_retrieval_falsification.route_schema import parse_routes_envelope

    manifest = [
        {"slug": "npc_x", "subject_class": "npc", "path": "n"},
        {"slug": "place_x", "subject_class": "location", "path": "l"},
    ]
    with raises(ValueError, match="requires at least one PC hub or the_party"):
        parse_routes_envelope(
            {
                "schema": "sentence_hub_routes_v1",
                "routes": [
                    {
                        "unit_id": "u1",
                        "assigned_hubs": ["npc_x"],
                        "confidence": "high",
                        "rationale": "routed NPC hub, so no placeholder needed",
                        "needs_new_hub_candidate": False,
                        "routing_diagnostic_bucket": "npc_placeholder",
                    }
                ],
            },
            manifest_jsonable=manifest,
        )


def test_route_row_allows_npc_placeholder_with_pc_hubs() -> None:
    from evals.sentence_routing_retrieval_falsification.route_schema import RouteRow

    r = RouteRow(
        unit_id="u1",
        assigned_hubs=["caelynn"],
        confidence="high",
        rationale="PC + named NPC focal without NPC hub",
        needs_new_hub_candidate=False,
        routing_diagnostic_bucket="npc_placeholder",
    )
    assert r.routing_diagnostic_bucket == "npc_placeholder"


def test_route_row_rejects_non_npc_placeholder_bucket_with_hubs() -> None:
    from pydantic import ValidationError

    from evals.sentence_routing_retrieval_falsification.route_schema import RouteRow

    with pytest.raises(ValidationError):
        RouteRow(
            unit_id="u1",
            assigned_hubs=["caelynn"],
            confidence="high",
            rationale="bad mix",
            needs_new_hub_candidate=False,
            routing_diagnostic_bucket="true_empty",
        )


def test_expand_the_party_sentinel_appends_non_pc_extras_after_roster() -> None:
    from evals.sentence_routing_retrieval_falsification.route_schema import (
        RouteRow,
        THE_PARTY_ROUTE_SENTINEL,
        expand_the_party_sentinel,
    )

    routes = [
        RouteRow(
            unit_id="u1",
            assigned_hubs=[THE_PARTY_ROUTE_SENTINEL, "npc_x"],
            confidence="high",
            rationale="party + npc",
            needs_new_hub_candidate=False,
        )
    ]
    out = expand_the_party_sentinel(routes, ["alpha", "beta"])
    assert out[0].assigned_hubs == ["alpha", "beta", "npc_x"]


def test_collect_stage_b_must_route_the_party_gold_uses_expansion() -> None:
    from evals.sentence_routing_retrieval_falsification.grader import collect_stage_b_violations
    from evals.sentence_routing_retrieval_falsification.route_schema import RouteRow

    manifest = {"a", "b", "c"}
    expected = {"u1"}
    routes = [
        RouteRow(
            unit_id="u1",
            assigned_hubs=["a", "b", "c"],
            confidence="high",
            rationale="ok",
            needs_new_hub_candidate=False,
        ),
    ]
    gold = {"must_route": [{"unit_id": "u1", "expected_hubs": ["the_party"], "max_extra_hubs": 0}]}
    viol, _ = collect_stage_b_violations(
        routes,
        gold,
        manifest_slugs=manifest,
        expected_unit_ids=expected,
        party_expansion_slugs=["a", "b", "c"],
    )
    assert not viol


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


def test_routing_prompt_variants_have_distinct_ids() -> None:
    from evals.sentence_routing_retrieval_falsification.routing_prompt import (
        PROMPT_VARIANT_APPENDS,
        ROUTING_PROMPT_BASE_ID,
        build_routing_system_prompt,
    )

    assert "party_continuation_v1" in PROMPT_VARIANT_APPENDS
    assert "party_roster_strict_v1" in PROMPT_VARIANT_APPENDS

    base_text, base_id = build_routing_system_prompt(None)
    v1_text, v1_id = build_routing_system_prompt("party_continuation_v1")
    strict_text, strict_id = build_routing_system_prompt("party_roster_strict_v1")

    assert base_id == ROUTING_PROMPT_BASE_ID
    assert v1_id != base_id
    assert strict_id != base_id
    assert strict_id != v1_id, "party_roster_strict_v1 must produce a distinct prompt id"

    assert v1_text.startswith(base_text)
    assert strict_text.startswith(v1_text), (
        "party_roster_strict_v1 must compose the party_continuation_v1 body so "
        "the strict variant is a proper superset for ablation purposes"
    )
    assert "Narrow-multi-PC counter-example" in strict_text
    assert "Marla then grapples Bonogo" in strict_text


def test_stage_b_cohort_summary_records_prompt_ids() -> None:
    from evals.sentence_routing_retrieval_falsification.sentence_routing_stage_b_cohort_report import (
        StageBRunRecord,
        build_cohort_payload,
    )

    payload = build_cohort_payload(
        [
            StageBRunRecord(
                run_index=0,
                gates_passed=False,
                scenario_estimated_cost_usd=0.01,
                sidecar_json_path="run.json",
                stage_b_violation_count=1,
                routing_prompt_base_id="base123",
                routing_prompt_id="full123",
            )
        ],
        model_id="model",
        scenario_id="scenario",
        prompt_variant=None,
    )
    assert payload["prompt_variant"] is None
    assert payload["routing_prompt_base_id"] == "base123"
    assert payload["routing_prompt_id"] == "full123"
    assert payload["runs"][0]["routing_prompt_base_id"] == "base123"
    assert payload["runs"][0]["routing_prompt_id"] == "full123"
