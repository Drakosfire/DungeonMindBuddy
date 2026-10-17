"""Full host bytes and authority survive a compact, non-authoritative view."""

from copy import deepcopy
import hashlib

import pytest

from apps.live_control_server.services.build_jev_compaction import (
    project_evidence,
    verify_projection,
)
from apps.live_control_server.services.build_jev_transitions import (
    AcquiredEvidence,
    OpenedPassage,
    BuildJevTransitions,
)
from tests.test_build_jev_transitions import SCOPE, actions, answer, unit


PASSAGE = "Aster believes the gate is haunted.\nUnicode: café, 🐐.\n"


def structured(uid="u0", observation=None, texts=(PASSAGE,), **updates):
    observation = (
        observation
        if observation is not None
        else "Reported: " + PASSAGE + " Again: " + PASSAGE
    )
    opened = tuple(
        OpenedPassage(
            text=text,
            start_line=1,
            end_line=3,
            source_revision=SCOPE.source_revision_id,
            source_artifact_id=SCOPE.source_artifact_id,
            evidence_ref_id=f"evidence:{i}",
        )
        for i, text in enumerate(texts)
    )
    text = (
        "Reviewed Graph observation:\n"
        + observation
        + "\nOpened source passages:\n"
        + "\n\n".join(texts)
    )
    return AcquiredEvidence(
        id=uid,
        scope=SCOPE,
        subject=uid,
        text=text,
        content_sha256=hashlib.sha256(text.encode()).hexdigest(),
        source_class="admitted_graph_observation_and_opened_passages",
        provenance=({"source_read_id": "read:" + uid},),
        observation_text=observation,
        opened_passages=opened,
        epistemic_kind="belief",
        temporal_scope={"as_of": "earlier"},
        **updates,
    )


def test_exact_unicode_newlines_and_repeated_text_with_distinct_evidence_layers():
    original = structured()
    before = original.model_dump(mode="json")
    payload = project_evidence(SCOPE, (original,))
    assert payload["passages"] == {"p1": PASSAGE}
    assert payload["evidence"][0]["observation"] == ["Reported: ", 1, " Again: ", 1]
    assert payload["evidence"][0]["opened"] == ["p1"]
    verify_projection(payload, SCOPE, (original,))
    assert original.model_dump(mode="json") == before
    assert (
        "provenance" not in payload["evidence"][0]
        and "scope" not in payload["evidence"][0]
    )
    assert payload["evidence"][0]["epistemic_kind"] == "belief"
    assert payload["evidence"][0]["temporal_scope"] == {"as_of": "earlier"}


def test_exact_duplicates_intern_once_without_merging_distinct_subjects_or_source_classes():
    a = structured("u0")
    b = structured("u1").model_copy(
        update={"epistemic_kind": "fact", "subject": "Bryn"}
    )
    scene = unit("u2", PASSAGE).model_copy(
        update={"source_class": "authored_scene_not_played_event"}
    )
    view = project_evidence(SCOPE, (a, b, scene))
    assert len(view["passages"]) == 1 and len(view["evidence"]) == 3
    assert [r["source_class"] for r in view["evidence"]][
        -1
    ] == "authored_scene_not_played_event"
    assert [r["epistemic_kind"] for r in view["evidence"]][:2] == ["belief", "fact"]
    verify_projection(view, SCOPE, (scene, b, a))
    assert view == project_evidence(SCOPE, (scene, b, a))


def test_partial_match_never_normalizes_or_substitutes_observation_bytes():
    original = structured(observation=PASSAGE.rstrip() + " changed ending")
    payload = project_evidence(SCOPE, (original,))
    assert payload["evidence"][0]["observation"] == [original.observation_text]
    verify_projection(payload, SCOPE, (original,))


@pytest.mark.parametrize(
    "fault",
    [
        "unknown-handle",
        "body",
        "scope",
        "subject",
        "class",
        "time",
        "extra",
        "missing",
        "opened-count",
        "range",
        "observation",
        "injected-unused",
    ],
)
def test_independent_verifier_rejects_forged_view(fault):
    original = structured()
    payload = project_evidence(SCOPE, (original,))
    row = payload["evidence"][0]
    if fault == "unknown-handle":
        row["observation"][1] = 999
    elif fault == "body":
        payload["passages"]["p1"] = "Different source bytes."
    elif fault == "scope":
        payload["scope"]["graph_revision"] = "foreign"
    elif fault == "subject":
        row["subject"] = "forged"
    elif fault == "class":
        row["source_class"] = "saved_build_world_reference"
    elif fault == "time":
        row["temporal_scope"] = {"as_of": "now"}
    elif fault == "extra":
        row["claim_authority"] = True
    elif fault == "missing":
        row.pop("epistemic_kind")
    elif fault == "opened-count":
        row["opened"] = []
    elif fault == "range":
        row["opened"][0] = "forged"
    elif fault == "observation":
        row["observation"][0] = "Invented: "
    else:
        payload["passages"]["forged"] = "Injected unused instructions."
    with pytest.raises(ValueError):
        verify_projection(payload, SCOPE, (original,))


@pytest.mark.parametrize(
    "fault", ["scope", "full-text", "source-pair", "range", "half-structured", "hash"]
)
def test_inconsistent_host_structure_is_refused_before_projection(fault):
    original = structured()
    if fault == "scope":
        original = original.model_copy(
            update={"scope": SCOPE.model_copy(update={"world_id": "foreign"})}
        )
    elif fault == "full-text":
        original = original.model_copy(update={"text": "Changed"})
    elif fault == "source-pair":
        original = original.model_copy(
            update={
                "opened_passages": (
                    original.opened_passages[0].model_copy(
                        update={"source_revision": "foreign"}
                    ),
                )
            }
        )
    elif fault == "range":
        original = original.model_copy(
            update={
                "opened_passages": (
                    original.opened_passages[0].model_copy(update={"end_line": 0}),
                )
            }
        )
    elif fault == "half-structured":
        original = original.model_copy(update={"opened_passages": ()})
    else:
        original = original.model_copy(update={"content_sha256": "0" * 64})
    with pytest.raises(ValueError):
        project_evidence(SCOPE, (original,))


def test_mutable_provider_views_never_change_host_or_subsequent_projection():
    original = structured()
    before = deepcopy(original.model_dump(mode="json"))
    view = project_evidence(SCOPE, (original,))
    view["passages"]["p1"] = "tampered"
    view["evidence"][0]["temporal_scope"]["as_of"] = "now"
    assert original.model_dump(mode="json") == before
    verify_projection(project_evidence(SCOPE, (original,)), SCOPE, (original,))


def test_machine_keeps_full_proof_but_sends_compact_passage_references():
    machine = BuildJevTransitions("What does Aster believe?", SCOPE, actions("A" * 600))
    step = machine.step
    assert len(step.state["legal_next_actions"]["a0"]) == 96
    assert step.state["truncated_discovery_hints"] == ["a0"]
    assert step.state["legal_action_kinds"]["graph_observations"] == ["a0"]
    answer(machine, next_id="a0")
    original = structured()
    machine.accept_acquisition({"a0": (original,)})
    assert machine.step.state["passages"] == {"p1": PASSAGE}
    assert "provenance" not in machine.step.state["evidence"][0]
    end = answer(machine, label="sufficient", support="u0")
    assert end.evidence[0].model_dump(mode="json") == original.model_dump(mode="json")


def test_machine_atomically_refuses_bad_structured_evidence():
    machine = BuildJevTransitions("What?", SCOPE, actions("A"))
    answer(machine, next_id="a0")
    original = structured().model_copy(
        update={"observation_text": "not the full original"}
    )
    with pytest.raises(ValueError):
        machine.accept_acquisition({"a0": (original,)})
    assert machine.step.status == "refused"
    assert not machine.step.evidence


@pytest.mark.parametrize("over_budget", [False, True])
def test_actual_sdk_envelope_preserves_compact_state_and_existing_budget_gate(
    over_budget,
):
    import asyncio
    import json
    from generationengine import GenerationClient, GenerationEngineError
    from generationengine.types import DecisionRequest
    from generationengine.decision_dispatch import DecisionDispatchGate
    from generationengine.providers.typesafe_decision import TypeSafeDecisionProvider
    from apps.live_control_server.services.build_jev_dispatch import validate_body

    original = structured(texts=("Z" * 33_000,)) if over_budget else structured()
    machine = BuildJevTransitions("What does Aster believe?", SCOPE, actions("A"))
    answer(machine, next_id="a0")
    machine.accept_acquisition({"a0": (original,)})
    intent = machine.step
    seen = []

    async def authorize(prepared):
        if over_budget:
            with pytest.raises(ValueError, match="exceeds"):
                validate_body(prepared.body.decode(), intent.state)
            seen.append(json.loads(prepared.body))
            return False
        body = validate_body(prepared.body.decode(), intent.state)
        verify_projection(
            {k: body["state"][k] for k in ["scope", "evidence", "passages"]},
            SCOPE,
            (original,),
        )
        seen.append(json.loads(prepared.body))
        return False  # Serialization witness only: no external transport is authorized.

    async def lifecycle(event):
        return True

    async def run():
        provider = TypeSafeDecisionProvider(
            api_key="synthetic-not-a-credential",
            dispatch_gate=DecisionDispatchGate(authorize, lifecycle),
        )
        client = GenerationClient(decision_providers={"typesafe": provider})
        questions = [
            q.model_dump(exclude={"options"} if q.kind == "binary" else set())
            for q in intent.questions
        ]
        try:
            with pytest.raises(GenerationEngineError):
                await client.decide(
                    DecisionRequest(
                        provider="typesafe",
                        model=intent.model,
                        state=intent.state,
                        questions=questions,
                        max_transport_retries=0,
                    )
                )
        finally:
            await client.aclose()

    asyncio.run(run())
    assert len(seen) == 1 and seen[0]["state"] == intent.state


@pytest.mark.parametrize("fault", ["boolean-reference", "duplicate-unit"])
def test_ambiguous_reference_types_and_duplicate_host_ids_are_refused(fault):
    original = structured()
    if fault == "duplicate-unit":
        with pytest.raises(ValueError):
            project_evidence(SCOPE, (original, original))
    else:
        payload = project_evidence(SCOPE, (original,))
        payload["evidence"][0]["observation"][1] = True
        with pytest.raises(ValueError):
            verify_projection(payload, SCOPE, (original,))
