"""Deferred coverage scheduling, synthetic decisions only; baseline remains separate."""

from copy import deepcopy

import pytest

from apps.live_control_server.services.build_jev_transitions import (
    FRONTIER_POLICY,
    AcquisitionIntent,
    BuildJevTransitions,
    DecisionIntent,
    FrontierDisposition,
    ReadAction,
)
from tests.test_build_jev_transitions import SCOPE, actions, answer, unit


def machine(*labels):
    return BuildJevTransitions(
        "Which uses are described?",
        SCOPE,
        actions(*labels),
        frontier_policy=FRONTIER_POLICY,
    )


def coverage_reply(m, labels):
    step = m.step
    assert step.phase == "coverage"
    answers = {}
    for i, value in enumerate(labels):
        selected, scores = value if isinstance(value, tuple) else (value, None)
        answers[f"use_{i}"] = {"kind": "choice", "selected": selected}
        if scores is not None:
            answers[f"use_{i}"]["probabilities"] = scores
    return m.accept_decision(step.request_id, step.model, answers)


def negative(score):
    return "not_useful", {"not_useful": score, "useful": 0, "unknown": 1 - score}


def test_fifty_negative_one_unknown_shape_reads_unknown_saved_range_only():
    catalog = actions(*(f"Candidate {i}" for i in range(50))) + (
        ReadAction(
            id="saved:200:368",
            label="Saved Build source, lines 200–368",
            kind="saved_build_section",
            unit_ids=("saved:200:368",),
        ),
    )
    m = BuildJevTransitions(
        "Which uses are described?", SCOPE, catalog, frontier_policy=FRONTIER_POLICY
    )
    answer(m)
    intent = coverage_reply(
        m, [negative(0.95)] * 15 + [negative(0.7)] * 35 + ["unknown"]
    )
    assert isinstance(intent, AcquisitionIntent)
    assert [a.id for a in intent.actions] == ["saved:200:368"]
    assert len(m._excluded) == 15 and len(m._deferred) == 35
    assert m._visited == set() and m._units == {}
    assert len(m._coverage_judgments[0]["answers"]) == 51


def test_useful_before_unknown_one_unique_acquisition_per_evidence_wave():
    m = machine("Unknown", "Useful", "Deferred")
    answer(m)
    step = coverage_reply(m, ["unknown", "useful", negative(0.7)])
    assert [a.id for a in step.actions] == ["a1"]
    old_basis = m._coverage_basis
    m.accept_acquisition({"a1": (unit("u1", "A distinct supported use."),)})
    assert m.step.phase == "assess"
    assert m._coverage_basis is None and not m._deferred and not m._excluded
    assert m.step.state["coverage_frontier"]["evidence_basis_sha256"] != old_basis
    assert len(m._coverage_judgments) == 1  # historical answers retained, invalidated
    assert "a1" not in m.step.state["legal_next_actions"]
    answer(m, label="sufficient", support="u1")
    intent = coverage_reply(m, ["unknown", negative(0.7)])
    assert [a.id for a in intent.actions] == ["a0"]


def test_sufficient_with_deferred_is_truthful_partial_and_writer_audit_is_compact():
    m = machine("Known", "Deferred")
    answer(m, next_id="a0")
    m.accept_acquisition({"a0": (unit("u0", "Known use."),)})
    answer(m, label="sufficient", support="u0")
    end = coverage_reply(m, [negative(0.7)])
    assert isinstance(end, FrontierDisposition)
    assert end.status == "provisionally_supported"
    assert end.coverage_status == "heuristic_partial"
    assert end.deferred_unread_ids == ("a1",) and end.excluded_unread_ids == ()
    assert end.acquired_action_ids == ("a0",)
    summary = end.writer_summary()
    assert summary["deferred_unread_ids"] == ["a1"]
    assert "answers" not in str(summary) and "probabilities" not in str(summary)
    assert len(summary["coverage_judgments_sha256"]) == 64
    assert (
        end.coverage_judgments[0]["evidence_basis_sha256"] == end.evidence_basis_sha256
    )


@pytest.mark.parametrize("continue_read", [False, True])
def test_insufficient_frontier_can_select_deferred_or_abstain_without_cycle(
    continue_read,
):
    m = machine("Deferred")
    first = m.step.request_id
    answer(m)
    step = coverage_reply(m, [negative(0.6)])
    assert isinstance(step, DecisionIntent) and step.phase == "assess"
    assert step.request_id != first
    assert step.state["coverage_frontier"]["current_coverage_judged"] is True
    step = answer(m, next_id="a0" if continue_read else "none")
    if continue_read:
        assert [a.id for a in step.actions] == ["a0"]
        m.accept_acquisition({"a0": (unit("u0", "Support acquired only now."),)})
        end = answer(m, label="sufficient", support="u0")
        assert (
            end.status == "provisionally_supported"
            and end.coverage_status == "catalog_exhausted"
        )
    else:
        assert (
            step.status == "insufficient_evidence"
            and step.coverage_status == "heuristic_partial"
        )
    assert len(m._coverage_judgments) == 1


def test_new_evidence_reopens_high_confidence_exclusions_without_erasing_history():
    m = machine("Excluded for now", "Necessary hop")
    answer(m)
    coverage_reply(m, [negative(0.99), "unknown"])
    m.accept_acquisition({"a1": (unit("u1", "New connection to first candidate."),)})
    assert "a0" in m.step.state["legal_next_actions"]
    assert m._coverage_judgments[0]["excluded_ids"] == ["a0"]
    assert not m._excluded
    assert answer(m, next_id="a0").actions[0].id == "a0"


@pytest.mark.parametrize(
    "scores,excluded",
    [
        ({"not_useful": 0.9, "useful": 0.05, "unknown": 0.05}, True),
        ({"not_useful": 0.89, "useful": 0.05, "unknown": 0.05}, False),
        ({"not_useful": 0.9, "useful": 0.1, "unknown": 0.1}, False),
        (None, False),
    ],
)
def test_exclusion_floor_and_unnormalized_mass_are_unchanged(scores, excluded):
    m = machine("Candidate")
    answer(m)
    coverage_reply(m, [("not_useful", scores)])
    assert ("a0" in m._excluded) is excluded
    assert ("a0" in m._deferred) is not excluded


def test_conflict_survives_coverage_and_deferred_abstention():
    m = machine("Earlier", "Conflicting", "Deferred")
    answer(m, next_id="a0")
    m.accept_acquisition({"a0": (unit("u0", "Earlier claim."),)})
    answer(m, next_id="a1")
    m.accept_acquisition({"a1": (unit("u1", "Conflicting claim."),)})
    answer(m, label="conflict")
    coverage_reply(m, [negative(0.6)])
    end = answer(m, label="conflict")
    assert end.status == "unresolved_conflict" and len(end.evidence) == 2


def test_stale_response_cannot_apply_to_new_evidence_or_scope():
    m = machine("First", "Deferred")
    answer(m)
    request = m.step
    coverage_reply(m, ["useful", negative(0.7)])
    m.accept_acquisition({"a0": (unit("u0", "New evidence."),)})
    with pytest.raises(ValueError, match="request/model differs"):
        m.accept_decision(request.request_id, request.model, {})
    assert m.step.status == "refused"
    other = BuildJevTransitions(
        "Which uses are described?",
        SCOPE.model_copy(update={"world_id": "other"}),
        actions("First", "Deferred"),
        frontier_policy=FRONTIER_POLICY,
    )
    assert other.step.request_id != machine("First", "Deferred").step.request_id


def test_mutable_copies_cannot_change_current_frontier_and_no_retention_combination():
    m = machine("Deferred")
    answer(m)
    coverage_reply(m, [negative(0.7)])
    copied = deepcopy(m.step)
    copied.state["coverage_frontier"]["deferred_unread_ids"].clear()
    assert m.step.state["coverage_frontier"]["deferred_unread_ids"] == ["a0"]
    with pytest.raises(ValueError, match="complete acquired"):
        BuildJevTransitions(
            "Question",
            SCOPE,
            actions("Candidate"),
            frontier_policy=FRONTIER_POLICY,
            retention_policy="question_relevance_packets_v1",
        )
