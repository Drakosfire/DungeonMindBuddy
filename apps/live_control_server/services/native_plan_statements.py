"""Read-only Core composition for ordinary Plan native-statement discovery.

Search summaries stay host-only. Clause IO occurs only after the owning APP read
selection has been durably recorded. No repository or ID is accepted from a user.
"""
from dataclasses import dataclass
import json
from dungeonmind.application.vnext import SearchReadService, EntityReadService
from application_state.agent_conversation.native_plan_statements import (
    NativePlanQueryAuthorityV1, NativePlanQueryUnavailableV1, NativePlanQueryV1,
    NativePlanStatementMatchV1, NativePlanStatementReadV1, NativePlanStatementReadAuthorizedV1, validate_support_authority,
)
from . import source_statements as statements
from .native_statement_answer_context import header, build_support
from .managed_world_graph_projection import resolve_managed_world_binding
from .world_graph_projection import WorldGraphProjectionServiceError


@dataclass(frozen=True)
class QueryContext:
    query: NativePlanQueryV1
    binding: object
    pinned: tuple
    repository: object
    principal: object
    resolve_binding: object


def _principal(principal):
    if principal is None or principal.role != 'gm':
        raise ValueError('Native Plan query requires authenticated GM authority')


def _payload(entity, statement_id):
    summaries = [a for a in entity.assertions
        if a.subject_entity_id == statement_id and a.predicate == 'dnd5e:summary']
    if not summaries:
        return None
    payloads = []
    for a in summaries:
        raw = getattr(a.value, 'value', None)
        if not isinstance(raw, str):
            continue
        try:
            payload = json.loads(raw, object_pairs_hook=statements._unique)
        except ValueError:
            continue
        if isinstance(payload, dict) and payload.get('schema') == 'dmb_source_statement_v1':
            statements._validate_payload(payload)
            payloads.append(payload)
    if not payloads:
        return None
    if len(payloads) != 1 or len(summaries) != 1:
        raise ValueError('Native statement has conflicting qualified summaries')
    return payloads[0]


def _subject_labels(statement_id, paths, entities, campaign):
    """Navigation from admitted ABOUT/name records, never statement meaning."""
    subjects = []
    for identity, witnesses in paths:
        if identity == statement_id:
            continue
        entity = entities[identity]
        about = {a.assertion_id for a in entity.assertions
            if a.subject_entity_id == statement_id and a.predicate == statements.mapping.ABOUT
            and getattr(a.value, 'entity_id', None) == identity}
        if not set(witnesses) <= about:
            raise ValueError('Navigation subject differs from admitted ABOUT witness')
        names = {a.value.value.strip() for a in entity.assertions
            if a.subject_entity_id == identity and a.predicate == 'dnd5e:name'
            and getattr(a.value, 'kind', None) == 'literal'
            and isinstance(a.value.value, str) and a.value.value.strip()
            and tuple((b.axis, b.value) for b in a.metadata.scope)
                == ((statements.CAMPAIGN_SCOPE_AXIS, campaign),)} if entity.found and entity.completeness.status == 'complete' else set()
        subjects.append(f'{next(iter(names))} [{identity}]' if len(names) == 1 else identity)
    return ', '.join(sorted(set(subjects)))


def prepare_query(managed_world_id, question, principal, *, source_context=None,
                  revision_id=None, repository=None, resolve_binding=None,
                  scope_mode='world', campaign_id=None):
    _principal(principal)
    resolve = resolve_binding or resolve_managed_world_binding
    try:
        bound = resolve(managed_world_id)
    except WorldGraphProjectionServiceError as exc:
        if exc.code not in {'native_graph_binding_missing', 'native_graph_binding_inactive',
                            'native_graph_provisioning_pending'}:
            raise
        return None, NativePlanQueryUnavailableV1(managed_world_id=managed_world_id,
            reason='native_graph_binding_unavailable')
    if bound.managed_world_id != managed_world_id:
        raise ValueError('Active query binding differs from requested World')
    repo = repository if repository is not None else statements.native.repository()
    space = bound.native_world_id
    if source_context is not None:
        source = source_context.authority
        if ((source.managed_world_id, source.native_world_id, source.binding_version)
                != (managed_world_id, space, bound.binding_version)):
            raise ValueError('Independent native capabilities differ in World ownership')
        if revision_id is not None and revision_id != source.revision_id:
            raise ValueError('Independent native capabilities differ in pinned R')
        revision_id = source.revision_id
        access = source_context.access
        from graph_memory.vnext.domain_runtime import DungeonBuddyVNextProjectionInput, build_dungeonbuddy_read_context
        read = build_dungeonbuddy_read_context(parsed_revision=access.parsed,
            projection_input=DungeonBuddyVNextProjectionInput(world_id=space,
                revision_id=revision_id, role='gm', scope_mode=scope_mode, campaign_id=campaign_id),
            source_reader=access.source_view)
        domain, profile = statements.native.descriptors(repo, space, revision_id)
        pinned = read, access, domain, profile
    else:
        if revision_id is None:
            head = repo.get_head(space)
            if head is None:
                return None, NativePlanQueryUnavailableV1(managed_world_id=managed_world_id,
                    reason='native_graph_head_unavailable')
            revision_id = head.head_revision_id
        pinned = statements._context(repo, space, revision_id, campaign_id, 'gm', scope_mode=scope_mode)
    h = header(repo.get_revision(space, revision_id))
    authority = NativePlanQueryAuthorityV1(managed_world_id=managed_world_id, native_world_id=space,
        binding_version=bound.binding_version, revision_id=revision_id,
        domain_ref=h['domain_ref'], profile_ref=h['profile_ref'],
        acquisition_epoch=pinned[1].source_view.epoch, scope_mode=scope_mode, campaign_id=campaign_id)
    result = SearchReadService().search_entities(pinned[0], question)
    if (result.identity.space_id, result.identity.revision_id) != (space, revision_id):
        raise ValueError('Core search changed query authority')
    gaps = [] if result.completeness.status == 'complete' else ['native_search_partial']
    discovered = tuple(hit.entity.entity_id for hit in result.hits)
    routes, entities = {}, {}
    for hit in result.hits:
        entity_id = hit.entity.entity_id
        obj = EntityReadService().get_complete_entity(pinned[0], entity_id)
        entities[entity_id] = obj
        if obj.completeness.status != 'complete':
            gaps.append('native_entity_partial')
        direct = [a.assertion_id for a in obj.assertions
            if a.subject_entity_id == entity_id and a.predicate == 'dnd5e:summary']
        if direct:
            routes.setdefault(entity_id, []).append((entity_id, direct))
        for a in obj.assertions:
            if (a.predicate == statements.mapping.ABOUT
                    and getattr(a.value, 'entity_id', None) == entity_id
                    and a.subject_entity_id != entity_id):
                routes.setdefault(a.subject_entity_id, []).append((entity_id, [a.assertion_id]))
    matches = []
    for statement_id, paths in routes.items():
        obj = entities.get(statement_id)
        if obj is None:
            obj = EntityReadService().get_complete_entity(pinned[0], statement_id)
        if not obj.found or obj.completeness.status != 'complete':
            gaps.append('native_statement_entity_unavailable')
            continue
        try:
            payload = _payload(obj, statement_id)
        except (ValueError, TypeError, KeyError, AttributeError):
            gaps.append('native_statement_payload_invalid')
            continue
        if payload is None:
            continue
        clause = payload['clause']
        if (clause['world'] != space or scope_mode == 'campaign' and clause['campaign'] != campaign_id):
            raise ValueError('Admitted qualified statement changed query scope')
        # Only Core-returned links seed this complete entity, never a global scan.
        own_ids = {a.assertion_id for a in obj.assertions if a.subject_entity_id == statement_id}
        witness_ids = {a for _, ids in paths for a in ids}
        if not witness_ids <= own_ids:
            raise ValueError('Statement discovery links differ from admitted complete entity')
        logical = clause['logical_source']
        subjects = _subject_labels(statement_id, paths, entities, clause['campaign'])
        matches.append(NativePlanStatementMatchV1(statement_id=statement_id,
            discovered_entity_ids=tuple(sorted({node for node, _ in paths})),
            discovery_assertion_ids=tuple(sorted(witness_ids)), campaign_id=clause['campaign'],
            logical_source=logical, episode=payload['episode'],
            label=(f"About {subjects} · " if subjects else "")
                + f"{logical['object_id']} — {payload['episode']} ({clause['campaign']})"))
    query = NativePlanQueryV1(authority=authority, question=question,
        search_result_sha256=result.result_digest, discovered_entity_ids=discovered,
        matches=tuple(matches), status='partial' if gaps else 'complete', gap_codes=tuple(sorted(set(gaps))))
    if resolve(managed_world_id) != bound:
        raise ValueError('Active Graph binding changed during native query')
    return QueryContext(query, bound, pinned, repo, principal, resolve), query


def read_selected(context, authorization, principal, *, resolve_binding=None):
    """Trusted caller must first persist an exact selected-read authorization."""
    _principal(principal)
    query, repo = context.query, context.repository
    authority = query.authority
    resolve = resolve_binding or context.resolve_binding
    if resolve(authority.managed_world_id) != context.binding:
        raise ValueError('Native query binding changed before selected read')
    if not isinstance(authorization, NativePlanStatementReadAuthorizedV1) or authorization.query_sha256 != query.sha256:
        raise ValueError('Selected read requires its exact native query authorization')
    statement_ids = authorization.statement_ids
    matches = {m.statement_id: m for m in query.matches}
    if len(statement_ids) != len(set(statement_ids)) or not set(statement_ids) <= set(matches):
        raise ValueError('Selected statement was not discovered by this query')
    reads, unavailable = [], []
    for identity in statement_ids:
        match = matches[identity]
        try:
            bundle = statements._bundle(repo, authority.native_world_id, authority.revision_id,
                match.campaign_id, identity, 'gm', pinned=context.pinned)
            if not set(match.discovery_assertion_ids) <= set(bundle['assertion_ids']):
                raise ValueError('Selected bundle differs from discovery witness')
            support, body_size = build_support(repo, authority.native_world_id,
                authority.revision_id, bundle, context.pinned, with_body_size=True)
            read = NativePlanStatementReadV1(support=support, source_body_bytes=body_size)
            validate_support_authority(authority, read)
            reads.append(read)
        except statements.StatementUnavailableError:
            unavailable.append(identity)
    if resolve(authority.managed_world_id) != context.binding:
        raise ValueError('Native query binding changed during selected read')
    return tuple(reads), tuple(unavailable)


def reopen_context(query, principal):
    """Current access to a retained query's original R, without re-running search."""
    _principal(principal)
    authority = query.authority
    bound = resolve_managed_world_binding(authority.managed_world_id)
    if (bound.native_world_id, bound.binding_version) != (authority.native_world_id, authority.binding_version):
        raise ValueError('Historical native query binding changed')
    repo = statements.native.repository()
    pinned = statements._context(repo, authority.native_world_id, authority.revision_id,
        authority.campaign_id, principal.role, scope_mode=authority.scope_mode)
    h = header(repo.get_revision(authority.native_world_id, authority.revision_id))
    if (h['domain_ref'] != authority.domain_ref.model_dump() or h['profile_ref'] != authority.profile_ref.model_dump()
            or pinned[1].source_view.epoch < authority.acquisition_epoch):
        raise ValueError('Historical native query authority changed')
    return QueryContext(query, bound, pinned, repo, principal, resolve_managed_world_binding)
