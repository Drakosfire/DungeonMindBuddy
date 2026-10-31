"""Saved-page selection adapter; governed Graph prepare/commit remain the only writer."""
from __future__ import annotations

from pathlib import Path
from pydantic import BaseModel, ConfigDict, Field, model_validator

from apps.live_control_server.config import artifact_data_root
from .graph_document_source import GraphDocumentSource, resolve_graph_document_source
from .graph_object_authoring_prepare import GraphObjectAuthoringPrepareRequest, GraphObjectAuthoringError
from .workspace_document_registry import get_workspace_document_snapshot
from .managed_world_graph_projection import ManagedWorldGraphProjectionRequest, project_managed_world_graph


class RelationshipEndpoint(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    node_id: str | None
    label: str = Field(min_length=1)
    kind: str = Field(min_length=1)

    @model_validator(mode="after")
    def readable(self):
        if any(not value.strip() or value != value.strip() for value in (self.label, self.kind)) or self.node_id == "":
            raise ValueError("Choose a readable identity")
        return self


class DocumentRelationshipRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    world_id: str = Field(pattern=r"^[a-z0-9][a-z0-9_-]{0,62}$")
    document_source: GraphDocumentSource
    quote: str = Field(min_length=1)
    source: RelationshipEndpoint
    target: RelationshipEndpoint
    predicate: str = Field(min_length=1)
    label: str = Field(min_length=1)
    context: str = Field(min_length=1)


def relationship_request(root: Path, request: DocumentRelationshipRequest) -> GraphObjectAuthoringPrepareRequest:
    """Resolve one exact occurrence and deliberate identities, without publishing."""
    root = artifact_data_root(root)

    def refuse(message):
        raise GraphObjectAuthoringError(message, code="relationship_review_invalid", status_code=409)

    selector = request.document_source
    snapshot = get_workspace_document_snapshot(root, selector.document_id)
    if (snapshot.record.world_id != request.world_id or snapshot.record.campaign_id != request.world_id
            or snapshot.record.kind != "worldbuilding_source" or snapshot.record.status != "active"
            or not snapshot.file_exists or snapshot.loaded_revision != selector.revision
            or snapshot.content_sha256 != selector.content_sha256):
        refuse("The saved page changed or belongs to another World. Select the current saved passage again.")
    body = snapshot.markdown
    start = body.find(request.quote)
    if not request.quote.strip() or start < 0 or body.find(request.quote, start + 1) >= 0:
        refuse("Choose one exact, uniquely occurring saved passage.")
    if any(not value.strip() or value != value.strip() for value in (request.predicate, request.label, request.context)):
        refuse("Describe the relationship and its context before previewing.")
    if ((request.source.node_id and request.source.node_id == request.target.node_id)
            or not request.source.node_id and not request.target.node_id
            and request.source.label.casefold() == request.target.label.casefold()):
        refuse("Choose two different identities.")
    graph = project_managed_world_graph(ManagedWorldGraphProjectionRequest(
        schema="dmb_managed_world_graph_projection_request_v1", managedWorldId=request.world_id), root=root)
    nodes = graph.projection.nodes
    for endpoint in (request.source, request.target):
        if endpoint.node_id:
            matches = [n for n in nodes if n.node_id == endpoint.node_id]
            if len(matches) != 1 or matches[0].label != endpoint.label or matches[0].kind != endpoint.kind:
                refuse("A selected identity changed or is outside this World. Review its identity again.")
        elif any(endpoint.label.casefold() in {n.label.casefold(), *(a.casefold() for a in n.aliases or [])} for n in nodes):
            refuse("That name or alias already exists. Choose the existing World identity.")
    source = resolve_graph_document_source(root, selector, world_id=request.world_id, campaign_id=request.world_id)
    index = source.source_span_index
    first = body.count("\n", 0, start) + 1
    last = body.count("\n", 0, start + len(request.quote) - 1) + 1
    spans = [s for s in index["spans"] if s["start_line"] <= first and s["end_line"] >= last]
    if len(spans) != 1:
        refuse("Select a passage within one saved source block.")
    selection = {"selectionKind": "text_span", "selectedText": request.quote,
        "normalizedSelectedText": request.quote, "sourceSpanRefId": spans[0]["source_span_id"]}
    visibility = {"visibility": "gm_private", "revealState": "unrevealed"}
    shared = {"selection": selection, "visibility": visibility, "graphScopes": ["campaign_memory_graph"],
        "status": "staged_local", "provenancePreview": {"operatorNote": "Explicit saved-page relationship review"}}
    proposals = []
    def ref(endpoint, key):
        if endpoint.node_id:
            return {"refKind": "existing_graph_node", "nodeId": endpoint.node_id, "label": endpoint.label, "kind": endpoint.kind}
        proposals.append({**shared, "localProposalId": key, "proposalKind": "object",
            "objectRef": {"label": endpoint.label, "kind": endpoint.kind, "aliases": [], "summary": ""}})
        return {"refKind": "local_proposal", "localProposalId": key, "label": endpoint.label, "kind": endpoint.kind}
    from_ref, to_ref = ref(request.source, "source"), ref(request.target, "target")
    proposals.append({**shared, "localProposalId": "relationship", "proposalKind": "relationship",
        "sourceObjectRef": from_ref, "targetObjectRef": to_ref, "relationshipType": request.predicate,
        # The existing native writer retains labels and source evidence, not the
        # proposal summary. Keep reviewed temporal context in its durable label.
        "relationshipLabel": request.label + " — " + request.context, "summary": request.context, "direction": "directed"})
    return GraphObjectAuthoringPrepareRequest(worldId=request.world_id, campaignId=request.world_id,
        documentSource=selector, proposals=proposals)
