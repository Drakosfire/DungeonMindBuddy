"""Managed Build ownership → native Graph authority for manual authoring only."""
from dataclasses import dataclass
from types import SimpleNamespace


@dataclass(frozen=True)
class GraphReviewPublicationContext:
    world_id: str
    campaign_scope: str | None
    binding: dict | None = None

    def transport_artifact(self, artifact):
        if self.binding is None:
            return artifact
        data = artifact.model_dump() if hasattr(artifact, 'model_dump') else vars(artifact).copy()
        data.update(world_id=self.world_id, campaign_id=self.campaign_scope)
        return SimpleNamespace(**data)


def resolve_publication_context(request, resolved, *, source_root):
    from apps.live_control_server.services.graph_object_authoring_prepare import (
        GraphObjectAuthoringError, _buddy_source_artifact, authored_world_id,
    )
    from apps.live_control_server.services.managed_world_graph_projection import (
        resolve_managed_world_binding, WorldGraphProjectionServiceError,
    )
    from apps.live_control_server.services.workspace_document_registry import (
        get_workspace_document, WorkspaceDocumentRegistryError,
    )

    artifact = _buddy_source_artifact(resolved)
    managed = authored_world_id(request)
    if getattr(artifact, 'source_domain', None) != 'worldbuilding':
        return GraphReviewPublicationContext(managed, request.campaign_id)
    document_id = getattr(artifact, 'workspace_document_id', None)
    document_revision = getattr(artifact, 'workspace_document_revision', None)
    digest = getattr(artifact, 'content_sha256', None)
    if (request.world_id != managed or request.campaign_id != managed
            or getattr(artifact, 'world_id', None) != managed
            or getattr(artifact, 'campaign_id', None) not in (None, '', managed)
            or not document_id or not document_revision
            or getattr(resolved, 'source_domain', None) != 'worldbuilding'
            or getattr(resolved, 'session_id', None)
            or getattr(resolved, 'source_revision_id', None) != f'sha256:{digest}'):
        raise GraphObjectAuthoringError('An exact registered managed-World Build source is required.',
                                        code='world_binding_required', status_code=409)
    try:
        document = get_workspace_document(source_root, document_id)
        binding = resolve_managed_world_binding(managed)
    except (WorkspaceDocumentRegistryError, WorldGraphProjectionServiceError) as exc:
        unavailable = exc.status_code >= 500
        raise GraphObjectAuthoringError('Registered World/source binding is unavailable.',
            code='authority_unavailable' if unavailable else 'world_binding_required',
            status_code=503 if unavailable else 409) from exc
    if (document.kind != 'worldbuilding_source' or document.status != 'active'
            or document.world_id != managed or binding.managed_world_id != managed):
        raise GraphObjectAuthoringError('Registered source ownership changed.',
                                        code='world_binding_changed', status_code=409)
    return GraphReviewPublicationContext(binding.native_world_id, None, {
        'managed_world_id': managed, 'native_world_id': binding.native_world_id,
        'binding_version': binding.binding_version, 'document_id': document_id,
        'document_revision': document_revision, 'source_artifact_id': artifact.source_artifact_id,
        'source_sha256': digest,
    })
