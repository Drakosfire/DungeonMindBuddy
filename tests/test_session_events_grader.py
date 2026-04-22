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
        violations, ratio, unmatched = collect_se5_violations(actual, expected)
        assert violations == [], f"Expected no violations but got: {violations}"
        assert ratio == 1.0
        assert unmatched == []

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
        violations, ratio, unmatched = collect_se5_violations(actual, expected)
        assert ratio == 0.0
        assert len(unmatched) == 2
        # Since ratio < 0.5, should have a violation
        assert violations

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
        violations, ratio, unmatched = collect_se5_violations(actual, expected)
        assert ratio == pytest.approx(0.5)
        # At exactly 0.5 threshold → PASS (ratio NOT < threshold)
        assert violations == []

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
        violations, ratio, unmatched = collect_se5_violations(actual, expected)
        assert ratio == pytest.approx(0.25)
        assert violations  # below threshold

    def test_empty_expected_events_passes(self):
        violations, ratio, unmatched = collect_se5_violations([_valid_event()], [])
        assert violations == []
        assert ratio == 1.0
        assert unmatched == []


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
        assert telemetry["event_count"] == 15
        assert "caelynn" in telemetry["participants_seen"]
        assert "combat" in telemetry["event_classes_seen"]
