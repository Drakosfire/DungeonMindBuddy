"""Host-only pending Build source preparation and retained-query reopening."""
from __future__ import annotations

from uuid import uuid4
from application_state.agent_conversation import types as ledger
from application_state.agent_conversation.build_source_free import effective_pending_source, pending_source_work
from application_state.agent_conversation.native_context import BuildPendingContextReceiptV1
from application_state.agent_conversation.native_plan_assertions import NativeGraphQueryV4
from application_state.agent_conversation.native_plan_statements import NativePlanQueryUnavailableV1


class PendingBuildSourcePreparation:
    def __init__(self, *, world_id, principal, app_access, prepare_source, resolve_query,
                 resolve_identity=None, reopen_query=None):
        if (not world_id or principal is None or principal.role != 'gm'
                or getattr(principal, 'managed_world_id', world_id) != world_id or not callable(app_access)
                or not callable(prepare_source) or not callable(resolve_query)):
            raise ValueError('Pending source preparation requires its authenticated host owners')
        if resolve_identity is None:
            from .managed_world_graph_projection import resolve_managed_source_identity
            resolve_identity = resolve_managed_source_identity
        if reopen_query is None:
            from .native_graph_reads import reopen_context
            reopen_query = reopen_context
        self.world_id, self.principal, self.app_access = world_id, principal, app_access
        self.prepare_source, self.resolve_query = prepare_source, resolve_query
        self.resolve_identity, self.reopen_query = resolve_identity, reopen_query

    def _captured_identity(self, turn, world_id):
        binding = turn.graph_context_receipt.source_observation.binding
        if world_id != self.world_id or binding is None:
            raise ValueError('Pending source identity differs from its captured World')
        current = self.resolve_identity(world_id)
        if any(getattr(current, field) != getattr(binding, field) for field in (
                'managed_world_id', 'native_world_id', 'binding_version', 'provisioning_id')):
            raise ValueError('Pending source ownership changed before preparation')
        return current

    def _authorize(self, conn, turn, prepared):
        if (type(turn.graph_context_receipt) is not BuildPendingContextReceiptV1
                or turn.world_id != self.world_id or self.principal.role != 'gm'
                or getattr(self.principal, 'managed_world_id', self.world_id) != self.world_id
                or self.app_access(conn, turn, None) is not True):
            return False
        observed = turn.graph_context_receipt.source_observation
        binding = observed.binding
        revision = observed.requested_or_observed_revision
        if binding is None or (revision is None and not observed.deferred_head):
            return False
        current = self.resolve_identity(self.world_id)
        fields = ('managed_world_id', 'native_world_id', 'binding_version', 'provisioning_id')
        if any(getattr(current, field) != getattr(binding, field) for field in fields):
            return False
        if prepared is not None:
            if (type(prepared) is not tuple or len(prepared) != 2
                    or type(prepared[0]) is not ledger.NativeCorpusAuthorityV1
                    or (revision is not None and prepared[0].revision_id != revision)
                    or any(getattr(prepared[0], field) != getattr(binding, field) for field in fields)):
                return False
        return True

    def _source(self, turn, stored=None):
        observed = turn.graph_context_receipt.source_observation
        revision = stored[0].revision_id if stored is not None else observed.requested_or_observed_revision
        if observed.binding is None or (revision is None and not observed.deferred_head):
            raise ValueError('Pending source has no captured scope to prepare')
        context, authority = self.prepare_source(self.world_id, self.principal, revision_id=revision,
            resolve_identity=lambda world_id: self._captured_identity(turn, world_id))
        if (context is None or type(authority) is not ledger.NativeCorpusAuthorityV1
                or context.authority != authority or (revision is not None and authority.revision_id != revision)
                or any(getattr(authority, field) != getattr(observed.binding, field) for field in (
                    'managed_world_id', 'native_world_id', 'binding_version', 'provisioning_id'))):
            raise ValueError('Pending source preparation did not verify the captured revision')
        if stored is not None:
            original = stored[0]
            if (authority.model_dump(mode='json', exclude={'acquisition_epoch'})
                    != original.model_dump(mode='json', exclude={'acquisition_epoch'})
                    or authority.acquisition_epoch < original.acquisition_epoch):
                raise ValueError('Pending reopening changed its original source authority')
        return context, authority

    def prepare(self, adapter):
        """Publish host contexts only after the transactional access owner returns."""
        if type(adapter._broker_receipt()) is not BuildPendingContextReceiptV1:
            raise ValueError('Pending source owner cannot prepare another action family')
        receipt = adapter._broker_receipt()
        if receipt.source_observation.managed_world_id != self.world_id:
            raise ValueError('Pending source preparation belongs to another World')
        stored = effective_pending_source(receipt, adapter._broker_execution())
        prepared = []
        if stored is None:
            pending_source_work(adapter._broker_execution())
            observed = receipt.source_observation
            if (observed.binding is None or (observed.requested_or_observed_revision is None
                                             and not observed.deferred_head)):
                return False  # No later World/head may substitute for an unobserved scope.
            def materialize(turn):
                context, authority = self._source(turn)
                query_context, query = self.resolve_query(turn, context)
                if (type(query) not in (NativeGraphQueryV4, NativePlanQueryUnavailableV1)
                        or (type(query) is NativeGraphQueryV4 and (query_context is None or query_context.query != query))
                        or (type(query) is NativePlanQueryUnavailableV1 and query_context is not None)):
                    raise ValueError('Pending source requires its exact query preparation owner')
                prepared.append((context, authority, query_context, query))
                return authority, query
            from .agent_turn_service import _require_fresh_execution_append
            adapter.turn = _require_fresh_execution_append(adapter.fence.commit('settle_pending_build_source',
                event_id=uuid4(), materialize_source=materialize, authorize_current_access=self._authorize))
        else:
            def reopen(turn, source):
                context, _ = self._source(turn, source)
                query = source[1]
                query_context = self.reopen_query(query, self.principal) if type(query) is NativeGraphQueryV4 else None
                if query_context is not None and query_context.query != query:
                    raise ValueError('Pending query reopening changed its original discovery')
                if type(query) is NativeGraphQueryV4 and query_context is None:
                    raise ValueError('Pending query reopening did not verify its original authority')
                prepared.append((context, source[0], query_context, query))
                return source
            turn, fresh = adapter.fence.commit('reopen_pending_build_source', reopen_source=reopen,
                authorize_current_access=self._authorize)
            if fresh is not False:
                raise ValueError('Pending reopening cannot create new source authority')
            adapter.turn = turn
        if len(prepared) != 1:
            raise ValueError('Pending source requires its one checked preparation result')
        context, authority, query_context, query = prepared[0]
        if effective_pending_source(adapter._broker_receipt(), adapter._broker_execution()) != (authority, query):
            raise ValueError('Pending host contexts differ from the admitted authority and query')
        adapter.native_corpus_context, adapter.native_source_authority = context, authority
        adapter.native_query_context, adapter.native_query = query_context, query
        return True


def prepare_pending_native_source(adapter):
    """Acquire native context only for unresolved lookup after App acquisition.

    Read App pages must first pass their coverage owner; their presence alone
    cannot authorize a second search or prove sufficient factual coverage.
    """
    if type(adapter._broker_receipt()) is not BuildPendingContextReceiptV1:
        return False
    execution = adapter._broker_execution()
    stored = effective_pending_source(adapter._broker_receipt(), execution)
    if stored is None:
        if any(type(event) is ledger.BuildPriorBodyEvidenceAdmittedV3 for event in execution.events):
            return False
        work = [event for event in execution.events if type(event) is ledger.BuildRequestedWorkResolutionV1]
        if len(work) != 1:
            raise ValueError('Pending preparation requires one admitted work decision')
        work, = work
        if (work.resolution.get('barrier') is not None
                or work.resolution.get('source_scope') not in {'source_lookup', 'uncertain'}
                or work.requested_work in {'review_blank_lore_page', 'clarify_request', 'clarify_creation'}):
            return False
        from application_state.agent_conversation.build_related_pages import RelatedPageRead
        if any(type(event) is RelatedPageRead for event in execution.events):
            from application_state.agent_conversation.build_pending_app_coverage import BuildAppCoverageDecidedV1
            decisions = [event for event in execution.events if type(event) is BuildAppCoverageDecidedV1]
            if len(decisions) != 1 or decisions[0].verdict != 'native_sources_required':
                return False
            pending_source_work(execution)
    owner = adapter.pending_build_source_preparation
    if type(owner) is not PendingBuildSourcePreparation:
        raise ValueError('Pending native preparation has no current host owner')
    return owner.prepare(adapter)
