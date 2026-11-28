"""Trusted Plan source composition; the existing Jev harness owns execution.

This module creates no request runner and opens no document body. Its output is
host-only authority for the existing claim/authorization and navigation owners.
"""
from contextlib import ExitStack
from dataclasses import replace
from hashlib import sha256
from functools import lru_cache
import json

from application_state.agent_conversation import types as t
from application_state.agent_conversation.plan_source_context import validate_source_execution_binding
from ..integrations.dungeonmind.native_corpus_source import (
    NativeSourceHeadUnavailable, prepare_native_source_context,
    turn_parsed_revision_cache, turn_source_repository,
)


def prepare(managed_world_id, principal, *, revision_id=None, repository=None, resolve_identity=None):
    """Resolve source ownership before optional Graph bootstrap, without body IO.

    Absence of a head is an explicit unavailable capability. Authorization,
    descriptor, binding and integrity failures are not empty search results.
    """
    if principal is None or principal.role != "gm":
        raise ValueError("GM authority is required for Plan source inspection")
    parsed_cache = None
    if repository is None:
        repository = turn_source_repository()
        parsed_cache = turn_parsed_revision_cache
    try:
        context = prepare_native_source_context(
            managed_world_id=managed_world_id, principal=principal,
            revision_id=revision_id, repository=repository,
            resolve_identity=resolve_identity, parsed_cache=parsed_cache,
        )
    except NativeSourceHeadUnavailable:
        return None, t.NativeCorpusUnavailableV1(managed_world_id=managed_world_id,
            failure_code="native_source_head_unavailable")
    return context, context.authority


@lru_cache(maxsize=1)
def _selective_plan_fact_cache():
    from dungeonmind.infrastructure.postgres.selective_query import SelectiveFactCache

    return SelectiveFactCache()


def prepare_selective_query(managed_world_id, principal, resolve_query, *,
                            revision_id=None, phase, repository=None, resolve_identity=None):
    """Compose source authority and Graph query before releasing the Core scope."""
    from dungeonmind.application.vnext import open_native_text_source_access_context
    from dungeonmind.application.vnext.admission import AlwaysAdmitPolicy
    from dungeonmind.infrastructure.postgres.selective_query import open_selective_source_query
    from graph_memory.vnext.domain_runtime import (
        DUNGEONBUDDY_POLICY_ID, DungeonBuddyVNextProjectionInput,
        build_dungeonbuddy_projection_request, resolve_dungeonbuddy_descriptors,
    )

    def resolve_descriptors(domain_ref, profile_ref):
        return resolve_dungeonbuddy_descriptors(domain_ref=domain_ref, profile_ref=profile_ref)

    def open_access(*, repository, space_id, revision_id, audience_labels, domain_contract, **_):
        nonlocal reader
        projection = DungeonBuddyVNextProjectionInput(
            world_id=space_id, revision_id=revision_id, role=principal.role, scope_mode='world',
        )
        opened = stack.enter_context(open_selective_source_query(
            repository,
            request=build_dungeonbuddy_projection_request(projection),
            resolve_descriptors=resolve_descriptors,
            domain_policy=AlwaysAdmitPolicy(policy_id=DUNGEONBUDDY_POLICY_ID),
            source_audience_labels=audience_labels,
            fact_cache=_selective_plan_fact_cache(),
        ))
        if opened is None:
            stack.close()
            return open_native_text_source_access_context(
                repository=repository, space_id=space_id, revision_id=revision_id,
                domain_contract=domain_contract, audience_labels=audience_labels,
                parsed_cache=turn_parsed_revision_cache, prefer_verified_source_rows=True,
            )
        source, reader = opened
        return source

    reader = None
    with ExitStack() as stack:
        try:
            with phase("plan_native_source_authority"):
                prepared = prepare_native_source_context(
                    managed_world_id=managed_world_id, principal=principal, revision_id=revision_id,
                    repository=repository if repository is not None else turn_source_repository(),
                    resolve_identity=resolve_identity, open_access=open_access,
                )
        except NativeSourceHeadUnavailable:
            return None
        with phase("plan_native_statement_query"):
            query_context, query = resolve_query(replace(prepared, selective_query=reader))
    return prepared, prepared.authority, query_context, query


def _plan_basis(work):
    basis = work.content_basis
    return t.PlanAskContextBasis(world_id=basis.world_id, document_id=basis.document_id,
        object_revision=basis.object_revision, work_revision_id=basis.work_revision_id,
        revision_n=basis.revision_n, content_sha256=basis.content_sha256)


def _contextual_document_title(basis, composed_capture=None):
    """Read metadata only when it still belongs to this exact captured basis."""
    from application_state.content.service import get_plan, snapshot_plan
    from application_state.errors import ApplicationStateConflictError
    if composed_capture is not None:
        snapshot = snapshot_plan(str(basis.document_id))
        obj = snapshot.work_object
        if (
            snapshot.page_presentation is None
            or snapshot.page_presentation.fingerprint() != composed_capture.base_page_presentation_sha256
            or snapshot.content_sha256 != basis.content_sha256
            or snapshot.from_working_copy
        ):
            raise ApplicationStateConflictError('Plan layout changed before composed request admission')
    else:
        obj = get_plan(str(basis.document_id))
    if (str(obj.work_object_id) != str(basis.document_id)
            or obj.world_id != basis.world_id or obj.status != 'active'
            or obj.object_revision != basis.object_revision
            or str(obj.current_revision_id) != str(basis.work_revision_id)):
        raise ApplicationStateConflictError('Plan metadata changed before contextual request admission')
    return obj.title


def _native_plan_parts(request, basis, playable_target, submitted_intent):
    from application_state.agent_conversation.native_context import PlanWorkContextV1
    from application_state.agent_conversation.native_execution import NativePlanActionV2, NativePlanActionV3
    from application_state.agent_conversation.plan_placement import PlanPlacementCatalogV2
    from application_state.agent_conversation.plan_composed_targeting import ComposedPlanPlacementCatalogV1
    from .build_related_pages import discover
    composed = type(request.plan_placement_catalog) is ComposedPlanPlacementCatalogV1
    contextual_capture = composed or (type(request.plan_placement_catalog) is PlanPlacementCatalogV2
        and request.plan_authoring_capture.target_kind in {'insert_at_caret', 'replace_selection'})
    action_type = NativePlanActionV3 if contextual_capture else NativePlanActionV2
    contextual = {}
    if composed:
        contextual["document_title"] = _contextual_document_title(
            basis, request.plan_authoring_capture,
        )
    elif contextual_capture:
        contextual["document_title"] = _contextual_document_title(basis)
    return (PlanWorkContextV1(plan_basis=basis, plan_context_policy=request.plan_context_policy,
            playable_target=playable_target),
        action_type(intent=submitted_intent, authoring_capture=request.plan_authoring_capture,
            placement_catalog=request.plan_placement_catalog, related_page_catalog=discover(request), **contextual))


def freeze_plan_request(request, work, playable_target, budget, *, authority, native_query,
        provenance, submitted_intent, dialogue):
    """Admit a real governed request; no provider input exists at this boundary."""
    from application_state.agent_conversation.native_context import NativePlanRequestAdmissionV1
    from application_state.agent_conversation.native_plan_opening import request_manifest, opening_dialogue_sha256
    if (request.surface.surface_id != 'plan' or type(request.plan_context_policy) is not t.PlanContextPolicyV2
            or work.content_basis is None or native_query is None
            or authority.managed_world_id != work.content_basis.world_id):
        raise ValueError('Plan request admission requires its actual native World request and work')
    work_context, action = _native_plan_parts(request, _plan_basis(work), playable_target, submitted_intent)
    roles = t.GraphControllerWriterRolesV1.model_validate(budget['providerRoles'])
    accounting = t.GraphExecutionAccountingV1(kind='conservative_upper_bound', estimator=budget['estimator'])
    # Pure request-manifest sealing, never a placeholder provider envelope.
    admission = NativePlanRequestAdmissionV1(manifest_sha256='0' * 64,
        submitted_intent_sha256=t.canonical_sha256(action.intent), dialogue_sha256=opening_dialogue_sha256(dialogue),
        tokenizer_name=budget['estimator'], tokenizer_version='v1',
        output_token_reserve=budget['outputReserveTokens'], context_window_limit=budget['contextLimitTokens'])
    manifest = request_manifest(action=action, work_context=work_context,
        source_authority_sha256=t.canonical_sha256(authority), native_query_sha256=t.canonical_sha256(native_query),
        provenance_sha256=t.canonical_sha256(provenance), provider_roles=roles,
        provider_input_accounting=accounting, admission=admission)
    admission = admission.model_copy(update={'manifest_sha256': t.canonical_sha256(manifest)})
    return _freeze_native(work_context, action, admission, authority, native_query, provenance, budget)


def freeze(request, work, playable_target, view, budget, *, authority, graph_receipt=None,
           graph_policy=None, included_history=(), plan_jev_request=None, native_query=None,
           provenance=None, submitted_intent=None):
    """Freeze the actual first Jev wire under independent source/Graph bases."""
    from .agent_turn_service import _json_node_count
    from .plan_jev_dispatch import verify_initial_input
    from application_state.agent_conversation.rules_authority_types import canonical_sha256
    verify_initial_input(view, request, work, plan_jev_request)
    basis = work.content_basis
    if (request.surface.surface_id != "plan" or request.plan_context_policy is None
            or basis is None or authority.managed_world_id != basis.world_id):
        raise ValueError("Plan source composition requires its exact committed Plan World")
    if isinstance(request.plan_context_policy,t.PlanContextPolicyV2) and native_query is None:
        raise ValueError('Current Plan requires its explicit native query result, including typed unavailability')
    if (graph_receipt is None) != (graph_policy is None):
        raise ValueError("A genuine Graph capability requires its own receipt and policy")
    if graph_receipt is not None and (not isinstance(graph_receipt, t.PlanWorldGraphContextReceiptV1)
            or not isinstance(graph_policy, t.PlanPlacementAuthoringPolicyV1)):
        raise ValueError("Plan source composition cannot manufacture a Graph capability")
    raw = view["payloadJson"].encode()
    if len(raw) != view["payloadUtf8Bytes"] or sha256(raw).hexdigest() != view["payloadSha256"]:
        raise ValueError("Plan source first provider bytes differ from their actual witness")
    body = json.loads(raw)
    count = len(raw) + 64 * (1 + _json_node_count(body))
    assembled = t.PlanSourceProviderInputV1(provider_model_name=view["model"],
        provider_model_version=view["model"], tokenizer_name=budget["estimator"],
        tokenizer_version="v1", provider_envelope_input_tokens=count,
        output_token_reserve=budget["outputReserveTokens"], context_window_limit=budget["contextLimitTokens"],
        included_history=[t.PlanWorldGraphHistoryPinV1(turn_id=turn_id,
            answer_sha256=sha256(text.encode()).hexdigest()) for turn_id, text in included_history
            if text and _contains_text(body, text)], assembled_input_sha256=view["payloadSha256"])
    plan_basis = _plan_basis(work)
    if native_query is not None:
        from application_state.agent_conversation.native_context import NativeProviderInputV1
        if graph_receipt is not None or graph_policy is not None:
            raise ValueError("Shared native Plan cannot inherit a second Graph capability")
        work_context, action = _native_plan_parts(request, plan_basis, playable_target, submitted_intent)
        return _freeze_native(work_context, action,
            NativeProviderInputV1(**assembled.model_dump(exclude={'assembler_version'})),
            authority,native_query,provenance,budget)
    receipt_type = t.PlanSourceContextReceiptV1
    provisional = receipt_type.model_construct(
        receipt_serializer_version="canonical-json-utf8-v1", context_receipt_sha256="0" * 64,
        plan_context_policy=request.plan_context_policy, plan_basis=plan_basis,
        playable_target=playable_target, source_authority=authority,
        graph_capability=graph_receipt, assembled_input=assembled)
    payload = provisional.model_dump(mode="json", by_alias=True, exclude={"context_receipt_sha256"})
    receipt = receipt_type.model_validate(payload | {"context_receipt_sha256": canonical_sha256(payload)})
    fields = dict(allowed_graph_operations=[], max_provider_attempts=None, max_graph_operations=None,
        max_results_per_operation=0, max_total_provider_input_tokens=None,
        max_total_provider_output_tokens=None, provider_input_accounting={
            "kind": "conservative_upper_bound", "estimator": budget["estimator"]},
        source_opened=False, source_read_scope=None, max_source_read_chars=96000,
        max_chars_per_source_read=12000, source_read_accounting="settled_receipts_v1",
        provider_roles=budget["providerRoles"], native_source_section_policy="exact_native_source_sections_v1",
        requested_work_policy="semantic_plan_placement_v1",
        placement_catalog_sha256=request.plan_placement_catalog.sha256 if request.plan_placement_catalog is not None else None,
        plan_authoring_capture_sha256=request.plan_authoring_capture.sha256 if request.plan_authoring_capture is not None else None,
        source_authority_sha256=canonical_sha256(authority.model_dump(mode="json", by_alias=True)))
    if graph_policy is not None:
        for key in ("allowed_graph_operations", "max_results_per_operation", "source_read_scope",
                    "max_source_read_chars", "max_chars_per_source_read"):
            fields[key] = getattr(graph_policy, key)
    policy_type = t.PlanSourceExecutionPolicyV1
    execution_type = t.PlanSourceExecutionV1
    policy = policy_type(**fields)
    execution_payload = dict(schema=execution_type.model_fields['schema_'].default,
        context_receipt_sha256=receipt.context_receipt_sha256,
        policy=policy.model_dump(mode="json", by_alias=True))
    execution = execution_type.model_validate(execution_payload | {
        "execution_policy_sha256": canonical_sha256(execution_payload), "events": []})
    validate_source_execution_binding(receipt, execution)
    return receipt, execution, ([], [], [])


def freeze_build(request, work, view, budget, *, authority, native_query, provenance,
                 submitted_intent, projection, accounting, included_history=(), reviewed_admission=None,
                 source_observation=None, conversation_observation=None):
    """Capture actual Build work and its first prepared semantic wire, without a Graph packet."""
    from application_state.agent_conversation.native_context import BuildWorkContextV1, NativeBuildProviderInputV2, NativeReviewedActionInputV1
    from application_state.agent_conversation.native_execution import NativeBuildActionV1
    from application_state.agent_conversation.build_intentional_response import (
        MENU_DIGEST, RESOLVER_DIGEST, SCOPED_BUILD_MENU_DIGEST,
        SCOPED_BUILD_RESOLVER_DIGEST, opening_work_question,
    )
    basis = work.build_source
    if request.surface.surface_id!='build' or basis is None or accounting is None:
        raise ValueError('Native Build requires its actual saved work and accounting')
    pending = source_observation is not None or conversation_observation is not None
    if pending:
        from application_state.agent_conversation.build_source_free import BuildSourceObservationV1, BuildConversationObservationV1
        if (type(source_observation) is not BuildSourceObservationV1
                or type(conversation_observation) is not BuildConversationObservationV1
                or authority is not None or native_query is not None or reviewed_admission is not None
                or request.build_authored_references is not None):
            raise ValueError('Pending Build requires observations without acquired authority, references or reviewed admission')
    reviewed=reviewed_admission is not None
    menu, resolver = ((MENU_DIGEST, RESOLVER_DIGEST) if reviewed else
                      (SCOPED_BUILD_MENU_DIGEST, SCOPED_BUILD_RESOLVER_DIGEST))
    if reviewed:
        from application_state.agent_conversation.reviewed_action import admission_manifest,digest
        if (view is not None or reviewed_admission!=submitted_intent or submitted_intent.reviewed_step is None):
            raise ValueError('Native human admission differs from its exact reviewed intent')
        assembled=NativeReviewedActionInputV1(submitted_intent_sha256=t.canonical_sha256(submitted_intent),
            assembled_input_sha256=digest(admission_manifest(submitted_intent)))
    else:
        if projection is None or submitted_intent.reviewed_step is not None:
            raise ValueError('Native semantic Build requires its actual prepared projection')
        body=json.loads(view['payloadJson'])
        raw=view['payloadJson'].encode()
        if (len(raw)!=view['payloadUtf8Bytes'] or sha256(raw).hexdigest()!=view['payloadSha256']
                or body['state']!=projection.state() or body['questions']!=projection.questions()
                or body['questions'].get('requested_work') != opening_work_question(menu)
                or (view['provider'],view['model'],view['apiMode'])!=('typesafe','jev-1.14.0','typesafe_decision')):
            raise ValueError('Native Build initial prepared request changed before capture')
        accounting.validate(body,raw,context_mode=view['contextMode'],host_phase=getattr(projection,'host_phase',None))
    actions = budget['buildJevActions']
    from types import SimpleNamespace
    from application_state.agent_conversation.build_intentional_response import policy_capabilities,captured_capabilities
    caps = (captured_capabilities if reviewed else policy_capabilities)(SimpleNamespace(**actions))
    if not reviewed:
        from dataclasses import replace
        caps = replace(caps, reviews=(*caps.reviews, "lore_page"))
    source_basis = t.BuildSourceContextBasisV1(world_id=basis.world_id, document_id=basis.document_id,
        registry_revision=basis.revision, content_sha256=basis.content_sha256, visibility=basis.visibility_state)
    from application_state.agent_conversation.build_related_pages import PagePointer
    related = actions.get('related_page_catalog')
    related = None if related is None else tuple(PagePointer.model_validate(row) for row in related)
    action = NativeBuildActionV1(intent=submitted_intent, write_capability=request.build_write_capability,
        image_move_capture=request.build_image_move_capture,
        capabilities=caps, related_page_catalog=related,
        saved_source_char_count=len(basis.markdown), requested_work_menu_sha256=menu,
        response_resolver_sha256=resolver)
    if not reviewed:
        if getattr(projection,'host_phase',None)!='select':
            raise ValueError('Fresh native Build requires semantic initial input')
        from application_state.agent_conversation.build_intentional_response import semantic_routing_state, semantic_request_id, digest
        from .agent_turn_service import _turn_idempotency_key
        host = json.loads(projection.host_interaction_json)
        expected_state = semantic_routing_state(request.message, host, request.build_authored_references,
                                                write_capability=request.build_write_capability)
        if action.image_move_capture is not None:
            from application_state.build_proposal.image_move_decision import BuildImageMoveDecision, OPENING_STATE_KEY

            if basis.visibility_state != "internal" or basis.page_presentation is None:
                raise ValueError("Build image movement requires the current internal composed Page")
            move = BuildImageMoveDecision.from_saved(
                action.image_move_capture, request.message, basis.markdown, basis.page_presentation,
            )
            move.require_opening_offer(body)
            expected_state["interaction"][OPENING_STATE_KEY] = move.semantic_state()
        if (host['current_page']!={'document_id':basis.document_id,'title':basis.title}
            or host['allowed_operations']!=list(caps.operations)
            or host['capability_sha256']!=(digest(request.build_write_capability.model_dump(mode='json')) if request.build_write_capability is not None else None)
            or host.get('related_page_catalog')!=actions.get('related_page_catalog')
            or body['state']!=expected_state
            or projection.request_id!=semantic_request_id(body['state'],world_id=basis.world_id,
                client_thread_id=request.client_thread_id,idempotency_key=_turn_idempotency_key(basis.world_id,request.turn_id))):
            raise ValueError('Semantic Build input differs from its captured work and capability')
        from application_state.agent_conversation.native_context import NativeBuildPendingProviderInputV3
        input_type = NativeBuildPendingProviderInputV3 if pending else NativeBuildProviderInputV2
        assembled = input_type(provider_model_name=view['model'], provider_model_version=view['model'],
            tokenizer_name=accounting.descriptor['policy'], tokenizer_version=accounting.tokenizer_version,
            provider_envelope_input_tokens=accounting.estimate(body), output_token_reserve=0,
            context_window_limit=budget['contextLimitTokens'],
            included_history=tuple(t.PlanWorldGraphHistoryPinV1(turn_id=turn_id,
                answer_sha256=sha256(text.encode()).hexdigest()) for turn_id,text in included_history
                if text and _contains_text(body,text)), assembled_input_sha256=view['payloadSha256'])
    if pending:
        if (host.get('conversation_id') != str(conversation_observation.conversation_id)
                or host.get('pointer_revision') != conversation_observation.pointer_revision):
            raise ValueError('Pending Build conversation differs from its frozen host interaction')
        return _freeze_pending_build(BuildWorkContextV1(source_basis=source_basis), action, assembled,
            source_observation, conversation_observation, provenance, budget,
            controller_accounting=accounting.descriptor,
            writer_budget=_native_writer_budget(actions['writer_context_budget'], accounting))
    return _freeze_native(BuildWorkContextV1(source_basis=source_basis),action,assembled,
        authority,native_query,provenance,budget,controller_accounting=accounting.descriptor,
        writer_budget=_native_writer_budget(actions['writer_context_budget'], accounting))


def _native_writer_budget(budget, accounting):
    from application_state.agent_conversation.native_execution import NativeWriterEstimatedBudgetV1
    # The legacy harness budget remains its historical codec. Only this actual
    # shared native owner adopts the already prepared offline counter.
    return NativeWriterEstimatedBudgetV1(schema='dmb_native_writer_estimated_budget_v1',
        provider=budget['provider'], model=budget['model'], api_mode=budget['api_mode'],
        estimator=accounting.descriptor['policy'], tokenizer_version=accounting.tokenizer_version,
        context_limit_tokens=None, output_reserve_tokens=0)


def _freeze_native(work_context, action, assembled, authority, native_query, provenance, budget,
                   *, controller_accounting=None, writer_budget=None, play_context_receipt=None):
    """One shared root composition; surface work and Core source identity keep their owners."""
    from application_state.agent_conversation.native_context import SurfaceNativeContextReceiptV1, validate_work_context
    from application_state.agent_conversation.native_execution import (
        SurfaceNativeExecutionPolicyV1, SurfaceNativeExecutionV1, validate_context_binding)
    from application_state.agent_conversation.rules_authority_types import canonical_sha256
    data = dict(provenance_sha256=canonical_sha256(provenance), work_context=work_context,
        source_authority=authority, native_query=native_query, assembled_input=assembled)
    provisional = SurfaceNativeContextReceiptV1.model_construct(context_receipt_sha256='0'*64,**data)
    wire = provisional.model_dump(mode='json',by_alias=True,exclude={'context_receipt_sha256'})
    receipt = SurfaceNativeContextReceiptV1.model_validate_json(json.dumps(wire|{'context_receipt_sha256':canonical_sha256(wire)}))
    policy = SurfaceNativeExecutionPolicyV1(action=action,source_authority_sha256=canonical_sha256(authority),
        native_query_sha256=canonical_sha256(native_query),provider_roles=budget['providerRoles'],
        provider_input_accounting={'kind':'conservative_upper_bound','estimator':budget['estimator']},
        max_provider_attempts=None,max_total_provider_input_tokens=None,max_total_provider_output_tokens=None,
        controller_continuation_accounting=controller_accounting,writer_context_budget=writer_budget)
    wire = dict(schema='dmb_surface_native_execution_v1',context_receipt_sha256=receipt.context_receipt_sha256,
        policy=policy.model_dump(mode='json',by_alias=True))
    execution = SurfaceNativeExecutionV1.model_validate_json(json.dumps(wire|{'execution_policy_sha256':canonical_sha256(wire),'events':[]}))
    validate_work_context(receipt,provenance,play_context_receipt=play_context_receipt)
    validate_context_binding(receipt,execution)
    return receipt,execution,([],[],[])


def _freeze_pending_build(work_context, action, assembled, source_observation, conversation_observation,
                          provenance, budget, *, controller_accounting, writer_budget):
    """Compose the distinct Build observation codec without any source grant."""
    from application_state.agent_conversation.native_context import BuildPendingContextReceiptV1, _join_work_context
    from application_state.agent_conversation.native_execution import BuildPendingExecutionPolicyV1, BuildPendingExecutionV1
    from application_state.agent_conversation.build_source_free import validate_pending_execution_binding
    data = dict(provenance_sha256=t.canonical_sha256(provenance), work_context=work_context,
        source_observation=source_observation, conversation_observation=conversation_observation, assembled_input=assembled)
    provisional = BuildPendingContextReceiptV1.model_construct(context_receipt_sha256='0' * 64, **data)
    wire = provisional.model_dump(mode='json', by_alias=True, exclude={'context_receipt_sha256'})
    receipt = BuildPendingContextReceiptV1.model_validate_json(json.dumps(wire | {
        'context_receipt_sha256': t.canonical_sha256(wire)}))
    policy = BuildPendingExecutionPolicyV1(action=action,
        source_observation_sha256=t.canonical_sha256(source_observation), provider_roles=budget['providerRoles'],
        provider_input_accounting={'kind': 'conservative_upper_bound', 'estimator': budget['estimator']},
        max_provider_attempts=None, max_total_provider_input_tokens=None, max_total_provider_output_tokens=None,
        controller_continuation_accounting=controller_accounting, writer_context_budget=writer_budget)
    wire = dict(schema='dmb_build_pending_execution_v1', context_receipt_sha256=receipt.context_receipt_sha256,
        policy=policy.model_dump(mode='json', by_alias=True))
    execution = BuildPendingExecutionV1.model_validate_json(json.dumps(wire | {
        'execution_policy_sha256': t.canonical_sha256(wire), 'events': []}))
    provenance = t.TurnProvenance.model_validate_json(provenance.model_dump_json(by_alias=True))
    _join_work_context(receipt, provenance)
    execution = validate_pending_execution_binding(receipt, execution)
    return receipt, execution, ([], [], [])


def _contains_text(value, text):
    if isinstance(value, str):
        return value == text
    if isinstance(value, list):
        return any(_contains_text(item, text) for item in value)
    if isinstance(value, dict):
        return any(_contains_text(item, text) for item in value.values())
    return False


def play_work_proof(request,work,dialogue):
    from .native_play_graph_owner import prepare_play_sources
    frame,_=prepare_play_sources(request,work,native=True)
    return dict(source_frame=frame.model_dump(mode='json',by_alias=True),
        session_evidence=list((work.session_evidence or {}).get('sessions',[])),
        dialogue=[dict(role=row['role'],content=row['content']) for row in dialogue])


def freeze_play(request,work,view,budget,*,authority,native_query,provenance,submitted_intent,parent):
    """Freeze actual Run work and exact first semantic Jev request together."""
    from .agent_turn_service import _json_node_count,_turn_idempotency_key
    from application_state.agent_conversation.jev_retrieval_contract import NativePlayRetrievalDecisionInputV1,validate_wire_body
    from application_state.agent_conversation.native_play_work import project_work
    from application_state.agent_conversation.native_context import PlayWorkContextV1,NativeProviderInputV1
    from application_state.agent_conversation.native_execution import NativePlayActionV1
    if (request.surface.surface_id!='play' or not isinstance(parent, NativePlayRetrievalDecisionInputV1)
            or parent.question!=request.message or work.play_context_receipt is None
            or authority.managed_world_id!=work.play_context_receipt.world_id
            or (view['provider'],view['model'],view['apiMode'])!=('typesafe','jev-1.14.0','decision')):
        raise ValueError('Native Play requires its actual Run and retrieval controller')
    proof=play_work_proof(request,work,[row.model_dump() for row in parent.dialogue])
    frame=t.PlaySourceFrameV1.model_validate_json(json.dumps(proof['source_frame']))
    context=PlayWorkContextV1(play_basis=work.play_context_receipt,
        play_sources=frame.manifest,play_source_frame_sha256=t.canonical_sha256(frame))
    if parent.play_work!=project_work(context,provenance,
            _turn_idempotency_key(request.owner_scope.world_id,request.turn_id),proof):
        raise ValueError('Native Play first request changed its exact work')
    raw=view['payloadJson'].encode()
    if len(raw)!=view['payloadUtf8Bytes'] or sha256(raw).hexdigest()!=view['payloadSha256']:
        raise ValueError('Native Play first provider bytes changed before claim')
    validate_wire_body(parent,raw)
    assembled=NativeProviderInputV1(provider_model_name=view['model'],provider_model_version=view['model'],
        tokenizer_name=budget['estimator'],tokenizer_version='v1',
        provider_envelope_input_tokens=len(raw)+64*(1+_json_node_count(json.loads(raw))),
        output_token_reserve=budget['outputReserveTokens'],context_window_limit=budget['contextLimitTokens'],
        included_history=[],assembled_input_sha256=view['payloadSha256'])
    return _freeze_native(context,NativePlayActionV1(intent=submitted_intent),assembled,
        authority,native_query,provenance,budget,play_context_receipt=work.play_context_receipt)
