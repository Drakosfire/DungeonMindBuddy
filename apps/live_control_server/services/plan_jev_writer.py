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
from .hermes_product_prompt import BUDDY_SYSTEM_PROMPT
from .native_rules_capture import NativeProviderReply

from application_state.agent_conversation.surface_evidence_answer import INSTRUCTIONS as EVIDENCE_INSTRUCTIONS

INSTRUCTIONS = SOURCE_ATTRIBUTION_INSTRUCTIONS + EVIDENCE_INSTRUCTIONS + """
Answer the current co-GM question directly using relevant supplied material. Preserve
beliefs, time and authored versus played events. Entity labels and dialogue are
navigation/context, not evidence. Read short evidence handles only as passage joins.
For authored excerpts, select an exact block_handle from the ordered authored blocks.
The host supplies its literal text; never emit quote text or the whole-source handle. Do not quote unrelated evidence.
For image grounding give a coherent visual brief and unresolved composition question;
prepare an image_prompt only when requested. No edit or generation happened.
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
    graph_revision: str
    closures: tuple
    session_titles: tuple = ()
    passages: tuple = ()
    source_partial: bool = False
    authored: tuple = ()
    current_policy: bool | str = False
    native_sections: tuple = ()


class PlanWriterProvider(OpenAITextProvider):
    """Buddy owns message assembly and retains the actual official SDK response.

    The pinned GE adapter owns guarded SDK IO. Its request-assembly seam accepts
    our text-only messages, rather than encoding an entire transcript as prose.
    No installed dependency is patched and no SDK response is reconstructed.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.actual_response = None
        original = self._client.responses.create
        async def capture(**options):
            self.actual_response = await original(**options)
            return self.actual_response
        self._client.responses.create = capture

    def _request_kwargs(self, call, *, streaming=False):
        options = super()._request_kwargs(call, streaming=streaming)
        messages = strict_json(call.user_prompt)
        if not isinstance(messages, list) or any(set(row) != {"role", "content"}
                or row['role'] != 'user' or not isinstance(row['content'], str) for row in messages):
            raise ValueError("Plan writer requires exact text evidence messages")
        options['input'] = messages
        options['service_tier'] = 'fast'
        return options


class PlanJevWriter:
    def __init__(self, adapter, proof, rules):
        self.adapter, self.proof, self.rules = adapter, proof, rules
        self.projection = project(adapter.fence.turn, proof, adapter.context_capture.trace.model_dump(mode='json'))
        rule_frame = rules.frame()
        self.messages = [{'role': 'user', 'content': canonical_bytes(self.projection.frame).decode()},
                         {'role': 'user', 'content': canonical_bytes(rule_frame).decode()},
                         {'role': 'user', 'content': 'Return JSON.'}]
        from application_state.agent_conversation.surface_evidence_answer import NATIVE_POLICY, NATIVE_INSTRUCTIONS
        instructions = (INSTRUCTIONS.replace(EVIDENCE_INSTRUCTIONS,NATIVE_INSTRUCTIONS)
            if self.projection.frame.get('answer_policy') == NATIVE_POLICY else INSTRUCTIONS)
        self.instructions = '\n\n'.join((BUDDY_SYSTEM_PROMPT, instructions,
            RULES_INSTRUCTIONS if rule_frame.lookups else ''))
        self.model = adapter._broker_execution().policy.provider_roles.writer.model
        self.prepared = self.authorization = self.call = None
        self._usage_recorded = False
        self.output_limit_exceeded = False

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
            'max_output_tokens': a.budget['outputReserveTokens'], 'text': {'format': {'type': 'json_object'}},
            'tools': [], 'stream': False, 'reasoning': {'effort': 'none'}, 'service_tier': 'fast'}
        if strict_json(prepared.body.decode()) != expected:
            raise ValueError('Plan writer actual request differs from staged evidence/instructions')
        projection = self.projection
        estimate = len(prepared.body) + 64 * (1 + _json_node_count(expected))
        if estimate + a.budget['outputReserveTokens'] > a.budget['contextLimitTokens']:
            raise ValueError('Plan writer exceeds the existing provider context allowance')
        event = t.PlanJevWriterAuthorizedV2(kind='plan_jev_writer_authorized_v2', event_id=uuid4(),
            sequence=len(a._broker_execution().events), provider_attempt_id=UUID(prepared.attempt_id),
            envelope_sha256=prepared.body_sha256, serializer_version='openai-sdk-json-v1',
            provider='openai', model=self.model, api_mode='responses', tool_schema_sha256=sha256(b'[]').hexdigest(),
            input_accounting_kind='conservative_upper_bound', input_estimator=a.budget['estimator'],
            input_tokens=estimate, output_token_reserve=a.budget['outputReserveTokens'],
            frame_sha256=canonical_sha256(projection.frame), included_graph_event_ids=list(projection.graph_event_ids),
            included_source_read_event_ids=[e.event_id for e in a._broker_execution().events
                if isinstance(e, t.ValidatedSourceReadEventV2) and e.event_id in projection.source_event_ids],
            included_source_reuse_event_ids=[e.event_id for e in a._broker_execution().events
                if isinstance(e, t.SourcePassageReuseEventV1) and e.event_id in projection.source_event_ids], included_assertion_ids=list(projection.assertion_ids),
            included_relationship_ids=list(projection.relationship_ids), included_evidence_ref_ids=list(projection.evidence_ref_ids))
        view = {'provider':'openai','model':self.model,'apiMode':'responses','payloadJson':prepared.body.decode(),
                'payloadSha256':prepared.body_sha256,'payloadUtf8Bytes':prepared.body_size}
        a.turn = _require_fresh_execution_append(a.fence.append('authorize_plan_jev_writer','authorization',event,
            producer_proof={'prepared_request_json':view['payloadJson'],'evidence':self.proof}))
        a.last_provider_attempt_id = event.provider_attempt_id
        self.rules.authorize(view)
        a._capture_prepared_prompt(view, event)
        from application_state.agent_conversation.session_citation_labels import producing_session_titles
        from application_state.agent_conversation.surface_source_answer import producing_passages
        passages, source_partial = producing_passages(a.turn, event, view["payloadJson"])
        from application_state.agent_conversation.native_source_answer import producing_sections
        from application_state.agent_conversation.surface_evidence_answer import producing_authored, require_current_policy
        a.build_claim_evidence[event.provider_attempt_id] = PlanClaimEvidence(event.provider_attempt_id,
            event.envelope_sha256, a._broker_execution().context_receipt_sha256,
            a._broker_receipt().graph_authority.graph_revision, projection.closures,
            producing_session_titles(a.turn, event, view["payloadJson"]), passages, source_partial,
            producing_authored(a.turn, event, view["payloadJson"]), require_current_policy(a.turn, event, view["payloadJson"]),
            producing_sections(a.turn,event,view["payloadJson"]))
        self.prepared, self.authorization = prepared, event
        return True

    def record(self, event):
        if self.prepared is None or event.request != self.prepared: return False
        transition = {'sending':'sdk_entered','response_received':'response_received',
            'known_not_sent':'known_not_sent','outcome_unknown':'outcome_unknown'}.get(event.outcome)
        acknowledged = transition is not None and self.adapter.record_lifecycle({'transition':transition,
            'statusCode':event.http_status,'runtimeApiRequestId':f'generationengine:{self.prepared.attempt_id}'})
        if acknowledged and transition == 'sdk_entered':
            self.call = {'provider':'openai','requested_model':self.model,
                'runtime_api_request_id':f'generationengine:{self.prepared.attempt_id}',
                'status':'error','usage':{'status':'unavailable'}}
        return acknowledged

    def capture(self, result, response):
        if (self.prepared is None or response is None or response.status != 'completed' or response.error is not None
                or response.model != self.model or result.observation.state.value != 'completed'
                or result.observation.retry_count != 0 or result.observation.provider_attempt_count != 1
                or result.text != response.output_text or not result.text):
            raise ValueError('Plan writer has no complete exact SDK reply')
        for item in response.output:
            if item.type == 'reasoning': continue
            if (item.type != 'message' or item.role != 'assistant' or item.status != 'completed'
                    or any(part.type != 'output_text' for part in item.content)):
                raise ValueError('Plan writer reply contains an unexpected tool/refusal message')
        raw = result.text
        native = self.rules.native
        reply = NativeProviderReply(str(native.authorization_id), f'generationengine:{self.prepared.attempt_id}',
            'openai',self.model,'responses',self.prepared.body_sha256,'stop','answered',raw,sha256(raw.encode()).hexdigest(),len(raw.encode()),())
        if not self.rules.capture_reply(reply): raise ValueError('Plan writer reply capture was not acknowledged')
        self.adapter.context_capture.answer_draft(raw, producing_provider_attempt_id=self.authorization.provider_attempt_id)
        return reply

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
        try:
            result = await client.generate_text(TextRequest(provider='openai',model=self.model,
                user_prompt=json.dumps(self.messages,ensure_ascii=False),system_prompt=self.instructions,
                temperature=None,reasoning_effort='none',max_output_tokens=self.adapter.budget['outputReserveTokens'],
                json_object=True,max_conformance_retries=0,max_transport_retries=0))
            self.observe(result.observation,status='ok')
            if self.call is not None and provider.actual_response is not None:
                self.call['response_service_tier'] = provider.actual_response.service_tier
            reply = self.capture(result,provider.actual_response)
            if self.call is not None:
                self.call['duration_ms']=(perf_counter()-started)*1000
                self.adapter.context_capture.provider_usage([self.call])
                self._usage_recorded = True
        except BaseException as exc:
            self.observe(getattr(exc,'observation',None),status='error')
            response=provider.actual_response
            if response is not None and getattr(response,'status',None)=='incomplete':
                self.output_limit_exceeded = getattr(getattr(response,'incomplete_details',None),'reason',None)=='max_output_tokens'
                partial=getattr(response,'output_text',None)
                if partial and self.authorization is not None:
                    self.adapter.context_capture.answer_draft(partial,
                        producing_provider_attempt_id=self.authorization.provider_attempt_id)
            raise
        finally:
            try:
                if self.call is not None and not self._usage_recorded:
                    self.call['duration_ms']=(perf_counter()-started)*1000
                    self.adapter.context_capture.provider_usage([self.call])
            finally: await client.aclose()
        final_turn=self.adapter.stop()
        if final_turn is None: raise ValueError('Plan writer lost its current completion claim')
        return self.rules.complete(final_turn,reply)
