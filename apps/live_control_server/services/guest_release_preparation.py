"""Prepare a private release candidate from explicit owner selections.

The caller authenticates the subject and enforces hosted World access. No guest
route may call this service, and its result is not published until promotion.
"""
from __future__ import annotations

import hashlib
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from application_state import guest_release, media
from application_state.errors import ApplicationStateUnavailableError
from apps.live_control_server.services.guest_release_media import sanitize_release_image
from apps.live_control_server.services.guest_release_evidence import verify_source_citation
from apps.live_control_server.services.guest_release_native_graph import read_player_graph
from apps.live_control_server.services.guest_release_projection import project_selected_graph
from apps.live_control_server.services.guest_release_sources import selected_page_excerpt
from apps.live_control_server.services.hosted_native_graph_access import hosted_world_media_owner


class SourceSelection(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    document_id: UUID
    revision_n: int = Field(gt=0, strict=True)
    sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    start: int = Field(ge=0, strict=True)
    end: int = Field(gt=0, strict=True)
    excerpt: str = Field(min_length=1, max_length=20_000)
    evidence_id: str = Field(min_length=1, max_length=255)


class RelationshipSelection(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    edge_id: str = Field(min_length=1, max_length=255)
    evidence_id: str = Field(min_length=1, max_length=255)
    source_index: int = Field(ge=0, strict=True)


class ReleaseSelection(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    graph_revision: str = Field(min_length=1, max_length=255)
    node_ids: list[str] = Field(max_length=500)
    relationships: list[RelationshipSelection] = Field(max_length=1000)
    sources: list[SourceSelection] = Field(max_length=500)
    asset_ids: list[UUID] = Field(max_length=100)


def prepare(*, world_id: str, subject: str, selection: ReleaseSelection) -> tuple[UUID, str]:
    """Copy selected authorized bytes and stage an unexposed candidate."""
    # No classic Graph fallback: ordinary first-World initialization uses vNext.
    # Keep unavailable until player filtering, citation closure and metadata-safe
    # asset copying are implemented and verified together.
    raise ApplicationStateUnavailableError("Guest release preparation is not yet available")


def _prepare_candidate(*, world_id: str, subject: str, selection: ReleaseSelection) -> tuple[UUID, str]:
    """Experimental assembly; not an authorized or mounted entry point."""
    generation = guest_release.owner_generation(world_id=world_id, subject=subject)
    binding, projection, access = read_player_graph(managed_world_id=world_id, revision_id=selection.graph_revision)
    edge_ids = [item.edge_id for item in selection.relationships]
    if (len(set(selection.node_ids)) != len(selection.node_ids) or len(set(edge_ids)) != len(edge_ids)
        or len(set(selection.asset_ids)) != len(selection.asset_ids)):
        raise ValueError("Duplicate release selection")
    sources, bindings = [], []
    for source in selection.sources:
        excerpt, source_binding = selected_page_excerpt(world_id=world_id, document_id=str(source.document_id),
            revision_n=source.revision_n, expected_sha256=source.sha256, start=source.start,
            end=source.end, expected_excerpt=source.excerpt)
        verify_source_citation(evidence_id=source.evidence_id, access=access, excerpt=excerpt,
            source_binding=source_binding[:9], expected_native_world_id=binding.native_world_id,
            expected_graph_revision=selection.graph_revision)
        sources.append(excerpt)
        bindings.append((*source_binding, source.evidence_id))
    citations = {}
    for relationship in selection.relationships:
        if relationship.source_index >= len(sources):
            raise ValueError("Relationship source selection is unavailable")
        citations[relationship.edge_id] = (relationship.evidence_id, sources[relationship.source_index],
                                            bindings[relationship.source_index][:9])
    evidence_bindings = []
    node_bindings = []
    graph = project_selected_graph(projection, expected_world_id=binding.native_world_id,
        expected_revision=selection.graph_revision, selected_node_ids=set(selection.node_ids),
        selected_edge_ids=set(edge_ids), citation_selections=citations, source_access=access,
        private_evidence_bindings=evidence_bindings, private_node_bindings=node_bindings)
    assets, manifest_assets = [], []
    owner = hosted_world_media_owner(world_id)
    for asset_id in selection.asset_ids:
        original = media.read_staged_bytes(asset_id, owner)
        mime, content = sanitize_release_image(original)
        release_asset_id = uuid4()
        assets.append((release_asset_id, mime, content))
        manifest_assets.append({"id": str(release_asset_id), "mime_type": mime,
                                "sha256": hashlib.sha256(content).hexdigest()})
    manifest = {"schema": "buddy_guest_release_v1", "graph": graph, "sources": sources,
                "assets": sorted(manifest_assets, key=lambda item: item["id"])}
    return guest_release.stage(world_id=world_id, subject=subject, expected_owner_generation=generation,
        native_world_id=binding.native_world_id, native_binding_version=binding.binding_version,
        graph_revision=selection.graph_revision, manifest=manifest, assets=assets, source_bindings=bindings,
        evidence_bindings=evidence_bindings, node_bindings=node_bindings)
