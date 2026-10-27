"""Corpus navigation receipts; term matches never grant answer/Graph support."""
from __future__ import annotations

from hashlib import sha256
import re
from dataclasses import dataclass
from uuid import UUID
from . import types as t
from .source_writer_output import strict_json

POLICY = "registered_corpus_sections_v1"
SEARCH = "search_retained_source_sections"
GRAMMAR = frozenset("a an and are as at be before by do for from give how i in into is it its me my not of on or our read that the their them these this to use was we were what when where which who why with you your".split())


def terms(text):
    return sorted(set(re.findall(r"\w+", text.casefold())) - GRAMMAR)


def enabled(policy):
    return getattr(policy, 'corpus_source_policy', None) == POLICY


def action_handle(turn):
    # Navigation address only. The actual grant separately binds conversation,
    # turn, attempt, provider and context after the first decision claims them.
    return 'corpus-search:' + t.canonical_sha256({'world': turn.world_id, 'query': turn.user_text})



def view(event):
    data = strict_json(event.source_view_json)
    if (not isinstance(data, dict) or set(data) != {'schema', 'native_world_id',
            'scope', 'started_at', 'finished_at', 'snapshot_fingerprint', 'members', 'gaps'}
            or data['schema'] != 'dmb_corpus_source_view_v1'
            or data['scope'] != {'admissibility': 'gm', 'scope_mode': 'world_cross_campaign',
                                 'campaign_id': None, 'focus': {'kind': 'none', 'session_id': None}}
            or data['native_world_id'] != event.native_world_id
            or t.canonical_sha256(data) != event.source_view_sha256
            or not isinstance(data['gaps'], list) or not isinstance(data['members'], list)):
        raise ValueError('Corpus source view differs from its explicit frozen metadata')
    keys = []
    for row in data['members']:
        if not isinstance(row, dict) or set(row) != {'artifact', 'revision'}:
            raise ValueError('Corpus membership requires exact artifact/revision records')
        artifact, revision = row['artifact'], row['revision']
        if (artifact.get('schema_version') != 'dm_source_artifact_v2'
                or artifact.get('world_id') != event.native_world_id
                or artifact.get('status') != 'active' or artifact.get('visibility') not in {'gm', 'player'}
                or artifact.get('source_domain') not in {'session_recap', 'worldbuilding'}
                or not isinstance(artifact.get('source_artifact_id'), str)
                or not artifact['source_artifact_id'].strip()
                or revision.get('source_artifact_id') != artifact['source_artifact_id']
                or revision.get('schema_version') != 'dm_source_revision_v1'
                or not isinstance(revision.get('source_revision_id'), str)
                or not revision['source_revision_id'].strip()
                or not isinstance(revision.get('content_sha256'), str)
                or not re.fullmatch('[0-9a-f]{64}', revision['content_sha256'])):
            raise ValueError('Corpus member lacks active explicit source authority')
        keys.append((artifact['source_artifact_id'], revision['source_revision_id']))
    if keys != sorted(set(keys)):
        raise ValueError('Corpus membership must be sorted and unique')
    return data


@dataclass(frozen=True)
class SourceRevisionIdentity:
    """A registry address, deliberately without any Graph anchor/evidence fields."""
    source_artifact_id: str
    source_revision_id: str


def registry_origin(event):
    body = strict_json(event.origin_proof_json)
    if (not isinstance(body, dict) or set(body) != {'schema', 'search_event_id',
            'source_view_sha256', 'artifact', 'revision'}
            or body['schema'] != 'dmb_registry_source_origin_v1'
            or t.canonical_sha256(body) != event.origin_proof_sha256):
        raise ValueError('Registry source origin requires exact typed metadata')
    # Membership and scope are established against the earlier durable grant.
    identity = SourceRevisionIdentity(source_artifact_id=body['artifact'].get('source_artifact_id'),
        source_revision_id=body['revision'].get('source_revision_id'))
    UUID(body['search_event_id'])
    return body, None, identity


def validate_search_authorization(turn, event):
    authority = turn.graph_context_receipt.graph_authority
    if (not enabled(turn.graph_context_execution.policy)
            or event.world_id != turn.world_id or event.conversation_id != turn.conversation_id
            or event.turn_id != turn.turn_id or event.attempt != turn.attempt
            or event.native_world_id != authority.native_world_id
            or event.binding_version != authority.binding_version
            or event.query_sha256 != sha256(turn.user_text.encode()).hexdigest()
            or event.query_terms != terms(turn.user_text) or not event.query_terms
            or event.action_handle != action_handle(turn)):
        raise ValueError('Corpus search differs from its actual submission and bound scope')
    view(event)
    if isinstance(turn.graph_context_execution.policy, t.PlanJevRetrievalPolicyV1):
        from .plan_jev_decision import current_selection
        selected = current_selection(turn)
        if selected.operation != 'select_candidates' or event.action_handle not in selected.selected_handles:
            raise ValueError('Corpus scan was not selected by the current Plan decision')


def validate_events(execution):
    grants, catalogs, navs, completed = {}, {}, {}, set()
    provider, outcome, writer = None, None, False
    for event in execution.events:
        if isinstance(event, t.ProviderAttemptAuthorizedEventV1):
            if set(grants) != completed:
                raise ValueError('Provider cannot proceed with unresolved corpus search')
            provider, outcome = event.provider_attempt_id, None
            writer = isinstance(event, t.PlanJevWriterAuthorizedV1)
        elif isinstance(event, t.ProviderOutcomeEventV1) and event.provider_attempt_id == provider:
            outcome = event.outcome
        elif isinstance(event, t.CorpusSourceSearchAuthorizedV1):
            if (not enabled(execution.policy) or writer or outcome != 'response_received'
                    or provider != event.provider_attempt_id or event.search_id in grants
                    or grants or event.context_receipt_sha256 != execution.context_receipt_sha256
                    or event.execution_policy_sha256 != execution.execution_policy_sha256
                    or event.world_id != execution.policy.source_read_scope.world_id):
                raise ValueError('Corpus search lacks a unique acknowledged capability')
            view(event)
            grants[event.search_id] = event
        elif isinstance(event, t.NativeSourceNavigationAuthorizedV2):
            body, _, _ = registry_origin(event)
            grant = next((g for g in grants.values() if str(g.event_id) == body['search_event_id']), None)
            if (grant is None or grant.search_id in completed or provider != grant.provider_attempt_id
                    or outcome != 'response_received' or body['source_view_sha256'] != grant.source_view_sha256
                    or {'artifact': body['artifact'], 'revision': body['revision']} not in view(grant)['members']
                    or event.world_id != grant.world_id or event.native_world_id != grant.native_world_id
                    or event.binding_version != grant.binding_version):
                raise ValueError('Registry navigation lacks exact earlier corpus membership')
            navs[event.navigation_id] = (event, grant)
        elif isinstance(event, t.NativeSourceCatalogObservedV1):
            catalogs[event.event_id] = event
        elif isinstance(event, t.CorpusSourceSearchObservedV1):
            grant = grants.get(event.search_id)
            if (grant is None or event.search_id in completed or provider != grant.provider_attempt_id
                    or outcome != 'response_received' or event.source_view_sha256 != grant.source_view_sha256
                    or event.query_sha256 != grant.query_sha256):
                raise ValueError('Corpus result differs from its exact search grant')
            expected = set(event.catalog_event_ids)
            if len(event.catalog_event_ids) != len(expected):
                raise ValueError('Corpus result repeats catalog identities')
            membership = {(r['artifact']['source_artifact_id'], r['revision']['source_revision_id'],
                           r['revision']['content_sha256']) for r in view(grant)['members']}
            source_keys = []
            for identity in expected:
                catalog = catalogs.get(identity)
                key = ((catalog.source_artifact_id, catalog.native_source_revision_id, catalog.content_sha256)
                       if catalog is not None else None)
                if key not in membership:
                    raise ValueError('Corpus result catalog is outside exact frozen membership')
                source_keys.append(key)
            if len(set(source_keys)) != len(source_keys):
                raise ValueError('Corpus result repeats a source revision')
            acquired = {e.event_id for e in catalogs.values() if e.navigation_id in navs
                        and navs[e.navigation_id][1] == grant}
            if not acquired <= expected:
                raise ValueError('Corpus result omits an acquired registry catalog')
            seen = set()
            for hit in event.matches:
                catalog = catalogs.get(hit.catalog_event_id)
                key = (hit.catalog_event_id, hit.section_id)
                if (catalog is None or catalog.outcome != 'complete' or key in seen
                        or hit.section_id not in {s.section_id for s in catalog.sections}
                        or not hit.matched_terms or hit.matched_terms != sorted(set(hit.matched_terms))
                        or not set(hit.matched_terms) <= set(grant.query_terms)):
                    raise ValueError('Corpus match is not navigation over an acquired exact section')
                seen.add(key)
            complete = (event.failure_code is None and not view(grant)['gaps'] and len(expected) == len(view(grant)['members'])
                        and all(catalogs[k].outcome == 'complete' for k in expected))
            if event.coverage != ('enumerated_membership_scanned' if complete else 'partial'):
                raise ValueError('Corpus coverage must retain known gaps; it is never global completeness')
            completed.add(event.search_id)


def validate_receipt(receipt, execution):
    if execution is None:
        return
    grants = [e for e in execution.events if isinstance(e, t.CorpusSourceSearchAuthorizedV1)]
    if not grants:
        return
    if not isinstance(receipt, (t.PlanWorldGraphContextReceiptV1, t.PlayWorldGraphContextReceiptV1)):
        raise ValueError('Corpus search requires its frozen Plan or native Play receipt')
    authority = receipt.graph_authority
    for event in grants:
        if (
                event.world_id != authority.managed_world_id
                or event.native_world_id != authority.native_world_id
                or event.binding_version != authority.binding_version
                or event.context_receipt_sha256 != receipt.context_receipt_sha256):
            raise ValueError('Corpus search differs from managed/native context receipt')
