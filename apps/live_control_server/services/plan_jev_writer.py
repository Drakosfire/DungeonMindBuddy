"""One exact Plan writer dispatch; no retrieval tools, retries or repair loop."""
from contextlib import nullcontext
from dataclasses import dataclass
from hashlib import sha256
import json
from time import monotonic, perf_counter
from uuid import UUID, uuid4

from generationengine.providers.openai_text import OpenAITextProvider
from application_state.agent_conversation import types as t
from application_state.agent_conversation.plan_jev_graph_packet import project
from application_state.agent_conversation.rules_authority_types import canonical_bytes, canonical_sha256
from application_state.agent_conversation.source_writer_output import strict_json
from application_state.agent_conversation.surface_source_answer import SOURCE_ATTRIBUTION_INSTRUCTIONS
from .semantic_block_writing import SEMANTIC_BLOCK_WRITING
from .hermes_product_prompt import BUDDY_SYSTEM_PROMPT, IMAGE_DIRECTION_INSTRUCTIONS
from .native_rules_capture import NativeProviderReply
from .agent_turn_trace import host_work_observer
from .build_jev_writer import WriterCapacityError, WriterAccountingError

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
Preserve the author's unselected text and preparation notes. For selection replacement, return
only the replacement for the captured selection. For a playable body replacement, return the
complete captured body and copy all Markdown outside the requested change verbatim, including
existing callout titles and bodies, prose, tables, and artwork references. When adding a note or
passage to a playable body, keep every existing block in its original order and insert the
requested material as a separate block. For an insertion target, return only the new fragment
without repeating the page. Do not add a chat acknowledgment, surrounding explanation, save claim
or whole document.
Do not mint object IDs, dmb-node references, playable markers or unknown component markers.
Headings, prose, lists and ordinary editable tables are supported; preserve existing protected
tokens exactly when their captured selected content must be included. No page was saved.
""" + SEMANTIC_BLOCK_WRITING
RULES_INSTRUCTIONS = """A Rules lookup was performed. Use only supplied Rules supports for Rules claims,
preserving their applicability. Keep interpretation and gaps distinct from supported
Rules claims; campaign prose does not establish Rules. Ignore irrelevant Rules material.
Use the supplied native schema to combine the campaign response and relevant Rules
segments in reading order. Every included segment must appear once in that order.
"""


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


class CapturedWriterProvider(OpenAITextProvider):
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
        self.actual_response = response
        self._selected_reply = (response, result.text)
        return result

    def consume_selected_text(self, response):
        selected = self._selected_reply
        self._selected_reply = None
        if selected is None or selected[0] is not response:
            raise _ReplyRejected('plan_writer_response_identity_mismatch',
                'Plan writer has no complete exact SDK reply')
        return selected[1]

    def consume_completed_text(self, response, model):
        """Validate the actual SDK final before a domain accepts selected text."""
        if response is None or response.status != 'completed' or response.error is not None:
            raise _ReplyRejected('plan_writer_response_incomplete', 'Writer has no complete exact SDK reply')
        if response.model != model:
            raise _ReplyRejected('plan_writer_response_model_mismatch', 'Writer response model differs')
        selected_text = self.consume_selected_text(response)
        for item in response.output:
            if item.type == 'reasoning':
                continue
            if (item.type != 'message' or item.role != 'assistant' or item.status != 'completed'
                    or any(part.type != 'output_text' for part in item.content)):
                raise _ReplyRejected('plan_writer_unexpected_output', 'Writer reply contains an unexpected tool/refusal message')
        return selected_text


class PlanWriterProvider(CapturedWriterProvider):
    """Plan owns its evidence-message assembly; final SDK capture is shared."""
    def _request_kwargs(self, call, *, streaming=False):
        options = super()._request_kwargs(call, streaming=streaming)
        messages = strict_json(call.user_prompt)
        if not isinstance(messages, list) or any(set(row) != {"role", "content"}
                or row['role'] not in ('user', 'assistant') or not isinstance(row['content'], str) for row in messages):
            raise ValueError("Plan writer requires exact text evidence messages")
        options['input'] = messages
        options['service_tier'] = 'fast'
        return options


class _ReplyRejected(ValueError):
    """Fixed local diagnostics; never expose arbitrary provider/exception text."""
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


def authorize_native_writer(adapter, rules, proof, prepared, expected, frame, *,
                            compact_plan_editor_prose=None, compact_plan_graph_qualifications=None,
                            deduplicate_plan_recap_prose=None):
    """One native admission for the exact SDK input; output schemas stay owned."""
    from generationengine.text_dispatch import PreparedTextDispatch
    from .agent_turn_service import _json_node_count, _require_fresh_execution_append
    from application_state.agent_conversation.native_execution import NativeWriterAuthorizedV1, native_read_event_ids
    policy=adapter._broker_execution().policy
    model=policy.provider_roles.writer.model
    budget=policy.writer_context_budget
    reserve=budget.output_reserve_tokens if budget is not None else adapter.budget['outputReserveTokens']
    limit=budget.context_limit_tokens if budget is not None else adapter.budget['contextLimitTokens']
    if (not isinstance(prepared,PreparedTextDispatch)
            or (prepared.provider,prepared.model,prepared.api_mode,prepared.method,prepared.url)
                !=('openai',model,'responses','POST','https://api.openai.com/v1/responses')
            or len(prepared.body)!=prepared.body_size or sha256(prepared.body).hexdigest()!=prepared.body_sha256
            or strict_json(prepared.body.decode())!=expected):
        raise ValueError('Native writer actual request differs from its staged owner request')
    from application_state.agent_conversation.native_writer import validate_output_request
    validate_output_request(expected,reserve)
    from application_state.agent_conversation.native_execution import NativeWriterEstimatedBudgetV1
    if isinstance(budget, NativeWriterEstimatedBudgetV1):
        from .build_jev_accounting import ExperimentalAccounting
        accounting = getattr(adapter, '_build_jev_accounting', None)
        if (not isinstance(accounting, ExperimentalAccounting)
                or accounting.descriptor != policy.controller_continuation_accounting.model_dump(mode='json')
                or accounting.tokenizer_version != budget.tokenizer_version):
            raise WriterAccountingError('Native writer requires its prepared offline accounting; the retained request was not sent.')
        try:
            from application_state.agent_conversation.build_proposal_input import proposal_packet_text
            if isinstance(expected.get('input'), list) and proposal_packet_text(expected) is not None:
                # The image is encoded as pixels by the provider. Counting its base64
                # as prose would reject valid images before SDK dispatch.
                estimate = accounting.estimate({**expected, 'input': proposal_packet_text(expected)}) + 4096
            else:
                estimate = accounting.estimate(expected)
        except Exception as exc:
            raise WriterAccountingError('Native writer input could not be counted; the retained request was not sent.') from exc
        input_kind, estimator = 'estimated_token_count', budget.estimator
    else:
        estimate=len(prepared.body)+64*(1+_json_node_count(expected))
        input_kind, estimator = 'conservative_upper_bound', adapter.budget['estimator']
    if limit is not None and estimate+reserve>limit:
        raise WriterCapacityError('Native writer exceeds the existing provider context allowance. The request is retained; the writing provider was not called. Narrow the requested context before retrying.',
            code='build_writer_context_over_budget', actual=estimate+reserve, limit=limit)
    from application_state.agent_conversation.native_execution import NativeBuildActionV1, NativeBuildWriterAuthorizedV2
    from application_state.agent_conversation.native_build_work_view import frame_in_request, is_semantic_frame
    from application_state.agent_conversation.build_proposal_input import proposal_packet_text
    build_text = proposal_packet_text(expected)
    work_view = strict_json(build_text).get('surface_work') if build_text is not None else frame_in_request(expected)
    writer_type, work_commitment = NativeWriterAuthorizedV1, {}
    if type(policy.action) is NativeBuildActionV1 and is_semantic_frame(work_view):
        from application_state.agent_conversation.native_writer import model_work_frame
        turn=adapter.fence.turn
        host_work=model_work_frame(turn.graph_context_receipt,turn.graph_context_execution,
            provenance=turn.provenance,idempotency_key=turn.idempotency_key,work_proof=proof,
            world_id=turn.world_id,conversation_id=turn.conversation_id,turn_id=turn.turn_id,attempt=turn.attempt,
                play_context_receipt=turn.play_context_receipt if turn.graph_context_receipt.work_context.surface_id=='play' else None)
        writer_type=NativeBuildWriterAuthorizedV2
        work_commitment={'work_frame_sha256':canonical_sha256(host_work)}
    event=writer_type(event_id=uuid4(),sequence=len(adapter._broker_execution().events),
        provider_attempt_id=UUID(prepared.attempt_id),envelope_sha256=prepared.body_sha256,
        serializer_version='openai-sdk-json-v1',provider='openai',model=model,api_mode='responses',
        tool_schema_sha256=canonical_sha256([]),input_accounting_kind=input_kind,
        input_estimator=estimator,input_tokens=estimate,output_token_reserve=reserve,
        frame_sha256=canonical_sha256(frame),included_graph_event_ids=[],included_source_read_event_ids=[],
        included_assertion_ids=[],included_relationship_ids=[],included_evidence_ref_ids=[],
        native_read_event_ids=native_read_event_ids(adapter._broker_execution().events),
        compact_plan_editor_prose=compact_plan_editor_prose,
        compact_plan_graph_qualifications=compact_plan_graph_qualifications,
        deduplicate_plan_recap_prose=deduplicate_plan_recap_prose, **work_commitment)
    adapter.turn=_require_fresh_execution_append(adapter.fence.append('authorize_native_writer','authorization',event,
        expected_rules_revision=rules.native.record.revision,prepared_request_json=prepared.body.decode(),work_proof=proof,
        **({'authoring_reservation':{'action_id':rules.authoring[0].action_id,'capture':rules.authoring[1]}}
            if rules.authoring is not None else {})))
    adapter.last_provider_attempt_id=event.provider_attempt_id
    view=dict(provider='openai',model=model,apiMode='responses',payloadJson=prepared.body.decode(),
        payloadSha256=prepared.body_sha256,payloadUtf8Bytes=prepared.body_size)
    rules.authorize(view)
    adapter._capture_prepared_prompt(view,event)
    return event


def selected_writer_text(result,response,provider,model):
    """Direct writer callers consume the one complete actual SDK selection."""
    selected=provider.consume_completed_text(response,model)
    if (result.observation.state.value!='completed' or result.observation.retry_count!=0
            or result.observation.provider_attempt_count!=1 or result.text!=selected or not selected):
        raise _ReplyRejected('plan_writer_response_identity_mismatch','Writer has no complete exact SDK reply')
    return selected


def capture_native_reply(adapter,rules,prepared,received,raw):
    """Acknowledge only a domain-validated complete selected SDK final."""
    if received is None or not adapter.record_lifecycle(dict(transition='response_received',
            statusCode=received.http_status,runtimeApiRequestId=f'generationengine:{prepared.attempt_id}',
            responseSha256=sha256(raw.encode()).hexdigest())):
        raise _ReplyRejected('plan_writer_native_capture_unacknowledged','Selected writer output was not acknowledged')
    reply=NativeProviderReply(str(rules.native.authorization_id),f'generationengine:{prepared.attempt_id}',
        'openai',prepared.model,'responses',prepared.body_sha256,'stop','answered',raw,
        sha256(raw.encode()).hexdigest(),len(raw.encode()),())
    if not rules.capture_reply(reply):
        raise _ReplyRejected('plan_writer_native_capture_unacknowledged','Writer reply capture was not acknowledged')
    return reply


def _conversation_response_task(execution):
    """An actual work decision selects response guidance; prompt text never does."""
    from application_state.agent_conversation.native_execution import (
        SurfaceNativeExecutionV1, NativePlanActionV1, NativePlanActionV2, NativePlanActionV3,
        NativePlayActionV1, NativeBuildActionV1, NATIVE_PLAN_WORK_SELECTION_TYPES)
    if type(execution) is not SurfaceNativeExecutionV1:
        return None
    from application_state.agent_conversation.plan_contextual_questions import response_task
    question_task = response_task(execution)
    if question_task is not None:
        return question_task
    action = execution.policy.action
    if type(action) is NativePlayActionV1:
        return 'answer'  # This action owns only a read-only Run question.
    if type(action) in (NativePlanActionV1, NativePlanActionV2, NativePlanActionV3):
        choices = [e for e in execution.events if isinstance(e, t.PlanRequestedWorkSelectedV2)]
        accepted = NATIVE_PLAN_WORK_SELECTION_TYPES if type(action) in (NativePlanActionV2, NativePlanActionV3) else (t.PlanRequestedWorkSelectedV2,)
        if len(choices) != 1 or type(choices[0]) not in accepted:
            return None
        if type(action) is NativePlanActionV3 and choices[0].requested_work == 'discuss':
            return 'plan_contextual_discussion'
        if choices[0].requested_work == 'clarify':
            from application_state.agent_conversation.plan_placement import PlanPlacementCatalogV2
            if type(action.placement_catalog) is PlanPlacementCatalogV2:
                return 'plan_placement_clarify'
        return {'discuss': 'answer', 'clarify': 'clarify',
                'different_destination': 'different_destination'}.get(choices[0].requested_work)
    if type(action) is NativeBuildActionV1:
        from application_state.agent_conversation.build_intentional_response import selected_contract, selected_action
        selected = selected_action(execution)
        if isinstance(selected, t.BuildReviewedActionSelectionV1):
            from application_state.agent_conversation.reviewed_action import writer_scope
            return 'scoped_discussion' if selected.operation == 'answer_from_sources' and writer_scope(execution) is not None else None
        contract = selected_contract(execution)
        if contract is None or contract['operation'] != 'answer_from_sources':
            return None
        if contract['purpose'] == 'explain_capability':
            return 'explain_capability'
        if contract['purpose'] == 'clarify':
            return 'clarify'
        if contract['requested_work'] == 'review_variant_approval':
            return 'variant_approval'
        if contract['purpose'] == 'fulfill' and contract['requested_work'] == 'discuss':
            return 'build_discussion'
    return None


LORE_PROPOSAL_GUIDANCE = (
    "In a populated lore review, carry forward the author's relevant suggestions for this subject "
    "from the conversation as separate labeled proposals. Keep them out of passage-backed "
    "claims, even if they concern the same people or events. Do not introduce new suggestions."
)


PLAN_SOURCE_REFERENCE_RESPONSE = (
    'Saved authored pages describe authored material, not played truth. Use related_page_claim '
    'with the supplied local read_id. Buddy binds that exact supplied page to the citation. '
    'Do not return supporting_quotes or regenerate quote witnesses. Every factual clause must '
    'be supported by the ONE selected page; split claims from different pages into separate '
    'segments. Preserve uncertainty, and do not ask for a supplied page again.')

SOURCE_BACKED_DISCUSSION_RESPONSE = (
    '\nThis is a source-backed factual discussion. Give a useful factual brief through the '
    'supplied source-claim kinds and their local references, not uncited discussion or a '
    'generic readiness acknowledgment. A saved source\'s own proposed lore is an attributed '
    'source claim, not a new invented idea. Preserve concrete proposed motives and choices '
    'that the sources state; do not call them unknown just because other connections or '
    'details remain open. When supplied documents differ, attribute their positions instead '
    'of flattening them into one unresolved summary. A draft\'s general open question does '
    'not itself retract a specific proposal in another supplied source. Explicit later '
    'author corrections still take precedence. Do not invent a fact to fill a gap: if the '
    'available sources are insufficient, use the limitations offered by the response schema. '
    'No minimum factual claim is required.')

RELATED_PAGE_RESPONSE = (
    'Saved authored pages describe authored material, not played truth. '
    'Use related_page_claim with the supplied local read_id and supporting_quotes containing '
    'exact nonblank quotes from that same saved page. Do not ask for a supplied page again.')


SUPPLIED_SOURCE_RESPONSE = ('\nFor saved_source_claim select the supplied local section_read_ids; '
                'for related_page_claim select the supplied local read_id. Buddy binds the exact '
                'supplied read to the citation. Do not return supporting_quotes or recopy evidence '
                'as a validation witness. For these two claim kinds, ground each claim in its selected source, preserve uncertainty, '
                'and distinguish authored material from played events. Every factual clause in a '
                'related_page_claim must be supported by its ONE selected page. Split claims that '
                'draw on different pages into separate segments with their own references. Do not '
                'declare a motive or choice unknown when the selected source states it explicitly; '
                'qualify only the identity, mechanism or future actions that actually remain open. '
                'These citation requirements do not apply to collaboration drafts, retained author '
                'context, discussion or proposals; use those supplied materials according to their '
                'existing instructions. Prose formatting is free.\n')

class PlanJevWriter:
    def __init__(self, adapter, proof, rules, *, dialogue=()):
        self.adapter, self.proof, self.rules = adapter, proof, rules
        self.failure_stage = 'prepare'
        native_budget = getattr(adapter.fence.turn.graph_context_execution.policy,'writer_context_budget',None)
        self.output_reserve = native_budget.output_reserve_tokens if native_budget is not None else adapter.budget['outputReserveTokens']
        self.context_limit = native_budget.context_limit_tokens if native_budget is not None else adapter.budget['contextLimitTokens']
        self.shared = type(adapter.fence.turn.graph_context_receipt) is t.SurfaceNativeContextReceiptV1
        from application_state.agent_conversation.rules_authority_plan_packet import model_rules_frame
        rule_frame = model_rules_frame(rules.frame())
        self.projection = None
        self.generic_reply_limits = False
        if self.shared:
            from application_state.agent_conversation.native_writer import model_frame, model_work_frame
            from application_state.agent_conversation.native_evidence_view import semantic_frame,output_frame
            from application_state.agent_conversation.plan_writer_output_schema import native_output_format
            turn=adapter.fence.turn
            from application_state.agent_conversation.native_execution import NativeBuildActionV1, NativePlanActionV2, NativePlanActionV3
            plan_prose = (type(turn.graph_context_execution.policy.action) in (NativePlanActionV2, NativePlanActionV3)
                          and getattr(rules, 'authoring', None) is None)
            self.frame=model_frame(turn.graph_context_receipt,turn.graph_context_execution,
                                   passages_only=plan_prose)
            self.work_frame=model_work_frame(turn.graph_context_receipt,turn.graph_context_execution,
                provenance=turn.provenance,idempotency_key=turn.idempotency_key,work_proof=proof,
                world_id=turn.world_id,conversation_id=turn.conversation_id,turn_id=turn.turn_id,attempt=turn.attempt,
                play_context_receipt=turn.play_context_receipt if turn.graph_context_receipt.work_context.surface_id=='play' else None)
            self.provider_frame=semantic_frame(
                self.frame, project_managed_images=isinstance(turn.graph_context_execution.policy.action, NativeBuildActionV1),
            )
            self.frame=output_frame(self.frame,self.provider_frame)
            from application_state.agent_conversation.plan_jev_graph_packet import NATIVE_WORK_SCHEMA as PLAN_WORK_SCHEMA
            from application_state.agent_conversation.native_play_work import SCHEMA as PLAY_WORK_SCHEMA
            variant_format = False
            format_version = 2
            if self.work_frame.get('schema') == PLAY_WORK_SCHEMA:
                from application_state.agent_conversation.native_play_work import semantic_frame as play_work_view
                self.provider_work=play_work_view(self.work_frame)
            elif self.work_frame.get('schema') == PLAN_WORK_SCHEMA:
                from application_state.agent_conversation.native_plan_work_view import semantic_frame as plan_work_view
                self.provider_work=plan_work_view(self.work_frame,turn.graph_context_execution,
                    supplied_source_references=True)
            else:
                from application_state.agent_conversation.native_build_work_view import (
                    semantic_frame as build_work_view, variant_output_version, variant_sources,
                )
                from application_state.agent_conversation.build_intentional_response import is_anchored_discussion

                variant_format = bool(not rule_frame.lookups and variant_sources(self.work_frame))
                if variant_format:
                    format_version = variant_output_version(self.work_frame)
                elif (not rule_frame.lookups
                        and not any(isinstance(event, t.BuildPriorBodyEvidenceAdmittedV3)
                                    for event in turn.graph_context_execution.events)
                        and any(is_anchored_discussion(event) for event in turn.graph_context_execution.events)):
                    format_version = 7
                self.provider_work=build_work_view(
                    self.work_frame, turn.graph_context_execution, include_variant=variant_format, variant_edits=variant_format,
                    variant_passage_review=format_version in {9, 10, 11}, bind_lore_page=True,
                    supplied_source_references=True,
                    typed_source_answer=True, lore_page_limitations=True, lore_request_reference=True,
                )
            self.output_format=native_output_format(self.frame,rule_frame,
                self.work_frame | self.provider_work,
                build_local=self.work_frame.get('schema') not in {PLAN_WORK_SCHEMA,PLAY_WORK_SCHEMA},
                format_version=format_version, execution=turn.graph_context_execution, generic_reply_limits=True)
            from application_state.agent_conversation.plan_writer_output_schema import offered_generic_limits
            self.generic_reply_limits = offered_generic_limits(self.output_format)
            # Discussion ends with current evidence rather than prior assistant
            # prose. Keep the exact frames; authoring keeps its current draft last.
            frames=((self.provider_work,rule_frame,self.provider_frame)
                if getattr(rules,'authoring',None) is None
                else (self.provider_frame,rule_frame,self.provider_work))
        else:
            self.projection = project(adapter.fence.turn, proof, adapter.context_capture.trace.model_dump(mode='json'))
            self.frame=self.projection.frame
            from application_state.agent_conversation.plan_writer_output_schema import output_format
            self.output_format=output_format(self.frame,rule_frame)
            frames=(self.frame,rule_frame)
        self.compact_plan_editor_prose = None
        self.compact_plan_graph_qualifications = None
        self.deduplicate_plan_recap_prose = None
        self.messages=[{'role':'user','content':canonical_bytes(frame).decode()} for frame in frames]
        if self.shared and getattr(rules, 'authoring', None) is None:
            from application_state.agent_conversation.native_execution import NativePlanActionV2, NativePlanActionV3
            if type(turn.graph_context_execution.policy.action) in (NativePlanActionV2, NativePlanActionV3):
                from application_state.agent_conversation.native_evidence_view import render_plan_evidence
                from application_state.agent_conversation.rules_authority_plan_packet import render_plan_rules
                from application_state.agent_conversation.native_plan_work_view import compact_editor_prose
                prose_work = compact_editor_prose(self.provider_work)
                self.compact_plan_editor_prose = True if prose_work is not self.provider_work else None
                assertions = self.provider_frame.get("native_assertions") or {}
                self.compact_plan_graph_qualifications = True if assertions.get("assertions") else None
                self.deduplicate_plan_recap_prose = True
                self.messages = (
                    [{'role': 'user', 'content': render_plan_rules(rule_frame)}] if rule_frame.lookups else []
                ) + [{'role': 'user', 'content': render_plan_evidence(
                    self.provider_frame, prose_work,
                    compact_graph_qualifications=self.compact_plan_graph_qualifications,
                    deduplicate_recap_prose=self.deduplicate_plan_recap_prose,
                )}]
        if not self.shared:
            self.messages.append({'role':'user','content':'Return JSON.'})
        from application_state.agent_conversation.retained_conversation import dialogue_messages
        retained_dialogue = dialogue_messages(turn.graph_context_execution) if self.shared else None
        if retained_dialogue is not None:
            from application_state.agent_conversation.retained_conversation import require_current_presentation
            require_current_presentation(turn.graph_context_execution)
        if retained_dialogue is not None:
            from application_state.agent_conversation.retained_conversation import writer_messages
            self.messages = writer_messages(turn.graph_context_execution, self.messages)
        else:
            self.messages = [
                {"role": item["role"], "content": canonical_bytes({"conversation": item["content"]}).decode()}
                for item in dialogue
            ] + self.messages
        self.prompt_components = None
        related_page_response = (SUPPLIED_SOURCE_RESPONSE
            if self.shared and self.provider_work.get('build_work', {}).get('citation_policy') == 'supplied_source_references_v1'
            else PLAN_SOURCE_REFERENCE_RESPONSE if self.shared and self.provider_work.get('citation_policy') == 'supplied_source_references_v1'
            else RELATED_PAGE_RESPONSE)
        task = (_conversation_response_task(adapter._broker_execution())
                if self.shared and getattr(rules, 'authoring', None) is None else None)
        single_variant_base = self.shared and variant_format and len(variant_sources(self.work_frame)) == 1
        from application_state.agent_conversation.writer_evidence_selection import native_conversation_terminal

        conversation_draft = (self.shared and native_conversation_terminal(turn) is not None
            and self.provider_work.get("build_work", {}).get("requested_work", {}).get("requested_work") == "review_lore_page_from_conversation")
        self.reasoning_effort = "medium" if single_variant_base else "none" if conversation_draft else "low"
        if task is not None:
            from application_state.agent_conversation.response_prompt import compose_response_prompt
            prompt = compose_response_prompt(
                task=task,
                rules_instructions=RULES_INSTRUCTIONS if rule_frame.lookups else None,
                related_page_instructions=related_page_response
                    if self.provider_work.get('related_authored_pages', {}).get('pages') else None,
                single_variant_base=single_variant_base,
                generic_reply_limits=self.generic_reply_limits,
                build_source_status=(type(turn.graph_context_execution.policy.action) is NativeBuildActionV1
                                     and task in ('answer', 'build_discussion', 'scoped_discussion')))
            self.instructions = prompt.instructions
            self.prompt_components = prompt.manifest()  # Host-only inspectability.
        else:
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
                from application_state.agent_conversation.surface_evidence_answer import BODY_POLICY, GENERIC_BODY_INSTRUCTIONS
                native_body_instructions = GENERIC_BODY_INSTRUCTIONS if self.generic_reply_limits else BODY_INSTRUCTIONS
                instructions = SOURCE_ATTRIBUTION_INSTRUCTIONS + native_body_instructions.replace(BODY_POLICY,self.frame['answer_policy']) + STATEMENT_INSTRUCTIONS + ASSERTION_INSTRUCTIONS + AUTHORING_GUIDANCE
                from application_state.agent_conversation.reviewed_action import SCOPE_KEY,SCOPE_GUIDANCE
                if SCOPE_KEY in self.work_frame:
                    instructions += '\n' + SCOPE_GUIDANCE
                if self.work_frame.get('requested_work') == 'clarify':
                    instructions += '\nAsk the specific clarifying question. Do not draft yet.'
                if getattr(rules,'authoring',None) is not None:
                    instructions += '\n' + AUTHORING_INSTRUCTIONS
            if self.shared and self.provider_work.get('related_authored_pages', {}).get('pages'):
                instructions += '\n' + related_page_response + '\n'
            from application_state.agent_conversation.plan_jev_decision import connected_page_review_enabled
            if self.shared and connected_page_review_enabled(adapter._broker_execution()):
                instructions += ('\nPrepare the requested new location page as a connected_page collaboration, '
                    'using one included saved authored page local read_id and a unique exact quote from that page. '
                    'Its origin is authoring context, not proof that a newly invented place is a played fact. '
                    'Use the author-selected name and scope; preserve deferred development and other-page edits '
                    'as unexecuted. Nothing has been created, saved or published. Do not write this into the Plan. '
                    'If no included saved page can supply the origin, leave collaboration null and explain what '
                    'is needed rather than inventing a quote.\n')
            destination = self.provider_work.get("build_work", {}).get("lore_page_destination") if self.shared else None
            if destination is not None:
                from application_state.agent_conversation.lore_page_review import explicit_blank_lore_page

                blank = (self.provider_work['build_work']['requested_work']['requested_work'] == 'review_blank_lore_page'
                    if 'request' in destination else explicit_blank_lore_page(destination['instruction']))
                if not blank:
                    instructions += "\n" + LORE_PROPOSAL_GUIDANCE
                work = self.provider_work["build_work"]["requested_work"]
                if work["requested_work"] == "review_lore_page_from_conversation":
                    instructions += (
                        '\nBuild the review from the preceding discussion in four parts. For cited facts, '
                        'retain the handle paired with the specific prior claim and verify the exact '
                        'passage supports your wording. Carry forward relevant authored setting and '
                        'premises already supplied in the discussion or current authored page present in '
                        'the supplied context, including earlier details when later turns add ideas. '
                        "Preserve the author's corrections and retractions; do not restore superseded "
                        'material. Use separate proposal segments with the existing invented_idea label '
                        'and a clear authored-note-context heading or prefix in their text, rather than '
                        'presenting this material as newly invented suggestions or independently '
                        'established played events. Dialogue alone is not source evidence: preserve its '
                        'attribution and uncertainty, and never manufacture a citation. Lack of a '
                        'passage-backed citation is not a reason to omit clearly attributed authored '
                        "context. Put the author's later creative directions in separate invented_idea "
                        'proposals, preserving tentative status and introducing no new ideas. In '
                        'open_questions, retain material unresolved identities, motives and relationships, '
                        'including relationships named in a proposal. Retain the alternatives already '
                        'discussed. Before returning, compare the draft with relevant earlier context and '
                        'later additions so neither is silently dropped. If there is too little material '
                        'to draft accurately, leave the proposal empty and surface the specific gap for '
                        'the author. '
                    )
            if self.shared:
                fragment_scope = self.work_frame.get('focused_edit_target', {}).get('fragment_scope')
                if fragment_scope is not None:
                    instructions += '\n' + fragment_scope['instruction']
            self.instructions = '\n\n'.join((BUDDY_SYSTEM_PROMPT, instructions,
                RULES_INSTRUCTIONS if rule_frame.lookups else '')) + ('' if self.shared or getattr(rules,'authoring',None) is not None else IMAGE_DIRECTION_INSTRUCTIONS)
            if single_variant_base:
                from application_state.agent_conversation.response_prompt import VARIANT_BASE

                self.instructions += "\n" + VARIANT_BASE.text
        if (self.shared and self.provider_work.get('build_work', {}).get('citation_policy') == 'supplied_source_references_v1'
                and (self.work_frame['artifact_under_edit']['sections']
                     or self.work_frame.get('related_authored_pages', {}).get('pages'))):
            self.instructions += SUPPLIED_SOURCE_RESPONSE
        if self.shared and self.provider_work.get('build_work', {}).get('source_answer_policy') == 'typed_supplied_source_answer_v1':
            self.instructions += SOURCE_BACKED_DISCUSSION_RESPONSE
        if self.shared and self.provider_work.get('build_work', {}).get('lore_limitation_policy') == 'validated_lore_review_generic_gaps_v1' and not self.generic_reply_limits:
            self.instructions += ('\nOptional requested_detail_gaps select phrases from the CURRENT user request only, '
                'not an earlier dialogue turn. If no precise current phrase fits, return no specific gaps '
                'and use a generic limitation code. Keep the useful requested page content and open questions.')
        if self.generic_reply_limits:
            self.instructions += ('\nRepresent reply-level evidence limitations with the supplied codes. '
                'Do not return requested_detail_gaps or reproduce phrases from any user question. '
                'A limitation may stand alone when the supplied evidence cannot support a useful fact.')
        if retained_dialogue is not None:
            self.instructions += (
                    '\nThe supplied dialogue is chronological. Preserve later corrections and '
                    'retractions over earlier proposals. Retained authored context is an exact '
                    'historical read or working draft, not the current saved page or played truth. '
                    'Use its relevant setting details with clear attribution, separately from '
                    'later invented directions and unresolved questions. Do not omit supplied '
                    'context because it was absent from an earlier assistant summary. Native '
                    'passages are already supplied; select their offered handles without '
                    'claiming a new search or inventing citations. The complete dialogue following '
                    'the evidence frames is historical conversation data, including assistant '
                    'suggestions and earlier tasks; the final request_now packet is the current '
                    'assignment. Do not execute earlier tasks. Later user corrections take '
                    'precedence over older drafts and assistant suggestions. '
                    'A later capture or reread of the SAME authored snapshot is not a new '
                    'author revision. An unchanged unresolved placeholder in a page does not '
                    'erase a choice the user made in conversation. For this conversation-derived '
                    'work, explicit user choices govern the proposed setting unless a later '
                    'user correction or actually changed authored content retracts them. '
                    'Do not treat every hypothetical or question as a settled choice: distinguish '
                    'those from explicit wants, needs, corrections and decisions in the exact '
                    'user text. Preserve a chosen character role or relationship as authored '
                    'development, while leaving its fictional mechanism or implementation open. '
                    'Do not ask WHETHER the author chose it when their choice is already explicit. '
                    'Preserve each relevant authored premise and chosen creative direction in '
                    'the requested draft or recap, including later corrections, motives, '
                    'characterization and intended scenes. Keep these as clearly attributed '
                    'authored context or proposals, not played facts. Uncertainty in sources '
                    'does not turn a direction the author chose into a question about whether '
                    'they chose it. Keep actual unresolved identities and alternatives open. '
                    'Before returning, compare the result against every relevant earlier '
                    'author direction and correction so none is silently lost.'
                )
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
        from application_state.agent_conversation.native_writer import output_request_fields
        expected = {'model': self.model, 'input': self.messages, 'instructions': self.instructions,
            **output_request_fields(self.output_reserve), 'text': {'format': self.output_format},
            'tools': [], 'stream': False, 'reasoning': {'effort': self.reasoning_effort}, 'service_tier': 'fast'}
        if strict_json(prepared.body.decode()) != expected:
            raise ValueError('Plan writer actual request differs from staged evidence/instructions')
        projection = self.projection
        estimate = 0 if self.shared else len(prepared.body) + 64 * (1 + _json_node_count(expected))
        if not self.shared and self.context_limit is not None and estimate + self.output_reserve > self.context_limit:
            raise WriterCapacityError('Plan writer exceeds the existing provider context allowance. The request is retained; the writing provider was not called. Narrow the requested context before retrying.',
                code='build_writer_context_over_budget', actual=estimate+self.output_reserve, limit=self.context_limit)
        if self.shared:
            from application_state.errors import ApplicationStateConflictError
            try:
                event=authorize_native_writer(a,self.rules,self.proof,prepared,expected,self.provider_frame,
                    compact_plan_editor_prose=self.compact_plan_editor_prose,
                    compact_plan_graph_qualifications=self.compact_plan_graph_qualifications,
                    deduplicate_plan_recap_prose=self.deduplicate_plan_recap_prose)
            except ApplicationStateConflictError:
                self.target_changed=self.rules.authoring is not None
                raise
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
            input_tokens=estimate, output_token_reserve=self.output_reserve,
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
        if self.prepared is None:
            raise _ReplyRejected('plan_writer_response_incomplete', 'Plan writer has no complete exact SDK reply')
        raw=selected_writer_text(result,response,provider,self.model)
        if self.shared:
            received,self.received_event=self.received_event,None
            return capture_native_reply(self.adapter,self.rules,self.prepared,received,raw)
        native = self.rules.native
        reply = NativeProviderReply(str(native.authorization_id), f'generationengine:{self.prepared.attempt_id}',
            'openai',self.model,'responses',self.prepared.body_sha256,'stop','answered',raw,sha256(raw.encode()).hexdigest(),len(raw.encode()),())
        if not self.rules.capture_reply(reply):
            raise _ReplyRejected('plan_writer_native_capture_unacknowledged',
                'Plan writer reply capture was not acknowledged')
        return reply

    def capture_draft(self, response, *, selected_text=None):
        """Retain actual output; contextual proof uses the SDK-selected final."""
        text = selected_text if selected_text is not None else getattr(response, "output_text", None)
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
            request_summary={'reasoning_effort': self.reasoning_effort})

    async def run(self, *, transport=None, api_key=None):
        trace = getattr(self.adapter, "trace", None)
        observer = host_work_observer.get()
        detailed = trace is not None and observer is not None
        with trace.measure_host_work("plan_writer_client_setup") if detailed else nullcontext():
            from generationengine import GenerationClient, TextRequest
            from generationengine.text_dispatch import TextDispatchGate
            from application_state.agent_conversation.native_build_work_view import VARIANT_PASSAGE_FORMATS

            preparation_started = None

            async def authorize(prepared):
                nonlocal preparation_started
                if preparation_started is not None:
                    observer(trace.trace_id, "writer_sdk_preparation", preparation_started, monotonic(), False)
                    preparation_started = None
                return self.authorize(prepared)
            async def record(event): return self.record(event)
            options = {'dispatch_gate':TextDispatchGate(authorize,record),'transport':transport}
            if api_key is not None: options['api_key'] = api_key
            provider = PlanWriterProvider(**options)
            client = GenerationClient(text_providers={'openai':provider})
        started = perf_counter()
        stage = self.failure_stage = "generation"
        try:
            if observer is not None and trace is not None:
                preparation_started = monotonic()
            result = await client.generate_structured(TextRequest(provider='openai',model=self.model,
                user_prompt=json.dumps(self.messages,ensure_ascii=False),system_prompt=self.instructions,
                temperature=None,reasoning_effort=self.reasoning_effort,max_output_tokens=self.output_reserve or None,
                json_schema=self.output_format['schema'],schema_name=self.output_format['name'],
                # Passage review can take longer than the default writer deadline.
                deadline_ms=120_000 if self.output_format['name'] in VARIANT_PASSAGE_FORMATS else None,
                max_conformance_retries=0,max_transport_retries=0))
            self.observe(result.observation,status='ok')
            if self.call is not None and provider.actual_response is not None:
                self.call['response_service_tier'] = provider.actual_response.service_tier
            stage = 'draft'
            if not self.shared:
                self.capture_draft(provider.actual_response)
            stage = self.failure_stage = 'capture'
            reply = self.capture(result,provider.actual_response,provider)
            if self.shared:
                from application_state.agent_conversation.native_execution import NativePlanActionV3
                self.capture_draft(provider.actual_response, selected_text=(reply.text
                    if type(self.adapter._broker_execution().policy.action) is NativePlanActionV3 else None))
            if self.call is not None:
                self.call['duration_ms']=(perf_counter()-started)*1000
                self.adapter.context_capture.provider_usage([self.call])
                self._usage_recorded = True
        except BaseException as exc:
            response=provider.actual_response
            if response is not None and getattr(response,'status',None)=='incomplete':
                self.output_limit_exceeded = getattr(getattr(response,'incomplete_details',None),'reason',None)=='max_output_tokens'
            self.observe(getattr(exc,'observation',None),status='error')
            # GE preserves the dispatch-gate cause. Reuse the host's exact safe
            # classifier instead of mistaking an unsent request for provider failure.
            from .build_failure_diagnostic import failure_code
            code = failure_code(exc)
            preparation = code in {'build_writer_context_over_budget', 'build_writer_request_over_budget', 'build_writer_accounting_unavailable'}
            self.adapter.context_capture.observe({'kind':'failure',
                'phase':'context_build' if preparation else 'provider' if stage == 'generation' else 'delivery',
                'code':code if preparation else exc.code if isinstance(exc, _ReplyRejected) else f'plan_writer_{stage}_rejected'})
            try:
                self.capture_draft(response)
            except BaseException:
                self.adapter.context_capture.observe({'kind':'failure', 'phase':'delivery',
                    'code':'plan_writer_draft_rejected'})
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
