"""DungeonBuddy readiness projection for DungeonMind statblock v1."""
from __future__ import annotations

from apps.live_control_server.integrations.dungeonmind_statblocks.client import (
    DungeonMindStatblockV1Client,
    StatblockV1Client,
)
from apps.live_control_server.integrations.dungeonmind_statblocks.config import (
    StatblockIntegrationConfigError,
    load_statblock_integration_config,
)
from apps.live_control_server.integrations.dungeonmind_statblocks.errors import (
    StatblockIntegrationError,
    redact_secret,
)
from apps.live_control_server.integrations.dungeonmind_statblocks.models import (
    StatblockIntegrationReadinessV1,
)

_GENERATION_CAPS = frozenset({"candidate_generate"})
_READ_CAPS = frozenset(
    {
        "candidate_read",
        "statblock_read",
        "statblock_revision_read",
        "statblock_revision_list",
    }
)
_PERSISTENCE_CAPS = frozenset(
    {
        "statblock_create",
        "statblock_revision_append",
    }
)


def project_buddy_capabilities(
    *,
    downstream_capabilities: list[str],
    generation_enabled: bool,
    read_routes_enabled: bool,
) -> list[str]:
    """Project honest Buddy-facing capability labels from Server advertisements."""
    advertised = set(downstream_capabilities)
    projected: list[str] = []
    if generation_enabled and advertised & _GENERATION_CAPS:
        projected.append("generation")
    if read_routes_enabled and advertised & _READ_CAPS:
        projected.append("read")
    if read_routes_enabled and advertised & _PERSISTENCE_CAPS:
        projected.append("persistence")
    return projected


def build_local_unavailable_readiness(
    *,
    configured: bool,
    diagnostics: list[str],
) -> StatblockIntegrationReadinessV1:
    return StatblockIntegrationReadinessV1(
        configured=configured,
        available=False,
        downstream_status="unavailable",
        diagnostics=diagnostics,
    )


def _secret_from_client(client: StatblockV1Client) -> str:
    config = getattr(client, "config", None)
    if config is None:
        return ""
    return str(getattr(config, "internal_api_key", "") or "")


def _public_diagnostics(items: list[str], *, secret: str) -> list[str]:
    return [redact_secret(item, secret) for item in items if item]


def _probe_downstream(client: StatblockV1Client) -> StatblockIntegrationReadinessV1:
    secret = _secret_from_client(client)
    try:
        readiness = client.get_readiness()
        health = client.get_health()
    except StatblockIntegrationError as exc:
        return StatblockIntegrationReadinessV1(
            configured=True,
            available=False,
            downstream_status=exc.category,
            diagnostics=_public_diagnostics([exc.category, exc.message], secret=secret),
        )

    available = readiness.status == "ready"
    capabilities = project_buddy_capabilities(
        downstream_capabilities=health.capabilities,
        generation_enabled=readiness.generation_enabled,
        read_routes_enabled=readiness.read_routes_enabled,
    )
    diagnostics = list(readiness.errors)
    if readiness.detail:
        diagnostics.append(readiness.detail)
    return StatblockIntegrationReadinessV1(
        configured=True,
        available=available,
        downstream_status=readiness.status,
        contract=health.contract,
        contract_version=health.contract_version,
        capabilities=capabilities,
        diagnostics=_public_diagnostics(diagnostics, secret=secret),
    )


def evaluate_statblock_integration_readiness(
    *,
    client: StatblockV1Client | None = None,
) -> StatblockIntegrationReadinessV1:
    if client is not None:
        return _probe_downstream(client)

    try:
        config = load_statblock_integration_config()
    except StatblockIntegrationConfigError as exc:
        return build_local_unavailable_readiness(
            configured=False,
            diagnostics=[exc.category, str(exc)],
        )

    if not config.enabled:
        return build_local_unavailable_readiness(
            configured=False,
            diagnostics=["integration_disabled"],
        )

    if not config.is_configured:
        return build_local_unavailable_readiness(
            configured=False,
            diagnostics=["integration_misconfigured"],
        )

    active_client = DungeonMindStatblockV1Client(config=config)
    try:
        return _probe_downstream(active_client)
    finally:
        active_client.close()
