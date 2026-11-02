"""One exact Plan writer dispatch; no retrieval tools, retries or repair loop."""
from dataclasses import dataclass
from hashlib import sha256
import json
from time import perf_counter
from uuid import UUID, uuid4

from generationengine.providers.openai_text import OpenAITextProvider
from application_state.agent_conversation import types as t
from application_state.agent_conversation.plan_jev_graph_packet import project
from application_state.agent_conversation.rules_authority_types import canonical_bytes, canonical_sha256
from application_state.agent_conversation.source_writer_output import strict_json
from application_state.agent_conversation.surface_source_answer import SOURCE_ATTRIBUTION_INSTRUCTIONS
from .hermes_product_prompt import BUDDY_SYSTEM_PROMPT, IMAGE_DIRECTION_INSTRUCTIONS
from .native_rules_capture import NativeProviderReply

from application_state.agent_conversation.surface_evidence_answer import INSTRUCTIONS as EVIDENCE_INSTRUCTIONS

INSTRUCTIONS = SOURCE_ATTRIBUTION_INSTRUCTIONS + EVIDENCE_INSTRUCTIONS + """
Answer the current co-GM question directly using relevant supplied material. Preserve
beliefs, time and authored versus played events. Entity labels and dialogue are
navigation/context, not evidence. Read short evidence handles only as passage joins.
For a graph_claim, select passages only from that target's schema branch: their
opened_passages.evidence token must occur in the graph record's evidence list.
Identical passage text or line ranges do not make different evidence tokens interchangeable.
Use source_passage_claim for a claim grounded independently in an opened passage.
For authored excerpts, select an exact block_handle from the ordered authored blocks.
The host supplies its literal text; never emit quote text or the whole-source handle. Do not quote unrelated evidence.
For image grounding give a coherent visual brief and unresolved composition question;
prepare an image_prompt only when requested. No edit or generation happened.
"""
AUTHORING_INSTRUCTIONS = """Prepare only the requested editable Plan fragment at focused_edit_target.
The current_page_draft is the author's latest working copy and primary writing context.
A body_path refers to the already supplied committed blocks; do not repeat that body.
Keep saved Plan excerpts, retrieved World evidence, played outcomes and proposed writing distinct.
Return the same strict evidence JSON contract: each text-bearing segment is a complete literal
Markdown block of the proposed fragment, in reading order. Ground factual blocks using their
actual supplied selectors; mark invented possibilities as proposals. Tables use Markdown rows.
Preserve the author's unselected text and preparation notes. For replacement, rewrite only the
captured selection or playable body; for insertion, produce the new fragment without repeating
the page. Do not add a chat acknowledgment, surrounding explanation, save claim or whole document.
Do not mint object IDs, dmb-node references, playable markers or unknown component markers.
Headings, prose, lists and ordinary editable tables are supported; preserve existing protected
tokens exactly when their captured selected content must be included. No page was saved.
"""
RULES_INSTRUCTIONS = '''A Rules lookup was performed. Return its answer using exactly this outer object:
{"schema":"dmb_rules_mixed_answer_v1","base_output": BASE_OR_NULL,
"rules_segments":[...],"ordered_refs":[...]}. BASE_OR_NULL follows the Plan answer contract above.
A Rules claim is {"kind":"rules_claim","text":"prose","support_ids":["exact support_id"]}.
Only supports in the Rules frame establish Rules evidence; preserve their applicability.
Interpretation or gaps use {"kind":"rules_context","text":"prose","category":"interpretation or gap or connective"}.
Do not turn campaign prose into a Rules claim. Ignore Rules material irrelevant to the question.
ordered_refs includes {"domain":"base","segment_index":null} once if base_output is present,
and {"domain":"rules","segment_index":0} for every Rules segment, in reading order.
'''


@dataclass(frozen=True)
class PlanClaimEvidence:
    provider_attempt_id: UUID
    envelope_sha256: str
    context_receipt_sha256: str
    graph_revision: str | None
    closures: tuple
    session_titles: tuple = ()
    passages: tuple = ()
    source_partial: bool = False
    authored: tuple = ()
    current_policy: bool | str = False
    native_sections: tuple = ()
    body_excerpts: tuple = ()
    native_statements: tuple = ()
    native_assertions: tuple = ()


class PlanWriterProvider(OpenAITextProvider):
    """Buddy owns message assembly and retains the actual official SDK response.

    The pinned GE adapter owns guarded SDK IO. Its request-assembly seam accepts
    our text-only messages, rather than encoding an entire transcript as prose.
    No installed dependency is patched and no SDK response is reconstructed.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.actual_response = None
        self._selected_reply = None
        original = self._client.responses.create
        async def capture(**options):
            self.actual_response = None
            self._selected_reply = None
            self.actual_response = await original(**options)
            return self.actual_response
        self._client.responses.create = capture

    def _result_from_response(self, response):
        self._selected_reply = None
        result = super()._result_from_response(response)
        self._selected_reply = (response, result.text)
        return result

    def consume_selected_text(self, response):
        selected = self._selected_reply
        self._selected_reply = None
        if selected is None or selected[0] is not response:
            raise _ReplyRejected('plan_writer_response_identity_mismatch',
                'Plan writer has no complete exact SDK reply')
        return selected[1]

    def _request_kwargs(self, call, *, streaming=False):
        options = super()._request_kwargs(call, streaming=streaming)
        messages = strict_json(call.user_prompt)
        if not isinstance(messages, list) or any(set(row) != {"role", "content"}
                or row['role'] != 'user' or not isinstance(row['content'], str) for row in messages):
            raise ValueError("Plan writer requires exact text evidence messages")
        options['input'] = messages
        options['service_tier'] = 'fast'
        return options


class _ReplyRejected(ValueError):
    """Fixed local diagnostics; never expose arbitrary provider/exception text."""
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


class PlanJevWriter:
    def __init__(self, adapter, proof, rules):
        self.adapter, self.proof, self.rules = adapter, proof, rules
        self.shared = type(adapter.fence.turn.graph_context_receipt) is t.SurfaceNativeContextReceiptV1
        rule_frame = rules.frame()
        self.projection = None
        if self.shared:
            from application_state.agent_conversation.native_writer import model_frame, model_work_frame
            from application_state.agent_conversation.plan_writer_output_schema import native_output_format
            turn=adapter.fence.turn
            self.frame=model_frame(turn.graph_context_receipt,turn.graph_context_execution)
            self.work_frame=model_work_frame(turn.graph_context_receipt,turn.graph_context_execution,
                provenance=turn.provenance,idempotency_key=turn.idempotency_key,work_proof=proof,
                world_id=turn.world_id,conversation_id=turn.conversation_id,turn_id=turn.turn_id,attempt=turn.attempt)
            self.output_format=native_output_format(self.frame,rule_frame,self.work_frame)
            frames=(self.frame,rule_frame,self.work_frame)
        else:
            self.projection = project(adapter.fence.turn, proof, adapter.context_capture.trace.model_dump(mode='json'))
            self.frame=self.projection.frame
            from application_state.agent_conversation.plan_writer_output_schema import output_format
            self.output_format=output_format(self.frame,rule_frame)
            frames=(self.frame,rule_frame)
        self.messages=[{'role':'user','content':canonical_bytes(frame).decode()} for frame in frames]
        self.messages.append({'role':'user','content':'Return JSON.'})
        from application_state.agent_conversation.surface_evidence_answer import PLAN_INSTRUCTIONS, BODY_INSTRUCTIONS
        instructions = INSTRUCTIONS.replace(EVIDENCE_INSTRUCTIONS,
            BODY_INSTRUCTIONS if isinstance(adapter.fence.turn.graph_context_receipt, t.PlanSourceContextReceiptV1) else PLAN_INSTRUCTIONS)
        instructions = instructions.replace('exact block_handle', 'exact selection_id')
        if isinstance(adapter.fence.turn.graph_context_receipt, t.PlanSourceContextReceiptV1):
            instructions = instructions.replace('native_source_claim uses its selected section_handles',
                'native_body_claim uses its selected excerpt_handles')
        if (self.work_frame if self.shared else self.frame).get('requested_work') == 'clarify':
            instructions += '\nAsk the specific clarifying question needed to resolve the intended work or destination. Keep it in conversation; do not draft the page yet.'
        if getattr(rules,'authoring',None) is not None:
            instructions=instructions.replace('Answer the current co-GM question directly using relevant supplied material.',
                'Write the requested Plan fragment using the current page and relevant supplied material.')
            instructions=instructions.replace('For image grounding give a coherent visual brief and unresolved composition question;\nprepare an image_prompt only when requested. No edit or generation happened.\n','')
            instructions += '\n' + AUTHORING_INSTRUCTIONS
        if isinstance(adapter.fence.turn.graph_context_receipt, t.PlanNativeContextReceiptV1):
            from application_state.agent_conversation.native_plan_statements import INSTRUCTIONS as STATEMENT_INSTRUCTIONS
            from application_state.agent_conversation.native_plan_statements import POLICY as STATEMENT_POLICY
            from application_state.agent_conversation.surface_evidence_answer import BODY_POLICY
            instructions = instructions.replace(BODY_POLICY, STATEMENT_POLICY) + '\n' + STATEMENT_INSTRUCTIONS
        if self.frame.get('schema') == 'dmb_plan_jev_writer_frame_v8':
            from application_state.agent_conversation.native_plan_assertions import INSTRUCTIONS as ASSERTION_INSTRUCTIONS, POLICY as ASSERTION_POLICY
            instructions = instructions.replace(STATEMENT_POLICY, ASSERTION_POLICY) + '\n' + ASSERTION_INSTRUCTIONS
        if self.shared:
            from application_state.agent_conversation.native_writer import AUTHORING_GUIDANCE
            from application_state.agent_conversation.native_plan_statements import INSTRUCTIONS as STATEMENT_INSTRUCTIONS
            from application_state.agent_conversation.native_plan_assertions import INSTRUCTIONS as ASSERTION_INSTRUCTIONS
            from application_state.agent_conversation.surface_evidence_answer import BODY_POLICY
            instructions = SOURCE_ATTRIBUTION_INSTRUCTIONS + BODY_INSTRUCTIONS.replace(BODY_POLICY,self.frame['answer_policy']) + STATEMENT_INSTRUCTIONS + ASSERTION_INSTRUCTIONS + AUTHORING_GUIDANCE
            if self.work_frame.get('requested_work') == 'clarify':
                instructions += '\nAsk the specific clarifying question. Do not draft yet.'
            if getattr(rules,'authoring',None) is not None:
                instructions += '\n' + AUTHORING_INSTRUCTIONS
        self.instructions = '\n\n'.join((BUDDY_SYSTEM_PROMPT, instructions,
            RULES_INSTRUCTIONS if rule_frame.lookups else '')) + ('' if getattr(rules,'authoring',None) is not None else IMAGE_DIRECTION_INSTRUCTIONS)
        self.model = adapter._broker_execution().policy.provider_roles.writer.model
        self.prepared = self.authorization = self.call = self.received_event = None
        self._usage_recorded = False
        self._draft_capture_attempted = False
        self.output_limit_exceeded = False
        self.target_changed = False

    def authorize(self, prepared):
        from generationengine.text_dispatch import PreparedTextDispatch
        from .agent_turn_service import _json_node_count, _require_fresh_execution_append
        if (self.prepared is not None or self.adapter.failure is not None
                or getattr(self.adapter, "_build_native_acquisition_services", None) is not None
                or getattr(self.adapter, "_plan_graph_read_services", None) is not None):
            return False
        if (not isinstance(prepared, PreparedTextDispatch)
                or (prepared.provider, prepared.model, prepared.api_mode, prepared.method, prepared.url)
                != ('openai', self.model, 'responses', 'POST', 'https://api.openai.com/v1/responses')
                or len(prepared.body) != prepared.body_size or sha256(prepared.body).hexdigest() != prepared.body_sha256):
            raise ValueError('Plan writer actual dispatch identity differs')
        a = self.adapter
        expected = {'model': self.model, 'input': self.messages, 'instructions': self.instructions,
            'max_output_tokens': a.budget['outputReserveTokens'], 'text': {'format': self.output_format},
            'tools': [], 'stream': False, 'reasoning': {'effort': 'none'}, 'service_tier': 'fast'}
        if strict_json(prepared.body.decode()) != expected:
            raise ValueError('Plan writer actual request differs from staged evidence/instructions')
        projection = self.projection
        estimate = len(prepared.body) + 64 * (1 + _json_node_count(expected))
        if estimate + a.budget['outputReserveTokens'] > a.budget['contextLimitTokens']:
            raise ValueError('Plan writer exceeds the existing provider context allowance')
        if self.shared:
            from application_state.errors import ApplicationStateConflictError
            from application_state.agent_conversation.native_execution import NativeWriterAuthorizedV1
            event=NativeWriterAuthorizedV1(event_id=uuid4(),sequence=len(a._broker_execution().events),
                provider_attempt_id=UUID(prepared.attempt_id),envelope_sha256=prepared.body_sha256,
                serializer_version='openai-sdk-json-v1',provider='openai',model=self.model,api_mode='responses',
                tool_schema_sha256=canonical_sha256([]),input_accounting_kind='conservative_upper_bound',
                input_estimator=a.budget['estimator'],input_tokens=estimate,
                output_token_reserve=a.budget['outputReserveTokens'],frame_sha256=canonical_sha256(self.frame),
                included_graph_event_ids=[],included_source_read_event_ids=[],included_assertion_ids=[],
                included_relationship_ids=[],included_evidence_ref_ids=[],native_read_event_ids=tuple(sorted(
                    (e.event_id for e in a._broker_execution().events if isinstance(e,(
                        t.NativeBodyReadObservedV1,t.NativePlanStatementReadObservedV1,t.NativePlanAssertionReadObservedV1))),key=str)))
            try:
                a.turn=_require_fresh_execution_append(a.fence.append('authorize_native_writer','authorization',event,
                    expected_rules_revision=self.rules.native.record.revision,
                    prepared_request_json=prepared.body.decode(),work_proof=self.proof,
                    **({'authoring_reservation':{'action_id':self.rules.authoring[0].action_id,'capture':self.rules.authoring[1]}}
                        if self.rules.authoring is not None else {})))
            except ApplicationStateConflictError:
                self.target_changed=self.rules.authoring is not None
                raise
            a.last_provider_attempt_id=event.provider_attempt_id
            view={'provider':'openai','model':self.model,'apiMode':'responses','payloadJson':prepared.body.decode(),
                  'payloadSha256':prepared.body_sha256,'payloadUtf8Bytes':prepared.body_size}
            self.rules.authorize(view)
            a._capture_prepared_prompt(view,event)
            self.prepared,self.authorization=prepared,event
            return True
        native_plan = isinstance(a._broker_receipt(), t.PlanNativeContextReceiptV1)
        from application_state.agent_conversation.native_plan_assertions import NativePlanQueryV2
        assertions = native_plan and isinstance(a._broker_receipt().native_query, NativePlanQueryV2)
        writer_type = t.PlanNativeWriterAuthorizedV2 if assertions else t.PlanNativeWriterAuthorizedV1 if native_plan else t.PlanJevWriterAuthorizedV2
        event = writer_type(kind='plan_native_writer_authorized_v2' if assertions else 'plan_native_writer_authorized_v1' if native_plan else 'plan_jev_writer_authorized_v2', event_id=uuid4(),
            sequence=len(a._broker_execution().events) + (1 if isinstance(a._broker_receipt(), t.PlanSourceContextReceiptV1) else 0),
            provider_attempt_id=UUID(prepared.attempt_id),
            envelope_sha256=prepared.body_sha256, serializer_version='openai-sdk-json-v1',
            provider='openai', model=self.model, api_mode='responses', tool_schema_sha256=sha256(b'[]').hexdigest(),
            input_accounting_kind='conservative_upper_bound', input_estimator=a.budget['estimator'],
            input_tokens=estimate, output_token_reserve=a.budget['outputReserveTokens'],
            frame_sha256=canonical_sha256(projection.frame), included_graph_event_ids=list(projection.graph_event_ids),
            included_source_read_event_ids=[e.event_id for e in a._broker_execution().events
                if isinstance(e, t.ValidatedSourceReadEventV2) and e.event_id in projection.source_event_ids],
            included_source_reuse_event_ids=[e.event_id for e in a._broker_execution().events
                if isinstance(e, t.SourcePassageReuseEventV1) and e.event_id in projection.source_event_ids], included_assertion_ids=list(projection.assertion_ids),
            included_relationship_ids=list(projection.relationship_ids), included_evidence_ref_ids=list(projection.evidence_ref_ids),
            **({'native_assertion_read_event_ids': [e.event_id for e in a._broker_execution().events
                if isinstance(e, t.NativePlanAssertionReadObservedV1)]} if assertions else {}),
            **({'native_statement_read_event_ids': [e.event_id for e in a._broker_execution().events
                if isinstance(e, t.NativePlanStatementReadObservedV1)]} if native_plan else {}))
        view = {'provider':'openai','model':self.model,'apiMode':'responses','payloadJson':prepared.body.decode(),
                'payloadSha256':prepared.body_sha256,'payloadUtf8Bytes':prepared.body_size}
        from application_state.errors import ApplicationStateConflictError
        try:
            a.turn = _require_fresh_execution_append(a.fence.append('authorize_plan_jev_writer','authorization',event,
                producer_proof={'prepared_request_json':view['payloadJson'],'evidence':self.proof},
                **({'authoring_reservation':{'action_id':self.rules.authoring[0].action_id,'capture':self.rules.authoring[1]}}
                    if getattr(self.rules,'authoring',None) is not None else {})))
        except ApplicationStateConflictError:
            self.target_changed = getattr(self.rules, 'authoring', None) is not None
            raise
        a.last_provider_attempt_id = event.provider_attempt_id
        self.rules.authorize(view)
        a._capture_prepared_prompt(view, event)
        from application_state.agent_conversation.session_citation_labels import producing_session_titles
        from application_state.agent_conversation.surface_source_answer import producing_passages
        passages, source_partial = producing_passages(a.turn, event, view["payloadJson"])
        from application_state.agent_conversation.native_source_answer import producing_sections
        from application_state.agent_conversation.surface_evidence_answer import producing_authored, require_current_policy
        from application_state.agent_conversation.plan_source_context import capability_bases
        from application_state.agent_conversation.native_corpus import producing_bodies, body_input_partial
        from application_state.agent_conversation.native_plan_statements import producing_reads, input_partial
        from application_state.agent_conversation.native_plan_assertions import producing_reads as assertion_reads, input_partial as assertion_partial
        graph = capability_bases(a._broker_receipt()).graph
        a.build_claim_evidence[event.provider_attempt_id] = PlanClaimEvidence(event.provider_attempt_id,
            event.envelope_sha256, a._broker_execution().context_receipt_sha256,
            graph.graph_authority.graph_revision if graph is not None else None, projection.closures,
            producing_session_titles(a.turn, event, view["payloadJson"]), passages, source_partial or body_input_partial(a._broker_execution()) or input_partial(a.turn) or assertion_partial(a.turn),
            producing_authored(a.turn, event, view["payloadJson"]), require_current_policy(a.turn, event, view["payloadJson"]),
            producing_sections(a.turn,event,view["payloadJson"]), producing_bodies(a.turn,event,view["payloadJson"]),
            producing_reads(a.turn,event,view["payloadJson"]),
            native_assertions=assertion_reads(a.turn,event,view["payloadJson"]))
        self.prepared, self.authorization = prepared, event
        return True

    def record(self, event):
        if self.prepared is None or event.request != self.prepared: return False
        transition = {'sending':'sdk_entered','response_received':'response_received',
            'known_not_sent':'known_not_sent','outcome_unknown':'outcome_unknown'}.get(event.outcome)
        if self.shared and transition == 'response_received':
            # HTTP receipt precedes SDK parsing. Keep APP uncertain until the
            # actual complete selected text can acknowledge its exact digest.
            if self.received_event is not None:
                return False
            self.received_event=event
            return True
        acknowledged = transition is not None and self.adapter.record_lifecycle({'transition':transition,
            'statusCode':event.http_status,'runtimeApiRequestId':f'generationengine:{self.prepared.attempt_id}'})
        if acknowledged and transition == 'sdk_entered':
            self.call = {'provider':'openai','requested_model':self.model,
                'runtime_api_request_id':f'generationengine:{self.prepared.attempt_id}',
                'status':'error','usage':{'status':'unavailable'}}
        return acknowledged

    def capture(self, result, response, provider):
        if self.prepared is None or response is None or response.status != 'completed' or response.error is not None:
            raise _ReplyRejected('plan_writer_response_incomplete', 'Plan writer has no complete exact SDK reply')
        if response.model != self.model:
            raise _ReplyRejected('plan_writer_response_model_mismatch', 'Plan writer has no complete exact SDK reply')
        selected_text = provider.consume_selected_text(response)
        if (result.observation.state.value != 'completed' or result.observation.retry_count != 0
                or result.observation.provider_attempt_count != 1
                or result.text != selected_text or not result.text):
            raise _ReplyRejected('plan_writer_response_identity_mismatch', 'Plan writer has no complete exact SDK reply')
        for item in response.output:
            if item.type == 'reasoning': continue
            if (item.type != 'message' or item.role != 'assistant' or item.status != 'completed'
                    or any(part.type != 'output_text' for part in item.content)):
                raise _ReplyRejected('plan_writer_unexpected_output', 'Plan writer reply contains an unexpected tool/refusal message')
        raw = result.text
        if self.shared:
            received,self.received_event=self.received_event,None
            if received is None or not self.adapter.record_lifecycle({
                    'transition':'response_received','statusCode':received.http_status,
                    'runtimeApiRequestId':f'generationengine:{self.prepared.attempt_id}',
                    'responseSha256':sha256(raw.encode()).hexdigest()}):
                raise _ReplyRejected('plan_writer_native_capture_unacknowledged','Selected writer output was not acknowledged')
        native = self.rules.native
        reply = NativeProviderReply(str(native.authorization_id), f'generationengine:{self.prepared.attempt_id}',
            'openai',self.model,'responses',self.prepared.body_sha256,'stop','answered',raw,sha256(raw.encode()).hexdigest(),len(raw.encode()),())
        if not self.rules.capture_reply(reply):
            raise _ReplyRejected('plan_writer_native_capture_unacknowledged',
                'Plan writer reply capture was not acknowledged')
        return reply

    def capture_draft(self, response):
        """Debug only: retain actual unvalidated text before receipt/answer checks."""
        text = getattr(response, "output_text", None)
        if (not self._draft_capture_attempted and self.authorization is not None
                and isinstance(text, str) and text):
            self._draft_capture_attempted = True
            self.adapter.context_capture.answer_draft(
                text, producing_provider_attempt_id=self.authorization.provider_attempt_id)

    def observe(self, observation, *, status):
        if self.call is None or observation is None: return
        counts={'input_tokens':observation.input_tokens,'output_tokens':observation.output_tokens}
        usage={'status':'reported' if any(v is not None for v in counts.values()) else 'unavailable',**counts}
        for field in ('cached_input_tokens', 'reasoning_tokens'):
            value = getattr(observation, field, None)
            if value is not None: usage[field] = value
        if observation.input_tokens is not None and observation.cached_input_tokens is not None:
            usage['uncached_input_tokens'] = observation.input_tokens - observation.cached_input_tokens
        if all(v is not None for v in counts.values()): usage['total_tokens']=sum(counts.values())
        self.call.update(status=status,response_model=observation.response_model,usage=usage,
            request_summary={'reasoning_effort': 'none'})

    async def run(self, *, transport=None, api_key=None):
        from generationengine import GenerationClient, TextRequest
        from generationengine.text_dispatch import TextDispatchGate
        async def authorize(prepared): return self.authorize(prepared)
        async def record(event): return self.record(event)
        options = {'dispatch_gate':TextDispatchGate(authorize,record),'transport':transport}
        if api_key is not None: options['api_key'] = api_key
        provider = PlanWriterProvider(**options)
        client = GenerationClient(text_providers={'openai':provider})
        started = perf_counter()
        stage = "generation"
        try:
            result = await client.generate_structured(TextRequest(provider='openai',model=self.model,
                user_prompt=json.dumps(self.messages,ensure_ascii=False),system_prompt=self.instructions,
                temperature=None,reasoning_effort='none',max_output_tokens=self.adapter.budget['outputReserveTokens'],
                json_schema=self.output_format['schema'],schema_name=self.output_format['name'],
                max_conformance_retries=0,max_transport_retries=0))
            self.observe(result.observation,status='ok')
            if self.call is not None and provider.actual_response is not None:
                self.call['response_service_tier'] = provider.actual_response.service_tier
            stage = 'draft'
            if not self.shared:
                self.capture_draft(provider.actual_response)
            stage = 'capture'
            reply = self.capture(result,provider.actual_response,provider)
            if self.shared:
                self.capture_draft(provider.actual_response)
            if self.call is not None:
                self.call['duration_ms']=(perf_counter()-started)*1000
                self.adapter.context_capture.provider_usage([self.call])
                self._usage_recorded = True
        except BaseException as exc:
            response=provider.actual_response
            if response is not None and getattr(response,'status',None)=='incomplete':
                self.output_limit_exceeded = getattr(getattr(response,'incomplete_details',None),'reason',None)=='max_output_tokens'
            self.observe(getattr(exc,'observation',None),status='error')
            self.adapter.context_capture.observe({'kind':'failure',
                'phase':'provider' if stage == 'generation' else 'delivery',
                'code':exc.code if isinstance(exc, _ReplyRejected) else f'plan_writer_{stage}_rejected'})
            try:
                self.capture_draft(response)
            except BaseException as draft_error:
                self.adapter.context_capture.observe({'kind':'failure', 'phase':'delivery',
                    'code':'plan_writer_draft_rejected'})
                raise exc from draft_error
            raise
        finally:
            try:
                if self.call is not None and not self._usage_recorded:
                    self.call['duration_ms']=(perf_counter()-started)*1000
                    self.adapter.context_capture.provider_usage([self.call])
            finally:
                try:
                    await client.aclose()
                except BaseException:
                    self.adapter.context_capture.observe({"kind":"failure", "phase":"delivery",
                        "code":"plan_writer_cleanup_rejected"})
                    raise
        try:
            final_turn=self.adapter.stop()
            if final_turn is None: raise ValueError('Plan writer lost its current completion claim')
            return self.rules.complete(final_turn,reply,**({"work_proof":self.proof} if self.shared else {}))
        except BaseException:
            self.adapter.context_capture.observe({'kind':'failure', 'phase':'delivery',
                'code':'plan_writer_completion_rejected'})
            raise
