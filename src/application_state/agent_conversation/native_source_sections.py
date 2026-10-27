"""Selected excerpt receipts over an earlier immutable host body; no source IO."""
from hashlib import sha256
from time import perf_counter

from application_state.errors import ApplicationStateValidationError
from . import types as t
from .build_section import exact_saved_section
from .native_source_catalog import NativeSourceCatalogMaterial


def _existing(execution, event_id, cls, **identity):
    for event in execution.events:
        if event.event_id == event_id:
            if not isinstance(event, cls) or any(getattr(event, k) != v for k, v in identity.items()):
                raise ValueError("Native section event identity was reused with changed target")
            return event
    return None


def _provider(execution):
    latest = next((e for e in reversed(execution.events) if isinstance(e, t.ProviderAttemptAuthorizedEventV1)), None)
    outcomes = [e for e in execution.events if isinstance(e, t.ProviderOutcomeEventV1)
                and latest is not None and e.provider_attempt_id == latest.provider_attempt_id]
    if latest is None or not outcomes or outcomes[-1].outcome != "response_received":
        raise ValueError("Native section requires an acknowledged current provider")
    if isinstance(latest, t.PlanJevWriterAuthorizedV1):
        raise ValueError("Native acquisition cannot follow the final writer")
    return latest.provider_attempt_id


def authorize_section_locked(conn, turn, *, event_id, read_id, catalog_event_id, section_id):
    execution = turn.graph_context_execution
    try:
        prior = _existing(execution, event_id, t.NativeSourceSectionAuthorizedV1,
                          read_id=read_id, catalog_event_id=catalog_event_id)
        if prior is not None:
            if prior.section.section_id != section_id:
                raise ValueError("Native section retry changed its section")
            return prior
        t.validate_selected_source_binding(turn.graph_context_receipt, execution)
        provider = _provider(execution)
        catalog = next((e for e in execution.events if isinstance(e, t.NativeSourceCatalogObservedV1)
                        and e.event_id == catalog_event_id and e.outcome == "complete"), None)
        if catalog is None:
            raise ValueError("Native section requires an earlier complete catalog")
        section = next((s for s in catalog.sections if s.section_id == section_id), None)
        if section is None:
            raise ValueError("Native section is not a member of the catalog")
        if any(isinstance(e,t.NativeSourceSectionAuthorizedV1) and (e.read_id == read_id
                or (e.catalog_event_id == catalog_event_id and e.section.section_id == section_id)) for e in execution.events):
            raise ValueError("Native section already has an authorization; reuse its receipt")
        return t.NativeSourceSectionAuthorizedV1(kind="native_source_section_authorized_v1",
            event_id=event_id, sequence=len(execution.events), read_id=read_id, provider_attempt_id=provider,
            context_receipt_sha256=execution.context_receipt_sha256,
            execution_policy_sha256=execution.execution_policy_sha256,
            catalog_event_id=catalog_event_id, catalog_sha256=catalog.catalog_sha256,
            section=section, authorized_chars=section.char_end-section.char_start)
    except (ValueError, AttributeError) as exc:
        raise ApplicationStateValidationError(str(exc)) from exc


def materialize_section_locked(conn, turn, *, event_id, read_id, material):
    execution = turn.graph_context_execution
    try:
        prior = _existing(execution, event_id, t.NativeSourceSectionObservedV1, read_id=read_id)
        if prior is not None:
            return prior
        t.validate_selected_source_binding(turn.graph_context_receipt, execution)
        provider = _provider(execution)
        auth = next((e for e in execution.events if isinstance(e,t.NativeSourceSectionAuthorizedV1)
                     and e.read_id == read_id), None)
        if auth is None or auth.provider_attempt_id != provider:
            raise ValueError("Native section read lacks its current authorization")
        if any(isinstance(e,t.NativeSourceSectionObservedV1) and e.read_id == read_id for e in execution.events):
            raise ValueError("Native section already has a receipt; reuse it")
        catalog = next(e for e in execution.events if isinstance(e,t.NativeSourceCatalogObservedV1)
                       and e.event_id == auth.catalog_event_id)
    except (ValueError, AttributeError, StopIteration) as exc:
        raise ApplicationStateValidationError(str(exc)) from exc
    started = perf_counter()
    text, failure = None, None
    fresh_bytes, material_failure = 0, None
    nav = next(e for e in execution.events if isinstance(e, t.NativeSourceNavigationAuthorizedV1)
               and e.navigation_id == catalog.navigation_id)
    registry = isinstance(nav, t.NativeSourceNavigationAuthorizedV2)
    if material is None and registry:
        from .native_source_catalog import load_source_locked, section_catalog
        from .native_source_navigation import origin_artifact
        source, body, material_failure = load_source_locked(conn,
            source_artifact_id=catalog.source_artifact_id, digest=catalog.content_sha256,
            app_source_revision_id=catalog.app_source_revision_id, artifact=origin_artifact(nav), authority=turn.graph_context_receipt.graph_authority)
        fresh_bytes = len(source.markdown.encode('utf-8')) if source is not None else 0
        if (body is not None and source.source_revision_id == catalog.app_source_revision_id
                and t.canonical_sha256(source.lineage) == catalog.lineage_sha256
                and section_catalog(body, source_artifact_id=catalog.source_artifact_id,
                    native_source_revision_id=catalog.native_source_revision_id,
                    content_sha256=catalog.content_sha256) == catalog.sections):
            material = NativeSourceCatalogMaterial(catalog.navigation_id, catalog.event_id,
                source.source_revision_id, catalog.source_artifact_id,
                catalog.native_source_revision_id, catalog.content_sha256, body)
        elif material_failure is None:
            material_failure = 'source_material_mismatch'
    if material is None:
        failure = "source_material_unavailable"
    elif (not isinstance(material, NativeSourceCatalogMaterial)
            or material.navigation_id != catalog.navigation_id or material.catalog_event_id != catalog.event_id
            or material.app_source_revision_id != catalog.app_source_revision_id
            or material.source_artifact_id != catalog.source_artifact_id
            or material.native_source_revision_id != catalog.native_source_revision_id
            or material.content_sha256 != catalog.content_sha256 or not isinstance(material.markdown,str)):
        failure = "source_material_mismatch"
    else:
        try:
            exact = exact_saved_section(material.markdown, catalog.content_sha256,
                                       auth.section.line_start, auth.section.line_end)
            if (exact != material.markdown[auth.section.char_start:auth.section.char_end]
                    or len(exact) != auth.authorized_chars):
                raise ValueError("Native catalog character/line slice differs")
            if exact.strip(): text = exact
            else: failure = "empty_section"
        except (ValueError, TypeError, UnicodeError):
            failure = "source_material_mismatch"
    event_type = t.NativeSourceSectionObservedV2 if registry else t.NativeSourceSectionObservedV1
    extra = {'material_failure_code': material_failure} if registry else {}
    return event_type(kind="native_source_section_observed_v2" if registry else "native_source_section_observed_v1",
        event_id=event_id, sequence=len(execution.events), read_id=read_id,
        authorization_event_id=auth.event_id, catalog_event_id=catalog.event_id,
        source_artifact_id=catalog.source_artifact_id, native_source_revision_id=catalog.native_source_revision_id,
        app_source_revision_id=catalog.app_source_revision_id, content_sha256=catalog.content_sha256,
        section=auth.section, outcome="complete" if text is not None else "unavailable", failure_code=failure,
        text=text, excerpt_sha256=sha256(text.encode("utf-8")).hexdigest() if text is not None else None,
        returned_chars=len(text) if text is not None else 0, fresh_body_read_bytes=fresh_bytes, **extra,
        extraction_elapsed_ms=max(0,int((perf_counter()-started)*1000)))


def validate_section_events(execution):
    catalogs, auths, reads, targets = {}, {}, set(), set()
    provider, outcome = None, None
    for event in execution.events:
        if isinstance(event,t.ProviderAttemptAuthorizedEventV1):
            if set(auths) != reads:
                raise ValueError("Provider cannot proceed with unresolved native section reservations")
            provider, outcome = event.provider_attempt_id, None
        elif isinstance(event,t.ProviderOutcomeEventV1) and event.provider_attempt_id == provider:
            outcome = event.outcome
        elif isinstance(event,t.NativeSourceCatalogObservedV1):
            catalogs[event.event_id] = event
        elif isinstance(event,t.NativeSourceSectionAuthorizedV1):
            catalog = catalogs.get(event.catalog_event_id)
            target = (event.catalog_event_id,event.section.section_id)
            if (not isinstance(execution.policy,(t.PlanNativeSourceSectionsPolicyV1,t.PlayNativeSourceSectionsPolicyV1))
                    or provider != event.provider_attempt_id or outcome != "response_received"
                    or catalog is None or catalog.outcome != "complete"
                    or event.catalog_sha256 != catalog.catalog_sha256 or event.section not in catalog.sections
                    or event.read_id in auths or target in targets
                    or event.authorized_chars != event.section.char_end-event.section.char_start
                    or event.authorized_chars > execution.policy.max_chars_per_source_read
                    or event.context_receipt_sha256 != execution.context_receipt_sha256
                    or event.execution_policy_sha256 != execution.execution_policy_sha256):
                raise ValueError("Native section authorization differs from exact catalog/provider/budget")
            auths[event.read_id] = event
            targets.add(target)
        elif isinstance(event,t.NativeSourceSectionObservedV1):
            auth = auths.get(event.read_id)
            if auth is None or event.read_id in reads or event.authorization_event_id != auth.event_id:
                raise ValueError("Native section receipt requires one earlier unique authorization")
            catalog = catalogs[auth.catalog_event_id]
            if (provider != auth.provider_attempt_id or outcome != "response_received"
                    or event.catalog_event_id != auth.catalog_event_id or event.section != auth.section
                    or event.source_artifact_id != catalog.source_artifact_id
                    or event.native_source_revision_id != catalog.native_source_revision_id
                    or event.app_source_revision_id != catalog.app_source_revision_id
                    or event.content_sha256 != catalog.content_sha256
                    or event.returned_chars > auth.authorized_chars):
                raise ValueError("Native section receipt differs from its authorized source")
            if isinstance(event,t.NativeSourceSectionObservedV2):
                nav = next(e for e in execution.events if isinstance(e,t.NativeSourceNavigationAuthorizedV1)
                           and e.navigation_id == catalog.navigation_id)
                if (not isinstance(nav,t.NativeSourceNavigationAuthorizedV2)
                        or event.outcome == 'complete' and (event.material_failure_code is not None
                            or event.fresh_body_read_bytes not in {0,catalog.body_read_bytes})):
                    raise ValueError('Fresh registry read differs from its exact catalog/origin')
            reads.add(event.read_id)
