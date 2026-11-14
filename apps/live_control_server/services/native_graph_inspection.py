"""Faithful native inspection; Core owns admission, identity and source access."""

from base64 import b64encode

from dungeonmind.application.vnext import (
    EntityReadService,
    EvidenceReadService,
    list_admitted_native_text_sources,
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


from dungeonmind.application.vnext.native_source_access import NativeParsedRevisionCache


def _pinned(scope, principal, *, parsed_cache=None):
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
        parsed_cache=parsed_cache,
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


SESSION_RECAP_SOURCE = "dungeonbuddy.source:session_recap"


def related_recaps(scope, principal, assertion_id):
    """Discover readable recap spans attached as support to the pinned assertion."""
    bound, read, access, pin, _ = _pinned(scope, principal)
    result = EvidenceReadService().get_assertion_evidence(read, assertion_id)
    if not result.available or result.completeness.status != "complete":
        raise InspectionUnavailable("native_inspection_assertion_unavailable")
    support = tuple(e.evidence_ref_id for e in result.evidence if e.evidence_role == "support")
    sources = list_admitted_native_text_sources(access, evidence_ref_ids=support)
    if not sources.complete:
        raise InspectionUnavailable("native_inspection_source_unavailable")
    targets = [
        {
            "selection": {"kind": "source", "assertion_id": assertion_id, "evidence_ref_id": ref},
            "source_artifact_id": row.source_artifact.source_artifact_id,
            "source_revision_id": row.source_revision.source_revision_id,
        }
        for row in sources.sources
        if row.source_artifact.source_classification == SESSION_RECAP_SOURCE
        for ref in row.evidence_ref_ids
    ]
    return _response(bound, pin, schema="dmb_native_related_recaps_v1", targets=targets)


def inspect(request, principal, *, include_source_span=False, source_classification=None):
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
    if source_classification is not None:
        sources = list_admitted_native_text_sources(
            access, evidence_ref_ids=(selection.evidence_ref_id,),
        )
        if not sources.complete or not any(
            row.source_artifact.source_classification == source_classification
            and selection.evidence_ref_id in row.evidence_ref_ids
            for row in sources.sources
        ):
            raise InspectionUnavailable("native_inspection_source_unavailable")
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
    if include_source_span:
        span["source_span_ref_id"] = evidence.source_span_ref_id
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
        parsed_cache=_shared_parsed_cache,
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


def open_neighborhood_anchor(request, principal, *, include_receipt=False, authority=None):
    from graph_memory.retrieval.models import WorldGraphSourceAnchorReadResult
    from apps.live_control_server.integrations.dungeonmind.vnext_neighborhood import native_anchor_selection
    from apps.live_control_server.models.native_graph_inspection import InspectionRead

    require_native_graph_gm(principal)
    managed_world_id = authority.managed_world_id if authority is not None else request.world_id
    bound = native.binding(managed_world_id)
    if authority is not None and (
        request.world_id != authority.native_world_id
        or bound["native_world_id"] != authority.native_world_id
        or bound["binding_version"] != authority.binding_version
        or request.revision_pin != authority.graph_revision
    ):
        raise InspectionUnavailable("native_inspection_binding_changed")
    from apps.live_control_server.integrations.dungeonmind.world_graph_reads import ResolvedSourceAnchorReadV2

    result = WorldGraphSourceAnchorReadResult(outcome="empty", anchor_id=request.anchor_id)
    empty = ResolvedSourceAnchorReadV2(result, None, None, None, None, None, None, None, None) if include_receipt else result
    if request.revision_pin is None:
        return empty
    try:
        assertion_id, evidence_ref_id = native_anchor_selection(request.anchor_id)
    except ValueError:
        return empty
    if request.admissibility != principal.role:
        return empty
    pin = InspectionPin(
        managed_world_id=managed_world_id,
        native_world_id=bound["native_world_id"],
        binding_version=bound["binding_version"],
        revision_id=request.revision_pin,
        scope_mode=request.scope_mode,
        campaign_id=request.campaign_id if request.scope_mode == "campaign" else None,
    )
    from dungeonmind.application.vnext.errors import KnowledgeReadContextIntegrityError

    try:
        packet = inspect(InspectionRead(
            scope=pin,
            selection={"kind": "source", "assertion_id": assertion_id, "evidence_ref_id": evidence_ref_id},
        ), principal, include_source_span=include_receipt)
    except KnowledgeReadContextIntegrityError:
        if native.read_repository().get_revision(pin.native_world_id, pin.revision_id) is None:
            return empty
        raise
    source = packet.get("source")
    if source is None or native.binding(managed_world_id) != bound:
        return empty
    excerpt = source["text"]
    result = WorldGraphSourceAnchorReadResult(
        outcome="enough", anchor_id=request.anchor_id, evidence_ref_id=evidence_ref_id,
        source_artifact_id=source["source_artifact_id"], locator_kind="source_span",
        media_type="text/plain", content=excerpt[:request.max_chars],
        content_sha256=source["body_sha256"], truncated=len(excerpt) > request.max_chars,
    )
    if not include_receipt:
        return result
    from graph_memory.retrieval.models import WorldGraphRetrievalSnapshot

    span = source["source_span_ref_id"]
    head = native.read_repository().get_head(pin.native_world_id)
    if head is None:
        return empty
    result = result.model_copy(update={
        "source_span_ref_id": span,
        "snapshot": WorldGraphRetrievalSnapshot(
            world_id=request.world_id, campaign_id=request.campaign_id,
            revision_id=pin.revision_id, head_revision_id=head.head_revision_id,
            is_head=pin.revision_id == head.head_revision_id, focus=request.focus.model_dump(), admissibility=request.admissibility,
            scope_mode=request.scope_mode,
        ),
    })
    return ResolvedSourceAnchorReadV2(
        result, source["source_revision_id"], source["body_sha256"], evidence_ref_id,
        source["source_artifact_id"], span, "source_span", span, pin.revision_id,
    )


_shared_parsed_cache = NativeParsedRevisionCache()


def _shared_retrieval_pin(request, principal):
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
    return bound, head, pin


def shared_exact_object(request, principal):
    from graph_memory.retrieval.models import WorldGraphNeighborhoodRequest

    neighborhood = WorldGraphNeighborhoodRequest(
        schema="dmb_world_graph_neighborhood_request_v1",
        seedNodeIds=[request.node_id],
        maxDepth=1,
        **request.model_dump(by_alias=True, exclude={"schema_", "node_id"}),
    )
    return shared_neighborhood(neighborhood, principal, object_id=request.node_id)


def shared_neighborhood(request, principal, *, object_id=None):
    bound, head, pin = _shared_retrieval_pin(request, principal)
    _, read, _, _, _ = _pinned(pin, principal, parsed_cache=_shared_parsed_cache)
    return _shared_retrieval_projection(request, bound, head, pin, read, object_id=object_id)


def _shared_retrieval_projection(request, bound, head, pin, read, *, object_id=None, search_entities=None):
    from graph_memory.retrieval.models import (
        WorldGraphRetrievalCoverage, WorldGraphRetrievalResult,
        WorldGraphRetrievalSnapshot, WorldGraphSourceAnchor,
    )
    from apps.live_control_server.integrations.dungeonmind.vnext_neighborhood import (
        map_nodes, map_relationships, read_neighborhood, native_anchor_id,
    )
    attributes = []
    selected_entities = {}
    if search_entities is not None:
        from types import SimpleNamespace
        from dungeonmind.application.vnext.records import ParsedEntityRefValue
        from apps.live_control_server.integrations.dungeonmind.vnext_neighborhood import BoundedNeighborhood

        reader = EntityReadService()
        complete = search_entities.values()
        edges = {
            row.assertion_id: row
            for item in complete for row in item.assertions
            if isinstance(row.value, ParsedEntityRefValue)
        }
        cap = request.bounds.max_relationships
        bounded = BoundedNeighborhood(
            tuple(search_entities), tuple(edges[key] for key in sorted(edges)[:cap]),
            False, len(edges) > cap,
        )
        result = SimpleNamespace(
            evidence=[row for item in complete for row in item.evidence],
            source_artifacts=[row for item in complete for row in item.source_artifacts],
            missing_seed_entity_ids=(),
        )
        from apps.live_control_server.integrations.dungeonmind.vnext_neighborhood import map_entity_result

        selected_entities = {entity_id: reader.get_entity(read, entity_id) for entity_id in search_entities}
        nodes = [
            map_entity_result(entity, entity_id, attributes=attributes, allow_multiple=True)
            for entity_id, entity in selected_entities.items()
        ]
    elif object_id is not None:
        from apps.live_control_server.integrations.dungeonmind.vnext_neighborhood import BoundedNeighborhood, map_entity_result
        from dungeonmind.application.vnext.records import ParsedEntityRefValue

        result = EntityReadService().get_complete_entity(read, object_id)
        relationships = sorted(
            (row for row in result.assertions if isinstance(row.value, ParsedEntityRefValue)),
            key=lambda row: row.assertion_id,
        )
        cap = request.bounds.max_relationships
        bounded = BoundedNeighborhood(
            node_ids=(object_id,) if result.found else (),
            edges=tuple(relationships[:cap]),
            nodes_truncated=False,
            relationships_truncated=len(relationships) > cap,
        )
        selected = EntityReadService().get_entity(read, object_id) if result.found else None
        nodes = [map_entity_result(selected, object_id, attributes=attributes)] if selected else []
        if selected is not None:
            selected_entities[object_id] = selected
    else:
        result, bounded = read_neighborhood(read, request.seed_node_ids, request.max_depth, request.bounds)
        nodes = map_nodes(read, bounded, attributes=attributes)
    edges = map_relationships(read, result, bounded)
    evidence = {row.evidence_ref_id: row for row in result.evidence}
    artifacts = {row.source_artifact_id: row for row in result.source_artifacts}
    from apps.live_control_server.integrations.dungeonmind.vnext_complete_object import _source_domain

    supporting_edges = {}
    for edge in edges:
        for evidence_id in edge.evidence_ref_ids:
            ref = evidence[evidence_id]
            if ref.evidence_role == "support" and ref.source_span_ref_id:
                supporting_edges.setdefault(evidence_id, []).append(edge)

    anchors = []
    for evidence_id, supporters in sorted(supporting_edges.items()):
        ref = evidence[evidence_id]
        artifact = artifacts[ref.source_artifact_id]
        assertion_ids = sorted({edge.edge_id for edge in supporters})
        object_ids = sorted({
            node_id for edge in supporters
            for node_id in (edge.source_node_id, edge.target_node_id)
        })
        anchors.append(WorldGraphSourceAnchor(
            anchor_id=native_anchor_id(assertion_ids[0], evidence_id),
            revision_id=pin.revision_id,
            evidence_ref_id=evidence_id,
            source_artifact_id=ref.source_artifact_id,
            source_domain=_source_domain(artifact.source_classification),
            source_span_ref_id=ref.source_span_ref_id,
            supporting_graph_object_ids=object_ids,
            supporting_assertion_ids=assertion_ids,
            readable=ref.can_open_source, locator_kind="source_span",
        ))
    by_id = {anchor.evidence_ref_id: anchor for anchor in anchors}
    for entity_id, selected in selected_entities.items():
        selected_sources = {source.source_artifact_id: source for source in selected.source_artifacts}
        for ref in selected.evidence:
            if ref.evidence_role != "support" or not ref.source_span_ref_id:
                continue
            supporters = {
                row.assertion_id for row in selected.assertions
                if ref.evidence_ref_id in row.metadata.evidence_ref_ids
            }
            if not supporters:
                continue
            existing = by_id.get(ref.evidence_ref_id)
            if existing is not None:
                existing.supporting_assertion_ids = sorted(supporters.union(existing.supporting_assertion_ids))
                existing.supporting_graph_object_ids = sorted({entity_id, *existing.supporting_graph_object_ids})
                continue
            by_id[ref.evidence_ref_id] = WorldGraphSourceAnchor(
                anchor_id=native_anchor_id(min(supporters), ref.evidence_ref_id),
                revision_id=pin.revision_id,
                evidence_ref_id=ref.evidence_ref_id,
                source_artifact_id=ref.source_artifact_id,
                source_domain=_source_domain(selected_sources[ref.source_artifact_id].source_classification),
                source_span_ref_id=ref.source_span_ref_id,
                supporting_graph_object_ids=[entity_id],
                supporting_assertion_ids=sorted(supporters),
                readable=ref.can_open_source, locator_kind="source_span",
            )
    anchors = [by_id[key] for key in sorted(by_id)]
    _response(bound, pin)
    truncated = [
        field for field in ("nodes", "relationships") if getattr(bounded, f"{field}_truncated")
    ]
    if len(anchors) > request.bounds.max_source_anchors:
        truncated.append("source_anchors")
    attributes.sort(key=lambda row: row.assertion_id)
    if len(attributes) > request.bounds.max_attributes:
        truncated.append("attributes")
    missing = [] if object_id is not None else list(result.missing_seed_entity_ids)
    if search_entities is not None:
        operation = "search"
        request_summary = {"query_text": request.query_text, "seed_node_ids": request.seed_node_ids}
    elif object_id is not None:
        operation = "object"
        request_summary = {"node_id": object_id}
    else:
        operation = "neighborhood"
        request_summary = {"seed_node_ids": list(request.seed_node_ids), "max_depth": request.max_depth}
    return WorldGraphRetrievalResult(
        operation=operation,
        requested_node_id=object_id,
        resolved_node_id=object_id if nodes else None,
        outcome="partial" if truncated or missing else "enough" if nodes else "empty",
        snapshot=WorldGraphRetrievalSnapshot(
            world_id=request.world_id, campaign_id=request.campaign_id,
            revision_id=pin.revision_id, head_revision_id=head.head_revision_id,
            is_head=pin.revision_id == head.head_revision_id,
            focus=request.focus.to_projection_focus(), admissibility=request.admissibility,
            scope_mode=request.scope_mode,
        ),
        request_summary=request_summary,
        nodes=nodes, relationships=edges,
        attributes=attributes[:request.bounds.max_attributes],
        source_anchors=anchors[:request.bounds.max_source_anchors],
        coverage=WorldGraphRetrievalCoverage(
            requested_seed_node_ids=request.seed_node_ids,
            missing_seed_node_ids=missing, truncated_fields=truncated,
        ),
    )


def shared_evidence(request, principal):
    from dungeonmind.application.vnext.records import ParsedEntityRefValue
    from graph_memory.retrieval.models import (
        WorldGraphRetrievalAttribute,
        WorldGraphRetrievalCoverage,
        WorldGraphRetrievalResult,
        WorldGraphRetrievalSnapshot,
        WorldGraphSourceAnchor,
    )
    from apps.live_control_server.integrations.dungeonmind.vnext_complete_object import (
        _map_assertion,
        _source_domain,
    )
    from apps.live_control_server.integrations.dungeonmind.vnext_neighborhood import (
        BoundedNeighborhood,
        map_entity_result,
        map_relationships,
        native_anchor_id,
    )

    bound, head, pin = _shared_retrieval_pin(request, principal)
    _, read, _, _, _ = _pinned(pin, principal, parsed_cache=_shared_parsed_cache)
    target = request.target
    nodes, relationships, attributes = [], [], []
    supporters = {}
    if target.kind == "node":
        result = EntityReadService().get_entity(read, target.id)
        object_ids = [target.id]
        if result.found:
            nodes.append(map_entity_result(result, target.id))
            for assertion in result.assertions:
                for ref_id in assertion.metadata.evidence_ref_ids:
                    supporters.setdefault(ref_id, set()).add(assertion.assertion_id)
    else:
        result = EvidenceReadService().get_assertion_evidence(read, target.id)
        assertion = result.assertion
        object_ids = []
        if result.available and assertion is not None:
            is_relationship = isinstance(assertion.value, ParsedEntityRefValue)
            if is_relationship == (target.kind == "relationship"):
                object_ids = [assertion.subject_entity_id]
                evidence = {row.evidence_ref_id: row for row in result.evidence}
                if is_relationship:
                    relationships = map_relationships(
                        read, result, BoundedNeighborhood((), (assertion,), False, False)
                    )
                    object_ids = sorted({relationships[0].source_node_id, relationships[0].target_node_id})
                else:
                    view = _map_assertion(assertion, evidence_by_id=evidence)
                    attributes.append(WorldGraphRetrievalAttribute(
                        **view.model_dump(include=set(WorldGraphRetrievalAttribute.model_fields))
                    ))
                supporters = {ref_id: {target.id} for ref_id in evidence}

    sources = {row.source_artifact_id: row for row in result.source_artifacts}
    anchors = []
    for ref in result.evidence:
        assertion_ids = sorted(supporters.get(ref.evidence_ref_id, ()))
        if not assertion_ids or ref.evidence_role != "support" or not ref.source_span_ref_id:
            continue
        anchors.append(WorldGraphSourceAnchor(
            anchor_id=native_anchor_id(assertion_ids[0], ref.evidence_ref_id),
            revision_id=pin.revision_id,
            evidence_ref_id=ref.evidence_ref_id,
            source_artifact_id=ref.source_artifact_id,
            source_domain=_source_domain(sources[ref.source_artifact_id].source_classification),
            source_span_ref_id=ref.source_span_ref_id,
            supporting_graph_object_ids=object_ids,
            supporting_assertion_ids=assertion_ids,
            readable=ref.can_open_source,
            locator_kind="source_span",
        ))
    _response(bound, pin)
    cap = request.bounds.max_source_anchors
    truncated = len(anchors) > cap
    return WorldGraphRetrievalResult(
        operation="evidence",
        outcome="partial" if truncated else "enough" if supporters else "empty",
        snapshot=WorldGraphRetrievalSnapshot(
            world_id=request.world_id, campaign_id=request.campaign_id,
            revision_id=pin.revision_id, head_revision_id=head.head_revision_id,
            is_head=pin.revision_id == head.head_revision_id,
            focus=request.focus.to_projection_focus(), admissibility=request.admissibility,
            scope_mode=request.scope_mode,
        ),
        request_summary={"target_kind": target.kind, "target_id": target.id},
        nodes=nodes, relationships=relationships, attributes=attributes,
        source_anchors=anchors[:cap],
        coverage=WorldGraphRetrievalCoverage(
            truncated_fields=["source_anchors"] if truncated else [],
        ),
    )


def _reviewed_search_matches(hits, result, read, space, repository):
    from hashlib import sha256

    from graph_memory.retrieval.models import WorldGraphNativeReviewedSourceObservationMatch
    from dungeonmind.application.vnext.prospective import get_prospective_publication
    from graph_memory.vnext.domain_runtime import (
        CAMPAIGN_SCOPE_AXIS, DUNGEONBUDDY_OBSERVATION_PREDICATE, PLAYER_LABEL,
    )

    nodes = {node.node_id: node for node in result.nodes}
    publications = {}
    matches = []
    for hit in hits:
        node = nodes.get(hit.entity.entity_id)
        if node is None:
            continue
        for assertion in hit.admitted_match_assertions:
            if assertion.predicate != DUNGEONBUDDY_OBSERVATION_PREDICATE:
                continue
            row = native.assertion_contract(assertion).model_dump(mode="json")
            text = row["value"].get("value")
            metadata = row["metadata"]
            ids = [item["payload"].get("reviewed_observation_publication_id")
                   for item in metadata["domain_metadata"]
                   if item["schema"] == "dungeonbuddy.domain_metadata:world_context_v1"
                   and isinstance(item["payload"], dict)]
            if not isinstance(text, str) or len(ids) != 1 or not isinstance(ids[0], str):
                continue
            publication_id = ids[0]
            if publication_id not in publications:
                publications[publication_id] = get_prospective_publication(
                    space, publication_id, repository=repository,
                )
            publication = publications[publication_id]
            if publication is None or not any(
                binding.result_kind == "assertion" and binding.durable_id == assertion.assertion_id
                for binding in publication.prospective_result.results
            ):
                continue
            anchor = next((anchor for anchor in result.source_anchors
                           if anchor.readable and assertion.assertion_id in anchor.supporting_assertion_ids), None)
            if anchor is None:
                continue
            evidence = read.parsed.evidence_by_id.get(anchor.evidence_ref_id)
            if evidence is None:
                continue
            excerpt = text[:768]
            matches.append(WorldGraphNativeReviewedSourceObservationMatch(
                assertion_id=assertion.assertion_id,
                subject_node_id=node.node_id,
                observation_kind="worldbuilding_observation",
                text_excerpt=excerpt, excerpt_start=0, excerpt_end=len(excerpt),
                text_length=len(text), text_sha256=sha256(text.encode("utf-8")).hexdigest(),
                entity_kind=node.kind,
                publication_id=publication_id,
                publication_revision_id=publication.publication_receipt.published_revision_id,
                source_artifact_id=evidence.source_artifact_id,
                source_revision_id=evidence.source_revision_id,
                evidence_ref_ids=[anchor.evidence_ref_id],
                campaign_scope=next((binding["value"] for binding in metadata["scope"]
                                     if binding["axis"] == CAMPAIGN_SCOPE_AXIS), None),
                visibility="player" if PLAYER_LABEL in metadata["visibility"].get("labels", ()) else "gm",
                epistemic_kind=metadata["epistemic_basis"],
                temporal_scope=metadata["temporal_scope"],
            ))
    return matches


def shared_search(request, principal, *, include_source_pins=False,
                  expected_native_world_id=None, expected_binding_version=None):
    from dungeonmind.application.vnext import SearchReadService

    bound, head, pin = _shared_retrieval_pin(request, principal)
    if expected_native_world_id is not None and (
        pin.native_world_id != expected_native_world_id or pin.binding_version != expected_binding_version
    ):
        raise InspectionUnavailable("native_inspection_binding_changed")
    read_binding, read, _, _, _ = _pinned(pin, principal, parsed_cache=_shared_parsed_cache)
    if read_binding != bound:
        raise InspectionUnavailable("native_inspection_binding_changed")
    search = SearchReadService().search_entities(read, request.query_text, limit=20)
    seeds = list(dict.fromkeys(request.seed_node_ids))
    reader = EntityReadService()
    complete_entities = {}

    def complete_entity(entity_id):
        if entity_id not in complete_entities:
            complete_entities[entity_id] = reader.get_complete_entity(read, entity_id)
        return complete_entities[entity_id]

    present = sorted(seed for seed in seeds if complete_entity(seed).assertions)
    missing = sorted(set(seeds) - set(present))
    reasons = {
        hit.entity.entity_id: list(hit.match_kinds)
        for hit in search.hits
        if hit.admitted_match_assertions
        or hit.entity.entity_id in present
        or complete_entity(hit.entity.entity_id).assertions
    }
    for seed in present:
        reasons.setdefault(seed, []).append("exact_seed")
    others = [entity_id for entity_id in reasons if entity_id not in present]
    remaining = max(request.bounds.max_nodes - len(present), 0)
    selected = present + others[:remaining]

    result = _shared_retrieval_projection(
        request, bound, head, pin, read,
        search_entities={entity_id: complete_entity(entity_id) for entity_id in selected},
    )
    truncated = list(result.coverage.truncated_fields)
    if len(others) > remaining or search.completeness.status != "complete":
        truncated = list(dict.fromkeys([*truncated, "nodes"]))
    observations = _reviewed_search_matches(
        search.hits, result, read, pin.native_world_id, native.read_repository()
    )
    for match in observations:
        if "reviewed_source_observation" not in reasons[match.subject_node_id]:
            reasons[match.subject_node_id].append("reviewed_source_observation")
    result = result.model_copy(update={
        "outcome": "partial" if missing or truncated else "enough" if selected else "empty",
        "matched_node_ids": selected,
        "reviewed_source_observation_matches": observations,
        "match_reasons": {entity_id: reasons[entity_id] for entity_id in selected},
        "coverage": result.coverage.model_copy(update={
            "requested_seed_node_ids": seeds,
            "missing_seed_node_ids": missing,
            "truncated_fields": truncated,
        }),
    })

    if not include_source_pins:
        return result

    from apps.live_control_server.integrations.dungeonmind.world_graph_reads import (
        ResolvedSourceAnchorMetadataV2, ResolvedWorldGraphOperationV3,
    )

    pins = []
    for anchor in result.source_anchors:
        if not anchor.readable:
            continue
        evidence = read.parsed.evidence_by_id.get(anchor.evidence_ref_id)
        if (evidence is None or evidence.source_artifact_id != anchor.source_artifact_id
                or not evidence.source_revision_id or anchor.revision_id != pin.revision_id):
            raise InspectionUnavailable("native_search_source_identity_mismatch")
        pins.append(ResolvedSourceAnchorMetadataV2(
            anchor_id=anchor.anchor_id, graph_revision=pin.revision_id,
            evidence_ref_id=evidence.evidence_ref_id,
            source_artifact_id=evidence.source_artifact_id,
            source_revision_id=evidence.source_revision_id,
        ))
    return ResolvedWorldGraphOperationV3(result, tuple(pins))


def plan_subject_search(request, principal):
    """Return navigation labels from the broker's pinned native read."""
    from dungeonmind.application.vnext import SearchReadService
    from graph_memory.retrieval.models import (
        WorldGraphRetrievalCoverage,
        WorldGraphRetrievalNode,
        WorldGraphRetrievalResult,
        WorldGraphRetrievalSnapshot,
    )
    from .native_graph_reads import _navigation_labels

    if request.revision_pin is None or request.seed_node_ids:
        raise ValueError("Plan subject search requires a pinned query without seeds")
    bound, head, pin = _shared_retrieval_pin(request, principal)
    _, read, _, _, _ = _pinned(pin, principal, parsed_cache=_shared_parsed_cache)
    search = SearchReadService().search_entities(read, request.query_text, limit=20)
    reader = EntityReadService()
    hits = [hit for hit in search.hits if hit.admitted_match_assertions]
    limit = request.bounds.max_nodes
    retained = {hit.entity.entity_id: hit for hit in hits[:limit]}
    labels = _navigation_labels({entity_id: reader.get_entity(read, entity_id) for entity_id in retained})
    nodes = [
        WorldGraphRetrievalNode(node_id=entity_id, label=labels[entity_id], kind="entity", role="match")
        for entity_id in retained
    ]
    reasons = {entity_id: list(hit.match_kinds) for entity_id, hit in retained.items()}
    _response(bound, pin)
    truncated = len(hits) > limit or search.completeness.status != "complete"
    return WorldGraphRetrievalResult(
        operation="search",
        outcome="partial" if truncated else "enough" if nodes else "empty",
        snapshot=WorldGraphRetrievalSnapshot(
            world_id=request.world_id, campaign_id=request.campaign_id,
            revision_id=pin.revision_id, head_revision_id=head.head_revision_id,
            is_head=pin.revision_id == head.head_revision_id,
            focus=request.focus.to_projection_focus(), admissibility=request.admissibility,
            scope_mode=request.scope_mode,
        ),
        request_summary={"query_text": request.query_text, "seed_node_ids": []},
        matched_node_ids=list(reasons), match_reasons=reasons, nodes=nodes,
        coverage=WorldGraphRetrievalCoverage(truncated_fields=["nodes"] if truncated else []),
    )
