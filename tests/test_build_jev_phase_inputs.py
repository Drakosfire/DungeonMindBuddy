"""Role-specific input and exposure proofs; synthetic decisions, real SDK/APP."""

import json
from dataclasses import replace
from hashlib import sha256

import pytest

from apps.live_control_server.services import build_jev_dispatch as policy
from apps.live_control_server.services.build_jev_compaction import project_evidence
from apps.live_control_server.services.build_jev_driver import BuildJevDriver
from apps.live_control_server.services.build_jev_harness import BuildJevHarness
from apps.live_control_server.services.build_jev_transitions import (
    FRONTIER_POLICY,
    BuildJevTransitions,
    Disposition,
)
from application_state.agent_conversation import types as ledger
from tests.test_build_jev_transitions import SCOPE, actions, answer, unit
from tests.test_build_jev_frontier import coverage_reply, negative
from tests.test_agent_build_jev_ordinary_harness import (
    DecisionWire,
    WriterWire,
    ordinary_case,
    build_case as _build_case,
)
from tests.test_agent_build_governed_graph import execute


@pytest.fixture
def build_case(tmp_path, monkeypatch, application_state_dsn):
    return _build_case.__wrapped__(tmp_path, monkeypatch, application_state_dsn)


def machine(*labels):
    return BuildJevTransitions(
        "Which uses are described?",
        SCOPE,
        actions(*labels),
        frontier_policy=FRONTIER_POLICY,
        phase_input_policy=policy.PHASE_POLICY,
    )


def test_full_assessment_is_exact_but_navigation_has_no_evidence_bodies():
    m = machine("First", "Other")
    assert m.step.phase == "navigate"
    assert [q.name for q in m.step.questions] == ["next"]
    answer(m, next_id="a0")
    evidence = unit(
        "u0",
        "UNIQUE PASSAGE BODY. " * 700,
        epistemic_kind="belief",
        temporal_scope={"as_of": "earlier"},
    )
    m.accept_acquisition({"a0": (evidence,)})
    assessment = m.step
    assert assessment.phase == "assess" and "legal_next_actions" not in assessment.state
    assert "next" not in {q.name for q in assessment.questions}
    expected = project_evidence(SCOPE, (evidence,))
    assert {k: assessment.state[k] for k in expected} == expected
    navigation = answer(m, label="more_evidence", support="u0")
    assert navigation.phase == "navigate" and "evidence" not in navigation.state
    assert "passages" not in navigation.state and "UNIQUE PASSAGE" not in json.dumps(
        navigation.state
    )
    assert {q.name for q in navigation.questions} == {"next"}
    metadata = navigation.state["acquired_discovery"][0]["units"][0]
    assert metadata["source_class"] == evidence.source_class
    assert metadata["epistemic_kind"] == "belief" and metadata["temporal_scope"] == {
        "as_of": "earlier"
    }
    binding = navigation.state["assessment_binding"]
    assert (
        binding["request_id"] == assessment.request_id and binding["supported"] is False
    )
    assert (
        binding["evidence_basis_sha256"]
        == navigation.state["coverage_frontier"]["evidence_basis_sha256"]
    )


def test_unknown_coverage_reads_then_reassesses_full_evidence_and_stops_partial():
    m = machine("First", "Unknown", "Deferred")
    answer(m, next_id="a0")
    m.accept_acquisition({"a0": (unit("u0", "Known use."),)})
    coverage = answer(m, label="sufficient", support="u0")
    assert coverage.phase == "coverage" and "passages" not in coverage.state
    assert all(q.name.startswith("use_") for q in coverage.questions)
    assert coverage_reply(m, ["unknown", negative(0.6)]).actions[0].id == "a1"
    m.accept_acquisition({"a1": (unit("u1", "New distinct use."),)})
    assert m.step.phase == "assess" and m.step.state["assessment_binding"] is None
    answer(m, label="sufficient", support="u1")
    end = coverage_reply(m, [negative(0.6)])
    assert (
        end.status == "provisionally_supported"
        and end.coverage_status == "heuristic_partial"
    )
    assert end.acquired_action_ids == ("a0", "a1") and len(end.evidence) == 2


def test_insufficient_navigation_abstains_after_one_current_coverage_judgment():
    m = machine("Deferred")
    initial = m.step.request_id
    answer(m)
    step = coverage_reply(m, [negative(0.7)])
    assert step.phase == "navigate" and step.request_id != initial
    end = answer(m)
    assert isinstance(end, Disposition) and end.status == "insufficient_evidence"
    assert len(end.coverage_judgments) == 1


def test_two_hops_and_contradiction_remain_assessment_owned():
    m = machine("First", "Necessary hop", "Competing")
    answer(m, next_id="a0")
    m.accept_acquisition({"a0": (unit("u0", "A leads B."),)})
    answer(m)
    answer(m, next_id="a1")
    m.accept_acquisition({"a1": (unit("u1", "B governs C."),)})
    answer(m, label="sufficient", support="u1")
    coverage_reply(m, ["useful"])
    m.accept_acquisition({"a2": (unit("u2", "A does not lead B now."),)})
    end = answer(m, label="conflict")
    assert end.status == "unresolved_conflict" and len(end.evidence) == 3
    assert end.coverage_status == "catalog_exhausted"


def test_phase_policy_is_explicit_and_no_catalog_has_honest_empty_terminal():
    with pytest.raises(ValueError, match="explicit frontier"):
        BuildJevTransitions(
            "Question", SCOPE, (), phase_input_policy=policy.PHASE_POLICY
        )
    assert machine().step.status == "insufficient_evidence"
    legacy = BuildJevTransitions(
        "Question", SCOPE, actions("One"), frontier_policy=FRONTIER_POLICY
    )
    assert legacy.step.phase == "assess" and "next" in {
        q.name for q in legacy.step.questions
    }
    assert "phase_input_policy" not in legacy.step.state


def test_actual_sdk_coverage_has_no_current_source_exposure_but_writer_does(
    build_case, monkeypatch, tmp_path
):
    decisions, writer = DecisionWire(), WriterWire()
    runtime = BuildJevHarness(decision_transport=decisions, writer_transport=writer)
    case, _ = ordinary_case(build_case, monkeypatch)
    execute(case, tmp_path, runtime)
    execution = runtime.adapter.turn.graph_context_execution
    authorizations = [
        e
        for e in execution.events
        if isinstance(e, ledger.ProviderAttemptAuthorizedEventV3)
    ]
    bodies = [json.loads(request.content) for request in decisions.calls]
    assert [b["state"]["decision"]["phase"] for b in bodies] == [
        "select",
        "navigate",
        "assess",
        "coverage",
    ]
    for body, event in zip(bodies[1:], authorizations[1:], strict=False):
        state = body["state"]
        assert (
            state["schema"] == policy.PHASE_SCHEMA
            and state["input_policy"] == policy.PHASE_POLICY
        )
        if state["decision"]["phase"] in {"navigate", "coverage"}:
            assert event.included_graph_event_ids == []
            assert event.included_evidence_ref_ids == []
            assert event.included_source_read_event_ids == []
            assert "passages" not in state["decision"]["state"]
        if state["decision"]["phase"] == "coverage":
            receipt = state["phase_binding"]["assessment_receipt"]
            assert receipt["provider_attempt_id"] == str(
                authorizations[2].provider_attempt_id
            )
            assert receipt["envelope_sha256"] == authorizations[2].envelope_sha256
    assert len(writer.calls) == 1
    assert authorizations[-1].included_source_read_event_ids
    assert runtime.adapter.turn.completion.source_citations


@pytest.mark.parametrize(
    "mutation",
    [
        "basis",
        "assessment",
        "receipt",
        "material",
        "policy",
        "inject_passage",
        "schema_downgrade",
        "unacknowledged_parent",
    ],
)
def test_forged_phase_input_is_rejected_before_dispatch(
    build_case, monkeypatch, tmp_path, mutation
):
    original = BuildJevDriver.authorize
    rejected = []

    def authorize(driver, prepared):
        body = json.loads(prepared.body)
        if (
            body["state"].get("schema") != policy.PHASE_SCHEMA
            or body["state"]["decision"]["phase"] != "coverage"
        ):
            return original(driver, prepared)
        state = body["state"]
        binding = state["phase_binding"]
        if mutation == "basis":
            binding["evidence_basis_sha256"] = "f" * 64
        elif mutation == "assessment":
            binding["assessment"]["request_id"] = "foreign"
        elif mutation == "receipt":
            binding["assessment_receipt"]["provider_attempt_id"] = "foreign"
        elif mutation == "material":
            binding["acquired_material_sha256"] = "f" * 64
        elif mutation == "policy":
            state["input_policy"] = policy.CONTINUATION_POLICY
        elif mutation == "schema_downgrade":
            state["schema"] = policy.CONTINUATION_SCHEMA
            state["input_policy"] = policy.CONTINUATION_POLICY
        elif mutation == "unacknowledged_parent":
            driver._assessment_receipt["provider_attempt_id"] = "foreign"
            binding["assessment_receipt"]["provider_attempt_id"] = "foreign"
        else:
            state["decision"]["state"]["passages"] = {"p1": "injected source"}
        raw = json.dumps(body).encode()
        # Even a forged staged parent snapshot must match the independently live
        # machine phase commitment and discovery view.
        driver._pending = replace(driver._pending, state_json=policy.canonical(state))
        accepted = original(
            driver,
            replace(
                prepared,
                body=raw,
                body_size=len(raw),
                body_sha256=sha256(raw).hexdigest(),
            ),
        )
        rejected.append(accepted)
        return accepted

    monkeypatch.setattr(BuildJevDriver, "authorize", authorize)
    decisions, writer = DecisionWire(), WriterWire()
    case, _ = ordinary_case(build_case, monkeypatch)
    from apps.live_control_server.services.agent_turn_service import (
        AgentTurnServiceError,
    )

    with pytest.raises(AgentTurnServiceError):
        execute(
            case,
            tmp_path,
            BuildJevHarness(decision_transport=decisions, writer_transport=writer),
        )
    assert rejected == [False] and len(decisions.calls) == 3 and not writer.calls


def _authoring_machine(question):
    from uuid import uuid4
    from application_state.agent_conversation.build_world_context import (
        BuildContextScope, FrozenBuildBasis, PrimarySectionOrigin,
    )
    from apps.live_control_server.services.build_jev_transitions import (
        ContextEvidence, ReadAction, WorldReadAction, JOINT_SUPPORT_POLICY,
    )
    basis = FrozenBuildBasis(world_id="world:test", document_id="doc:test",
        registry_revision=1, content_sha256="f" * 64, visibility="internal")
    scope = BuildContextScope(managed_world_id="world:test", world_id="native:test",
        binding_version=1, graph_revision="rev:1", primary_basis=basis,
        client_thread_id="thread:test", client_turn_id="turn:test")
    m = BuildJevTransitions(question, scope, (
        ReadAction(id="page", label="Current authored page", kind="saved_build_section", unit_ids=("page",)),
        WorldReadAction(id="world-object:other", label="World entity: Harbor Watch", kind="world_object"),
    ), frontier_policy=FRONTIER_POLICY, phase_input_policy=policy.PHASE_POLICY,
        support_policy=JOINT_SUPPORT_POLICY)
    rule = m.step.state["authoring_support_rule"]
    assert "not conversation history, source titles or discovery hints" in rule
    assert "first read the relevant saved_build_section actions" in rule
    assert "open relevant saved sections before judging context adequate" in m.step.questions[0].question
    answer(m, next_id="page")
    text = "Lantern Hill is an orchard town. Its founders valued self-reliance; lantern keepers tend the trees."
    m.accept_acquisition({"page": (ContextEvidence(id="page", scope=scope,
        origin=PrimarySectionOrigin(source_basis=basis, section_event_id=uuid4(), read_id=uuid4()),
        subject="Current authored page", text=text, content_sha256=sha256(text.encode()).hexdigest(),
        source_class="saved_build_world_reference", provenance=({"section_read_id": "read:page"},)),)})
    return m


def test_authoring_context_is_bound_through_assessment_and_coverage_without_minting_facts():
    m = _authoring_machine("Invent ten folksy names fitting the town's culture.")
    assess = m.step
    rule = assess.state["authoring_support_rule"]
    assert "do not need to exist in sources" in rule
    assert "established facts" in rule and "mixed creative/factual" in rule
    questions = {q.name: q.question for q in assess.questions}
    assert "authoring_support_rule" in questions["sufficiency"]
    assert "requested inventions themselves" in questions["joint_support"]
    original = project_evidence(m._scope, m._view_units())
    assert {k: assess.state[k] for k in original} == original
    coverage = answer(m, label="sufficient", relevance={"joint_support": .99})
    assert coverage.state["assessment_binding"]["request_id"] == assess.request_id
    assert coverage.state["authoring_support_rule"] == rule
    assert "optional source of inspiration is not_useful" in coverage.state["coverage_rule"]
    end = coverage_reply(m, [negative(.99)])
    assert end.status == "provisionally_supported" and end.acquired_action_ids == ("page",)
    assert len(end.evidence) == 1 and end.evidence[0].text == m._units["page"].text
    # A semantic judgment permits writing; it does not create source evidence.
    assert end.coverage_status != "catalog_exhausted"


def test_mixed_authoring_request_still_needs_actual_missing_factual_support():
    m = _authoring_machine("Verify the Harbor Watch captain, then invent a fitting town nickname.")
    navigation = answer(m, label="more_evidence", relevance={"joint_support": .01})
    assert navigation.phase == "navigate"
    assert navigation.state["assessment_binding"]["supported"] is False
    assert "authoring_support_rule" in navigation.questions[0].question
    read = answer(m, next_id="world-object:other")
    assert [a.id for a in read.actions] == ["world-object:other"]
    # A factual-only scope gets no authoring permission, even with creative words.
    source_only = BuildJevTransitions("Invent a name", SCOPE, actions("Source"),
        frontier_policy=FRONTIER_POLICY, phase_input_policy=policy.PHASE_POLICY)
    assert "authoring_support_rule" not in source_only.step.state
