"""Native Plan query commitments; source ownership never grants Graph authority."""
from __future__ import annotations

from typing import Literal
from uuid import UUID
from pydantic import Field, model_validator
from .native_statement_input import Strict, NativeAuthorityRefV1, NativeStatementSupportV1, digest


class NativePlanQueryAuthorityV1(Strict):
    schema_: Literal['dmb_native_plan_query_authority_v1'] = Field(
        default='dmb_native_plan_query_authority_v1', alias='schema')
    managed_world_id: str = Field(min_length=1)
    native_world_id: str = Field(min_length=1)
    binding_version: int = Field(gt=0, strict=True)
    revision_id: str = Field(min_length=1)
    domain_ref: NativeAuthorityRefV1
    profile_ref: NativeAuthorityRefV1
    acquisition_epoch: int = Field(ge=0, strict=True)
    role: Literal['gm'] = 'gm'
    scope_mode: Literal['world', 'campaign']
    campaign_id: str | None
    session_id: str | None = None

    @model_validator(mode='after')
    def scope(self):
        if self.scope_mode == 'campaign' and not self.campaign_id:
            raise ValueError('Campaign query requires its campaign')
        if self.session_id is not None and not self.campaign_id:
            raise ValueError('Session focus requires its campaign')
        return self


class NativePlanQueryUnavailableV1(Strict):
    schema_: Literal['dmb_native_plan_query_unavailable_v1'] = Field(
        default='dmb_native_plan_query_unavailable_v1', alias='schema')
    managed_world_id: str = Field(min_length=1)
    reason: Literal['native_graph_binding_unavailable', 'native_graph_head_unavailable']


class NativePlanStatementMatchV1(Strict):
    statement_id: str = Field(pattern=r'^ent:.+')
    discovered_entity_ids: tuple[str, ...] = Field(min_length=1)
    discovery_assertion_ids: tuple[str, ...] = Field(min_length=1)
    # Navigation metadata only. Neither meaning nor quote is projected before selection.
    campaign_id: str = Field(min_length=1)
    logical_source: dict[str, str]
    episode: str
    label: str = Field(min_length=1)


class NativePlanQueryV1(Strict):
    schema_: Literal['dmb_native_plan_query_v1'] = Field(default='dmb_native_plan_query_v1', alias='schema')
    authority: NativePlanQueryAuthorityV1
    question: str = Field(min_length=1)
    search_result_sha256: str = Field(pattern=r'^[a-f0-9]{64}$')
    discovered_entity_ids: tuple[str, ...]
    matches: tuple[NativePlanStatementMatchV1, ...]
    status: Literal['complete', 'partial']
    gap_codes: tuple[str, ...]
    universal_absence_claimed: Literal[False] = False

    @model_validator(mode='after')
    def discovery_closure(self):
        identities = [m.statement_id for m in self.matches]
        if (len(identities) != len(set(identities))
                or len(self.discovered_entity_ids) != len(set(self.discovered_entity_ids))
                or (self.status == 'partial') != bool(self.gap_codes)):
            raise ValueError('Native query completeness or distinct matches differ')
        for match in self.matches:
            if not set(match.discovered_entity_ids) <= set(self.discovered_entity_ids):
                raise ValueError('Statement was not discovered by this query')
            if self.authority.scope_mode == 'campaign' and match.campaign_id != self.authority.campaign_id:
                raise ValueError('Statement campaign differs from query admission')
        return self

    @property
    def sha256(self):
        return digest(self)


def selection_handle(query, match):
    return 'native-statement:' + digest({'query': query.sha256, 'statement': match.statement_id})


class NativePlanStatementReadAuthorizedV1(Strict):
    kind: Literal['native_plan_statement_read_authorized_v1'] = 'native_plan_statement_read_authorized_v1'
    event_id: UUID
    sequence: int = Field(ge=0, strict=True)
    provider_attempt_id: UUID
    query_sha256: str = Field(pattern=r'^[a-f0-9]{64}$')
    statement_ids: tuple[str, ...] = Field(min_length=1)

    @model_validator(mode='after')
    def distinct(self):
        if len(self.statement_ids) != len(set(self.statement_ids)):
            raise ValueError('Statement selection repeats an ID')
        return self


class NativePlanStatementReadV1(Strict):
    support: NativeStatementSupportV1
    source_body_bytes: int = Field(gt=0, strict=True)

    @model_validator(mode='after')
    def extent(self):
        if self.support.clause_end_byte > self.source_body_bytes:
            raise ValueError('Statement clause escapes its original body')
        return self


class NativePlanStatementReadObservedV1(Strict):
    kind: Literal['native_plan_statement_read_observed_v1'] = 'native_plan_statement_read_observed_v1'
    event_id: UUID
    sequence: int = Field(ge=0, strict=True)
    authorization_event_id: UUID
    reads: tuple[NativePlanStatementReadV1, ...]
    unavailable_statement_ids: tuple[str, ...]
    status: Literal['complete', 'partial']

    @model_validator(mode='after')
    def exact_reads(self):
        ids = [r.support.statement_id for r in self.reads]
        if (len(ids) != len(set(ids)) or len(self.unavailable_statement_ids) != len(set(self.unavailable_statement_ids))
                or set(ids) & set(self.unavailable_statement_ids)
                or (self.status == 'partial') != bool(self.unavailable_statement_ids)):
            raise ValueError('Native selected read status differs from its inventory')
        return self


def validate_support_authority(authority, read):
    support = read.support
    clause = support.payload['clause']
    if (clause['world'] != authority.native_world_id
            or authority.scope_mode == 'campaign' and clause['campaign'] != authority.campaign_id
            or support.ancestry[0]['revision_id'] != authority.revision_id
            or support.publication_receipt.get('space_id') != authority.native_world_id):
        raise ValueError('Native support differs from its query authority')
    for h in support.ancestry:
        if (h['space_id'] != authority.native_world_id
                or h['domain_ref'] != authority.domain_ref.model_dump()
                or h['profile_ref'] != authority.profile_ref.model_dump()):
            raise ValueError('Native support changed domain/profile authority')


def validate_execution(receipt, execution):
    """One selected-read/provider state machine for both native record families."""
    from . import types as t
    if not isinstance(execution, t.PlanNativeExecutionV1) or execution.policy.native_query_sha256 != digest(receipt.native_query):
        raise ValueError('Native Plan requires its exact query policy/ledger')
    validate_selected_record_events(receipt.native_query, execution)


def validate_selected_record_events(query, execution):
    """Shared native selected-record checks; source admission remains with Core."""
    from . import types as t
    from .native_plan_assertions import (NativePlanQueryV2, NativePlanAssertionReadAuthorizedV1,
        NativePlanAssertionReadObservedV1, selection_handle as assertion_handle)
    statements = {m.statement_id: m for m in query.matches} if isinstance(query, NativePlanQueryV1) else {}
    assertions = {m.assertion_id: m for m in query.assertion_matches} if isinstance(query, NativePlanQueryV2) else {}
    provider = outcome = selection = None
    grants, observations, attempted = {}, {}, set()
    writer = False
    for event in execution.events:
        if isinstance(event, t.ProviderAttemptAuthorizedEventV1):
            shared_writer = False
            if event.kind == "native_writer_authorized_v1":
                from .native_execution import NativeWriterAuthorizedV1
                shared_writer = type(event) is NativeWriterAuthorizedV1
            if shared_writer or isinstance(event, t.PlanJevWriterAuthorizedV1):
                if not shared_writer:
                    expected = t.PlanNativeWriterAuthorizedV2 if isinstance(query, NativePlanQueryV2) else t.PlanNativeWriterAuthorizedV1
                    if not isinstance(event, expected) or (not isinstance(query, NativePlanQueryV2) and isinstance(event, t.PlanNativeWriterAuthorizedV2)):
                        raise ValueError('Native query Plan requires its own writer inclusion')
                if set(grants) != {e.authorization_event_id for e in observations.values()}:
                    raise ValueError('Native writer requires every selected read grant to be settled')
                # The shared root closes one inclusion set across every native
                # family; immutable Plan codecs retain their original lists.
                families = [] if shared_writer else [(NativePlanStatementReadObservedV1, event.native_statement_read_event_ids)]
                if not shared_writer and isinstance(query, NativePlanQueryV2):
                    families.append((NativePlanAssertionReadObservedV1, event.native_assertion_read_event_ids))
                for observed_type, included in families:
                    if (len(included) != len(set(included))
                            or set(included) != {e.event_id for e in observations.values() if isinstance(e, observed_type)}):
                        raise ValueError('Native writer changed selected support exposure')
                writer = True
            provider, outcome, selection = event.provider_attempt_id, None, None
        elif isinstance(event, t.ProviderOutcomeEventV1) and event.provider_attempt_id == provider:
            outcome = event.outcome
        elif isinstance(event, t.PlanJevRetrievalSelectionV1):
            selection = event
        elif isinstance(event, (NativePlanStatementReadAuthorizedV1, NativePlanAssertionReadAuthorizedV1)):
            assertion = isinstance(event, NativePlanAssertionReadAuthorizedV1)
            ids = event.assertion_ids if assertion else event.statement_ids
            matches = assertions if assertion else statements
            handle = assertion_handle if assertion else selection_handle
            keys = {(assertion, identity) for identity in ids}
            if (writer or outcome != 'response_received' or selection is None
                    or selection.operation != 'select_candidates' or event.provider_attempt_id != provider
                    or not isinstance(query, NativePlanQueryV1) or event.query_sha256 != query.sha256
                    or not set(ids) <= set(matches) or attempted & keys
                    or not {handle(query, matches[i]) for i in ids} <= set(selection.selected_handles)):
                raise ValueError('Native selected read lacks its exact current controller/query grant')
            grants[event.event_id] = event
            attempted.update(keys)
        elif isinstance(event, (NativePlanStatementReadObservedV1, NativePlanAssertionReadObservedV1)):
            grant = grants.get(event.authorization_event_id)
            assertion = isinstance(event, NativePlanAssertionReadObservedV1)
            expected = NativePlanAssertionReadAuthorizedV1 if assertion else NativePlanStatementReadAuthorizedV1
            ids = {r.assertion.assertion_id for r in event.reads} if assertion else {r.support.statement_id for r in event.reads}
            unavailable = event.unavailable_assertion_ids if assertion else event.unavailable_statement_ids
            granted = set(grant.assertion_ids if assertion else grant.statement_ids) if isinstance(grant, expected) else None
            if (writer or granted is None or grant.provider_attempt_id != provider or outcome != 'response_received'
                    or any(e.authorization_event_id == grant.event_id for e in observations.values())
                    or granted != ids | set(unavailable)):
                raise ValueError('Native read observation differs from selected grant')
            for read in event.reads:
                if assertion:
                    match = assertions[read.assertion.assertion_id]
                    if digest(read.assertion) != match.assertion_sha256 or read.assertion.subject_entity_id != match.subject_entity_id:
                        raise ValueError('Native assertion changed after discovery')
                else:
                    validate_support_authority(query.authority, read)
                    match = statements[read.support.statement_id]
                    if (read.support.payload['clause']['campaign'] != match.campaign_id
                            or read.support.payload['clause']['logical_source'] != match.logical_source
                            or read.support.payload['episode'] != match.episode
                            or not set(match.discovery_assertion_ids) <= set(read.support.assertion_ids)):
                        raise ValueError('Native selected support changed its discovered statement')
            observations[event.event_id] = event


def selected_reads(turn):
    from . import types as t
    if not isinstance(turn.graph_context_receipt, t.PlanNativeContextReceiptV1):
        return ()
    return tuple((event, read) for event in turn.graph_context_execution.events
        if isinstance(event, NativePlanStatementReadObservedV1) for read in event.reads)


def model_frame(turn):
    from . import types as t
    receipt = turn.graph_context_receipt
    if not isinstance(receipt, t.PlanNativeContextReceiptV1):
        raise ValueError('Native statement frame requires its Plan owner')
    query = receipt.native_query
    rows = selected_reads(turn)
    partial = isinstance(query, NativePlanQueryV1) and query.status == 'partial' or any(
        isinstance(e, NativePlanStatementReadObservedV1) and e.status == 'partial'
        for e in turn.graph_context_execution.events)
    return {'schema': 'dmb_plan_native_statement_frame_v1',
        'authority': query.authority.model_dump(mode='json', by_alias=True) if isinstance(query, NativePlanQueryV1) else None,
        'status': 'unavailable' if not isinstance(query, NativePlanQueryV1) else 'partial' if partial else 'complete',
        'gap_codes': list(query.gap_codes) if isinstance(query, NativePlanQueryV1) else [query.reason],
        'universal_absence_claimed': False,
        'statements': [{'statement_handle': 'statement:' + digest({'query': query.sha256, 'read': str(event.event_id), 'statement': read.support.statement_id}),
            'payload': read.support.payload,
            'source_artifact_id': read.support.source_artifact_id,
            'source_revision_id': read.support.source_revision_id,
            'source_body_sha256': read.support.source_body_sha256}
            for event, read in rows]}


POLICY = 'dmb_surface_evidence_answer_v7'
INSTRUCTIONS = """Native statements record what sources say, not independent proof that embedded events happened.
Use {"kind":"native_statement_report","text":"source-attributed prose","statement_handles":["exact exposed handle"]}.
Select only supports actually relevant to the claim. Preserve all relevant episodes,
reporter, uncertainty, qualifications and nonfactive embedded content. Textual source
order does not prove fictional chronology or causality. Do not attach nearby unsupported
clauses. Partial discovery or no matches never proves universal absence.
"""


def producing_reads(turn, authorization, raw):
    from . import types as t
    if not isinstance(turn.graph_context_receipt, t.PlanNativeContextReceiptV1):
        return ()
    from hashlib import sha256
    from .plan_jev_graph_packet import frame_in_request
    from .rules_authority_types import canonical_sha256
    frame = frame_in_request(raw)
    expected = model_frame(turn)
    if (not isinstance(authorization, t.PlanNativeWriterAuthorizedV1)
            or sha256(raw.encode()).hexdigest() != authorization.envelope_sha256
            or canonical_sha256(frame) != authorization.frame_sha256
            or frame.get('native_statements') != expected):
        raise ValueError('Native statements differ from actual producing input')
    reads = selected_reads(turn)
    if set(authorization.native_statement_read_event_ids) != {event.event_id for event, _ in reads} | {
            event.event_id for event in turn.graph_context_execution.events
            if isinstance(event, NativePlanStatementReadObservedV1)}:
        raise ValueError('Native statement exposure differs from producing authorization')
    return tuple((row['statement_handle'], event, read)
        for row, (event, read) in zip(expected['statements'], reads, strict=True))


def citation(receipt, authorization, read, *, index):
    from .native_statement_answer import NativeStatementClauseCitationV1
    authority, support = receipt.native_query.authority, read.support
    return NativeStatementClauseCitationV1(segment_index=index, statement_id=support.statement_id,
        provider_attempt_id=authorization.provider_attempt_id, envelope_sha256=authorization.envelope_sha256,
        context_receipt_sha256=receipt.context_receipt_sha256,
        managed_world_id=authority.managed_world_id, native_world_id=authority.native_world_id,
        campaign_id=support.payload['clause']['campaign'], read_revision_id=authority.revision_id,
        publication_revision_id=support.publication_receipt['published_revision_id'],
        source_artifact_id=support.source_artifact_id, source_revision_id=support.source_revision_id,
        body_sha256=support.source_body_sha256, start_byte=support.clause_start_byte,
        end_byte=support.clause_end_byte, clause_sha256=support.clause_sha256,
        semantic_digest=support.semantic_digest)


def validate_citations(completion, receipt, execution, authorization):
    from . import types as t
    if not isinstance(receipt, t.PlanNativeContextReceiptV1):
        if getattr(completion, 'native_clause_citations', ()):
            raise ValueError('Native statement citations require their own Plan query')
        return
    if not isinstance(completion, t.SurfaceEvidenceCompletionV6):
        raise ValueError('Native Plan requires its retained native-report completion')
    validate_execution(receipt, execution)
    reads = {read.support.statement_id: read for event in execution.events
        if isinstance(event, NativePlanStatementReadObservedV1)
        and event.event_id in authorization.native_statement_read_event_ids for read in event.reads}
    seen = set()
    for item in completion.native_clause_citations:
        key = item.segment_index, item.statement_id
        if (key in seen or item.segment_index >= len(completion.answer_segments)
                or not isinstance(completion.answer_segments[item.segment_index], t.SourcePassageClaimV1)
                or item.statement_id not in reads
                or item != citation(receipt, authorization, reads[item.statement_id], index=item.segment_index)):
            raise ValueError('Native clause citation differs from original included support')
        seen.add(key)


def input_partial(turn):
    from . import types as t
    receipt = turn.graph_context_receipt
    return isinstance(receipt, t.PlanNativeContextReceiptV1) and (
        isinstance(receipt.native_query, NativePlanQueryV1) and receipt.native_query.status == 'partial'
        or any(isinstance(e, NativePlanStatementReadObservedV1) and e.status == 'partial'
               for e in turn.graph_context_execution.events))
