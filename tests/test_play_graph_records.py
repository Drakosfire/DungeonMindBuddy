"""Owning native conversation record codecs; no SQL/native SDK activation."""
from datetime import UTC, datetime, timedelta
import json
from uuid import uuid4

import pytest

from application_state.agent_conversation import types as t
from application_state.agent_conversation.play_graph_authority import play_graph_intent_fingerprint
from application_state.agent_conversation.service import _validated_base_execution_locked
from application_state.errors import ApplicationStateValidationError
from tests.test_play_graph_context import fixture, intent_wire
from tests.test_play_graph_completion import start, acknowledge, complete, play_claim
from tests.test_play_graph_authority import native_events

NOW=datetime(2026,10,20,tzinfo=UTC)


def provenance(receipt):
    primary,support=t.encode_play_run_turn_context_references(receipt.play_basis)
    support += [t.encode_play_graph_binding_reference(t.PlayGraphBindingReceiptV1(
        schema="dmb_play_graph_binding_receipt_v1",managed_world_id=receipt.play_basis.world_id,
        native_world_id=receipt.graph_authority.native_world_id,binding_version=receipt.graph_authority.binding_version)),
        t.HistoricalReference(resolution="resolved",kind="world_graph_revision",object_id=receipt.graph_authority.native_world_id,
            revision=receipt.graph_authority.graph_revision)]
    return t.TurnProvenance(world_id=receipt.play_basis.world_id,surface_resolution="resolved",surface_id="play",
        surface_instance_id="play:run-one",primary_work=primary,supporting_work=support,
        selected_object=t.HistoricalReference(resolution="absent"))


def submission():
    receipt,execution,_=fixture()
    intent=t.PlayGraphIntentV1.model_validate_json(json.dumps(intent_wire()))
    return t.TurnSubmission(world_id="world-one",conversation_id=uuid4(),idempotency_key=uuid4(),expected_conversation_revision=1,
        user_text=intent.message,provenance=provenance(receipt),submitted_intent_v2=intent,
        graph_context_receipt=receipt,graph_context_execution=execution,play_context_receipt=receipt.play_basis)


def retained(*,status="accepted",completed=False):
    sub=submission()
    receipt,execution=sub.graph_context_receipt,sub.graph_context_execution
    completion=None;body=None
    if completed:
        receipt,execution,frame,auth=start()
        execution=acknowledge(execution,auth)
        completion=complete(receipt,[play_claim(frame)])
        body="\n".join(segment.text for segment in completion.answer_segments)
        binding=t.CompletionBindingEventV1(kind="completion_binding",event_id=uuid4(),sequence=len(execution.events),
            provider_attempt_id=auth.provider_attempt_id,completion_sha256=t.canonical_sha256(completion),claim_graph_event_ids={})
        execution=native_events(execution,[*execution.events,binding]);status="completed"
    return t.Turn(turn_id=uuid4(),conversation_id=sub.conversation_id,world_id=sub.world_id,idempotency_key=sub.idempotency_key,
        sequence=1,revision=1,status=status,user_text=sub.user_text,assistant_text=body,failure_code=None,
        provenance=sub.provenance,submitted_intent_fingerprint_v2=t.submitted_turn_intent_fingerprint_v2(sub.submitted_intent_v2),
        graph_context_receipt=receipt,graph_context_execution=execution,play_context_receipt=receipt.play_basis,
        completion=completion,attempt=1 if status!="accepted" else 0,claim_expires_at=NOW+timedelta(minutes=1) if status=="running" else None,
        accepted_at=NOW,completed_at=NOW if completed else None,updated_at=NOW)


def test_native_submission_and_retained_codecs_use_real_owning_types_and_exact_fingerprint():
    sub=submission()
    restored=t.TurnSubmission.model_validate_json(sub.model_dump_json(by_alias=True))
    assert isinstance(restored.submitted_intent_v2,t.PlayGraphIntentV1)
    assert isinstance(restored.graph_context_receipt,t.PlayWorldGraphContextReceiptV1)
    assert isinstance(restored.graph_context_execution,t.PlayWorldGraphExecutionV1)
    assert not isinstance(restored.graph_context_execution,t.PlanWorldGraphExecutionV2)
    assert t.submitted_turn_intent_fingerprint_v2(restored.submitted_intent_v2)==play_graph_intent_fingerprint(restored.submitted_intent_v2)
    # Schema generation exercises the same owner namespace used during startup.
    for model in (t.TurnSubmission,t.Turn,t.TurnResult):model.model_json_schema()


@pytest.mark.parametrize("status",["accepted","running","failed","interrupted"])
def test_native_nonterminal_and_failure_record_roundtrip_preserves_null_completion(status):
    turn=retained(status=status)
    encoded=turn.model_dump_json(by_alias=True)
    assert t.Turn.model_validate_json(encoded).model_dump_json(by_alias=True)==encoded
    assert turn.completion is None and turn.assistant_text is None


def test_native_completed_record_uses_its_exact_source_binding_and_body():
    turn=retained(completed=True)
    encoded=turn.model_dump_json(by_alias=True)
    restored=t.Turn.model_validate_json(encoded)
    assert restored.model_dump_json(by_alias=True)==encoded
    assert isinstance(restored.completion,t.PlayWorldGraphCompletionV1)
    binding=restored.graph_context_execution.events[-1]
    t.validate_execution_completion(restored.completion,restored.graph_context_receipt,restored.graph_context_execution,
        binding.provider_attempt_id,binding.claim_graph_event_ids)


@pytest.mark.parametrize("change",["message","world","surface_instance","context","intent_edition","intent_target","ledger_nonempty","accounting","binding","graph_revision","missing_binding","plan_ledger"])
def test_native_submission_rejects_cross_owner_intent_context_and_ledger(change):
    sub=submission();wire=sub.model_dump(mode="json",by_alias=True)
    if change=="message":wire["user_text"]="Other question"
    if change=="world":wire["world_id"]="other"
    if change=="surface_instance":wire["provenance"]["surface_instance_id"]="other"
    if change=="context":wire["play_context_receipt"]=None
    if change=="intent_edition":wire["submitted_intent_v2"]["primary_work"]["play_content_basis"]["content_sha256"]="f"*64
    if change=="intent_target":wire["submitted_intent_v2"]["play_target"]["scene_id"]="scene:other"
    if change=="ledger_nonempty":
        _,execution,_,_=start();wire["graph_context_execution"]=execution.model_dump(mode="json",by_alias=True)
    if change=="accounting":
        receipt=wire["graph_context_receipt"];receipt["assembled_input"]["tokenizer_name"]="other"
        receipt["context_receipt_sha256"]=t.canonical_sha256({k:v for k,v in receipt.items() if k!="context_receipt_sha256"})
        execution=wire["graph_context_execution"];execution["context_receipt_sha256"]=receipt["context_receipt_sha256"]
        from application_state.agent_conversation.play_graph_authority import play_graph_execution_policy_digest
        execution["execution_policy_sha256"]=play_graph_execution_policy_digest(execution["context_receipt_sha256"],t.NativePlayGraphPolicyV1.model_validate_json(json.dumps(execution["policy"])))
    if change in {"binding","graph_revision"}:
        for ref in wire["provenance"]["supporting_work"]:
            if ref["kind"]==("dmb_play_graph_binding_v1" if change=="binding" else "world_graph_revision"):ref["revision"]="2" if change=="binding" else "other"
    if change=="missing_binding":wire["provenance"]["supporting_work"]=[ref for ref in wire["provenance"]["supporting_work"] if ref["kind"]!="dmb_play_graph_binding_v1"]
    if change=="plan_ledger":
        from tests.test_settled_source_read_accounting import fixture_execution
        wire["graph_context_execution"]=fixture_execution().model_dump(mode="json",by_alias=True)
    with pytest.raises(ValueError):t.TurnSubmission.model_validate_json(json.dumps(wire))


@pytest.mark.parametrize("change",["context","run","world","binding","partial_text","missing_fingerprint","wrong_receipt_kind"])
def test_retained_native_record_rechecks_provenance_context_and_no_partial_answer(change):
    wire=retained().model_dump(mode="json",by_alias=True)
    if change=="context":wire["play_context_receipt"]=None
    if change=="run":wire["provenance"]["primary_work"]["object_id"]="other"
    if change=="world":wire["world_id"]="other"
    if change=="binding":
        for ref in wire["provenance"]["supporting_work"]:
            if ref["kind"]=="dmb_play_graph_binding_v1":ref["revision"]="2"
    if change=="partial_text":wire["assistant_text"]="Do not publish a partial answer"
    if change=="missing_fingerprint":wire["submitted_intent_fingerprint_v2"]=None
    if change=="wrong_receipt_kind":wire["graph_context_receipt"]["schema"]="dmb_agent_plan_world_graph_context_receipt_v1"
    with pytest.raises(ValueError):t.Turn.model_validate_json(json.dumps(wire))


@pytest.mark.parametrize("change",["text","no_completion","no_completed_at","wrong_status","completion_hash"])
def test_completed_native_record_cannot_lose_or_change_its_acceptance(change):
    wire=retained(completed=True).model_dump(mode="json",by_alias=True)
    if change=="text":wire["assistant_text"]="Other answer"
    if change=="no_completion":wire["completion"]=None
    if change=="no_completed_at":wire["completed_at"]=None
    if change=="wrong_status":wire["status"]="failed"
    if change=="completion_hash":wire["graph_context_execution"]["events"][-1]["completion_sha256"]="f"*64
    with pytest.raises(ValueError):t.Turn.model_validate_json(json.dumps(wire))


def test_native_result_is_not_accepted_through_the_ordinary_app_completion_path():
    turn=retained(completed=True)
    binding=turn.graph_context_execution.events[-1]
    result=t.TurnResult(world_id=turn.world_id,conversation_id=turn.conversation_id,turn_id=turn.turn_id,
        expected_revision=turn.revision,assistant_text=turn.assistant_text,completion=turn.completion,
        producing_provider_attempt_id=binding.provider_attempt_id,claim_graph_event_ids={})
    assert isinstance(t.TurnResult.model_validate_json(result.model_dump_json(by_alias=True)).completion,t.PlayWorldGraphCompletionV1)
    with pytest.raises(ApplicationStateValidationError,match="actual producing-output proof"):
        _validated_base_execution_locked(None,turn,result)
    wire=result.model_dump(mode="json",by_alias=True);wire["assistant_text"]="Other answer"
    with pytest.raises(ValueError):t.TurnResult.model_validate_json(json.dumps(wire))
    wire=result.model_dump(mode="json",by_alias=True);wire["producing_provider_attempt_id"]=None;wire["claim_graph_event_ids"]=None
    with pytest.raises(ValueError):t.TurnResult.model_validate_json(json.dumps(wire))
