"""Offline tests for the Stage D NPC entity-resolution grader + resolver.

All tests are pure offline — no network calls, no model invocations. Synthetic
registry + synthetic Stage C output fixtures live inline so the tests don't
depend on the canonical corpus state or Stage C cohort sidecars.

Coverage:

* ER1: valid PASS; missing array; bad slug format; orphan source_index;
       invalid resolution verb
* ER2: clean PASS; PC slug leak in resolved_entities;
       PC name leak in proposed_aliases.target_slug
* ER3: clean PASS; merge_to_registry_slug pointing at non-registry slug;
       merge_to_canonical_new_candidate pointing at unknown slug;
       must_not_merge forbidden pair both resolving to same canonical
* ER4: must_merge_clusters all collapse PASS; cluster split FAIL;
       must_resolve_unresolved still in unresolvable[] FAIL
* ER5: clean PASS; status not 'candidate' FAIL; hub_path not null FAIL;
       slug collides with registry FAIL
* Resolver: PC term in suggested_slug → unresolvable; slug-variant cluster
       (no registry hit) collapses to single canonical with longest slug
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from evals.stage_d_entity_resolution_vertical_slice.grader import (
    _grade_er1,
    _grade_er2,
    _grade_er3,
    _grade_er4,
    _grade_er5,
    grade_stage_d,
)
from evals.stage_d_entity_resolution_vertical_slice.step1_stage_d_run import (
    _slugs_should_cluster,
    resolve_stage_d,
)


# ---------------------------------------------------------------------------
# Synthetic fixtures
# ---------------------------------------------------------------------------


def _registry() -> list[dict]:
    return [
        {
            "slug": "captain_lysandra_ironveil",
            "display_name": "Captain Lysandra Ironveil",
            "aliases": ["Lysandra", "the captain"],
            "status": "tracked",
            "first_session": 8,
            "last_session": 13,
            "hub_path": "Elderwyld/Cities and Towns/Mirathorn/NPCs/captain_lysandra_ironveil/",
            "setting_hub_path": None,
            "notes": "",
        },
        {
            "slug": "torbin_jove",
            "display_name": "Torbin Jove",
            "aliases": [],
            "status": "tracked",
            "first_session": 4,
            "last_session": 13,
            "hub_path": "Elderwyld/Cities and Towns/Mirathorn/NPCs/torbin_jove/",
            "setting_hub_path": None,
            "notes": "",
        },
        {
            "slug": "bubbles_the_float_goat",
            "display_name": "Bubbles the Float Goat",
            "aliases": ["Bubbles"],
            "status": "candidate",
            "first_session": 3,
            "last_session": 3,
            "hub_path": None,
            "setting_hub_path": None,
            "notes": "",
        },
    ]


def _pc_roster() -> list[dict]:
    return [
        {"slug": "bonogo", "display_name": "Bonogo", "aliases": []},
        {"slug": "caelynn", "display_name": "Caelynn", "aliases": []},
        {"slug": "stafl", "display_name": "Stafl", "aliases": []},
    ]


def _stage_c_output() -> dict:
    return {
        "tracked_npcs_active": [],
        "new_npc_candidates": [
            {
                "descriptor": "Bubbles the Float Goat",
                "suggested_slug": "bubbles",
                "evidence_event_indices": [0, 1, 2],
                "rationale": "named entity",
            },
            {
                "descriptor": "Bubbles the Float Goat",
                "suggested_slug": "bubbles_the_float_goat",
                "evidence_event_indices": [0, 1, 2],
                "rationale": "named entity",
            },
            {
                "descriptor": "Pippa",
                "suggested_slug": "pippa",
                "evidence_event_indices": [0, 4],
                "rationale": "named non-PC",
            },
        ],
        "unresolved_descriptors": [
            {
                "descriptor": "the captain",
                "evidence_event_indices": [5],
                "rationale": "honorific only",
            },
        ],
    }


def _gold() -> dict:
    return {
        "schema": "stage_d_v0.1",
        "scenario_id": "test",
        "input": {"pc_roster": _pc_roster()},
        "grading": {
            "must_not_merge": [],
            "must_merge_clusters": [],
            "must_resolve_unresolved": [],
        },
    }


def _good_output() -> dict:
    return {
        "resolved_entities": [
            {
                "source_kind": "new_candidate",
                "source_index": 0,
                "resolution": "merge_to_registry_slug",
                "canonical_slug": "bubbles_the_float_goat",
                "evidence_event_indices": [0, 1, 2],
                "rationale": "alias match",
            },
            {
                "source_kind": "new_candidate",
                "source_index": 1,
                "resolution": "merge_to_registry_slug",
                "canonical_slug": "bubbles_the_float_goat",
                "evidence_event_indices": [0, 1, 2],
                "rationale": "slug match",
            },
            {
                "source_kind": "new_candidate",
                "source_index": 2,
                "resolution": "new_net_entity",
                "canonical_slug": "pippa",
                "evidence_event_indices": [0, 4],
                "rationale": "not in registry",
            },
            {
                "source_kind": "unresolved_descriptor",
                "source_index": 0,
                "resolution": "merge_to_registry_slug",
                "canonical_slug": "captain_lysandra_ironveil",
                "evidence_event_indices": [5],
                "rationale": "alias 'the captain'",
            },
        ],
        "proposed_aliases": [],
        "proposed_new_records": [
            {
                "slug": "pippa",
                "display_name": "Pippa",
                "aliases": [],
                "status": "candidate",
                "first_session": 3,
                "last_session": 3,
                "hub_path": None,
                "setting_hub_path": None,
                "notes": "from stage d",
            }
        ],
        "unresolvable": [],
    }


# ---------------------------------------------------------------------------
# ER1 — schema validity
# ---------------------------------------------------------------------------


class TestER1Schema:
    def test_clean_pass(self) -> None:
        v, viol, _ = _grade_er1(_good_output(), _stage_c_output())
        assert v == "PASS", viol

    def test_missing_top_level_array_fails(self) -> None:
        out = _good_output()
        del out["proposed_aliases"]
        v, viol, _ = _grade_er1(out, _stage_c_output())
        assert v == "FAIL"
        assert any("proposed_aliases" in s for s in viol)

    def test_bad_slug_regex_fails(self) -> None:
        out = _good_output()
        out["resolved_entities"][0]["canonical_slug"] = "Bubbles!The"
        v, viol, _ = _grade_er1(out, _stage_c_output())
        assert v == "FAIL"
        assert any("^[a-z0-9_]+$" in s for s in viol)

    def test_orphan_source_index_fails(self) -> None:
        out = _good_output()
        out["resolved_entities"][0]["source_index"] = 99
        v, viol, _ = _grade_er1(out, _stage_c_output())
        assert v == "FAIL"
        assert any("orphan pointer" in s for s in viol)

    def test_invalid_resolution_verb_fails(self) -> None:
        out = _good_output()
        out["resolved_entities"][0]["resolution"] = "guess"
        v, viol, _ = _grade_er1(out, _stage_c_output())
        assert v == "FAIL"
        assert any("resolution" in s for s in viol)

    def test_invalid_proposed_divergence_mode_fails(self) -> None:
        out = _good_output()
        out["proposed_new_records"][0]["proposed_divergence_mode"] = "merge_all_the_things"
        v, viol, _ = _grade_er1(out, _stage_c_output())
        assert v == "FAIL"
        assert any("proposed_divergence_mode" in s for s in viol)


# ---------------------------------------------------------------------------
# ER2 — PC safety
# ---------------------------------------------------------------------------


class TestER2PCSafety:
    def test_clean_pass(self) -> None:
        v, viol, _ = _grade_er2(_good_output(), _pc_roster())
        assert v == "PASS", viol

    def test_pc_slug_in_resolved_entity_fails(self) -> None:
        out = _good_output()
        out["resolved_entities"][2]["canonical_slug"] = "stafl"
        v, viol, _ = _grade_er2(out, _pc_roster())
        assert v == "FAIL"
        assert any("stafl" in s for s in viol)

    def test_pc_slug_in_proposed_alias_target_fails(self) -> None:
        out = _good_output()
        out["proposed_aliases"].append({
            "target_slug": "bonogo",
            "alias_text": "the rogue",
            "source_descriptor_ids": [],
            "rationale": "x",
        })
        v, viol, _ = _grade_er2(out, _pc_roster())
        assert v == "FAIL"
        assert any("bonogo" in s for s in viol)


# ---------------------------------------------------------------------------
# ER3 — no false merges (precision)
# ---------------------------------------------------------------------------


class TestER3Precision:
    def test_clean_pass(self) -> None:
        v, viol, _ = _grade_er3(_good_output(), _stage_c_output(), _registry(), [])
        assert v == "PASS", viol

    def test_merge_to_registry_with_unknown_slug_fails(self) -> None:
        out = _good_output()
        out["resolved_entities"][0]["canonical_slug"] = "nonexistent_npc"
        v, viol, _ = _grade_er3(out, _stage_c_output(), _registry(), [])
        assert v == "FAIL"
        assert any("nonexistent_npc" in s for s in viol)

    def test_merge_to_canonical_new_candidate_with_unknown_slug_fails(self) -> None:
        out = _good_output()
        out["resolved_entities"].append({
            "source_kind": "new_candidate",
            "source_index": 2,
            "resolution": "merge_to_canonical_new_candidate",
            "canonical_slug": "not_a_real_candidate",
            "evidence_event_indices": [],
            "rationale": "x",
        })
        v, viol, _ = _grade_er3(out, _stage_c_output(), _registry(), [])
        assert v == "FAIL"
        assert any("not_a_real_candidate" in s for s in viol)

    def test_must_not_merge_forbidden_pair_fails(self) -> None:
        out = _good_output()
        out["resolved_entities"][2]["canonical_slug"] = "bubbles_the_float_goat"
        out["resolved_entities"][2]["resolution"] = "merge_to_registry_slug"
        v, viol, _ = _grade_er3(
            out, _stage_c_output(), _registry(), [["pippa", "bubbles_the_float_goat"]]
        )
        assert v == "FAIL"
        assert any("forbidden merge" in s for s in viol)


# ---------------------------------------------------------------------------
# ER4 — recall (within scope)
# ---------------------------------------------------------------------------


class TestER4Recall:
    def test_clusters_all_collapse_pass(self) -> None:
        v, viol, _ = _grade_er4(
            _good_output(),
            _stage_c_output(),
            [["bubbles", "bubbles_the_float_goat"]],
            [],
        )
        assert v == "PASS", viol

    def test_cluster_split_fails(self) -> None:
        out = _good_output()
        out["resolved_entities"][1]["canonical_slug"] = "different_canonical"
        out["resolved_entities"][1]["resolution"] = "new_net_entity"
        v, viol, _ = _grade_er4(
            out,
            _stage_c_output(),
            [["bubbles", "bubbles_the_float_goat"]],
            [],
        )
        assert v == "FAIL"
        assert any("split across" in s for s in viol)

    def test_must_resolve_unresolved_still_unresolvable_fails(self) -> None:
        out = _good_output()
        out["resolved_entities"] = [r for r in out["resolved_entities"] if r["source_kind"] != "unresolved_descriptor"]
        out["unresolvable"].append({
            "source_kind": "unresolved_descriptor",
            "source_index": 0,
            "descriptor": "the captain",
            "reason": "no name",
        })
        v, viol, _ = _grade_er4(out, _stage_c_output(), [], ["the captain"])
        assert v == "FAIL"
        assert any("the captain" in s for s in viol)


# ---------------------------------------------------------------------------
# ER5 — registry / status policy
# ---------------------------------------------------------------------------


class TestER5RegistryPolicy:
    def test_clean_pass(self) -> None:
        v, viol, _ = _grade_er5(_good_output(), _registry())
        assert v == "PASS", viol

    def test_status_not_candidate_fails(self) -> None:
        out = _good_output()
        out["proposed_new_records"][0]["status"] = "tracked"
        v, viol, _ = _grade_er5(out, _registry())
        assert v == "FAIL"
        assert any("status" in s for s in viol)

    def test_hub_path_not_null_fails(self) -> None:
        out = _good_output()
        out["proposed_new_records"][0]["hub_path"] = "Some/Path/"
        v, viol, _ = _grade_er5(out, _registry())
        assert v == "FAIL"
        assert any("hub_path" in s for s in viol)

    def test_slug_collides_with_registry_fails(self) -> None:
        out = _good_output()
        out["proposed_new_records"][0]["slug"] = "torbin_jove"
        v, viol, _ = _grade_er5(out, _registry())
        assert v == "FAIL"
        assert any("collides" in s for s in viol)

    def test_er5_ignores_branch_hint_extras(self) -> None:
        out = _good_output()
        out["proposed_new_records"][0]["proposed_campaign_hub_path"] = (
            "Longmont Campaign/Campaign 1/NPCs/pippa/"
        )
        out["proposed_new_records"][0]["proposed_divergence_mode"] = "inherit"
        v, viol, _ = _grade_er5(out, _registry())
        assert v == "PASS", viol


# ---------------------------------------------------------------------------
# Resolver helpers (deterministic v0)
# ---------------------------------------------------------------------------


class TestResolver:
    def test_pc_term_in_suggested_slug_routes_to_unresolvable(self) -> None:
        stage_c = {
            "tracked_npcs_active": [],
            "new_npc_candidates": [
                {
                    "descriptor": "Caelynn the Brave",
                    "suggested_slug": "caelynn_brave",
                    "evidence_event_indices": [1],
                    "rationale": "x",
                },
            ],
            "unresolved_descriptors": [],
        }
        out = resolve_stage_d(
            stage_c_output=stage_c,
            events=[],
            registry=_registry(),
            pc_roster=_pc_roster(),
            session_number=1,
            campaign_id="longmont-c1",
        )
        assert len(out.unresolvable) == 1
        assert out.unresolvable[0].source_kind == "new_candidate"
        assert "PC" in out.unresolvable[0].reason

    def test_slug_variant_cluster_collapses_no_registry_hit(self) -> None:
        # Neither slug exists in the registry; cluster code path picks the
        # longer slug as canonical and emits one proposed_new_record.
        stage_c = {
            "tracked_npcs_active": [],
            "new_npc_candidates": [
                {
                    "descriptor": "Glow Kindle",
                    "suggested_slug": "glowkindle",
                    "evidence_event_indices": [1],
                    "rationale": "x",
                },
                {
                    "descriptor": "Glow Kindle",
                    "suggested_slug": "glowkindel",
                    "evidence_event_indices": [2],
                    "rationale": "typo variant",
                },
            ],
            "unresolved_descriptors": [],
        }
        out = resolve_stage_d(
            stage_c_output=stage_c,
            events=[],
            registry=_registry(),
            pc_roster=_pc_roster(),
            session_number=1,
            campaign_id="longmont-c1",
        )
        assert len(out.resolved_entities) == 2
        canonicals = {r.canonical_slug for r in out.resolved_entities}
        assert len(canonicals) == 1
        assert len(out.proposed_new_records) == 1
        canonical_slug = out.proposed_new_records[0].slug
        assert canonical_slug in {"glowkindle", "glowkindel"}
        # Longest slug wins (both length 10, tie broken by max() stability —
        # accept either as long as both inputs collapsed).

    def test_slug_clustering_precision_floor(self) -> None:
        # Short shared prefix should NOT cluster (precision floor).
        assert _slugs_should_cluster("cat", "cat_owl") is False
        # Substring containment with len(shorter) >= 4 SHOULD cluster.
        assert _slugs_should_cluster("bubbles", "bubbles_the_float_goat") is True
        # Levenshtein <=2 with similar lengths SHOULD cluster.
        assert _slugs_should_cluster("glowkindle", "glowkindel") is True
        # Two completely different slugs should NOT cluster.
        assert _slugs_should_cluster("pippa", "grishna") is False


# ---------------------------------------------------------------------------
# Top-level orchestrator smoke
# ---------------------------------------------------------------------------


class TestTopLevelOrchestrator:
    def test_all_pass_shape(self) -> None:
        report = grade_stage_d(
            _good_output(),
            _gold(),
            _stage_c_output(),
            events=[],
            registry=_registry(),
        )
        assert report["all_gates_passed"] is True
        assert report["gates_passed"] == "5/5"
        assert report["per_gate_verdict"]["ER1"] == "PASS"
        assert report["per_gate_verdict"]["ER5"] == "PASS"
        assert isinstance(report["telemetry"], dict)
        assert report["telemetry"]["resolved_count"] == 4
        assert report["telemetry"]["proposed_new_records_count"] == 1
