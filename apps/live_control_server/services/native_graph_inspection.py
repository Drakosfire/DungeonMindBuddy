"""Faithful native inspection; Core owns admission, identity and source access."""

from base64 import b64encode

from dungeonmind.application.vnext import (
    EntityReadService,
    EvidenceReadService,
    open_admitted_native_text,
    open_native_text_source_access_context,
)
from apps.live_control_server.integrations.dungeonmind.native_world_source_admission import _repository
from fastapi.encoders import jsonable_encoder
from apps.live_control_server.services.native_pdf_evidence import open_admitted_pdf_evidence, render_admitted_pdf_evidence
from apps.live_control_server.services.build_pdf_region_render import read_region_text
from apps.live_control_server.integrations.dungeonmind import (
    native_registry_source as native,
)
from apps.live_control_server.models.native_graph_inspection import Closed, InspectionPin
from apps.live_control_server.models.world_graph_object_projection import WorldGraphObjectProjectionRequest
from apps.live_control_server.integrations.dungeonmind.vnext_complete_object import (
    DungeonBuddyVNextReadIdentity,
    VNextCompleteObjectProjectionError,
    project_complete_world_object_vnext,
    world_object_display_values,
)
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
    read, access, _, profile = native.read_context(
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
    return bound, read, access, pin, profile


def _response(bound, pin, **payload):
    if native.binding(pin.managed_world_id) != bound:
        raise InspectionUnavailable("native_inspection_binding_changed")
    return {"scope": pin.model_dump(mode="json"), **payload}


def catalog(scope, principal):
    response, _ = catalog_with_profile(scope, principal)
    return response


def catalog_with_profile(scope, principal):
    bound, read, access, pin, profile = _pinned(scope, principal)
    listing = EntityReadService().list_entities(read)
    # Only Core's admitted IDs from this same immutable context are serialized.
    assertions = [
        native.assertion_contract(access.parsed.get_assertion(identity)).model_dump(mode="json")
        for identity in listing.admitted_assertion_ids
    ]
    response = _response(
        bound,
        pin,
        schema="dmb_native_graph_catalog_v1",
        catalogue=jsonable_encoder(listing),
        assertions=assertions,
    )
    return response, profile


def authoring_identities(scope, principal):
    """Read authorized identity fields at one binding and graph revision."""
    bound, read, _, pin, _ = _pinned(scope, principal)
    service = EntityReadService()
    listing, admitted_aliases = service.list_entities_with_aliases(read)
    if listing.completeness.status != "complete":
        raise InspectionUnavailable("native_authoring_identities_partial")

    assertions_by_entity = {}
    for assertion_id in listing.admitted_assertion_ids:
        assertion = read.parsed.get_assertion(assertion_id)
        assertions_by_entity.setdefault(assertion.subject_entity_id, []).append(assertion)
    aliases_by_entity = {}
    for alias in admitted_aliases:
        aliases_by_entity.setdefault(alias.entity_id, []).append(alias.alias_text)

    identities = []
    for entity in listing.entities:
        entity_id = entity.entity_id
        assertions = tuple(assertions_by_entity.get(entity_id, ()))
        aliases = aliases_by_entity.get(entity_id, [])
        try:
            label, kind, summary = world_object_display_values(assertions, entity_id)
            selectable = True
        except VNextCompleteObjectProjectionError:
            label, kind, summary = f"Unresolved identity · {entity_id}", "entity", None
            selectable = False
            names = set()
            for assertion in assertions:
                if assertion.subject_entity_id == entity_id and assertion.predicate == "dnd5e:name":
                    value = getattr(assertion.value, "value", None)
                    if isinstance(value, str):
                        names.add(value)
            aliases.extend(sorted(names.difference(aliases)))
        identities.append({
            "node_id": entity_id,
            "label": label,
            "kind": kind,
            "role": kind,
            "summary": summary,
            "aliases": aliases,
            "selectable": selectable,
        })
    return _response(bound, pin, identities=identities)


def inspect(request, principal):
    bound, read, access, pin, _ = _pinned(request.scope, principal)
    selection = request.selection
    if selection.kind == "neighborhood":
        from graph_memory.retrieval.models import WorldGraphRetrievalBounds
        from apps.live_control_server.integrations.dungeonmind.vnext_neighborhood import (
            map_nodes, map_relationships, read_neighborhood,
        )

        result, bounded = read_neighborhood(
            read, selection.seed_node_ids, selection.max_depth,
            WorldGraphRetrievalBounds(
                maxNodes=selection.max_nodes,
                maxRelationships=selection.max_relationships,
            ),
        )
        return _response(
            bound, pin, schema="dmb_native_graph_neighborhood_v1",
            node_ids=bounded.node_ids,
            nodes=[node.model_dump(mode="json", by_alias=True) for node in map_nodes(read, bounded)],
            missing_seed_node_ids=result.missing_seed_entity_ids,
            relationships=[edge.model_dump(mode="json", by_alias=True)
                           for edge in map_relationships(read, result, bounded)],
            nodes_truncated=bounded.nodes_truncated,
            relationships_truncated=bounded.relationships_truncated,
        )
    if selection.kind == "chronology":
        listing = EntityReadService().list_entities(read)
        admitted = [
            access.parsed.get_assertion(identity)
            for identity in listing.admitted_assertion_ids
        ]
        event_ids = set()
        for parsed in admitted:
            if parsed.predicate != "dnd5e:classification":
                continue
            value = native.assertion_contract(parsed).value
            if value.kind == "term_ref" and value.term in {"dnd5e:event", "dungeonbuddy:event"}:
                event_ids.add(parsed.subject_entity_id)
        assertions = []
        for parsed in admitted:
            if parsed.subject_entity_id not in event_ids:
                continue
            assertion = native.assertion_contract(parsed)
            if parsed.predicate == "dungeonbuddy.custom:on_timeline" or assertion.metadata.temporal_scope is not None:
                assertions.append(assertion.model_dump(mode="json"))
        return _response(
            bound, pin, schema="dmb_native_graph_chronology_v1",
            assertions=assertions,
            completeness=jsonable_encoder(listing.completeness),
        )
    if selection.kind == "entity":
        listing = EntityReadService().list_entities(read)
        if selection.entity_id not in {entity.entity_id for entity in listing.entities}:
            raise InspectionUnavailable("native_inspection_entity_unavailable")
        result = EntityReadService().get_complete_entity(read, selection.entity_id)
        return _response(
            bound,
            pin,
            schema="dmb_native_graph_entity_v1",
            entity=jsonable_encoder(result, sqlalchemy_safe=False),
        )
    result = EvidenceReadService().get_assertion_evidence(read, selection.assertion_id)
    if not result.available or result.completeness.status != "complete":
        raise InspectionUnavailable("native_inspection_assertion_unavailable")
    if not any(
        e.evidence_ref_id == selection.evidence_ref_id and e.evidence_role == "support"
        for e in result.evidence
    ):
        raise InspectionUnavailable("native_inspection_evidence_unavailable")
    evidence = access.parsed.get_evidence(selection.evidence_ref_id)
    if evidence is not None and evidence.evidence_ref_id.startswith("pdf-region:"):
        try:
            region, image = render_admitted_pdf_evidence(
                evidence, space_id=pin.native_world_id, load=_repository().get_native_pdf_source,
            )
        except ValueError as exc:
            raise InspectionUnavailable("native_inspection_source_unavailable") from exc
        return _response(
            bound, pin, schema="dmb_native_graph_pdf_region_v1",
            evidence_ref_id=evidence.evidence_ref_id,
            region=region.model_dump(mode="json"),
            png_base64=b64encode(image).decode("ascii"),
        )
    opened = open_admitted_native_text(access, selection.evidence_ref_id)
    if opened.status != "available":
        raise InspectionUnavailable("native_inspection_source_unavailable")
    # Core verifies the whole source; the caller receives only its selected span.
    span = opened.model_dump(mode="json", exclude={"body_text"})
    span["text"] = opened.body_text.encode("utf-8")[
        opened.span_start_byte : opened.span_end_byte
    ].decode("utf-8")
    return _response(bound, pin, schema="dmb_native_graph_source_v1", source=span)


def statblock_pdf_support(reference, regions, principal):
    """Resolve reviewed crops through the referenced creature's admitted assertions."""
    scope = InspectionPin(
        managed_world_id=reference.managed_world_id,
        native_world_id=reference.native_world_id,
        binding_version=reference.binding_version,
        revision_id=reference.graph_revision,
    )
    bound, read, access, pin, _ = _pinned(scope, principal)
    entity = EntityReadService().get_complete_entity(read, reference.node_id)
    if not entity.found or entity.completeness.status != "complete":
        return _response(bound, pin, support=[])
    support = {}
    for assertion in entity.assertions:
        if assertion.subject_entity_id != reference.node_id:
            continue
        result = EvidenceReadService().get_assertion_evidence(read, assertion.assertion_id)
        if not result.available or result.completeness.status != "complete":
            continue
        for item in result.evidence:
            ref_id = item.evidence_ref_id
            if item.evidence_role != "support" or not ref_id.startswith("pdf-region:") or ref_id in support:
                continue
            evidence = access.parsed.get_evidence(ref_id)
            if evidence is None:
                continue
            try:
                region, pdf = open_admitted_pdf_evidence(
                    evidence, space_id=pin.native_world_id, load=_repository().get_native_pdf_source,
                )
            except ValueError:
                continue
            if region in regions:
                support[ref_id] = {
                    "assertion_id": assertion.assertion_id,
                    "evidence_ref_id": ref_id,
                    "text": read_region_text(pdf, region),
                }
    return _response(bound, pin, support=list(support.values()))


class NativeCompleteObjectRead(Closed):
    scope: InspectionPin | None = None
    request: WorldGraphObjectProjectionRequest


def complete_object(body: NativeCompleteObjectRead, principal):
    scope, request = body.scope, body.request
    if request.admissibility != principal.role:
        raise InspectionUnavailable("native_complete_object_scope_mismatch")
    if scope is not None and (
        request.world_id != scope.managed_world_id
        or request.scope_mode != scope.scope_mode
        or (scope.campaign_id is not None and request.campaign_id != scope.campaign_id)
        or request.revision_pin != scope.revision_id
    ):
        raise InspectionUnavailable("native_complete_object_scope_mismatch")
    require_native_graph_gm(principal)
    bound = native.binding(request.world_id)
    space = bound["native_world_id"]
    version = bound["binding_version"]
    if scope is not None and (scope.native_world_id, scope.binding_version) != (space, version):
        raise InspectionUnavailable("native_inspection_binding_changed")
    repo = native.read_repository()
    head = repo.get_head(space)
    if head is None:
        raise InspectionUnavailable("native_inspection_head_unavailable")
    pin = scope or InspectionPin(
        managed_world_id=request.world_id,
        native_world_id=space,
        binding_version=version,
        revision_id=request.revision_pin or head.head_revision_id,
        scope_mode=request.scope_mode,
        campaign_id=request.campaign_id if request.scope_mode == "campaign" else None,
    )
    def resolve_domain(domain_ref, profile_ref):
        domain, _ = native.resolve_dungeonbuddy_descriptors(
            domain_ref=domain_ref, profile_ref=profile_ref,
        )
        return domain

    access = open_native_text_source_access_context(
        repository=repo, space_id=pin.native_world_id, revision_id=pin.revision_id,
        domain_contract=resolve_domain, audience_labels=(native.GM_LABEL, native.PLAYER_LABEL),
    )
    result = project_complete_world_object_vnext(
        parsed_revision=access.parsed,
        source_reader=access.source_view,
        request=request.model_copy(update={"world_id": pin.native_world_id}),
        read_identity=DungeonBuddyVNextReadIdentity(
            space_id=pin.native_world_id,
            revision_id=pin.revision_id,
            head_revision_id=head.head_revision_id,
            is_head=pin.revision_id == head.head_revision_id,
        ),
    )
    from apps.live_control_server.models.world_graph_object_projection import (
        object_projection_semantic_fingerprint,
    )

    for binding in result.source_bindings:
        if binding.provenance_status != "span_unresolvable":
            continue
        opened = open_admitted_native_text(access, binding.evidence_ref_id)
        if opened.status != "available":
            continue
        binding.excerpt = opened.body_text.encode("utf-8")[
            opened.span_start_byte : opened.span_end_byte
        ].decode("utf-8")
        binding.provenance_status = "excerpt_ready"
        result.telemetry.excerpt_count += 1
    if result.telemetry.excerpt_count:
        from apps.live_control_server.services.world_graph_object_projection import (
            hydrate_adjacency_excerpts,
        )

        bindings_by_evidence = {
            binding.evidence_ref_id: binding for binding in result.source_bindings
        }
        result.node = hydrate_adjacency_excerpts(
            result.node, bindings_by_evidence=bindings_by_evidence
        )
        result.related_nodes = [
            hydrate_adjacency_excerpts(node, bindings_by_evidence=bindings_by_evidence)
            for node in result.related_nodes
        ]
        result.semantic_fingerprint = object_projection_semantic_fingerprint(
            revision_id=pin.revision_id,
            node_id=request.node_id,
            admissibility=request.admissibility,
            assertions=result.assertions,
            relationships=result.relationships,
            related_node_ids=[node.node_id for node in result.related_nodes],
            source_bindings=result.source_bindings,
        )
    if native.binding(pin.managed_world_id) != bound:
        raise InspectionUnavailable("native_inspection_binding_changed")
    return result.model_dump(mode="json", by_alias=True)


def open_neighborhood_anchor(request, principal):
    from graph_memory.retrieval.models import WorldGraphSourceAnchorReadResult
    from apps.live_control_server.integrations.dungeonmind.vnext_neighborhood import native_anchor_selection
    from apps.live_control_server.models.native_graph_inspection import InspectionRead

    require_native_graph_gm(principal)
    bound = native.binding(request.world_id)
    result = WorldGraphSourceAnchorReadResult(outcome="empty", anchor_id=request.anchor_id)
    if request.revision_pin is None:
        return result
    try:
        assertion_id, evidence_ref_id = native_anchor_selection(request.anchor_id)
    except ValueError:
        return result
    if request.admissibility != principal.role:
        return result
    pin = InspectionPin(
        managed_world_id=request.world_id,
        native_world_id=bound["native_world_id"],
        binding_version=bound["binding_version"],
        revision_id=request.revision_pin,
        scope_mode=request.scope_mode,
        campaign_id=request.campaign_id if request.scope_mode == "campaign" else None,
    )
    packet = inspect(InspectionRead(
        scope=pin,
        selection={"kind": "source", "assertion_id": assertion_id, "evidence_ref_id": evidence_ref_id},
    ), principal)
    source = packet.get("source")
    if source is None or native.binding(request.world_id) != bound:
        return result
    excerpt = source["text"]
    return WorldGraphSourceAnchorReadResult(
        outcome="enough", anchor_id=request.anchor_id, evidence_ref_id=evidence_ref_id,
        source_artifact_id=source["source_artifact_id"], locator_kind="source_span",
        media_type="text/plain", content=excerpt[:request.max_chars],
        content_sha256=source["body_sha256"], truncated=len(excerpt) > request.max_chars,
    )


def shared_neighborhood(request, principal):
    from graph_memory.retrieval.models import (
        WorldGraphRetrievalCoverage,
        WorldGraphRetrievalResult,
        WorldGraphRetrievalSnapshot,
        WorldGraphSourceAnchor,
    )
    from apps.live_control_server.integrations.dungeonmind.vnext_neighborhood import native_anchor_id

    require_native_graph_gm(principal)
    if request.admissibility != principal.role:
        raise InspectionUnavailable("native_neighborhood_scope_mismatch")
    bound = native.binding(request.world_id)
    head = native.read_repository().get_head(bound["native_world_id"])
    if head is None:
        raise InspectionUnavailable("native_inspection_head_unavailable")
    pin = InspectionPin(
        managed_world_id=request.world_id,
        native_world_id=bound["native_world_id"],
        binding_version=bound["binding_version"],
        revision_id=request.revision_pin or head.head_revision_id,
        scope_mode=request.scope_mode,
        campaign_id=request.campaign_id if request.scope_mode == "campaign" else None,
    )
    from apps.live_control_server.integrations.dungeonmind.vnext_neighborhood import (
        map_nodes, map_relationships, read_neighborhood,
    )
    _, read, _, _, _ = _pinned(pin, principal)
    result, bounded = read_neighborhood(
        read, request.seed_node_ids, request.max_depth, request.bounds
    )
    nodes = map_nodes(read, bounded)
    edges = map_relationships(read, result, bounded)
    evidence = {row.evidence_ref_id: row for row in result.evidence}
    artifacts = {row.source_artifact_id: row for row in result.source_artifacts}
    from apps.live_control_server.integrations.dungeonmind.vnext_complete_object import _source_domain

    anchors = []
    for edge in edges:
        for evidence_id in edge.evidence_ref_ids:
            ref = evidence[evidence_id]
            if ref.evidence_role != "support" or not ref.source_span_ref_id:
                continue
            artifact = artifacts[ref.source_artifact_id]
            anchors.append(WorldGraphSourceAnchor(
                anchor_id=native_anchor_id(edge.edge_id, evidence_id),
                revision_id=pin.revision_id,
                evidence_ref_id=evidence_id,
                source_artifact_id=ref.source_artifact_id,
                source_domain=_source_domain(artifact.source_classification),
                source_span_ref_id=ref.source_span_ref_id,
                supporting_graph_object_ids=[edge.source_node_id, edge.target_node_id],
                supporting_assertion_ids=[edge.edge_id],
                readable=ref.can_open_source, locator_kind="source_span",
            ))
    _response(bound, pin)
    truncated = [
        field for field in ("nodes", "relationships") if getattr(bounded, f"{field}_truncated")
    ]
    if len(anchors) > request.bounds.max_source_anchors:
        truncated.append("source_anchors")
    missing = list(result.missing_seed_entity_ids)
    return WorldGraphRetrievalResult(
        operation="neighborhood",
        outcome="partial" if truncated or missing else "enough" if nodes else "empty",
        snapshot=WorldGraphRetrievalSnapshot(
            world_id=request.world_id, campaign_id=request.campaign_id,
            revision_id=pin.revision_id, head_revision_id=head.head_revision_id,
            is_head=pin.revision_id == head.head_revision_id,
            focus=request.focus.to_projection_focus(), admissibility=request.admissibility,
            scope_mode=request.scope_mode,
        ),
        nodes=nodes, relationships=edges,
        source_anchors=anchors[:request.bounds.max_source_anchors],
        coverage=WorldGraphRetrievalCoverage(
            requested_seed_node_ids=request.seed_node_ids,
            missing_seed_node_ids=missing, truncated_fields=truncated,
        ),
    )
