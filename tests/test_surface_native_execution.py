"""Shared native component bindings, not APP admission or SDK/answer proof."""
from copy import deepcopy
from dataclasses import replace
from hashlib import sha256
import json
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from application_state.agent_conversation import types as t
from application_state.agent_conversation.build_intentional_response import Capabilities, MENU_DIGEST, RESOLVER_DIGEST
from application_state.agent_conversation.native_context import SurfaceNativeContextReceiptV1
from application_state.agent_conversation.native_execution import (
    NativeBuildActionV1, NativePlanActionV1, NativePlayActionV1,
    SurfaceNativeExecutionPolicyV1, SurfaceNativeExecutionV1, NativeWriterAuthorizedV1, validate_context_binding,
)
from application_state.build_proposal.types import BuildWriteCapability
from tests.test_surface_native_context import wire, seal, provenance_for
from tests.test_build_decision_context import constant
from tests.test_play_graph_authority import intent_wire


def component(surface="plan", *, unavailable=False):
    data = wire(surface, unavailable=unavailable)
    # Real Build/Plan SDK fixtures share the existing 128k test writer allowance.
    if surface in {"build", "plan", "play"}:
        data["assembled_input"]["context_window_limit"] = 128000
    if not unavailable:
        data["native_query"]["authority"].update(scope_mode="world", campaign_id=None)
    context = SurfaceNativeContextReceiptV1.model_validate_json(json.dumps(seal(data)))
    provenance=provenance_for(context.work_context).model_copy(update={'surface_instance_id':surface+':one'})
    data['provenance_sha256']=t.canonical_sha256(provenance)
    context=SurfaceNativeContextReceiptV1.model_validate_json(json.dumps(seal(data)))
    work = context.work_context
    common = dict(world_id="world-one", client_thread_id="thread-one", message="What did the check reveal?",
        surface_id=surface, surface_instance_id=surface+":one", client_work_state="saved_clean")
    if surface == "build":
        basis = work.source_basis
        intent = t.BuildGraphIntentV1(**common, primary_work=dict(kind="build", object_id=basis.document_id,
            expected_revision=basis.registry_revision, expected_content_sha256=basis.content_sha256),
            graph_request=dict(mode="world", world_id="world-one", focus=dict(kind="none")))
        action = NativeBuildActionV1(intent=intent, write_capability=None,
            capabilities=Capabilities(("answer_from_sources",)), related_page_catalog=None,
            saved_source_char_count=20, requested_work_menu_sha256=MENU_DIGEST,
            response_resolver_sha256=RESOLVER_DIGEST)
        mode = "typesafe_decision"
    elif surface == "plan":
        basis = work.plan_basis
        intent = t.SubmittedTurnIntentV2(**common, primary_work=dict(kind="plan", object_id=basis.document_id,
            expected_revision=basis.object_revision, expected_revision_n=basis.revision_n,
            expected_content_sha256=basis.content_sha256), plan_context_policy=work.plan_context_policy,
            graph_request=dict(mode="none"), graph_selection=None)
        action = NativePlanActionV1(intent=intent, authoring_capture=None, placement_catalog=None)
        mode = "decision"
    else:
        data = intent_wire()
        data.update(message=common["message"], surface_instance_id=common["surface_instance_id"])
        data["play_target"].update(beat_id=work.play_basis.beat_id, scene_id=work.play_basis.scene_id)
        intent = t.PlayGraphIntentV1.model_validate_json(json.dumps(data))
        action = NativePlayActionV1(intent=intent)
        mode = "decision"
    roles = t.GraphControllerWriterRolesV1(
        controller=t.GraphProviderRoleTargetV1(provider="typesafe", model="jev-1.14.0", api_mode=mode),
        writer=t.GraphProviderRoleTargetV1(provider="openai", model="gpt-6-luna", api_mode="responses"))
    accounting = t.GraphExecutionAccountingV1(kind="conservative_upper_bound", estimator="synthetic")
    budget = t.BuildWriterContextBudgetV1.model_validate(dict(schema="dmb_build_writer_context_budget_v1",
        provider="openai", model="gpt-6-luna", api_mode="responses", estimator="utf8_json_bytes_plus_64_per_node_v1",
        context_limit_tokens=128000, max_request_bytes=128000, output_reserve_tokens=4096)) if surface=="build" else None
    policy = SurfaceNativeExecutionPolicyV1(action=action,
        source_authority_sha256=t.canonical_sha256(context.source_authority),
        native_query_sha256=t.canonical_sha256(context.native_query), provider_roles=roles,
        provider_input_accounting=accounting, max_provider_attempts=None,
        max_total_provider_input_tokens=None,
        max_total_provider_output_tokens=None,
        controller_continuation_accounting=constant(1000).descriptor if surface=="build" else None,
        writer_context_budget=budget)
    return context, execution(context.context_receipt_sha256, policy)


def execution(context_sha, policy, events=()):
    data = dict(schema="dmb_surface_native_execution_v1", context_receipt_sha256=context_sha,
        policy=policy.model_dump(mode="json", by_alias=True))
    return SurfaceNativeExecutionV1.model_validate_json(json.dumps(data | {
        "execution_policy_sha256": t.canonical_sha256(data),
        "events": [e.model_dump(mode="json", by_alias=True) if hasattr(e, "model_dump") else e for e in events]}))


def controller(surface, policy, *, sequence=0, semantic=True):
    role = policy.provider_roles.controller
    fields = dict(event_id=uuid4(), sequence=sequence, provider_attempt_id=uuid4(),
        envelope_sha256="d"*64, serializer_version="typesafe-sdk-json-v1",
        provider=role.provider, model=role.model, api_mode=role.api_mode, tool_schema_sha256="e"*64,
        input_accounting_kind="conservative_upper_bound", input_estimator="synthetic", input_tokens=120,
        output_token_reserve=200, included_assertion_ids=[], included_relationship_ids=[],
        included_evidence_ref_ids=[], included_graph_event_ids=[], included_source_read_event_ids=[])
    if surface=="play":
        return t.NativeRetrievalAuthorizedV1(**fields,decision_request_id=uuid4(),parent_request_sha256="f"*64)
    if surface=="plan":
        cls=t.PlanRequestedWorkAuthorizedV2 if semantic else t.NativeRetrievalAuthorizedV1
        return cls(kind="plan_requested_work_authorized_v2" if semantic else "native_retrieval_authorized_v1", **fields,
            decision_request_id=uuid4(), parent_request_sha256="f"*64)
    from application_state.agent_conversation.build_decision_context import identity
    fields.update(input_accounting_kind="estimated_token_count", input_estimator=policy.controller_continuation_accounting.policy)
    context=dict(context_mode="default", context_phase="select" if semantic else "navigate", max_question_input_tokens=120,
        dispatch_identity_sha256=identity(envelope_sha256=fields["envelope_sha256"],
            provider=role.provider, model=role.model, api_mode=role.api_mode, context_mode="default"))
    if not semantic:
        return t.NativeRetrievalAuthorizedV1(**fields,decision_request_id=uuid4(),parent_request_sha256="f"*64,build_context=context)
    return t.ProviderAttemptAuthorizedEventV5(kind="provider_attempt_authorized_v5", **fields,**context)


def outcomes(provider,sequence):
    return [t.ProviderOutcomeEventV1(kind="provider_outcome",event_id=uuid4(),sequence=sequence+i,
        provider_attempt_id=provider.provider_attempt_id,outcome=value)
        for i,value in enumerate(("sdk_entered","response_received"))]


def choice(context,record,provider,sequence,operation,handles=()):
    return t.NativeRetrievalSelectedV1(kind="native_retrieval_selected_v1",event_id=uuid4(),sequence=sequence,
        context_receipt_sha256=context.context_receipt_sha256,execution_policy_sha256=record.execution_policy_sha256,
        decision_request_id=getattr(provider,"decision_request_id",uuid4()),controller_attempt_id=provider.provider_attempt_id,
        controller_envelope_sha256=provider.envelope_sha256,controller_response_sha256="f"*64,
        parent_request_sha256=getattr(provider,"parent_request_sha256","e"*64),operation=operation,
        selected_handles=list(handles))


BUILD_TURN_ID=UUID('b0000000-0000-4000-8000-000000000001')


def build_resolution(policy, provider, sequence, *, turn_id=BUILD_TURN_ID, attempt=1, requested='discuss'):
    from dataclasses import asdict
    from application_state.agent_conversation import build_intentional_response as semantic
    contract=semantic.resolution_for(policy,requested)
    request_id='select:'+('a'*64)
    return t.BuildRequestedWorkResolutionV1(kind='build_requested_work_resolved_v1',event_id=uuid4(),sequence=sequence,
        controller_attempt_id=provider.provider_attempt_id,controller_envelope_sha256=provider.envelope_sha256,
        controller_response_sha256='f'*64,machine_request_id=request_id,requested_work=requested,
        intent_family=contract['intent_family'],menu_sha256=semantic.MENU_DIGEST,resolver_sha256=semantic.RESOLVER_DIGEST,
        response_capabilities_sha256=semantic.digest(asdict(policy.action.capabilities)),resolution=contract,
        operation=contract['operation'],broker_operation_id=semantic.operation_id_for(turn_id,attempt,request_id,requested),
        capability_sha256=policy.action.intent.build_write_capability_sha256,
        arguments_sha256=semantic.digest({'instruction':policy.action.intent.message} if contract['operation']!='answer_from_sources' else {}))


def decision_prefix(surface,context,record):
    first=controller(surface,record.policy)
    events=[first,*outcomes(first,1)]
    if surface=="plan":
        events.append(t.PlanRequestedWorkSelectedV2(kind="plan_requested_work_selected_v2",event_id=uuid4(),sequence=3,
            context_receipt_sha256=context.context_receipt_sha256,execution_policy_sha256=record.execution_policy_sha256,
            decision_request_id=first.decision_request_id,controller_attempt_id=first.provider_attempt_id,
            controller_envelope_sha256=first.envelope_sha256,controller_response_sha256="f"*64,
            parent_request_sha256=first.parent_request_sha256,requested_work="discuss",original_capture_sha256=None,
            placement_catalog_sha256=None,placement_selector=None,original_capture=None,placement_catalog=None))
        active=controller(surface,record.policy,sequence=len(events),semantic=False)
        events.extend([active,*outcomes(active,len(events)+1)])
    else:
        if surface=='build':
            events.append(build_resolution(record.policy,first,len(events)))
            active=controller(surface,record.policy,sequence=len(events),semantic=False)
            events.extend([active,*outcomes(active,len(events)+1)])
        else:
            active=first
    return events,active


@pytest.mark.parametrize("surface", ["build", "plan", "play"])
@pytest.mark.parametrize("unavailable", [False, True])
def test_shared_native_component_roundtrip_uses_actual_closed_action_and_work(surface, unavailable):
    context, record = component(surface, unavailable=unavailable)
    validated = validate_context_binding(context, record)
    assert validated is not record
    assert validated.events is not record.events
    assert validated.model_dump_json(by_alias=True) == record.model_dump_json(by_alias=True)
    reopened = type(record).model_validate_json(record.model_dump_json(by_alias=True))
    assert reopened == record
    assert reopened.policy.action.intent == record.policy.action.intent
    assert not {"source_read_scope", "allowed_graph_operations", "max_graph_operations", "source_opened"} & set(
        record.policy.model_dump())


@pytest.mark.parametrize("surface", ["build", "plan", "play"])
def test_actual_initial_provider_accounting_is_shared_without_projection(surface):
    context, record = component(surface)
    event = controller(surface, record.policy)
    data = context.model_dump(mode="json", by_alias=True)
    data["assembled_input"].update(provider_model_name=event.model, provider_model_version=event.model,
        tokenizer_name=event.input_estimator)
    context = type(context).model_validate_json(json.dumps(seal(data)))
    record = execution(context.context_receipt_sha256, record.policy, [event])
    validate_context_binding(context, record)
    assert type(record.events[0]) is type(event)
    assert record.events[0].model_dump_json() == event.model_dump_json()
    altered = context.model_dump(mode="json", by_alias=True)
    altered["assembled_input"]["assembled_input_sha256"] = "c"*64
    altered = type(context).model_validate_json(json.dumps(seal(altered)))
    with pytest.raises(ValueError, match="first provider"):
        validate_context_binding(altered, execution(altered.context_receipt_sha256, record.policy, [event]))


@pytest.mark.parametrize("surface", ["build", "plan", "play"])
def test_native_component_does_not_authorize_classic_event_or_exposure(surface):
    context, record = component(surface)
    with pytest.raises(ValidationError):
        execution(context.context_receipt_sha256, record.policy, [{"kind":"validated_graph_operation_v3"}])
    event = controller(surface, record.policy).model_copy(update={"included_graph_event_ids":[uuid4()]})
    with pytest.raises(ValueError, match="absent classic"):
        execution(context.context_receipt_sha256, record.policy, [event])


@pytest.mark.parametrize("surface,field,value", [("build","registry_revision",9),
    ("plan","revision_n",9), ("play","scene_id","scene:other")])
def test_fully_rehashed_component_cannot_substitute_actual_surface_work(surface, field, value):
    context, record = component(surface)
    data = context.model_dump(mode="json", by_alias=True)
    basis = {"build":"source_basis", "plan":"plan_basis", "play":"play_basis"}[surface]
    data["work_context"][basis][field] = value
    altered = type(context).model_validate_json(json.dumps(seal(data)))
    with pytest.raises(ValueError):
        validate_context_binding(altered, execution(altered.context_receipt_sha256, record.policy))


@pytest.mark.parametrize("field", ["source_authority_sha256", "native_query_sha256"])
def test_rehashed_policy_cannot_replace_its_native_authority_component(field):
    context, record = component()
    policy = record.policy.model_copy(update={field:"b"*64})
    with pytest.raises(ValueError, match="commitments differ"):
        validate_context_binding(context, execution(context.context_receipt_sha256, policy))


def test_rehashed_query_cannot_replace_the_unchanged_question():
    context, record = component()
    data = context.model_dump(mode="json", by_alias=True)
    data["native_query"]["question"] = "A substituted question"
    altered = type(context).model_validate_json(json.dumps(seal(data)))
    policy = record.policy.model_copy(update={"native_query_sha256":t.canonical_sha256(altered.native_query)})
    with pytest.raises(ValueError, match="unchanged submitted"):
        validate_context_binding(altered, execution(altered.context_receipt_sha256, policy))


def test_build_captured_capabilities_preserve_uncaptured_and_empty_catalog():
    context, record = component("build")
    action = record.policy.action
    empty = NativeBuildActionV1.model_validate_json(action.model_dump_json().replace('"related_page_catalog":null', '"related_page_catalog":[]'))
    assert action.related_page_catalog is None and empty.related_page_catalog == ()
    assert t.canonical_sha256(action) != t.canonical_sha256(empty)
    data = action.model_dump(mode="json", by_alias=True)
    data["capabilities"]["plan_surface"] = "true"
    with pytest.raises(ValueError):
        NativeBuildActionV1.model_validate_json(json.dumps(data))
    assert action.capabilities.reviews is None
    assert replace(action.capabilities, reviews=()).reviews == ()


def test_real_editor_capability_has_one_owner_and_exact_hash_scope():
    from apps.live_control_server.models.build_document_proposal import BuildWriteCapability as HTTP
    assert HTTP is BuildWriteCapability
    context, record = component("build")
    action = record.policy.action
    cap = BuildWriteCapability(idempotency_key=uuid4(), conversation_id=uuid4(), expected_pointer_revision=1,
        basis=dict(world_id="world-one", document_id="page-one", registry_revision=3,
            content_sha256="a"*64, visibility="internal", draft_sha256=sha256(b"draft").hexdigest(),
            editor_sha256="b"*64, caret=0, draft_generation=0, selection_generation=0), draft_markdown="draft")
    data = action.model_dump(mode="json", by_alias=True)
    data["intent"]["build_write_capability_sha256"] = t.canonical_sha256(cap.model_dump(mode="json"))
    data["write_capability"] = cap.model_dump(mode="json", by_alias=True)
    data["capabilities"]["operations"].append("propose_build_insertion")
    captured = NativeBuildActionV1.model_validate_json(json.dumps(data))
    assert captured.write_capability == cap
    tampered = deepcopy(data)
    tampered["write_capability"]["basis"]["registry_revision"] = 8
    with pytest.raises(ValueError):
        NativeBuildActionV1.model_validate_json(json.dumps(tampered))
    tampered = deepcopy(data)
    tampered["capabilities"]["operations"].remove("propose_build_insertion")
    with pytest.raises(ValueError, match="Offered writing"):
        NativeBuildActionV1.model_validate_json(json.dumps(tampered))


def test_play_uses_actual_jev_and_writer_roles_without_application_limits():
    context,record=component('play')
    assert record.policy.provider_roles.controller.identity()==('typesafe','jev-1.14.0','decision')
    assert record.policy.provider_roles.writer.identity()==('openai','gpt-6-luna','responses')
    for field in ('max_provider_attempts','max_total_provider_input_tokens','max_total_provider_output_tokens'):
        with pytest.raises(ValueError,match='provider-owned'):
            execution(context.context_receipt_sha256,record.policy.model_copy(update={field:4}))
    wrong=record.policy.model_copy(update={'provider_roles':record.policy.provider_roles.writer})
    with pytest.raises(ValueError):
        execution(context.context_receipt_sha256,wrong)


def test_rehashed_query_cannot_narrow_world_request_to_a_campaign():
    context, record = component()
    data = context.model_dump(mode="json", by_alias=True)
    data["native_query"]["authority"].update(scope_mode="campaign", campaign_id="campaign-one")
    altered = type(context).model_validate_json(json.dumps(seal(data)))
    policy = record.policy.model_copy(update={"native_query_sha256":t.canonical_sha256(altered.native_query)})
    with pytest.raises(ValueError, match="submitted World question"):
        validate_context_binding(altered, execution(altered.context_receipt_sha256, policy))


def native_writer(surface,policy,*,sequence,read_ids=()):
    role = policy.provider_roles.writer
    return NativeWriterAuthorizedV1(event_id=uuid4(), sequence=sequence, provider_attempt_id=uuid4(),
        envelope_sha256="b"*64, serializer_version="openai-sdk-json-v1", provider=role.provider,
        model=role.model, api_mode=role.api_mode, tool_schema_sha256="c"*64,
        input_accounting_kind="conservative_upper_bound", input_estimator="synthetic",
        input_tokens=10, output_token_reserve=4096 if surface=="build" else 200,
        included_assertion_ids=[], included_relationship_ids=[], included_evidence_ref_ids=[],
        included_graph_event_ids=[], included_source_read_event_ids=[], frame_sha256="f"*64,
        native_read_event_ids=read_ids)


@pytest.mark.parametrize("surface", ["build", "plan"])
def test_native_writer_has_one_shared_exact_inclusion_contract(surface):
    context, record = component(surface)
    first = controller(surface, record.policy)
    data=context.model_dump(mode="json",by_alias=True)
    data["assembled_input"]["tokenizer_name"]=first.input_estimator
    context=type(context).model_validate_json(json.dumps(seal(data)))
    record=execution(context.context_receipt_sha256,record.policy)
    prefix,active=decision_prefix(surface,context,record)
    prefix.append(choice(context,record,active,len(prefix),"finish_retrieval"))
    writer = native_writer(surface,record.policy,sequence=len(prefix))
    accepted=execution(context.context_receipt_sha256, record.policy, [*prefix,writer])
    validate_context_binding(context,accepted)
    assert type(accepted.events[-1]) is NativeWriterAuthorizedV1
    assert not hasattr(accepted.events[-1],"native_statement_read_event_ids")
    with pytest.raises(ValueError,match="exact settled read inclusion"):
        execution(context.context_receipt_sha256,record.policy,[*prefix,
            writer.model_copy(update={"native_read_event_ids":(uuid4(),)})])
    generic=writer.model_dump(exclude={"frame_sha256","native_read_event_ids"})
    generic["kind"]="provider_attempt_authorized_v3"
    with pytest.raises(ValueError,match="shared selected-read inclusion"):
        execution(context.context_receipt_sha256,record.policy,[*prefix,
            t.ProviderAttemptAuthorizedEventV3.model_validate(generic)])
    with pytest.raises(ValueError):
        execution(context.context_receipt_sha256,record.policy,[*prefix,
            writer.model_copy(update={"native_read_event_ids":(first.event_id,first.event_id)})])


def test_new_native_root_cannot_retain_a_second_body_inclusion_manifest():
    context,record=component()
    with pytest.raises(ValidationError):
        execution(context.context_receipt_sha256,record.policy,[dict(kind="native_body_provider_included_v1")])


@pytest.mark.parametrize("surface", ["build", "plan"])
def test_shared_writer_retains_unavailable_native_read_settlement(surface):
    from application_state.agent_conversation.native_plan_assertions import selection_handle
    context,record=component(surface)
    first=controller(surface,record.policy)
    data=context.model_dump(mode="json",by_alias=True)
    data["assembled_input"]["tokenizer_name"]=first.input_estimator
    data["native_query"].update(discovered_entity_ids=["entity-one"],assertion_matches=[dict(
        assertion_id="assertion-one",subject_entity_id="entity-one",discovered_entity_ids=["entity-one"],
        assertion_sha256="a"*64,label="Discovered assertion")])
    context=type(context).model_validate_json(json.dumps(seal(data)))
    policy=record.policy.model_copy(update={"native_query_sha256":t.canonical_sha256(context.native_query)})
    record=execution(context.context_receipt_sha256,policy)
    prefix,active=decision_prefix(surface,context,record)
    prefix.append(choice(context,record,active,len(prefix),"select_candidates",
        [selection_handle(context.native_query,context.native_query.assertion_matches[0])]))
    grant=t.NativePlanAssertionReadAuthorizedV1(event_id=uuid4(),sequence=len(prefix),
        provider_attempt_id=active.provider_attempt_id,query_sha256=context.native_query.sha256,
        assertion_ids=("assertion-one",))
    prefix.append(grant)
    observed=t.NativePlanAssertionReadObservedV1(event_id=uuid4(),sequence=len(prefix),
        authorization_event_id=grant.event_id,reads=(),unavailable_assertion_ids=("assertion-one",),status="partial")
    prefix.append(observed)
    unsettled=prefix[:-1]
    finish=controller(surface,policy,sequence=len(prefix),semantic=False)
    prefix.extend([finish,*outcomes(finish,len(prefix)+1)])
    prefix.append(choice(context,record,finish,len(prefix),"finish_retrieval"))
    writer=native_writer(surface,policy,sequence=len(prefix),read_ids=(observed.event_id,))
    accepted=execution(context.context_receipt_sha256,policy,[*prefix,writer])
    validate_context_binding(context,accepted)
    # A failed read remains visible to the writer but cannot invent support.
    assert next(e for e in accepted.events if e.event_id==observed.event_id).reads==()
    assert accepted.events[-1].native_read_event_ids==(observed.event_id,)
    with pytest.raises(ValueError,match="exact settled read inclusion"):
        execution(context.context_receipt_sha256,policy,[*prefix,writer.model_copy(update={"native_read_event_ids":()})])
    with pytest.raises(ValueError,match="every selected read grant|explicit completed retrieval finish"):
        missing=execution(context.context_receipt_sha256,policy,[*unsettled,
            native_writer(surface,policy,sequence=len(unsettled))])
        validate_context_binding(context,missing)


def test_play_writer_cannot_smuggle_unknown_reads_in_shared_writer_codec():
    context,record=component("play")
    shared=native_writer("play",record.policy,sequence=0,read_ids=(uuid4(),))
    with pytest.raises(ValueError,match="exact settled read inclusion"):
        execution(context.context_receipt_sha256,record.policy,[shared])


@pytest.mark.parametrize("mutation",["no_destination","no_finish","scope","request","response","second_destination","controller_after_finish"])
def test_native_plan_uses_existing_owner_phase_checks(mutation):
    context,record=component("plan")
    prefix,active=decision_prefix("plan",context,record)
    finish=choice(context,record,active,len(prefix),"finish_retrieval")
    events=[*prefix,finish,native_writer("plan",record.policy,sequence=len(prefix)+1)]
    if mutation=="no_destination":
        events=[controller("plan",record.policy,semantic=False)]
    elif mutation=="no_finish":
        events=[*prefix,native_writer("plan",record.policy,sequence=len(prefix))]
    elif mutation in {"scope","request","response"}:
        field={"scope":"context_receipt_sha256","request":"parent_request_sha256","response":"controller_attempt_id"}[mutation]
        events[-2]=finish.model_copy(update={field:uuid4() if mutation=="response" else "a"*64})
    elif mutation=="second_destination":
        events=[*prefix,controller("plan",record.policy,sequence=len(prefix))]
    else:
        events=[*prefix,finish,controller("plan",record.policy,sequence=len(prefix)+1,semantic=False)]
    with pytest.raises(ValueError):
        execution(context.context_receipt_sha256,record.policy,events)


@pytest.mark.parametrize("retrieval", ["never", "unfinished", "finished"])
def test_build_auxiliary_controller_preserves_retrieval_finish_barrier(retrieval):
    context, record = component("build")
    first = controller("build", record.policy)
    events = [first, *outcomes(first, 1)]
    events.append(build_resolution(record.policy, first, len(events)))
    if retrieval != "never":
        active = controller("build", record.policy, sequence=len(events), semantic=False)
        events.extend([active, *outcomes(active, len(events) + 1)])
        events.append(choice(context, record, active, len(events),
            "finish_retrieval" if retrieval == "finished" else "select_candidates",
            () if retrieval == "finished" else ("statement:synthetic",)))
    auxiliary = controller("build", record.policy, sequence=len(events)).model_copy(
        update={"context_phase": "writer_selection"})
    events.extend([auxiliary, *outcomes(auxiliary, len(events) + 1)])
    events.append(native_writer("build", record.policy, sequence=len(events)))
    if retrieval == "unfinished":
        with pytest.raises(ValueError, match="unfinished native retrieval"):
            execution(context.context_receipt_sha256, record.policy, events)
    else:
        accepted = execution(context.context_receipt_sha256, record.policy, events)
        assert type(accepted.events[-1]) is NativeWriterAuthorizedV1
        if retrieval == "finished":
            resumed = controller("build", record.policy,
                sequence=len(events) - 1, semantic=False)
            with pytest.raises(ValueError, match="cannot resume"):
                execution(context.context_receipt_sha256, record.policy,
                    [*events[:-1], resumed])


@pytest.mark.parametrize("family",["search","body","statement","assertion"])
def test_native_plan_cannot_finish_with_pending_native_grant(family):
    # Isolate the phase owner's pending state. Native read owners separately
    # validate exact grant/capture identity and source bytes.
    from application_state.agent_conversation.native_retrieval import validate_decision_phases
    context,record=component("plan")
    prefix,active=decision_prefix("plan",context,record)
    prefix.append(choice(context,record,active,len(prefix),"select_candidates",["selected:synthetic"]))
    fields=dict(event_id=uuid4(),sequence=len(prefix),provider_attempt_id=active.provider_attempt_id)
    if family=="search":
        grant=t.NativeBodySearchAuthorizedV1(**fields,context_receipt_sha256=context.context_receipt_sha256,
            execution_policy_sha256=record.execution_policy_sha256,authority=context.source_authority,query_sha256="b"*64)
    elif family=="body":
        grant=t.NativeBodyReadAuthorizedV1(**fields,search_event_id=uuid4(),catalog_sha256="b"*64,
            retrieval_kind="section",section_id="section:one")
    elif family=="statement":
        grant=t.NativePlanStatementReadAuthorizedV1(**fields,query_sha256="b"*64,statement_ids=("statement-one",))
    else:
        grant=t.NativePlanAssertionReadAuthorizedV1(**fields,query_sha256="b"*64,assertion_ids=("assertion-one",))
    prefix.append(grant)
    last=controller("plan",record.policy,sequence=len(prefix),semantic=False)
    prefix.extend([last,*outcomes(last,len(prefix)+1)])
    prefix.append(choice(context,record,last,len(prefix),"finish_retrieval"))
    with pytest.raises(ValueError,match="unresolved source read"):
        validate_decision_phases(record.model_copy(update={"events":prefix}))


def test_retained_history_keeps_event_and_provider_budget_limits():
    context, record = component('plan')
    event = controller('plan', record.policy)
    with pytest.raises(ValidationError, match='at most 2048'):
        execution(context.context_receipt_sha256, record.policy, [event] * 2049)
    policy = record.policy.model_copy(update={'max_total_provider_input_tokens': event.input_tokens - 1})
    with pytest.raises(ValueError, match='provider token budget exceeded'):
        execution(context.context_receipt_sha256, policy, [event])


def test_build_capabilities_reconstruct_fresh_python_data_without_wire_change():
    context, record = component("build")
    original = record.model_dump(mode="json", by_alias=True)
    fresh = SurfaceNativeExecutionV1.model_validate(record.model_dump(mode="python", by_alias=True))
    assert fresh.model_dump(mode="json", by_alias=True) == original
    assert fresh.policy.action.capabilities is not record.policy.action.capabilities
    assert validate_context_binding(context, record).model_dump(mode="json", by_alias=True) == original


@pytest.mark.parametrize("field,value", [
    ("operations", ["answer_from_sources"]),
    ("operations", ("answer_from_sources", "answer_from_sources")),
    ("operations", ("answer_from_sources", "foreign_operation")),
    ("operations", ("answer_from_sources", {})),
    ("reviews", ["questions"]),
    ("plan_surface", "false"),
    ("author_save", 1),
    ("unknown_capability", True),
])
def test_python_capability_reconstruction_preserves_strict_refusals(field, value):
    from pydantic import ValidationError
    _, record = component("build")
    data = record.policy.action.model_dump(mode="python", by_alias=True)
    data["capabilities"][field] = value
    with pytest.raises(ValidationError):
        NativeBuildActionV1.model_validate(data)


def test_mutated_existing_capability_is_reconstructed_before_binding():
    from pydantic import ValidationError
    context, record = component("build")
    object.__setattr__(record.policy.action.capabilities, "operations",
                       ("answer_from_sources", "foreign_operation"))
    with pytest.raises(ValidationError):
        validate_context_binding(context, record)


@pytest.mark.parametrize("field,value", [
    ("plan_surface", "false"), ("author_save", 1),
    ("operations", ["answer_from_sources", "foreign_operation"]),
    ("operations", ["answer_from_sources", {}]),
    ("unknown_capability", True),
])
def test_json_capability_reconstruction_keeps_existing_invalid_wire_refusals(field, value):
    from pydantic import ValidationError
    _, record = component("build")
    data = record.policy.action.model_dump(mode="json", by_alias=True)
    data["capabilities"][field] = value
    with pytest.raises(ValidationError):
        NativeBuildActionV1.model_validate_json(json.dumps(data))


# Current related authored pages reuse the native selection and exact quote owner.
def related_plan_case():
    from application_state.agent_conversation.native_execution import NativePlanActionV2
    from application_state.agent_conversation import build_related_pages as related
    from tests.test_surface_native_work_input import work_case
    from tests.test_surface_native_execution import controller, outcomes, choice
    context, old, work = work_case('plan', draft=False)
    page = related.PagePointer(world_id=work['world_id'],document_id=uuid4(),
        registry_revision=3,title='Edge',visibility='internal')
    action = NativePlanActionV2(**old.policy.action.model_dump(mode='python',by_alias=True),related_page_catalog=(page,))
    root = execution(context.context_receipt_sha256,old.policy.model_copy(update={'action':action}))
    events = [e.model_copy(update={'execution_policy_sha256':root.execution_policy_sha256})
        if hasattr(e,'execution_policy_sha256') else e for e in old.events[:-1]]
    active = next(e for e in reversed(events) if isinstance(e,t.ProviderAttemptAuthorizedEventV1))
    selected = choice(context,root,active,len(events),'select_candidates',(related.plan_handle(page),))
    events.append(selected)
    body = '# Edge\n\nThe old bath house stands by the east gate. 🌿\n'
    read = related.RelatedPageRead(event_id=uuid4(),sequence=len(events),read_id=uuid4(),
        selection_event_id=selected.event_id,page=related.PageReference(**page.model_dump(),
            content_sha256=sha256(body.encode()).hexdigest()),markdown=body)
    events.append(read)
    active = controller('plan',root.policy,sequence=len(events),semantic=False)
    events.extend([active,*outcomes(active,len(events)+1)])
    events.append(choice(context,root,active,len(events),'finish_retrieval'))
    return context,execution(context.context_receipt_sha256,root.policy,events),work,read


def test_current_plan_saved_page_uses_local_writer_selector_and_exact_quote_owner():
    from application_state.agent_conversation.native_plan_work_view import semantic_frame
    from application_state.agent_conversation.native_writer import verify_input_records
    from application_state.agent_conversation.native_completion import normalize_output
    from tests.test_surface_native_work_input import produce
    from tests.test_surface_native_completion import answer
    context,record,work,read=related_plan_case()
    def project(value):
        view=semantic_frame(value,record);value.clear();value.update(view)
    candidate=answer([dict(kind='related_page_claim',text='The saved Edge page places the bath house by the east gate.',
        read_id='page0',supporting_quotes=['The old bath house stands by the east gate. 🌿'])])
    stored,auth,proof,host=produce(context,record,work,mutate=project,candidate=candidate)
    evidence=verify_input_records(context,stored,auth,proof['prepared_request_json'],**work)
    wire=json.loads(proof['prepared_request_json'])
    body=next(json.loads(m['content']) for m in wire['input'] if 'related_authored_pages' in m['content'])
    assert body['related_authored_pages']['pages']==[dict(read_id='page0',title='Edge',markdown=read.markdown)]
    assert str(read.read_id) not in json.dumps(body)
    assert str(read.page.document_id) not in json.dumps(body)
    assert evidence.related_pages==(read,)
    completion=normalize_output(context,stored,auth,**proof)
    assert completion.surface_id=='plan' and completion.answer_context_status=='authored_grounded'
    assert completion.answer_segments[0].read_id==read.read_id
    assert completion.answer_segments[0].page==read.page
    assert completion.collaboration is None


@pytest.mark.parametrize('mutation',['foreign_world','duplicate','hybrid','version','missing_catalog'])
def test_saved_plan_action_rejects_foreign_and_ambiguous_catalogues(mutation):
    from application_state.agent_conversation.native_execution import SurfaceNativeExecutionPolicyV1
    context,record,work,read=related_plan_case()
    raw=record.model_dump(mode='json',by_alias=True)
    action=raw['policy']['action']
    if mutation=='foreign_world':action['related_page_catalog'][0]['world_id']='foreign'
    elif mutation=='duplicate':action['related_page_catalog']*=2
    elif mutation=='hybrid':action.pop('action_version')
    elif mutation=='version':action['action_version']='unknown'
    else:action.pop('related_page_catalog')
    with pytest.raises(ValueError):SurfaceNativeExecutionPolicyV1.model_validate_json(json.dumps(raw['policy']))


@pytest.mark.parametrize('mutation',['unselected','selection','foreign_revision','wrong_world','duplicate','post_writer_selection','write_current_page'])
def test_plan_related_read_cannot_escape_its_current_native_selection(mutation):
    context,record,work,read=related_plan_case()
    events=list(record.events)
    index=read.sequence
    if mutation=='unselected':events[index-1]=events[index-1].model_copy(update={'selected_handles':['node:unrelated']})
    elif mutation=='selection':events[index]=read.model_copy(update={'selection_event_id':uuid4()})
    elif mutation=='foreign_revision':events[index]=read.model_copy(update={'page':read.page.model_copy(update={'registry_revision':4})})
    elif mutation=='wrong_world':events[index]=read.model_copy(update={'page':read.page.model_copy(update={'world_id':'foreign'})})
    elif mutation=='duplicate':events.insert(index+1,read.model_copy(update={'event_id':uuid4()}))
    elif mutation=='post_writer_selection':
        # A later retrieval decision does not retroactively authorize this read.
        events[index]=read.model_copy(update={'selection_event_id':events[-1].event_id})
    else:events[3]=events[3].model_copy(update={'requested_work':'write_current_page'})
    with pytest.raises(ValueError):execution(context.context_receipt_sha256,record.policy,
        [e.model_copy(update={'sequence':i}) for i,e in enumerate(events)])


@pytest.mark.parametrize('read_id,quotes',[('page0',['A fabricated quote.']),('page1',['The old bath house stands by the east gate. 🌿'])])
def test_plan_related_claim_cannot_borrow_another_page_or_quote(read_id,quotes):
    from application_state.agent_conversation.native_plan_work_view import semantic_frame
    from application_state.agent_conversation.native_completion import normalize_output
    from tests.test_surface_native_work_input import produce
    from tests.test_surface_native_completion import answer
    context,record,work,read=related_plan_case()
    def project(value):
        view=semantic_frame(value,record);value.clear();value.update(view)
    candidate=answer([dict(kind='related_page_claim',text='A claim.',read_id=read_id,supporting_quotes=quotes)])
    stored,auth,proof,_=produce(context,record,work,mutate=project,candidate=candidate)
    with pytest.raises(ValueError):normalize_output(context,stored,auth,**proof)


def test_old_plan_action_remains_a_closed_reader_and_current_producer_is_explicit_v2():
    from application_state.agent_conversation.native_execution import NativePlanActionV1, NativePlanActionV2
    from tests.test_surface_native_execution import component
    context,old=component('plan')
    reopened=type(old).model_validate_json(old.model_dump_json(by_alias=True))
    assert type(reopened.policy.action) is NativePlanActionV1
    assert 'action_version' not in reopened.policy.action.model_dump(mode='json',by_alias=True)
    context,current,work,read=related_plan_case()
    reopened=type(current).model_validate_json(current.model_dump_json(by_alias=True))
    assert type(reopened.policy.action) is NativePlanActionV2
    assert reopened.policy.action.action_version=='plan_saved_authored_pages_v2'
