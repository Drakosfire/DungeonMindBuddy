"""Faithful native inspection; Core owns admission, identity and source access."""

from dungeonmind.application.vnext import (
    EntityReadService,
    EvidenceReadService,
    open_admitted_native_text,
)
from dungeonmind.contracts.vnext.domain import Assertion
from fastapi.encoders import jsonable_encoder
from apps.live_control_server.integrations.dungeonmind import (
    native_registry_source as native,
)
from apps.live_control_server.models.native_graph_inspection import InspectionPin
from apps.live_control_server.services.agent_graph_auth import require_native_graph_gm


class InspectionUnavailable(ValueError):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


def _pinned(scope, principal):
    require_native_graph_gm(principal)
    bound = native.binding(scope.managed_world_id)
    repo = native.read_repository()
    space = bound["native_world_id"]
    if isinstance(scope, InspectionPin):
        if (scope.native_world_id, scope.binding_version) != (
            space,
            bound["binding_version"],
        ):
            raise InspectionUnavailable("native_inspection_binding_changed")
        revision = scope.revision_id
    else:
        head = repo.get_head(space)
        if head is None:
            raise InspectionUnavailable("native_inspection_head_unavailable")
        revision = head.head_revision_id
    read, access, _, _ = native.read_context(
        repo,
        space,
        revision,
        scope.campaign_id,
        principal.role,
        scope_mode=scope.scope_mode,
    )
    pin = InspectionPin(
        managed_world_id=scope.managed_world_id,
        native_world_id=space,
        binding_version=bound["binding_version"],
        revision_id=revision,
        scope_mode=scope.scope_mode,
        campaign_id=scope.campaign_id,
    )
    return bound, read, access, pin


def _response(bound, pin, **payload):
    if native.binding(pin.managed_world_id) != bound:
        raise InspectionUnavailable("native_inspection_binding_changed")
    return {"scope": pin.model_dump(mode="json"), **payload}


def catalog(scope, principal):
    bound, read, access, pin = _pinned(scope, principal)
    listing = EntityReadService().list_entities(read)
    # Only Core's admitted IDs from this same immutable context are serialized.
    assertions = [
        Assertion.model_validate(
            access.parsed.get_assertion(identity), from_attributes=True
        ).model_dump(mode="json")
        for identity in listing.admitted_assertion_ids
    ]
    return _response(
        bound,
        pin,
        schema="dmb_native_graph_catalog_v1",
        catalogue=jsonable_encoder(listing),
        assertions=assertions,
    )


def inspect(request, principal):
    bound, read, access, pin = _pinned(request.scope, principal)
    selection = request.selection
    if selection.kind == "entity":
        listing = EntityReadService().list_entities(read)
        if selection.entity_id not in {entity.entity_id for entity in listing.entities}:
            raise InspectionUnavailable("native_inspection_entity_unavailable")
        result = EntityReadService().get_complete_entity(read, selection.entity_id)
        return _response(
            bound,
            pin,
            schema="dmb_native_graph_entity_v1",
            entity=jsonable_encoder(result),
        )
    result = EvidenceReadService().get_assertion_evidence(read, selection.assertion_id)
    if not result.available or result.completeness.status != "complete":
        raise InspectionUnavailable("native_inspection_assertion_unavailable")
    if not any(
        e.evidence_ref_id == selection.evidence_ref_id and e.evidence_role == "support"
        for e in result.evidence
    ):
        raise InspectionUnavailable("native_inspection_evidence_unavailable")
    opened = open_admitted_native_text(access, selection.evidence_ref_id)
    if opened.status != "available":
        raise InspectionUnavailable("native_inspection_source_unavailable")
    # Core verifies the whole source; the caller receives only its selected span.
    span = opened.model_dump(mode="json", exclude={"body_text"})
    span["text"] = opened.body_text.encode("utf-8")[
        opened.span_start_byte : opened.span_end_byte
    ].decode("utf-8")
    return _response(bound, pin, schema="dmb_native_graph_source_v1", source=span)
