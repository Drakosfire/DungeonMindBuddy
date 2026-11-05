"""Human source inspection through the existing Core source owner, without a Graph gate."""

from fastapi.encoders import jsonable_encoder
from dungeonmind.application.vnext import (
    list_admitted_native_text_sources,
    open_admitted_native_text,
)
from apps.live_control_server.integrations.dungeonmind.native_corpus_source import (
    prepare_native_source_context,
)
from apps.live_control_server.integrations.dungeonmind import (
    native_registry_source as native,
)
from apps.live_control_server.models.native_graph_inspection import InspectionPin


class SourceInspectionUnavailable(ValueError):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


def _pinned(scope, principal):
    if scope.scope_mode != "world" or scope.campaign_id is not None:
        raise SourceInspectionUnavailable(
            "native_source_inspection_world_scope_required"
        )
    context = prepare_native_source_context(
        managed_world_id=scope.managed_world_id,
        principal=principal,
        revision_id=scope.revision_id if isinstance(scope, InspectionPin) else None,
        repository=native.read_repository(),
    )
    authority = context.authority
    pin = InspectionPin(
        managed_world_id=authority.managed_world_id,
        native_world_id=authority.native_world_id,
        binding_version=authority.binding_version,
        revision_id=authority.revision_id,
    )
    if isinstance(scope, InspectionPin) and scope != pin:
        raise SourceInspectionUnavailable("native_source_inspection_binding_changed")
    return context, pin


def _response(context, pin, **payload):
    if context.resolve_identity(pin.managed_world_id) != context.binding:
        raise SourceInspectionUnavailable("native_source_inspection_binding_changed")
    return {"scope": pin.model_dump(mode="json"), **payload}



def _navigation(items, world_id):
    """Producer display metadata only, after Core has authorized membership."""
    from application_state.source import service as sources
    from application_state.source.naming import registered_source_name
    from application_state.content import pages
    from application_state.errors import ApplicationStateError

    recap_namespace = "dungeonbuddy.app-recap-source.v1"
    page_namespace = "dungeonbuddy.workspace-document-registry"
    recaps = [item for item in items if item.origin and item.origin.namespace == recap_namespace]
    page_items = [item for item in items if item.origin and item.origin.namespace == page_namespace]
    revisions, page_records = {}, {}
    if recaps:
        try:
            revisions = {
                (row.source_artifact_id, str(row.source_revision_id)): row
                for row in sources.get_source_revision_metadata(
                    bindings=[(item.origin.object_id, item.source_revision.content_sha256)
                              for item in recaps], world_id=world_id,
                )
            }
        except ApplicationStateError:
            pass  # Native source reads remain independent; label coverage is explicit below.
    if page_items:
        try:
            page_records = {
                str(state.page.work_object_id): state.page
                for state in pages.page_inventory(world_id=world_id, status=None)
            }
        except ApplicationStateError:
            pass
    navigation = []
    for item in items:
        classification = item.source_artifact.source_classification
        kind = {"dungeonbuddy.source:session_recap": "recap",
                "dungeonbuddy.source:worldbuilding": "worldbuilding"}.get(classification, "other")
        row = dict(label=None, kind=kind, campaign_id=None, session_id=None,
                   status="unavailable", metadata_revision=None,
                   origin_matches_current_metadata=None)
        origin = item.origin
        if origin and origin.namespace == recap_namespace:
            meta = revisions.get((origin.object_id, origin.revision_id))
            if (meta is not None and meta.world_id == world_id
                    and meta.content_sha256 == item.source_revision.content_sha256):
                row.update(label=registered_source_name(meta.model_dump(mode="json")),
                           campaign_id=meta.campaign_id, session_id=meta.session_id,
                           metadata_revision=str(meta.source_revision_id),
                           origin_matches_current_metadata=True)
        elif origin and origin.namespace == page_namespace:
            page = page_records.get(origin.object_id)
            if page is not None and page.world_id == world_id:
                revision = f"registry-revision:{page.object_revision}"
                row.update(label=page.title.strip() or None, campaign_id=page.campaign_id,
                           metadata_revision=revision,
                           origin_matches_current_metadata=origin.revision_id == revision)
        if row["label"]:
            row["status"] = "available"
        navigation.append(row)
    return navigation

def catalog(scope, principal):
    context, pin = _pinned(scope, principal)
    # The Core catalogue owns eligibility/visibility; no APP labels grant access.
    result = list_admitted_native_text_sources(context.access)
    navigation = _navigation(result.sources, pin.managed_world_id)
    catalogue = jsonable_encoder(result)
    for item, display in zip(catalogue["sources"], navigation):
        item["navigation"] = display
    return _response(
        context, pin, schema="dmb_native_source_catalog_v1", catalogue=catalogue,
        navigation_complete=all(row["status"] == "available" for row in navigation),
    )


def inspect(request, principal):
    context, pin = _pinned(request.scope, principal)
    evidence = context.access.parsed.get_evidence(request.evidence_ref_id)
    if (
        evidence is None
        or evidence.source_artifact_id != request.source_artifact_id
        or evidence.source_revision_id != request.source_revision_id
    ):
        raise SourceInspectionUnavailable(
            "native_source_inspection_selection_unavailable"
        )
    opened = open_admitted_native_text(context.access, request.evidence_ref_id)
    if opened.status != "available":
        raise SourceInspectionUnavailable("native_source_inspection_source_unavailable")
    # Core verifies the body and original evidence span; this is not an assertion claim.
    return _response(
        context,
        pin,
        schema="dmb_native_source_body_v1",
        source=opened.model_dump(mode="json"),
    )
