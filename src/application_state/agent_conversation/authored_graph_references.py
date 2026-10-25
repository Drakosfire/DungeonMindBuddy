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
    if not policy_enabled(execution.policy):
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
    authored = [e for e in execution.events if getattr(e, 'kind', '').startswith('build_authored_')]
    if not policy_enabled(execution.policy):
        if authored:
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
                    if (receipt.evidence_ref_id != pin.evidence_ref_id
                        or receipt.source_artifact_id != pin.source_artifact_id
                        or receipt.source_revision_id != pin.source_revision_id
                        or receipt.outcome != 'enough' or receipt.truncated
                        or receipt.evidence_sufficiency_status != 'sufficient'):
                        raise ValueError('Authored Graph passage lacks complete exact source support')
                    supplied.add(receipt.anchor_id)
            partial = any(e.truncated or e.coverage_status != 'complete' or e.evidence_sufficiency_status != 'sufficient' for e in operations)
            if event.outcome in {'read', 'read_partial'} and (event.outcome == 'read_partial') != partial:
                raise ValueError('Authored Graph context must preserve partial object coverage')
            if event.outcome in {'read', 'read_partial'} and (not pins or set(pins) != supplied):
                raise ValueError('Authored Graph reference was marked read without all source support')
    writers = [e for e in execution.events if isinstance(e, t.ProviderAttemptAuthorizedEventV1)
               and (e.provider, e.model, e.api_mode) == execution.policy.provider_roles.writer.identity()]
    if writers:
        writer_context(execution)
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
