"""Play adopts actual Core human source reads without borrowing model grants."""

import json
from types import SimpleNamespace
from uuid import uuid4

import pytest

from application_state.agent_conversation import types as t
from application_state.agent_conversation.play_authored_sources import (
    PlayAuthoredSourceContextV1,
    capture_input,
    observe_source,
    model_frame,
)
from application_state.agent_conversation.play_graph_authority import (
    play_source_frame,
    play_graph_execution_policy_digest,
)
from application_state.agent_conversation.play_graph_context import (
    validate_play_graph_execution_binding,
    validate_play_graph_intent_receipt,
)
from apps.live_control_server.integrations.dungeonmind.native_corpus_source import (
    read_authored_source,
)
from tests.test_native_authored_source_references import selected, BODY
from tests.test_native_corpus_source_access import lane as native_source_lane  # noqa: F401
from tests.test_surface_native_writer import published_lane as published_lane  # noqa: F401
from tests.test_play_graph_context import fixture, seal_receipt
from tests.test_play_graph_authority import intent_wire


@pytest.fixture
def source_case(request):
    return request.getfixturevalue("native_source_lane")


def play_case(lane, kind="section"):
    core, ref, sections = selected(lane, kind=kind)
    ctx = PlayAuthoredSourceContextV1(
        authority=core.authority, references=t.AuthoredReferencesV2(references=(ref,))
    )
    receipt, execution, frame = fixture()
    a = core.authority
    sources = tuple(
        source.model_copy(
            update={
                "locator": source.locator.model_copy(
                    update={"world_id": a.managed_world_id}
                )
            }
        )
        for source in frame.sources
    )
    frame = play_source_frame(sources)
    wire = receipt.model_dump(mode="json", by_alias=True)
    wire["play_basis"]["world_id"] = a.managed_world_id
    wire["play_sources"] = frame.manifest.model_dump(mode="json", by_alias=True)
    wire["play_source_frame_sha256"] = t.canonical_sha256(frame)
    wire["graph_authority"].update(
        managed_world_id=a.managed_world_id,
        native_world_id=a.native_world_id,
        binding_version=a.binding_version,
        graph_revision=a.revision_id,
    )
    wire["authored_source_context"] = ctx.model_dump(mode="json", by_alias=True)
    receipt = seal_receipt(wire)
    policy = execution.policy.model_dump(mode="json", by_alias=True)
    policy["source_read_scope"].update(
        world_id=a.managed_world_id, graph_revision=a.revision_id
    )
    policy["authored_source_context"] = ctx.model_dump(mode="json", by_alias=True)
    policy = type(execution.policy).model_validate(policy)
    execution = t.PlayWorldGraphExecutionV1(
        context_receipt_sha256=receipt.context_receipt_sha256,
        execution_policy_sha256=play_graph_execution_policy_digest(
            receipt.context_receipt_sha256, policy
        ),
        policy=policy,
        events=[],
    )
    turn = SimpleNamespace(
        graph_context_receipt=receipt,
        graph_context_execution=execution,
        turn_id=uuid4(),
        conversation_id=uuid4(),
        attempt=1,
        submitted_intent_fingerprint_v2="a" * 64,
        idempotency_key=uuid4(),
        user_text="What does the selected episode describe?",
        source_frame=frame,
    )
    return turn, core, ref, sections


def append(turn, event):
    execution = turn.graph_context_execution
    turn.graph_context_execution = type(execution).model_validate_json(
        json.dumps(
            execution.model_dump(mode="json", by_alias=True)
            | {
                "events": [
                    e.model_dump(mode="json", by_alias=True)
                    for e in [*execution.events, event]
                ]
            }
        )
    )
    validate_play_graph_execution_binding(
        turn.graph_context_receipt, turn.graph_context_execution
    )


@pytest.mark.parametrize("kind", ["section", "full_document"])
def test_play_captures_and_reads_exact_core_source_before_any_provider(
    source_case, kind
):
    turn, core, ref, sections = play_case(source_case, kind)
    append(turn, capture_input(turn, event_id=uuid4()))
    calls = []

    def opening(actual):
        calls.append(actual)
        return read_authored_source(core, actual)

    event = observe_source(
        turn, event_id=uuid4(), reference_index=0, materialize=opening
    )
    append(turn, event)
    assert calls == [ref]
    assert not any(
        isinstance(e, t.ProviderAttemptAuthorizedEventV1)
        for e in turn.graph_context_execution.events
    )
    expected = (
        BODY
        if kind == "full_document"
        else BODY[sections[1].char_start : sections[1].char_end]
    )
    (row,) = model_frame(turn.graph_context_execution)["excerpts"]
    assert row["text"] == expected and row["excerpt_handle"] == "r0"
    assert row["extent_kind"] == (
        "full_document" if kind == "full_document" else "section"
    )
    assert (
        turn.graph_context_receipt.play_sources.entries
    )  # Original Run frame retained.


def test_play_source_capture_requires_exact_original_intent(source_case):
    turn, _, ref, _ = play_case(source_case)
    wire = intent_wire()
    wire["world_id"] = wire["graph_request"]["world_id"] = ref.managed_world_id
    wire["authored_references"] = t.AuthoredReferencesV2(references=(ref,)).model_dump(
        mode="json", by_alias=True
    )
    intent = t.PlayGraphIntentV1.model_validate(wire)
    validate_play_graph_intent_receipt(intent, turn.graph_context_receipt)
    with pytest.raises(ValueError, match="references differ"):
        validate_play_graph_intent_receipt(
            intent.model_copy(update={"authored_references": None}),
            turn.graph_context_receipt,
        )


@pytest.mark.parametrize("change", ["capture", "index", "world", "extent", "repeat"])
def test_play_source_events_cannot_change_or_repeat_the_human_selection(
    source_case, change
):
    turn, core, _, _ = play_case(source_case)
    append(turn, capture_input(turn, event_id=uuid4()))
    event = observe_source(
        turn,
        event_id=uuid4(),
        reference_index=0,
        materialize=lambda ref: read_authored_source(core, ref),
    )
    if change == "capture":
        event = event.model_copy(update={"capture_event_id": uuid4()})
    if change == "index":
        event = event.model_copy(update={"reference_index": 1})
    if change == "world":
        event = event.model_copy(
            update={
                "catalog": event.catalog.model_copy(
                    update={
                        "authority": event.catalog.authority.model_copy(
                            update={"managed_world_id": "foreign"}
                        )
                    }
                )
            }
        )
    if change == "extent":
        event = event.model_copy(
            update={
                "excerpt": event.excerpt.model_copy(
                    update={"section": event.catalog.sections[0]}
                )
            }
        )
    if change == "repeat":
        append(turn, event)
        event = event.model_copy(update={"event_id": uuid4(), "sequence": 2})
    with pytest.raises(ValueError):
        append(turn, event)


def test_unreferenced_play_cannot_admit_a_human_read_event(source_case):
    turn, _, _, _ = play_case(source_case)
    event = capture_input(turn, event_id=uuid4())
    _, execution, _ = fixture()
    with pytest.raises(ValueError, match="frozen source capability"):
        type(execution).model_validate(
            execution.model_dump(mode="python", by_alias=True) | {"events": [event]}
        )


def prepared_reference_request(lane, mutate=None):
    from hashlib import sha256
    from application_state.agent_conversation.play_session_input import pack
    from application_state.agent_conversation.play_graph_input import NativePlayInputV6
    from application_state.agent_conversation.surface_evidence_answer import (
        BODY_POLICY,
        BODY_INSTRUCTIONS,
    )
    from tests.test_play_graph_authority import native_provider

    turn, core, _, _ = play_case(lane)
    append(turn, capture_input(turn, event_id=uuid4()))
    append(
        turn,
        observe_source(
            turn,
            event_id=uuid4(),
            reference_index=0,
            materialize=lambda ref: read_authored_source(core, ref),
        ),
    )
    frame, sessions = pack(turn.source_frame, str(turn.idempotency_key), [])
    carrier = NativePlayInputV6(
        submission_id=turn.idempotency_key,
        message=turn.user_text,
        source_frame=frame,
        session_evidence=sessions,
        native_body_evidence=model_frame(turn.graph_context_execution),
        answer_policy=BODY_POLICY,
        answer_instructions=BODY_INSTRUCTIONS,
    )
    body = {
        "model": "synthetic",
        "messages": [
            {"role": "user", "content": carrier.model_dump_json(by_alias=True)}
        ],
    }
    if mutate:
        mutate(body)
    raw = json.dumps(body, ensure_ascii=False, separators=(",", ":"))
    auth = native_provider(3).model_copy(
        update={
            "envelope_sha256": sha256(raw.encode()).hexdigest(),
            "api_mode": "chat_completions",
        }
    )
    return turn, auth, raw


def test_play_reference_inclusion_binds_exact_actual_producer_bytes(source_case):
    from application_state.agent_conversation.play_authored_sources import prove_input
    from application_state.agent_conversation.native_corpus import body_frame

    turn, auth, raw = prepared_reference_request(source_case)
    proof = prove_input(turn, auth, raw, sequence=auth.sequence + 1, event_id=uuid4())
    assert proof.provider_attempt_id == auth.provider_attempt_id
    assert proof.envelope_sha256 == auth.envelope_sha256
    assert proof.read_event_ids == (turn.graph_context_execution.events[1].event_id,)
    assert proof.frame_sha256 == t.canonical_sha256(
        body_frame((turn.graph_context_execution.events[1],))
    )


@pytest.mark.parametrize(
    "change",
    [
        "text",
        "extent",
        "missing",
        "submission",
        "message",
        "model",
        "role",
        "duplicate",
    ],
)
def test_play_reference_input_rejects_resealed_substitution(source_case, change):
    from application_state.agent_conversation.play_authored_sources import prove_input

    def mutate(body):
        message = body["messages"][0]
        carrier = json.loads(message["content"])
        if change == "text":
            carrier["native_body_evidence"]["excerpts"][0]["text"] = (
                "Unadmitted different passage"
            )
        if change == "extent":
            carrier["native_body_evidence"]["excerpts"][0]["extent_kind"] = (
                "full_document"
            )
        if change == "missing":
            carrier["native_body_evidence"] = None
        if change == "submission":
            carrier["submission_id"] = str(uuid4())
        if change == "message":
            carrier["message"] = "A different question"
        if change == "model":
            body["model"] = "different-model"
        if change == "role":
            message["role"] = "assistant"
        message["content"] = json.dumps(carrier)
        if change == "duplicate":
            body["messages"].append(dict(message))

    turn, auth, raw = prepared_reference_request(source_case, mutate)
    with pytest.raises(ValueError):
        prove_input(turn, auth, raw, sequence=auth.sequence + 1, event_id=uuid4())


def accepted_play_source_case(source_case, *, token_ceilings=True, provider_capacity=None):
    """Actual Core read and APP Run acceptance; no model or provider is invoked."""
    from hashlib import sha256
    from application_state.agent_conversation import AgentConversationService
    from application_state.agent_conversation.play_session_input import pack
    from application_state.agent_conversation.play_graph_input import NativePlayInputV6
    from application_state.agent_conversation.surface_evidence_answer import (
        BODY_POLICY,
        BODY_INSTRUCTIONS,
    )
    from apps.live_control_server.integrations.dungeonmind.native_corpus_source import (
        prepare_native_source_context,
    )
    from apps.live_control_server.services.native_play_graph_owner import (
        prepare_authored_sources,
    )
    from tests.application_state.test_native_play_graph_postgres import make_submission
    from tests.test_play_graph_records import provenance
    from tests.test_native_corpus_source_access import GM
    from tests.test_play_graph_authority import native_provider

    service, sub, frame = make_submission()
    _, origin, _ = selected(source_case)
    binding = SimpleNamespace(
        managed_world_id=sub.world_id,
        native_world_id="world:test",
        binding_version=1,
        provisioning_id=source_case.bound.provisioning_id,
    )
    core = prepare_native_source_context(
        managed_world_id=sub.world_id,
        principal=GM,
        repository=source_case.repo,
        resolve_identity=lambda _: binding,
    )
    ref = origin.model_copy(update={"managed_world_id": sub.world_id})
    refs = t.AuthoredReferencesV2(references=(ref,))
    request = SimpleNamespace(
        authored_references=refs,
        surface=SimpleNamespace(surface_id="play"),
        owner_scope=SimpleNamespace(world_id=sub.world_id),
    )
    prepared = prepare_authored_sources(request, GM, prepared=core)
    packed, sessions = pack(frame, str(sub.idempotency_key), [])
    carrier = NativePlayInputV6(
        submission_id=sub.idempotency_key,
        message=sub.user_text,
        source_frame=packed,
        session_evidence=sessions,
        native_body_evidence=prepared.model_frame(),
        answer_policy=BODY_POLICY,
        answer_instructions=BODY_INSTRUCTIONS,
    )
    raw = json.dumps(
        {
            "model": "synthetic",
            "messages": [
                {"role": "user", "content": carrier.model_dump_json(by_alias=True)}
            ],
            "tools": [],
        },
        ensure_ascii=False,
    )
    wire = sub.graph_context_receipt.model_dump(mode="json", by_alias=True)
    wire["graph_authority"].update(
        native_world_id="world:test", graph_revision=core.authority.revision_id
    )
    wire["assembled_input"]["assembled_input_sha256"] = sha256(raw.encode()).hexdigest()
    wire["authored_source_context"] = prepared.context.model_dump(
        mode="json", by_alias=True
    )
    provider_capacity = not token_ceilings if provider_capacity is None else provider_capacity
    if provider_capacity:
        wire['assembled_input'].update(context_window_limit=None,output_token_reserve=0)
    receipt = seal_receipt(wire)
    policy = sub.graph_context_execution.policy.model_dump(mode="json", by_alias=True)
    policy["source_read_scope"]["graph_revision"] = core.authority.revision_id
    policy["authored_source_context"] = wire["authored_source_context"]
    if not token_ceilings:
        policy.update(max_total_provider_input_tokens=None,max_total_provider_output_tokens=None)
    policy = t.NativePlayGraphPolicyV1.model_validate(policy)
    execution = t.PlayWorldGraphExecutionV1(
        context_receipt_sha256=receipt.context_receipt_sha256,
        execution_policy_sha256=play_graph_execution_policy_digest(
            receipt.context_receipt_sha256, policy
        ),
        policy=policy,
        events=[],
    )
    intent = sub.submitted_intent_v2.model_copy(update={"authored_references": refs})
    sub = sub.model_copy(
        update={
            "submitted_intent_v2": intent,
            "graph_context_receipt": receipt,
            "graph_context_execution": execution,
            "provenance": provenance(receipt),
        }
    )
    turn = service.accept_turn(sub)
    turn = service.claim_turn(
        sub.world_id, sub.conversation_id, turn.turn_id, expected_revision=turn.revision
    ).turn
    turn, _ = service.capture_native_authored_references(
        sub.world_id,
        sub.conversation_id,
        turn.turn_id,
        expected_revision=turn.revision,
        expected_attempt=turn.attempt,
        event_id=uuid4(),
    )
    (row,) = prepared.reads
    turn, _ = service.observe_native_authored_source(
        sub.world_id,
        sub.conversation_id,
        turn.turn_id,
        expected_revision=turn.revision,
        expected_attempt=turn.attempt,
        event_id=uuid4(),
        reference_index=0,
        materialize=lambda _: (row.catalog, row.excerpt),
    )
    assert model_frame(turn.graph_context_execution) == prepared.model_frame()
    auth = native_provider(len(turn.graph_context_execution.events) + 1).model_copy(
        update={
            "envelope_sha256": sha256(raw.encode()).hexdigest(),
            "api_mode": "chat_completions",
        }
    )
    if provider_capacity:
        auth=auth.model_copy(update={'output_token_reserve':0})
    assert (
        AgentConversationService().inspect_turn(
            world_id=sub.world_id, turn_id=turn.turn_id
        )
        == turn
    )
    return service, sub, turn, auth, raw


def test_play_reference_reads_and_actual_input_commit_at_the_app_owner(source_case):
    service, sub, turn, auth, raw = accepted_play_source_case(source_case)
    updated, fresh = service.authorize_native_play_provider(
        sub.world_id,
        sub.conversation_id,
        turn.turn_id,
        expected_revision=turn.revision,
        expected_attempt=turn.attempt,
        provider_attempt_event=auth,
        prepared_request_json=raw,
    )
    assert fresh
    assert [e.kind for e in updated.graph_context_execution.events] == [
        "build_authored_references_captured_v1",
        "native_authored_source_read_v1",
        "play_source_provider_inclusion_v1",
        "provider_attempt_authorized_v3",
        "native_body_provider_included_v1",
    ]
    assert service.inspect_turn(world_id=sub.world_id, turn_id=turn.turn_id) == updated
    replay, fresh = service.authorize_native_play_provider(
        sub.world_id,
        sub.conversation_id,
        turn.turn_id,
        expected_revision=updated.revision,
        expected_attempt=updated.attempt,
        provider_attempt_event=auth,
        prepared_request_json=raw,
    )
    assert not fresh and replay == updated


def test_later_play_provider_cannot_reseal_different_selected_source_bytes(source_case):
    from hashlib import sha256
    from application_state.errors import ApplicationStateValidationError
    from tests.test_play_graph_authority import native_provider

    service, sub, turn, auth, raw = accepted_play_source_case(source_case)
    turn, _ = service.authorize_native_play_provider(
        sub.world_id,
        sub.conversation_id,
        turn.turn_id,
        expected_revision=turn.revision,
        expected_attempt=turn.attempt,
        provider_attempt_event=auth,
        prepared_request_json=raw,
    )
    for value in ("sdk_entered", "response_received"):
        turn, _ = service.record_provider_outcome(
            sub.world_id,
            sub.conversation_id,
            turn.turn_id,
            expected_revision=turn.revision,
            expected_attempt=turn.attempt,
            outcome=t.ProviderOutcomeEventV1(
                kind="provider_outcome",
                event_id=uuid4(),
                sequence=len(turn.graph_context_execution.events),
                provider_attempt_id=auth.provider_attempt_id,
                outcome=value,
            ),
        )
    body = json.loads(raw)
    carrier = json.loads(body["messages"][0]["content"])
    carrier["native_body_evidence"]["excerpts"][0]["text"] = (
        "Unadmitted replacement text."
    )
    body["messages"][0]["content"] = json.dumps(carrier)
    changed = json.dumps(body)
    auth = native_provider(len(turn.graph_context_execution.events) + 1).model_copy(
        update={
            "envelope_sha256": sha256(changed.encode()).hexdigest(),
            "api_mode": "chat_completions",
        }
    )
    with pytest.raises(
        ApplicationStateValidationError, match="selected sources changed"
    ):
        service.authorize_native_play_provider(
            sub.world_id,
            sub.conversation_id,
            turn.turn_id,
            expected_revision=turn.revision,
            expected_attempt=turn.attempt,
            provider_attempt_event=auth,
            prepared_request_json=changed,
        )
    assert service.inspect_turn(world_id=sub.world_id, turn_id=turn.turn_id) == turn


@pytest.mark.parametrize(
    "change",
    [
        "receipt_only",
        "policy_only",
        "extra_context_key",
        "world",
        "revision",
        "binding",
        "object",
        "unknown_event",
        "extra_policy_key",
    ],
)
@pytest.mark.parametrize("token_ceilings", [True, False])
def test_play_source_storage_rejects_malformed_or_foreign_context(
    source_case, application_state_dsn, change, token_ceilings
):
    import psycopg
    from psycopg.types.json import Jsonb

    _, _, turn, _, _ = accepted_play_source_case(source_case,token_ceilings=token_ceilings)
    receipt = turn.graph_context_receipt.model_dump(mode="json", by_alias=True)
    execution = turn.graph_context_execution.model_dump(mode="json", by_alias=True)
    ctx = receipt["authored_source_context"]
    if change == "receipt_only":
        del execution["policy"]["authored_source_context"]
    elif change == "policy_only":
        del receipt["authored_source_context"]
    elif change == "extra_context_key":
        ctx["unowned"] = True
    elif change in ("world", "revision", "binding"):
        key, value = {
            "world": ("managed_world_id", "foreign"),
            "revision": ("revision_id", "other-revision"),
            "binding": ("binding_version", 999),
        }[change]
        ctx["authority"][key] = value
    elif change == "object":
        ctx["references"]["references"][0]["schema"] = "dmb_authored_graph_reference_v1"
    elif change == "unknown_event":
        execution["events"].append({"kind": "unowned_read"})
    elif change == "extra_policy_key":
        execution["policy"]["unowned"] = True
    if change not in ("receipt_only", "policy_only"):
        execution["policy"]["authored_source_context"] = ctx
    with psycopg.connect(application_state_dsn) as conn:
        with pytest.raises(psycopg.errors.CheckViolation):
            conn.execute(
                "UPDATE agent.turn SET graph_context_receipt=%s, graph_context_execution=%s WHERE turn_id=%s",
                (Jsonb(receipt), Jsonb(execution), turn.turn_id),
            )


@pytest.mark.parametrize("include_scene", [False, True])
def test_play_selected_source_normalizes_and_persists_inspectable_body_citation(
    source_case, application_state_dsn, include_scene
):
    import psycopg
    from psycopg.types.json import Jsonb
    from application_state.agent_conversation.play_authored_sources import (
        producing_bodies,
    )
    from application_state.agent_conversation.surface_evidence_answer import (
        BODY_POLICY,
        normalize,
        producing_authored,
        authored_block_index,
    )
    from apps.live_control_server.services.agent_turn_service import _BuildClaimEvidence

    service, sub, turn, auth, raw = accepted_play_source_case(source_case)
    turn, _ = service.authorize_native_play_provider(
        sub.world_id,
        sub.conversation_id,
        turn.turn_id,
        expected_revision=turn.revision,
        expected_attempt=turn.attempt,
        provider_attempt_event=auth,
        prepared_request_json=raw,
    )
    support = _BuildClaimEvidence(
        auth.provider_attempt_id,
        auth.envelope_sha256,
        turn.graph_context_receipt.context_receipt_sha256,
        turn.graph_context_receipt.graph_authority.graph_revision,
        (),
        current_policy=BODY_POLICY,
        authored=producing_authored(turn, auth, raw),
        body_excerpts=producing_bodies(turn, auth, raw),
    )
    for outcome in ("sdk_entered", "response_received"):
        turn, _ = service.record_provider_outcome(
            sub.world_id,
            sub.conversation_id,
            turn.turn_id,
            expected_revision=turn.revision,
            expected_attempt=turn.attempt,
            outcome=t.ProviderOutcomeEventV1(
                kind="provider_outcome",
                event_id=uuid4(),
                sequence=len(turn.graph_context_execution.events),
                provider_attempt_id=auth.provider_attempt_id,
                outcome=outcome,
            ),
        )
    candidate = dict(
        schema=BODY_POLICY,
        answer_segments=[
            dict(
                kind="native_body_claim",
                text="The selected source describes the sample.",
                excerpt_handles=["r0"],
            )
        ],
        limitations=[],
        requested_detail_gaps=[],
    )
    if include_scene:
        _, selectors = authored_block_index(support.authored, str(turn.idempotency_key))
        candidate["answer_segments"].append(
            dict(kind="authored_excerpt", selection_id=next(iter(selectors)))
        )
    completion, bindings, answer = normalize(
        candidate, turn, auth.provider_attempt_id, support
    )
    # Exercise the actual raw-output owner too, with the same SDK bytes and
    # producer. Rules remain unused; no alternative answer acceptance path.
    from hashlib import sha256
    from tests.test_rules_build_input import execution as rules_execution, append
    from application_state.agent_conversation.rules_authority_events import (
        RulesProviderAuthorizedV1,
        RulesProviderIncludedV1,
        RulesNativeProviderOutcomeV1,
    )
    from application_state.agent_conversation.native_rules_output import (
        NativeRulesOutputProofV1,
        normalize_unused_native_output,
    )

    rules = rules_execution()
    rules = rules.model_copy(
        update={
            "scope": rules.scope.model_copy(
                update={
                    "world_id": turn.world_id,
                    "conversation_id": turn.conversation_id,
                    "turn_id": turn.turn_id,
                    "product_attempt": turn.attempt,
                }
            )
        }
    )
    common = dict(
        execution_id=rules.scope.execution_id,
        provider_attempt_id=auth.provider_attempt_id,
        request_envelope_sha256=auth.envelope_sha256,
    )
    rules = append(
        rules,
        RulesProviderAuthorizedV1(
            kind="provider_authorized",
            event_id=uuid4(),
            sequence=len(rules.events),
            matched_outputs=(),
            declared_support_refs=(),
            **common,
        ),
    )
    rules = append(
        rules,
        RulesProviderIncludedV1(
            kind="provider_included",
            event_id=uuid4(),
            sequence=len(rules.events),
            matched_outputs=(),
            support_refs=(),
            **common,
        ),
    )
    output = json.dumps(candidate)
    capture = SimpleNamespace(
        authorization_id="host:play-source-test",
        api_request_id="api:play-source-test",
        provider=auth.provider,
        model=auth.model,
        api_mode=auth.api_mode,
        request_sha256=auth.envelope_sha256,
        status="answered",
        finish_reason="stop",
        text=output,
        text_sha256=sha256(output.encode()).hexdigest(),
        text_utf8_bytes=len(output.encode()),
        tool_calls=(),
    )
    rules = append(
        rules,
        RulesNativeProviderOutcomeV1.from_capture(
            capture, event_id=uuid4(), sequence=len(rules.events), **common
        ),
    )
    proof = NativeRulesOutputProofV1.from_capture(
        capture,
        prepared_request_json=raw,
        rules_execution_id=rules.scope.execution_id,
        producing_provider_attempt_id=auth.provider_attempt_id,
    )
    assert normalize_unused_native_output(turn, rules, proof) == (
        completion,
        bindings,
        answer,
    )
    (citation,) = completion.native_body_citations
    assert completion.surface_id == "play"
    assert citation.read_event_id == support.body_excerpts[0].read.event_id
    assert (
        citation.source_artifact_id
        == support.body_excerpts[0].read.catalog.source.artifact.source_artifact_id
    )
    assert not completion.native_source_citations and not completion.source_citations
    # SQL storage-shape check only; this deliberately does not claim to replace
    # APP's separate mandatory producing-output proof and Rules settlement owner.
    execution = turn.graph_context_execution
    binding = t.CompletionBindingEventV1(
        kind="completion_binding",
        event_id=uuid4(),
        sequence=len(execution.events),
        provider_attempt_id=auth.provider_attempt_id,
        completion_sha256=t.canonical_sha256(completion),
        claim_graph_event_ids=bindings,
    )
    execution = type(execution).model_validate_json(
        execution.model_copy(
            update={"events": [*execution.events, binding]}
        ).model_dump_json(by_alias=True)
    )
    with psycopg.connect(application_state_dsn) as conn:
        conn.execute(
            "UPDATE agent.turn SET status='completed',assistant_text=%s,completed_at=clock_timestamp(),claim_expires_at=NULL,completion=%s,graph_context_execution=%s WHERE turn_id=%s",
            (
                answer,
                Jsonb(completion.model_dump(mode="json", by_alias=True)),
                Jsonb(execution.model_dump(mode="json", by_alias=True)),
                turn.turn_id,
            ),
        )
    reopened = service.inspect_turn(world_id=sub.world_id, turn_id=turn.turn_id)
    assert reopened.completion == completion
    from apps.live_control_server.services.agent_native_source_sections import (
        open_native_body_excerpt,
    )
    from apps.live_control_server.services.agent_source_passages import (
        SourcePassageOpenError,
    )
    from tests.test_native_corpus_source_access import GM

    identity = SimpleNamespace(
        managed_world_id=sub.world_id,
        native_world_id="world:test",
        binding_version=1,
        provisioning_id=source_case.bound.provisioning_id,
    )
    opened = open_native_body_excerpt(
        world_id=sub.world_id,
        turn_id=turn.turn_id,
        citation_index=0,
        principal=GM,
        service=service,
        repository=source_case.repo,
        resolve_identity=lambda _: identity,
    )
    assert (
        opened.citation == citation
        and opened.content == support.body_excerpts[0].read.excerpt.text
    )
    with pytest.raises(SourcePassageOpenError):
        open_native_body_excerpt(
            world_id=sub.world_id,
            turn_id=turn.turn_id,
            citation_index=0,
            principal=SimpleNamespace(role="player"),
            service=service,
            repository=source_case.repo,
            resolve_identity=lambda _: identity,
        )
    candidate["answer_segments"][0]["excerpt_handles"] = ["another-attempt"]
    with pytest.raises(ValueError, match="excerpt"):
        normalize(candidate, turn, auth.provider_attempt_id, support)


def test_play_reclaim_reuses_exact_persisted_source_prefix_without_new_capture(
    source_case,
):
    from apps.live_control_server.services.native_play_graph_owner import (
        prepare_authored_sources,
        acquire_authored_sources,
    )
    from tests.test_native_corpus_source_access import GM

    service, sub, turn, _, _ = accepted_play_source_case(source_case)
    request = SimpleNamespace(
        authored_references=sub.submitted_intent_v2.authored_references,
        surface=SimpleNamespace(surface_id="play"),
        owner_scope=SimpleNamespace(world_id=sub.world_id),
    )
    import psycopg
    from application_state.agent_conversation.service import _ready_dsn
    from apps.live_control_server.integrations.dungeonmind.native_corpus_source import (
        prepare_native_source_context,
    )

    with psycopg.connect(_ready_dsn()) as conn:
        conn.execute(
            "UPDATE agent.turn SET claim_expires_at=clock_timestamp()-interval '1 second' WHERE turn_id=%s",
            (turn.turn_id,),
        )
    turn = service.claim_turn(
        sub.world_id, sub.conversation_id, turn.turn_id, expected_revision=turn.revision
    ).turn
    assert turn.attempt == 2 and turn.graph_context_execution.events[0].attempt == 1
    identity = SimpleNamespace(
        managed_world_id=sub.world_id,
        native_world_id="world:test",
        binding_version=1,
        provisioning_id=source_case.bound.provisioning_id,
    )
    core = prepare_native_source_context(
        managed_world_id=sub.world_id,
        principal=GM,
        revision_id=turn.graph_context_receipt.authored_source_context.authority.revision_id,
        repository=source_case.repo,
        resolve_identity=lambda _: identity,
    )
    prepared = prepare_authored_sources(request, GM, existing_turn=turn, prepared=core)

    def append(*args, **kwargs):
        pytest.fail(
            "A fully captured retry must not append another source capture/read"
        )

    adapter = SimpleNamespace(
        work=SimpleNamespace(play_authored_sources=prepared),
        fence=SimpleNamespace(turn=turn, append=append),
        turn=None,
    )
    acquire_authored_sources(adapter)
    assert adapter.turn == turn
    assert service.inspect_turn(world_id=sub.world_id, turn_id=turn.turn_id) == turn
    from dataclasses import replace

    adapter.work.play_authored_sources = replace(prepared, reads=())
    with pytest.raises(ValueError, match="prefix"):
        acquire_authored_sources(adapter)


@pytest.mark.parametrize(
    "field,value",
    [
        ("turn_id", str(uuid4())),
        ("conversation_id", str(uuid4())),
        ("attempt", 9),
        ("submitted_intent_fingerprint", "f" * 64),
    ],
)
def test_play_source_capture_cannot_borrow_another_turn_or_attempt(
    source_case, field, value
):
    _, _, turn, _, _ = accepted_play_source_case(source_case)
    wire = turn.model_dump(mode="json", by_alias=True)
    wire["graph_context_execution"]["events"][0][field] = value
    with pytest.raises(ValueError, match="another request or attempt"):
        t.Turn.model_validate_json(json.dumps(wire))


@pytest.mark.parametrize('provider_capacity',[False,True])
def test_exact_selected_play_source_admits_no_aggregate_token_ceiling(source_case,provider_capacity):
    service,sub,turn,auth,raw=accepted_play_source_case(source_case,token_ceilings=False,provider_capacity=provider_capacity)
    updated,fresh=service.authorize_native_play_provider(sub.world_id,sub.conversation_id,turn.turn_id,
        expected_revision=turn.revision,expected_attempt=turn.attempt,
        provider_attempt_event=auth,prepared_request_json=raw)
    assert fresh and updated.graph_context_execution.policy.max_total_provider_input_tokens is None
    assert updated.graph_context_execution.policy.max_total_provider_output_tokens is None
    assert updated.graph_context_execution.policy.max_provider_attempts > 0


@pytest.mark.parametrize("mode",["work","selected","automatic","memory","rules","graph","unknown","writer_failure","source_failure","forged_work"])
def test_shared_play_ordinary_factory_uses_jev_writer_and_replays_saved_run_answer(
    application_state_dsn,monkeypatch,tmp_path,source_case,mode,request,
):
    from apps.live_control_server.models.agent_turn import AgentTurnRequest
    from apps.live_control_server.routes import agent
    from apps.live_control_server.services.agent_turn_service import execute_agent_turn
    from apps.live_control_server.services.play_jev_harness import PlayJevHarness
    from apps.live_control_server.services.hermes_session_store import HermesSessionPointerStore
    from application_state.agent_conversation import AgentConversationService
    from tests.application_state.test_native_play_graph_postgres import make_submission
    from tests.test_plan_jev_harness import Finish
    import httpx2
    from tests.test_plan_jev_writer import WriterWire
    from application_state.agent_conversation.native_context import SurfaceNativeContextReceiptV1
    import httpx
    graph_lane=request.getfixturevalue('published_lane') if mode=='graph' else None
    service,sub,_frame=make_submission(edition=True,world=graph_lane.world.world_id if graph_lane is not None else None)
    world=sub.world_id
    query_context=query_result=None
    if graph_lane is not None:
        from tests.test_native_plan_statements import query
        query_context,query_result=query(graph_lane,scope_mode='world')
    core=ref=None
    if mode in {'selected','automatic','source_failure'}:
        from apps.live_control_server.integrations.dungeonmind import native_corpus_source as native_owner
        from tests.test_native_corpus_source_access import GM
        old,ref,_sections=selected(source_case)
        source_case.bound.managed_world_id=world
        core=native_owner.prepare_native_source_context(managed_world_id=world,principal=GM,
            repository=source_case.repo,resolve_identity=lambda _:source_case.bound)
        ref=ref.model_copy(update={'managed_world_id':world})
    intent=sub.submitted_intent_v2
    if mode=='memory':
        from application_state.play.session_review import commit_review,ReviewCommand
        basis=sub.play_context_receipt
        commit_review(world_id=world,run_id=basis.run_id,command_id=str(uuid4()),request=ReviewCommand(
            action='end',expected_revision=0,expected_run_revision=basis.run_revision,
            expected_content_sha256=basis.content_sha256,final_thoughts='Players want more exploration next time.'))
    if mode=='graph':intent=intent.model_copy(update={'message':query_result.question})
    if mode=='rules':
        intent=intent.model_copy(update={'message':'Can I end my move in an occupied space?'})
    request=AgentTurnRequest.model_validate_json(json.dumps(dict(
        schema='dmb_agent_turn_request_v1',graph_selection=None,
        client_thread_id='shared-play-native',turn_id=str(uuid4()),message=intent.message,
        surface=dict(surface_id='play',instance_id=intent.surface_instance_id),
        owner_scope=dict(kind='world',world_id=world),client_work_state='saved_clean',
        primary_work=intent.primary_work.model_dump(mode='json'),
        graph_request=intent.graph_request.model_dump(mode='json'),
        play_target=intent.play_target.model_dump(mode='json'),
        **({'authored_references':t.AuthoredReferencesV2(references=(ref,)).model_dump(mode='json',by_alias=True)}
          if mode in {'selected','source_failure'} else {}))))
    monkeypatch.setattr('apps.live_control_server.services.world_container_registry.get_world_container',
        lambda root,world_id:SimpleNamespace(world_id=world_id,name="Synthetic Play World"))
    monkeypatch.setattr(agent,'_managed_world_root',lambda:tmp_path)
    monkeypatch.setattr('apps.live_control_server.services.agent_graph_policy.resolve_agent_graph_openai_inference',
        lambda **_:('openai-api','gpt-6-luna','https://api.openai.com/v1'))
    monkeypatch.setattr('apps.live_control_server.services.plan_source_turn.prepare',
        lambda world_id,*_args,**_kwargs:(core,core.authority) if core is not None else (None,t.NativeCorpusUnavailableV1(
            managed_world_id=world_id,failure_code='native_source_head_unavailable')))
    class Decisions(Finish):
        async def handle_async_request(self,request):
            if mode=='unknown':
                self.calls.append(request)
                raise httpx2.ReadTimeout('Synthetic ambiguous Play controller outcome',request=request)
            if mode not in {'automatic','rules','graph'}:return await super().handle_async_request(request)
            self.calls.append(request);body=json.loads(request.content)
            answers={}
            for name,question in body['questions'].items():
                include=name.startswith('candidate_') and body['state']['candidates'][int(name.split('_')[1])]['kind']==('public_rules_lookup' if mode=='rules' else 'Native Graph object; open its complete admitted statement and assertion support' if mode=='graph' else 'Explicit admitted full-source read; metadata choice, not evidence') and len(self.calls)==1
                choice='finish_retrieval' if name=='operation' else 'include' if include else 'exclude'
                answers[name]={'type':'choice','choice':choice,'confidence':1,
                    'probabilities':{key:float(key==choice) for key in question['criteria']}}
            return httpx2.Response(200,request=request,json={'model':'jev-1.14.0','answers':answers,
                'usage':{'input_tokens':31,'output_tokens':7}})
    decisions=Decisions()
    class Answer(WriterWire):
        async def handle_async_request(self,wire_request):
            body=json.loads(wire_request.content)
            frames=[json.loads(row['content']) for row in body['input'] if row['content'].startswith('{')]
            work=next(frame for frame in frames if 'current_play' in frame)
            evidence=next(frame for frame in frames if 'native_body_evidence' in frame)
            selected=next(row for source in work['current_play'] if source['source_kind']=='scene_note'
                for row in source['text_blocks'])
            answer_segments=[dict(kind='authored_excerpt',selection_id=selected['selection_id'])]
            if mode in {'selected','automatic'}:
                excerpts=evidence['native_body_evidence']['excerpts']
                assert len(excerpts)==1
                answer_segments.append(dict(kind='native_body_claim',text=excerpts[0]['text'].strip(),
                    excerpt_handles=[excerpts[0]['excerpt_handle']]))
            if mode=='graph':
                assertion=evidence['native_assertions']['assertions'][0]
                answer_segments.append(dict(kind='native_assertion_claim',text=str(assertion['assertion']['value']),
                    assertion_handles=[assertion['assertion_handle']]))
            if mode=='memory':
                source=next(source for packet in work['session_evidence'] for source in packet['sources']
                    if source['kind']=='closing_reflections')
                answer_segments.append(dict(kind='session_summary',text='Players want more exploration next time.',
                    selection_ids=[block['selection_id'] for block in source['text_blocks']]))
            output=dict(schema=evidence.get('answer_policy','dmb_surface_evidence_answer_v8'),
                answer_segments=answer_segments,limitations=[],requested_detail_gaps=[])
            if mode=='rules':
                rule=next(frame for frame in frames if 'ruleset' in frame)['supports'][0]
                output=dict(kind='rules_answer',base_output=output,
                    rules_segments=[dict(kind='rules_claim',text=rule['excerpt_text'],support_ids=[rule['support_id']])],
                    ordered_refs=[dict(domain='base',segment_index=None),dict(domain='rules',segment_index=0)])
            self.text=json.dumps(output)
            return await super().handle_async_request(wire_request)
    wire=Answer(None,'',status='incomplete' if mode=='writer_failure' else 'completed')
    class Harness(PlayJevHarness):
        def execute(self,adapter,**kwargs):
            wire.adapter=adapter
            return super().execute(adapter,**kwargs)
    harness=Harness(decision_transport=decisions,writer_transport=wire,
        decision_api_key='synthetic-not-secret',writer_api_key='synthetic-not-secret')
    monkeypatch.setattr('apps.live_control_server.services.play_jev_harness.default_play_jev_runtime',lambda:harness)
    kwargs=dict(root=tmp_path,pointer_store=HermesSessionPointerStore(tmp_path/'pointers'),
        owner_resolver=lambda _:{'kind':'world','id':world,'name':'Synthetic Play World'},
        work_resolver=agent._work_resolver,conversation_service=service,native_principal=SimpleNamespace(role='gm'),
        native_graph_query_resolver=lambda request,*_args:(query_context,query_result) if mode=='graph' else (None,t.NativePlanQueryUnavailableV1(
            managed_world_id=world,reason='native_graph_head_unavailable')),
        graph_resolver=lambda *_args:pytest.fail('No classic Graph fallback'),
        plan_graph_resolver=lambda *_args:pytest.fail('No legacy Play Graph bootstrap'))
    if mode=='source_failure':
        def missing(*_args):raise ValueError('The exact selected source is unavailable')
        monkeypatch.setattr('apps.live_control_server.services.native_authored_references.read_authored_source',missing)
    if mode=='forged_work':
        from apps.live_control_server.services import plan_source_turn
        original=plan_source_turn.play_work_proof
        def forged(*args):
            proof=original(*args)
            frames=[t.PlaySourcePayloadV1.model_validate_json(json.dumps(source)) for source in proof['source_frame']['sources']]
            frames=[source.model_copy(update={'text':source.text+' Invented Run text.'})
                if source.source_kind=='current_moment' else source for source in frames]
            proof['source_frame']=play_source_frame(tuple(frames)).model_dump(mode='json',by_alias=True)
            return proof
        monkeypatch.setattr(plan_source_turn,'play_work_proof',forged)
    if mode in {'unknown','writer_failure','source_failure','forged_work'}:
        from apps.live_control_server.services.agent_turn_service import AgentTurnServiceError
        with pytest.raises(AgentTurnServiceError):execute_agent_turn(request,**kwargs)
        kept=service.list_turns(world,wire.adapter.fence.turn.conversation_id)[-1]
        assert kept.status in {'interrupted','failed'} and kept.completion is None
        assert len(decisions.calls)==(0 if mode in {'source_failure','forged_work'} else 1)
        assert len(wire.calls)==(1 if mode=='writer_failure' else 0)
        if mode=='unknown':assert any(getattr(e,'outcome',None)=='outcome_unknown' for e in kept.graph_context_execution.events)
        trace=service.list_context_trace_attempts(world_id=world,turn_id=kept.turn_id)[-1]
        assert trace.capture_status!='recording'
        before=(len(decisions.calls),len(wire.calls))
        with pytest.raises(AgentTurnServiceError):execute_agent_turn(request,**kwargs)
        assert before==(len(decisions.calls),len(wire.calls))
        return
    response=execute_agent_turn(request,**kwargs)
    assert response.answer.status=='ok'  and response.answer.text.startswith('Saved native note 🦉.')
    delivered=response.rules_context.base_context if mode=='rules' else response.play_context
    assert type(delivered.receipt) is SurfaceNativeContextReceiptV1
    assert delivered.delivery_replay is False
    assert len(decisions.calls)==(2 if mode in {'automatic','rules','graph'} else 1) and len(wire.calls)==1
    assert not any('requested_work' in json.loads(call.content)['questions'] for call in decisions.calls)
    for call in [*decisions.calls,*wire.calls]:
        assert 'max_output_tokens' not in json.loads(call.content)
        raw=call.content.decode()
        assert sub.play_context_receipt.run_id not in raw
        assert sub.play_context_receipt.runbook_object_id not in raw
        assert 'play_source_frame_sha256' not in raw and 'edition revision 1' not in raw
    replay=execute_agent_turn(request,**kwargs)
    assert (replay.rules_context.base_context if mode=='rules' else replay.play_context).delivery_replay is True
    assert replay.answer.text==response.answer.text
    assert len(decisions.calls)==(2 if mode in {'automatic','rules','graph'} else 1) and len(wire.calls)==1
    stored=AgentConversationService().list_turns(world,wire.adapter.turn.conversation_id)[-1]
    if mode=='rules':stored=stored.base_projection.turn
    assert stored.play_context_receipt==sub.play_context_receipt
    assert stored.completion.answer_segments[0].source_kind=='play'
    if mode in {'selected','automatic'}:assert stored.completion.native_body_citations
    if mode=='memory':assert stored.completion.answer_segments[-1].kind=='session_summary'
    if mode=='graph':assert stored.completion.native_assertion_citations
    if mode=='selected':
        import os
        from pathlib import Path
        if destination:=os.environ.get('DMB_NATIVE_PLAY_WIRE'):
            Path(destination).write_text(json.dumps(dict(response={key:response.model_dump(mode='json',by_alias=True)[key] for key in ('play_context','graph')},
                request=request.model_dump(mode='json',by_alias=True),
                provenance=stored.provenance.model_dump(mode='json',by_alias=True)),ensure_ascii=False,indent=2)+'\n')
