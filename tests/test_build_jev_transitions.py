"""Question-driven host transitions, with synthetic semantic replies and reads."""

import hashlib

import pytest

from apps.live_control_server.services.build_jev_transitions import (
    AcquiredEvidence,
    AcquisitionIntent,
    BuildJevTransitions,
    DecisionIntent,
    Disposition,
    ReadAction,
    SourceScope,
)


SCOPE = SourceScope(
    world_id="world:test",
    graph_revision="rev:1",
    source_artifact_id="artifact:1",
    source_revision_id="source:1",
    source_sha256="f" * 64,
)


def unit(uid, text, **updates):
    return AcquiredEvidence(
        id=uid,
        scope=SCOPE,
        subject=uid,
        text=text,
        content_sha256=hashlib.sha256(text.encode()).hexdigest(),
        source_class="admitted_graph_observation_and_opened_passages",
        provenance=({"source_read_id": "read:" + uid, "start_line": 1, "end_line": 2},),
        **updates,
    )


def actions(*labels):
    return tuple(
        ReadAction(
            id=f"a{i}", label=label, kind="graph_observations", unit_ids=(f"u{i}",)
        )
        for i, label in enumerate(labels)
    )


def answer(
    machine,
    *,
    label="more_evidence",
    next_id="none",
    support="none",
    relevance=None,
    uses=None,
):
    step = machine.step
    assert isinstance(step, DecisionIntent)
    replies = {}
    for q in step.questions:
        if q.kind == "binary":
            replies[q.name] = {
                "kind": "binary",
                "probability_true": (relevance or {}).get(q.name, 0.99),
            }
        else:
            selected = (
                (uses or {}).get(q.name, "unknown")
                if q.name.startswith("use_")
                else {"sufficiency": label, "support": support, "next": next_id}[q.name]
            )
            replies[q.name] = {"kind": "choice", "selected": selected}
            if selected == "not_useful":
                replies[q.name]["probabilities"] = {
                    "not_useful": 0.99,
                    "useful": 0.005,
                    "unknown": 0.005,
                }
    return machine.accept_decision(step.request_id, step.model, replies)


def test_question_without_gold_requirements_or_seeds_drives_two_hops():
    machine = BuildJevTransitions(
        "How does Aster relate to Harbor's government?",
        SCOPE,
        actions("Aster leads an assembly", "Assembly's civic role"),
    )
    first = machine.step
    assert isinstance(first, DecisionIntent) and first.phase == "assess"
    assert first.state["evidence"] == []
    assert "requirements" not in first.state and "initial_actions" not in first.state
    assert answer(machine, next_id="a0").actions[0].id == "a0"
    machine.accept_acquisition({"a0": (unit("u0", "Aster leads the assembly."),)})
    assert answer(machine, next_id="a1").actions[0].id == "a1"
    machine.accept_acquisition({"a1": (unit("u1", "The assembly governs Harbor."),)})
    end = answer(machine, label="sufficient", support="u0")
    assert isinstance(end, Disposition) and end.status == "provisionally_supported"
    assert end.acquired_action_ids == ("a0", "a1") and len(end.evidence) == 2
    assert end.reason == "catalog_exhausted"


def test_plural_coverage_reads_additional_fact_before_accepting_tentative_answer():
    machine = BuildJevTransitions(
        "What uses do float goats have?", SCOPE, actions("Milk", "Flotation", "Hauling")
    )
    answer(machine, next_id="a0")
    machine.accept_acquisition({"a0": (unit("u0", "Goats supply milk."),)})
    coverage = answer(machine, label="sufficient", support="u0")
    assert coverage.phase == "coverage"
    intent = answer(machine, uses={"use_0": "useful", "use_1": "unknown"})
    assert [a.id for a in intent.actions] == ["a1", "a2"]
    machine.accept_acquisition(
        {"a1": (unit("u1", "Goats float."),), "a2": (unit("u2", "Goats pull wagons."),)}
    )
    end = answer(machine, label="sufficient", support="u0")
    assert len(end.evidence) == 3 and end.excluded_unread_ids == ()


def test_competing_claim_cannot_be_skipped_after_tentative_sufficiency():
    machine = BuildJevTransitions(
        "Who leads the council now?",
        SCOPE,
        actions("Aster leads", "Later disputed succession"),
    )
    answer(machine, next_id="a0")
    original = unit(
        "u0",
        "Aster believes she leads.",
        epistemic_kind="belief",
        temporal_scope={"as_of": "earlier"},
    )
    machine.accept_acquisition({"a0": (original,)})
    answer(machine, label="sufficient", support="u0")
    answer(machine, uses={"use_0": "useful"})
    machine.accept_acquisition(
        {"a1": (unit("u1", "Bryn contests Aster's present authority."),)}
    )
    end = answer(machine, label="conflict", support="u1")
    assert end.status == "unresolved_conflict"
    assert end.evidence[0].epistemic_kind == "belief" and end.evidence[
        0
    ].temporal_scope == {"as_of": "earlier"}


@pytest.mark.parametrize(
    "label", ["more_evidence", "uncertain", "conflict", "sufficient"]
)
def test_empty_catalog_or_unsupported_sufficiency_is_honest(label):
    machine = BuildJevTransitions("Where is the lost gate?", SCOPE, ())
    end = answer(machine, label=label)
    assert end.status == "insufficient_evidence"
    assert not end.evidence


def test_high_confidence_irrelevance_is_explicitly_heuristic_and_qualifications_survive():
    machine = BuildJevTransitions(
        "What does Aster believe?", SCOPE, actions("Aster's belief", "Unrelated food")
    )
    answer(machine, next_id="a0")
    machine.accept_acquisition(
        {
            "a0": (
                unit(
                    "u0", "Aster believes the gate is haunted.", epistemic_kind="belief"
                ),
            )
        }
    )
    coverage = answer(machine, label="sufficient", support="u0")
    assert "uncalibrated" in coverage.state["rules"]
    end = answer(machine, uses={"use_0": "not_useful"})
    assert end.status == "provisionally_supported" and end.excluded_unread_ids == (
        "a1",
    )
    assert end.reason == "heuristic_unread_exclusions"
    assert end.evidence[0].epistemic_kind == "belief"


def test_low_confidence_or_missing_distribution_is_read_conservatively():
    for distribution in (None, {"not_useful": 0.6, "useful": 0.2, "unknown": 0.2}):
        machine = BuildJevTransitions("What is the gate?", SCOPE, actions("Ambiguous"))
        answer(machine)
        step = machine.step
        reply = {"kind": "choice", "selected": "not_useful"}
        if distribution is not None:
            reply["probabilities"] = distribution
        intent = machine.accept_decision(step.request_id, step.model, {"use_0": reply})
        assert isinstance(intent, AcquisitionIntent)


@pytest.mark.parametrize(
    "fault",
    ["partial", "foreign", "body", "duplicate", "wrong-unit", "empty-provenance"],
)
def test_invalid_acquisition_is_atomic_and_never_retried(fault):
    machine = BuildJevTransitions("What are the uses?", SCOPE, actions("A", "B"))
    answer(machine)  # No speculative seed; coverage acquires ambiguous legal actions.
    answer(machine)
    first, second = unit("u0", "A."), unit("u1", "B.")
    delivery = {"a0": (first,), "a1": (second,)}
    if fault == "partial":
        delivery.pop("a1")
    elif fault == "foreign":
        delivery["a1"] = (
            second.model_copy(
                update={"scope": SCOPE.model_copy(update={"world_id": "foreign"})}
            ),
        )
    elif fault == "body":
        delivery["a1"] = (second.model_copy(update={"text": "tampered"}),)
    elif fault == "duplicate":
        delivery["a1"] = (second, second)
    elif fault == "wrong-unit":
        delivery["a1"] = (first,)
    else:
        delivery["a1"] = (second.model_copy(update={"provenance": ({},)}),)
    with pytest.raises(ValueError):
        machine.accept_acquisition(delivery)
    assert machine.step.status == "refused" and not machine.step.evidence
    with pytest.raises(ValueError, match="no pending"):
        machine.accept_acquisition(delivery)


@pytest.mark.parametrize(
    "fault", ["request", "model", "keys", "choice", "kind", "extra", "probability"]
)
def test_reply_is_bound_to_exact_pending_schema_and_unknown_refuses(fault):
    machine = BuildJevTransitions("What?", SCOPE, actions("A"))
    step = machine.step
    response = {
        "sufficiency": {"kind": "choice", "selected": "more_evidence"},
        "next": {"kind": "choice", "selected": "a0"},
    }
    rid, model = step.request_id, step.model
    if fault == "request":
        rid = "old-request"
    elif fault == "model":
        model = "other-model"
    elif fault == "keys":
        response.pop("next")
    elif fault == "choice":
        response["next"]["selected"] = "invented"
    elif fault == "kind":
        response["next"]["kind"] = "binary"
    elif fault == "extra":
        response["next"]["hidden"] = "ignore me"
    else:
        response["next"]["probabilities"] = {"none": float("nan"), "a0": 1}
    with pytest.raises(ValueError):
        machine.accept_decision(rid, model, response)
    assert machine.step.status == "refused"
    with pytest.raises(ValueError, match="no pending"):
        machine.accept_decision(step.request_id, step.model, response)


def test_mutable_views_and_inputs_do_not_retarget_or_rewrite_internal_evidence():
    machine = BuildJevTransitions("Question", SCOPE, actions("A"))
    step = machine.step
    step.state["scope"]["world_id"] = "foreign"
    assert machine.step.state["scope"]["world_id"] == "world:test"
    answer(machine, next_id="a0")
    acquired = unit("u0", "A.", temporal_scope={"as_of": "then"})
    machine.accept_acquisition({"a0": (acquired,)})
    acquired.provenance[0]["source_read_id"] = "forged"
    acquired.temporal_scope["as_of"] = "forged"
    end = answer(machine, label="sufficient", support="u0")
    assert end.evidence[0].provenance[0]["source_read_id"] == "read:u0"
    end.evidence[0].temporal_scope["as_of"] = "forged"
    assert machine.step.evidence[0].temporal_scope["as_of"] == "then"


def test_finite_exhaustion_never_reoffers_an_action_or_reissues_a_decision():
    machine = BuildJevTransitions("Missing fact", SCOPE, actions("A", "B"))
    seen = set()
    for aid, uid in (("a0", "u0"), ("a1", "u1")):
        request = machine.step
        assert request.request_id not in seen
        seen.add(request.request_id)
        assert [a.id for a in answer(machine, next_id=aid).actions] == [aid]
        machine.accept_acquisition({aid: (unit(uid, "Unrelated fact."),)})
    assert machine.step.state["legal_next_actions"] == {}
    end = answer(machine)
    assert end.status == "insufficient_evidence" and end.acquired_action_ids == (
        "a0",
        "a1",
    )
    with pytest.raises(ValueError):
        machine.accept_decision("old", "jev-1.14.0", {})


def test_cancel_or_uncertain_attempt_stops_without_fallback():
    machine = BuildJevTransitions("What?", SCOPE, actions("A"))
    assert machine.refuse().reason == "uncertain_attempt_do_not_replay"
    with pytest.raises(ValueError):
        machine.refuse()


@pytest.mark.parametrize(
    "legal",
    [
        (
            ReadAction(
                id="none", label="bad", kind="graph_observations", unit_ids=("u",)
            ),
        ),
        (
            ReadAction(
                id="a", label="bad", kind="graph_observations", unit_ids=("none",)
            ),
        ),
        actions("A") + actions("A"),
        (
            ReadAction(
                id="a", label="bad", kind="graph_observations", unit_ids=("u", "u")
            ),
        ),
    ],
)
def test_catalog_refuses_ambiguous_or_reserved_identity(legal):
    with pytest.raises(ValueError):
        BuildJevTransitions("Question", SCOPE, legal)


def test_irrelevant_support_does_not_make_sufficiency_successful():
    machine = BuildJevTransitions("Who governs?", SCOPE, actions("Food"))
    answer(machine, next_id="a0")
    machine.accept_acquisition({"a0": (unit("u0", "Goats eat grass."),)})
    end = answer(
        machine, label="sufficient", support="u0", relevance={"relevant_0": 0.01}
    )
    assert end.status == "insufficient_evidence"


def test_overlap_covered_by_other_reads_is_not_reported_as_unread_exclusion():
    catalog = (
        *actions("A", "B"),
        ReadAction(
            id="overlap",
            label="Same pair",
            kind="graph_observations",
            unit_ids=("u0", "u1"),
        ),
    )
    machine = BuildJevTransitions("What are the facts?", SCOPE, catalog)
    answer(machine)
    answer(machine, uses={"use_0": "useful", "use_1": "useful", "use_2": "not_useful"})
    machine.accept_acquisition({"a0": (unit("u0", "A."),), "a1": (unit("u1", "B."),)})
    end = answer(machine, label="sufficient", support="u0")
    assert end.status == "provisionally_supported" and not end.excluded_unread_ids
    assert end.reason == "catalog_exhausted"


def test_saved_authored_scene_cannot_arrive_as_admitted_graph_evidence():
    machine = BuildJevTransitions("Question", SCOPE, actions("A"))
    answer(machine, next_id="a0")
    forged = unit("u0", "An authored scene.").model_copy(
        update={"source_class": "authored_scene_not_played_event"}
    )
    with pytest.raises(ValueError, match="source class"):
        machine.accept_acquisition({"a0": (forged,)})
    assert machine.step.status == "refused"
