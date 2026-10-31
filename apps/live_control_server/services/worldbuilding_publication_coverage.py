"""Exact-run reopening reads native proof; it never resumes publication."""

from apps.live_control_server import config as live_config
from apps.live_control_server.models.worldbuilding_publication_coverage import (
    WorldbuildingCandidatePublicationCoverage,
    WorldbuildingHistoricalPublicationReceipt,
    WorldbuildingPublicationCoverage,
    WorldbuildingPublicationFacet,
)
from apps.live_control_server.ports.world_graph_authority import (
    WorldbuildingPublicationDiscoveryRequest,
    WorldGraphAuthorityError,
)
from apps.live_control_server.ports.world_graph_authority_access import get_world_graph_authority
from apps.live_control_server.services.extract_promote import (
    ExtractPromoteError,
    _load_worldbuilding_publication_input,
)
from apps.live_control_server.services.promotable_ingest_run import (
    PromotableIngestRunError,
    resolve_promotable_ingest_run,
)
from apps.live_control_server.services.worldbuilding_graph_publication import (
    _authority_error,
    _promotable_run_error,
    _registered_publication_binding,
    _world_scoped_preview,
)


def get_worldbuilding_publication_coverage(run_id: str) -> WorldbuildingPublicationCoverage:
    try:
        resolved = resolve_promotable_ingest_run(run_id, root=live_config.repo_root())
    except PromotableIngestRunError as exc:
        raise _promotable_run_error(exc) from exc
    preview = _load_worldbuilding_publication_input(resolved).preview
    binding = _registered_publication_binding(resolved)
    preview = _world_scoped_preview(preview, binding)
    authority = get_world_graph_authority()
    try:
        head = authority.current_head(binding.native_world_id)
        if head.world_id != binding.native_world_id:
            raise WorldGraphAuthorityError("World head binding disagrees", code="integrity_failure")
        history = authority.discover_worldbuilding_publications(
            WorldbuildingPublicationDiscoveryRequest(
                world_id=binding.native_world_id, revision_id=head.revision_id,
                run_id=resolved.run_id, source_artifact_id=resolved.source_artifact_id,
                source_revision_id=resolved.source_revision_id,
                source_uri=resolved.sealed_source_uri, preview=preview,
            )
        )
        if (
            history.world_id != binding.native_world_id
            or history.revision_id != head.revision_id
            or history.run_id != resolved.run_id
            or history.source_artifact_id != resolved.source_artifact_id
            or history.source_revision_id != resolved.source_revision_id
        ):
            raise WorldGraphAuthorityError("Discovery source/World binding disagrees",
                                           code="integrity_failure")
    except WorldGraphAuthorityError as exc:
        raise _authority_error(exc) from exc
    if _registered_publication_binding(resolved) != binding:
        raise ExtractPromoteError("World/source binding changed during discovery",
                                 code="worldbuilding_source_binding_changed", status_code=409)
    kinds = {item.node_id: "node" for item in preview.nodes}
    kinds.update({item.edge_id: "edge" for item in preview.edges})
    kinds.update({item.observation_id: "source_observation" for item in preview.source_observations})
    unknown = any(item.unmapped_assertion_ids for item in history.publications)
    facets = {candidate_id: [] for candidate_id in kinds}
    receipts = []
    for publication in history.publications:
        receipts.append(WorldbuildingHistoricalPublicationReceipt(
            native_operation_id=publication.native_operation_id, review_id=publication.review_id,
            parent_revision_id=publication.parent_revision_id,
            published_revision_id=publication.published_revision_id,
            reviewed_contribution_id=publication.reviewed_contribution_id,
            reviewed_contribution_sha256=publication.reviewed_contribution_sha256,
            unmapped_assertion_ids=list(publication.unmapped_assertion_ids),
        ))
        for fact in publication.facets:
            if kinds.get(fact.candidate_id) != fact.candidate_kind:
                raise ExtractPromoteError("Publication candidate mapping disagrees",
                                         code="publication_integrity_failure", status_code=409)
            facets[fact.candidate_id].append(WorldbuildingPublicationFacet(
                facet=fact.facet, assertion_id=fact.assertion_id,
                subject_node_id=fact.subject_node_id, verdict=fact.verdict,
                native_operation_id=publication.native_operation_id,
                published_revision_id=publication.published_revision_id,
            ))
    candidates = []
    for candidate_id, kind in sorted(kinds.items()):
        facts = facets[candidate_id]
        accepted = any(fact.verdict == "accepted" for fact in facts)
        rejected = any(fact.verdict == "rejected" for fact in facts)
        status = ("published_facts" if accepted else "rejected_facts" if rejected
                  else "unknown" if unknown else "not_published")
        candidates.append(WorldbuildingCandidatePublicationCoverage(
            candidate_id=candidate_id, candidate_kind=kind, status=status, facets=facts,
        ))
    return WorldbuildingPublicationCoverage(
        run_id=resolved.run_id, managed_world_id=binding.managed_world_id,
        native_world_id=binding.native_world_id, revision_id=history.revision_id,
        source_artifact_id=resolved.source_artifact_id,
        source_revision_id=resolved.source_revision_id,
        status="unknown" if unknown else "published" if receipts else "not_published",
        scanned_revision_count=history.scanned_revision_count,
        publications=receipts, candidates=candidates,
        diagnostics=["unmapped_historical_assertions"] if unknown else [],
    )
