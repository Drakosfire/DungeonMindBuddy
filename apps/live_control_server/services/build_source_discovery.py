"""Read-only Build source discovery; pointers never confer claim authority."""
from dataclasses import asdict

from dungeonmind.application.world_graph_retrieval import ReviewedSourceDiscoveryRequest
from dungeonmind.contracts.projection_v2 import WorldGraphProjectionRequestV2
from graph_memory.evidence.source_artifact import build_worldbuilding_source_artifact_id


def discover_build_source(services, basis, *, native_world_id: str, graph_revision: str) -> dict:
    artifact_id = build_worldbuilding_source_artifact_id(
        workspace_document_id=basis.document_id,
        workspace_document_revision=basis.revision,
        content_sha256=basis.content_sha256,
    )
    base = {"schema": "dmb_build_source_discovery_v1", "discovery_only": True,
            "world_id": native_world_id, "graph_revision": graph_revision,
            "source_artifact_id": artifact_id,
            "interpretation": (
                "Pointers and excerpts help choose object expansion; they are not admitted claims or citations. "
                "Fetch the subject object, read its complete reviewed observations and open supporting passages. "
                "Preserve epistemic and temporal qualifications. Sharing a source does not imply membership. "
                "This indexes reviewed source observations only, not all Graph relationships or knowledge."
            )}
    artifacts = [a for a in services.bundle.sources.list_artifacts_for_world(native_world_id)
                 if a.source_artifact_id == artifact_id]
    if not artifacts:
        return {**base, "status": "source_not_admitted", "eligible_count": None,
                "entries": [], "next_page_token": None, "coverage": None}
    if len(artifacts) != 1:
        raise ValueError("Ambiguous Build source artifact")
    artifact = artifacts[0]
    ref = getattr(artifact, "workspace_document_ref", None)
    if (artifact.world_id != native_world_id or ref is None
            or ref.document_id != basis.document_id or ref.revision != basis.revision
            or getattr(artifact.source_domain, "value", artifact.source_domain) != "worldbuilding"
            or getattr(artifact.status, "value", artifact.status) != "active"):
        raise ValueError("Build source catalog ownership mismatch")
    revisions = [r for r in services.bundle.sources.list_revisions(artifact_id)
                 if r.source_artifact_id == artifact_id
                 and r.content_sha256.removeprefix("sha256:") == basis.content_sha256]
    if len(revisions) != 1:
        raise ValueError("Exact Build source revision is missing or ambiguous")
    source_revision = revisions[0].source_revision_id
    result = services.retrieval.discover_reviewed_source_observations(ReviewedSourceDiscoveryRequest(
        WorldGraphProjectionRequestV2(world_id=native_world_id, scope_mode="world_cross_campaign",
            admissibility="gm", revision_pin=graph_revision),
        artifact_id, source_revision, max_entries=64,
    ))
    # Deliberately omit anchors: discovery must not expand effective source pins.
    entries = [{k: v for k, v in asdict(e).items() if k != "source_anchors"}
               for e in result.entries]
    return {**base, "source_revision_id": source_revision,
            "status": "partial" if (result.next_page_token or result.coverage.gap_codes or result.coverage.missing_ids) else "complete",
            "eligible_count": result.eligible_count, "entries": entries,
            "next_page_token": result.next_page_token, "coverage": asdict(result.coverage),
            "continuation_note": "Only this initial page is supplied; use object expansion for listed targets. "
                "A partial page cannot establish an exhaustive roster."}
