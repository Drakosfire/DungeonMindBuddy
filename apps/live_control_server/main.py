from __future__ import annotations

from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI

from apps.live_control_server.routes.graph_authoring import router as graph_authoring_router
from apps.live_control_server.routes.graph_preview import router as graph_preview_router
from apps.live_control_server.routes.live import router as live_router
from apps.live_control_server.routes.party_registry import router as party_registry_router
from apps.live_control_server.routes.recap_ingest import router as recap_ingest_router
from apps.live_control_server.routes.world_graph_bootstrap import (
    router as world_graph_bootstrap_router,
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
from apps.live_control_server.services.hermes_graph_agent_host import (
    get_hermes_graph_agent_host,
    shutdown_hermes_graph_agent_host,
)
from src.bootstrap_env import load_dungeonmindbuddy_dotenv

load_dungeonmindbuddy_dotenv()


@asynccontextmanager
async def lifespan(_application: FastAPI) -> AsyncIterator[None]:
    """Own Hermes graph-agent host lifecycle for deterministic shutdown."""
    # Lazy start on first execute remains allowed; shutdown ownership is required.
    get_hermes_graph_agent_host()
    try:
        yield
    finally:
        shutdown_hermes_graph_agent_host()


def create_app() -> FastAPI:
    application = FastAPI(
        title="DungeonMindBuddy Live Control",
        version="0.1.0",
        description="L3 live-play API over file-backed session state (query spine + surface/jobs).",
        lifespan=lifespan,
    )
    application.include_router(live_router)
    application.include_router(graph_preview_router)
    application.include_router(graph_authoring_router)
    application.include_router(recap_ingest_router)
    application.include_router(party_registry_router)
    application.include_router(world_graph_bootstrap_router)
    application.include_router(world_graph_projection_router)
    application.include_router(world_graph_retrieval_router)
    application.include_router(workspace_documents_router)

    @application.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return application


app = create_app()
