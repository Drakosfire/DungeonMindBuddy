"""Author-selected identities and immutable context snapshots; never Graph facts."""
from __future__ import annotations

from hashlib import sha256
import json
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

POLICY = 'authored_graph_reference_context_v1'


def digest(value):
    return sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
        separators=(',', ':'), allow_nan=False).encode()).hexdigest()


class Closed(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True, populate_by_name=True)


class AuthoredGraphReferenceV1(Closed):
    schema_: Literal['dmb_authored_graph_reference_v1'] = Field(default='dmb_authored_graph_reference_v1', alias='schema')
    managed_world_id: str
    native_world_id: str
    binding_version: int = Field(strict=True, ge=1)
    graph_revision: str
    node_id: str
    label: str  # Author-facing selection text, not a claim or an evidence source.

    @field_validator('managed_world_id', 'native_world_id', 'graph_revision', 'node_id', 'label')
    @classmethod
    def nonblank(cls, value):
        if not value.strip():
            raise ValueError('A Graph reference needs a nonblank identity and label')
        return value

    def identity(self):
        return self.managed_world_id, self.native_world_id, self.node_id

    def basis(self):
        return self.model_dump(mode='json', by_alias=True, exclude={'label'})


def effective_references(*groups):
    """Collapse identical scoped selections, refusing conflicting origin snapshots."""
    chosen = {}
    for group in groups:
        for ref in group:
            old = chosen.get(ref.identity())
            if old is not None and old.basis() != ref.basis():
                raise ValueError('The same Graph object has conflicting selection snapshots; choose it again')
            chosen.setdefault(ref.identity(), ref)
    return tuple(chosen.values())


class AuthoredGraphReferencesV1(Closed):
    schema_: Literal['dmb_authored_graph_references_v1'] = Field(default='dmb_authored_graph_references_v1', alias='schema')
    references: tuple[AuthoredGraphReferenceV1, ...]

    @model_validator(mode='after')
    def distinct(self):
        if effective_references(self.references) != self.references:
            raise ValueError('Graph reference inputs must contain distinct scoped objects')
        return self

    @property
    def sha256(self):
        return digest(self.model_dump(mode='json', by_alias=True))

    def require_world(self, world):
        if any(ref.managed_world_id != world for ref in self.references):
            raise ValueError('Graph reference belongs to a different managed World')


def source_references(turn):
    """Captured author input only; generated prose cannot create node identity."""
    execution = getattr(turn, 'graph_context_execution', None)
    rows = [event for event in getattr(execution, 'events', ())
            if getattr(event, 'kind', None) == 'build_authored_references_captured_v1']
    if len(rows) > 1:
        raise ValueError('Ambiguous authored Graph reference capture')
    return rows[0].references.references if rows else ()


def policy_enabled(policy):
    return getattr(policy, 'authored_graph_reference_policy', None) == POLICY


def capture(execution):
    rows = [e for e in execution.events if getattr(e, 'kind', None) == 'build_authored_references_captured_v1']
    if len(rows) != 1:
        raise ValueError('Authored references require one immutable input capture')
    return rows[0]


def source_event_ids(execution):
    """Actual mandatory author-requested reads, separate from relevance votes."""
    if not policy_enabled(getattr(execution, 'policy', None)):
        return set()
    return {eid for e in execution.events if getattr(e, 'kind', None) == 'build_authored_reference_read_v1'
            and e.outcome in {'read', 'read_partial'} for eid in e.source_read_event_ids}


def provider_references(references):
    # Client labels are presentation only, including in semantic routing input.
    return {'schema': references.schema_, 'references': [ref.basis() for ref in references.references]}


def writer_context(execution):
    if not policy_enabled(execution.policy):
        return None
    original = capture(execution)
    reads = [e for e in execution.events if getattr(e, 'kind', None) == 'build_authored_reference_read_v1']
    if {e.node_id for e in reads if e.outcome == 'read'} != {r.node_id for r in original.references.references}:
        raise ValueError('A requested Graph reference has not been read successfully')
    return {'policy': POLICY, 'capture_event_id': str(original.event_id),
        'selected_references': provider_references(original.references),
        'read_graph_revision': original.read_graph_revision,
        'reads': [{'event_id': str(e.event_id), 'node_id': e.node_id, 'outcome': e.outcome} for e in reads]}


def validate_execution(execution):
    from . import types as t
    authored = [e for e in execution.events if isinstance(e, (t.BuildAuthoredReferencesCapturedV1, t.BuildAuthoredReferenceAuthorizedV1, t.BuildAuthoredReferenceReadV1))]
    inclusions = [e for e in execution.events if isinstance(e, t.BuildAuthoredProviderInclusionV1)]
    if not policy_enabled(execution.policy):
        if authored or inclusions:
            raise ValueError('Historical policy cannot acquire authored Graph context')
        return
    captures = [e for e in authored if e.kind == 'build_authored_references_captured_v1']
    if len(captures) > 1:
        raise ValueError('Authored Graph references can be captured once')
    if not captures:
        # Initial execution is frozen before its capture is appended at admission.
        if execution.events:
            raise ValueError('Authored Graph references must precede provider authorization')
        return
    c = captures[0]
    if c.references.sha256 != execution.policy.authored_graph_references_sha256 or c.sequence != 0:
        raise ValueError('Authored Graph input differs from its frozen capability')
    scope = execution.policy.source_read_scope
    c.references.require_world(scope.world_id)
    if c.read_graph_revision != scope.graph_revision:
        raise ValueError('Authored Graph read revision differs from current frozen scope')
    references = {r.node_id: r for r in c.references.references}
    if len(references) != len(c.references.references):
        raise ValueError('One frozen World cannot resolve ambiguous node identities')
    events = {e.event_id: e for e in execution.events}
    seen = set()
    completed = set()
    for event in authored:
        if event.kind == 'build_authored_references_captured_v1':
            continue
        if event.capture_event_id != c.event_id or event.node_id not in references:
            raise ValueError('Authored Graph read has no selected identity')
        if event.kind == 'build_authored_reference_authorized_v1':
            if event.node_id in seen:
                raise ValueError('An authored object read cannot be authorized twice')
            seen.add(event.node_id)
            expected = {'retrievalSessionId': scope.retrieval_session_id, 'operation': 'object',
                        'targets': [{'kind': 'node', 'id': event.node_id}]}
            if event.arguments_sha256 != digest(expected):
                raise ValueError('Authored Graph object arguments changed')
        elif event.kind == 'build_authored_reference_read_v1':
            if event.node_id in completed:
                raise ValueError('An authored object result cannot be recorded twice')
            completed.add(event.node_id)
            if event.returned_node_ids != sorted(set(event.returned_node_ids)) or event.node_id not in event.returned_node_ids:
                raise ValueError('Authored object result does not contain its exact selected identity')
            if len(set(event.operation_event_ids)) != len(event.operation_event_ids) or len(set(event.source_read_event_ids)) != len(event.source_read_event_ids):
                raise ValueError('Authored read receipts must have distinct event identities')
            authorized = events.get(event.authorization_event_id)
            if (not isinstance(authorized, t.BuildAuthoredReferenceAuthorizedV1)
                or authorized.node_id != event.node_id or authorized.sequence >= event.sequence):
                raise ValueError('Authored Graph result lacks its exact authorization')
            operations = [events.get(eid) for eid in event.operation_event_ids]
            if not operations or any(not isinstance(e, t.ValidatedGraphOperationEventV3)
                or e.sequence != authorized.sequence + 1 or e.sequence >= event.sequence
                or e.request_arguments_sha256 != authorized.arguments_sha256
                or e.graph_revision != scope.graph_revision for e in operations):
                raise ValueError('Authored Graph result differs from its actual object read')
            pins = {p.anchor_id: p for e in operations for p in e.returned_source_pins}
            supplied = set()
            for eid in event.source_read_event_ids:
                read = events.get(eid)
                if not isinstance(read, t.ValidatedSourceReadEventV2) or read.sequence >= event.sequence:
                    raise ValueError('Authored Graph context requires actual source reads')
                for receipt in read.receipts:
                    pin = pins.get(receipt.anchor_id)
                    if pin is None:
                        continue
                    complete = (receipt.outcome == 'enough' and not receipt.truncated
                        and receipt.evidence_sufficiency_status == 'sufficient')
                    unavailable_revision = (event.outcome == 'source_gap'
                        and receipt.outcome == 'unavailable' and receipt.source_revision_id is None)
                    if (receipt.evidence_ref_id != pin.evidence_ref_id
                        or receipt.source_artifact_id != pin.source_artifact_id
                        or (receipt.source_revision_id != pin.source_revision_id and not unavailable_revision)
                        or (not complete and event.outcome != 'source_gap')):
                        raise ValueError('Authored Graph passage lacks complete exact source support')
                    if complete:
                        supplied.add(receipt.anchor_id)
            partial = any(e.truncated or e.coverage_status != 'complete' or e.evidence_sufficiency_status != 'sufficient' for e in operations)
            if event.outcome in {'read', 'read_partial'} and (event.outcome == 'read_partial') != partial:
                raise ValueError('Authored Graph context must preserve partial object coverage')
            if event.outcome in {'read', 'read_partial'} and (not pins or set(pins) != supplied):
                raise ValueError('Authored Graph reference was marked read without all source support')
    writers = [e for e in execution.events if isinstance(e, t.ProviderAttemptAuthorizedEventV1)
               and (e.provider, e.model, e.api_mode) == execution.policy.provider_roles.writer.identity()]
    seen_providers = set()
    for inclusion in inclusions:
        if (inclusion.provider_attempt_id in seen_providers or inclusion.capture_event_id != c.event_id
            or inclusion.references_sha256 != c.references.sha256
            or inclusion.source_read_event_ids != sorted(source_event_ids(execution), key=str)):
            raise ValueError('Authored provider inclusion differs from frozen acquired references')
        seen_providers.add(inclusion.provider_attempt_id)
        if any(e.sequence >= inclusion.sequence for e in authored):
            raise ValueError('Authored provider inclusion must follow acquisition')
    if writers:
        writer_context(execution)
        for writer in writers:
            require_writer_inclusion(execution, writer)
        for event in authored:
            if event.sequence >= writers[0].sequence:
                raise ValueError('Authored Graph acquisition must settle before writing')


def authorize_operation(turn, arguments):
    """Author input grants only one exact object read, never a search or write."""
    from . import types as t
    execution = turn.graph_context_execution
    if not policy_enabled(execution.policy) or turn.status != 'running':
        return False
    digest_args = digest(arguments)
    for event in execution.events[-1:]:
        if isinstance(event, t.BuildAuthoredReferenceAuthorizedV1) and event.arguments_sha256 == digest_args:
            if any(isinstance(e, t.ValidatedGraphOperationEventV3)
                   and e.sequence > event.sequence and e.request_arguments_sha256 == digest_args for e in execution.events):
                return False
            return True
    return False



def source_authorization_error(turn, anchor_ids):
    """Permit only fresh exact pins of the pending author-owned object read."""
    from . import types as t
    execution = turn.graph_context_execution
    if turn.status != 'running' or not policy_enabled(execution.policy):
        return 'source_read_before_authorization'
    if not anchor_ids or len(set(anchor_ids)) != len(anchor_ids):
        return 'invalid_authored_source_anchors'
    if any(isinstance(e, t.ProviderAttemptAuthorizedEventV1)
           and (e.provider,e.model,e.api_mode) == execution.policy.provider_roles.writer.identity()
           for e in execution.events):
        return 'authored_source_acquisition_closed'
    authorizations = [e for e in execution.events if isinstance(e,t.BuildAuthoredReferenceAuthorizedV1)]
    if not authorizations:
        return 'source_read_before_authorization'
    authorization = authorizations[-1]
    if any(isinstance(e,t.BuildAuthoredReferenceReadV1) and e.authorization_event_id == authorization.event_id for e in execution.events):
        return 'authored_source_acquisition_closed'
    operations = [e for e in execution.events if isinstance(e,t.ValidatedGraphOperationEventV3)
        and e.sequence == authorization.sequence+1 and e.request_arguments_sha256 == authorization.arguments_sha256]
    if len(operations) != 1:
        return 'authored_source_object_unsettled'
    pins = {p.anchor_id for p in operations[0].returned_source_pins}
    if not set(anchor_ids).issubset(pins):
        return 'authored_source_anchor_unselected'
    for prior in execution.events:
        if isinstance(prior,t.SourceReadAuthorizationEventV2) and set(anchor_ids).intersection(p.anchor_id for p in prior.anchors):
            settled = any(isinstance(e,t.ValidatedSourceReadEventV2) and e.read_call_id == prior.read_call_id for e in execution.events)
            return 'authored_source_receipt_requires_recovery' if settled else 'authored_source_read_indeterminate'
    return None


def validate_packet(packet, execution):
    expected = writer_context(execution)
    if packet.get('authored_reference_context') != expected:
        raise ValueError('Writer authored reference context differs from its actual acquired input')


def validate_object_result_proof(event, execution, proof):
    """Admission joins native result bytes to the existing validated operation digest."""
    from .types import ValidatedGraphOperationEventV3
    if not isinstance(proof, dict) or set(proof) != {str(eid) for eid in event.operation_event_ids}:
        raise ValueError('Authored object result requires exact validated operation bytes')
    records = {e.event_id: e for e in execution.events if isinstance(e, ValidatedGraphOperationEventV3)}
    nodes = set()
    for eid in event.operation_event_ids:
        packet = dict(proof[str(eid)])
        for key in ('retrievalSessionId', 'addedClaimIds', 'claimLedger'):
            packet.pop(key, None)
        operation = records.get(eid)
        if operation is None or digest(packet) != operation.result_packet_sha256:
            raise ValueError('Authored object result differs from its validated native result')
        if packet.get('operation') != 'object' or packet.get('requestedNodeId') != event.node_id:
            raise ValueError('Authored result belongs to another requested object')
        nodes.update(node['nodeId'] for node in packet.get('nodes', []))
    if event.node_id not in nodes or event.returned_node_ids != sorted(nodes):
        raise ValueError('Authored object result does not contain its selected identity')


def require_writer_inclusion(execution, writer):
    from .types import BuildAuthoredProviderInclusionV1
    if not policy_enabled(execution.policy):
        return
    matches = [e for e in execution.events if isinstance(e, BuildAuthoredProviderInclusionV1)
        and e.provider_attempt_id == writer.provider_attempt_id]
    if len(matches) != 1 or matches[0].sequence >= writer.sequence or matches[0].envelope_sha256 != writer.envelope_sha256:
        raise ValueError('Writer lacks its exact admitted authored-reference input proof')



def protected_source_material(turn, traces):
    """Exact prior-attempt bytes joined to immutable same-turn read receipts."""
    from . import types as t
    from .context_trace import TraceSourcePassage, TurnContextTraceV1
    execution = turn.graph_context_execution
    events = {e.event_id:e for e in execution.events}
    required = source_event_ids(execution)
    inventory, references = {}, []
    traces = [TurnContextTraceV1.model_validate(trace) for trace in traces]
    for trace in traces:
        if (trace.world_id != turn.world_id or trace.conversation_id != turn.conversation_id
            or trace.turn_id != turn.turn_id or trace.attempt > turn.attempt):
            raise ValueError('Protected source trace belongs to another turn or attempt')
        for passage in trace.observations:
            if not isinstance(passage,TraceSourcePassage) or passage.source_read_event_id not in required:
                continue
            key=(str(passage.source_read_event_id),passage.source_read_id)
            event=events[passage.source_read_event_id]
            receipts=[r for r in event.receipts if r.source_read_id == passage.source_read_id]
            auths=[e for e in execution.events if isinstance(e,t.SourceReadAuthorizationEventV2) and e.read_call_id == event.read_call_id]
            later_starts=[other.execution_start_sequence for other in traces if other.attempt > trace.attempt]
            if (key in inventory or len(receipts)!=1 or len(auths)!=1
                or event.sequence < trace.execution_start_sequence
                or later_starts and event.sequence >= min(later_starts)):
                raise ValueError('Protected source capture has ambiguous read or physical-attempt ownership')
            receipt=receipts[0]
            if (passage.read_call_id != event.read_call_id
                or passage.world_id != execution.policy.source_read_scope.world_id
                or passage.graph_revision != execution.policy.source_read_scope.graph_revision
                or receipt.outcome != 'enough' or receipt.truncated or receipt.evidence_sufficiency_status != 'sufficient'
                or passage.outcome != receipt.outcome or not passage.source_name or not passage.source_name.strip()
                or any(getattr(passage,k) != getattr(receipt,k) for k in ('anchor_id','evidence_ref_id',
                    'source_artifact_id','source_revision_id','line_start','line_end','returned_chars','content_sha256'))
                or len(passage.text) != receipt.returned_chars or sha256(passage.text.encode()).hexdigest() != receipt.content_sha256
                or not any(pin.anchor_id == receipt.anchor_id and pin.evidence_ref_id == receipt.evidence_ref_id
                    and pin.source_artifact_id == receipt.source_artifact_id and pin.source_revision_id == receipt.source_revision_id
                    for pin in auths[0].anchors)):
                raise ValueError('Protected source body differs from its exact authorization and receipt')
            inventory[key]=passage.model_dump(mode='json')
            references.append({'schema':'dmb_trace_historical_source_ref_v1','world_id':trace.world_id,
                'conversation_id':str(trace.conversation_id),'turn_id':str(trace.turn_id),'attempt':trace.attempt,
                'trace_id':str(trace.trace_id),'source_read_event_id':str(passage.source_read_event_id),
                'source_read_id':passage.source_read_id,'content_sha256':passage.content_sha256})
    return {'observations':list(inventory.values()),'historical_source_reads':references}


def load_protected_source_material(conn, turn):
    from .context_trace import TurnContextTraceV1
    from .context_trace_store import validate_authored_reference_observation, validate_prompt_authorization
    from .context_trace import TraceAuthoredGraphReferenceV1, TracePromptReference
    rows=conn.execute('SELECT payload,attempt FROM agent.turn_context_trace WHERE turn_id=%s ORDER BY attempt',(turn.turn_id,)).fetchall()
    traces=[]
    for payload,attempt in rows:
        trace=TurnContextTraceV1.model_validate(payload)
        if trace.attempt != attempt:
            raise ValueError('Protected trace attempt differs from its stored row')
        for observation in trace.observations:
            if isinstance(observation,TraceAuthoredGraphReferenceV1):
                validate_authored_reference_observation(observation,turn.graph_context_execution.model_dump(mode='json',by_alias=True),trace)
            if isinstance(observation,TracePromptReference):
                validate_prompt_authorization(observation,turn.graph_context_execution.model_dump(mode='json',by_alias=True),trace.execution_start_sequence)
        traces.append(trace)
    return protected_source_material(turn,traces)


def validate_writer_input(packet, execution, trace):
    """Compare actual input with protected source bytes; retain only the proof digest."""
    validate_packet(packet, execution)
    if not policy_enabled(execution.policy):
        if 'authored_reference_passages' in packet:
            raise ValueError('Historical writer cannot gain authored source material')
        return None
    from . import types as t
    rows = [row for row in trace.get('observations', []) if row.get('kind') == 'source_passage']
    captured = {(str(row.get('source_read_event_id')), str(row.get('source_read_id'))): row for row in rows}
    if len(captured) != len(rows):
        raise ValueError('Protected source captures must have unique event and read identities')
    events = {e.event_id: e for e in execution.events}
    reads = [read for read in execution.events
        if isinstance(read, t.BuildAuthoredReferenceReadV1) and read.outcome == 'read']
    # Match writer_material's sorted union and opened_world_passages' donor rule.
    # Every object keeps its read receipt; shared physical source bytes appear once.
    operation_ids = sorted({eid for read in reads for eid in read.operation_event_ids}, key=str)
    donors = {pin.anchor_id: eid for eid in operation_ids for pin in events[eid].returned_source_pins}
    required_by_read = {}
    for read in reads:
        pins = {pin.anchor_id: (operation.event_id, pin) for eid in read.operation_event_ids
            for operation in [events[eid]] for pin in operation.returned_source_pins}
        for eid in read.source_read_event_ids:
            for receipt in events[eid].receipts:
                if receipt.anchor_id not in pins:
                    continue
                origin, pin = pins[receipt.anchor_id]
                row = captured.get((str(eid), str(receipt.source_read_id)))
                if (row is None or row.get('anchor_id') != receipt.anchor_id
                    or row.get('evidence_ref_id') != receipt.evidence_ref_id
                    or row.get('source_artifact_id') != receipt.source_artifact_id
                    or row.get('source_revision_id') != receipt.source_revision_id
                    or row.get('line_start') != receipt.line_start or row.get('line_end') != receipt.line_end
                    or not isinstance(row.get('text'), str)
                    or sha256(row['text'].encode()).hexdigest() != receipt.content_sha256
                    or not isinstance(row.get('source_name'), str) or not row['source_name'].strip()):
                    raise ValueError('Authored writer source differs from protected complete read bytes')
                from .build_world_context import WorldPassageOrigin
                proof = WorldPassageOrigin(operation_event_id=donors[receipt.anchor_id], source_read_event_id=eid,
                    source_read_id=receipt.source_read_id, anchor_id=receipt.anchor_id,
                    evidence_ref_id=receipt.evidence_ref_id, source_artifact_id=receipt.source_artifact_id,
                    source_revision_id=receipt.source_revision_id, content_sha256=receipt.content_sha256,
                    line_start=receipt.line_start, line_end=receipt.line_end)
                material = {'origin': proof.model_dump(mode='json'), 'text': row['text'], 'source_name': row['source_name'].strip()}
                identity = (str(eid), str(receipt.source_read_id))
                if identity in required_by_read and required_by_read[identity] != material:
                    raise ValueError('Shared authored source receipts disagree')
                required_by_read[identity] = material
    required = list(required_by_read.values())
    if packet.get('schema') in {'dmb_build_compose_input_v1', 'dmb_build_image_direction_input_v1'}:
        actual = packet.get('authored_reference_passages')
        key = lambda row: digest(row)
        if not isinstance(actual, list) or sorted(map(key, actual)) != sorted(map(key, required)):
            raise ValueError('Authored writer material differs from exact object/source reads')
    else:
        actual = packet.get('opened_passages', [])
        for row in required:
            origin = row['origin']
            if not any(p.get('text') == row['text'] and p.get('source_name') == row['source_name']
                and all(p.get(k) == origin[k] for k in ('source_artifact_id','source_revision_id','line_start','line_end')) for p in actual):
                raise ValueError('Discussion writer omitted an authored source passage')
    return digest({'context': writer_context(execution), 'passages': required})


def validate_provider_inclusion(event, execution, prepared_request_json, trace):
    from .source_writer_output import strict_json
    if not isinstance(prepared_request_json, str) or sha256(prepared_request_json.encode()).hexdigest() != event.envelope_sha256:
        raise ValueError('Authored writer proof differs from actual prepared request')
    body = strict_json(prepared_request_json)
    packet = strict_json(body['input'])
    if validate_writer_input(packet, execution, trace) != event.material_sha256:
        raise ValueError('Authored writer proof differs from its acquired material')


def validate_stored_writer(conn, turn, writer, request_json=None):
    """Final proposal/recovery uses admitted proof; images also reopen retained bytes."""
    execution = turn.graph_context_execution
    if not policy_enabled(execution.policy):
        return
    require_writer_inclusion(execution, writer)
    if request_json is not None:
        from .types import BuildAuthoredProviderInclusionV1
        inclusion = next(e for e in execution.events if isinstance(e, BuildAuthoredProviderInclusionV1)
            and e.provider_attempt_id == writer.provider_attempt_id)
        validate_provider_inclusion(inclusion, execution, request_json, load_protected_source_material(conn, turn))
