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
from apps.live_control_server.integrations.dungeonmind.world_graph_reads import direct_services_from_config
from apps.live_control_server.integrations.dungeonmind.source_origin import verify_native_source_origin
from dungeonmind.contracts.projection_v2 import WorldGraphProjectionRequestV2
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
        if isinstance(nav, t.NativeSourceNavigationAuthorizedV2):
            from apps.live_control_server.integrations.dungeonmind.corpus_source_inventory import verify_registry_source_origin
            current = verify_registry_source_origin(direct_services_from_config(authority.native_world_id),
                native_world_id=authority.native_world_id, proof=original)
        else:
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
