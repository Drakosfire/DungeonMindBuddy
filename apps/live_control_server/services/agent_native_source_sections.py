"""Authenticated completion selector → fresh native access → exact immutable bytes."""
from hashlib import sha256
from uuid import UUID

from application_state.agent_conversation import AgentConversationService
from application_state.agent_conversation import types as t
from application_state.agent_conversation.rules_authority_reads import MixedCompletedTurnV1
from application_state.agent_conversation.native_source_navigation import origin_payload, origin_artifact
from application_state.agent_conversation.native_source_scope import source_scope_matches, SCOPE_FIELDS
from application_state.agent_conversation.build_section import exact_saved_section
from application_state.source.service import get_source_markdown, get_source_artifact_scope
from apps.live_control_server.services.managed_world_graph_projection import resolve_managed_world_binding
from .agent_source_passages import SourcePassageOpenError


def open_native_source_section(*, world_id: str, turn_id: UUID, citation_index: int, service=None):
    if isinstance(citation_index,bool) or not isinstance(citation_index,int) or not 0 <= citation_index <= 16383:
        raise SourcePassageOpenError('source_section_selector_invalid',422)
    turn = (service or AgentConversationService()).inspect_turn(world_id=world_id,turn_id=turn_id)
    if isinstance(turn,MixedCompletedTurnV1):
        if turn.base_projection.kind != 'approved':
            raise SourcePassageOpenError('source_section_completion_unavailable',404)
        turn = turn.base_projection.turn
    if (turn.world_id != world_id or turn.turn_id != turn_id or turn.status != 'completed'
            or not isinstance(turn.completion,t.SurfaceEvidenceCompletionV3)):
        raise SourcePassageOpenError('source_section_completion_unavailable',404)
    if citation_index >= len(turn.completion.native_source_citations):
        raise SourcePassageOpenError('source_section_not_found',404)
    citation = turn.completion.native_source_citations[citation_index]
    execution = turn.graph_context_execution
    authority = turn.graph_context_receipt.graph_authority
    catalog = next(e for e in execution.events if isinstance(e,t.NativeSourceCatalogObservedV1)
        and e.event_id == citation.catalog_event_id)
    nav = next(e for e in execution.events if isinstance(e,t.NativeSourceNavigationAuthorizedV1)
        and e.navigation_id == catalog.navigation_id)
    original,donor,pin = origin_payload(nav)
    try:
        binding = resolve_managed_world_binding(world_id)
        if (binding.managed_world_id != world_id or binding.native_world_id != authority.native_world_id
                or binding.binding_version != authority.binding_version):
            raise ValueError('Managed World binding changed')
        from apps.live_control_server.integrations.dungeonmind.world_graph_reads import direct_services_from_config

        if isinstance(nav, t.NativeSourceNavigationAuthorizedV2):
            from apps.live_control_server.integrations.dungeonmind.corpus_source_inventory import verify_registry_source_origin
            current = verify_registry_source_origin(direct_services_from_config(authority.native_world_id),
                native_world_id=authority.native_world_id, proof=original)
        else:
            from dungeonmind.contracts.projection_v2 import WorldGraphProjectionRequestV2

            from apps.live_control_server.integrations.dungeonmind.source_origin import verify_native_source_origin

            current = verify_native_source_origin(direct_services_from_config(authority.native_world_id),
                projection=WorldGraphProjectionRequestV2.model_validate(original['projection']),donor=donor,pin=pin)
        if (current.source_artifact_id != citation.source_artifact_id
                or current.native_source_revision_id != citation.native_source_revision_id
                or current.content_sha256 != citation.content_sha256):
            raise ValueError('Native source identity changed')
    except Exception as exc:
        # Denial or an unavailable access authority never reaches body storage.
        raise SourcePassageOpenError('source_section_access_unavailable') from exc
    try:
        artifact = origin_artifact(nav)
        scope = get_source_artifact_scope(source_artifact_id=citation.source_artifact_id)
        if scope is None or not source_scope_matches(scope, artifact, authority):
            raise ValueError("Immutable source ownership unavailable")
        source = get_source_markdown(source_artifact_id=citation.source_artifact_id,
            content_sha256=citation.content_sha256,source_revision_id=citation.app_source_revision_id)
        if (source is None or source.source_revision_id != citation.app_source_revision_id
                or source.source_artifact_id != citation.source_artifact_id
                or not source_scope_matches(source.model_dump(include=SCOPE_FIELDS),artifact,authority)
                or source.content_sha256 != citation.content_sha256 or source.media_type != 'text/markdown'
                or source.encoding.lower() != 'utf-8'):
            raise ValueError('Immutable source identity unavailable')
        ref = artifact.get('workspace_document_ref')
        if ref and (source.lineage.get('workspace_document_id') != ref['document_id']
                or source.lineage.get('workspace_document_revision') != ref['revision']):
            raise ValueError('Immutable source lineage changed')
        text = exact_saved_section(source.markdown,citation.content_sha256,citation.line_start,citation.line_end)
        if sha256(text.encode()).hexdigest() != citation.excerpt_sha256:
            raise ValueError('Exact source section changed')
    except Exception as exc:
        raise SourcePassageOpenError('source_section_bytes_unavailable') from exc
    from apps.live_control_server.models.agent_turn import AgentNativeSourceSectionReadResponseV1
    return AgentNativeSourceSectionReadResponseV1(world_id=world_id,turn_id=turn_id,
        citation_index=citation_index,citation=citation,content=text)


def open_native_body_excerpt(*, world_id, turn_id, citation_index, principal, service=None,
                             repository=None, resolve_identity=None):
    """Reopen the original body extent through fresh Core access, never trace text."""
    if principal is None or principal.role != 'gm':
        raise SourcePassageOpenError('native_body_access_denied', 403)
    if isinstance(citation_index, bool) or not isinstance(citation_index, int) or not 0 <= citation_index <= 16383:
        raise SourcePassageOpenError('native_body_selector_invalid', 422)
    turn = (service or AgentConversationService()).inspect_turn(world_id=world_id, turn_id=turn_id)
    if isinstance(turn, MixedCompletedTurnV1):
        if turn.base_projection.kind != 'approved':
            raise SourcePassageOpenError('native_body_completion_unavailable', 404)
        turn = turn.base_projection.turn
    from application_state.agent_conversation.native_completion import SurfaceNativeCompletionV1
    from application_state.agent_conversation.native_context import BuildPendingContextReceiptV1
    from application_state.agent_conversation.native_execution import BuildPendingExecutionV1
    pending = (type(turn.graph_context_receipt) is BuildPendingContextReceiptV1
        and type(turn.graph_context_execution) is BuildPendingExecutionV1
        and type(turn.completion) is SurfaceNativeCompletionV1)
    shared = (type(turn.graph_context_receipt) is t.SurfaceNativeContextReceiptV1
        and type(turn.completion) is SurfaceNativeCompletionV1)
    legacy = (isinstance(turn.graph_context_receipt, t.PlanSourceContextReceiptV1)
        and isinstance(turn.completion, t.SurfaceEvidenceCompletionV5))
    play = (isinstance(turn.graph_context_receipt, t.PlayWorldGraphContextReceiptV1)
        and turn.graph_context_receipt.authored_source_context is not None
        and isinstance(turn.completion, t.SurfaceEvidenceCompletionV5)
        and turn.completion.surface_id == 'play')
    if (turn.world_id != world_id or turn.turn_id != turn_id or turn.status != 'completed'
            or not (shared or pending or legacy or play)):
        raise SourcePassageOpenError('native_body_completion_unavailable', 404)
    pending_source = None
    if pending:
        try:
            from application_state.agent_conversation.build_source_free import effective_pending_source
            pending_source = effective_pending_source(turn.graph_context_receipt, turn.graph_context_execution)
        except (ValueError, TypeError, KeyError, AttributeError) as exc:
            raise SourcePassageOpenError('native_body_access_unavailable', 409) from exc
    if citation_index >= len(turn.completion.native_body_citations):
        raise SourcePassageOpenError('native_body_not_found', 404)
    citation = turn.completion.native_body_citations[citation_index]
    if citation.prior_reference is not None:
        from application_state.agent_conversation.native_corpus import prior_body_writer_supports, resolve_prior_body_citation
        reference = citation.prior_reference
        support = next((item for item in prior_body_writer_supports(turn.graph_context_execution)
            if item.support.reference == reference), None)
        app = service or AgentConversationService()
        try:
            if support is None:
                raise ValueError("Carried citation lacks its retained admission")
            original = app.inspect_turn(world_id=world_id, turn_id=reference.turn_id)
            claim, passage = resolve_prior_body_citation(turn, original, reference,
                history_turn_ids={reference.turn_id})
            if (claim, passage) != (support.support.claim_text, support.support.passage):
                raise ValueError("Carried citation differs from the original completion")
            opened = open_native_body_excerpt(world_id=world_id, turn_id=reference.turn_id,
                citation_index=reference.citation_index, principal=principal, service=app,
                repository=repository, resolve_identity=resolve_identity)
            if opened.citation != support.support.original_citation or opened.content != passage:
                raise ValueError("Carried citation differs from the reopened original extent")
        except Exception as exc:
            raise SourcePassageOpenError('native_body_access_unavailable', 409) from exc
        return opened.model_copy(update=dict(turn_id=turn_id, citation_index=citation_index, citation=citation))

    from application_state.agent_conversation.native_corpus import resolve_retained_body_citation
    from ..integrations.dungeonmind.native_corpus_source import (
        prepare_native_source_context, read_native_corpus_member,
    )
    try:
        catalog, section, expected_text = resolve_retained_body_citation(
            turn.graph_context_execution, citation,
        )
        from application_state.agent_conversation.retained_conversation import native_supports
        retained = [support for support in native_supports(turn.graph_context_execution)
                    if support.read.event_id == citation.read_event_id]
        if retained:
            if len(retained) != 1 or retained[0].catalog != catalog:
                raise ValueError('Retained citation has ambiguous original authority')
            authority = catalog.authority
        elif pending:
            if pending_source is None:
                raise ValueError('Pending citation lacks its settled source authority')
            authority = pending_source[0]
        else:
            authority = (turn.graph_context_receipt.authored_source_context.authority
                if play else turn.graph_context_receipt.source_authority)
        prepared = prepare_native_source_context(managed_world_id=authority.managed_world_id,
            principal=principal, revision_id=authority.revision_id, repository=repository,
            resolve_identity=resolve_identity)
        body = read_native_corpus_member(authority=authority,
            member=catalog.source, principal=principal, prepared=prepared)
        if body is None:
            raise ValueError('Historical native body is unavailable')
        text = body[section.char_start:section.char_end]
        if (text != expected_text
                or body.encode()[section.byte_start:section.byte_end] != text.encode()):
            raise ValueError('Historical native body extent changed')
    except Exception as exc:
        raise SourcePassageOpenError('native_body_access_unavailable', 409) from exc
    from .native_source_display import opened_source_display_label
    from apps.live_control_server.models.agent_turn import AgentNativeBodyExcerptReadResponseV2
    return AgentNativeBodyExcerptReadResponseV2(world_id=world_id, turn_id=turn_id,
        citation_index=citation_index, citation=citation, content=text,
        display_label=opened_source_display_label(prepared, catalog.source))
