"""Offline tests for the session-events-extraction grader.

All tests are purely offline — no network calls, no model invocations.
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import pytest

from evals.session_events_extraction_vertical_slice.grader import (
    collect_se1_violations,
    collect_se2_violations,
    collect_se3_violations,
    collect_se4_violations,
    collect_se5_violations,
    collect_se6_violations,
    collect_se7_violations,
    collect_session_events_violations,
    per_gate_verdict,
)
from src.contracts.schema_validation import validate_instance
from jsonschema.exceptions import ValidationError


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_EVIDENCE_ID = "Longmont Campaign/Campaign 2/Session Recaps/Session 20 - Recap.md"


def _valid_event(**overrides) -> dict:
    base = {
        "event_class": "combat",
        "time_scope": "scene",
        "certainty": "observed",
        "participants": ["caelynn", "ephanna"],
        "outcomes": ["swarm defeated"],
        "event_name": "Red gnat swarm battle",
        "evidence_id": _EVIDENCE_ID,
    }
    base.update(overrides)
    return base


def _minimal_valid_event() -> dict:
    """Minimal event with only required fields per schema."""
    return {
        "event_class": "conversation",
        "time_scope": "scene",
        "certainty": "observed",
    }


def _gold_grading() -> dict:
    return {
        "min_event_count": 10,
        "max_event_count": 25,
        "must_cover_participants": [
            "captain_lysandra_ironveil",
            "caelynn",
            "karsemine",
            "ephanna",
            "sara_mirathorn_operator",
            "bonogo",
        ],
        "must_cover_event_classes": ["combat", "conversation", "discovery", "social_conflict"],
        "expected_events": [
            _valid_event(
                event_class="combat",
                participants=["caelynn", "ephanna", "karsemine"],
                event_name="Red gnat swarm battle",
                outcomes=["swarm retreats"],
            ),
            _valid_event(
                event_class="social_conflict",
                participants=["bonogo", "stacey"],
                event_name="Bonogo threatens Stacey with knife",
                outcomes=["Stacey runs home shaken"],
            ),
            _valid_event(
                event_class="conversation",
                participants=["caelynn", "sara_mirathorn_operator"],
                event_name="Caelynn calls Sara via rockie-talkie",
                outcomes=["Sara connects Caelynn to Lysandra"],
            ),
            _valid_event(
                event_class="discovery",
                participants=["caelynn", "captain_lysandra_ironveil"],
                event_name="Lysandra found with tower blueprint",
                outcomes=["tower blueprint found", "shimmery eyes"],
            ),
        ],
    }


# ---------------------------------------------------------------------------
# SE1 — schema validity
# ---------------------------------------------------------------------------


class TestSE1:
    def test_valid_event_passes(self):
        events = [_valid_event()]
        violations = collect_se1_violations(events)
        assert violations == []

    def test_minimal_valid_event_passes(self):
        violations = collect_se1_violations([_minimal_valid_event()])
        assert violations == []

    def test_bad_event_class_fails(self):
        event = _valid_event(event_class="explosion")  # not in enum
        violations = collect_se1_violations([event])
        assert len(violations) == 1
        assert "SE1" in violations[0]

    def test_missing_required_field_fails(self):
        event = {"event_class": "combat", "time_scope": "scene"}  # missing certainty
        violations = collect_se1_violations([event])
        assert len(violations) == 1
        assert "SE1" in violations[0]

    def test_bad_time_scope_fails(self):
        event = _valid_event(time_scope="yearly")  # not in enum
        violations = collect_se1_violations([event])
        assert violations  # at least one SE1 violation

    def test_additional_property_fails(self):
        event = _valid_event()
        event["unexpected_field"] = "should fail"
        violations = collect_se1_violations([event])
        assert violations

    def test_multiple_events_one_bad(self):
        events = [_valid_event(), _valid_event(event_class="not_real")]
        violations = collect_se1_violations(events)
        assert len(violations) == 1
        assert "event[1]" in violations[0]


# ---------------------------------------------------------------------------
# SE2 — count window
# ---------------------------------------------------------------------------


class TestSE2:
    def test_within_window_passes(self):
        events = [_valid_event() for _ in range(12)]
        violations = collect_se2_violations(events, min_count=10, max_count=25)
        assert violations == []

    def test_at_min_passes(self):
        events = [_valid_event() for _ in range(10)]
        assert collect_se2_violations(events, min_count=10, max_count=25) == []

    def test_at_max_passes(self):
        events = [_valid_event() for _ in range(25)]
        assert collect_se2_violations(events, min_count=10, max_count=25) == []

    def test_below_min_fails(self):
        events = [_valid_event() for _ in range(5)]
        violations = collect_se2_violations(events, min_count=10, max_count=25)
        assert len(violations) == 1
        assert "SE2" in violations[0]
        assert "min_event_count" in violations[0]

    def test_above_max_fails(self):
        events = [_valid_event() for _ in range(30)]
        violations = collect_se2_violations(events, min_count=10, max_count=25)
        assert len(violations) == 1
        assert "SE2" in violations[0]
        assert "max_event_count" in violations[0]


# ---------------------------------------------------------------------------
# SE3 — participant coverage
# ---------------------------------------------------------------------------


class TestSE3:
    def test_all_required_present_passes(self):
        events = [
            _valid_event(participants=["caelynn", "captain_lysandra_ironveil"]),
            _valid_event(participants=["karsemine", "ephanna"]),
        ]
        violations = collect_se3_violations(events, ["caelynn", "captain_lysandra_ironveil", "karsemine", "ephanna"])
        assert violations == []

    def test_missing_slug_fails(self):
        events = [_valid_event(participants=["caelynn"])]
        violations = collect_se3_violations(events, ["caelynn", "bonogo"])
        assert len(violations) == 1
        assert "bonogo" in violations[0]

    def test_empty_must_cover_passes(self):
        events = [_valid_event()]
        assert collect_se3_violations(events, []) == []

    def test_all_slugs_in_single_event_passes(self):
        events = [_valid_event(participants=["a", "b", "c"])]
        assert collect_se3_violations(events, ["a", "b", "c"]) == []


# ---------------------------------------------------------------------------
# SE4 — event-class coverage
# ---------------------------------------------------------------------------


class TestSE4:
    def test_all_required_classes_present_passes(self):
        events = [
            _valid_event(event_class="combat"),
            _valid_event(event_class="conversation"),
            _valid_event(event_class="discovery"),
            _valid_event(event_class="social_conflict"),
        ]
        violations = collect_se4_violations(events, ["combat", "conversation", "discovery", "social_conflict"])
        assert violations == []

    def test_missing_class_fails(self):
        events = [_valid_event(event_class="combat")]
        violations = collect_se4_violations(events, ["combat", "ritual"])
        assert len(violations) == 1
        assert "ritual" in violations[0]

    def test_empty_must_cover_passes(self):
        assert collect_se4_violations([_valid_event()], []) == []


# ---------------------------------------------------------------------------
# SE5 — anchor coverage
# ---------------------------------------------------------------------------


class TestSE5:
    def _expected(self, event_class: str, participants: list, name: str, outcomes: list) -> dict:
        return _valid_event(
            event_class=event_class,
            participants=participants,
            event_name=name,
            outcomes=outcomes,
        )

    def test_full_match_passes(self):
        """All expected events are matched."""
        expected = [
            self._expected("combat", ["caelynn", "ephanna"], "swarm battle", ["swarm defeated"]),
            self._expected("conversation", ["caelynn", "sara_mirathorn_operator"], "rockie talkie call", ["Sara connects"]),
        ]
        # Actual mirrors expected closely
        actual = [
            _valid_event(event_class="combat", participants=["caelynn"], event_name="swarm battle at forest edge", outcomes=["swarm defeated ephanna"]),
            _valid_event(event_class="conversation", participants=["caelynn", "sara_mirathorn_operator"], event_name="rockie talkie contact", outcomes=["Sara connects Lysandra"]),
        ]
        violations, ratio, unmatched, term_violations = collect_se5_violations(actual, expected)
        assert violations == [], f"Expected no violations but got: {violations}"
        assert ratio == 1.0
        assert unmatched == []
        assert term_violations == []

    def test_zero_overlap_fails(self):
        """No expected events are matched."""
        expected = [
            self._expected("combat", ["caelynn"], "swarm battle", ["swarm defeated"]),
            self._expected("discovery", ["captain_lysandra_ironveil"], "tower blueprint found", ["blueprint drawn in dirt"]),
        ]
        # Actual has wrong classes and participants
        actual = [
            _valid_event(event_class="ritual", participants=["stafl"], event_name="something else entirely", outcomes=["different thing"]),
        ]
        violations, ratio, unmatched, term_violations = collect_se5_violations(actual, expected)
        assert ratio == 0.0
        assert len(unmatched) == 2
        # Since ratio < 0.5, should have a violation
        assert violations
        assert term_violations == []

    def test_partial_overlap_reports_correct_ratio(self):
        """2 of 4 expected events matched → ratio 0.5 (at threshold, should PASS)."""
        expected = [
            self._expected("combat", ["caelynn"], "swarm battle", ["swarm retreats"]),
            self._expected("conversation", ["caelynn", "sara_mirathorn_operator"], "rockie talkie", ["Sara connects"]),
            self._expected("discovery", ["captain_lysandra_ironveil"], "tower blueprint", ["blueprint drawn"]),
            self._expected("social_conflict", ["bonogo", "stacey"], "knife threat", ["Stacey runs home"]),
        ]
        actual = [
            # Matches expected[0]
            _valid_event(event_class="combat", participants=["caelynn", "ephanna"], event_name="swarm battle", outcomes=["swarm retreats to forest"]),
            # Matches expected[1]
            _valid_event(event_class="conversation", participants=["caelynn", "sara_mirathorn_operator"], event_name="rockie talkie call Sara", outcomes=["Sara connects Lysandra"]),
            # Does NOT match expected[2] or [3] — different class/participants
            _valid_event(event_class="travel", participants=["karsemine"], event_name="unrelated travel", outcomes=["arrived"]),
        ]
        violations, ratio, unmatched, term_violations = collect_se5_violations(actual, expected)
        assert ratio == pytest.approx(0.5)
        # At exactly 0.5 threshold → PASS (ratio NOT < threshold)
        assert violations == []
        assert term_violations == []

    def test_below_threshold_fails(self):
        """1 of 4 matched → ratio 0.25 → FAIL."""
        expected = [
            self._expected("combat", ["caelynn"], "swarm battle", ["swarm retreats"]),
            self._expected("conversation", ["caelynn", "sara_mirathorn_operator"], "rockie talkie", ["Sara connects"]),
            self._expected("discovery", ["captain_lysandra_ironveil"], "tower blueprint", ["blueprint drawn"]),
            self._expected("social_conflict", ["bonogo", "stacey"], "knife threat", ["Stacey runs home"]),
        ]
        actual = [
            _valid_event(event_class="combat", participants=["caelynn"], event_name="swarm battle", outcomes=["swarm retreats"]),
        ]
        violations, ratio, unmatched, term_violations = collect_se5_violations(actual, expected)
        assert ratio == pytest.approx(0.25)
        assert violations  # below threshold
        assert term_violations == []

    def test_empty_expected_events_passes(self):
        violations, ratio, unmatched, term_violations = collect_se5_violations([_valid_event()], [])
        assert violations == []
        assert ratio == 1.0
        assert unmatched == []
        assert term_violations == []

    # -- must_preserve_terms cases (outcome-vocabulary sub-gate) --

    def _expected_with_terms(
        self,
        event_class: str,
        participants: list,
        name: str,
        outcomes: list,
        must_preserve_terms: list,
    ) -> dict:
        ev = self._expected(event_class, participants, name, outcomes)
        ev["must_preserve_terms"] = must_preserve_terms
        return ev

    def test_must_preserve_terms_all_present_passes(self):
        """Matched actual contains all required terms verbatim → no term violations."""
        expected = [
            self._expected_with_terms(
                "combat",
                ["caelynn", "ephanna", "karsemine"],
                "swarm battle",
                ["Karsemine uses scimitar", "Caelynn casts Thunderwave"],
                ["scimitar", "Thunderwave", "Eldritch Blast"],
            ),
        ]
        actual = [
            _valid_event(
                event_class="combat",
                participants=["caelynn", "ephanna", "karsemine"],
                event_name="Red gnat swarm battle at forest edge",
                outcomes=[
                    "Karsemine lands 4 scimitar hits using Zephyr Strike",
                    "Ephanna's second Eldritch Blast removes a cluster",
                    "Caelynn casts Thunderwave splitting the swarm",
                ],
            ),
        ]
        violations, ratio, unmatched, term_violations = collect_se5_violations(actual, expected)
        assert violations == []
        assert term_violations == []
        assert ratio == 1.0

    def test_must_preserve_terms_missing_term_fails_with_payload(self):
        """Matched actual drops one required term → SE5 emits missing_outcome_terms violation."""
        expected = [
            self._expected_with_terms(
                "combat",
                ["caelynn", "ephanna", "karsemine"],
                "swarm battle",
                ["Karsemine uses scimitar", "Caelynn casts Thunderwave"],
                ["scimitar", "Thunderwave", "Eldritch Blast"],
            ),
        ]
        actual = [
            _valid_event(
                event_class="combat",
                participants=["caelynn", "ephanna", "karsemine"],
                event_name="Red gnat swarm battle",
                # "Eldritch Blast" missing — paraphrased away
                outcomes=[
                    "Karsemine lands 4 scimitar hits",
                    "Ephanna casts an attack spell",
                    "Caelynn casts Thunderwave splitting the swarm",
                ],
            ),
        ]
        violations, ratio, unmatched, term_violations = collect_se5_violations(actual, expected)
        # Lenient ratio still 1.0 — match is intact, just missing terms.
        assert ratio == 1.0
        assert unmatched == []
        # Exactly one structured term violation.
        assert len(term_violations) == 1
        tv = term_violations[0]
        assert tv["kind"] == "missing_outcome_terms"
        assert tv["expected_event_index"] == 0
        assert tv["missing_terms"] == ["Eldritch Blast"]
        assert tv["actual_event_name"] == "Red gnat swarm battle"
        assert "Karsemine lands 4 scimitar hits" in tv["actual_event_outcomes"]
        # SE5 string violation surfaces too so the gate FAILs.
        assert any("missing_outcome_terms" in v for v in violations)

    def test_must_preserve_terms_case_insensitive(self):
        """Term presence check is case-insensitive substring match."""
        expected = [
            self._expected_with_terms(
                "social_conflict",
                ["bonogo", "stacey"],
                "knife threat",
                ["Bonogo holds knife to throat"],
                ["KNIFE", "Stacey"],
            ),
        ]
        actual = [
            _valid_event(
                event_class="social_conflict",
                participants=["bonogo", "stacey"],
                event_name="Bonogo intimidates Stacey with knife threat",
                outcomes=["Bonogo holds a knife to her throat", "stacey runs home shaken"],
            ),
        ]
        violations, ratio, unmatched, term_violations = collect_se5_violations(actual, expected)
        assert term_violations == []
        assert violations == []

    def test_must_preserve_terms_or_group_satisfied_by_either_alternative(self) -> None:
        """``a|b`` in must_preserve_terms: either substring satisfies the slot."""
        expected = [
            self._expected_with_terms(
                "discovery",
                ["caelynn", "captain_lysandra_ironveil"],
                "wagon camp lysandra",
                ["eyes shimmery"],
                ["shimmery", "tower", "drawing|blueprint"],
            ),
        ]
        actual = [
            _valid_event(
                event_class="discovery",
                participants=["caelynn", "captain_lysandra_ironveil"],
                event_name="The party finds Lysandra's wagon camp",
                outcomes=[
                    "Her eyes are shimmery like cult members.",
                    "She describes a tower where voices come from.",
                    "Caelynn studies the blueprint in the dirt.",
                ],
            ),
        ]
        violations, _ratio, _unmatched, term_violations = collect_se5_violations(
            actual, expected
        )
        assert term_violations == []
        assert violations == []

    def test_must_preserve_terms_or_group_fails_when_neither_alternative_present(self) -> None:
        expected = [
            self._expected_with_terms(
                "discovery",
                ["caelynn", "captain_lysandra_ironveil"],
                "wagon camp lysandra",
                ["eyes"],
                ["drawing|blueprint"],
            ),
        ]
        actual = [
            _valid_event(
                event_class="discovery",
                participants=["caelynn", "captain_lysandra_ironveil"],
                event_name="camp scene",
                outcomes=["nothing specific"],
            ),
        ]
        violations, _ratio, _unmatched, term_violations = collect_se5_violations(
            actual, expected
        )
        assert len(term_violations) == 1
        assert "drawing|blueprint" in term_violations[0]["missing_terms"]
        assert any("missing_outcome_terms" in v for v in violations)

    def test_must_preserve_terms_per_term_check_across_pool(self):
        """Term sub-check is per-term across the participant-overlap pool: each term
        only needs to appear in SOME participant-overlapping actual, not all in one."""
        expected = [
            self._expected_with_terms(
                "combat",
                ["caelynn"],
                "swarm battle",
                ["swarm defeated"],
                ["Thunderwave", "scimitar"],
            ),
        ]
        # No single actual has both terms, but together the pool covers them.
        actual = [
            _valid_event(
                event_class="combat",
                participants=["caelynn"],
                event_name="swarm fight",
                outcomes=["caelynn casts Thunderwave"],
            ),
            _valid_event(
                event_class="combat",
                participants=["caelynn", "karsemine"],
                event_name="swarm flank",
                outcomes=["Karsemine scimitar hits"],
            ),
        ]
        violations, ratio, unmatched, term_violations = collect_se5_violations(actual, expected)
        # Both terms preserved across the pool — no term violations.
        assert term_violations == []
        assert violations == []

    def test_must_preserve_terms_per_term_missing_when_paraphrased_away(self):
        """If a term appears NOWHERE in any participant-overlapping actual, that term
        is reported missing. This is the paraphrasing-detection signal."""
        expected = [
            self._expected_with_terms(
                "combat",
                ["caelynn", "ephanna"],
                "swarm battle",
                ["swarm defeated"],
                ["Eldritch Blast", "Thunderwave"],
            ),
        ]
        # Pool covers Thunderwave but no event mentions Eldritch Blast (paraphrased to "attack spell").
        actual = [
            _valid_event(
                event_class="combat",
                participants=["caelynn"],
                event_name="swarm fight",
                outcomes=["caelynn casts Thunderwave"],
            ),
            _valid_event(
                event_class="combat",
                participants=["caelynn", "ephanna"],
                event_name="ephanna ranged",
                outcomes=["Ephanna casts an attack spell at the swarm"],
            ),
        ]
        violations, ratio, unmatched, term_violations = collect_se5_violations(actual, expected)
        assert len(term_violations) == 1
        tv = term_violations[0]
        assert tv["missing_terms"] == ["Eldritch Blast"]
        # Best representative actual should be the one preserving the most terms (Thunderwave).
        assert tv["actual_event_name"] in {"swarm fight", "ephanna ranged"}

    def test_must_preserve_terms_empty_list_no_constraint(self):
        """Backward compat: empty must_preserve_terms list does not introduce false failures."""
        expected = [
            self._expected_with_terms(
                "conversation",
                ["caelynn", "stafl"],
                "party reports findings",
                ["forest responds to ground changes"],
                [],
            ),
        ]
        actual = [
            _valid_event(
                event_class="conversation",
                participants=["caelynn", "stafl"],
                event_name="party briefs Stafl",
                outcomes=["forest responds to ground changes"],
            ),
        ]
        violations, ratio, unmatched, term_violations = collect_se5_violations(actual, expected)
        assert term_violations == []
        assert violations == []

    def test_must_preserve_terms_field_absent_no_constraint(self):
        """Backward compat: missing must_preserve_terms field is treated as no constraint."""
        expected = [
            self._expected("conversation", ["caelynn"], "mayor denies Lysandra", ["mayor denies"]),
        ]
        # Note: no must_preserve_terms key at all
        assert "must_preserve_terms" not in expected[0]
        actual = [
            _valid_event(
                event_class="conversation",
                participants=["caelynn"],
                event_name="mayor talks to Caelynn",
                outcomes=["mayor never heard of anyone"],
            ),
        ]
        violations, ratio, unmatched, term_violations = collect_se5_violations(actual, expected)
        assert term_violations == []
        assert violations == []

    def test_must_preserve_terms_passes_when_class_drifts_but_vocabulary_kept(self):
        """Term sub-check is decoupled from strict event_class matching.

        If the model classified the same beat under a different but related class
        (e.g. ``ritual`` instead of ``social_conflict`` for Caelynn's bracelet
        de-escalation) yet preserved the distinctive vocabulary verbatim, SE5
        should NOT fire a missing_outcome_terms violation. The lenient coverage
        ratio may still penalize the class drift via 'unmatched', but the term
        sub-gate is about vocabulary, not classification."""
        expected = [
            self._expected_with_terms(
                "social_conflict",
                ["caelynn", "marla_brambleback", "bonogo"],
                "Caelynn de-escalates Marla vs Bonogo with bracelet",
                ["Caelynn uses bracelet to diffuse aggression"],
                ["bracelet"],
            ),
        ]
        # Model classified the same beat under "ritual", same participants,
        # vocabulary preserved verbatim.
        actual = [
            _valid_event(
                event_class="ritual",
                participants=["caelynn", "marla_brambleback", "bonogo"],
                event_name="Caelynn calms the worksite with her bracelet",
                outcomes=["Caelynn uses her bracelet to soothe the dispute"],
            ),
        ]
        violations, ratio, unmatched, term_violations = collect_se5_violations(actual, expected)
        # No term violations: vocabulary IS preserved in a participant-overlapping event.
        assert term_violations == []
        # The lenient gate still flags it as unmatched (event_class differs), but term-violations
        # are independently zero. Below-threshold lenient FAIL is the only string violation.
        assert ratio == 0.0
        assert unmatched == [0]
        # Single SE5 violation comes from lenient coverage, not from term drift.
        assert len(violations) == 1
        assert "missing_outcome_terms" not in violations[0]

    def test_must_preserve_terms_unmatched_event_no_term_violation(self):
        """If an expected event has no candidate match, SE5 does not emit a term violation
        (lenient gate already captures it as unmatched)."""
        expected = [
            self._expected_with_terms(
                "ritual",
                ["caelynn"],
                "antidote tea",
                ["caelynn brews tea"],
                ["antidote", "tea"],
            ),
        ]
        # No matching ritual events.
        actual = [
            _valid_event(event_class="combat", participants=["karsemine"], event_name="something else", outcomes=["different"]),
        ]
        violations, ratio, unmatched, term_violations = collect_se5_violations(actual, expected)
        assert ratio == 0.0
        assert unmatched == [0]
        # No structured term violation — the expected event was unmatched.
        assert term_violations == []
        # SE5 gate FAILs anyway because ratio < threshold.
        assert violations


# ---------------------------------------------------------------------------
# SE6 — optional capture-layer anchor coverage
# ---------------------------------------------------------------------------


class TestSE6:
    def test_expected_anchored_spans_pass_when_covered(self) -> None:
        events = [
            _valid_event(
                participants=["caelynn"],
                source_anchors=[
                    {
                        "source_type": "recap_extracted",
                        "path": _EVIDENCE_ID,
                        "line_start": 18,
                        "line_end": 24,
                        "content_hash": "0" * 64,
                        "commit_sha": "abc123",
                        "agent": None,
                        "thread_id": None,
                    }
                ],
            )
        ]
        expected = [
            {"npc_slug": "caelynn", "path": _EVIDENCE_ID, "line_range": [20, 24], "rationale": "test span"}
        ]
        violations, ratio, unmatched = collect_se6_violations(events, expected)
        assert violations == []
        assert ratio == 1.0
        assert unmatched == []

    def test_expected_anchored_spans_fail_when_missing(self) -> None:
        events = [_valid_event(participants=["caelynn"], source_anchors=[])]
        expected = [
            {"npc_slug": "caelynn", "path": _EVIDENCE_ID, "line_range": [20, 24], "rationale": "test span"}
        ]
        violations, ratio, unmatched = collect_se6_violations(events, expected)
        assert violations
        assert ratio == 0.0
        assert unmatched == [0]

    def test_expected_anchored_spans_fail_for_coarse_anchor(self) -> None:
        events = [
            _valid_event(
                participants=["caelynn"],
                source_anchors=[
                    {
                        "source_type": "recap_extracted",
                        "path": _EVIDENCE_ID,
                        "line_start": 1,
                        "line_end": 300,
                        "content_hash": "0" * 64,
                        "commit_sha": "abc123",
                        "agent": None,
                        "thread_id": None,
                    }
                ],
            )
        ]
        expected = [
            {"npc_slug": "caelynn", "path": _EVIDENCE_ID, "line_range": [20, 24], "rationale": "test span"}
        ]
        violations, ratio, unmatched = collect_se6_violations(events, expected)
        assert violations
        assert ratio == 0.0
        assert unmatched == [0]

    def test_collect_session_events_runs_se6_when_configured(self) -> None:
        events = [
            _valid_event(
                participants=["caelynn", "ephanna"],
                source_anchors=[
                    {
                        "source_type": "recap_extracted",
                        "path": _EVIDENCE_ID,
                        "line_start": 8,
                        "line_end": 14,
                        "content_hash": "0" * 64,
                        "commit_sha": "abc123",
                        "agent": None,
                        "thread_id": None,
                    }
                ],
            )
        ]
        grading = {
            "min_event_count": 1,
            "max_event_count": 25,
            "must_cover_participants": ["caelynn", "ephanna"],
            "must_cover_event_classes": ["combat"],
            "expected_events": [],
            "expected_anchored_spans": [
                {"npc_slug": "caelynn", "path": _EVIDENCE_ID, "line_range": [10, 12], "rationale": "anchor"}
            ],
        }
        violations, telemetry = collect_session_events_violations(events, grading)
        assert "se6" not in violations
        assert telemetry["expected_anchor_span_coverage_ratio"] == 1.0
        assert telemetry["unmatched_expected_anchor_span_indices"] == []


# ---------------------------------------------------------------------------
# SE7 — every event anchor verifies against on-disk recap bytes
# ---------------------------------------------------------------------------


class TestSE7:
    @staticmethod
    def _write_mini_recap(tmp_path: Path) -> tuple[Path, str]:
        rel = "recap_folder/r.md"
        (tmp_path / "recap_folder").mkdir(parents=True)
        (tmp_path / rel).write_text("first line\nsecond line\nthird\n", encoding="utf-8")
        return tmp_path, rel

    def test_se7_passes_tight_verified_anchor(self, tmp_path: Path) -> None:
        from src.ingestion.source_anchor import build_recap_extracted_anchor, resolve_git_commit_sha

        corpus_root, rel = self._write_mini_recap(tmp_path)
        lines = (corpus_root / rel).read_text(encoding="utf-8").splitlines()
        _, anchor = build_recap_extracted_anchor(
            corpus_source_path=rel,
            full_file_lines=lines,
            line_start_1=2,
            line_end_1=2,
            commit_sha=resolve_git_commit_sha(cwd=_REPO_ROOT),
        )
        events = [_valid_event(participants=["caelynn"], source_anchors=[anchor.to_json_dict()])]
        violations, tel = collect_se7_violations(
            events, corpus_root=corpus_root, recap_relative_path=rel
        )
        assert violations == []
        assert tel["se7_anchors_checked"] == 1
        assert tel["se7_whole_file_placeholder_count"] == 0

    def test_se7_rejects_whole_file_placeholder(self, tmp_path: Path) -> None:
        from src.ingestion.source_anchor import build_recap_extracted_anchor, resolve_git_commit_sha

        corpus_root, rel = self._write_mini_recap(tmp_path)
        lines = (corpus_root / rel).read_text(encoding="utf-8").splitlines()
        _, anchor = build_recap_extracted_anchor(
            corpus_source_path=rel,
            full_file_lines=lines,
            line_start_1=1,
            line_end_1=len(lines),
            commit_sha=resolve_git_commit_sha(cwd=_REPO_ROOT),
        )
        events = [_valid_event(participants=["caelynn"], source_anchors=[anchor.to_json_dict()])]
        violations, tel = collect_se7_violations(
            events, corpus_root=corpus_root, recap_relative_path=rel
        )
        assert violations
        assert tel["se7_whole_file_placeholder_count"] == 1

    def test_se7_rejects_wrong_path(self, tmp_path: Path) -> None:
        from src.ingestion.source_anchor import build_recap_extracted_anchor, resolve_git_commit_sha

        corpus_root, rel = self._write_mini_recap(tmp_path)
        lines = (corpus_root / rel).read_text(encoding="utf-8").splitlines()
        _, anchor = build_recap_extracted_anchor(
            corpus_source_path=rel,
            full_file_lines=lines,
            line_start_1=2,
            line_end_1=2,
            commit_sha=resolve_git_commit_sha(cwd=_REPO_ROOT),
        )
        bad = anchor.to_json_dict()
        bad["path"] = "recap_folder/other.md"
        events = [_valid_event(participants=["caelynn"], source_anchors=[bad])]
        violations, _ = collect_se7_violations(
            events, corpus_root=corpus_root, recap_relative_path=rel
        )
        assert any("path" in v for v in violations)

    def test_collect_session_events_skips_se7_without_flag(self, tmp_path: Path) -> None:
        from src.ingestion.source_anchor import build_recap_extracted_anchor, resolve_git_commit_sha

        corpus_root, rel = self._write_mini_recap(tmp_path)
        lines = (corpus_root / rel).read_text(encoding="utf-8").splitlines()
        _, anchor = build_recap_extracted_anchor(
            corpus_source_path=rel,
            full_file_lines=lines,
            line_start_1=2,
            line_end_1=2,
            commit_sha=resolve_git_commit_sha(cwd=_REPO_ROOT),
        )
        bad = dict(anchor.to_json_dict())
        bad["content_hash"] = "0" * 64
        events = [_valid_event(participants=["caelynn", "ephanna"], source_anchors=[bad])]
        grading = {
            "min_event_count": 1,
            "max_event_count": 25,
            "must_cover_participants": ["caelynn", "ephanna"],
            "must_cover_event_classes": ["combat"],
            "expected_events": [],
        }
        violations, _ = collect_session_events_violations(
            events,
            grading,
            corpus_root=corpus_root,
            recap_relative_path=rel,
        )
        assert "se7" not in violations

    def test_collect_session_events_runs_se7_when_configured(self, tmp_path: Path) -> None:
        from src.ingestion.source_anchor import build_recap_extracted_anchor, resolve_git_commit_sha

        corpus_root, rel = self._write_mini_recap(tmp_path)
        lines = (corpus_root / rel).read_text(encoding="utf-8").splitlines()
        _, anchor = build_recap_extracted_anchor(
            corpus_source_path=rel,
            full_file_lines=lines,
            line_start_1=2,
            line_end_1=2,
            commit_sha=resolve_git_commit_sha(cwd=_REPO_ROOT),
        )
        events = [_valid_event(participants=["caelynn", "ephanna"], source_anchors=[anchor.to_json_dict()])]
        grading = {
            "min_event_count": 1,
            "max_event_count": 25,
            "must_cover_participants": ["caelynn", "ephanna"],
            "must_cover_event_classes": ["combat"],
            "expected_events": [],
            "require_verified_event_anchors": True,
        }
        violations, telemetry = collect_session_events_violations(
            events,
            grading,
            corpus_root=corpus_root,
            recap_relative_path=rel,
        )
        assert "se7" not in violations
        assert telemetry["se7_anchors_checked"] == 1

    def test_collect_session_events_se7_fails_on_hash_mismatch_when_configured(
        self, tmp_path: Path
    ) -> None:
        from src.ingestion.source_anchor import build_recap_extracted_anchor, resolve_git_commit_sha

        corpus_root, rel = self._write_mini_recap(tmp_path)
        lines = (corpus_root / rel).read_text(encoding="utf-8").splitlines()
        _, anchor = build_recap_extracted_anchor(
            corpus_source_path=rel,
            full_file_lines=lines,
            line_start_1=2,
            line_end_1=2,
            commit_sha=resolve_git_commit_sha(cwd=_REPO_ROOT),
        )
        bad = dict(anchor.to_json_dict())
        bad["content_hash"] = "0" * 64
        events = [_valid_event(participants=["caelynn", "ephanna"], source_anchors=[bad])]
        grading = {
            "min_event_count": 1,
            "max_event_count": 25,
            "must_cover_participants": ["caelynn", "ephanna"],
            "must_cover_event_classes": ["combat"],
            "expected_events": [],
            "require_verified_event_anchors": True,
        }
        violations, _ = collect_session_events_violations(
            events,
            grading,
            corpus_root=corpus_root,
            recap_relative_path=rel,
        )
        assert violations.get("se7")


# ---------------------------------------------------------------------------
# SE5 — sibling-event fallback for must_preserve_terms (corpus-level)
# ---------------------------------------------------------------------------


class TestSE5SiblingFallback:
    """SE5 must_preserve_terms sibling-event fallback (added 2026-04-22).

    When a required term is missing from the matched actual event for an
    expected event but present in some other actual event in the run, SE5
    soft-passes the term and records it under telemetry
    ``terms_preserved_via_sibling`` instead of emitting a
    ``missing_outcome_terms`` violation. Hard-fail behavior is preserved when
    the term appears in zero actual events.
    """

    def _expected_with_terms(
        self,
        event_class: str,
        participants: list,
        name: str,
        outcomes: list,
        must_preserve_terms: list,
    ) -> dict:
        ev = _valid_event(
            event_class=event_class,
            participants=participants,
            event_name=name,
            outcomes=outcomes,
        )
        ev["must_preserve_terms"] = must_preserve_terms
        return ev

    def test_pass_via_participant_overlapping_sibling_event(self):
        """(a) Term missing from matched actual but present in a participant-overlapping sibling actual
        → SE5 PASS, no violation, telemetry entry recorded."""
        expected = [
            self._expected_with_terms(
                "combat",
                ["caelynn", "ephanna"],
                "swarm battle",
                ["swarm defeated"],
                ["Thunderwave", "Eldritch Blast"],
            ),
        ]
        # Best matched actual (combat, both participants) preserves Thunderwave but
        # lacks "Eldritch Blast"; a participant-overlapping sibling carries it.
        actual = [
            _valid_event(
                event_class="combat",
                participants=["caelynn", "ephanna"],
                event_name="swarm fight at edge",
                outcomes=["Caelynn casts Thunderwave at the swarm"],
            ),
            _valid_event(
                event_class="travel",
                participants=["ephanna", "karsemine"],
                event_name="post-combat retrospective",
                outcomes=["Ephanna recounts firing two Eldritch Blast volleys"],
            ),
        ]
        violations, telemetry = collect_session_events_violations(
            actual,
            {
                "min_event_count": 1,
                "max_event_count": 25,
                "must_cover_participants": ["caelynn", "ephanna", "karsemine"],
                "must_cover_event_classes": ["combat", "travel"],
                "expected_events": expected,
            },
        )
        verdict = per_gate_verdict(violations)
        assert verdict["SE5"] == "PASS", f"Expected SE5 PASS, got {verdict}; violations={violations}"
        # Zero structured term violations.
        assert telemetry["se5_term_violations"] == []
        assert telemetry["expected_events_with_missing_terms"] == []
        assert telemetry["missing_terms_total"] == 0
        # Sibling-fallback telemetry has exactly one entry pointing at the right slots.
        sibling = telemetry["terms_preserved_via_sibling"]
        assert len(sibling) == 1
        entry = sibling[0]
        assert entry["expected_event_index"] == 0
        assert entry["term"] == "Eldritch Blast"
        assert entry["actual_event_index"] == 1

    def test_fail_when_term_only_in_non_overlapping_sibling_event(self):
        """A term dumped into an unrelated event must not satisfy SE5."""
        expected = [
            self._expected_with_terms(
                "combat",
                ["caelynn", "ephanna"],
                "swarm battle",
                ["swarm defeated"],
                ["Eldritch Blast"],
            ),
        ]
        actual = [
            _valid_event(
                event_class="combat",
                participants=["caelynn", "ephanna"],
                event_name="swarm fight at edge",
                outcomes=["Ephanna casts an attack spell at the swarm"],
            ),
            _valid_event(
                event_class="travel",
                participants=["karsemine"],
                event_name="post-combat retrospective",
                outcomes=["Karsemine recalls Ephanna's Eldritch Blast volleys"],
            ),
        ]
        violations, telemetry = collect_session_events_violations(
            actual,
            {
                "min_event_count": 1,
                "max_event_count": 25,
                "must_cover_participants": ["caelynn", "ephanna", "karsemine"],
                "must_cover_event_classes": ["combat", "travel"],
                "expected_events": expected,
            },
        )
        verdict = per_gate_verdict(violations)
        assert verdict["SE5"] == "FAIL"
        tvs = telemetry["se5_term_violations"]
        assert len(tvs) == 1
        assert tvs[0]["missing_terms"] == ["Eldritch Blast"]
        assert telemetry["terms_preserved_via_sibling"] == []

    def test_fail_when_term_nowhere_in_run(self):
        """(b) Term appears in zero actual events → SE5 FAIL with exactly one
        ``missing_outcome_terms`` violation; sibling telemetry empty."""
        expected = [
            self._expected_with_terms(
                "combat",
                ["caelynn", "ephanna"],
                "swarm battle",
                ["swarm defeated"],
                ["Eldritch Blast"],
            ),
        ]
        actual = [
            _valid_event(
                event_class="combat",
                participants=["caelynn", "ephanna"],
                event_name="swarm fight at edge",
                outcomes=["Ephanna casts an attack spell at the swarm"],
            ),
            _valid_event(
                event_class="travel",
                participants=["karsemine"],
                event_name="post-combat retrospective",
                outcomes=["Karsemine notes the swarm cleared and tracks ride east"],
            ),
        ]
        violations, telemetry = collect_session_events_violations(
            actual,
            {
                "min_event_count": 1,
                "max_event_count": 25,
                "must_cover_participants": ["caelynn", "ephanna", "karsemine"],
                "must_cover_event_classes": ["combat", "travel"],
                "expected_events": expected,
            },
        )
        verdict = per_gate_verdict(violations)
        assert verdict["SE5"] == "FAIL"
        # Exactly one structured term violation, of the expected kind.
        tvs = telemetry["se5_term_violations"]
        assert len(tvs) == 1
        assert tvs[0]["kind"] == "missing_outcome_terms"
        assert tvs[0]["missing_terms"] == ["Eldritch Blast"]
        assert telemetry["missing_terms_total"] >= 1
        assert telemetry["terms_preserved_via_sibling"] == []

    def test_mixed_matched_sibling_and_missing(self):
        """(c) Three required terms — one in matched, one in sibling, one nowhere.

        Assert: SE5 FAIL (because of the third), exactly one violation listing
        only the third term, telemetry counts only the third term in
        ``missing_terms_total``, and sibling telemetry has one entry for the
        second term."""
        expected = [
            self._expected_with_terms(
                "combat",
                ["caelynn", "ephanna"],
                "swarm battle",
                ["swarm defeated"],
                ["Thunderwave", "Eldritch Blast", "scimitar"],
            ),
        ]
        # Matched actual (best participant overlap, preserves Thunderwave only):
        actual = [
            _valid_event(
                event_class="combat",
                participants=["caelynn", "ephanna"],
                event_name="swarm fight at edge",
                outcomes=["Caelynn casts Thunderwave splitting the swarm"],
            ),
            # Sibling actual with participant overlap carries "Eldritch Blast"
            # → soft-pass via sibling.
            _valid_event(
                event_class="travel",
                participants=["ephanna", "karsemine"],
                event_name="post-combat retrospective",
                outcomes=["Karsemine recalls Ephanna's Eldritch Blast volleys"],
            ),
            # Another sibling — does not carry any of the missing terms.
            _valid_event(
                event_class="conversation",
                participants=["bonogo"],
                event_name="bonogo ramble",
                outcomes=["Bonogo recounts the firkin run"],
            ),
        ]
        violations, telemetry = collect_session_events_violations(
            actual,
            {
                "min_event_count": 1,
                "max_event_count": 25,
                "must_cover_participants": ["caelynn", "ephanna", "karsemine", "bonogo"],
                "must_cover_event_classes": ["combat", "travel", "conversation"],
                "expected_events": expected,
            },
        )
        verdict = per_gate_verdict(violations)
        assert verdict["SE5"] == "FAIL", f"Expected SE5 FAIL, got {verdict}"
        # Exactly one structured term violation, listing only the third term.
        tvs = telemetry["se5_term_violations"]
        assert len(tvs) == 1
        assert tvs[0]["kind"] == "missing_outcome_terms"
        assert tvs[0]["missing_terms"] == ["scimitar"]
        # Telemetry counts only the third term.
        assert telemetry["missing_terms_total"] == 1
        assert telemetry["expected_events_with_missing_terms"] == [0]
        # Sibling telemetry has one entry — the second term.
        sibling = telemetry["terms_preserved_via_sibling"]
        assert len(sibling) == 1
        assert sibling[0]["expected_event_index"] == 0
        assert sibling[0]["term"] == "Eldritch Blast"
        assert sibling[0]["actual_event_index"] == 1

    def test_backward_compat_canonical_s20_happy_path_still_passes(self):
        """(d) Backward-compat smoke: the canonical S20 happy-path test
        (``TestFullPass.test_full_pass_all_gates``) must still PASS after the
        sibling-fallback change. Re-run its construction inline so this assert
        co-locates with the sibling-fallback suite without modifying the
        original test."""
        full_pass = TestFullPass()
        events = full_pass._build_plausible_events()
        grading = full_pass._build_grading()

        violations, telemetry = collect_session_events_violations(events, grading)
        verdict = per_gate_verdict(violations)
        assert verdict == {
            "SE1": "PASS",
            "SE2": "PASS",
            "SE3": "PASS",
            "SE4": "PASS",
            "SE5": "PASS",
        }, f"Backward-compat regression on canonical S20 happy path: {verdict} (violations={violations})"
        # Sibling-fallback telemetry exists and is well-typed (may be empty —
        # this fixture has no must_preserve_terms in its grading).
        assert "terms_preserved_via_sibling" in telemetry
        assert isinstance(telemetry["terms_preserved_via_sibling"], list)


# ---------------------------------------------------------------------------
# per_gate_verdict
# ---------------------------------------------------------------------------


class TestPerGateVerdict:
    def test_all_pass_when_no_violations(self):
        verdict = per_gate_verdict({})
        assert verdict == {"SE1": "PASS", "SE2": "PASS", "SE3": "PASS", "SE4": "PASS", "SE5": "PASS"}

    def test_se1_fail_when_se1_violations(self):
        verdict = per_gate_verdict({"se1": ["some error"]})
        assert verdict["SE1"] == "FAIL"
        assert verdict["SE2"] == "PASS"

    def test_all_fail_when_all_violated(self):
        verdict = per_gate_verdict({"se1": ["e1"], "se2": ["e2"], "se3": ["e3"], "se4": ["e4"], "se5": ["e5"]})
        assert all(v == "FAIL" for v in verdict.values())


# ---------------------------------------------------------------------------
# Full integration test (top-level orchestration)
# ---------------------------------------------------------------------------


class TestFullPass:
    """Build a plausible events list that should pass all gates against gold-shaped grading."""

    def _build_plausible_events(self) -> list[dict]:
        """15 events that cover all required participants and classes."""
        ev = _valid_event
        evidence = _EVIDENCE_ID
        return [
            ev(event_class="combat", participants=["ephanna", "karsemine", "caelynn", "thrin_branchborn"],
               event_name="Red gnat swarm battle at forest edge",
               outcomes=["swarm defeated", "Caelynn Thunderwave splits swarm"], evidence_id=evidence),
            ev(event_class="social_conflict", participants=["bonogo", "stacey", "stuart"],
               event_name="Stuart confronts Stacey in warehouse over stolen gold",
               outcomes=["Stuart threatens Stacey with dart", "Stacey throws gold pouch"], evidence_id=evidence),
            ev(event_class="social_conflict", participants=["bonogo", "stacey"],
               event_name="Bonogo threatens Stacey with knife in alley",
               outcomes=["Stacey runs home shaken", "knife threat"], evidence_id=evidence),
            ev(event_class="conversation", participants=["caelynn", "ephanna", "karsemine", "stafl"],
               event_name="Party reports forest findings to Stafl",
               outcomes=["do not attack trees directly", "forest responds to ground changes"], evidence_id=evidence),
            ev(event_class="social_conflict", participants=["marla_brambleback", "bonogo", "stafl"],
               event_name="Marla Brambleback confronts Bonogo over Stacey harassment",
               outcomes=["Marla berates Bonogo", "Marla grapples Bonogo"], evidence_id=evidence),
            ev(event_class="social_conflict", participants=["caelynn", "marla_brambleback", "bonogo"],
               event_name="Caelynn de-escalates Marla vs Bonogo with bracelet",
               outcomes=["Caelynn uses bracelet to diffuse aggression"], evidence_id=evidence),
            ev(event_class="discovery", participants=["caelynn", "ephanna", "karsemine", "bonogo"],
               event_name="Fortification fires drive forest retreat eastward",
               outcomes=["trees pull back and turn east", "town cheers"], evidence_id=evidence),
            ev(event_class="conversation", participants=["caelynn"],
               event_name="Mayor denies knowledge of Lysandra",
               outcomes=["mayor never heard of Lysandra"], evidence_id=evidence),
            ev(event_class="conversation", participants=["caelynn", "sara_mirathorn_operator", "captain_lysandra_ironveil"],
               event_name="Caelynn contacts Sara then connects to Lysandra via rockie-talkie",
               outcomes=["Sara connects Caelynn to Lysandra", "Lysandra exhausted and disoriented"], evidence_id=evidence),
            ev(event_class="travel", participants=["caelynn", "ephanna", "karsemine", "bonogo", "thrin_branchborn"],
               event_name="Karsemine tracks Lysandra group reaches wagon camp",
               outcomes=["group finds wagon and wandering horses after 30 minutes"], evidence_id=evidence),
            ev(event_class="discovery", participants=["caelynn", "captain_lysandra_ironveil"],
               event_name="Lysandra found with shimmery cult eyes drawing tower blueprint",
               outcomes=["shimmery eyes like cult members", "tower blueprint in dirt"], evidence_id=evidence),
            ev(event_class="ritual", participants=["caelynn", "captain_lysandra_ironveil"],
               event_name="Caelynn administers antidote tea to cure Lysandra of cult influence",
               outcomes=["Lysandra cured of spell", "antidote tea prepared"], evidence_id=evidence),
            ev(event_class="investigation", participants=["stafl"],
               event_name="Stafl investigates provisions and finds tainted meat in jerky crates",
               outcomes=["tainted meat found", "bacon untouched", "jerky crates must be burned"], evidence_id=evidence),
            ev(event_class="conversation", participants=["caelynn", "sara_mirathorn_operator"],
               event_name="Caelynn reports Lysandra found safe and tainted meat discovered to Sara",
               outcomes=["Sara concerned about trust in Mirathorn", "transferred to Professor Tealeaf"], evidence_id=evidence),
            ev(event_class="conversation", participants=["ephanna", "caelynn", "marla_brambleback"],
               event_name="Ephanna announces Questionable Company departure Marla asks about Bonogo",
               outcomes=["party leaving town to continue journey"], evidence_id=evidence),
        ]

    def _build_grading(self) -> dict:
        return {
            "min_event_count": 10,
            "max_event_count": 25,
            "must_cover_participants": [
                "captain_lysandra_ironveil",
                "caelynn",
                "karsemine",
                "ephanna",
                "sara_mirathorn_operator",
                "bonogo",
                "marla_brambleback",
                "stacey",
            ],
            "must_cover_event_classes": [
                "combat",
                "conversation",
                "discovery",
                "social_conflict",
                "ritual",
                "investigation",
            ],
            "expected_events": [
                _valid_event(
                    event_class="combat",
                    participants=["caelynn", "ephanna"],
                    event_name="swarm battle at forest edge",
                    outcomes=["swarm defeated"],
                ),
                _valid_event(
                    event_class="social_conflict",
                    participants=["bonogo", "stacey"],
                    event_name="knife threat alley",
                    outcomes=["Stacey runs home"],
                ),
                _valid_event(
                    event_class="conversation",
                    participants=["caelynn", "sara_mirathorn_operator"],
                    event_name="rockie talkie Sara",
                    outcomes=["Sara connects Lysandra"],
                ),
                _valid_event(
                    event_class="discovery",
                    participants=["caelynn", "captain_lysandra_ironveil"],
                    event_name="tower blueprint found Lysandra",
                    outcomes=["tower blueprint"],
                ),
            ],
        }

    def test_full_pass_all_gates(self):
        events = self._build_plausible_events()
        grading = self._build_grading()

        violations, telemetry = collect_session_events_violations(events, grading)
        verdict = per_gate_verdict(violations)

        assert verdict == {
            "SE1": "PASS",
            "SE2": "PASS",
            "SE3": "PASS",
            "SE4": "PASS",
            "SE5": "PASS",
        }, f"Expected all PASS but got: {verdict}\nViolations: {violations}"

    def test_telemetry_fields_present(self):
        events = self._build_plausible_events()
        grading = self._build_grading()
        _, telemetry = collect_session_events_violations(events, grading)
        assert "event_count" in telemetry
        assert "participants_seen" in telemetry
        assert "event_classes_seen" in telemetry
        assert "expected_event_coverage_ratio" in telemetry
        assert "unmatched_expected_event_indices" in telemetry
        # SE5 outcome-vocabulary telemetry
        assert "expected_events_with_missing_terms" in telemetry
        assert "missing_terms_total" in telemetry
        assert "se5_term_violations" in telemetry
        assert telemetry["event_count"] == 15
        assert "caelynn" in telemetry["participants_seen"]
        assert "combat" in telemetry["event_classes_seen"]
        # No must_preserve_terms in this grading → empty term-violation telemetry
        assert telemetry["expected_events_with_missing_terms"] == []
        assert telemetry["missing_terms_total"] == 0
        assert telemetry["se5_term_violations"] == []


# ---------------------------------------------------------------------------
# Top-level orchestration with must_preserve_terms (telemetry + gate FAIL)
# ---------------------------------------------------------------------------


class TestMustPreserveTermsIntegration:
    """SE5 with must_preserve_terms in the gold should fail the gate and
    populate expected_events_with_missing_terms / missing_terms_total telemetry."""

    def _events(self) -> list[dict]:
        # Plausible events covering all required participants + classes.
        evidence = _EVIDENCE_ID
        ev = _valid_event
        return [
            ev(event_class="combat",
               participants=["ephanna", "karsemine", "caelynn", "thrin_branchborn"],
               event_name="Red gnat swarm battle at forest edge",
               # Missing "Eldritch Blast" — paraphrased away.
               outcomes=[
                   "Karsemine lands 4 scimitar hits using Zephyr Strike",
                   "Ephanna casts an attack spell",
                   "Caelynn casts Thunderwave splitting the swarm 10 feet back",
               ],
               evidence_id=evidence),
            ev(event_class="social_conflict",
               participants=["bonogo", "stacey"],
               event_name="Bonogo intimidates Stacey with knife threat",
               outcomes=["Bonogo holds knife to Stacey's throat", "Stacey runs home shaken"],
               evidence_id=evidence),
            ev(event_class="conversation",
               participants=["caelynn", "sara_mirathorn_operator"],
               event_name="Caelynn calls Sara via rockie-talkie",
               outcomes=["Sara connects Caelynn to Lysandra"],
               evidence_id=evidence),
            ev(event_class="discovery",
               participants=["captain_lysandra_ironveil", "caelynn"],
               event_name="Lysandra found drawing tower blueprint",
               outcomes=["shimmery eyes like cult", "tower blueprint in dirt"],
               evidence_id=evidence),
        ]

    def _grading(self) -> dict:
        return {
            "min_event_count": 1,
            "max_event_count": 25,
            "must_cover_participants": [
                "captain_lysandra_ironveil", "caelynn", "ephanna", "karsemine",
                "sara_mirathorn_operator", "bonogo", "stacey",
            ],
            "must_cover_event_classes": ["combat", "social_conflict", "conversation", "discovery"],
            "expected_events": [
                _valid_event(
                    event_class="combat",
                    participants=["caelynn", "ephanna", "karsemine"],
                    event_name="swarm battle",
                    outcomes=["swarm defeated"],
                ) | {"must_preserve_terms": ["scimitar", "Thunderwave", "Eldritch Blast"]},
                _valid_event(
                    event_class="social_conflict",
                    participants=["bonogo", "stacey"],
                    event_name="knife threat",
                    outcomes=["Stacey runs home"],
                ) | {"must_preserve_terms": ["knife"]},
                _valid_event(
                    event_class="conversation",
                    participants=["caelynn", "sara_mirathorn_operator"],
                    event_name="rockie talkie",
                    outcomes=["Sara connects Lysandra"],
                ) | {"must_preserve_terms": ["rockie-talkie", "Sara"]},
                _valid_event(
                    event_class="discovery",
                    participants=["captain_lysandra_ironveil"],
                    event_name="tower blueprint",
                    outcomes=["blueprint drawn"],
                ) | {"must_preserve_terms": ["blueprint", "tower"]},
            ],
        }

    def test_missing_term_fails_se5_gate(self):
        events = self._events()
        grading = self._grading()
        violations, telemetry = collect_session_events_violations(events, grading)
        verdict = per_gate_verdict(violations)

        # SE5 must FAIL because expected_events[0] is missing "Eldritch Blast".
        assert verdict["SE5"] == "FAIL"
        # Other gates remain PASS.
        assert verdict["SE1"] == "PASS"
        assert verdict["SE2"] == "PASS"
        assert verdict["SE3"] == "PASS"
        assert verdict["SE4"] == "PASS"

        # Telemetry attribution is precise.
        assert telemetry["expected_events_with_missing_terms"] == [0]
        assert telemetry["missing_terms_total"] == 1
        tvs = telemetry["se5_term_violations"]
        assert len(tvs) == 1
        assert tvs[0]["kind"] == "missing_outcome_terms"
        assert tvs[0]["expected_event_index"] == 0
        assert tvs[0]["missing_terms"] == ["Eldritch Blast"]

    def test_all_terms_preserved_passes_gate(self):
        events = self._events()
        # Patch the combat event to include "Eldritch Blast"
        events[0]["outcomes"] = [
            "Karsemine lands 4 scimitar hits using Zephyr Strike",
            "Ephanna's second Eldritch Blast removes a cluster",
            "Caelynn casts Thunderwave splitting the swarm 10 feet back",
        ]
        grading = self._grading()
        violations, telemetry = collect_session_events_violations(events, grading)
        verdict = per_gate_verdict(violations)
        assert verdict == {
            "SE1": "PASS", "SE2": "PASS", "SE3": "PASS", "SE4": "PASS", "SE5": "PASS",
        }
        assert telemetry["expected_events_with_missing_terms"] == []
        assert telemetry["missing_terms_total"] == 0


# ---------------------------------------------------------------------------
# referenced_slugs[] schema + grader-policy regression
# ---------------------------------------------------------------------------


class TestReferencedSlugsSchema:
    """The new optional ``referenced_slugs[]`` field on event_record (added 2026-04-22).

    Semantics: slugs of entities NAMED or REFERENCED in connection with this event but
    NOT actively participating. Designed for the Kirfan-class failure mode
    (Backlog.md:24): when a recap names an NPC in a "Big beats" header but describes
    the same beat in prose as "the elderly fisherman", Stage A captures the event
    but currently drops the named slug. ``referenced_slugs[]`` preserves that naming
    evidence for a downstream entity-resolution stage.

    These tests pin the schema-level contract (additive, optional, string-only items)
    AND verify SE3/SE5 grader behavior is unchanged by the new field — that policy
    decision is queued in Backlog.md as its own measurement-driven ticket.
    """

    def test_schema_accepts_referenced_slugs_populated(self) -> None:
        record = {
            "event_class": "discovery",
            "time_scope": "scene",
            "certainty": "observed",
            "participants": ["bonogo", "stafl", "baergrom"],
            "referenced_slugs": ["kirfan"],
        }
        validate_instance(record, "event_record.schema.json")

    def test_schema_accepts_referenced_slugs_absent(self) -> None:
        """Backward compat: existing event_records without referenced_slugs still pass."""
        record = {
            "event_class": "discovery",
            "time_scope": "scene",
            "certainty": "observed",
            "participants": ["bonogo", "stafl"],
        }
        assert "referenced_slugs" not in record
        validate_instance(record, "event_record.schema.json")

    def test_schema_accepts_empty_referenced_slugs(self) -> None:
        record = {
            "event_class": "discovery",
            "time_scope": "scene",
            "certainty": "observed",
            "referenced_slugs": [],
        }
        validate_instance(record, "event_record.schema.json")

    def test_schema_rejects_non_string_referenced_slugs(self) -> None:
        record = {
            "event_class": "discovery",
            "time_scope": "scene",
            "certainty": "observed",
            "referenced_slugs": [123, {"slug": "kirfan"}],
        }
        with pytest.raises(ValidationError):
            validate_instance(record, "event_record.schema.json")

    def test_schema_rejects_empty_string_in_referenced_slugs(self) -> None:
        """Items must be non-empty strings (mirrors participants[] minLength constraint)."""
        record = {
            "event_class": "discovery",
            "time_scope": "scene",
            "certainty": "observed",
            "referenced_slugs": [""],
        }
        with pytest.raises(ValidationError):
            validate_instance(record, "event_record.schema.json")


class TestReferencedSlugsGraderRegression:
    """Regression guard for the deliberate "no grader policy change" decision.

    SE3 and SE5 must be unaffected by ``referenced_slugs[]``. A character that appears
    only in ``referenced_slugs[]`` (and not in any event's ``participants[]``) must
    still trip SE3. This test is the canary for any future accidental grader change.
    """

    def test_se3_still_participants_only_with_referenced_slugs_present(self) -> None:
        """A slug present only in referenced_slugs[] does NOT satisfy must_cover_participants."""
        events = [
            _valid_event(
                participants=["bonogo", "stafl"],
                referenced_slugs=["kirfan"],
            ),
        ]
        violations = collect_se3_violations(events, ["bonogo", "stafl", "kirfan"])
        assert len(violations) == 1
        assert "kirfan" in violations[0]

    def test_se3_passes_when_slug_in_participants_even_with_referenced_slugs(self) -> None:
        """SE3 is satisfied by participants[] alone; referenced_slugs[] is purely additive."""
        events = [
            _valid_event(
                participants=["bonogo", "stafl", "kirfan"],
                referenced_slugs=["marla_brambleback"],
            ),
        ]
        assert collect_se3_violations(events, ["bonogo", "stafl", "kirfan"]) == []

    def test_full_pass_unchanged_when_referenced_slugs_added(self) -> None:
        """Adding referenced_slugs[] to a previously-passing event set must not change verdicts."""
        full_pass = TestFullPass()
        events = full_pass._build_plausible_events()
        for ev in events:
            ev["referenced_slugs"] = ["some_referenced_npc"]
        grading = full_pass._build_grading()

        violations, telemetry = collect_session_events_violations(events, grading)
        verdict = per_gate_verdict(violations)
        assert verdict == {
            "SE1": "PASS",
            "SE2": "PASS",
            "SE3": "PASS",
            "SE4": "PASS",
            "SE5": "PASS",
        }, f"referenced_slugs[] perturbed grader verdict: {verdict} (violations={violations})"
