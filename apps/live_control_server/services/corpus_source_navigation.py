"""One explicitly selected corpus scan; no prose is added to model context."""
from hashlib import sha256
from types import SimpleNamespace
from uuid import uuid4
from application_state.agent_conversation import types as t
from application_state.agent_conversation.corpus_source_search import action_handle, enabled, terms, SourceRevisionIdentity
from application_state.agent_conversation.jev_retrieval_contract import RetrievalCandidate
from application_state.source.naming import registered_source_name
from dungeonmind.domain.canonical import canonical_json
from ..integrations.dungeonmind.world_graph_reads import direct_services_from_config
from ..integrations.dungeonmind.corpus_source_inventory import collect_source_view, verify_registry_source_origin


class CorpusSourceNavigation:
    def __init__(self, owner):
        self.owner = owner
        self.attempted = False
        self.observation = None
        self.members = {}

    def offered(self):
        adapter = self.owner.adapter
        if adapter.fence is None:
            # Plan's first catalog precedes its durable claim. This address is
            # navigation only; the selected action must still pass the actual
            # frozen capability/submission guard after authorization.
            if adapter.request.surface.surface_id != 'plan':
                return ()
            turn = SimpleNamespace(world_id=adapter.world_id, user_text=adapter.request.message)
        else:
            turn = adapter.fence.turn
            if not enabled(turn.graph_context_execution.policy):
                return ()
        if self.attempted or not terms(turn.user_text):
            return ()
        return (RetrievalCandidate(handle=action_handle(turn),
            label='Search retained source sections for the current request',
            kind='Corpus lexical navigation, independent of Graph connections; matches are not evidence'),)

    def examined(self):
        if not self.attempted:
            return ()
        turn = self.owner.adapter.fence.turn
        status = self.observation.coverage if self.observation is not None else 'unavailable'
        return (RetrievalCandidate(handle=action_handle(turn), label='Retained source search',
            kind=status + '; coverage of enumerated membership only, not global or semantic completeness'),)

    def revision_metadata(self, handle):
        member = self.members.get(handle)
        if member is None:
            return None
        current = member['artifact'].get('current_revision_id')
        revision = member['revision']
        return {'status_at_capture': ('unknown' if current is None else
                'current' if current == revision['source_revision_id'] else 'historical'),
            'recorded_at': revision['created_at'],
            'campaign_id': member['artifact'].get('campaign_id'),
            'session_id': member['artifact'].get('session_id')}

    def access(self, handle):
        grant, identity, _ = self.owner.sources[handle]
        member = self.members[handle]
        authority = self.owner._bound_authority()
        proof = {'schema': 'dmb_registry_source_origin_v1', 'search_event_id': str(grant.event_id),
            'source_view_sha256': grant.source_view_sha256,
            'artifact': member['artifact'], 'revision': member['revision']}
        return verify_registry_source_origin(direct_services_from_config(authority.native_world_id),
            native_world_id=authority.native_world_id, proof=proof)

    def search(self, *, plan=False):
        owner, a = self.owner, self.owner.adapter
        turn = a.fence.turn
        handle = action_handle(turn)
        if not enabled(turn.graph_context_execution.policy) or not terms(turn.user_text):
            raise ValueError('corpus_search_unavailable')
        if plan:
            owner._plan_selection([handle])
        if self.attempted:
            if self.observation is None:
                raise ValueError('corpus_search_unavailable')
            owner._bound_authority()
            return {'schema': 'dmb_corpus_source_search_result_v1',
                'coverage': self.observation.coverage, 'global_completeness': 'not_established',
                'reused_search': True, 'sections': [],
                'reused_section_handles': ['native-section:' + hit.section_id for hit in self.observation.matches]}
        self.attempted = True  # consume before any IO; no automatic retry
        authority = owner._bound_authority()
        source_view = collect_source_view(direct_services_from_config(authority.native_world_id),
            native_world_id=authority.native_world_id)
        with a.fence.renewer._lock:
            turn = a.fence.renewer._turn
            execution = turn.graph_context_execution
            provider = next(e for e in reversed(execution.events) if isinstance(e, t.ProviderAttemptAuthorizedEventV1))
            grant = t.CorpusSourceSearchAuthorizedV1(kind='corpus_source_search_authorized_v1',
                event_id=uuid4(), sequence=len(execution.events), search_id=uuid4(),
                provider_attempt_id=provider.provider_attempt_id,
                context_receipt_sha256=execution.context_receipt_sha256,
                execution_policy_sha256=execution.execution_policy_sha256,
                world_id=turn.world_id, native_world_id=authority.native_world_id,
                binding_version=authority.binding_version, conversation_id=turn.conversation_id,
                turn_id=turn.turn_id, attempt=turn.attempt, action_handle=handle,
                query_sha256=sha256(turn.user_text.encode()).hexdigest(), query_terms=terms(turn.user_text),
                source_view_json=canonical_json(source_view), source_view_sha256=t.canonical_sha256(source_view))
            owner._commit('authorize_corpus_source_search', authorization=grant)
        matches, catalogs, failed = [], [], False
        from .native_source_navigation import section_query_terms
        from application_state.errors import ApplicationStateValidationError
        for member in source_view['members']:
            artifact, revision = member['artifact'], member['revision']
            key = (artifact['source_artifact_id'], revision['source_revision_id'])
            existing = next((h for h, e in owner.sources.items()
                if (e[1].source_artifact_id, e[1].source_revision_id) == key), None)
            source_handle = existing or ('corpus-source:' + t.canonical_sha256(
                {'search': str(grant.event_id), 'artifact': key[0], 'revision': key[1]}))
            if existing is None:
                name = registered_source_name(artifact)
                if name is None:
                    failed = True
                    continue
                owner.sources[source_handle] = (grant, SourceRevisionIdentity(
                    source_artifact_id=key[0], source_revision_id=key[1]), name.strip())
                self.members[source_handle] = member
            self.members[source_handle] = member
            prior_sections = set(owner.sections)
            try:
                owner.browse(source_handle)
                catalog = owner.catalogs[source_handle]
                catalogs.append(catalog.event_id)
                material = owner.materials.get(catalog.event_id)
                if material is None:
                    failed = True
                    continue
                hits = section_query_terms(material.markdown, catalog.sections, turn.user_text)
                for section in catalog.sections:
                    section_handle = 'native-section:' + section.section_id
                    if hits[section.section_id]:
                        matches.append(t.CorpusSourceSectionMatchV1(catalog_event_id=catalog.event_id,
                            section_id=section.section_id, matched_terms=hits[section.section_id]))
                    elif section_handle not in prior_sections:
                        owner.sections.pop(section_handle, None)
                        owner.query_matches.pop(section_handle, None)
            except (ValueError, ApplicationStateValidationError):
                failed = True
                catalog = owner.catalogs.get(source_handle)
                if catalog is not None and catalog.event_id not in catalogs:
                    catalogs.append(catalog.event_id)
                owner.unavailable('corpus_source_unavailable')
            finally:
                # Do not retain whole-corpus host material. Graph-origin cache
                # behavior remains unchanged; registry selections reacquire
                # exact bytes at the existing APP reader boundary.
                catalog = owner.catalogs.get(source_handle)
                if isinstance(owner.sources[source_handle][0], t.CorpusSourceSearchAuthorizedV1) and catalog is not None:
                    owner.materials.pop(catalog.event_id, None)
        turn = a.fence.renewer._turn
        event = t.CorpusSourceSearchObservedV1(kind='corpus_source_search_observed_v1',
            event_id=uuid4(), sequence=len(turn.graph_context_execution.events), search_id=grant.search_id,
            query_sha256=grant.query_sha256, source_view_sha256=grant.source_view_sha256,
            catalog_event_ids=catalogs, matches=matches,
            coverage=('partial' if failed or source_view['gaps'] or len(catalogs) != len(source_view['members'])
                      else 'enumerated_membership_scanned'),
            failure_code='corpus_source_unavailable' if failed else None)
        owner._commit('record_corpus_source_search', observation=event)
        self.observation = event
        return {'schema': 'dmb_corpus_source_search_result_v1', 'coverage': event.coverage,
            'global_completeness': 'not_established', 'sections': [
                {'section_handle': 'native-section:' + hit.section_id,
                 'source_name': owner.catalog_names[next(h for h, c in owner.catalogs.items() if c.event_id == hit.catalog_event_id)],
                 'title': next(s.label for c in owner.catalogs.values() if c.event_id == hit.catalog_event_id
                               for s in c.sections if s.section_id == hit.section_id),
                 'matched_query_terms': hit.matched_terms,
                 'source_revision': self.revision_metadata(next(h for h,c in owner.catalogs.items() if c.event_id == hit.catalog_event_id))} for hit in matches]}
