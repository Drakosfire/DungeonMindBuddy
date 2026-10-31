"""Shared native Core context for current readers and reviewed preparation.

This module performs no directory discovery or source admission.
"""
from __future__ import annotations

from dataclasses import asdict

from dungeonmind.application.vnext import open_native_text_source_access_context
from dungeonmind.infrastructure.postgres import PostgresDatabase, PostgresNativeSourceEvidenceRepository
from apps.live_control_server import config
from apps.live_control_server.services.managed_world_graph_projection import resolve_managed_world_binding
from graph_memory.vnext.domain_runtime import GM_LABEL, PLAYER_LABEL, resolve_dungeonbuddy_descriptors


def repository():
    return PostgresNativeSourceEvidenceRepository(
        PostgresDatabase(config.world_graph_authority_database_url())
    )


def descriptors(repo, space_id, revision_id):
    snapshot = repo.get_revision(space_id, revision_id)
    if snapshot is None:
        raise ValueError("Selected native World revision is missing")
    return resolve_dungeonbuddy_descriptors(
        domain_ref=snapshot.revision.domain_contract_ref,
        profile_ref=snapshot.revision.semantic_profile_ref,
    )


def binding(managed_world_id):
    return asdict(resolve_managed_world_binding(managed_world_id))


def access_context(repo, space_id):
    head = repo.get_head(space_id)
    if head is None:
        raise ValueError("native World has no head")
    domain, _ = descriptors(repo, space_id, head.head_revision_id)
    access = open_native_text_source_access_context(
        repository=repo,
        space_id=space_id,
        revision_id=head.head_revision_id,
        domain_contract=domain,
        audience_labels=(GM_LABEL, PLAYER_LABEL),
    )
    p = access.parsed
    context = {
        "space_id": space_id,
        "revision_id": p.revision_id,
        "graph_sha256": p.graph_payload_sha256,
        "source_epoch": access.source_view.epoch,
        "domain_ref": {
            "authority_id": p.domain_contract_ref.domain_id,
            "revision": p.domain_contract_ref.domain_revision,
            "descriptor_sha256": p.domain_contract_ref.descriptor_sha256,
        },
        "profile_ref": {
            "authority_id": p.semantic_profile_ref.profile_id,
            "revision": p.semantic_profile_ref.profile_revision,
            "descriptor_sha256": p.semantic_profile_ref.descriptor_sha256,
        },
    }
    return context, access
