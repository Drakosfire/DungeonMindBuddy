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
from .native_source_display import source_display_metadata


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




def catalog(scope, principal):
    context, pin = _pinned(scope, principal)
    # The Core catalogue owns eligibility/visibility; no APP labels grant access.
    result = list_admitted_native_text_sources(context.access)
    navigation = source_display_metadata(result.sources, pin.managed_world_id)
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
    # Reuse the native acquisition selector over the body Core just verified.
    # Character offsets are Python Unicode code points, not JavaScript UTF-16.
    from application_state.agent_conversation.native_source_catalog import (
        SELECTOR, section_catalog,
    )
    sections = section_catalog(
        opened.body_text, source_artifact_id=opened.source_artifact_id,
        native_source_revision_id=opened.source_revision_id,
        content_sha256=opened.body_sha256,
    ) if opened.body_text.strip() else None
    # Core verifies the body and original evidence span; this is not an assertion claim.
    return _response(
        context,
        pin,
        schema="dmb_native_source_body_v1",
        source=opened.model_dump(mode="json"),
        section_catalog=None if sections is None else {"selector_policy": SELECTOR,
                         "sections": [row.model_dump(mode="json") for row in sections]},
    )

def published_recap(request, principal):
    world = request.managed_world_id
    binding = native.binding(world)
    repo = native.read_repository()
    head = repo.get_head(binding["native_world_id"])
    if head is None:
        raise SourceInspectionUnavailable("native_published_recap_head_unavailable")
    context, pin = _pinned(InspectionPin(
        managed_world_id=world,
        native_world_id=binding["native_world_id"],
        binding_version=binding["binding_version"],
        revision_id=head.head_revision_id,
    ), principal)
    catalogue = list_admitted_native_text_sources(context.access)
    if not catalogue.complete:
        raise SourceInspectionUnavailable("native_published_recap_catalog_incomplete")
    navigation = source_display_metadata(catalogue.sources, pin.managed_world_id)
    matches = [
        item for item, display in zip(catalogue.sources, navigation, strict=True)
        if display["kind"] == "recap"
        and display["status"] == "available"
        and display["origin_matches_current_metadata"] is True
        and display["campaign_id"] == request.campaign_id
        and display["session_id"] == request.session_id
    ]
    if len(matches) != 1:
        raise SourceInspectionUnavailable("native_published_recap_selection_unavailable")
    item = matches[0]
    for evidence_ref_id in sorted(item.evidence_ref_ids):
        opened = open_admitted_native_text(context.access, evidence_ref_id)
        if opened.status == "available":
            if native.binding(world) != binding:
                raise SourceInspectionUnavailable("native_published_recap_binding_changed")
            return _response(
                context, pin, schema="dmb_native_published_recap_v1",
                campaign_id=request.campaign_id, session_id=request.session_id,
                source=opened.model_dump(mode="json"),
            )
    raise SourceInspectionUnavailable("native_published_recap_source_unavailable")
