"""Offline tests for the Stage C NPC-candidate-identification grader.

All tests are pure offline — no network calls, no model invocations. Synthetic
registry + synthetic events fixtures live inline so the tests don't depend on
the canonical S20 corpus state.

Coverage:

* NC1: valid PASS; missing array; bad slug format; out-of-range index;
       non-registry slug in tracked_active
* NC2: clean PASS; PC slug leak in tracked_active; PC name leak in candidate
       descriptor
* NC3: full recall PASS; missing tracked NPC FAIL; alias-only floor missing
       FAIL; soft-bonus telemetry hit + miss
* NC4: cited evidence PASS; missing evidence FAIL
* NC5: under window PASS; over window FAIL
* Top-level: all-pass shape; gates_passed_str count
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from evals.stage_c_npc_candidates_vertical_slice.grader import (
    _grade_nc1,
    _grade_nc2,
    _grade_nc3,
    _grade_nc4,
    _grade_nc5,
    _pc_match_terms,
    grade_stage_c,
)


# ---------------------------------------------------------------------------
# Synthetic fixtures
# ---------------------------------------------------------------------------


def _registry() -> list[dict]:
    return [
        {
            "slug": "thrin_branchborn",
            "display_name": "Thrin Branchborn",
            "aliases": ["Thrin"],
            "status": "tracked",
            "first_session": 17,
            "last_session": 21,
            "hub_path": "Longmont Campaign/Campaign 2/NPCs/thrin_branchborn/",
            "setting_hub_path": None,
            "notes": "",
        },
        {
            "slug": "stacey_brambleback",
            "display_name": "Stacey Brambleback",
            "aliases": ["Stacey"],
            "status": "tracked",
            "first_session": 19,
            "last_session": 20,
            "hub_path": "Elderwyld/Cities and Towns/Mossford/NPCs/stacey_brambleback/",
            "setting_hub_path": None,
            "notes": "",
        },
        {
            "slug": "sheriff_roderic_marr",
            "display_name": "Sheriff Roderic Marr",
            "aliases": ["Sheriff Marr"],
            "status": "background",
            "first_session": 19,
            "last_session": 20,
            "hub_path": "Elderwyld/Cities and Towns/Mossford/NPCs/sheriff_roderic_marr/",
            "setting_hub_path": None,
            "notes": "",
        },
        {
            "slug": "dustwalker",
            "display_name": "Dustwalker",
            "aliases": [],
            "status": "tracked",
            "first_session": 3,
            "last_session": 14,
            "hub_path": "Longmont Campaign/Campaign 2/NPCs/dustwalker/",
            "setting_hub_path": None,
            "notes": "",
        },
    ]


def _events() -> list[dict]:
    """3 events: thrin participates, stacey participates (alias-only), kirfan referenced."""
    return [
        {
            "event_class": "combat",
            "time_scope": "scene",
            "certainty": "observed",
            "participants": ["caelynn", "ephanna", "thrin_branchborn"],
            "referenced_slugs": [],
        },
        {
            "event_class": "social_conflict",
            "time_scope": "scene",
            "certainty": "observed",
            "participants": ["bonogo", "stacey"],
            "referenced_slugs": [],
        },
        {
            "event_class": "discovery",
            "time_scope": "scene",
            "certainty": "observed",
            "participants": ["bonogo", "stafl"],
            "referenced_slugs": ["kirfan"],
        },
    ]


def _gold() -> dict:
    return {
        "input": {
            "pc_roster": [
                {"slug": "bonogo", "display_name": "Bonogo", "aliases": []},
                {"slug": "caelynn", "display_name": "Caelynn", "aliases": []},
                {"slug": "ephanna", "display_name": "Ephanna", "aliases": []},
                {"slug": "stafl", "display_name": "Stafl", "aliases": []},
            ],
        },
        "grading": {
            "expected_tracked_active_minimum": [
                "thrin_branchborn",
                "stacey_brambleback",
            ],
            "expected_new_candidates_should_include_at_least_one_of": ["kirfan"],
            "max_total_candidates": 25,
            "pc_roster_for_negative_check": ["bonogo", "caelynn", "ephanna", "stafl"],
        },
    }


def _good_output() -> dict:
    return {
        "tracked_npcs_active": [
            {
                "slug": "thrin_branchborn",
                "evidence_event_indices": [0],
                "appearance_count": 1,
            },
            {
                "slug": "stacey_brambleback",
                "evidence_event_indices": [1],
                "appearance_count": 1,
            },
        ],
        "new_npc_candidates": [
            {
                "descriptor": "Kirfan",
                "suggested_slug": "kirfan",
                "evidence_event_indices": [2],
                "rationale": "Named NPC referenced but not in registry.",
            },
        ],
        "unresolved_descriptors": [],
    }


# ---------------------------------------------------------------------------
# NC1 — structure validity
# ---------------------------------------------------------------------------


class TestNC1Structure:
    def test_valid_output_passes(self):
        verdict, violations, _ = _grade_nc1(_good_output(), _events(), _registry())
        assert verdict == "PASS", violations
        assert violations == []

    def test_missing_top_level_array_fails(self):
        bad = {"tracked_npcs_active": [], "new_npc_candidates": []}
        verdict, violations, _ = _grade_nc1(bad, _events(), _registry())
        assert verdict == "FAIL"
        assert any("unresolved_descriptors" in v for v in violations)

    def test_bad_slug_format_in_new_candidate_fails(self):
        bad = _good_output()
        bad["new_npc_candidates"][0]["suggested_slug"] = "Kirfan!"
        verdict, violations, _ = _grade_nc1(bad, _events(), _registry())
        assert verdict == "FAIL"
        assert any("^[a-z0-9_]+$" in v for v in violations)

    def test_out_of_range_event_index_fails(self):
        bad = _good_output()
        bad["tracked_npcs_active"][0]["evidence_event_indices"] = [99]
        verdict, violations, _ = _grade_nc1(bad, _events(), _registry())
        assert verdict == "FAIL"
        assert any("out of range" in v for v in violations)

    def test_non_registry_slug_in_tracked_active_fails(self):
        bad = _good_output()
        bad["tracked_npcs_active"].append({
            "slug": "not_a_real_npc",
            "evidence_event_indices": [0],
            "appearance_count": 1,
        })
        verdict, violations, _ = _grade_nc1(bad, _events(), _registry())
        assert verdict == "FAIL"
        assert any("not in registry" in v for v in violations)


# ---------------------------------------------------------------------------
# NC2 — PC negative-list cleanliness
# ---------------------------------------------------------------------------


class TestNC2PCLeak:
    def _terms(self):
        return _pc_match_terms(_gold()["input"]["pc_roster"])

    def test_clean_passes(self):
        pc_slugs_check = _gold()["grading"]["pc_roster_for_negative_check"]
        _, terms = self._terms()
        verdict, violations, _ = _grade_nc2(_good_output(), pc_slugs_check, terms)
        assert verdict == "PASS"
        assert violations == []

    def test_pc_slug_in_tracked_active_fails(self):
        bad = _good_output()
        bad["tracked_npcs_active"].append({
            "slug": "bonogo",
            "evidence_event_indices": [1],
            "appearance_count": 1,
        })
        pc_slugs_check = _gold()["grading"]["pc_roster_for_negative_check"]
        _, terms = self._terms()
        verdict, violations, telemetry = _grade_nc2(bad, pc_slugs_check, terms)
        assert verdict == "FAIL"
        assert any("'bonogo'" in v for v in violations)
        assert telemetry["pc_leaks"]

    def test_pc_name_in_candidate_descriptor_fails(self):
        bad = _good_output()
        bad["new_npc_candidates"].append({
            "descriptor": "Caelynn's mysterious shadow",
            "suggested_slug": "mysterious_shadow",
            "evidence_event_indices": [0],
            "rationale": "Some narrative shadow",
        })
        pc_slugs_check = _gold()["grading"]["pc_roster_for_negative_check"]
        _, terms = self._terms()
        verdict, violations, _ = _grade_nc2(bad, pc_slugs_check, terms)
        assert verdict == "FAIL"
        assert any("caelynn" in v.lower() for v in violations)


# ---------------------------------------------------------------------------
# NC3 — registry positive-list recall
# ---------------------------------------------------------------------------


class TestNC3RegistryRecall:
    def test_full_recall_passes(self):
        gold = _gold()
        verdict, violations, _ = _grade_nc3(
            _good_output(),
            _events(),
            _registry(),
            gold["grading"]["expected_tracked_active_minimum"],
        )
        assert verdict == "PASS", violations
        assert violations == []

    def test_missing_tracked_npc_in_events_fails(self):
        bad = _good_output()
        bad["tracked_npcs_active"] = [t for t in bad["tracked_npcs_active"]
                                      if t["slug"] != "thrin_branchborn"]
        gold = _gold()
        verdict, violations, telemetry = _grade_nc3(
            bad,
            _events(),
            _registry(),
            gold["grading"]["expected_tracked_active_minimum"],
        )
        assert verdict == "FAIL"
        assert any("thrin_branchborn" in v for v in violations)
        assert "thrin_branchborn" in telemetry["expected_tracked_active_missing"]

    def test_alias_only_floor_missing_fails(self):
        """stacey_brambleback is in expected_tracked_active_minimum even though
        the event slug is 'stacey' (alias). If the model fails to alias-resolve,
        the alias-floor check must catch it."""
        bad = _good_output()
        bad["tracked_npcs_active"] = [t for t in bad["tracked_npcs_active"]
                                      if t["slug"] != "stacey_brambleback"]
        gold = _gold()
        verdict, violations, telemetry = _grade_nc3(
            bad,
            _events(),
            _registry(),
            gold["grading"]["expected_tracked_active_minimum"],
        )
        assert verdict == "FAIL"
        assert any("stacey_brambleback" in v for v in violations)


# ---------------------------------------------------------------------------
# NC4 — new-candidate evidence discipline
# ---------------------------------------------------------------------------


class TestNC4Evidence:
    def test_cited_evidence_passes(self):
        verdict, violations, _ = _grade_nc4(_good_output(), _events())
        assert verdict == "PASS"
        assert violations == []

    def test_missing_evidence_fails(self):
        bad = _good_output()
        bad["new_npc_candidates"][0]["evidence_event_indices"] = []
        verdict, violations, _ = _grade_nc4(bad, _events())
        assert verdict == "FAIL"
        assert any("zero evidence" in v for v in violations)


# ---------------------------------------------------------------------------
# NC5 — count window
# ---------------------------------------------------------------------------


class TestNC5CountWindow:
    def test_under_window_passes(self):
        verdict, violations, _ = _grade_nc5(_good_output(), max_total_candidates=25)
        assert verdict == "PASS"
        assert violations == []

    def test_over_window_fails(self):
        bad = _good_output()
        bad["new_npc_candidates"] = [
            {
                "descriptor": f"NPC {i}",
                "suggested_slug": f"npc_{i}",
                "evidence_event_indices": [0],
                "rationale": "test",
            }
            for i in range(30)
        ]
        verdict, violations, telemetry = _grade_nc5(bad, max_total_candidates=25)
        assert verdict == "FAIL"
        assert telemetry["total_candidates"] == 30


# ---------------------------------------------------------------------------
# Top-level orchestrator
# ---------------------------------------------------------------------------


class TestGradeStageC:
    def test_all_pass_returns_5_5(self):
        out = grade_stage_c(_good_output(), _gold(), _events(), _registry())
        assert out["gates_passed"] == "5/5"
        assert out["all_gates_passed"] is True
        assert out["per_gate_verdict"] == {
            "NC1": "PASS",
            "NC2": "PASS",
            "NC3": "PASS",
            "NC4": "PASS",
            "NC5": "PASS",
        }
        assert out["telemetry"]["expected_new_candidate_coverage_hit"] is True

    def test_soft_bonus_miss_does_not_fail_gate(self):
        """If the model fails to surface kirfan but everything else is correct,
        gates still PASS — soft bonus is telemetry-only."""
        out_no_kirfan = _good_output()
        out_no_kirfan["new_npc_candidates"] = []
        result = grade_stage_c(out_no_kirfan, _gold(), _events(), _registry())
        assert result["all_gates_passed"] is True
        assert result["telemetry"]["expected_new_candidate_coverage_hit"] is False

    def test_pc_leak_fails_top_level(self):
        bad = _good_output()
        bad["tracked_npcs_active"].append({
            "slug": "bonogo",
            "evidence_event_indices": [1],
            "appearance_count": 1,
        })
        result = grade_stage_c(bad, _gold(), _events(), _registry())
        assert result["per_gate_verdict"]["NC2"] == "FAIL"
        assert result["all_gates_passed"] is False

    def test_telemetry_keys_present(self):
        out = grade_stage_c(_good_output(), _gold(), _events(), _registry())
        for key in (
            "tracked_active_count",
            "new_candidates_count",
            "unresolved_count",
            "registry_recall_ratio",
            "expected_tracked_active_missing",
            "expected_new_candidate_coverage_hit",
            "pc_leaks",
        ):
            assert key in out["telemetry"]
