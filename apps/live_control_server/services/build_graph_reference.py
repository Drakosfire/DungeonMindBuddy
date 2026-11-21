"""Read current native Graph identity before accepting typed Build placement."""

from __future__ import annotations

from hashlib import sha256

from application_state.agent_conversation.plan_authoring import strict_json
from application_state.build_proposal.graph_reference import BuildGraphReferencePlacement
from application_state.build_proposal.graph_reference_review import BuildGraphReferencePrepare, BuildGraphReferenceReview
from application_state.content.markdown_source_blocks import source_block_spans
from application_state.content.page_presentation import BlockBinding, PagePresentation, leading_yaml
from application_state.errors import ApplicationStateConflictError
from apps.live_control_server.config import managed_world_data_root
from apps.live_control_server.models.native_graph_inspection import InspectionPin, InspectionScope

from .agent_graph_auth import NativeGraphPrincipal
from .build_document_proposal import BuildComposeError, _source
from .native_graph_explorer import NativeGraphExplorerError, hosted_response_binding
from .native_graph_inspection import InspectionUnavailable, authoring_identities
from .workspace_document_registry import WorkspaceDocumentRegistryError, get_committed_page_snapshot


def require_current_build_graph_reference(
    placement: BuildGraphReferencePlacement, principal: NativeGraphPrincipal,
) -> None:
    reference = placement.reference
    try:
        with hosted_response_binding(principal, placement.basis.world_id):
            graph = authoring_identities(InspectionScope(managed_world_id=placement.basis.world_id), principal)
    except (InspectionUnavailable, NativeGraphExplorerError) as error:
        raise ApplicationStateConflictError("The current Graph identity is unavailable") from error
    expected = InspectionPin(
        managed_world_id=reference.managed_world_id,
        native_world_id=reference.native_world_id,
        binding_version=reference.binding_version,
        revision_id=reference.graph_revision,
    )
    if graph["scope"] != expected.model_dump(mode="json"):
        raise ApplicationStateConflictError("The selected Graph identity belongs to a different or changed Graph")
    matches = [row for row in graph["identities"] if row["node_id"] == reference.node_id]
    if (len(matches) != 1 or not matches[0]["selectable"]
            or matches[0]["kind"] != placement.entity_kind or matches[0]["label"] != reference.label):
        raise ApplicationStateConflictError("The selected Graph identity or classification changed")


def _ids(editor_json):
    return [block.get("attrs", {}).get("pageBlockId") for block in strict_json(editor_json)["content"]]


def _expected_layout(source, command, committed_markdown, prefix):
    before_ids = _ids(command.editor_json)
    if source.page_presentation is None:
        if any(before_ids):
            raise ApplicationStateConflictError("The captured Graph placement differs from the saved page identities")
        return None
    if (any(item.kind != "block" for item in source.page_presentation.items)
            or [item.id for item in source.page_presentation.items] != before_ids):
        raise ApplicationStateConflictError("The captured Graph placement differs from the saved page identities")
    offset = len(prefix.encode("utf-8"))
    encoded = committed_markdown.encode("utf-8")
    after_ids = _ids(command.after_editor_json)
    spans = source_block_spans(command.after_draft_markdown)
    bindings = [BlockBinding(
        id=identity, byte_start=start + offset, byte_end=end + offset,
        sha256=sha256(encoded[start + offset:end + offset]).hexdigest(),
    ) for identity, (start, end) in zip(after_ids, spans, strict=True)]
    return PagePresentation(markdown_sha256=sha256(encoded).hexdigest(), items=bindings).checked(
        committed_markdown,
    ).fingerprint()


def authorize_graph_reference_prepare(
    review: BuildGraphReferenceReview, command: BuildGraphReferencePrepare, principal: NativeGraphPrincipal,
) -> None:
    source = authorize_graph_reference_save(review, principal)
    prefix = leading_yaml(source.markdown)
    after_markdown = prefix + command.after_draft_markdown
    if (source.markdown[len(prefix):] != command.draft_markdown
            or sha256(after_markdown.encode("utf-8")).hexdigest() != command.apply.content_sha256):
        raise ApplicationStateConflictError("The Graph reference prepare differs from the exact saved source")
    if _expected_layout(source, command, after_markdown, prefix) != command.apply.presentation_sha256:
        raise ApplicationStateConflictError("The Graph reference prepare differs from the exact page identities")


def authorize_graph_reference_save(review: BuildGraphReferenceReview, principal: NativeGraphPrincipal):
    try:
        source = _source(review.placement)
    except (BuildComposeError, WorkspaceDocumentRegistryError) as error:
        raise ApplicationStateConflictError("The saved page changed before Graph reference placement") from error
    require_current_build_graph_reference(review.placement, principal)
    return source


def observe_graph_reference_save(review: BuildGraphReferenceReview) -> int:
    basis = review.placement.basis
    try:
        snapshot = get_committed_page_snapshot(managed_world_data_root(), basis.document_id)
    except WorkspaceDocumentRegistryError as error:
        raise ApplicationStateConflictError("The saved Graph reference page is unavailable") from error
    record = snapshot.record
    receipt = review.apply
    if (receipt is None or record.document_id != basis.document_id or record.world_id != basis.world_id
            or record.status != "active" or record.content_status != "committed"
            or record.kind != "worldbuilding_source" or record.source_domain != "worldbuilding"
            or record.visibility_state != basis.visibility or snapshot.loaded_revision != basis.registry_revision + 1
            or record.revision != snapshot.loaded_revision or snapshot.content_sha256 != receipt.content_sha256
            or sha256(snapshot.markdown.encode("utf-8")).hexdigest() != receipt.content_sha256
            or snapshot.page_presentation_sha256 != receipt.presentation_sha256):
        raise ApplicationStateConflictError("The saved Graph reference does not match the prepared insertion")
    return snapshot.loaded_revision
