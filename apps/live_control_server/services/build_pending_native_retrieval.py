"""Pending Build's actual native controller, using its own admitted source owner.

This driver grants no Core access. Selected IO stays with the existing guarded
native read owners; source preparation/discovery is never repeated here.
"""
from __future__ import annotations

import hashlib
import json
import re
from uuid import UUID, uuid4

from application_state.agent_conversation import types as ledger
from application_state.agent_conversation.native_retrieval import (
    NativeBuildDecisionContextV1, NativeRetrievalAuthorizedV1, NativeRetrievalSelectedV1,
    owner, scope_digest, source_pins, controller_accounting,
)
from application_state.agent_conversation.jev_retrieval_contract import (
    NativeBuildRetrievalDecisionInputV3, prepare_decision, decode_selection,
)
from .build_pending_app_pages import PendingAppPageDriver, _commit
from .build_jev_driver import canonical, sdk_answers
from .build_jev_transitions import DecisionIntent, DecisionQuestion
from .build_jev_dispatch import prepared_driver_view


class PendingNativeRetrievalDriver(PendingAppPageDriver):
    """One exact controller attempt; no retry, hidden search or legacy identity."""
    def __init__(self, adapter, candidates, *, dialogue=(), examined_candidates=(),
                 allowed_operations=('select_candidates', 'discover_more', 'finish_retrieval')):
        self.adapter = adapter
        self.receipt, self.before = owner(adapter.fence.turn)
        if getattr(adapter, 'prepare_deferred_build_query', None) is not None:
            raise ValueError('Pending retrieval cannot race deferred source preparation')
        self.parent = NativeBuildRetrievalDecisionInputV3(
            request_id=uuid4(), parent_attempt_id=uuid4(), scope_sha256=scope_digest(adapter.fence.turn),
            question=self.before.policy.action.intent.message, dialogue=tuple(dialogue),
            candidates=tuple(candidates), examined_candidates=tuple(examined_candidates),
            allowed_operations=tuple(allowed_operations), **source_pins(self.receipt, self.before))
        request = prepare_decision(self.parent, controller_accounting=controller_accounting(self.before))
        self.wire = {'model': request.model, 'state': request.state, 'questions': {
            q.name: {'type': 'choice', 'instructions': q.question, 'criteria': dict.fromkeys(q.options)}
            for q in request.questions}}
        self.step = DecisionIntent(request_id=str(self.parent.request_id), phase='navigate',
            state=request.state, questions=tuple(DecisionQuestion(name=q.name, kind='choice',
                question=q.question, options=q.options) for q in request.questions))
        self.plan = self.prepared = self.selection = self.proof = None

    def authorize(self, prepared):
        adapter = self.adapter
        if (self.plan is None or self.prepared is not None or adapter.failure is not None
                or adapter._broker_execution() != self.before):
            return False
        from .build_jev_accounting import DecisionCapacityError
        try:
            view = prepared_driver_view(prepared, self.plan, accounting=adapter._build_jev_accounting)
        except DecisionCapacityError as exc:
            self.admission_failure = exc
            return False
        self.parent = self.parent.model_copy(update={'parent_attempt_id': UUID(prepared.attempt_id)})
        auth = NativeRetrievalAuthorizedV1(event_id=uuid4(), sequence=len(self.before.events),
            provider_attempt_id=UUID(prepared.attempt_id), decision_request_id=self.parent.request_id,
            parent_request_sha256=self.parent.digest, envelope_sha256=prepared.body_sha256,
            serializer_version=view['serializerVersion'], provider=view['provider'], model=view['model'],
            api_mode=view['apiMode'], tool_schema_sha256=ledger.canonical_sha256([]),
            input_accounting_kind='estimated_token_count', input_estimator=adapter._build_jev_accounting.descriptor['policy'],
            input_tokens=adapter._build_jev_accounting.estimate(json.loads(prepared.body)), output_token_reserve=0,
            included_assertion_ids=[], included_relationship_ids=[], included_evidence_ref_ids=[],
            included_graph_event_ids=[], included_source_read_event_ids=[],
            build_context=NativeBuildDecisionContextV1(context_mode=view['contextMode'], context_phase='navigate',
                max_question_input_tokens=view['maxQuestionInputTokens'], dispatch_identity_sha256=view['dispatchIdentitySha256']))
        self.proof = {'parent_request_json': self.parent.model_dump_json(by_alias=True),
            'request_json': prepared.body.decode()}
        _commit(adapter, 'authorize_pending_native_retrieval', authorization=auth,
            prepared_input_proof=self.proof, authorize_current_access=adapter.pending_build_access)
        adapter.last_provider_attempt_id = auth.provider_attempt_id
        adapter._prepared_build_decision = prepared
        adapter._capture_prepared_prompt(view, auth)
        self.prepared = prepared
        return True

    def accept_decision(self, model, answers, *, actual_response):
        adapter = self.adapter
        if (self.prepared is None or str(adapter.last_provider_attempt_id) != self.prepared.attempt_id
                or model != self.wire['model'] or sdk_answers(actual_response) != answers):
            raise ValueError('Pending native retrieval requires its actual producing SDK response')
        selected = decode_selection(self.parent, actual_response)
        response = canonical(actual_response.model_dump(mode='json'))
        adapter.context_capture.observe({'kind': 'context_snapshot', 'stage': 'after', 'materials': [{
            'item_id': f'unvalidated-native-retrieval-result:{self.prepared.attempt_id}',
            'state': 'model_context', 'role': 'assistant', 'text': response}]})
        event = NativeRetrievalSelectedV1(event_id=uuid4(), sequence=len(adapter._broker_execution().events),
            context_receipt_sha256=self.receipt.context_receipt_sha256,
            execution_policy_sha256=self.before.execution_policy_sha256,
            decision_request_id=self.parent.request_id, controller_attempt_id=UUID(self.prepared.attempt_id),
            controller_envelope_sha256=self.prepared.body_sha256,
            controller_response_sha256=hashlib.sha256(response.encode()).hexdigest(),
            parent_request_sha256=self.parent.digest, operation=selected.operation,
            selected_handles=list(selected.selected_handles), actual_input_tokens=actual_response.observation.input_tokens,
            actual_output_tokens=actual_response.observation.output_tokens)
        proof = self.proof | {'response_json': response}
        _commit(adapter, 'record_pending_native_selection', selection=event,
            producer_proof=proof, authorize_current_access=adapter.pending_build_access)
        self.selection, self.proof = event, proof


def _record_state(execution):
    from application_state.agent_conversation.native_plan_statements import NativePlanStatementReadAuthorizedV1, NativePlanStatementReadObservedV1
    from application_state.agent_conversation.native_plan_assertions import NativePlanAssertionReadAuthorizedV1, NativePlanAssertionReadObservedV1
    result = {}
    for family, grant_type, observed_type, field in (
            ('statement', NativePlanStatementReadAuthorizedV1, NativePlanStatementReadObservedV1, 'statement_ids'),
            ('assertion', NativePlanAssertionReadAuthorizedV1, NativePlanAssertionReadObservedV1, 'assertion_ids')):
        grants = [e for e in execution.events if type(e) is grant_type]
        observed = {e.authorization_event_id: e for e in execution.events if type(e) is observed_type}
        attempted = {identity for e in grants for identity in getattr(e, field)}
        opened = {r.support.statement_id if family == 'statement' else r.assertion.assertion_id
                  for e in observed.values() for r in e.reads}
        result[family] = grants, observed, attempted, opened
    return result


def _object_candidates(query, execution):
    from application_state.agent_conversation.native_plan_assertions import NativeGraphQueryV4, object_record_catalog
    from application_state.agent_conversation.jev_retrieval_contract import RetrievalCandidate
    if type(query) is not NativeGraphQueryV4:
        return (), ()
    state = _record_state(execution)
    offers, examined = [], []
    for unit in object_record_catalog(query).units:
        ids = {'statement': set(unit.statement_ids), 'assertion': set(unit.assertion_ids)}
        if not any(ids.values()):
            continue
        if any(values - state[family][2] for family, values in ids.items()):
            offers.append(RetrievalCandidate(handle=unit.handle, label=unit.label,
                kind='Native Graph object; open its complete admitted statement and assertion support'))
        else:
            opened = {(family, identity) for family, values in ids.items() for identity in values & state[family][3]}
            complete = all(values <= state[family][3] for family, values in ids.items())
            status = 'opened' if complete else 'partial' if opened else 'unavailable'
            examined.append(RetrievalCandidate(handle=unit.handle, label=unit.label,
                kind=f'Previously selected native object: {status}; not an answer-sufficiency verdict'))
    return tuple(offers), tuple(examined)


def _read_selected_objects(adapter, query, selection):
    from application_state.agent_conversation.native_plan_assertions import NativeGraphQueryV4, object_record_ids
    from .native_graph_reads import read_selected
    if type(query) is not NativeGraphQueryV4:
        return
    for family in ('statement', 'assertion'):
        execution = adapter._broker_execution()
        grants, observed, attempted, _ = _record_state(execution)[family]
        pending = [g for g in grants if g.event_id not in observed]
        if any(g.provider_attempt_id != selection.controller_attempt_id for g in pending):
            raise ValueError('Pending native read belongs to another controller')
        ids = object_record_ids(query, selection.selected_handles, assertion=family == 'assertion', attempted=attempted)
        if ids:
            event_id = uuid4()
            _commit(adapter, 'authorize_pending_native_read', event_id=event_id, record_kind=family,
                record_ids=tuple(ids), authorize_current_access=adapter.pending_build_access)
            pending.append(next(e for e in adapter._broker_execution().events if e.event_id == event_id))
        for grant in pending:
            context = adapter.native_query_context
            if context is None or context.query != query:
                raise ValueError('Pending native reads require the original public query context')
            _commit(adapter, 'observe_pending_native_read', event_id=uuid4(), authorization_event_id=grant.event_id,
                read=lambda actual, context=context: read_selected(context, actual, context.principal),
                authorize_current_access=adapter.pending_build_access)


def _followup_statblock(adapter, authority):
    from application_state.agent_conversation.build_saved_statblock import BuildSavedStatblockReadV1
    from .statblock_saved_revision import published_statblock_reference

    turn = adapter.fence.turn
    if turn.sequence <= 1:
        return ()
    previous = adapter.service.list_turns(
        turn.world_id, turn.conversation_id, limit=1, before_sequence=turn.sequence,
    )
    if len(previous) != 1 or previous[0].status != "completed":
        return ()
    prior = previous[0]
    work = getattr(prior.graph_context_receipt, "work_context", None)
    if (getattr(work, "surface_id", None) != "build"
            or work.source_basis != turn.graph_context_receipt.work_context.source_basis
            or prior.graph_context_execution is None):
        return ()
    reads = [event for event in prior.graph_context_execution.events if type(event) is BuildSavedStatblockReadV1]
    if len(reads) != 1 or reads[0].world_id != turn.world_id:
        return ()
    read = reads[0]
    reference = published_statblock_reference(turn.world_id, authority, read.draft_id, read.locator)
    if reference is None:
        return ()
    return ((reference.label, read.draft_id, read.locator),)


def _statblock_catalog(adapter, authority):
    from apps.live_control_server.routes.statblock_storage import statblock_data_root
    from .statblock_saved_revision import iter_saved_mechanics

    principal = getattr(adapter, "native_principal", None)
    if getattr(principal, "role", None) != "gm":
        return {}
    if re.search(r"\b(?:stat[ -]?blocks?|saved mechanics)\b", adapter.request.message, re.IGNORECASE):
        root = statblock_data_root(adapter.root)
        entries = iter_saved_mechanics(root, world_id=adapter.fence.turn.world_id)
    else:
        entries = _followup_statblock(adapter, authority)
    return {
        f"saved-statblock:{index}": (label, UUID(str(draft_id)), locator)
        for index, (label, draft_id, locator) in enumerate(entries)
    }


def _read_statblock(adapter, world_id, draft_id, locator, authority):
    from apps.live_control_server.routes.statblock_storage import statblock_data_root
    from .native_graph_inspection import InspectionUnavailable, statblock_pdf_support
    from .native_pdf_evidence import reviewed_pdf_regions
    from .statblock_saved_revision import open_version, published_statblock_reference

    principal = adapter.native_principal
    if principal.role != "gm" or authority.managed_world_id != world_id:
        raise ValueError("Saved statblock is outside the current World authority")
    opened = open_version(
        statblock_data_root(adapter.root), world_id=world_id,
        draft_id=str(draft_id), revision_id=locator.revision_id,
    )
    if (opened["world_id"] != world_id or UUID(str(opened["draft_id"])) != draft_id
            or opened["locator"] != locator.model_dump(mode="json")):
        raise ValueError("Opened statblock differs from its selected saved revision")
    resource = opened["resource"]
    regions = reviewed_pdf_regions(resource, world_id=world_id)
    support = None
    if regions:
        reference = published_statblock_reference(world_id, authority, draft_id, locator)
        if reference is not None:
            try:
                support = statblock_pdf_support(
                    reference, regions, principal, expected_source_epoch=authority.acquisition_epoch,
                )
            except InspectionUnavailable as exc:
                if exc.code != "statblock_pdf_review_incomplete":
                    raise
    return resource["definition"], support


async def run_pending_native_retrieval(adapter, harness, *, dialogue=(), rules=None):
    """Collect under actual pending owners until an acknowledged explicit finish.

    The initial query is already frozen. No discovery retry or legacy Graph
    bootstrap is performed. Interrupted source IO remains an unresolved grant;
    the navigator refuses to repeat it. Stored completed acquisitions are reused.
    """
    from application_state.agent_conversation.build_pending_native import prepared_pending_source
    from application_state.agent_conversation.native_retrieval import current_selection
    from application_state.agent_conversation.native_plan_assertions import NativeGraphQueryV4, object_record_catalog
    from application_state.agent_conversation.native_corpus import native_corpus_search_handle
    from application_state.agent_conversation.plan_jev_rules_lookup import RULES_HANDLE, rules_candidate
    from .native_source_navigation import navigator
    receipt, execution = owner(adapter.fence.turn)
    authority, query = prepared_pending_source(receipt, execution)
    if getattr(adapter, 'native_query', None) != query:
        raise ValueError('Pending retrieval cannot substitute its prepared query')
    from application_state.agent_conversation.build_saved_statblock import BuildSavedStatblockReadV1
    from application_state.agent_conversation.jev_retrieval_contract import RetrievalCandidate

    sources = navigator(adapter)
    statblocks = _statblock_catalog(adapter, authority)
    producing = None
    while True:
        _, execution = owner(adapter.fence.turn)
        acquired_statblocks = {
            e.handle for e in execution.events if type(e) is BuildSavedStatblockReadV1
        }
        auths = [e for e in execution.events if type(e) is NativeRetrievalAuthorizedV1]
        selected = None
        if auths:
            choices = [e for e in execution.events if type(e) is NativeRetrievalSelectedV1
                       and e.controller_attempt_id == auths[-1].provider_attempt_id]
            if len(choices) != 1:
                raise ValueError('Pending native dispatch is unresolved and cannot be resent')
            selected = current_selection(adapter.fence.turn)
            if selected.operation == 'finish_retrieval':
                return {}  # Build's writer reconstructs its actual stored work.
            if selected.operation != 'select_candidates':
                raise ValueError('Pending native discovery was already prepared once')
            object_handles = ({u.handle for u in object_record_catalog(query).units}
                              if type(query) is NativeGraphQueryV4 else set())
            grant, search, auths_read, reads = sources._events()
            settled = {sources._handle(g) for g in auths_read if g.event_id in reads}
            if grant is not None and search is not None:
                settled.add(native_corpus_search_handle(grant.query_sha256))
            native_offers = {row.handle for row in sources.offered()}
            metadata = set(sources._keyword_catalog()) | {sources.expansion_handle()}
            known = object_handles | native_offers | settled | metadata | ({RULES_HANDLE} if rules is not None else set())
            known |= set(statblocks) | acquired_statblocks
            if not set(selected.selected_handles) <= known:
                raise ValueError('Pending native selection differs from its actual acquisition catalogue')
            _read_selected_objects(adapter, query, selected)
            needed = [h for h in selected.selected_handles if h in native_offers and h not in settled]
            if needed:
                sources.select(tuple(needed))
            if rules is not None and RULES_HANDLE in selected.selected_handles and not rules.selected:
                if producing is None or producing.selection != selected:
                    raise ValueError('Recovered Rules selection requires its original runtime and prepared proof')
                rules.lookup_selected(producing.proof['parent_request_json'])
            for handle in selected.selected_handles:
                if handle not in statblocks or handle in acquired_statblocks:
                    continue
                if producing is None or producing.selection != selected:
                    raise ValueError("Pending statblock selection requires its original frozen catalogue")
                _, draft_id, locator = statblocks[handle]
                _commit(adapter, "observe_pending_saved_statblock", selection_event_id=selected.event_id,
                    handle=handle, draft_id=draft_id, locator=locator,
                    read=lambda *args: _read_statblock(adapter, *args),
                    authorize_current_access=adapter.pending_build_access)
                acquired_statblocks.add(handle)
        offers, examined = _object_candidates(query, adapter._broker_execution())
        candidates = [*offers, *sources.offered()]
        reviewed = [*examined, *sources.examined()]
        for handle, (label, _, _) in statblocks.items():
            if handle in acquired_statblocks:
                reviewed.append(RetrievalCandidate(handle=handle, label=label, kind="Opened saved statblock"))
            else:
                candidates.append(RetrievalCandidate(
                    handle=handle, label=label, kind="Saved statblock; open its exact stored mechanics revision",
                ))
        if rules is not None:
            (reviewed if rules.selected else candidates).append(rules_candidate())
        producing = PendingNativeRetrievalDriver(adapter, candidates, dialogue=dialogue,
            examined_candidates=reviewed, allowed_operations=('select_candidates', 'finish_retrieval'))
        await harness._decide(adapter, producing)
