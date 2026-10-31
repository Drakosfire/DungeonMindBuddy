"""Core-owned assertion support reads after the exact APP selection grant."""
from dungeonmind.application.vnext import EvidenceReadService, open_admitted_native_text
from dungeonmind.contracts.vnext.domain import Assertion
from dungeonmind.contracts.vnext.source import EvidenceRefV3
from application_state.agent_conversation.native_statement_input import digest
from application_state.agent_conversation.native_plan_assertions import (
    NativePlanAssertionMatchV1, NativePlanQueryV2, NativePlanAssertionReadAuthorizedV1,
    NativePlanAssertionReadV1, NativeAssertionSpanV1,
)


def matches(entities, *, excluded_subjects):
    """Only assertions returned by Core's scoped complete-entity reads; no body IO."""
    found = {}
    for entity_id, entity in entities.items():
        if not entity.found or entity.completeness.status != 'complete':
            continue
        names = {a.value.value for a in entity.assertions if a.subject_entity_id == entity_id
            and a.predicate == 'dnd5e:name' and getattr(a.value, 'kind', None) == 'literal'
            and isinstance(a.value.value, str) and a.value.value.strip()}
        label = next(iter(names)) if len(names) == 1 else entity_id
        for parsed in entity.assertions:
            if parsed.subject_entity_id in excluded_subjects:
                continue  # Qualified source-statement semantics have their own contract.
            assertion = Assertion.model_validate(parsed, from_attributes=True)
            row = found.setdefault(assertion.assertion_id, [assertion, set(), assertion.subject_entity_id])
            row[1].add(entity_id)
            if assertion.subject_entity_id == entity_id:
                row[2] = label
    return tuple(NativePlanAssertionMatchV1(assertion_id=a.assertion_id,
        subject_entity_id=a.subject_entity_id, discovered_entity_ids=tuple(sorted(witnesses)),
        assertion_sha256=digest(a), label=f'{label} · {a.predicate}')
        for a, witnesses, label in sorted(found.values(), key=lambda row: row[0].assertion_id))


def read_selected(context, authorization, principal):
    from .native_plan_statements import _principal
    _principal(principal)
    query = context.query
    if (not isinstance(query, NativePlanQueryV2)
            or not isinstance(authorization, NativePlanAssertionReadAuthorizedV1)
            or authorization.query_sha256 != query.sha256):
        raise ValueError('Selected assertion requires its exact query authorization')
    authority = query.authority
    if context.resolve_binding(authority.managed_world_id) != context.binding:
        raise ValueError('Native assertion query binding changed before selected read')
    inventory = {m.assertion_id: m for m in query.assertion_matches}
    if not set(authorization.assertion_ids) <= set(inventory):
        raise ValueError('Selected assertion was not discovered by this query')
    read_context, access, _, _ = context.pinned
    reads, unavailable = [], []
    for identity in authorization.assertion_ids:
        result = EvidenceReadService().get_assertion_evidence(read_context, identity)
        if (result.identity.space_id, result.identity.revision_id) != (authority.native_world_id, authority.revision_id):
            raise ValueError('Core assertion read changed pinned authority')
        if not result.available or result.completeness.status != 'complete' or result.assertion is None:
            unavailable.append(identity)
            continue
        assertion = Assertion.model_validate(result.assertion, from_attributes=True)
        match = inventory[identity]
        if digest(assertion) != match.assertion_sha256 or assertion.subject_entity_id != match.subject_entity_id:
            raise ValueError('Native assertion changed after discovery')
        refs = tuple(EvidenceRefV3.model_validate(e, from_attributes=True) for e in result.evidence)
        supports = [e for e in refs if e.evidence_role == 'support']
        if not supports:
            unavailable.append(identity)
            continue
        spans = []
        for ref in supports:
            opened = open_admitted_native_text(access, ref.evidence_ref_id)
            if opened.status != 'available':
                break
            # Core owns receipt, source identity, scope, digest and UTF8 admission.
            if opened.source_authority_epoch != access.source_view.epoch:
                raise ValueError('Core source access changed its pinned acquisition epoch')
            text = opened.body_text.encode()[opened.span_start_byte:opened.span_end_byte].decode()
            spans.append(NativeAssertionSpanV1(evidence_ref_id=ref.evidence_ref_id,
                source_artifact_id=opened.source_artifact_id, source_revision_id=opened.source_revision_id,
                body_sha256=opened.body_sha256, start_byte=opened.span_start_byte, end_byte=opened.span_end_byte,
                span_sha256=opened.span_sha256, text=text))
        if len(spans) != len(supports):
            unavailable.append(identity)
            continue
        reads.append(NativePlanAssertionReadV1(assertion=assertion, evidence=refs, spans=tuple(spans)))
    if context.resolve_binding(authority.managed_world_id) != context.binding:
        raise ValueError('Native assertion query binding changed during selected read')
    return tuple(reads), tuple(unavailable)
