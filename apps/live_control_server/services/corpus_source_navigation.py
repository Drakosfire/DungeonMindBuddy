"""One explicitly selected corpus scan; no prose is added to model context."""
from hashlib import sha256
from contextlib import nullcontext
from collections import Counter
from types import SimpleNamespace
from uuid import uuid4
from application_state.agent_conversation import types as t
from application_state.agent_conversation.corpus_source_search import action_handle, enabled, terms, SourceRevisionIdentity
from application_state.agent_conversation.jev_retrieval_contract import RetrievalCandidate
from application_state.source.naming import registered_source_name
from .native_source_display import source_display_name
from dungeonmind.domain.canonical import canonical_json
from ..integrations.dungeonmind.world_graph_reads import direct_services_from_config
from ..integrations.dungeonmind.corpus_source_inventory import collect_source_view, verify_registry_source_origin


class CorpusSourceNavigation:
    def __init__(self, owner):
        self.owner = owner
        self.attempted = False
        self.observation = None
        self.members = {}

    def hydrate(self):
        """Recover navigation from this execution's durable receipts, without source IO."""
        owner = self.owner
        execution = owner.adapter.fence.turn.graph_context_execution
        if not enabled(execution.policy):
            return
        grant = next((e for e in execution.events if isinstance(e, t.CorpusSourceSearchAuthorizedV1)), None)
        if grant is None:
            return
        observation = next((e for e in execution.events if isinstance(e, t.CorpusSourceSearchObservedV1)
                            and e.search_id == grant.search_id), None)
        self.attempted = True
        if observation is None or self.observation is not None:
            return
        from application_state.agent_conversation.corpus_source_search import view, registry_origin
        members = {(m['artifact']['source_artifact_id'], m['revision']['source_revision_id']): m
                   for m in view(grant)['members']}
        navs = {e.navigation_id: e for e in execution.events
                if isinstance(e, t.NativeSourceNavigationAuthorizedV1)}
        for catalog in execution.events:
            if not isinstance(catalog, t.NativeSourceCatalogObservedV1) or catalog.event_id not in observation.catalog_event_ids:
                continue
            key = (catalog.source_artifact_id, catalog.native_source_revision_id)
            member = members[key]
            nav = navs[catalog.navigation_id]
            if isinstance(nav, t.NativeSourceNavigationAuthorizedV2):
                body, _, identity = registry_origin(nav)
                if body['search_event_id'] != str(grant.event_id):
                    raise ValueError('Recovered catalog differs from its corpus grant')
                handle = 'corpus-source:' + t.canonical_sha256(
                    {'search': str(grant.event_id), 'artifact': key[0], 'revision': key[1]})
                name = registered_source_name(member['artifact'])
                owner.sources[handle] = (grant, identity, name.strip())
            else:
                handle = next(h for h, e in owner.sources.items()
                              if (e[1].source_artifact_id, e[1].source_revision_id) == key)
                name = owner.sources[handle][2]
            self.members[handle] = member
            owner.catalogs[handle] = catalog
            owner.catalog_names[handle] = name.strip()
            owner.attempted_sources.add(handle)
            hits = {h.section_id: h.matched_terms for h in observation.matches
                    if h.catalog_event_id == catalog.event_id}
            frequency = Counter(term for matched in hits.values() for term in matched)
            for section in catalog.sections:
                if section.section_id in hits:
                    address = 'native-section:' + section.section_id
                    owner.sections[address] = (handle, section, name.strip())
                    owner.query_matches[address] = sorted(hits[section.section_id],
                        key=lambda term: (frequency[term], term))
            for event in execution.events:
                if isinstance(event, t.NativeSourceSectionAuthorizedV1) and event.catalog_event_id == catalog.event_id:
                    owner.attempted_sections.add('native-section:' + event.section.section_id)
                if isinstance(event, t.NativeSourceSectionObservedV1) and event.catalog_event_id == catalog.event_id:
                    owner.reads['native-section:' + event.section.section_id] = event
        self.observation = observation

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
                            section_id=section.section_id, matched_terms=sorted(hits[section.section_id])))
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
                 'matched_query_terms': owner.query_matches['native-section:' + hit.section_id],
                 'source_revision': self.revision_metadata(next(h for h,c in owner.catalogs.items() if c.event_id == hit.catalog_event_id))} for hit in matches]}


class NativeBodyNavigation:
    """Native-only Plan navigation; no classic registry dispatch or body cache."""
    def __init__(self, adapter):
        from application_state.agent_conversation.native_corpus import NativeCorpusAuthorityV1
        from ..integrations.dungeonmind.native_corpus_source import NativeCorpusContext
        authority = (adapter.fence.turn.graph_context_receipt.source_authority
            if adapter.fence is not None else adapter.native_source_authority)
        context = getattr(adapter, "native_corpus_context", None)
        if isinstance(authority, NativeCorpusAuthorityV1) and (
                not isinstance(context, NativeCorpusContext) or context.authority != authority):
            raise ValueError("Native navigation requires its original trusted source context")
        self.adapter = adapter
        self._source_display = None
        self._direct_sources = None

    def _source_choices(self):
        # Existing Core catalogue is metadata only. Source bodies require the
        # later explicit, durable controller selection and refreshed Core read.
        if self._source_display is None:
            from dungeonmind.application.vnext import list_admitted_native_text_sources
            from application_state.agent_conversation.native_corpus import native_direct_source_handle
            from .native_source_display import source_display_metadata
            context = self.adapter.native_corpus_context
            items = list_admitted_native_text_sources(context.access).sources
            labels = source_display_metadata(items, context.authority.managed_world_id)
            self._source_display, self._direct_sources = {}, {}
            for item, label in zip(items, labels):
                pair = (item.source_artifact.source_artifact_id, item.source_revision.source_revision_id)
                self._source_display[pair] = label
                handle = native_direct_source_handle(context.authority, *pair, item.source_revision.content_sha256)
                self._direct_sources[handle] = (pair, item.source_revision.content_sha256, label)
        return self._direct_sources

    def _source_name(self, catalog):
        self._source_choices()
        source = catalog.source
        display = self._source_display.get((source.artifact.source_artifact_id, source.revision.source_revision_id))
        return source_display_name(display, catalog.sections[0].label)

    def _read_label(self, catalog, section_id=None):
        name = self._source_name(catalog)
        if section_id is None:
            return name
        section = next(row for row in catalog.sections if row.section_id == section_id)
        return f"{name} · {section.label} · lines {section.line_start}–{section.line_end}"

    def _events(self, turn=None):
        from application_state.agent_conversation.native_corpus import (
            NativeBodySearchAuthorizedV1, NativeBodySearchObservedV1,
            NativeBodyReadAuthorizedV1, NativeBodyReadObservedV1, NativeDirectSourceAuthorizedV1,
        )
        events = (turn if turn is not None else self.adapter.fence.turn).graph_context_execution.events
        grant = next((e for e in events if isinstance(e, NativeBodySearchAuthorizedV1)), None)
        search = next((e for e in events if isinstance(e, NativeBodySearchObservedV1)), None)
        auths = [e for e in events if isinstance(e, (NativeBodyReadAuthorizedV1, NativeDirectSourceAuthorizedV1))]
        reads = {e.authorization_event_id: e for e in events if isinstance(e, NativeBodyReadObservedV1)}
        return grant, search, auths, reads

    @staticmethod
    def _handle(auth):
        from application_state.agent_conversation.native_corpus import (
            native_body_handle, native_full_document_handle, NativeDirectSourceAuthorizedV1, native_direct_source_handle)
        if isinstance(auth, NativeDirectSourceAuthorizedV1):
            return native_direct_source_handle(auth.authority, auth.source_artifact_id,
                auth.source_revision_id, auth.content_sha256)
        return (native_full_document_handle(auth.catalog_sha256) if auth.retrieval_kind == "full_document"
            else native_body_handle(auth.catalog_sha256, auth.section_id))

    def _acquired_extents(self):
        from application_state.agent_conversation.native_corpus import acquired_body_reads, acquired_body_catalogs
        execution = self.adapter.fence.turn.graph_context_execution
        catalogs = acquired_body_catalogs(execution)
        return tuple((read, catalogs[read.excerpt.catalog_sha256]) for read in acquired_body_reads(execution))

    def _keyword_catalog(self):
        from application_state.agent_conversation.native_retrieval import scope_digest
        from application_state.agent_conversation.native_source_keywords import keyword_catalog
        turn = self.adapter.fence.turn
        return keyword_catalog(turn.user_text, scope_digest(turn))

    def _keyword_offers(self):
        from application_state.agent_conversation.native_retrieval import NativeRetrievalSelectedV1
        from application_state.agent_conversation.native_source_keywords import KEYWORD_KIND
        turn = self.adapter.fence.turn
        if (type(turn.graph_context_receipt) is not t.SurfaceNativeContextReceiptV1 or
                any(type(e) is NativeRetrievalSelectedV1 for e in turn.graph_context_execution.events) or
                self._acquired_extents()):
            return ()
        return tuple(RetrievalCandidate(handle=handle, label=repr(word), kind=KEYWORD_KIND)
            for handle, word in self._keyword_catalog().items())

    def _selected_keywords(self):
        from application_state.agent_conversation.native_source_keywords import acknowledged_keyword_catalog
        return set(acknowledged_keyword_catalog(self.adapter.fence.turn).values())

    def accept_keyword_selection(self, handle, *, parent):
        if handle not in self._keyword_catalog():
            raise ValueError('Native keyword belongs to another query or frozen scope')
        self._require_metadata_selection(handle, parent=parent)

    def expansion_handle(self):
        from application_state.agent_conversation.native_retrieval import scope_digest
        turn = self.adapter.fence.turn
        return 'native-corpus-expand:' + t.canonical_sha256({
            'scope': scope_digest(turn), 'query': sha256(turn.user_text.encode()).hexdigest()})

    def _expanded(self):
        from application_state.agent_conversation.native_retrieval import NativeRetrievalSelectedV1
        handle = self.expansion_handle()
        return any(type(event) is NativeRetrievalSelectedV1 and
            event.operation == 'select_candidates' and handle in event.selected_handles
            for event in self.adapter.fence.turn.graph_context_execution.events)

    def _scoped_offers(self, rows, search):
        turn = self.adapter.fence.turn
        if type(turn.graph_context_receipt) is not t.SurfaceNativeContextReceiptV1:
            return tuple(rows)
        from .native_source_candidate_scope import preferred_source_pairs
        self._source_choices()
        from application_state.agent_conversation.native_corpus import NativeAuthoredSourceReadV1
        references = set()
        if search is None:
            references = {(read.catalog.source.artifact.source_artifact_id, read.catalog.source.revision.source_revision_id)
                for read in turn.graph_context_execution.events if isinstance(read, NativeAuthoredSourceReadV1)}
        pairs = preferred_source_pairs(turn.user_text, self._source_display, opened_reference_pairs=references)
        keywords = self._selected_keywords() if search is not None else set()
        # An unfiltered catalogue is presentation, not an acknowledged action.
        # Require execution ownership only when a hint can actually affect it.
        if pairs is None and not keywords:
            return tuple(rows)
        if self._expanded():
            return tuple(rows)
        addresses = {handle: pair for handle, (pair, _, _) in self._direct_sources.items()}
        if search is not None:
            from application_state.agent_conversation.native_corpus import native_body_handle, native_full_document_handle
            for catalog in search.catalogs:
                pair = (catalog.source.artifact.source_artifact_id, catalog.source.revision.source_revision_id)
                addresses[native_full_document_handle(catalog.catalog_sha256)] = pair
                addresses.update((native_body_handle(catalog.catalog_sha256, section.section_id), pair)
                    for section in catalog.sections)
        known = set(self._source_display)
        narrowed = [row for row in rows if pairs is None or row.handle not in addresses or
            addresses[row.handle] not in known or addresses[row.handle] in pairs]
        if search is not None:
            from application_state.agent_conversation.native_corpus import native_body_handle
            hits = {native_body_handle(hit.catalog_sha256, hit.section_id): set(hit.matched_terms)
                for hit in search.matches}
            # A positive hit can prioritize known sections. Unknown metadata and
            # all full-document/Graph/Rules choices remain reachable. No literal
            # match is not semantic absence, so retain the current view then.
            if keywords and any(keywords & hits.get(row.handle, set()) for row in narrowed):
                narrowed = [row for row in narrowed if row.handle not in hits or keywords & hits[row.handle]]
        if len(narrowed) != len(rows):
            narrowed.append(RetrievalCandidate(handle=self.expansion_handle(),
                label='Search beyond the selected-reference, campaign/session and keyword hints in this request',
                kind='Expand to all other admitted native sources and matching sections; no source text is read by this choice'))
        return tuple(narrowed)

    def _require_metadata_selection(self, handle, *, parent):
        from application_state.agent_conversation.plan_jev_decision import current_selection
        selection = current_selection(self.adapter.fence.turn)
        if (selection.operation != 'select_candidates'
                or handle not in selection.selected_handles
                or parent.request_id != selection.decision_request_id
                or parent.digest != selection.parent_request_sha256
                or handle not in {row.handle for row in parent.candidates}):
            raise ValueError('Native navigation lacks its exact acknowledged parent selection')

    def expand_selected(self, handle, *, parent):
        if handle != self.expansion_handle():
            raise ValueError('Native corpus expansion belongs to another query or frozen scope')
        self._require_metadata_selection(handle, parent=parent)
        # The admitted event already reconstructs the broad view. No grant,
        # source read, Graph operation, or extra state transition is needed.

    def offered(self):
        from application_state.agent_conversation.native_corpus import (
            NativeCorpusAuthorityV1, native_corpus_search_handle, native_body_handle, native_full_document_handle,
        )
        if self.adapter.fence is None:
            if not isinstance(self.adapter.native_source_authority,NativeCorpusAuthorityV1):
                return ()
            # Pre-claim offers are Core metadata only; actual reads still require
            # the acknowledged native decision under the accepted Turn claim.
            rows=[RetrievalCandidate(handle=handle,
                label='Read full document: '+source_display_name(display,'Admitted source'),
                kind='Explicit admitted full-source read; metadata choice, not evidence')
                for handle,(_pair,_digest,display) in self._source_choices().items()]
            rows.append(RetrievalCandidate(handle=native_corpus_search_handle(
                sha256(self.adapter.request.message.encode()).hexdigest()),
                label='Search admitted native source sections for the current question',
                kind='Source lexical navigation; not evidence or semantic completeness'))
            return tuple(rows)
        turn = self.adapter.fence.turn
        if not isinstance(turn.graph_context_receipt.source_authority, NativeCorpusAuthorityV1):
            return ()
        grant, search, auths, reads = self._events()
        if any(auth.event_id not in reads for auth in auths):
            raise ValueError("Native source read has an unresolved durable grant")
        if grant is not None and search is None:
            raise ValueError("Native source search has an unresolved durable grant")
        attempted = {self._handle(auth) for auth in auths}
        acquired = self._acquired_extents()
        opened_pairs = {(catalog.source.artifact.source_artifact_id, catalog.source.revision.source_revision_id)
                        for read, catalog in acquired if read.excerpt.selector_policy == 'native_full_document_v1'}
        rows = []
        direct = self._source_choices() if type(turn.graph_context_receipt) is t.SurfaceNativeContextReceiptV1 else {}
        for handle, (pair, digest, display) in direct.items():
            if handle not in attempted and pair not in opened_pairs:
                rows.append(RetrievalCandidate(handle=handle,
                    label='Read full document: ' + source_display_name(display, 'Admitted source'),
                    kind='Explicit admitted full-source read; metadata choice, not evidence'))
        if grant is None:
            rows.append(RetrievalCandidate(handle=native_corpus_search_handle(sha256(turn.user_text.encode()).hexdigest()),
                label="Search admitted native source sections for the current question",
                kind="Source lexical navigation; not evidence or semantic completeness"))
            rows.extend(self._keyword_offers())
            return self._scoped_offers(rows, search)
        def opened(catalog, start, end):
            return any((known.source.artifact.source_artifact_id, known.source.revision.source_revision_id,
                            known.source.revision.content_sha256) == (catalog.source.artifact.source_artifact_id,
                            catalog.source.revision.source_revision_id, catalog.source.revision.content_sha256)
                and read.excerpt.section.byte_start <= start and read.excerpt.section.byte_end >= end
                for read, known in acquired)
        hits = {(row.catalog_sha256, row.section_id): row.matched_terms for row in search.matches}
        direct_pairs = {pair for pair, _, _ in direct.values()}
        for catalog in search.catalogs:
            name = self._source_name(catalog)
            matched = [row for row in catalog.sections if (catalog.catalog_sha256, row.section_id) in hits]
            for section in matched:
                # A degenerate one-section document offers only its explicit
                # full-document action, never an implicit whole-body section.
                if section.byte_start == 0 and section.byte_end == catalog.body_bytes:
                    continue
                handle = native_body_handle(catalog.catalog_sha256, section.section_id)
                if handle not in attempted and not opened(catalog, section.byte_start, section.byte_end):
                    rows.append(RetrievalCandidate(handle=handle,
                        label=name + " · " + section.label + " · matched terms: " + ", ".join(hits[(catalog.catalog_sha256, section.section_id)]),
                        kind="Exact source section"))
            handle = native_full_document_handle(catalog.catalog_sha256)
            pair = (catalog.source.artifact.source_artifact_id, catalog.source.revision.source_revision_id)
            if pair not in direct_pairs and matched and handle not in attempted and not opened(catalog, 0, catalog.body_bytes):
                terms = sorted({term for section in matched
                                for term in hits[(catalog.catalog_sha256, section.section_id)]})
                rows.append(RetrievalCandidate(handle=handle,
                    label="Read full document: " + name + " · matched terms: " + ", ".join(terms),
                    kind="Explicit full-document read"))
        return self._scoped_offers(rows, search)

    def examined(self):
        from application_state.agent_conversation.native_corpus import NativeCorpusAuthorityV1, native_corpus_search_handle
        if self.adapter.fence is None:
            return ()
        turn = self.adapter.fence.turn
        authority = turn.graph_context_receipt.source_authority
        if not isinstance(authority, NativeCorpusAuthorityV1):
            return (RetrievalCandidate(handle="native-source-unavailable:" + authority.failure_code,
                label="Native source inspection unavailable", kind=authority.failure_code + "; not evidence of absence"),)
        grant, search, auths, reads = self._events()
        rows = []
        if grant is not None:
            rows.append(RetrievalCandidate(handle=native_corpus_search_handle(grant.query_sha256),
                label="Admitted native source search", kind=(
                    f"Navigation scan: {len(search.catalogs)} accessible revisions, {search.unavailable_source_count} unavailable; semantic/global completeness not established"
                    if search is not None else "Unresolved source search")))
        from application_state.agent_conversation.native_corpus import (
            NativeAuthoredSourceReadV1, native_body_handle, native_full_document_handle,
        )
        for read, catalog in self._acquired_extents():
            excerpt = read.excerpt
            full = excerpt.section.byte_start == 0 and excerpt.section.byte_end == catalog.body_bytes
            handle = (native_full_document_handle(catalog.catalog_sha256) if full
                else native_body_handle(catalog.catalog_sha256, excerpt.section.section_id))
            rows.append(RetrievalCandidate(handle=handle,
                label=self._source_name(catalog) + " · " + excerpt.section.label
                    + f" · lines {excerpt.section.line_start}–{excerpt.section.line_end}",
                kind=("Acquired user-selected source text; mandatory writer input" if isinstance(read, NativeAuthoredSourceReadV1)
                    else "Acquired exact source text") + "; not an answer-sufficiency verdict"))
        for auth in auths:
            read = reads.get(auth.event_id)
            if read is None or read.excerpt is None:
                rows.append(RetrievalCandidate(handle=self._handle(auth), label="Previously selected native source extent",
                    kind="Unavailable source read" if read is not None else "Unresolved source read"))
        if type(turn.graph_context_receipt) is t.SurfaceNativeContextReceiptV1:
            from application_state.agent_conversation.native_source_keywords import retained_keyword_candidates
            focus = retained_keyword_candidates(turn)
            if focus and self._expanded():
                rows.extend(focus)
        return tuple(rows)

    def _commit(self, method, **fields):
        a = self.adapter
        trace = getattr(a, "trace", None)
        if trace is not None:
            for name in ("read", "capture"):
                materialize = fields.get(name)
                if callable(materialize):
                    def measured(*args, _materialize=materialize, **kwargs):
                        with trace.measure_host_work("native_source_materialization"):
                            return _materialize(*args, **kwargs)
                    fields[name] = measured
        turn = a.fence.renewer._turn
        with trace.measure_host_work("native_source_append") if trace is not None else nullcontext():
            result = getattr(a.service, method)(turn.world_id, turn.conversation_id, turn.turn_id,
                expected_revision=turn.revision, expected_attempt=turn.attempt, **fields)
        a.fence.renewer._turn = a.turn = result[0]
        if method == 'authorize_native_direct_sources':
            by_id = {event.event_id: event for event in result[0].graph_context_execution.events}
            return tuple(by_id[row['event_id']] for row in fields['grants'])
        return result[0].graph_context_execution.events[-1]

    def _fulfilled_in_current_selection(self, handle):
        """A prior read in this acknowledged batch may cover a selected section.

        The controller can select a full document and one of its sections at
        once. Do not reopen the section or label its already acquired text as
        unavailable. Prior decisions and merely similar sources cannot satisfy it.
        """
        if not handle.startswith('native-body:'):
            return False
        from application_state.agent_conversation.plan_jev_decision import current_selection
        selection = current_selection(self.adapter.fence.turn)
        if selection.operation != 'select_candidates' or handle not in selection.selected_handles:
            return False
        _, search, _, _ = self._events()
        if search is None:
            return False
        catalog = next((c for c in search.catalogs for section in c.sections
            if handle == 'native-body:' + c.catalog_sha256 + ':' + section.section_id), None)
        if catalog is None:
            return False
        section = next(s for s in catalog.sections if handle.endswith(':' + s.section_id))
        def identity(catalog):
            return (catalog.source.artifact.source_artifact_id,
                catalog.source.revision.source_revision_id, catalog.source.revision.content_sha256)
        return any(read.sequence > selection.sequence and identity(known) == identity(catalog)
            and read.excerpt.section.byte_start <= section.byte_start
            and read.excerpt.section.byte_end >= section.byte_end
            for read, known in self._acquired_extents())

    def select(self, handles):
        from application_state.agent_conversation.native_corpus import native_corpus_search_handle
        from ..integrations.dungeonmind.native_corpus_source import (
            NativeCorpusContext, capture_native_sources, read_native_corpus_member, read_direct_native_source,
        )
        a = self.adapter
        context = getattr(a, "native_corpus_context", None)
        if not isinstance(context, NativeCorpusContext) or context.authority != a.fence.turn.graph_context_receipt.source_authority:
            raise ValueError("Native navigation requires its original trusted source context")
        offered = {row.handle for row in self.offered()}
        if (not handles or len(set(handles)) != len(handles)
                or any(handle not in offered and not self._fulfilled_in_current_selection(handle) for handle in handles)):
            raise ValueError("Native source selection differs from its offered current catalog")
        from .native_retrieval_activity import observe_native_retrieval
        pending_direct = {}
        for index, handle in enumerate(handles):
            if handle not in offered or self._fulfilled_in_current_selection(handle):
                continue  # Its exact text was already read in this selected batch.
            with a.fence.renewer._lock:
                turn = a.fence.renewer._turn
                is_search = handle == native_corpus_search_handle(sha256(turn.user_text.encode()).hexdigest())
                is_direct = handle.startswith('native-direct-source:')
                if is_direct:
                    choices = self._source_choices()
                    if handle not in pending_direct:
                        group = []
                        for selected_handle in handles[index:]:
                            if not selected_handle.startswith('native-direct-source:'):
                                break
                            pair, digest, _ = choices[selected_handle]
                            group.append((selected_handle, dict(event_id=uuid4(),
                                source_artifact_id=pair[0], source_revision_id=pair[1], content_sha256=digest)))
                        grants = self._commit('authorize_native_direct_sources', grants=tuple(row for _, row in group))
                        pending_direct.update((selected_handle, grant) for (selected_handle, _), grant in zip(group, grants, strict=True))
                    auth = pending_direct.pop(handle)
                    _, _, display = choices[handle]
                    operation = 'source_document_read'
                    label = source_display_name(display, 'Admitted source')
                elif is_search:
                    auth = self._commit("authorize_native_body_search", event_id=uuid4())
                    operation = 'source_search'
                    label = turn.user_text  # Exact query used by the native lexical-search owner.
                else:
                    _, search, _, _ = self._events(turn)
                    if handle.startswith("native-full-document:"):
                        catalog_sha, section, kind = handle.removeprefix("native-full-document:"), None, "full_document"
                    else:
                        catalog_sha, section = handle.removeprefix("native-body:").split(":", 1)
                        kind = "section"
                    auth = self._commit("authorize_native_body_read", event_id=uuid4(), search_event_id=search.event_id,
                        catalog_sha256=catalog_sha, retrieval_kind=kind, section_id=section)
                    operation = 'source_document_read' if kind == 'full_document' else 'source_section_read'
                    catalog = next(row for row in search.catalogs if row.catalog_sha256 == auth.catalog_sha256)
                    label = self._read_label(catalog, auth.section_id)
            # Capture owns the same claim lock. Persist the issued request before
            # I/O, outside that lock; each materialization uses the latest turn.
            observe_native_retrieval(a, operation, handle, label=label)
            with a.fence.renewer._lock:
                if is_direct:
                    result = self._commit('observe_native_direct_source', event_id=uuid4(), authorization_event_id=auth.event_id,
                        read=lambda grant: read_direct_native_source(context, authority=grant.authority,
                            source_artifact_id=grant.source_artifact_id, source_revision_id=grant.source_revision_id,
                            content_sha256=grant.content_sha256))
                elif is_search:
                    result = self._commit("observe_native_body_search", event_id=uuid4(), authorization_event_id=auth.event_id,
                        capture=lambda: capture_native_sources(managed_world_id=turn.world_id,
                            principal=context.principal, prepared=context))
                else:
                    result = self._commit("observe_native_body_read", event_id=uuid4(), authorization_event_id=auth.event_id,
                        read=lambda authority, member: read_native_corpus_member(authority=authority, member=member,
                            principal=context.principal, prepared=context))
            observe_native_retrieval(a, operation, handle, label=label, completed=True,
                unavailable=not is_search and result.excerpt is None)
        return {"schema": "dmb_native_body_navigation_result_v1", "body_text_exposed": False}

    def unavailable(self, code):
        capture = getattr(self.adapter, "context_capture", None)
        if capture is not None:
            capture.observe({"kind": "failure", "phase": "source_read", "code": code})
        return {"schema": "dmb_native_body_navigation_unavailable_v1", "code": code}
