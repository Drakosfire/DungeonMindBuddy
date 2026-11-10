"""APP native read admission and materialization under the existing turn lock.

The current concrete surface adapter is Plan; its SDK decisions and work binding
remain owned there. Record-family and corpus-body materializers share one strict
Turn admission boundary, without a new receipt, event family or provenance ledger.
Core continues to own source admission and current native source access.
"""
from copy import deepcopy
from uuid import UUID
from dataclasses import dataclass
from hashlib import sha256

from .native_corpus import (
    NativeCorpusAuthorityV1, NativeBodySearchAuthorizedV1, NativeBodySearchObservedV1,
    NativeInitialSourceSearchAuthorizedV1, initial_source_discovery_enabled, validate_initial_source_search,
    NativePlanRequestSearchAuthorizedV1, request_source_discovery_enabled, validate_request_source_search,
    NativeBodyReadAuthorizedV1, NativeBodyReadObservedV1, NativeBodySectionMatchV1,
    build_native_body_catalog, native_corpus_search_handle, native_body_handle,
    native_full_document_handle, select_native_full_document, select_native_body_excerpt,
)
from .native_plan_statements import (
    NativePlanQueryV1, NativePlanStatementReadAuthorizedV1, NativePlanStatementReadObservedV1,
    validate_execution,
)


@dataclass(frozen=True, slots=True)
class _NativeReadOperation:
    """Closed dispatch to existing read producers, never a generic Turn callback.

    Only these owners may inspect the admitted Turn. External readers receive
    detached grant/authority/reference values at their actual callback boundary.
    """
    producer: object
    arguments: dict

    def __post_init__(self):
        from .authored_graph_references import (
            capture_native_input, authorize_native_reference,
            observe_native_reference, observe_native_source_reference,
        )
        from .native_batch_completion import conclude_selected_batch
        if self.producer not in {
            authorize_read, observe_read, capture_native_input,
            authorize_native_reference, observe_native_reference, observe_native_source_reference,
            authorize_direct_sources_locked, observe_direct_source_locked,
            authorize_body_search_locked, observe_body_search_locked,
            authorize_initial_source_search_locked,
            authorize_request_source_search_locked,
            conclude_selected_batch,
            authorize_body_reads_locked, observe_body_reads_locked,
        }:
            raise ValueError('Native read requires its existing closed producer')

    def __call__(self, conn, turn):
        from application_state.errors import ApplicationStateValidationError
        try:
            return self.producer(turn, **self.arguments)
        except (ValueError, TypeError, KeyError, AttributeError) as exc:
            raise ApplicationStateValidationError(str(exc)) from exc


def validate_execution_binding(receipt, execution):
    """One frozen native authority/query binding for every admitted read family."""
    from . import types as t
    from .native_context import SurfaceNativeContextReceiptV1
    from .native_execution import SurfaceNativeExecutionV1, validate_context_binding
    if (type(receipt), type(execution)) == (SurfaceNativeContextReceiptV1, SurfaceNativeExecutionV1):
        validate_context_binding(receipt, execution)
        return
    if (type(receipt), type(execution)) not in {
        (t.PlanSourceContextReceiptV1, t.PlanSourceExecutionV1),
        (t.PlanNativeContextReceiptV1, t.PlanNativeExecutionV1),
    }:
        raise ValueError("Native reads require their exact receipt and execution")
    if (execution.context_receipt_sha256 != receipt.context_receipt_sha256
            or execution.policy.source_authority_sha256 != t.canonical_sha256(
                receipt.source_authority.model_dump(mode="json", by_alias=True))):
        raise ValueError("Native source execution differs from its frozen receipt authority")
    if isinstance(receipt, t.PlanNativeContextReceiptV1):
        validate_execution(receipt, execution)
    for event in execution.events:
        if isinstance(event, NativeBodySearchAuthorizedV1) and (
                not isinstance(receipt.source_authority, NativeCorpusAuthorityV1)
                or event.authority != receipt.source_authority):
            raise ValueError("Native source search differs from its frozen source-only authority")


def _owner(turn, *, require_source=False):
    """Resolve a transaction-internal producer's actual running surface owner.

    Shared inputs come only from APP's current locked storage admission: its
    complete initial/recovery codec or exclusively owned guarded session. That
    owner validates the stored binding before IO and the materialized transition
    again before persistence; this private helper is not a standalone binder.
    """
    from .plan_jev_decision import _owner as plan_owner
    from .plan_source_context import validate_source_provenance

    from .native_context import SurfaceNativeContextReceiptV1
    if type(turn.graph_context_receipt) is SurfaceNativeContextReceiptV1:
        from .native_retrieval import owner
        receipt, execution = owner(turn)
    else:
        receipt, execution = plan_owner(turn)
    if turn.world_id != turn.provenance.world_id:
        raise ValueError("Native read turn differs from its owning World")
    if type(receipt) is not SurfaceNativeContextReceiptV1:
        validate_execution_binding(receipt, execution)
    if require_source and not isinstance(receipt.source_authority, NativeCorpusAuthorityV1):
        raise ValueError("Native body acquisition requires its available frozen source authority")
    if type(receipt) is not SurfaceNativeContextReceiptV1:
        validate_source_provenance(receipt, turn.provenance)
    return receipt, execution


def _validate_prospective_read(receipt, execution, event):
    # Shared callbacks run only inside APP's locked append transaction. Its
    # postcallback binder owns full prospective validation before persistence.
    # Preserve the earlier duplicate-ID refusal before service replay handling.
    from .native_context import SurfaceNativeContextReceiptV1
    if type(receipt) is SurfaceNativeContextReceiptV1:
        if any(prior.event_id == event.event_id for prior in execution.events):
            raise ValueError("Graph execution event IDs must be unique")
    else:
        validate_execution_binding(receipt, execution.model_copy(update={"events": [*execution.events, event]}))


def authorize_read(turn, *, event_id, record_kind, record_ids):
    """Authorize one native record family through the shared selected-read ledger."""
    from .plan_jev_decision import current_selection
    from . import types as t
    from .native_plan_assertions import NativePlanQueryV2, NativePlanAssertionReadAuthorizedV1
    if record_kind not in {"statement", "assertion"}:
        raise ValueError("Unknown native selected-read record kind")
    receipt, execution = _owner(turn)
    query = getattr(receipt, "native_query", None)
    if (not isinstance(receipt, (t.PlanNativeContextReceiptV1,t.SurfaceNativeContextReceiptV1))
            or not isinstance(query, NativePlanQueryV1)
            or record_kind == "assertion" and not isinstance(query, NativePlanQueryV2)):
        raise ValueError("Native query is unavailable for the selected record kind")
    event_type, ids_field = ((NativePlanAssertionReadAuthorizedV1, "assertion_ids")
        if record_kind == "assertion" else (NativePlanStatementReadAuthorizedV1, "statement_ids"))
    event = event_type(event_id=event_id, sequence=len(execution.events),
        provider_attempt_id=current_selection(turn).controller_attempt_id,
        query_sha256=query.sha256, **{ids_field: tuple(record_ids)})
    _validate_prospective_read(receipt, execution, event)
    return event


def observe_read(turn, *, event_id, authorization_event_id, reads, unavailable_ids):
    """The retained grant chooses the observation family, never the caller."""
    from .native_plan_assertions import NativePlanAssertionReadAuthorizedV1, NativePlanAssertionReadObservedV1
    receipt, execution = _owner(turn)
    grants = [event for event in execution.events
        if isinstance(event, (NativePlanStatementReadAuthorizedV1, NativePlanAssertionReadAuthorizedV1))
        and event.event_id == authorization_event_id]
    if len(grants) != 1:
        raise ValueError("Native observation requires one exact retained read grant")
    event_type, unavailable_field = ((NativePlanAssertionReadObservedV1, "unavailable_assertion_ids")
        if isinstance(grants[0], NativePlanAssertionReadAuthorizedV1)
        else (NativePlanStatementReadObservedV1, "unavailable_statement_ids"))
    if isinstance(grants[0], NativePlanAssertionReadAuthorizedV1):
        from .native_context import SurfaceNativeContextReceiptV1
        if type(receipt) is SurfaceNativeContextReceiptV1:
            from .native_plan_assertions import NativePlanAssertionReadObservedV2, compact_assertion_read
            event_type = NativePlanAssertionReadObservedV2
            reads = tuple(compact_assertion_read(read) for read in reads)
    event = event_type(event_id=event_id, sequence=len(execution.events),
        authorization_event_id=authorization_event_id, reads=tuple(reads),
        status="partial" if unavailable_ids else "complete",
        **{unavailable_field: tuple(unavailable_ids)})
    _validate_prospective_read(receipt, execution, event)
    return event


def _prior_event(execution, event_id, model, **identity):
    prior = next((event for event in execution.events if event.event_id == event_id), None)
    if prior is not None and (not isinstance(prior, model)
            or any(getattr(prior, key) != value for key, value in identity.items())):
        raise ValueError("Native body event identity was reused with a changed target")
    return prior


def _selected_controller(turn, handle):
    from .plan_jev_decision import current_selection
    selected = current_selection(turn)
    if selected.operation != "select_candidates" or handle not in selected.selected_handles:
        raise ValueError("Native body acquisition was not selected by the current controller")
    return selected.controller_attempt_id


def authorize_body_search_locked(turn, *, event_id):
    receipt, execution = _owner(turn, require_source=True)
    query = sha256(turn.user_text.encode()).hexdigest()
    prior = _prior_event(execution, event_id, NativeBodySearchAuthorizedV1, query_sha256=query)
    if prior is not None:
        return prior
    if initial_source_discovery_enabled(execution):
        raise ValueError("Readonly Plan source discovery belongs to its initial work, not a later search vote")
    return NativeBodySearchAuthorizedV1(event_id=event_id, sequence=len(execution.events),
        provider_attempt_id=_selected_controller(turn, native_corpus_search_handle(query)),
        context_receipt_sha256=receipt.context_receipt_sha256,
        execution_policy_sha256=execution.execution_policy_sha256,
        authority=receipt.source_authority, query_sha256=query)


def authorize_initial_source_search_locked(turn, *, event_id):
    from .native_execution import NativePlanRequestedWorkSelectedV3
    receipt, execution = _owner(turn, require_source=True)
    work = next((event for event in execution.events
        if type(event) is NativePlanRequestedWorkSelectedV3), None)
    if work is None:
        raise ValueError("Initial source discovery requires its readonly work selection")
    prior = _prior_event(execution, event_id, NativeInitialSourceSearchAuthorizedV1,
        work_selection_event_id=work.event_id)
    if prior is not None:
        return prior
    grant = NativeInitialSourceSearchAuthorizedV1(event_id=event_id, sequence=len(execution.events),
        work_selection_event_id=work.event_id, context_receipt_sha256=receipt.context_receipt_sha256,
        execution_policy_sha256=execution.execution_policy_sha256, authority=receipt.source_authority,
        query_sha256=sha256(turn.user_text.encode()).hexdigest())
    validate_initial_source_search(execution, grant)
    return grant


def authorize_request_source_search_locked(turn, *, event_id):
    receipt, execution = _owner(turn, require_source=True)
    if not request_source_discovery_enabled(receipt, execution):
        raise ValueError('Request source discovery requires its actual request-admission protocol')
    manifest = receipt.assembled_input.manifest_sha256
    prior = _prior_event(execution, event_id, NativePlanRequestSearchAuthorizedV1,
        request_manifest_sha256=manifest)
    if prior is not None:
        return prior
    grant = NativePlanRequestSearchAuthorizedV1(event_id=event_id, sequence=len(execution.events),
        request_manifest_sha256=manifest, context_receipt_sha256=receipt.context_receipt_sha256,
        execution_policy_sha256=execution.execution_policy_sha256, authority=receipt.source_authority,
        query_sha256=sha256(turn.user_text.encode()).hexdigest())
    validate_request_source_search(execution, grant)
    return grant


def observe_body_search_locked(turn, *, event_id, authorization_event_id, capture):
    """The trusted Core capture runs only after a durable discovery grant."""
    from .corpus_source_search import terms
    receipt, execution = _owner(turn, require_source=True)
    prior = _prior_event(execution, event_id, NativeBodySearchObservedV1,
        authorization_event_id=authorization_event_id)
    if prior is not None:
        return prior
    grant = next((event for event in execution.events if isinstance(event,
        (NativeBodySearchAuthorizedV1, NativeInitialSourceSearchAuthorizedV1, NativePlanRequestSearchAuthorizedV1))
        and event.event_id == authorization_event_id), None)
    if grant is None:
        raise ValueError("Native source search lacks its current durable authorization")
    if type(grant) is NativePlanRequestSearchAuthorizedV1:
        validate_request_source_search(execution, grant)
        from . import types as t
        if any(isinstance(e, t.ProviderAttemptAuthorizedEventV1) for e in execution.events[grant.sequence + 1:]):
            raise ValueError('Request source discovery cannot resume after provider dispatch')
    elif type(grant) is NativeInitialSourceSearchAuthorizedV1:
        from .native_retrieval import NativeRetrievalAuthorizedV1
        validate_initial_source_search(execution, grant)
        if any(isinstance(event, NativeRetrievalAuthorizedV1) for event in execution.events[grant.sequence + 1:]):
            raise ValueError("Initial source discovery cannot resume after retrieval started")
    elif _selected_controller(turn, native_corpus_search_handle(grant.query_sha256)) != grant.provider_attempt_id:
        raise ValueError("Native source search lacks its current durable authorization")
    if any(isinstance(event, NativeBodySearchObservedV1) and event.authorization_event_id == grant.event_id
            for event in execution.events):
        raise ValueError("Native source search already has an observation; reuse its receipt")
    captured = capture()
    if captured.authority != receipt.source_authority:
        raise ValueError("Native source capture differs from its frozen authority")
    catalogs, matches = [], []
    query = set(terms(turn.user_text))
    for member in captured.members:
        key = (member.artifact.source_artifact_id, member.revision.source_revision_id)
        catalog = build_native_body_catalog(receipt.source_authority, member, captured.bodies[key])
        catalogs.append(catalog)
        for section in catalog.sections:
            # Keep every literal match, even when a term occurs in all sections.
            # Relevance and sufficiency remain separate controller/writer choices.
            matched = tuple(sorted(query & set(terms(captured.bodies[key][section.char_start:section.char_end]))))
            if matched:
                matches.append(NativeBodySectionMatchV1(catalog_sha256=catalog.catalog_sha256,
                    section_id=section.section_id, matched_terms=matched))
    return NativeBodySearchObservedV1(event_id=event_id, sequence=len(execution.events),
        authorization_event_id=grant.event_id, catalogs=tuple(catalogs), matches=tuple(matches),
        unavailable_source_count=captured.unavailable_source_count)


def _body_catalog(execution, search_event_id, catalog_sha256):
    search = next((event for event in execution.events if isinstance(event, NativeBodySearchObservedV1)
        and event.event_id == search_event_id), None)
    catalog = next((row for row in search.catalogs if row.catalog_sha256 == catalog_sha256), None) if search else None
    if catalog is None:
        raise ValueError("Selected native source catalog is unavailable")
    return catalog


def _body_handle(catalog, retrieval_kind, section_id):
    catalog_sha256 = catalog.catalog_sha256
    if retrieval_kind == "section":
        section = next((row for row in catalog.sections if row.section_id == section_id), None)
        if section is None:
            raise ValueError("Selected native body section is unavailable")
        if section.byte_start == 0 and section.byte_end == catalog.body_bytes:
            raise ValueError("Whole-body exposure requires an explicit full-document decision")
        handle = native_body_handle(catalog_sha256, section_id)
    elif retrieval_kind == "full_document" and section_id is None:
        handle = native_full_document_handle(catalog_sha256)
    else:
        raise ValueError("Native body read requires an explicit section or full-document selector")
    return handle


def _body_group(turn, execution, grants, *, settled=False):
    """One exact catalog binds the complete immutable member/access span."""
    from . import types as t
    if not grants or len({g.event_id for g in grants}) != len(grants):
        raise ValueError('Native body group repeats a grant')
    first = grants[0]
    if any((g.search_event_id, g.catalog_sha256, g.provider_attempt_id)
            != (first.search_event_id, first.catalog_sha256, first.provider_attempt_id) for g in grants):
        raise ValueError('Native body group requires the same exact catalog and source member')
    catalog = _body_catalog(execution, first.search_event_id, first.catalog_sha256)
    handles = [_body_handle(catalog, g.retrieval_kind, g.section_id) for g in grants]
    if len(set(handles)) != len(handles):
        raise ValueError('Native body group repeats a selected extent')
    choices = [e for e in execution.events if isinstance(e, t.PlanJevRetrievalSelectionV1)
        and e.controller_attempt_id == first.provider_attempt_id and e.operation == 'select_candidates']
    if len(choices) != 1:
        raise ValueError('Native body group lacks its exact producing selection')
    selection = choices[0]
    if not settled and any(_selected_controller(turn, h) != selection.controller_attempt_id for h in handles):
        raise ValueError('Native body group changed its current controller')
    positions = [selection.selected_handles.index(h) for h in handles]
    if positions != list(range(positions[0], positions[0] + len(positions))):
        raise ValueError('Native body group must follow consecutive selected order')
    if len(grants) > 1 and (any(g.retrieval_kind != 'section' for g in grants)
            or native_full_document_handle(first.catalog_sha256) in selection.selected_handles):
        raise ValueError('Full-document coverage is a native body group boundary')
    return catalog, selection


def authorize_body_reads_locked(turn, *, grants):
    """Commit every extent grant before the group's single physical capture."""
    _, execution = _owner(turn, require_source=True)
    fields = {'event_id', 'search_event_id', 'catalog_sha256', 'retrieval_kind', 'section_id'}
    if type(grants) is not tuple or not grants or any(type(g) is not dict or set(g) != fields for g in grants):
        raise ValueError('Native body grants require a nonempty closed group')
    proposed = tuple(NativeBodyReadAuthorizedV1(**g, sequence=len(execution.events) + i,
        provider_attempt_id=_selected_controller(turn, _body_handle(
            _body_catalog(execution, g['search_event_id'], g['catalog_sha256']), g['retrieval_kind'], g['section_id'])))
        for i, g in enumerate(grants))
    _, selection = _body_group(turn, execution, proposed)
    priors = tuple(_prior_event(execution, g['event_id'], NativeBodyReadAuthorizedV1,
        **{k: v for k, v in g.items() if k != 'event_id'}) for g in grants)
    if any(priors):
        if (not all(priors) or any(g.provider_attempt_id != selection.controller_attempt_id for g in priors)
                or [g.sequence for g in priors] != list(range(priors[0].sequence, priors[0].sequence + len(priors)))):
            raise ValueError('Native body group replay is partial, reordered or cross-controller')
        return priors
    observed = {e.authorization_event_id for e in execution.events if type(e) is NativeBodyReadObservedV1}
    if any(type(e) is NativeBodyReadAuthorizedV1 and e.event_id not in observed for e in execution.events):
        raise ValueError('Native body group has an unresolved capture; automatic replay is forbidden')
    return proposed


def _body_observation(auth, catalog, text, *, event_id, sequence):
    excerpt, failure = None, "native_body_unavailable"
    if text is not None:
        try:
            excerpt = select_native_full_document(catalog, text) if auth.retrieval_kind == 'full_document' else select_native_body_excerpt(catalog, text, auth.section_id)
            failure = None
        except (ValueError, UnicodeError):
            failure = "native_body_integrity_error"
    return NativeBodyReadObservedV1(event_id=event_id, sequence=sequence,
        authorization_event_id=auth.event_id, excerpt=excerpt, failure_code=failure)


def observe_body_reads_locked(turn, *, reads, read):
    """Capture one durable exact member once; commit all its selected extents."""
    receipt, execution = _owner(turn, require_source=True)
    if (type(reads) is not tuple or not reads
            or any(type(r) is not dict or set(r) != {'event_id', 'authorization_event_id'} for r in reads)
            or any(type(v) is not UUID for r in reads for v in r.values())
            or len({r['event_id'] for r in reads}) != len(reads)
            or len({r['authorization_event_id'] for r in reads}) != len(reads)):
        raise ValueError('Native body observations require a nonempty unique closed group')
    command = tuple((r['event_id'], r['authorization_event_id']) for r in reads)
    priors = tuple(_prior_event(execution, r['event_id'], NativeBodyReadObservedV1,
        authorization_event_id=r['authorization_event_id']) for r in reads)
    by_id = {e.event_id: e for e in execution.events if type(e) is NativeBodyReadAuthorizedV1}
    grants = tuple(by_id.get(r['authorization_event_id']) for r in reads)
    if any(g is None for g in grants):
        raise ValueError('Native body group lacks durable grants')
    if [g.sequence for g in grants] != list(range(grants[0].sequence, grants[0].sequence + len(grants))):
        raise ValueError('Native body group grants are reordered or not contiguous')
    start, end = grants[0].sequence, grants[-1].sequence + 1
    while start and type(execution.events[start - 1]) is NativeBodyReadAuthorizedV1:
        start -= 1
    while end < len(execution.events) and type(execution.events[end]) is NativeBodyReadAuthorizedV1:
        end += 1
    if [e.event_id for e in execution.events[start:end]] != [g.event_id for g in grants]:
        raise ValueError('Native body observations must settle the complete issued group')
    if any(priors):
        if not all(priors) or [p.sequence for p in priors] != list(range(priors[0].sequence, priors[0].sequence + len(priors))):
            raise ValueError('Native body observation replay is partial or reordered')
        _body_group(turn, execution, grants, settled=True)
        return priors
    catalog, selection = _body_group(turn, execution, grants)
    if any(g.provider_attempt_id != selection.controller_attempt_id for g in grants):
        raise ValueError('Native body authorization is no longer current')
    group_ids = {g.event_id for g in grants}
    if any(type(e) is NativeBodyReadObservedV1 and e.authorization_event_id in group_ids for e in execution.events):
        raise ValueError('Native body group already has an observation; reuse its receipt')
    # External code sees detached authority/member only, never the private Turn.
    # Exceptions propagate. A failed physical capture is not unavailability.
    text = read(deepcopy(receipt.source_authority), deepcopy(catalog.source))
    if reads != tuple(dict(event_id=eid, authorization_event_id=aid) for eid, aid in command):
        raise ValueError('Native body group command changed during physical capture')
    if text is not None and not isinstance(text, str):
        raise ValueError('Native body owner must return verified text or explicit unavailability')
    return tuple(_body_observation(g, catalog, text, event_id=eid,
        sequence=len(execution.events) + i) for i, (g, (eid, _)) in enumerate(zip(grants, command, strict=True)))


def authorize_direct_sources_locked(turn, *, grants):
    """Authorize one consecutive batch under the same acknowledged selection."""
    from .native_corpus import NativeDirectSourceAuthorizedV1, native_direct_source_handle
    from .native_context import SurfaceNativeContextReceiptV1
    from .plan_jev_decision import current_selection
    receipt, execution = _owner(turn, require_source=True)
    if type(receipt) is not SurfaceNativeContextReceiptV1:
        raise ValueError("Direct source selection requires the current shared native owner")
    fields = {"event_id", "source_artifact_id", "source_revision_id", "content_sha256"}
    if not isinstance(grants, tuple) or not grants or any(type(row) is not dict or set(row) != fields for row in grants):
        raise ValueError("Direct source grants require a nonempty closed batch")
    handles = [native_direct_source_handle(receipt.source_authority,
        row["source_artifact_id"], row["source_revision_id"], row["content_sha256"]) for row in grants]
    if len({row["event_id"] for row in grants}) != len(grants) or len(set(handles)) != len(handles):
        raise ValueError("Direct source batch repeats a grant or source")
    selection = current_selection(turn)
    if selection.operation != "select_candidates" or any(handle not in selection.selected_handles for handle in handles):
        raise ValueError("Direct source batch differs from its acknowledged selection")
    positions = [selection.selected_handles.index(handle) for handle in handles]
    if positions != list(range(positions[0], positions[0] + len(positions))):
        raise ValueError("Direct source batch is not consecutive in its selected order")
    priors = [_prior_event(execution, row["event_id"], NativeDirectSourceAuthorizedV1,
        **{key: value for key, value in row.items() if key != "event_id"}) for row in grants]
    if any(priors):
        if (not all(priors) or any(prior.provider_attempt_id != selection.controller_attempt_id for prior in priors)
                or [prior.sequence for prior in priors] != list(range(priors[0].sequence, priors[0].sequence + len(priors)))):
            raise ValueError("Direct source batch replay is partial, reordered or belongs to another controller")
        return tuple(priors)
    return tuple(NativeDirectSourceAuthorizedV1(**row, sequence=len(execution.events) + index,
        provider_attempt_id=selection.controller_attempt_id, authority=receipt.source_authority)
        for index, row in enumerate(grants))


def observe_direct_source_locked(turn, *, event_id, authorization_event_id, read):
    from .native_corpus import NativeDirectSourceAuthorizedV1, NativeDirectSourceObservedV1, native_direct_source_handle
    from .native_context import SurfaceNativeContextReceiptV1
    receipt, execution = _owner(turn, require_source=True)
    if type(receipt) is not SurfaceNativeContextReceiptV1:
        raise ValueError("Direct source selection requires the current shared native owner")
    prior = _prior_event(execution, event_id, NativeDirectSourceObservedV1,
        authorization_event_id=authorization_event_id)
    if prior is not None:
        return prior
    auth = next((event for event in execution.events if isinstance(event, NativeDirectSourceAuthorizedV1)
        and event.event_id == authorization_event_id), None)
    if auth is None or _selected_controller(turn, native_direct_source_handle(auth.authority,
            auth.source_artifact_id, auth.source_revision_id, auth.content_sha256)) != auth.provider_attempt_id:
        raise ValueError("Direct source read lacks its current durable selection")
    if any(isinstance(event, NativeDirectSourceObservedV1)
            and event.authorization_event_id == authorization_event_id for event in execution.events):
        raise ValueError("Direct source selection already has an observation; reuse its receipt")
    result = read(deepcopy(auth))
    catalog, excerpt = result if result is not None else (None, None)
    return NativeDirectSourceObservedV1(event_id=event_id, sequence=len(execution.events),
        authorization_event_id=auth.event_id, catalog=catalog, excerpt=excerpt,
        failure_code=None if result is not None else "native_body_unavailable")
