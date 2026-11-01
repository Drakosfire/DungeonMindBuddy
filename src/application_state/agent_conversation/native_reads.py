"""APP native read admission and materialization under the existing turn lock.

The current concrete surface adapter is Plan; its SDK decisions and work binding
remain owned there. Record-family and corpus-body materializers share one strict
Turn admission boundary, without a new receipt, event family or provenance ledger.
Core continues to own source admission and current native source access.
"""
from hashlib import sha256

from .native_corpus import (
    NativeCorpusAuthorityV1, NativeBodySearchAuthorizedV1, NativeBodySearchObservedV1,
    NativeBodyReadAuthorizedV1, NativeBodyReadObservedV1, NativeBodySectionMatchV1,
    build_native_body_catalog, native_corpus_search_handle, native_body_handle,
    native_full_document_handle, select_native_full_document, select_native_body_excerpt,
)
from .native_plan_statements import (
    NativePlanQueryV1, NativePlanStatementReadAuthorizedV1, NativePlanStatementReadObservedV1,
    validate_execution,
)


def validate_execution_binding(receipt, execution):
    """One frozen native authority/query binding for every admitted read family."""
    from . import types as t
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
    """Admit an actual running turn through its concrete supported surface owner."""
    from .plan_jev_decision import _owner as plan_owner
    from .plan_source_context import validate_source_provenance

    receipt, execution = plan_owner(turn)
    if turn.world_id != turn.provenance.world_id:
        raise ValueError("Native read turn differs from its owning World")
    validate_execution_binding(receipt, execution)
    if require_source and not isinstance(receipt.source_authority, NativeCorpusAuthorityV1):
        raise ValueError("Native body acquisition requires its available frozen source authority")
    validate_source_provenance(receipt, turn.provenance)
    return receipt, execution


def authorize_read(turn, *, event_id, record_kind, record_ids):
    """Authorize one native record family through the shared selected-read ledger."""
    from .plan_jev_decision import current_selection
    from . import types as t
    from .native_plan_assertions import NativePlanQueryV2, NativePlanAssertionReadAuthorizedV1
    if record_kind not in {"statement", "assertion"}:
        raise ValueError("Unknown native selected-read record kind")
    receipt, execution = _owner(turn)
    query = getattr(receipt, "native_query", None)
    if (not isinstance(receipt, t.PlanNativeContextReceiptV1)
            or not isinstance(query, NativePlanQueryV1)
            or record_kind == "assertion" and not isinstance(query, NativePlanQueryV2)):
        raise ValueError("Native query is unavailable for the selected record kind")
    event_type, ids_field = ((NativePlanAssertionReadAuthorizedV1, "assertion_ids")
        if record_kind == "assertion" else (NativePlanStatementReadAuthorizedV1, "statement_ids"))
    event = event_type(event_id=event_id, sequence=len(execution.events),
        provider_attempt_id=current_selection(turn).controller_attempt_id,
        query_sha256=query.sha256, **{ids_field: tuple(record_ids)})
    validate_execution(receipt, execution.model_copy(update={"events": [*execution.events, event]}))
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
    event = event_type(event_id=event_id, sequence=len(execution.events),
        authorization_event_id=authorization_event_id, reads=tuple(reads),
        status="partial" if unavailable_ids else "complete",
        **{unavailable_field: tuple(unavailable_ids)})
    validate_execution(receipt, execution.model_copy(update={"events": [*execution.events, event]}))
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
    return NativeBodySearchAuthorizedV1(event_id=event_id, sequence=len(execution.events),
        provider_attempt_id=_selected_controller(turn, native_corpus_search_handle(query)),
        context_receipt_sha256=receipt.context_receipt_sha256,
        execution_policy_sha256=execution.execution_policy_sha256,
        authority=receipt.source_authority, query_sha256=query)


def observe_body_search_locked(turn, *, event_id, authorization_event_id, capture):
    """The trusted Core capture runs only after a durable selected search grant."""
    from .corpus_source_search import terms
    receipt, execution = _owner(turn, require_source=True)
    prior = _prior_event(execution, event_id, NativeBodySearchObservedV1,
        authorization_event_id=authorization_event_id)
    if prior is not None:
        return prior
    grant = next((event for event in execution.events if isinstance(event, NativeBodySearchAuthorizedV1)
        and event.event_id == authorization_event_id), None)
    if grant is None or _selected_controller(turn, native_corpus_search_handle(grant.query_sha256)) != grant.provider_attempt_id:
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


def authorize_body_read_locked(turn, *, event_id, search_event_id, catalog_sha256,
                               retrieval_kind, section_id):
    _, execution = _owner(turn, require_source=True)
    prior = _prior_event(execution, event_id, NativeBodyReadAuthorizedV1,
        search_event_id=search_event_id, catalog_sha256=catalog_sha256,
        retrieval_kind=retrieval_kind, section_id=section_id)
    if prior is not None:
        return prior
    search = next((event for event in execution.events if isinstance(event, NativeBodySearchObservedV1)
        and event.event_id == search_event_id), None)
    catalog = next((row for row in search.catalogs if row.catalog_sha256 == catalog_sha256), None) if search else None
    if catalog is None:
        raise ValueError("Selected native source catalog is unavailable")
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
    return NativeBodyReadAuthorizedV1(event_id=event_id, sequence=len(execution.events),
        provider_attempt_id=_selected_controller(turn, handle), search_event_id=search_event_id,
        catalog_sha256=catalog_sha256, retrieval_kind=retrieval_kind, section_id=section_id)


def observe_body_read_locked(turn, *, event_id, authorization_event_id, read):
    """Read through the trusted Core owner; select only the authorized exact extent."""
    receipt, execution = _owner(turn, require_source=True)
    prior = _prior_event(execution, event_id, NativeBodyReadObservedV1,
        authorization_event_id=authorization_event_id)
    if prior is not None:
        return prior
    auth = next((event for event in execution.events if isinstance(event, NativeBodyReadAuthorizedV1)
        and event.event_id == authorization_event_id), None)
    if auth is None:
        raise ValueError("Native body read lacks its durable authorization")
    full = auth.retrieval_kind == "full_document"
    handle = native_full_document_handle(auth.catalog_sha256) if full else native_body_handle(auth.catalog_sha256, auth.section_id)
    if _selected_controller(turn, handle) != auth.provider_attempt_id:
        raise ValueError("Native body read authorization is no longer current")
    search = next(event for event in execution.events if isinstance(event, NativeBodySearchObservedV1)
        and event.event_id == auth.search_event_id)
    catalog = next(row for row in search.catalogs if row.catalog_sha256 == auth.catalog_sha256)
    # Access/authority failures from the owner propagate. They cannot become an
    # apparently successful empty read or permit a provider to skip the grant.
    if any(isinstance(event, NativeBodyReadObservedV1) and event.authorization_event_id == auth.event_id
            for event in execution.events):
        raise ValueError("Native body read already has an observation; reuse its receipt")
    text = read(receipt.source_authority, catalog.source)
    if text is not None and not isinstance(text, str):
        raise ValueError("Native body owner must return verified text or explicit unavailability")
    excerpt, failure = None, "native_body_unavailable"
    if text is not None:
        try:
            excerpt = select_native_full_document(catalog, text) if full else select_native_body_excerpt(catalog, text, auth.section_id)
            failure = None
        except (ValueError, UnicodeError):
            failure = "native_body_integrity_error"
    return NativeBodyReadObservedV1(event_id=event_id, sequence=len(execution.events),
        authorization_event_id=auth.event_id, excerpt=excerpt, failure_code=failure)


