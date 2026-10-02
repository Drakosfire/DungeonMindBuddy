"""DungeonMind #96 adapter for MIND-minted empty KnowledgeSpace genesis."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any


def provision_empty_world_space(
    *, allocation_id: str, database_url: str | None = None
) -> Any:
    """Ask DungeonMind to mint and durably provision one empty native space."""
    from dungeonmind.application.vnext import create_empty_space
    from dungeonmind.infrastructure.postgres.database import PostgresDatabase
    from dungeonmind.infrastructure.postgres.vnext_knowledge import (
        PostgresKnowledgeRevisionRepository,
    )

    from apps.live_control_server.config import world_graph_authority_database_url
    from graph_memory.vnext import (
        dungeonbuddy_dnd5e_custom_predicate_profile,
        dungeonbuddy_world_domain_contract,
    )

    dsn = (database_url or world_graph_authority_database_url() or "").strip()
    if not dsn:
        raise RuntimeError("DungeonMind World authority database URL is not configured")
    repository = PostgresKnowledgeRevisionRepository(PostgresDatabase(dsn))
    return create_empty_space(
        repository=repository,
        allocation_id=allocation_id,
        created_at=datetime.now(UTC),
        domain_contract=dungeonbuddy_world_domain_contract(),
        semantic_profile=dungeonbuddy_dnd5e_custom_predicate_profile(),
    )
