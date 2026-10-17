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


def contained_case():
    from apps.live_control_server.services.build_jev_compaction import CONTAINED_CODEC

    snippets = tuple(
        f"Paragraph {i}: " + (f"🐐 café {i} distinct detail. " * 12) for i in range(4)
    )
    graph = structured(texts=snippets)
    saved_text = (
        "🧙 prefix\n" + "\nheading\n".join(snippets) + "\nrepeat\n" + snippets[0]
    )
    saved = unit("saved", saved_text).model_copy(
        update={"source_class": "saved_build_world_reference"}
    )
    units = (graph, saved)
    return units, project_evidence(SCOPE, units, codec=CONTAINED_CODEC)


def test_contained_codec_exact_unicode_roundtrip_preserves_distinct_authority():
    from apps.live_control_server.services.build_jev_compaction import (
        CONTAINED_CODEC,
        expand_contained_passages,
        _cost,
        CONTAINED_RULE,
    )

    units, compact = contained_case()
    literal = project_evidence(SCOPE, units)
    assert CONTAINED_CODEC in compact
    assert expand_contained_passages(compact) == literal
    assert _cost(compact) + _cost({"grammar": CONTAINED_RULE}) < _cost(literal)
    assert compact["evidence"] == literal["evidence"]
    assert len(compact["passages"]) == 1
    container, rows = next(iter(compact[CONTAINED_CODEC].items()))
    for index in range(0, len(rows), 3):
        handle, start, end = rows[index : index + 3]
        assert compact["passages"][container][start:end] == literal["passages"][handle]
        assert start == compact["passages"][container].find(literal["passages"][handle])
    assert compact == project_evidence(
        SCOPE, tuple(reversed(units)), codec=CONTAINED_CODEC
    )
    assert units[0].provenance != units[1].provenance
    assert {u.source_class for u in units} == {
        "admitted_graph_observation_and_opened_passages",
        "saved_build_world_reference",
    }
    verify_projection(compact, SCOPE, units, codec=CONTAINED_CODEC)
    with pytest.raises(ValueError):
        verify_projection(compact, SCOPE, units)  # no implicit historical codec upgrade


@pytest.mark.parametrize(
    "fault",
    [
        "missing_container",
        "chain",
        "cycle",
        "duplicate",
        "unknown_alias",
        "bool_start",
        "float_end",
        "negative",
        "too_long",
        "empty",
        "reversed",
        "bad_triple",
        "empty_group",
        "changed_container",
        "wrong_offset",
        "extra_field",
        "qualification",
        "qualification_type",
    ],
)
def test_contained_corruption_cannot_reconstruct_parent(fault):
    from apps.live_control_server.services.build_jev_compaction import CONTAINED_CODEC

    units, compact = contained_case()
    bad = deepcopy(compact)
    groups = bad[CONTAINED_CODEC]
    container = next(iter(groups))
    rows = groups[container]
    alias = rows[0]
    if fault == "missing_container":
        bad["passages"].pop(container)
    elif fault == "chain":
        groups[alias] = groups.pop(container)
    elif fault == "cycle":
        groups[alias] = [container, 0, 1]
    elif fault == "duplicate":
        rows.extend(rows[:3])
    elif fault == "unknown_alias":
        rows.extend(["foreign", 0, 1])
    elif fault == "bool_start":
        rows[1] = True
    elif fault == "float_end":
        rows[2] = float(rows[2])
    elif fault == "negative":
        rows[1] = -1
    elif fault == "too_long":
        rows[2] = len(bad["passages"][container]) + 1
    elif fault == "empty":
        rows[2] = rows[1]
    elif fault == "reversed":
        rows[1], rows[2] = rows[2], rows[1]
    elif fault == "bad_triple":
        rows.pop()
    elif fault == "empty_group":
        groups[container] = []
    elif fault == "changed_container":
        bad["passages"][container] = "changed" + bad["passages"][container]
    elif fault == "wrong_offset":
        rows[1] += 1  # UTF-16/UTF-8 offsets must not replace Unicode code points.
    elif fault == "extra_field":
        bad["hidden"] = "injected"
    elif fault == "qualification":
        bad["evidence"][0]["epistemic_kind"] = "fact"
    else:
        bad["evidence"][0]["temporal_scope"] = {"as_of": False}
    with pytest.raises(ValueError):
        verify_projection(bad, SCOPE, units, codec=CONTAINED_CODEC)


def test_contained_type_sensitive_qualification_and_no_overlap_fallback():
    from apps.live_control_server.services.build_jev_compaction import CONTAINED_CODEC

    units, compact = contained_case()
    graph = units[0].model_copy(update={"temporal_scope": {"flag": False}})
    # Find the graph row independently of serialization order.
    compact = project_evidence(SCOPE, (graph, units[1]), codec=CONTAINED_CODEC)
    next(row for row in compact["evidence"] if row["id"] == graph.id)["temporal_scope"][
        "flag"
    ] = 0
    with pytest.raises(ValueError, match="exact parent"):
        verify_projection(compact, SCOPE, (graph, units[1]), codec=CONTAINED_CODEC)
    small = (unit("a", "tiny"), unit("b", "tiny overlap"))
    assert project_evidence(SCOPE, small, codec=CONTAINED_CODEC) == project_evidence(
        SCOPE, small
    )
    disjoint = (unit("a", "AAA"), unit("b", "BBB"))
    assert project_evidence(SCOPE, disjoint, codec=CONTAINED_CODEC) == project_evidence(
        SCOPE, disjoint
    )


def test_contained_overlapping_sources_and_deterministic_equal_containers():
    from apps.live_control_server.services.build_jev_compaction import (
        encode_contained_passages,
        expand_contained_passages,
        CONTAINED_CODEC,
    )

    fragment = "🐐 overlapping text " * 40
    shared = "prefix " + fragment + " suffix"
    payload = {
        "scope": {},
        "evidence": [],
        "passages": {"p1": shared, "p2": shared, "p3": fragment, "p4": fragment[5:]},
    }
    encoded = encode_contained_passages(payload)
    assert expand_contained_passages(encoded) == payload
    assert set(encoded["passages"]) == {"p1"}
    assert set(encoded[CONTAINED_CODEC]) == {"p1"}


def test_contained_codec_never_hides_irreducible_context_or_changes_default():
    import json
    from apps.live_control_server.services.build_jev_compaction import CONTAINED_CODEC
    from apps.live_control_server.services import build_jev_dispatch as policy

    units = (unit("a", "a" * 18000), unit("b", "b" * 18000))
    literal = project_evidence(SCOPE, units)
    compact = project_evidence(SCOPE, units, codec=CONTAINED_CODEC)
    assert compact == literal and CONTAINED_CODEC not in compact
    body = json.dumps(
        {
            "model": policy.MODEL,
            "state": compact,
            "questions": {
                "sufficiency": {
                    "type": "choice",
                    "instructions": "Enough support?",
                    "criteria": {"yes": None, "no": None},
                }
            },
        }
    )
    with pytest.raises(ValueError, match="conservative ceiling"):
        policy.validate_body(body, compact)
    with pytest.raises(ValueError, match="unsupported evidence codec"):
        project_evidence(SCOPE, units, codec="unknown")
