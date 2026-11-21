"""Prepare a private release candidate from explicit owner selections.

The caller authenticates the subject and enforces hosted World access. No guest
route may call this service, and its result is not published until promotion.
"""
from __future__ import annotations

import hashlib
import os
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, StrictInt

from application_state import guest_release, media
from application_state.errors import ApplicationStateUnavailableError
from apps.live_control_server.services.guest_release_media import sanitize_release_image
from apps.live_control_server.services.guest_release_evidence import verify_source_citation
from apps.live_control_server.services.guest_release_native_graph import read_owner_graph
from apps.live_control_server.services.guest_release_assertions import select_node, select_relationship
from apps.live_control_server.services.guest_release_sources import selected_page_excerpt
from apps.live_control_server.services.hosted_native_graph_access import hosted_world_media_owner


class GuestReleasePreparationError(ValueError):
    """An owner selection cannot be assembled into a release."""


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
    assertion_id: str = Field(min_length=1, max_length=255)
    subject_id: str = Field(min_length=1, max_length=255)
    predicate: str = Field(min_length=1, max_length=255)
    evidence_id: str = Field(min_length=1, max_length=255)
    source_index: int = Field(ge=0, strict=True)


class NodeSelection(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    entity_id: str = Field(min_length=1, max_length=255)
    name_assertion_id: str = Field(min_length=1, max_length=255)
    name_source_index: int = Field(ge=0, strict=True)
    kind_assertion_id: str = Field(min_length=1, max_length=255)
    kind_source_index: int = Field(ge=0, strict=True)


class SavedExampleSelection(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    title: str = Field(min_length=1, max_length=120)
    body: str = Field(min_length=1, max_length=10_000)
    source_indexes: list[StrictInt] = Field(min_length=2, max_length=10)
    asset_id: UUID | None = None
    image_description: str | None = Field(default=None, max_length=240)


class ReleaseSelection(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    graph_revision: str = Field(min_length=1, max_length=255)
    nodes: list[NodeSelection] = Field(max_length=500)
    relationships: list[RelationshipSelection] = Field(max_length=1000)
    sources: list[SourceSelection] = Field(max_length=500)
    asset_ids: list[UUID] = Field(max_length=100)
    saved_example: SavedExampleSelection | None = None


def prepare(*, world_id: str, subject: str, selection: ReleaseSelection) -> tuple[UUID, str]:
    """Copy selected authorized bytes and stage an unexposed candidate."""
    # This switch is independent of public delivery and remains off until the
    # full owner/release qualification in the handoff has passed.
    if os.environ.get("DMB_GUEST_RELEASE_PREPARE_ENABLED") != "1":
        raise ApplicationStateUnavailableError("Guest release preparation is not yet available")
    return _prepare_candidate(world_id=world_id, subject=subject, selection=selection)


def _prepare_candidate(*, world_id: str, subject: str, selection: ReleaseSelection) -> tuple[UUID, str]:
    """Experimental assembly; not an authorized or mounted entry point."""
    generation = guest_release.owner_generation(world_id=world_id, subject=subject)
    binding, context, support, access = read_owner_graph(managed_world_id=world_id, revision_id=selection.graph_revision)
    edge_ids = [item.assertion_id for item in selection.relationships]
    node_ids = [item.entity_id for item in selection.nodes]
    if (len(set(node_ids)) != len(node_ids) or len(set(edge_ids)) != len(edge_ids)
        or len(set(selection.asset_ids)) != len(selection.asset_ids)):
        raise GuestReleasePreparationError("Duplicate release selection")
    sources, bindings = [], []
    for source in selection.sources:
        excerpt, source_binding = selected_page_excerpt(world_id=world_id, document_id=str(source.document_id),
            revision_n=source.revision_n, expected_sha256=source.sha256, start=source.start,
            end=source.end, expected_excerpt=source.excerpt)
        native_evidence = access.parsed.get_evidence(source.evidence_id)
        if native_evidence is None:
            raise GuestReleasePreparationError("Selected evidence is unavailable")
        excerpt["evidence_role"] = native_evidence.evidence_role
        verify_source_citation(evidence_id=source.evidence_id, access=access, excerpt=excerpt,
            source_binding=source_binding[:9], expected_native_world_id=binding.native_world_id,
            expected_graph_revision=selection.graph_revision)
        sources.append(excerpt)
        bindings.append((*source_binding, source.evidence_id))
    def citation(index, evidence_id=None):
        if index >= len(sources):
            raise GuestReleasePreparationError("Source selection is unavailable")
        source = selection.sources[index]
        if evidence_id is not None and evidence_id != source.evidence_id:
            raise GuestReleasePreparationError("Source evidence selection differs")
        return source.evidence_id, sources[index], bindings[index][:9]

    evidence_bindings = []
    node_bindings = []
    common = dict(context=context, admitted_ids=set(support.listing.admitted_assertion_ids), access=access,
                  native_world_id=binding.native_world_id, revision_id=selection.graph_revision)
    public_nodes, public_edges, local_ids = [], [], {}
    for node in selection.nodes:
        public, private = select_node(**common, entity_id=node.entity_id, name_assertion_id=node.name_assertion_id,
            kind_assertion_id=node.kind_assertion_id, name_evidence=citation(node.name_source_index),
            kind_evidence=citation(node.kind_source_index))
        public_nodes.append(public)
        node_bindings.append(private)
        local_ids[node.entity_id] = public["id"]
    for relationship in selection.relationships:
        public, private = select_relationship(**common, assertion_id=relationship.assertion_id,
            subject_id=relationship.subject_id, predicate=relationship.predicate, node_ids=local_ids,
            evidence=citation(relationship.source_index, relationship.evidence_id))
        public_edges.append(public)
        evidence_bindings.append(private)
    graph = {"nodes": public_nodes, "edges": public_edges}
    assets, manifest_assets, local_assets = [], [], {}
    owner = hosted_world_media_owner(world_id)
    for asset_id in selection.asset_ids:
        original = media.read_staged_bytes(asset_id, owner)
        mime, content = sanitize_release_image(original)
        release_asset_id = uuid4()
        local_assets[asset_id] = release_asset_id
        assets.append((release_asset_id, mime, content))
        manifest_assets.append({"id": str(release_asset_id), "mime_type": mime,
                                "sha256": hashlib.sha256(content).hexdigest()})
    manifest = {"schema": "buddy_guest_release_v1", "projection_version": "explicit_native_assertions_v3",
                "image_sanitizer_version": "bounded_png_v1", "graph": graph, "sources": sources,
                "assets": sorted(manifest_assets, key=lambda item: item["id"])}
    if selection.saved_example is not None:
        example = selection.saved_example
        if (any(type(index) is not int or index < 0 or index >= len(sources) for index in example.source_indexes)
            or (example.asset_id is None) != (example.image_description is None)
            or (example.asset_id is not None and example.asset_id not in local_assets)):
            raise GuestReleasePreparationError("Saved example selection is unavailable")
        manifest["saved_example"] = {
            "version": "owner_saved_scene_v1", "title": example.title, "body": example.body,
            "references": [sources[index]["id"] for index in example.source_indexes],
            "image": None if example.asset_id is None else {
                "id": str(local_assets[example.asset_id]), "description": example.image_description},
        }
    return guest_release.stage(world_id=world_id, subject=subject, expected_owner_generation=generation,
        native_world_id=binding.native_world_id, native_binding_version=binding.binding_version,
        graph_revision=selection.graph_revision, manifest=manifest, assets=assets, source_bindings=bindings,
        evidence_bindings=evidence_bindings, node_bindings=node_bindings)
