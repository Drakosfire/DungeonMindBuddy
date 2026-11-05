"""Surface-neutral native Graph discovery and selected support reads.

Core owns Graph/source admission. APP owns durable selection grants. This host
composition uses those owners without a page, Plan, writer or UI dependency.
Query discovery never opens supporting text; selected reads and citation reopening
share the same pinned authority and binding checks.
"""
from dataclasses import dataclass
import json
from dungeonmind.application.vnext import (
    SearchReadService, EntityReadService, EvidenceReadService, open_admitted_native_text,
)
from apps.live_control_server.integrations.dungeonmind.native_registry_source import assertion_contract
from dungeonmind.contracts.vnext.source import EvidenceRefV3
from application_state.agent_conversation.native_statement_input import digest
from application_state.agent_conversation.native_plan_assertions import (
    NativePlanAssertionMatchV1, NativePlanQueryV2, NativePlanAssertionReadAuthorizedV1,
    NativePlanAssertionReadV1, NativeAssertionSpanV1, NativeGraphQueryV3, NativeGraphQueryV4, NativeObjectMatchV1, NativeAuthoredTargetV1,
)
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


def _require_gm(principal):
    if principal is None or principal.role != 'gm':
        raise ValueError('Native Graph query requires authenticated GM authority')


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


def _assertion_matches(entities, *, excluded_subjects):
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
            assertion = assertion_contract(parsed)
            row = found.setdefault(assertion.assertion_id, [assertion, set(), assertion.subject_entity_id])
            row[1].add(entity_id)
            if assertion.subject_entity_id == entity_id:
                row[2] = label
    return tuple(NativePlanAssertionMatchV1(assertion_id=a.assertion_id,
        subject_entity_id=a.subject_entity_id, discovered_entity_ids=tuple(sorted(witnesses)),
        assertion_sha256=digest(a), label=f'{label} · {a.predicate}')
        for a, witnesses, label in sorted(found.values(), key=lambda row: row[0].assertion_id))


def _entity_catalog(identities, pinned, *, space, revision_id, scope_mode, campaign_id, read_entity):
    """Compose one catalog from actual scoped Core entities, without body IO."""
    gaps = []
    routes, entities = {}, {}
    for entity_id in identities:
        obj = read_entity(revision_id, entity_id, pinned)
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
    qualified_subjects = set()
    for statement_id, paths in routes.items():
        obj = entities.get(statement_id)
        if obj is None:
            obj = read_entity(revision_id, statement_id, pinned)
        if not obj.found or obj.completeness.status != 'complete':
            gaps.append('native_statement_entity_unavailable')
            continue
        try:
            payload = _payload(obj, statement_id)
        except (ValueError, TypeError, KeyError, AttributeError):
            qualified_subjects.add(statement_id)
            gaps.append('native_statement_payload_invalid')
            continue
        if payload is None:
            continue
        qualified_subjects.add(statement_id)
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
    return (tuple(matches), _assertion_matches(entities, excluded_subjects=qualified_subjects),
        tuple(sorted(set(gaps))), entities)


def prepare_query(managed_world_id, question, principal, *, source_context=None,
                  revision_id=None, repository=None, resolve_binding=None,
                  scope_mode='world', campaign_id=None, authored_references=None):
    _require_gm(principal)
    if authored_references is not None:
        from application_state.agent_conversation.authored_graph_references import AuthoredGraphReferencesV1, AuthoredReferencesV2, object_selections
        if type(authored_references) not in {AuthoredGraphReferencesV1, AuthoredReferencesV2} or scope_mode != 'world' or campaign_id is not None:
            raise ValueError('Authored references require their exact World-scoped human input')
        authored_references.require_world(managed_world_id)
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
    if authored_references is not None and any(
            (ref.native_world_id, ref.binding_version) != (bound.native_world_id, bound.binding_version)
            for ref in object_selections(authored_references)):
        raise ValueError('Authored reference World binding changed')
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
    entities_by_revision = {}
    def read_entity(at_revision, entity_id, context):
        key = at_revision, entity_id
        if key not in entities_by_revision:
            entity = EntityReadService().get_complete_entity(context[0], entity_id)
            if (entity.identity.space_id, entity.identity.revision_id) != (space, at_revision):
                raise ValueError('Core entity read changed pinned authority')
            entities_by_revision[key] = entity
        return entities_by_revision[key]
    if authored_references is not None:
        for ref in object_selections(authored_references):
            if repo.get_revision(space, ref.graph_revision) is None:
                raise ValueError('Authored selection snapshot is unavailable')
            origin = (pinned if ref.graph_revision == revision_id else
                statements._context(repo, space, ref.graph_revision, None, 'gm', scope_mode='world'))
            selected = read_entity(ref.graph_revision, ref.node_id, origin)
            if not selected.found or selected.completeness.status != 'complete':
                raise ValueError('Authored entity is unavailable in its selection snapshot')
    result = SearchReadService().search_entities(pinned[0], question)
    if (result.identity.space_id, result.identity.revision_id) != (space, revision_id):
        raise ValueError('Core search changed query authority')
    gaps = [] if result.completeness.status == 'complete' else ['native_search_partial']
    discovered = tuple(hit.entity.entity_id for hit in result.hits)
    matches, assertion_matches, entity_gaps, _entities = _entity_catalog(discovered, pinned,
        space=space, revision_id=revision_id, scope_mode=scope_mode, campaign_id=campaign_id,
        read_entity=read_entity)
    gaps.extend(entity_gaps)
    targets = []
    if authored_references is not None:
        for ref in object_selections(authored_references):
            target_matches, target_assertions, target_gaps, entities = _entity_catalog(
                (ref.node_id,), pinned, space=space, revision_id=revision_id,
                scope_mode=scope_mode, campaign_id=campaign_id, read_entity=read_entity)
            entity = entities[ref.node_id]
            if not entity.found:
                target_gaps = ('native_authored_entity_unavailable',)
                status = 'unavailable'
                target_matches, target_assertions = (), ()
            else:
                status = 'partial' if target_gaps else 'complete'
            targets.append(NativeAuthoredTargetV1(node_id=ref.node_id, selection_revision_id=ref.graph_revision,
                matches=target_matches, assertion_matches=target_assertions,
                status=status, gap_codes=target_gaps))
            gaps.extend(target_gaps)
    objects = []
    for identity in discovered:
        entity = _entities[identity]
        names = {a.value.value.strip() for a in entity.assertions
            if a.subject_entity_id == identity and a.predicate == 'dnd5e:name'
            and getattr(a.value, 'kind', None) == 'literal'
            and isinstance(a.value.value, str) and a.value.value.strip()}
        objects.append(NativeObjectMatchV1(entity_id=identity,
            label=next(iter(names)) if len(names) == 1 else identity))
    query = NativeGraphQueryV4(authority=authority, question=question,
        assertion_matches=assertion_matches,
        search_result_sha256=result.result_digest, discovered_entity_ids=discovered,
        matches=tuple(matches), status='partial' if gaps else 'complete', gap_codes=tuple(sorted(set(gaps))),
        authored_targets=tuple(targets), object_matches=tuple(objects))
    if resolve(managed_world_id) != bound:
        raise ValueError('Active Graph binding changed during native query')
    return QueryContext(query, bound, pinned, repo, principal, resolve), query


def read_selected(context, authorization, principal):
    """Open support only for records in an exact APP-authorized query selection."""
    _require_gm(principal)
    query = context.query
    if (not isinstance(query, NativePlanQueryV1)
            or not isinstance(authorization, (NativePlanStatementReadAuthorizedV1, NativePlanAssertionReadAuthorizedV1))
            or authorization.query_sha256 != query.sha256):
        raise ValueError('Selected read requires its exact native query authorization')
    if isinstance(authorization, NativePlanAssertionReadAuthorizedV1):
        if not isinstance(query, NativePlanQueryV2):
            raise ValueError('Selected assertions require an assertion-capable native query')
        identities = authorization.assertion_ids
        discovered = {m.assertion_id for m in query.assertion_matches}
        reader = _read_assertions
    else:
        identities = authorization.statement_ids
        discovered = {m.statement_id for m in query.matches}
        reader = _read_statements
    if len(identities) != len(set(identities)) or not set(identities) <= discovered:
        raise ValueError('Selected record was not discovered by this query')
    authority = query.authority
    if context.resolve_binding(authority.managed_world_id) != context.binding:
        raise ValueError('Native query binding changed before selected read')
    result = reader(context, identities)
    if context.resolve_binding(authority.managed_world_id) != context.binding:
        raise ValueError('Native query binding changed during selected read')
    return result


@dataclass(frozen=True)
class AuthoredSupport:
    """Transient Core materialization; the existing APP owner admits the record."""
    query_sha256: str
    node_id: str
    statement_reads: tuple
    assertion_reads: tuple
    unavailable_statement_ids: tuple
    unavailable_assertion_ids: tuple
    status: str


def read_authored_reference(context, authorization, principal):
    """Use the same pinned support readers for an explicitly human-origin grant."""
    from application_state.agent_conversation.authored_graph_references import BuildAuthoredReferenceAuthorizedV2
    _require_gm(principal)
    query = context.query
    if (type(authorization) is not BuildAuthoredReferenceAuthorizedV2
            or not isinstance(query, NativeGraphQueryV3)
            or query.authority.scope_mode != 'world' or query.authority.campaign_id is not None
            or authorization.query_sha256 != query.sha256):
        raise ValueError('Authored read requires its exact native human-origin grant')
    target = next((target for target in query.authored_targets
        if target.node_id == authorization.node_id), None)
    if target is None:
        raise ValueError('Authored object was not requested by this native context')
    if context.resolve_binding(query.authority.managed_world_id) != context.binding:
        raise ValueError('Native query binding changed before authored read')
    statement_reads, unavailable_statements = _read_statements(context,
        tuple(match.statement_id for match in target.matches), matches=target.matches)
    assertion_reads, unavailable_assertions = _read_assertions(context,
        tuple(match.assertion_id for match in target.assertion_matches), matches=target.assertion_matches)
    if context.resolve_binding(query.authority.managed_world_id) != context.binding:
        raise ValueError('Native query binding changed during authored read')
    return AuthoredSupport(query_sha256=query.sha256, node_id=target.node_id,
        statement_reads=statement_reads, assertion_reads=assertion_reads,
        unavailable_statement_ids=unavailable_statements,
        unavailable_assertion_ids=unavailable_assertions,
        status='partial' if target.status != 'complete' or unavailable_statements or unavailable_assertions else 'complete')


def _read_statements(context, identities, *, matches=None):
    query, repo = context.query, context.repository
    authority = query.authority
    matches = {m.statement_id: m for m in (query.matches if matches is None else matches)}
    reads, unavailable = [], []
    for identity in identities:
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
    return tuple(reads), tuple(unavailable)


def _read_assertions(context, identities, *, matches=None):
    query = context.query
    authority = query.authority
    inventory = {m.assertion_id: m for m in (query.assertion_matches if matches is None else matches)}
    read_context, access, _, _ = context.pinned
    reads, unavailable = [], []
    for identity in identities:
        result = EvidenceReadService().get_assertion_evidence(read_context, identity)
        if (result.identity.space_id, result.identity.revision_id) != (authority.native_world_id, authority.revision_id):
            raise ValueError('Core assertion read changed pinned authority')
        if not result.available or result.completeness.status != 'complete' or result.assertion is None:
            unavailable.append(identity)
            continue
        assertion = assertion_contract(result.assertion)
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
            # A valid source/span proof can predate this coherent view. Core
            # owns membership and current access; proof age is not query authority.
            text = opened.body_text.encode()[opened.span_start_byte:opened.span_end_byte].decode()
            spans.append(NativeAssertionSpanV1(evidence_ref_id=ref.evidence_ref_id,
                source_artifact_id=opened.source_artifact_id, source_revision_id=opened.source_revision_id,
                body_sha256=opened.body_sha256, start_byte=opened.span_start_byte, end_byte=opened.span_end_byte,
                span_sha256=opened.span_sha256, text=text))
        if len(spans) != len(supports):
            unavailable.append(identity)
            continue
        reads.append(NativePlanAssertionReadV1(assertion=assertion, evidence=refs, spans=tuple(spans)))
    return tuple(reads), tuple(unavailable)


def reopen_context(query, principal):
    """Current access to a retained query's original R, without re-running search."""
    _require_gm(principal)
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
