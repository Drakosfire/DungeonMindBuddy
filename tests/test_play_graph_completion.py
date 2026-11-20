"""Native source lineage and completion evidence; no provider/SQL authority."""
import json
from uuid import uuid4

import pytest

from application_state.agent_conversation import types as t
from application_state.agent_conversation.play_graph_context import (
    prepare_play_source_provider_inclusion, validate_play_graph_execution_binding,
    validate_play_graph_provider_authorization,
)
from application_state.agent_conversation.play_graph_completion import validate_play_graph_completion
from tests.test_play_graph_context import fixture, seal_receipt
from tests.test_play_graph_authority import MOMENT, native_provider, native_events
from application_state.agent_conversation.play_graph_authority import play_graph_execution_policy_digest


def start(*, expose=True, graph=False):
    receipt, execution, frame = fixture()
    auth = native_provider(1 if expose else 0)
    if graph:
        auth = auth.model_copy(update={"included_assertion_ids":["assertion-one"], "included_evidence_ref_ids":["e0"]})
    if expose:
        included = prepare_play_source_provider_inclusion(receipt, execution, frame, event_id=uuid4(),
            provider_attempt_id=auth.provider_attempt_id, envelope_sha256=auth.envelope_sha256,
            owner_resolved_current_moment_text=MOMENT)
        execution = native_events(execution, [included])
    execution = validate_play_graph_provider_authorization(receipt, execution, auth)
    return receipt, execution, frame, auth


def acknowledge(execution, auth):
    events = list(execution.events)
    for outcome in ("sdk_entered", "response_received"):
        events.append(t.ProviderOutcomeEventV1(event_id=uuid4(), sequence=len(events), kind="provider_outcome",
            provider_attempt_id=auth.provider_attempt_id, outcome=outcome))
    return native_events(execution, events)


def play_claim(frame):
    return t.PlayContextClaimV1(kind="play_context_claim", text="The saved note records the crossing 🦉.",
        source_ids=sorted(entry.source_id for entry in frame.manifest.entries))


def graph_claim():
    return t.PlanWorldGraphClaimSegmentV1(kind="graph_claim", claim_id="claim:1", text="An admitted Graph fact.",
        target_kind="assertion", target_id="assertion-one", graph_revision="graph-one", evidence_ref_ids=["e0"])


def complete(receipt, segments, *, status="play_only_insufficient_evidence", read_ids=()):
    claims = [item for item in segments if isinstance(item,t.PlanWorldGraphClaimSegmentV1)]
    citations = t.PlanWorldGraphCitationMapV2(context_receipt_sha256=receipt.context_receipt_sha256,
        entries=[t.PlanWorldGraphCitationV2(claim_id=item.claim_id, target_kind=item.target_kind,
            target_id=item.target_id, graph_revision=item.graph_revision, evidence_ref_ids=item.evidence_ref_ids,
            source_opened=bool(read_ids), source_read_ids=list(read_ids)) for item in claims]) if claims else None
    return t.PlayWorldGraphCompletionV1(context_receipt_sha256=receipt.context_receipt_sha256,
        answer_basis=t.play_answer_basis(segments), answer_context_status=status,
        answer_segments=segments, citation_map=citations)


def test_exact_producing_sources_support_play_attribution_without_promoting_graph_truth():
    receipt, execution, frame, auth = start()
    execution = acknowledge(execution, auth)
    completion = complete(receipt,[play_claim(frame)])
    validate_play_graph_completion(completion,receipt,execution,auth.provider_attempt_id,{})
    assert completion.answer_basis == "play_sources"
    encoded = completion.model_dump_json(by_alias=True)
    assert t.PlayWorldGraphCompletionV1.model_validate_json(encoded).model_dump_json(by_alias=True)==encoded


@pytest.mark.parametrize("change", ["missing_inclusion", "unknown_source", "no_response", "other_producer", "wrong_status"])
def test_prepared_claim_requires_current_producer_sources_and_acknowledgement(change):
    receipt, execution, frame, auth = start(expose=change!="missing_inclusion")
    if change != "no_response": execution=acknowledge(execution,auth)
    claim=play_claim(frame)
    if change=="unknown_source": claim=claim.model_copy(update={"source_ids":["play-source:"+"f"*64]})
    completion=complete(receipt,[claim],status="play_only_graph_unused" if change=="wrong_status" else "play_only_insufficient_evidence")
    with pytest.raises(ValueError):
        validate_play_graph_completion(completion,receipt,execution,
            uuid4() if change=="other_producer" else auth.provider_attempt_id,{})


def test_earlier_exposure_cannot_authorize_a_later_request_that_omits_the_frame():
    receipt, execution, frame, first = start()
    execution=acknowledge(execution,first)
    second=native_provider(len(execution.events)).model_copy(update={"envelope_sha256":"f"*64})
    execution=validate_play_graph_provider_authorization(receipt,execution,second)
    execution=acknowledge(execution,second)
    with pytest.raises(ValueError,match="absent from the producing request"):
        validate_play_graph_completion(complete(receipt,[play_claim(frame)]),receipt,execution,second.provider_attempt_id,{})
    # Missing source inclusion is zero source authority, not a Graph/plaintext fallback.
    context=t.PlanWorldGraphConnectiveSegmentV1(kind="connective",text="What would you like to explore next?")
    validate_play_graph_completion(complete(receipt,[context]),receipt,execution,second.provider_attempt_id,{})


@pytest.mark.parametrize("change", ["frame_hash", "source_ids", "context", "policy", "provider", "envelope", "interleave", "duplicate"])
def test_source_inclusion_cannot_be_rebound_or_interleaved(change):
    receipt, execution, frame = fixture()
    auth=native_provider(1)
    event=prepare_play_source_provider_inclusion(receipt,execution,frame,event_id=uuid4(),
        provider_attempt_id=auth.provider_attempt_id,envelope_sha256=auth.envelope_sha256,
        owner_resolved_current_moment_text=MOMENT)
    fields={"frame_hash":("source_frame_sha256","f"*64),"source_ids":("source_ids",[]),
        "context":("context_receipt_sha256","f"*64),"policy":("execution_policy_sha256","f"*64),
        "provider":("provider_attempt_id",uuid4()),"envelope":("envelope_sha256","f"*64)}
    if change in fields:
        field,value=fields[change];event=event.model_copy(update={field:value})
    events=[event,auth]
    if change=="interleave":
        events=[event,t.ValidatedGraphOperationEventV3(kind="validated_graph_operation_v3",event_id=uuid4(),sequence=1,
            operation_id=uuid4(),operation="expand_graph_retrieval",request_arguments_sha256="a"*64,
            graph_revision="graph-one",result_packet_sha256="b"*64,assertion_ids=[],relationship_ids=[],
            evidence_ref_ids=[],evidence_sufficiency_status="insufficient",coverage_status="complete",
            truncated=False,source_opened=False,returned_source_pins=[]),auth.model_copy(update={"sequence":2})]
    if change=="duplicate":events=[event,event.model_copy(update={"event_id":uuid4(),"sequence":1})]
    with pytest.raises(ValueError):validate_play_graph_execution_binding(receipt,native_events(execution,events))


def test_pending_inclusion_can_be_retained_but_cannot_authorize_a_completion_or_follow_its_producer():
    receipt, execution, frame = fixture()
    auth=native_provider(1)
    event=prepare_play_source_provider_inclusion(receipt,execution,frame,event_id=uuid4(),
        provider_attempt_id=auth.provider_attempt_id,envelope_sha256=auth.envelope_sha256,
        owner_resolved_current_moment_text=MOMENT)
    pending=native_events(execution,[event])
    assert len(pending.events)==1
    with pytest.raises(ValueError):validate_play_graph_completion(complete(receipt,[play_claim(frame)]),receipt,pending,auth.provider_attempt_id,{})
    receipt, execution, frame, auth=start(expose=False)
    execution=acknowledge(execution,auth)
    with pytest.raises(ValueError):native_events(execution,[*execution.events,event.model_copy(update={
        "sequence":len(execution.events),"provider_attempt_id":auth.provider_attempt_id})])


def test_preparation_rehashes_actual_frame_and_checks_independent_owner_body():
    receipt,execution,frame=fixture()
    with pytest.raises(ValueError,match="independent source owner"):
        prepare_play_source_provider_inclusion(receipt,execution,frame,event_id=uuid4(),provider_attempt_id=uuid4(),
            envelope_sha256="c"*64,owner_resolved_current_moment_text="Other scene")
    wire=receipt.model_dump(mode="json",by_alias=True);wire["play_source_frame_sha256"]="f"*64
    changed=seal_receipt(wire)
    policy=execution.policy
    execution=t.PlayWorldGraphExecutionV1(context_receipt_sha256=changed.context_receipt_sha256,
        execution_policy_sha256=play_graph_execution_policy_digest(changed.context_receipt_sha256,policy),
        policy=policy,events=[])
    with pytest.raises(ValueError,match="frozen receipt manifest"):
        prepare_play_source_provider_inclusion(changed,execution,frame,event_id=uuid4(),provider_attempt_id=uuid4(),
            envelope_sha256="c"*64,owner_resolved_current_moment_text=MOMENT)


def test_graph_and_play_claims_keep_independent_producing_evidence_domains():
    receipt, execution, frame, auth=start(graph=True)
    execution=acknowledge(execution,auth)
    completion=complete(receipt,[play_claim(frame),graph_claim()],status="graph_grounded")
    validate_play_graph_completion(completion,receipt,execution,auth.provider_attempt_id,{"claim:1":[]})
    assert completion.answer_basis=="play_sources_plus_world_graph"
    receipt, execution, frame, auth=start(graph=False)
    execution=acknowledge(execution,auth)
    with pytest.raises(ValueError):validate_play_graph_completion(complete(receipt,[graph_claim()],status="graph_grounded"),receipt,execution,auth.provider_attempt_id,{"claim:1":[]})


@pytest.mark.parametrize("change", ["basis", "status", "plan_claim", "review", "source_order", "empty_source", "duplicate_claim", "citation", "size", "blank"])
def test_native_completion_shape_is_closed_and_source_citations_are_not_graph_citations(change):
    receipt,execution,frame,auth=start(graph=True)
    completion=complete(receipt,[play_claim(frame),graph_claim()],status="graph_grounded")
    wire=completion.model_dump(mode="json",by_alias=True)
    if change=="basis":wire["answer_basis"]="committed_plan"
    if change=="status":wire["answer_context_status"]="play_only_graph_unused"
    if change=="plan_claim":wire["answer_segments"][0]={"kind":"plan_claim","text":"Not a Plan","plan_content_sha256":"a"*64}
    if change=="review":wire["answer_segments"][0]={"kind":"session_evidence_claim","text":"Not supplied","run_id":"run-one"}
    if change=="source_order":wire["answer_segments"][0]["source_ids"].reverse()
    if change=="empty_source":wire["answer_segments"][0]["source_ids"]=[]
    if change=="duplicate_claim":wire["answer_segments"].append(wire["answer_segments"][1])
    if change=="citation":wire["citation_map"]["entries"][0]["target_id"]="other"
    if change=="blank":
        wire["answer_segments"]=[{"kind":"connective","text":" "}]
        wire.update(answer_basis="nonfactual_context",answer_context_status="play_only_insufficient_evidence",citation_map=None)
    if change=="size":
        wire["answer_segments"]=[{"kind":"connective","text":"🦉"*4000} for _ in range(5)]
        wire.update(answer_basis="nonfactual_context",answer_context_status="play_only_insufficient_evidence",citation_map=None)
    with pytest.raises(ValueError):t.PlayWorldGraphCompletionV1.model_validate_json(json.dumps(wire))


def test_plan_cannot_silently_project_an_in_memory_native_source_event():
    from tests.test_settled_source_read_accounting import fixture_execution
    receipt,execution,frame=fixture()
    event=prepare_play_source_provider_inclusion(receipt,execution,frame,event_id=uuid4(),provider_attempt_id=uuid4(),
        envelope_sha256="c"*64,owner_resolved_current_moment_text=MOMENT)
    forged=fixture_execution().model_copy(update={"events":[event]})
    with pytest.raises(ValueError,match="native-Play-only"):
        t.PlanWorldGraphExecutionV3.model_validate(forged)


@pytest.mark.parametrize("change", [None,"withheld_read","foreign_read","missing_binding"])
def test_native_indexed_evidence_uses_its_own_frozen_scope_and_producing_source_reads(change):
    from tests.test_settled_source_read_accounting import authorization,receipt as read_receipt
    receipt,execution,frame=fixture()
    wire=receipt.model_dump(mode="json",by_alias=True)
    wire["assembled_input"]["dispatched_evidence_ref_ids"]=["e1","e2","e3","e4","e5","e6","e7"]
    receipt=seal_receipt(wire)
    execution=t.PlayWorldGraphExecutionV1(context_receipt_sha256=receipt.context_receipt_sha256,
        execution_policy_sha256=play_graph_execution_policy_digest(receipt.context_receipt_sha256,execution.policy),
        policy=execution.policy,events=[])
    origin=t.ValidatedGraphOperationEventV3(kind="validated_graph_operation_v3",event_id=uuid4(),sequence=0,
        operation_id=uuid4(),operation="expand_graph_retrieval",request_arguments_sha256="a"*64,
        graph_revision="graph-one",result_packet_sha256="b"*64,assertion_ids=["assertion-one"],relationship_ids=[],
        evidence_ref_ids=["e0"],evidence_sufficiency_status="sufficient",coverage_status="complete",truncated=False,
        source_opened=False,returned_source_pins=[])
    source_auth=authorization(execution,1,count=1)
    source_done=read_receipt(source_auth,2)
    auth=native_provider(3).model_copy(update={"included_assertion_ids":["assertion-one"],
        "included_graph_event_ids":[origin.event_id],
        "included_source_read_event_ids":[] if change=="withheld_read" else [source_done.event_id]})
    execution=native_events(execution,[origin,source_auth,source_done])
    execution=validate_play_graph_provider_authorization(receipt,execution,auth)
    execution=acknowledge(execution,auth)
    ids=["foreign-read"] if change=="foreign_read" else [source_done.receipts[0].source_read_id]
    completion=complete(receipt,[graph_claim()],status="graph_grounded",read_ids=ids)
    bindings={"claim:1":[]} if change=="missing_binding" else {"claim:1":[origin.event_id]}
    if change is None:
        validate_play_graph_completion(completion,receipt,execution,auth.provider_attempt_id,bindings)
    else:
        with pytest.raises(ValueError):validate_play_graph_completion(completion,receipt,execution,auth.provider_attempt_id,bindings)


@pytest.mark.parametrize("change", ["later_provider", "pending_source"])
def test_earlier_acknowledged_answer_cannot_finish_after_new_execution_work(change):
    receipt,execution,frame,first=start()
    execution=acknowledge(execution,first)
    second=native_provider(len(execution.events)+(1 if change=="pending_source" else 0)).model_copy(update={"envelope_sha256":"f"*64})
    if change=="later_provider":
        execution=validate_play_graph_provider_authorization(receipt,execution,second)
    else:
        included=prepare_play_source_provider_inclusion(receipt,execution,frame,event_id=uuid4(),
            provider_attempt_id=second.provider_attempt_id,envelope_sha256=second.envelope_sha256,
            owner_resolved_current_moment_text=MOMENT)
        execution=native_events(execution,[*execution.events,included])
    with pytest.raises(ValueError,match="final acknowledged provider"):
        validate_play_graph_completion(complete(receipt,[play_claim(frame)]),receipt,execution,first.provider_attempt_id,{})


@pytest.mark.parametrize("change", [None,"hash","producer","mapping"])
def test_stored_native_completion_binding_is_checked_against_the_exact_answer(change):
    receipt,execution,frame,auth=start()
    execution=acknowledge(execution,auth)
    completion=complete(receipt,[play_claim(frame)])
    binding=t.CompletionBindingEventV1(kind="completion_binding",event_id=uuid4(),sequence=len(execution.events),
        provider_attempt_id=uuid4() if change=="producer" else auth.provider_attempt_id,
        completion_sha256="f"*64 if change=="hash" else t.canonical_sha256(completion),
        claim_graph_event_ids={"foreign":[]} if change=="mapping" else {})
    if change=="producer":
        with pytest.raises(ValueError):native_events(execution,[*execution.events,binding])
    else:
        execution=native_events(execution,[*execution.events,binding])
        if change is None:validate_play_graph_completion(completion,receipt,execution,auth.provider_attempt_id,{})
        else:
            with pytest.raises(ValueError,match="exact completion binding"):
                validate_play_graph_completion(completion,receipt,execution,auth.provider_attempt_id,{})
