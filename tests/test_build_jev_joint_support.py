"""Host decisions for distributed support; synthetic judgments are not model accuracy."""
import pytest

from application_state.agent_conversation import types as ledger
from apps.live_control_server.services.build_jev_dispatch import PHASE_POLICY
from apps.live_control_server.services.build_jev_transitions import (
    JOINT_SUPPORT_POLICY, FRONTIER_POLICY, BuildJevTransitions, AcquisitionIntent,
    Disposition,
)
from tests.test_build_jev_transitions import SCOPE, actions, unit, answer
from tests.test_build_jev_frontier import coverage_reply, negative


def machine(*labels):
    return BuildJevTransitions("How does Aster connect to Harbor's government?", SCOPE,
        actions(*labels), frontier_policy=FRONTIER_POLICY, phase_input_policy=PHASE_POLICY,
        support_policy=JOINT_SUPPORT_POLICY)


def acquire_two(m):
    answer(m, next_id="a0")
    m.accept_acquisition({"a0": (unit("u0", "Aster leads the assembly."),)})
    answer(m, label="more_evidence", relevance={"joint_support": 0.1})
    answer(m, next_id="a1")
    m.accept_acquisition({"a1": (unit("u1", "The assembly governs Harbor."),)})


def test_distributed_support_needs_no_individual_whole_answer_witness():
    m = machine("Aster", "Assembly", "Other")
    acquire_two(m)
    q = {q.name: q for q in m.step.questions}
    assert "support" not in q and q["joint_support"].kind == "binary"
    assert "no single unit" in q["joint_support"].question
    coverage = answer(m, label="sufficient", relevance={"joint_support": 0.99})
    assert coverage.phase == "coverage" and coverage.state["assessment_binding"]["supported"]
    end = coverage_reply(m, [negative(0.7)])
    assert isinstance(end, Disposition) and end.status == "provisionally_supported"
    assert end.relevant_ids == ("u0", "u1")
    assert end.coverage_status == "heuristic_partial" and end.deferred_unread_ids == ("a2",)


@pytest.mark.parametrize("mode", ["missing_bridge", "no_relevant_support", "uncertain_joint"])
def test_sufficient_label_cannot_bypass_missing_or_irrelevant_support(mode):
    m = machine("Aster", "Unopened link")
    answer(m, next_id="a0")
    m.accept_acquisition({"a0": (unit("u0", "Aster leads an assembly."),)})
    scores = {"joint_support": 0.0 if mode == "missing_bridge" else 0.49 if mode == "uncertain_joint" else 1.0}
    if mode == "no_relevant_support":
        scores["relevant_0"] = 0.01
    step = answer(m, label="sufficient", relevance=scores)
    assert step.phase == "navigate" and not step.state["assessment_binding"]["supported"]


@pytest.mark.parametrize("epistemic,temporal", [
    ("belief", {"as_of": "earlier"}), ("played_truth", {"as_of": "later"}),
])
def test_joint_support_does_not_erase_conflict_or_qualifications(epistemic, temporal):
    m = machine("Aster", "Harbor")
    answer(m, next_id="a0")
    evidence = unit("u0", "Aster believes the assembly governs Harbor.",
        epistemic_kind=epistemic, temporal_scope=temporal)
    m.accept_acquisition({"a0": (evidence,)})
    step = answer(m, label="conflict", relevance={"joint_support": 1.0})
    assert step.state["assessment_binding"]["conflict"] and not step.state["assessment_binding"]["supported"]
    answer(m, next_id="none")
    followup = coverage_reply(m, [negative(0.7)])
    assert followup.phase == "navigate"
    end = answer(m, next_id="none")
    assert end.status == "unresolved_conflict"
    assert len(end.coverage_judgments) == 1
    assert end.evidence[0].epistemic_kind == epistemic
    assert end.evidence[0].temporal_scope == temporal


def test_float_unknown_source_still_reads_and_invalidates_prior_coverage():
    m = machine("Water walking and goods", "Unknown authored approach")
    answer(m, next_id="a0")
    m.accept_acquisition({"a0": (unit("u0", "Goats walk on water and carry goods."),)})
    answer(m, label="sufficient", relevance={"joint_support": 1.0})
    original_basis = m._basis()
    read = coverage_reply(m, ["unknown"])
    assert isinstance(read, AcquisitionIntent) and read.actions[0].id == "a1"
    m.accept_acquisition({"a1": (unit("u1", "Authored approach farms use goats for labor and transportation."),)})
    assert m._coverage_basis is None and m._basis() != original_basis
    end = answer(m, label="sufficient", relevance={"joint_support": 1.0})
    assert end.status == "provisionally_supported" and end.coverage_status == "catalog_exhausted"
    assert len(end.evidence) == 2


def test_basis_is_stable_across_deferred_bookkeeping_and_commits_catalog():
    m = machine("Aster", "Harbor", "Unclear")
    acquire_two(m)
    answer(m, label="sufficient", relevance={"joint_support": 1.0})
    before = m._basis()
    end = coverage_reply(m, [negative(0.7)])
    assert m._basis() == before and len(end.coverage_judgments) == 1
    m._deferred.clear()
    assert m._basis() == before
    # Same evidence and question with a different immutable catalog has a distinct basis.
    other = machine("Aster", "Harbor", "Different available candidate")
    acquire_two(other)
    assert other._basis() != before


def test_legacy_choice_reply_cannot_masquerade_as_joint_binary():
    m = machine("Aster")
    answer(m, next_id="a0")
    m.accept_acquisition({"a0": (unit("u0", "Aster leads the assembly."),)})
    q = m.step
    reply = {x.name: {"kind": "binary", "probability_true": 1.0} for x in q.questions}
    reply["sufficiency"] = {"kind": "choice", "selected": "sufficient"}
    reply["joint_support"] = {"kind": "choice", "selected": "u0"}
    with pytest.raises(ValueError, match="schema|kind"):
        m.accept_decision(q.request_id, q.model, reply)
    assert m.step.status == "refused"


def test_historical_policy_fieldsets_and_default_baseline_remain_unchanged():
    for cls in [ledger.BuildPhaseActionControllerWriterPolicyV1,
                ledger.BuildEstimatedActionControllerWriterPolicyV1,
                ledger.BuildContainedActionControllerWriterPolicyV1]:
        assert "support_policy" not in cls.model_fields
    baseline = BuildJevTransitions("Question", SCOPE, actions("Aster"))
    answer(baseline, next_id="a0")
    baseline.accept_acquisition({"a0": (unit("u0", "Aster leads the assembly."),)})
    assert next(q for q in baseline.step.questions if q.name == "support").kind == "choice"
    assert "support_policy" not in baseline.step.state
