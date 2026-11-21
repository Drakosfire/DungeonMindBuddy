"""Read an exact managed native Graph using the player audience for release."""
from __future__ import annotations

from dungeonmind.application.vnext import EntityReadService

from apps.live_control_server.integrations.dungeonmind import native_registry_source
from apps.live_control_server.integrations.dungeonmind.vnext_world_projection import project_native_world
from apps.live_control_server.services.managed_world_graph_projection import resolve_managed_world_binding
from graph_memory.projection.world_projection import WorldGraphProjectionFocus, WorldGraphProjectionSnapshot


class GuestNativeGraphError(ValueError):
    """An exact player-scoped native Graph cannot be prepared."""


def read_owner_graph(*, managed_world_id: str, revision_id: str):
    """Open a coherent private view for explicit, owner-reviewed selections.

    This function does not authorize its caller or make any data public.
    """
    if not revision_id or revision_id != revision_id.strip():
        raise GuestNativeGraphError("Exact Graph revision is required")
    binding = resolve_managed_world_binding(managed_world_id)
    repository = native_registry_source.read_repository()
    if repository.get_head(binding.native_world_id) is None:
        raise GuestNativeGraphError("Native Graph head is unavailable")
    context, access, _, _ = native_registry_source.read_context(
        repository, binding.native_world_id, revision_id, None,
        role="gm", scope_mode="world",
    )
    support = EntityReadService().list_entities_with_support(context)
    if support.listing.identity.revision_id != revision_id:
        raise GuestNativeGraphError("Native Graph revision changed")
    if support.listing.completeness.status != "complete":
        raise GuestNativeGraphError("Native Graph listing is incomplete")
    if resolve_managed_world_binding(managed_world_id) != binding:
        raise GuestNativeGraphError("Native Graph binding changed during read")
    return binding, context, support, access


def read_player_graph(*, managed_world_id: str, revision_id: str):
    """Read the requested vNext revision; never broaden player visibility."""
    if not revision_id or revision_id != revision_id.strip():
        raise GuestNativeGraphError("Exact Graph revision is required")
    binding = resolve_managed_world_binding(managed_world_id)
    repository = native_registry_source.read_repository()
    head = repository.get_head(binding.native_world_id)
    if head is None:
        raise GuestNativeGraphError("Native Graph head is unavailable")
    context, access, _, _ = native_registry_source.read_context(
        repository, binding.native_world_id, revision_id, None,
        role="player", scope_mode="world",
    )
    support = EntityReadService().list_entities_with_support(context)
    if support.listing.identity.revision_id != revision_id:
        raise GuestNativeGraphError("Native Graph revision changed")
    snapshot = WorldGraphProjectionSnapshot(
        world_id=binding.native_world_id, campaign_id="", revision_id=revision_id,
        head_revision_id=head.head_revision_id, is_head=head.head_revision_id == revision_id,
        focus=WorldGraphProjectionFocus(), admissibility="player", scope_mode="world",
    )
    projection = project_native_world(context, support, snapshot, access=access,
                                      managed_world_id=managed_world_id)
    # Ordinary admitted source bodies are owner/GM-only even when an assertion
    # is player-visible. Inspect only explicitly selected evidence with the
    # owner's private view, without broadening the Graph projection or output.
    _, owner_access, _, _ = native_registry_source.read_context(
        repository, binding.native_world_id, revision_id, None,
        role="gm", scope_mode="world",
    )
    if owner_access.source_view.epoch != access.source_view.epoch:
        raise GuestNativeGraphError("Native source authority changed during read")
    if resolve_managed_world_binding(managed_world_id) != binding:
        raise GuestNativeGraphError("Native Graph binding changed during read")
    return binding, projection, owner_access
