from __future__ import annotations

from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI
from apps.live_control_server.routes.rules_lookup import router as rules_lookup_router

from apps.live_control_server.routes.media_images import router as media_images_router

from apps.live_control_server.routes.graph_authoring import router as graph_authoring_router
from apps.live_control_server.routes.agent_graph_local_session import (
    router as agent_graph_local_session_router,
)
from apps.live_control_server.routes.graph_preview import router as graph_preview_router
from apps.live_control_server.routes.combat_encounters import router as combat_encounters_router
from apps.live_control_server.routes.world_mechanics_associations import router as world_mechanics_router
from apps.live_control_server.routes.live import router as live_router
from apps.live_control_server.routes.party_registry import router as party_registry_router
from apps.live_control_server.routes.play_runs import router as play_runs_router
from apps.live_control_server.routes.play_prepared_tables import router as play_prepared_tables_router
from apps.live_control_server.routes.recap_ingest import router as recap_ingest_router
from apps.live_control_server.routes.world_graph_bootstrap import (
    router as world_graph_bootstrap_router,
)
from apps.live_control_server.routes.extract_promote import (
    router as extract_promote_router,
)
from apps.live_control_server.routes.world_graph_projection import (
    router as world_graph_projection_router,
)
from apps.live_control_server.routes.world_graph_retrieval import (
    router as world_graph_retrieval_router,
)
from apps.live_control_server.routes.workspace_documents import (
    router as workspace_documents_router,
)
from apps.live_control_server.routes.workspace_lifecycle import (
    router as workspace_lifecycle_router,
)
from apps.live_control_server.routes.world_containers import (
    router as world_containers_router,
)
from apps.live_control_server.routes.statblock_integration import (
    router as statblock_integration_router,
)
from apps.live_control_server.routes.threat_drafts import (
    router as threat_drafts_router,
)
from apps.live_control_server.routes.threat_publication import (
    router as threat_publication_router,
)
from apps.live_control_server.routes.threat_publication_identity import (
    router as threat_publication_identity_router,
)
from apps.live_control_server.routes.threat_publication_proposals import (
    router as threat_publication_proposals_router,
)
from apps.live_control_server.routes.threat_publication_commits import (
    router as threat_publication_commits_router,
)
from apps.live_control_server.routes.threat_query_hydration import (
    router as threat_query_hydration_router,
)
from apps.live_control_server.routes.statblock_candidates import (
    router as statblock_candidates_router,
)
from apps.live_control_server.routes.source_navigation import (
    router as source_navigation_router,
)
from apps.live_control_server.services.hermes_graph_agent_host import (
    get_hermes_graph_agent_host,
    shutdown_hermes_graph_agent_host,
)
from src.bootstrap_env import load_dungeonmindbuddy_dotenv

load_dungeonmindbuddy_dotenv()


@asynccontextmanager
async def lifespan(_application: FastAPI) -> AsyncIterator[None]:
    """Prepare local Agent dependencies and own deterministic host shutdown."""
    from apps.live_control_server.services.agent_turn_trace import configure_turn_trace_logging
    configure_turn_trace_logging()
    from apps.live_control_server.services.build_jev_runtime import prepare_default_build_runtime
    _application.state.build_jev_runtime_factory = prepare_default_build_runtime()
    get_hermes_graph_agent_host()
    try:
        yield
    finally:
        shutdown_hermes_graph_agent_host()
        _application.state.build_jev_runtime_factory = None


def create_app() -> FastAPI:
    application = FastAPI(
        title="DungeonMindBuddy Live Control",
        version="0.1.0",
        description="L3 live-play API over file-backed session state (query spine + surface/jobs).",
        lifespan=lifespan,
    )
    application.include_router(live_router)
    application.include_router(combat_encounters_router)
    application.include_router(world_mechanics_router)
    application.include_router(media_images_router)
    application.include_router(agent_graph_local_session_router)
    application.include_router(graph_preview_router)
    application.include_router(graph_authoring_router)
    application.include_router(recap_ingest_router)
    application.include_router(party_registry_router)
    application.include_router(play_runs_router)
    application.include_router(play_prepared_tables_router)
    application.include_router(world_graph_bootstrap_router)
    application.include_router(extract_promote_router)
    application.include_router(world_graph_projection_router)
    application.include_router(world_graph_retrieval_router)
    application.include_router(rules_lookup_router)
    application.include_router(workspace_documents_router)
    application.include_router(workspace_lifecycle_router)
    application.include_router(world_containers_router)
    application.include_router(statblock_integration_router)
    application.include_router(threat_drafts_router)
    application.include_router(threat_publication_router)
    application.include_router(threat_publication_identity_router)
    application.include_router(threat_publication_proposals_router)
    application.include_router(threat_publication_commits_router)
    application.include_router(threat_query_hydration_router)
    application.include_router(statblock_candidates_router)
    application.include_router(source_navigation_router)

    @application.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return application


app = create_app()
