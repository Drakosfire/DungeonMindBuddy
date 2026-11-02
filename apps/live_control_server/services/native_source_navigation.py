"""Shared parent-owned Plan/Play source navigation; no model-selected paths."""
import re
from collections import Counter
from uuid import uuid4

from application_state.agent_conversation import types as t
from application_state.agent_conversation.native_execution import NativePlanActionV1
from application_state.source.naming import registered_source_name
from application_state.agent_conversation.jev_retrieval_contract import RetrievalCandidate
from application_state.agent_conversation.native_source_input import section_row, CAPABILITIES
from application_state.agent_conversation.source_writer_output import strict_json
from .managed_world_graph_projection import resolve_managed_world_binding
from ..integrations.dungeonmind.world_graph_reads import direct_services_from_config
from ..integrations.dungeonmind.source_origin import verify_native_source_origin
from dungeonmind.contracts.projection_v2 import WorldGraphProjectionRequestV2

BROWSE = 'browse_native_source_sections'
READ = 'read_native_source_sections'
SEARCH = 'search_retained_source_sections'
TOOLS = frozenset({BROWSE,READ,SEARCH})
RESULT = 'dmb_native_source_section_result_v1'
UNAVAILABLE = 'dmb_native_source_section_unavailable_v1'
# Grammatical overlap is not a useful section-navigation signal. This does not
# remove words from evidence or constrain the number/size of selected sections.
from application_state.agent_conversation.corpus_source_search import GRAMMAR as _QUERY_GRAMMAR


class NativeSourceUnavailable(ValueError):
    pass


def section_query_terms(markdown,sections,question):
    """Navigation-only term matches; no uncited source prose enters a model."""
    query=set(re.findall(r"\w+",question.casefold())) - _QUERY_GRAMMAR
    words={s.section_id:set(re.findall(r"\w+",markdown[s.char_start:s.char_end].casefold())) for s in sections}
    frequency=Counter(term for values in words.values() for term in values & query)
    # Terms found in every section cannot distinguish sections. Keep hints for
    # a single-section source, where there is no comparative catalog.
    distinctive={term for term in query if len(words)<=1 or frequency[term]<len(words)}
    return {key:sorted(values & distinctive,key=lambda term:(frequency[term],term)) for key,values in words.items()}


def navigator(adapter):
    if getattr(adapter,'_native_source_navigator',None) is None:
        receipt=adapter.fence.turn.graph_context_receipt if adapter.fence is not None else None
        if (isinstance(receipt,t.PlanSourceContextReceiptV1) or
                (type(receipt) is t.SurfaceNativeContextReceiptV1
                 and type(adapter.fence.turn.graph_context_execution) is t.SurfaceNativeExecutionV1
                 and type(adapter.fence.turn.graph_context_execution.policy.action) is NativePlanActionV1)):
            from .corpus_source_navigation import NativeBodyNavigation
            adapter._native_source_navigator = NativeBodyNavigation(adapter)
        else:
            adapter._native_source_navigator = NativeSourceNavigator(adapter)
    return adapter._native_source_navigator


class NativeSourceNavigator:
    def __init__(self,adapter):
        self.adapter = adapter
        self.sources, self.catalogs, self.materials, self.sections, self.reads = {}, {}, {}, {}, {}
        self.call_results = {}
        self.catalog_names, self.query_matches = {}, {}
        self.attempted_sources = set()
        self.source_ownership = {}
        self.attempted_sections = set()
        from .corpus_source_navigation import CorpusSourceNavigation
        self.corpus = CorpusSourceNavigation(self)

    def enabled(self):
        fence = self.adapter.fence
        return fence is not None and isinstance(fence.turn.graph_context_execution.policy,CAPABILITIES)

    def collect(self):
        if not self.enabled():return
        turn = self.adapter.fence.turn
        execution = turn.graph_context_execution
        names = {}
        capture = getattr(self.adapter,'context_capture',None)
        trace = getattr(capture,'trace',None)
        for row in getattr(trace,'observations',()):
            name = getattr(row,'source_name',None)
            if isinstance(name,str) and name.strip():
                artifact,revision = getattr(row,'source_artifact_id',None),getattr(row,'source_revision_id',None)
                if isinstance(artifact,str) and isinstance(revision,str):names[(artifact,revision)] = name.strip()
        existing = {(entry[1].source_artifact_id,entry[1].source_revision_id) for entry in self.sources.values()}
        pins = execution.effective_source_pins()
        for donor in execution.events:
            if not isinstance(donor,t.ValidatedGraphOperationEventV3):continue
            for pin in donor.returned_source_pins:
                key = (pin.source_artifact_id,pin.source_revision_id)
                if key in existing or pins.get(pin.anchor_id) != pin:continue
                handle = 'native-source:'+t.canonical_sha256({'turn_id':str(turn.turn_id),
                    'donor':str(donor.event_id),'source_artifact_id':key[0],'native_source_revision_id':key[1]})
                label = names.get(key,'Source sections')
                self.sources[handle] = (donor,pin,label)
                existing.add(key)

        self.corpus.hydrate()

        # Eligibility is metadata only, batched once per newly encountered artifact.
        # Keep failed routes visible as unavailable examined subjects without
        # dispatching doomed native provenance/catalog reads. Actual reads retain
        # their authoritative scope and body checks after a positive preflight.
        unknown = list(dict.fromkeys(entry[1].source_artifact_id for entry in self.sources.values()
            if entry[1].source_artifact_id not in self.source_ownership))
        if unknown:
            from application_state.source.service import owned_source_artifacts
            authority = self._bound_authority()
            owned = frozenset().union(*(owned_source_artifacts(source_artifact_ids=unknown, world_id=world)
                for world in dict.fromkeys((authority.managed_world_id, authority.native_world_id))))
            self.source_ownership.update((identity, identity in owned) for identity in unknown)
        for handle, entry in self.sources.items():
            if not self.source_ownership[entry[1].source_artifact_id] and handle not in self.attempted_sources:
                self.attempted_sources.add(handle)

    def _section_candidate(self,handle,*,kind='Exact source section'):
        source_handle,section,name = self.sections[handle]
        revision = self.corpus.revision_metadata(source_handle)
        if revision is not None:
            if revision.get('campaign_id') is not None:name += ' (campaign ' + revision['campaign_id'] + ')'
            name += ' [' + revision['status_at_capture'] + ' revision at source-view capture; recorded ' + revision['recorded_at'] + ']'
        terms=self.query_matches.get(handle,[])
        hint=(f'; discriminating query-term coverage: {len(terms)}; matches: '+', '.join(terms)
            if terms else '; no discriminating query-term matches')
        return RetrievalCandidate(handle=handle,label=name+' — '+section.label+hint,kind=kind)

    def offered(self):
        self.collect()
        browse = [RetrievalCandidate(handle=handle,label='Explore '+entry[2],
            kind='Source navigation: inspect source sections beyond opened passages')
            for handle,entry in self.sources.items() if handle not in self.attempted_sources]
        sections = [self._section_candidate(handle)
            for handle in self.sections if handle not in self.attempted_sections]
        return tuple([*self.corpus.offered(),*browse,*sections])

    def examined(self):
        """Acquisition outcome metadata for decisions, never evidence prose."""
        self.collect()
        rows=[]
        for handle,entry in self.sources.items():
            if handle not in self.attempted_sources:continue
            catalog=self.catalogs.get(handle)
            outcome='Acquired' if catalog is not None and catalog.outcome=='complete' else 'Unavailable'
            rows.append(RetrievalCandidate(handle=handle,label=entry[2],
                kind=outcome+' source section catalog; navigation only'))
        for handle in self.sections:
            if handle not in self.attempted_sections:continue
            read=self.reads.get(handle)
            outcome='Acquired' if read is not None and read.outcome=='complete' else 'Unavailable'
            rows.append(self._section_candidate(handle,
                kind=outcome+' exact source section; navigation only, not evidence sufficiency'))
        return tuple([*self.corpus.examined(),*rows])

    def _plan_selection(self,handles):
        from application_state.agent_conversation.plan_jev_decision import current_selection
        selected = current_selection(self.adapter.fence.turn)
        if selected.operation != 'select_candidates' or not set(handles) <= set(selected.selected_handles):
            raise NativeSourceUnavailable('source_section_not_selected')

    def _bound_authority(self):
        turn = self.adapter.fence.renewer._turn
        authority = turn.graph_context_receipt.graph_authority
        binding = resolve_managed_world_binding(turn.world_id)
        if (authority.managed_world_id != turn.world_id or binding.managed_world_id != turn.world_id
                or binding.native_world_id != authority.native_world_id
                or binding.binding_version != authority.binding_version):
            raise NativeSourceUnavailable('source_navigation_unavailable')
        return authority

    def _access(self,entry):
        if isinstance(entry[0], t.CorpusSourceSearchAuthorizedV1):
            handle = next(h for h, e in self.sources.items() if e is entry)
            return self.corpus.access(handle)
        authority = self._bound_authority()
        projection = WorldGraphProjectionRequestV2.model_validate({'world_id':authority.native_world_id,
            'campaign_id':None,'admissibility':'gm','scope_mode':'world_cross_campaign',
            'focus':{'kind':'none','session_id':None},'revision_pin':authority.graph_revision})
        return verify_native_source_origin(direct_services_from_config(authority.native_world_id),
            projection=projection,donor=entry[0],pin=entry[1])

    def _commit(self,method,**fields):
        a = self.adapter
        turn = a.fence.renewer._turn
        result = getattr(a.service,method)(turn.world_id,turn.conversation_id,turn.turn_id,
            expected_revision=turn.revision,expected_attempt=turn.attempt,**fields)
        a.fence.renewer._turn = result[0]
        a.turn = result[0]
        return result

    def browse(self,handle,*,plan=False):
        self.collect()
        if handle not in self.sources:raise NativeSourceUnavailable('source_navigation_unavailable')
        if plan:self._plan_selection([handle])
        a = self.adapter
        with a.fence.renewer._lock:
            if handle in self.attempted_sources and handle not in self.catalogs:
                raise NativeSourceUnavailable('source_navigation_unavailable')
            self.attempted_sources.add(handle)
            origin = self._access(self.sources[handle])
            proof = strict_json(origin.proof_json)
            name = registered_source_name(proof['artifact'] if isinstance(self.sources[handle][0], t.CorpusSourceSearchAuthorizedV1) else proof['resolution']['artifact'])
            if name is None:
                raise NativeSourceUnavailable('source_navigation_unavailable')
            if handle not in self.catalogs:
                turn = a.fence.renewer._turn
                execution = turn.graph_context_execution
                provider = next(e for e in reversed(execution.events) if isinstance(e,t.ProviderAttemptAuthorizedEventV1))
                registry = isinstance(self.sources[handle][0], t.CorpusSourceSearchAuthorizedV1)
                nav_type = t.NativeSourceNavigationAuthorizedV2 if registry else t.NativeSourceNavigationAuthorizedV1
                nav = nav_type(kind='native_source_navigation_authorized_v2' if registry else 'native_source_navigation_authorized_v1',
                    event_id=uuid4(),sequence=len(execution.events),navigation_id=uuid4(),
                    provider_attempt_id=provider.provider_attempt_id,
                    context_receipt_sha256=execution.context_receipt_sha256,
                    execution_policy_sha256=execution.execution_policy_sha256,world_id=turn.world_id,
                    native_world_id=turn.graph_context_receipt.graph_authority.native_world_id,
                    binding_version=turn.graph_context_receipt.graph_authority.binding_version,
                    origin_proof_json=origin.proof_json,origin_proof_sha256=origin.proof_sha256)
                self._commit('authorize_native_source_navigation',authorization=nav)
                self._bound_authority()
                turn,_,material = self._commit('materialize_native_source_catalog',navigation_id=nav.navigation_id,event_id=uuid4())
                catalog = turn.graph_context_execution.events[-1]
                self.catalogs[handle] = catalog
                self.catalog_names[handle] = name.strip()
                self.materials[catalog.event_id] = material
                if catalog.outcome == 'complete':
                    matches=section_query_terms(material.markdown,catalog.sections,a.fence.renewer._turn.user_text) if material is not None else {}
                    for section in catalog.sections:
                        self.query_matches['native-section:'+section.section_id]=matches.get(section.section_id,[])
                        self.sections['native-section:'+section.section_id] = (handle,section,name.strip())
            catalog = self.catalogs[handle]
            if catalog.outcome != 'complete':raise NativeSourceUnavailable('source_navigation_unavailable')
            return {'schema':'dmb_native_source_catalog_v1','source_name':self.catalog_names[handle],
                'sections':[{'section_handle':'native-section:'+section.section_id,'title':section.label,
                    'matched_query_terms':self.query_matches.get('native-section:'+section.section_id,[])}
                    for section in catalog.sections]}

    def _read_one(self,handle):
        a = self.adapter
        source_handle,section,_name = self.sections[handle]
        prior = self.reads.get(handle)
        if handle in self.attempted_sections and prior is None:
            raise NativeSourceUnavailable('source_section_unavailable')
        self.attempted_sections.add(handle)
        self._access(self.sources[source_handle])
        if prior is not None:
            if prior.outcome != 'complete':raise NativeSourceUnavailable('source_section_unavailable')
            from application_state.agent_conversation.native_source_input import section_handle
            return None,section_handle(prior)
        catalog = self.catalogs[source_handle]
        turn,_ = self._commit('authorize_native_source_section',event_id=uuid4(),read_id=uuid4(),
            catalog_event_id=catalog.event_id,section_id=section.section_id)
        auth = turn.graph_context_execution.events[-1]
        turn,_,observed = self._commit('materialize_native_source_section',event_id=uuid4(),
            read_id=auth.read_id,material=self.materials.get(catalog.event_id))
        self.reads[handle] = observed
        if observed.outcome != 'complete':raise NativeSourceUnavailable('source_section_cache_unavailable')
        return section_row(turn.graph_context_execution,observed),None

    def read(self,handles,*,plan=False):
        if (not isinstance(handles,list) or not handles or any(not isinstance(h,str) for h in handles)
                or len(set(handles)) != len(handles) or any(h not in self.sections for h in handles)):
            raise NativeSourceUnavailable('source_section_unavailable')
        if plan:self._plan_selection(handles)
        rows, reused, partial = [], [], False
        from application_state.errors import ApplicationStateValidationError
        with self.adapter.fence.renewer._lock:
            for handle in handles:
                try:
                    row,reference = self._read_one(handle)
                    if row is not None:rows.append(row)
                    if reference is not None:reused.append(reference)
                except (ValueError,ApplicationStateValidationError):
                    # Keep earlier committed/exposed successes in a mixed batch.
                    # Claim conflicts and indeterminate storage errors propagate;
                    # they never become another read or false success.
                    partial = True
        # Trace persistence owns the same claim lock; observe after releasing it.
        if partial:self.unavailable('source_section_unavailable')
        return {'schema':RESULT,'sections':rows,'reused_section_handles':reused,'partial':partial}

    def select(self,handles):
        for handle in handles:
            from application_state.agent_conversation.corpus_source_search import action_handle
            if handle == action_handle(self.adapter.fence.turn):self.corpus.search(plan=True)
            elif handle in self.sources:self.browse(handle,plan=True)
            elif handle in self.sections:self.read([handle],plan=True)
            else:raise NativeSourceUnavailable('source_section_not_selected')

    def tool(self,name,arguments,*,call_id):
        if (not self.enabled() or not isinstance(self.adapter.fence.turn.graph_context_execution.policy,t.PlayNativeSourceSectionsPolicyV1)
                or name not in TOOLS or not isinstance(arguments,dict)):
            raise NativeSourceUnavailable('native_source_call_unverified')
        reply = getattr(self.adapter,'native_source_reply',None)
        latest = next((e for e in reversed(self.adapter.fence.turn.graph_context_execution.events)
            if isinstance(e,t.ProviderAttemptAuthorizedEventV1)),None)
        producing = getattr(self.adapter,'native_source_provider_id',None)
        if (latest is None or reply is None or getattr(reply,'request_sha256',None) != latest.envelope_sha256
                or producing != latest.provider_attempt_id):
            raise NativeSourceUnavailable('native_source_call_unverified')
        calls = [call for call in getattr(reply,'tool_calls',()) if call.call_id == call_id]
        if (reply.status != 'tool_calls' or len(calls) != 1 or calls[0].name != name
                or strict_json(calls[0].arguments_json) != arguments):
            raise NativeSourceUnavailable('native_source_call_unverified')
        identity = (reply.api_request_id,calls[0].call_id)
        if identity in self.call_results:return self.call_results[identity]
        self.collect()  # a recovered Play worker may dispatch before composing another offer
        if name == SEARCH and arguments == {}:
            result = self.corpus.search()
        elif name == BROWSE and set(arguments) == {'anchor_id'}:
            self.collect()
            matches = [handle for handle,entry in self.sources.items() if getattr(entry[1], 'anchor_id', None) == arguments['anchor_id']]
            if len(matches) != 1:raise NativeSourceUnavailable('source_navigation_unavailable')
            result = self.browse(matches[0])
        elif name == READ and set(arguments) == {'section_handles'}:
            result = self.read(arguments['section_handles'])
        else:raise NativeSourceUnavailable('native_source_call_unverified')
        self.call_results[identity] = result
        return result

    def unavailable(self,code):
        capture = getattr(self.adapter,'context_capture',None)
        if capture is not None:capture.observe({'kind':'failure','phase':'source_read','code':code})
        return {'schema':UNAVAILABLE,'code':code}
