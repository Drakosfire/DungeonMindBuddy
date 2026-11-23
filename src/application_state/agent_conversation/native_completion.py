"""Shared native answer normalization through existing evidence/capture owners.

Producing SDK proof and domain normalization reuse the existing evidence owners.
Actual admission, atomic persistence and retained reads use their APP owners;
ordinary surface caller cutover remains a separate gate.
"""
from hashlib import sha256
from typing import Annotated, Literal
from uuid import UUID
from types import SimpleNamespace

from pydantic import Field, model_validator

from . import types as t
from .build_draft_answer import DraftDiscussionV1, normalize_native_segment
from .relationship_review import RelationshipCollaborationV3
from .lore_page_review import ProposedLorePage
from . import native_corpus as bodies
from . import native_plan_statements as statements
from . import native_plan_assertions as assertions
from .native_writer import verify_input_records
from .native_statement_input import Strict
from .rules_authority_types import canonical_bytes, canonical_sha256
from .source_writer_output import require_captured_answer, strict_json, surface_limitation, project_surface_limitations
from .surface_evidence_answer import (native_fact_segment, status_for,
    authored_block_index, authored_selected_segment, validate_authored_shape)

from .build_saved_statblock import SavedStatblockPdfPin


class StatblockPdfClaim(Strict):
    kind: Literal['statblock_pdf_claim']
    text: str
    scope: SavedStatblockPdfPin
    assertion_id: str
    evidence_ref_id: str


NativeSegment = Annotated[
    t.SourcePassageClaimV1 | t.NativeAssertionClaimV1 | t.SurfaceAuthoredExcerptV1 | t.SessionSummaryV1
    | t.DraftReferenceClaimV1 | t.RelatedPageClaim | t.SavedSourceClaimV1 | DraftDiscussionV1
    | t.PlanWorldGraphProposalSegmentV1 | t.SurfaceLimitationV1 | StatblockPdfClaim,
    Field(discriminator='kind'),
]


class SurfaceNativeCompletionV1(Strict):
    schema_: Literal['dmb_surface_native_completion_v1'] = Field(default='dmb_surface_native_completion_v1', alias='schema')
    surface_id: Literal['build', 'plan', 'play']
    context_receipt_sha256: str = Field(pattern=r'^[a-f0-9]{64}$')
    producing_provider_attempt_id: UUID
    answer_basis: Literal['mixed_evidence'] = 'mixed_evidence'
    answer_context_status: t.SurfaceEvidenceStatusV1 | Literal['discussion']
    answer_segments: list[NativeSegment] = Field(max_length=128)
    collaboration: RelationshipCollaborationV3 | ProposedLorePage | None
    saved_source_citations: list[t.BuildSectionSegmentBindingV1] = Field(max_length=128)
    native_body_citations: list[t.NativeBodyExcerptCitationV1] = Field(max_length=t.MAX_CITATION_SOURCE_READ_IDS)
    native_clause_citations: list[t.NativeStatementClauseCitationV1] = Field(max_length=t.MAX_CITATION_SOURCE_READ_IDS)
    native_assertion_citations: list[t.NativeAssertionCitation] = Field(max_length=t.MAX_CITATION_SOURCE_READ_IDS)

    @model_validator(mode='after')
    def supported_shape(self):
        validate_authored_shape(self.answer_segments)
        build=[s for s in self.answer_segments if isinstance(s,(t.DraftReferenceClaimV1,t.SavedSourceClaimV1,DraftDiscussionV1,StatblockPdfClaim))]
        related = any(isinstance(s,t.RelatedPageClaim) for s in self.answer_segments)
        if related and self.surface_id not in {'build','plan'}:
            raise ValueError('Saved authored claims require their actual authoring surface')
        if isinstance(self.collaboration, ProposedLorePage) and any(
            segment.kind not in {"source_passage_claim", "limitation"}
            and not (segment.kind == "proposal" and segment.label == "invented_idea")
            for segment in self.answer_segments
        ):
            raise ValueError("Lore draft requires source passages or clearly labeled proposals")
        from .collaboration import ProposedConnectedPage
        if self.collaboration is not None and self.surface_id != 'build' and not (
                self.surface_id=='plan' and isinstance(self.collaboration,ProposedConnectedPage)):
            raise ValueError('This surface does not own the proposed collaboration')
        if build and self.surface_id != 'build':
            raise ValueError('Build work discussion and saved claims require their actual surface owner')
        saved={i:s for i,s in enumerate(self.answer_segments) if isinstance(s,t.SavedSourceClaimV1)}
        indices=[c.segment_index for c in self.saved_source_citations]
        if indices != sorted(saved) or any(c.text_sha256 != sha256(saved[c.segment_index].text.encode()).hexdigest()
                for c in self.saved_source_citations):
            raise ValueError('Saved work claims require one exact text-bound citation mapping')
        authored=[support for segment in self.answer_segments for support in
            (segment.supports if isinstance(segment,t.SessionSummaryV1) else [segment])
            if isinstance(support,t.SurfaceAuthoredQuoteV1)]
        allowed={'plan':{'plan','session'},'play':{'play','session'}}.get(self.surface_id,set())
        if any(s.source_kind not in allowed for s in authored):
            raise ValueError('Shared authored excerpts require their actual surface or session owner')
        if not self.answer_segments and self.collaboration is None:
            raise ValueError('Native completion cannot be empty')
        status=status_for(self.answer_segments) if self.answer_segments else 'discussion'
        if any(not s.text.strip() for s in self.answer_segments) or self.answer_context_status != status:
            raise ValueError('Native completion status differs from its typed segments')
        source = {i for i,s in enumerate(self.answer_segments) if isinstance(s,t.SourcePassageClaimV1)}
        graph = {i for i,s in enumerate(self.answer_segments) if isinstance(s,t.NativeAssertionClaimV1)}
        if source != {c.segment_index for c in [*self.native_body_citations,*self.native_clause_citations]}:
            raise ValueError('Native source claims require their exact source citation family')
        if graph != {c.segment_index for c in self.native_assertion_citations}:
            raise ValueError('Native assertions require their exact assertion citation family')
        keys = []
        for c in self.native_body_citations:
            keys.append(('body',c.segment_index,c.read_event_id,c.section_id))
            if (c.text_sha256 != sha256(self.answer_segments[c.segment_index].text.encode()).hexdigest()
                    or c.line_end < c.line_start):
                raise ValueError('Native body citation changed its segment text or extent')
        keys += [('statement',c.segment_index,c.statement_id) for c in self.native_clause_citations]
        keys += [('assertion',c.segment_index,c.read_event_id,c.assertion_id,c.evidence_ref_id) for c in self.native_assertion_citations]
        if len(keys) != len(set(keys)):
            raise ValueError('Native completion repeats a citation')
        for segment in self.answer_segments:
            if isinstance(segment,t.SurfaceLimitationV1) and segment != surface_limitation(segment.code,segment.question_phrase):
                raise ValueError('Native limitation prose must come from its owner')
        if len(canonical_bytes(self)) > 1_048_576:
            raise ValueError('Native completion exceeds the existing storage budget')
        return self



def require_object_only_completion(completion):
    """Check the typed zero-text shape, without granting acceptance authority."""
    if type(completion) is not SurfaceNativeCompletionV1:
        raise ValueError('Object-only output requires the exact shared native completion')
    checked = SurfaceNativeCompletionV1.model_validate_json(
        completion.model_dump_json(by_alias=True), strict=True)
    if checked.answer_segments or checked.collaboration is None or checked.answer_context_status != 'discussion':
        raise ValueError('Object-only output requires a typed review without answer text')
    return checked


def _validate_citations(completion, receipt, execution, auth, evidence):
    # Evidence is freshly reconstructed by this module's entry point, never an
    # arbitrary caller-supplied list or a second persisted inclusion manifest.
    statements.validate_citation_records(completion, receipt, auth,
        {read.support.statement_id:read for _,_,read in evidence.native_statements})
    assertions.validate_citation_records(completion, receipt, auth,
        {(event.event_id,read.assertion.assertion_id):(event,read) for _,event,read in evidence.native_assertions})
    bodies.validate_body_support_citations(completion, evidence.body_excerpts,
        producer=auth.provider_attempt_id,envelope_sha256=auth.envelope_sha256,before_sequence=auth.sequence)
    from .build_related_pages import validate_claims as validate_related_claims
    validate_related_claims(completion,execution)
    selected={read.event_id:read for read in evidence.saved_sections}
    for citation in completion.saved_source_citations:
        segment=completion.answer_segments[citation.segment_index]
        if any(event_id not in selected or selected[event_id].source_basis.content_sha256 != segment.content_sha256
                for event_id in citation.section_event_ids):
            raise ValueError('Saved work citation differs from its actual included Build read')
    if completion.surface_id=='build':
        from .plan_objective import validate_completion as validate_plan_output
        validate_plan_output(completion,execution,auth.provider_attempt_id)
        if isinstance(completion.collaboration, ProposedLorePage):
            reviews = [
                event for event in execution.events
                if isinstance(event, t.BuildRequestedWorkResolutionV1)
                and event.requested_work in ("review_lore_page", "review_lore_page_from_conversation")
                and event.resolution["barrier"] is None
            ]
            if len(reviews) != 1:
                raise ValueError("Lore draft lacks its admitted Build review")
            completion.collaboration.destination.bind(
                execution.policy.action.intent.message,
                conversational=reviews[0].requested_work == "review_lore_page_from_conversation",
                has_body=bool(completion.collaboration.open_questions) or any(
                    segment.kind != "limitation" for segment in completion.answer_segments),
            )
        if completion.collaboration is not None and completion.collaboration.kind=='connected_page':
            from .connected_page_origins import execution_rows
            from .collaboration import saved_excerpt
            saved_excerpt(completion.collaboration,execution_rows(execution,receipt.work_context.source_basis,auth.provider_attempt_id))
    if completion.surface_id=='plan' and completion.collaboration is not None:
        from .plan_jev_decision import connected_page_review_enabled
        from .collaboration import ProposedConnectedPage, saved_excerpt
        from .connected_page_origins import execution_rows
        if not connected_page_review_enabled(execution) or not isinstance(completion.collaboration,ProposedConnectedPage):
            raise ValueError('Plan collaboration lacks its explicit creation-review selection')
        saved_excerpt(completion.collaboration,execution_rows(execution,None,auth.provider_attempt_id))
    bindings = [e for e in execution.events if isinstance(e,t.CompletionBindingEventV1)]
    if bindings and (len(bindings) != 1 or bindings[0].provider_attempt_id != auth.provider_attempt_id
            or bindings[0].completion_sha256 != canonical_sha256(completion) or bindings[0].claim_graph_event_ids):
        raise ValueError('Native completion changed its stored producer binding')


def normalize_output(receipt, execution, authorization, *, prepared_request_json, raw_output_json,
                     capture, trace, world_id, conversation_id, turn_id, attempt,
                     provenance, idempotency_key, work_proof, play_context_receipt=None):
    """Reconstruct completion from exact producing input and final captured SDK text.

    The caller supplies its locked Turn identity and protected trace. This helper
    grants no read, write, publication, Rules or authored-work authority.
    """
    evidence = verify_input_records(receipt,execution,authorization,prepared_request_json,
        provenance=provenance,idempotency_key=idempotency_key,work_proof=work_proof,
        world_id=world_id,conversation_id=conversation_id,turn_id=turn_id,attempt=attempt,
        play_context_receipt=play_context_receipt, retained_build_proof=True)
    responses = [e for e in execution.events if isinstance(e,t.ProviderOutcomeEventV1)
        and e.provider_attempt_id == authorization.provider_attempt_id and e.outcome == 'response_received']
    if (len(responses) != 1 or not responses[0].request_id
            or responses[0].request_id != getattr(capture,'api_request_id',None)
            or any(not isinstance(e,t.CompletionBindingEventV1) for e in execution.events if e.sequence > responses[0].sequence)):
        raise ValueError('Native completion requires its final acknowledged SDK response')
    if (getattr(capture,'provider',None),getattr(capture,'model',None),getattr(capture,'api_mode',None)) != (
            authorization.provider,authorization.model,authorization.api_mode):
        raise ValueError('Native completion capture differs from its actual writer')
    if not isinstance(getattr(capture,'authorization_id',None),str) or not capture.authorization_id.strip():
        raise ValueError('Native completion lacks its actual SDK capture identity')
    from .native_rules_output import verify_captured_text
    verify_captured_text(capture,authorization_id=capture.authorization_id,api_request_id=responses[0].request_id,
        request_envelope_sha256=authorization.envelope_sha256,prepared_request_json=prepared_request_json,
        raw_output_json=raw_output_json,raw_output_sha256=sha256(raw_output_json.encode()).hexdigest(),
        raw_output_utf8_bytes=len(raw_output_json.encode()),response_sha256=responses[0].response_sha256)
    require_captured_answer(trace,world_id=world_id,conversation_id=conversation_id,turn_id=turn_id,
        attempt=attempt,provider_attempt_id=authorization.provider_attempt_id,
        context_receipt_sha256=receipt.context_receipt_sha256,raw_output_json=raw_output_json)
    return normalize_candidate(strict_json(raw_output_json),receipt,execution,authorization,evidence)


def normalize_statblock_variant(candidate, work_frame, *, variant_edits=False, variant_witnesses=False,
                                variant_carried_condition=False, variant_passage_review=False,
                                variant_trigger_retention=False, variant_passage_witnesses=False):
    from .native_build_work_view import variant_draft_passages, variant_sources

    proposal = candidate.get("statblock_variant")
    if proposal is None:
        return None
    sources = variant_sources(work_frame)
    keys = {"source", "add_rules", "replace_rules"} if variant_edits else {"source", "definition"}
    if variant_passage_review:
        keys.add("passage_review")
    if not isinstance(proposal, dict) or set(proposal) != keys:
        raise ValueError("Statblock variant does not match its producing format")
    if variant_passage_review:
        review = proposal["passage_review"]
        passages = variant_draft_passages(work_frame)
        dispositions = ("retain", "change", "omit")
        if variant_trigger_retention:
            dispositions += ("retain_trigger",)
        if (not passages or not isinstance(review, dict) or set(review) != set(passages)
                or any(value not in dispositions for value in review.values())):
            raise ValueError("Statblock variant must review every offered draft passage")
        if variant_trigger_retention:
            _validate_retained_trigger_bindings(proposal, passages)
    source = proposal["source"]
    if not isinstance(source, str) or source not in sources:
        raise ValueError("Statblock variant base was not admitted")
    from apps.live_control_server.services.conversation_variant_save import ConversationVariantDraft

    base = sources[source]
    if variant_witnesses:
        markdown = work_frame.get("working_draft_context", {}).get("draft_markdown", "")
        witnessed_passages = None
        if variant_passage_witnesses:
            witnessed_passages = {
                handle for handle in variant_draft_passages(work_frame)
                if proposal["passage_review"][handle] != "omit"
            }
        proposal = {
            field: _unwrap_witnessed_edits(
                proposal[field], markdown, carried_condition=variant_carried_condition,
                witnessed_passages=witnessed_passages,
            )
            for field in ("add_rules", "replace_rules")
        }
    definition = (
        _apply_statblock_rule_edits(base["definition"], proposal)
        if variant_edits else proposal["definition"]
    )
    return ConversationVariantDraft(base_event_id=base["event_id"], definition=definition)


def _validate_retained_trigger_bindings(proposal, passages):
    required = {
        handle: passages[handle] for handle, decision in proposal["passage_review"].items()
        if decision == "retain_trigger"
    }
    covered = set()
    for field in ("add_rules", "replace_rules"):
        edits = proposal[field]
        if not isinstance(edits, list):
            raise ValueError("Statblock rule edits must be arrays")
        for edit in edits:
            if not isinstance(edit, dict):
                raise ValueError("Statblock rule edits must be objects")
            condition = edit.get("carried_condition")
            if condition is None:
                continue
            if not isinstance(condition, str) or not condition.strip():
                raise ValueError("Carried trigger requires exact authored text")
            matches = [handle for handle, passage in required.items() if condition in passage]
            rule = edit.get("rule")
            activation = rule.get("activation") if isinstance(rule, dict) else None
            trigger = activation.get("trigger") if isinstance(activation, dict) else None
            if len(matches) != 1 or not isinstance(trigger, dict):
                raise ValueError("Carried trigger must bind to one retained trigger passage and a typed rule")
            if activation.get("timing_text") is not None or trigger.get("source_element_key") is not None:
                raise ValueError("Carried trigger cannot add timing or a rule dependency")
            covered.add(matches[0])
    if covered != required.keys():
        raise ValueError("Every retained trigger passage requires a carried condition")


def _unique_authored_quote(markdown, quote):
    start = markdown.find(quote) if isinstance(quote, str) and quote.strip() else -1
    return start >= 0 and markdown.find(quote, start + 1) < 0


def _unwrap_witnessed_edits(edits, markdown, *, carried_condition=False, witnessed_passages=None):
    from copy import deepcopy
    if not isinstance(edits, list):
        raise ValueError("Witnessed statblock rule edits must be arrays")
    rules = []
    witness_field = "authored_quotes" if witnessed_passages is None else "authored_passages"
    fields = {witness_field, "rule"}
    if carried_condition:
        fields.add("carried_condition")
    for edit in edits:
        if not isinstance(edit, dict) or set(edit) != fields:
            raise ValueError("Each witnessed edit must contain its quotes and rule")
        witnesses = edit[witness_field]
        if not isinstance(witnesses, list):
            raise ValueError("Authored rule witnesses must be an array")
        if witnessed_passages is None:
            for quote in witnesses:
                if not _unique_authored_quote(markdown, quote):
                    raise ValueError("Statblock rule witness must identify exact authored text")
        else:
            for handle in witnesses:
                if not isinstance(handle, str) or handle not in witnessed_passages:
                    raise ValueError("Statblock rule witness must select an offered, non-omitted passage")
        rule = edit["rule"]
        condition = edit.get("carried_condition")
        if condition is not None:
            if not _unique_authored_quote(markdown, condition):
                raise ValueError("Carried condition must identify exact authored text")
            rule = deepcopy(rule)
            trigger = rule.get("activation", {}).get("trigger")
            if not isinstance(trigger, dict) or not isinstance(rule.get("rules_text"), str):
                raise ValueError("Carried condition requires a typed trigger and rule consequences")
            trigger["condition_text"] = condition
            rule["rules_text"] = condition + "\n\n" + rule["rules_text"]
        rules.append(rule)
    return rules


def _apply_statblock_rule_edits(base, proposal):
    from copy import deepcopy

    from apps.live_control_server.integrations.dungeonmind_statblocks.generated.models import RuleElementInput

    definition = deepcopy(base)
    rules = definition["rule_elements"]
    inherited = {rule["key"]: index for index, rule in enumerate(rules)}
    for field in ("replace_rules", "add_rules"):
        if not isinstance(proposal[field], list):
            raise ValueError("Statblock rule edits must be arrays")
    available_keys = inherited.keys() | {
        raw["key"] for raw in proposal["add_rules"]
        if isinstance(raw, dict) and isinstance(raw.get("key"), str)
    }
    edited = set()
    for field in ("replace_rules", "add_rules"):
        for raw in proposal[field]:
            rule = RuleElementInput.model_validate(raw).model_dump(mode="json")
            # The statblock service uses an empty cost list for a rule with no costs.
            if rule["costs"] is None:
                rule["costs"] = []
            key = rule["key"]
            if key in edited or (key in inherited) != (field == "replace_rules"):
                raise ValueError("Statblock rule edit key conflicts with the saved base")
            edited.add(key)
            if field == "replace_rules":
                original = rules[inherited[key]]
                mechanic = rule["mechanic"]
                if (
                    original["mechanic"]["kind"] == "human_adjudicated"
                    and rule["automation_support"] == "manual"
                    and mechanic["kind"] == "multiattack"
                    and len(mechanic["sequences"]) == 1
                    and mechanic["sequences"][0]["element_key"] not in available_keys
                ):
                    # A summon can name a separate creature in its rules text.
                    # The sequence field can target only local rule elements.
                    rule["mechanic"] = original["mechanic"]
                rules[inherited[key]] = rule
            else:
                mechanic = rule["mechanic"]
                if (rule["automation_support"] == "manual"
                        and mechanic["kind"] == "multiattack"
                        and mechanic["sequences"] == [
                            {"element_key": key, "count": 1, "choice_group": None},
                        ]):
                    # A manual rule pointing only to itself has no executable
                    # attack sequence. Its existing rules text governs play.
                    rule["mechanic"] = {"kind": "human_adjudicated", "adjudication_tags": []}
                rules.append(rule)
    if not edited:
        raise ValueError("Statblock variant must propose at least one rule edit")
    return definition


def normalize_candidate(candidate, receipt, execution, authorization, evidence):
    """Normalize the actual parsed partition after its producer/input proof.

    Mixed Rules responses have one captured outer body. Their base partition
    uses this same algorithm without manufacturing a second provider response.
    """
    from .plan_contextual_targets import is_question
    if is_question(execution):
        from .plan_contextual_questions import decode_question
        text = decode_question(candidate, execution)
        segment = t.PlanWorldGraphProposalSegmentV1(kind='proposal', label='invented_idea', text=text)
        completion = SurfaceNativeCompletionV1(surface_id='plan',
            context_receipt_sha256=receipt.context_receipt_sha256,
            producing_provider_attempt_id=authorization.provider_attempt_id,
            answer_context_status=status_for([segment]), answer_segments=[segment], collaboration=None,
            saved_source_citations=[], native_body_citations=[], native_clause_citations=[], native_assertion_citations=[])
        _validate_citations(completion, receipt, execution, authorization, evidence)
        from .surface_evidence_answer import validate_authored_owners
        validate_authored_owners(completion, receipt)
        return completion
    from .build_intentional_response import native_review_enabled, normalize_native_review
    from .plan_jev_decision import connected_page_review_enabled
    plan_review=connected_page_review_enabled(execution)
    review_enabled=plan_review or execution.policy.action.surface_id=='build' and native_review_enabled(evidence.work_frame)
    keys={'schema','answer_segments','limitations','requested_detail_gaps'} | ({'collaboration'} if review_enabled else set())
    if evidence.variant_format:
        keys.add("statblock_variant")
    if (not isinstance(candidate,dict) or set(candidate) != keys
            or candidate['schema'] != evidence.frame['answer_policy'] or not isinstance(candidate['answer_segments'],list)):
        raise ValueError('Native completion requires its exact producing answer policy')
    if evidence.variant_visible_reply and not candidate['answer_segments']:
        raise ValueError('Native variant completion requires a visible reply')
    if evidence.variant_format:
        normalize_statblock_variant(candidate, evidence.work_frame, variant_edits=evidence.variant_edits,
            variant_witnesses=evidence.variant_witnesses,
            variant_carried_condition=evidence.variant_carried_condition,
            variant_passage_review=evidence.variant_passage_review,
            variant_trigger_retention=evidence.variant_trigger_retention,
            variant_passage_witnesses=evidence.variant_passage_witnesses)
    segments, body_cites, statement_cites, assertion_cites,saved_cites = [], [], [], [],[]
    blocks,selectors=authored_block_index(evidence.authored,str(evidence.idempotency_key),local=evidence.authored_local)
    selected_blocks=set()
    for row in candidate['answer_segments']:
        if isinstance(row, dict) and row.get('kind') == 'discussion' and evidence.typed_source_answer:
            raise ValueError('Source-backed factual discussion requires typed source claims')
        if (not isinstance(row,dict) or row.get('kind') not in {'authored_excerpt', 'statblock_pdf_claim'}
                and (not isinstance(row.get('text'),str) or not row['text'].strip())):
            raise ValueError('Native completion contains an invalid segment')
        if row.get('kind') in {'draft_reference_claim','related_page_claim','saved_source_claim','discussion'}:
            if execution.policy.action.surface_id != 'build':
                from .build_related_pages import plan_read_enabled
                if (row.get('kind') != 'related_page_claim' or not plan_read_enabled(execution)):
                    raise ValueError('Build work output cannot borrow another surface')
                row = dict(row)
                from .native_plan_work_view import resolve_related_read_alias
                row['read_id'] = resolve_related_read_alias(row.get('read_id'),evidence.related_pages)
            if evidence.build_local:
                from .native_build_work_view import resolve_selectors
                row=resolve_selectors(row,evidence.work_frame)
            segment,citation=normalize_native_segment(row,draft_record=evidence.draft_record,
                saved_sections=evidence.saved_sections,related_pages=evidence.related_pages,source_basis=getattr(receipt.work_context,'source_basis',None),index=len(segments),
                supplied_source_references=evidence.supplied_source_references)
            segments.append(segment)
            if citation is not None:
                saved_cites.append(citation)
        elif row.get('kind') == 'statblock_pdf_claim':
            from .native_build_work_view import resolve_statblock_pdf_quote

            if (execution.policy.action.surface_id != 'build' or not evidence.build_local
                    or set(row) != {'kind', 'source', 'quote'}):
                raise ValueError('PDF claim requires the producing Build work frame')
            scope, assertion_id, evidence_ref_id = resolve_statblock_pdf_quote(
                evidence.work_frame, row['source'], row['quote'])
            segments.append(StatblockPdfClaim(kind='statblock_pdf_claim', text=row['quote'],
                scope=scope, assertion_id=assertion_id, evidence_ref_id=evidence_ref_id))
        elif row.get('kind') in {'authored_excerpt','session_summary'}:
            segments.append(authored_selected_segment(row,blocks=blocks,selectors=selectors,selected_blocks=selected_blocks))
        elif row.get('kind') == 'proposal':
            segments.append(t.PlanWorldGraphProposalSegmentV1.model_validate(row))
        else:
            segment, body, statement, assertion = native_fact_segment(row,policy=candidate['schema'],
                receipt=receipt,auth=authorization,support=evidence,index=len(segments))
            segments.append(segment)
            body_cites.extend(body)
            statement_cites.extend(statement)
            assertion_cites.extend(assertion)
    review=candidate.get('collaboration')
    if review_enabled and evidence.build_local and review is not None:
        from .native_build_work_view import resolve_selectors
        review=resolve_selectors(review,evidence.work_frame)
    if plan_review and review is not None:
        from .collaboration import ProposedConnectedPage, saved_excerpt
        from .native_plan_work_view import resolve_related_read_alias
        from .connected_page_origins import execution_rows
        if not isinstance(review,dict):
            raise ValueError('Plan creation review requires its typed proposal')
        review=dict(review)
        review['read_id']=resolve_related_read_alias(review.get('read_id'),evidence.related_pages)
        collaboration=ProposedConnectedPage.model_validate(review)
        saved_excerpt(collaboration,execution_rows(execution,None,authorization.provider_attempt_id))
    else:
        collaboration = (
            normalize_native_review(
                review, segments, evidence.work_frame,
                author_text=execution.policy.action.intent.message,
            ) if review_enabled and not plan_review else None
        )
    explicit_source_gap = evidence.typed_source_answer and bool(
        candidate.get('limitations') or candidate.get('requested_detail_gaps'))
    if review_enabled and not segments and collaboration is None and not explicit_source_gap:
        raise ValueError('Empty intentional response')
    # A host retrieval footer cannot stand in for an actual clarification.
    from .native_execution import NATIVE_PLAN_ACTION_TYPES
    from .plan_placement import PlanPlacementCatalogV2
    action = execution.policy.action
    if (isinstance(action, NATIVE_PLAN_ACTION_TYPES)
            and type(action.placement_catalog) is PlanPlacementCatalogV2
            and evidence.work_frame.get('requested_work') == 'clarify'
            and not segments):
        raise ValueError('Plan placement clarification requires nonempty reply content')
    # Missing native capability does not make an available authored page
    # unavailable. Only native claims inherit that native retrieval qualification.
    local_authored=(execution.policy.action.surface_id in {'build','plan'}
        and (collaboration is not None or any(isinstance(s,(t.DraftReferenceClaimV1,t.RelatedPageClaim,t.SavedSourceClaimV1,DraftDiscussionV1)) for s in segments))
        and all(isinstance(s,(t.DraftReferenceClaimV1,t.RelatedPageClaim,t.SavedSourceClaimV1,DraftDiscussionV1,t.PlanWorldGraphProposalSegmentV1))
            for s in segments))
    local_authored = local_authored or (execution.policy.action.surface_id=='play'
        and any(isinstance(s,(t.SurfaceAuthoredExcerptV1,t.SessionSummaryV1)) for s in segments)
        and all(isinstance(s,(t.SurfaceAuthoredExcerptV1,t.SessionSummaryV1,t.PlanWorldGraphProposalSegmentV1)) for s in segments))
    has_cited_answer = bool(body_cites or statement_cites or assertion_cites or saved_cites
                            or any(isinstance(s, StatblockPdfClaim) for s in segments))
    limitations = project_surface_limitations(candidate['limitations'], candidate['requested_detail_gaps'],
        user_question=execution.policy.action.intent.message, derive_missing=True,
        host_partial=evidence.frame['input_status'] == 'partial' and not local_authored,
        empty_answer=not segments and collaboration is None, strict_gap_array=True,
        allow_generic_gap=has_cited_answer)
    # A selected question phrase does not establish an absence of evidence.
    segments.extend(limit for limit in limitations
        if not has_cited_answer or limit.question_phrase is None)
    completion = SurfaceNativeCompletionV1(surface_id=execution.policy.action.surface_id,
        context_receipt_sha256=receipt.context_receipt_sha256,producing_provider_attempt_id=authorization.provider_attempt_id,
        answer_context_status=status_for(segments) if segments else 'discussion',answer_segments=segments,collaboration=collaboration,saved_source_citations=saved_cites,
        native_body_citations=body_cites,native_clause_citations=statement_cites,native_assertion_citations=assertion_cites)
    _validate_citations(completion,receipt,execution,authorization,evidence)
    from .surface_evidence_answer import validate_authored_owners
    validate_authored_owners(completion,receipt)
    return completion


def verify_completion(completion, receipt, execution, authorization, **producing_proof):
    """No stored or caller-mutated completion can replace exact output reconstruction."""
    expected = normalize_output(receipt,execution,authorization,**producing_proof)
    if type(completion) is not SurfaceNativeCompletionV1 or canonical_sha256(completion) != canonical_sha256(expected):
        raise ValueError('Native completion differs from its exact producing output')
    return expected


def validate_retained_completion(completion, receipt, execution, producer, bindings):
    """Validate stored native citations/binding; producing admission owns acceptance."""
    from .native_execution import _revalidate_context_binding

    receipt, execution = _revalidate_context_binding(receipt, execution)
    _join_retained_completion(completion, receipt, execution, producer, bindings)


def _join_build_graph_reference_completion(completion, receipt, execution, producer, claims):
    from .native_execution import NativeBuildActionV1

    binding = execution.events[-1] if execution.events else None
    if (not isinstance(execution.policy.action, NativeBuildActionV1)
            or type(binding) is not t.BuildGraphReferenceCompletionBindingV1
            or claims != {} or binding.claim_graph_event_ids != {}
            or binding.provider_attempt_id != producer
            or binding.completion_sha256 != t.canonical_sha256(completion)
            or completion.context_receipt_sha256 != receipt.context_receipt_sha256):
        raise ValueError("Graph reference result differs from its retained decision binding")
    opening = next((event for event in execution.events if (
        isinstance(event, t.BuildRequestedWorkResolutionV1) and event.event_id == binding.opening_event_id
    )), None)
    if opening is None or opening.typed_graph_reference != "place_existing_reference":
        raise ValueError("Graph reference result requires its typed opening choice")
    authorization = next((event for event in execution.events if (
        isinstance(event, t.ProviderAttemptAuthorizedEventV1) and event.provider_attempt_id == producer
    )), None)
    response = execution.events[-2] if len(execution.events) >= 2 else None
    if (type(authorization) is not t.ProviderAttemptAuthorizedEventV5
            or authorization.context_phase != "graph_reference" or authorization.sequence <= opening.sequence
            or (authorization.provider, authorization.model, authorization.api_mode)
                != execution.policy.provider_roles.controller.identity()
            or not isinstance(response, t.ProviderOutcomeEventV1)
            or response.provider_attempt_id != producer or response.outcome != "response_received"):
        raise ValueError("Graph reference result requires the final acknowledged nomination")


def _join_build_image_move_completion(completion, receipt, execution, producer, claims):
    from .native_execution import NativeBuildActionV1

    action = execution.policy.action
    binding = execution.events[-1] if execution.events else None
    if (not isinstance(action, NativeBuildActionV1) or action.image_move_capture is None
            or type(binding) is not t.BuildImageMoveCompletionBindingV1
            or claims != {} or binding.claim_graph_event_ids != {}
            or binding.provider_attempt_id != producer
            or binding.completion_sha256 != t.canonical_sha256(completion)
            or completion.context_receipt_sha256 != receipt.context_receipt_sha256):
        raise ValueError("Image move result differs from its retained native decision")
    opening = next((event for event in execution.events if isinstance(event, t.BuildRequestedWorkResolutionV1)
                    and event.event_id == binding.opening_event_id), None)
    if (opening is None or opening.typed_image_move not in {"move_existing", "unresolved"}
            or opening.controller_attempt_id != producer
            or (opening.typed_image_move != "move_existing" and completion.disposition == "ready")):
        raise ValueError("Image move result requires its acknowledged opening choice")


def _join_retained_completion(completion, receipt, execution, producer, bindings):
    """Check the completion against an already validated context and execution."""
    from .native_execution import NATIVE_WRITER_TYPES, _validate_owned_context_binding
    from .native_writer import _model_frame_from_validated_prefix, read_evidence_records
    from .surface_evidence_answer import validate_authored_owners

    if type(completion) is t.BuildGraphReferenceCompletionV1:
        _join_build_graph_reference_completion(completion, receipt, execution, producer, bindings)
        return
    if any(type(event) is t.BuildGraphReferenceCompletionBindingV1 for event in execution.events):
        raise ValueError("A Graph reference binding requires its exact typed completion")
    if type(completion) is t.BuildImageMoveCompletionV1:
        _join_build_image_move_completion(completion, receipt, execution, producer, bindings)
        return
    if any(type(event) is t.BuildImageMoveCompletionBindingV1 for event in execution.events):
        raise ValueError("An image move binding requires its exact typed completion")

    if isinstance(completion,(t.BuildAuthoringCompletionV1,t.BuildImagePreparationCompletionV1)):
        from .build_authoring import validate_native_authoring_binding
        validate_native_authoring_binding(completion,receipt,execution,producer,bindings)
    elif (type(completion) is not SurfaceNativeCompletionV1 or bindings != {}
            or completion.context_receipt_sha256 != receipt.context_receipt_sha256
            or completion.surface_id != execution.policy.action.surface_id
            or completion.producing_provider_attempt_id != producer):
        raise ValueError('Retained native completion differs from its actual producing owner')
    if isinstance(completion,SurfaceNativeCompletionV1):
        completion = SurfaceNativeCompletionV1.model_validate_json(completion.model_dump_json(by_alias=True))
    auths=[e for e in execution.events if type(e) in NATIVE_WRITER_TYPES]
    if len(auths)!=1 or auths[0].provider_attempt_id != producer:
        raise ValueError('Retained native completion requires its unique writer')
    auth=auths[0]
    responses=[e for e in execution.events if isinstance(e,t.ProviderOutcomeEventV1)
        and e.provider_attempt_id==producer and e.outcome=='response_received']
    if (len(responses)!=1 or any(not isinstance(e,t.CompletionBindingEventV1) for e in execution.events if e.sequence>responses[0].sequence)):
        raise ValueError('Retained native completion lacks its final acknowledged output')
    if isinstance(completion,(t.BuildAuthoringCompletionV1,t.BuildImagePreparationCompletionV1)):
        return
    prefix = execution.model_copy(update={'events': execution.events[:auth.sequence]})
    _validate_owned_context_binding(receipt, prefix)
    frame = _model_frame_from_validated_prefix(receipt, prefix)
    from .build_primary_context import records
    evidence=SimpleNamespace(**read_evidence_records(prefix,frame),
        saved_sections=records(prefix,receipt.work_context.source_basis) if completion.surface_id=='build' else ())
    if completion.surface_id == 'plan':
        from .native_corpus import writer_passage_supports
        from .native_writer import body_handle

        evidence.body_excerpts += tuple(
            support for support in writer_passage_supports(prefix, body_handle)
            if support.selected_lines is not None
        )
    _validate_citations(completion,receipt,execution,auth,evidence)
    validate_authored_owners(completion,receipt)
