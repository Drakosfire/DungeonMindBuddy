"""Shared native Core context for current readers and reviewed preparation.

This module performs no directory discovery or source admission.
"""
from __future__ import annotations

from dataclasses import asdict
from psycopg.conninfo import conninfo_to_dict, make_conninfo

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


def read_repository():
    """Every inspection connection is read-only, including Core source reads."""
    dsn = config.world_graph_authority_database_url()
    options = conninfo_to_dict(dsn).get("options", "")
    return PostgresNativeSourceEvidenceRepository(PostgresDatabase(
        make_conninfo(dsn, options=(options + " -c default_transaction_read_only=on").strip())
    ))


def read_context(repo, space, revision, campaign, role="gm", *, scope_mode="campaign"):
    from graph_memory.vnext.domain_runtime import (
        DungeonBuddyVNextProjectionInput, build_dungeonbuddy_read_context,
    )
    domain, profile = descriptors(repo, space, revision)
    access = open_native_text_source_access_context(
        repository=repo, space_id=space, revision_id=revision, domain_contract=domain,
        audience_labels=(GM_LABEL, PLAYER_LABEL) if role == "gm" else (PLAYER_LABEL,),
    )
    read = build_dungeonbuddy_read_context(
        parsed_revision=access.parsed,
        projection_input=DungeonBuddyVNextProjectionInput(
            world_id=space, revision_id=revision, scope_mode=scope_mode,
            campaign_id=campaign, role=role,
        ),
        source_reader=access.source_view,
    )
    return read, access, domain, profile
