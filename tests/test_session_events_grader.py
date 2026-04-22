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
    collect_session_events_violations,
    per_gate_verdict,
)


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
