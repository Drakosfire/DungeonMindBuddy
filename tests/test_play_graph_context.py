"""Exact native Play owner/source/scope/provider joins, without DB or SDK."""
import json
from uuid import uuid4

import pytest

from application_state.agent_conversation.play_graph_authority import (
    PlayGraphIntentV1, PlayGraphPolicyV1, PlayWorldGraphExecutionV1,
    NativePlayGraphPolicyV1, play_graph_execution_policy_digest, play_source_frame,
)
from application_state.agent_conversation.play_graph_context import (
    PlayWorldGraphAssembledInputV1, PlayWorldGraphContextReceiptV1, PlayWorldGraphPacketV1,
    validate_play_graph_intent_receipt, validate_play_graph_source_frame,
    validate_play_graph_execution_binding, validate_play_graph_provider_authorization,
)
from application_state.agent_conversation.rules_authority_types import canonical_sha256
from application_state.agent_conversation.types import (
    PlanWorldGraphAuthorityV1, ProviderOutcomeEventV1, SourceScopeExtensionEventV3,
    ValidatedGraphOperationEventV3, RelatedRecapContextAuthorizationEventV2,
    RelatedRecapContextAdmissionV2, related_recap_provenance_result_digest,
)
from tests.test_play_graph_authority import basis, payload, MOMENT, intent_wire, native_execution, native_provider, native_events


def seal_receipt(wire):
    wire = dict(wire)
    wire["context_receipt_sha256"] = canonical_sha256({k: v for k, v in wire.items() if k != "context_receipt_sha256"})
    return PlayWorldGraphContextReceiptV1.model_validate_json(json.dumps(wire))


def fixture():
    frame = play_source_frame((payload(), payload("scene_note")))
    policy = native_execution().policy.model_dump(mode="json", by_alias=True)
    policy["source_read_scope"].update(world_id="world-one", graph_revision="graph-one", retrieval_session_id="retrieval-one")
    policy = NativePlayGraphPolicyV1.model_validate_json(json.dumps(policy))
    refs = sorted(pin.evidence_ref_id for pin in policy.source_read_scope.admitted_anchors)
    packet = PlayWorldGraphPacketV1(packet_serializer_version="canonical-json-utf8-v1",
        selection_policy_version="parent_initial_retrieval_with_bounded_source_index_v1",
        evidence_sufficiency_policy_version="synthetic", retrieval_packet_sha256="b" * 64,
        candidate_assertion_ids=["assertion-one"], candidate_relationship_ids=[], candidate_evidence_ref_ids=refs,
        retrieval_status="complete", evidence_sufficiency_status="sufficient", result_limit=32,
        coverage_status="complete", truncated=False, omission_reasons=[])
    assembled = PlayWorldGraphAssembledInputV1(assembler_version="native-play-v1", budget_policy_version="synthetic",
        provider_model_name="synthetic", provider_model_version="synthetic", tokenizer_name="synthetic", tokenizer_version="synthetic",
        provider_envelope_input_tokens=12, output_token_reserve=10, context_window_limit=1024,
        packet_disposition="included", dispatched_packet_sha256="b" * 64,
        dispatched_assertion_ids=["assertion-one"], dispatched_relationship_ids=[], dispatched_evidence_ref_ids=refs,
        source_token_accounting=[dict(source_kind="play", source_id="run-one", input_tokens=12)],
        included_history=[], assembled_input_sha256="c" * 64)
    wire = dict(schema="dmb_play_world_graph_context_receipt_v1", receipt_serializer_version="canonical-json-utf8-v1",
        play_graph_policy=PlayGraphPolicyV1().model_dump(mode="json", by_alias=True),
        play_basis=basis().model_dump(mode="json", by_alias=True), play_sources=frame.manifest.model_dump(mode="json", by_alias=True),
        retrieval_session_id="retrieval-one", graph_authority=PlanWorldGraphAuthorityV1(managed_world_id="world-one",
            native_world_id="native-world-one", binding_version=1, scope_mode="world", campaign_id=None,
            admissibility_version="gm-v1", graph_revision="graph-one").model_dump(mode="json", by_alias=True),
        graph_packet=packet.model_dump(mode="json", by_alias=True), assembled_input=assembled.model_dump(mode="json", by_alias=True),
        evidence_mode="metadata_only", source_opened=False)
    receipt = seal_receipt(wire)
    execution = PlayWorldGraphExecutionV1(context_receipt_sha256=receipt.context_receipt_sha256,
        execution_policy_sha256=play_graph_execution_policy_digest(receipt.context_receipt_sha256, policy), policy=policy, events=[])
    return receipt, execution, frame


def test_play_receipt_roundtrips_as_play_and_joins_original_intent_sources_and_graph():
    receipt, execution, frame = fixture()
    encoded = receipt.model_dump_json(by_alias=True)
    assert type(receipt).model_validate_json(encoded).model_dump_json(by_alias=True) == encoded
    assert receipt.assembled_input.source_token_accounting[0].source_kind == "play"
    validate_play_graph_intent_receipt(PlayGraphIntentV1.model_validate_json(json.dumps(intent_wire())), receipt)
    validate_play_graph_source_frame(receipt, frame, owner_resolved_current_moment_text=MOMENT)
    validate_play_graph_execution_binding(receipt, execution)
    appended = validate_play_graph_provider_authorization(receipt, execution, native_provider())
    assert len(appended.events) == 1 and execution.events == []
    assert receipt.committed_content_sha256 == basis().content_sha256


@pytest.mark.parametrize("change", ["world", "run", "revision", "edition", "beat", "scene"])
def test_original_intent_cannot_be_rebound_to_the_resolved_context(change):
    receipt, _, _ = fixture()
    wire = intent_wire()
    if change == "world": wire["world_id"] = wire["graph_request"]["world_id"] = "other"
    if change == "run": wire["primary_work"]["object_id"] = "other"
    if change == "revision": wire["primary_work"]["expected_revision"] = 4
    if change == "edition": wire["primary_work"]["play_content_basis"]["content_sha256"] = "f" * 64
    if change == "beat": wire["play_target"]["beat_id"] = "beat:other"
    if change == "scene": wire["play_target"]["scene_id"] = None
    with pytest.raises(ValueError, match="Submitted Play intent"):
        validate_play_graph_intent_receipt(PlayGraphIntentV1.model_validate_json(json.dumps(wire)), receipt)


@pytest.mark.parametrize("change", ["hash", "schema", "world", "campaign", "native_world", "session", "gm", "manifest_locator", "note", "dispatched", "selected_scope", "accounting"])
def test_receipt_rejects_forged_even_self_consistently_resealed_metadata(change):
    receipt, _, _ = fixture()
    wire = receipt.model_dump(mode="json", by_alias=True)
    if change == "hash":
        wire["context_receipt_sha256"] = "0" * 64
        with pytest.raises(ValueError): PlayWorldGraphContextReceiptV1.model_validate_json(json.dumps(wire))
        return
    if change == "schema": wire["schema"] = "dmb_agent_plan_world_graph_context_receipt_v1"
    if change == "world": wire["graph_authority"]["managed_world_id"] = "other"
    if change == "campaign": wire["graph_authority"]["campaign_id"] = "other"
    if change == "native_world": wire["graph_authority"]["native_world_id"] = " padded "
    if change == "session": wire["retrieval_session_id"] = " padded "
    if change == "gm": wire["graph_authority"]["admissibility_version"] = "player-v1"
    if change == "note": wire["play_basis"]["scene_note"] = "Other saved note"
    if change == "dispatched": wire["assembled_input"]["dispatched_assertion_ids"] = ["not-retrieved"]
    if change == "selected_scope": wire["graph_packet"]["selection_policy_version"] = "parent_initial_retrieval_with_selected_source_index_v1"
    if change == "accounting": wire["assembled_input"]["source_token_accounting"][0]["source_kind"] = "plan"
    if change == "manifest_locator":
        wire["play_sources"]["entries"][0]["locator"]["run_id"] = "other"
        wire["play_sources"]["manifest_sha256"] = canonical_sha256({k:v for k,v in wire["play_sources"].items() if k != "manifest_sha256"})
    with pytest.raises(ValueError): seal_receipt(wire)


def test_saved_note_and_moment_are_exact_body_commitments_not_source_labels():
    receipt, _, frame = fixture()
    with pytest.raises(ValueError, match="independent source owner"):
        validate_play_graph_source_frame(receipt, frame, owner_resolved_current_moment_text="Unrelated scene")
    replaced = play_source_frame((payload(text="Other source"), payload("scene_note")))
    with pytest.raises(ValueError, match="frozen receipt manifest"):
        validate_play_graph_source_frame(receipt, replaced, owner_resolved_current_moment_text="Other source")
    # A different note with internally valid payload/manifest hashes is still not
    # the saved note frozen by the Run/edition owner.
    wire = receipt.model_dump(mode="json", by_alias=True)
    replaced_note = play_source_frame((payload(), payload("scene_note", text="Other saved note")))
    wire["play_sources"] = replaced_note.manifest.model_dump(mode="json", by_alias=True)
    with pytest.raises(ValueError, match="exact saved note"): seal_receipt(wire)


@pytest.mark.parametrize("field", ["world_id", "graph_revision", "retrieval_session_id"])
def test_execution_scope_must_equal_frozen_receipt_even_with_a_valid_new_policy_digest(field):
    receipt, execution, _ = fixture()
    values = execution.policy.model_dump(mode="json", by_alias=True)
    values["source_read_scope"][field] = "other"
    policy = NativePlayGraphPolicyV1.model_validate_json(json.dumps(values))
    changed = PlayWorldGraphExecutionV1(context_receipt_sha256=receipt.context_receipt_sha256,
        execution_policy_sha256=play_graph_execution_policy_digest(receipt.context_receipt_sha256, policy), policy=policy, events=[])
    with pytest.raises(ValueError, match="frozen receipt Graph scope"):
        validate_play_graph_execution_binding(receipt, changed)


def test_initial_anchors_cannot_introduce_evidence_absent_from_receipt_candidates():
    receipt, execution, _ = fixture()
    values = execution.policy.model_dump(mode="json", by_alias=True)
    values["source_read_scope"]["admitted_anchors"][0]["evidence_ref_id"] = "other"
    policy = NativePlayGraphPolicyV1.model_validate_json(json.dumps(values))
    changed = PlayWorldGraphExecutionV1(context_receipt_sha256=receipt.context_receipt_sha256,
        execution_policy_sha256=play_graph_execution_policy_digest(receipt.context_receipt_sha256, policy), policy=policy, events=[])
    with pytest.raises(ValueError): validate_play_graph_execution_binding(receipt, changed)


@pytest.mark.parametrize("change", [None, "native_world", "binding"])
def test_dynamic_extensions_bind_native_world_and_binding_version(change):
    receipt, execution, _ = fixture()
    scope = execution.policy.source_read_scope
    pin = scope.admitted_anchors[0]
    origin = ValidatedGraphOperationEventV3(event_id=uuid4(), sequence=0, kind="validated_graph_operation_v3",
        operation_id=uuid4(), operation="expand_graph_retrieval", request_arguments_sha256="a" * 64,
        graph_revision=scope.graph_revision, result_packet_sha256="b" * 64, assertion_ids=[], relationship_ids=[],
        evidence_ref_ids=[pin.evidence_ref_id], evidence_sufficiency_status="sufficient", coverage_status="complete",
        truncated=False, source_opened=False, returned_source_pins=[pin])
    extension = SourceScopeExtensionEventV3(event_id=uuid4(), sequence=1, kind="source_scope_extension_v3",
        origin_graph_event_id=origin.event_id, context_receipt_sha256=receipt.context_receipt_sha256,
        execution_policy_sha256=execution.execution_policy_sha256, world_id=scope.world_id,
        native_world_id="other" if change == "native_world" else receipt.graph_authority.native_world_id,
        binding_version=2 if change == "binding" else 1, campaign_id=None, graph_revision=scope.graph_revision,
        retrieval_session_id=scope.retrieval_session_id, pins=[pin])
    execution = native_events(execution, [origin, extension])
    if change is None: validate_play_graph_execution_binding(receipt, execution)
    else:
        with pytest.raises(ValueError, match="managed/native World"): validate_play_graph_execution_binding(receipt, execution)


@pytest.mark.parametrize("field,value", [("envelope_sha256", "f" * 64), ("input_tokens", 13),
    ("output_token_reserve", 11), ("input_estimator", "other"),
    ("included_assertion_ids", ["foreign"]), ("included_evidence_ref_ids", ["foreign"])])
def test_first_provider_must_equal_frozen_actual_envelope_and_admitted_ids(field, value):
    receipt, execution, _ = fixture()
    event = native_provider().model_copy(update={field:value})
    with pytest.raises(ValueError): validate_play_graph_provider_authorization(receipt, execution, event)
    # Historical joining also catches an otherwise structurally valid forged
    # first provider authorization, rather than skipping it after append.
    if field not in {"input_estimator"}:
        changed = native_events(execution, [event])
        with pytest.raises(ValueError): validate_play_graph_execution_binding(receipt, changed)


def test_second_provider_keeps_current_scope_and_context_window_without_reusing_first_hash():
    receipt, execution, _ = fixture()
    first = native_provider()
    execution = validate_play_graph_provider_authorization(receipt, execution, first)
    events = [*execution.events,
        ProviderOutcomeEventV1(event_id=uuid4(), sequence=1, kind="provider_outcome", provider_attempt_id=first.provider_attempt_id, outcome="sdk_entered"),
        ProviderOutcomeEventV1(event_id=uuid4(), sequence=2, kind="provider_outcome", provider_attempt_id=first.provider_attempt_id, outcome="response_received")]
    execution = native_events(execution, events)
    second = native_provider(3).model_copy(update={"envelope_sha256":"f" * 64, "included_assertion_ids":["assertion-one"]})
    assert len(validate_play_graph_provider_authorization(receipt, execution, second).events) == 4
    with pytest.raises(ValueError, match="context window"):
        validate_play_graph_provider_authorization(receipt, execution, second.model_copy(update={"input_tokens":1024}))


def test_native_related_corpus_recap_scope_is_validated_without_a_plan_subclass_gate():
    from tests.application_state.test_agent_conversation_service import _related_recap_admission_fixture
    receipt, execution, _ = fixture()
    wire = _related_recap_admission_fixture(evidence_ref_id="e0", target_id="assertion-one").model_dump(mode="json", by_alias=True)
    wire.update(managed_world_id="world-one", native_world_id="native-world-one", graph_revision="graph-one",
        descriptor_world_id="native-world-one", descriptor_graph_revision_id="graph-one")
    wire["provenance_result_sha256"] = related_recap_provenance_result_digest(managed_world_id=wire["managed_world_id"],
        native_world_id=wire["native_world_id"], binding_version=wire["binding_version"], graph_revision=wire["graph_revision"],
        target_kind=wire["target_kind"], target_id=wire["target_id"],
        provenance_bindings=_related_recap_admission_fixture(evidence_ref_id="e0", target_id="assertion-one").provenance_bindings)
    admission = RelatedRecapContextAdmissionV2.model_validate_json(json.dumps(wire))
    auth = RelatedRecapContextAuthorizationEventV2(event_id=uuid4(), sequence=0, kind="related_recap_context_authorized_v2",
        read_call_id=uuid4(), context_receipt_sha256=receipt.context_receipt_sha256,
        execution_policy_sha256=execution.execution_policy_sha256, admission=admission, max_chars=100)
    validate_play_graph_execution_binding(receipt, native_events(execution, [auth]))
    # Valid standalone admission for a different managed/native binding must fail
    # here even though this native execution is not a PlanWorldGraphExecutionV2.
    foreign = _related_recap_admission_fixture(evidence_ref_id="e0", target_id="assertion-one")
    with pytest.raises(ValueError, match="frozen turn authority"):
        validate_play_graph_execution_binding(receipt, native_events(execution, [auth.model_copy(update={"admission":foreign})]))



def test_empty_source_commitment_grants_no_prepared_text_and_rejects_inserting_a_frame_later():
    receipt, execution, frame = fixture()
    empty = play_source_frame(())
    wire = receipt.model_dump(mode="json", by_alias=True)
    wire["play_sources"] = empty.manifest.model_dump(mode="json", by_alias=True)
    receipt = seal_receipt(wire)
    validate_play_graph_source_frame(receipt, empty, owner_resolved_current_moment_text=None)
    with pytest.raises(ValueError, match="frozen receipt manifest"):
        validate_play_graph_source_frame(receipt, frame, owner_resolved_current_moment_text=MOMENT)


def test_execution_cannot_rebind_a_valid_ledger_to_another_receipt_hash():
    receipt, execution, _ = fixture()
    execution = PlayWorldGraphExecutionV1(context_receipt_sha256="f" * 64,
        execution_policy_sha256=play_graph_execution_policy_digest("f" * 64, execution.policy),
        policy=execution.policy, events=[])
    with pytest.raises(ValueError, match="frozen receipt Graph scope"):
        validate_play_graph_execution_binding(receipt, execution)
