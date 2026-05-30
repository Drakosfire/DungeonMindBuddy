from __future__ import annotations

from fastapi import FastAPI

from apps.live_control_server.routes.live import router as live_router
from apps.live_control_server.routes.recap_ingest import router as recap_ingest_router


def create_app() -> FastAPI:
    application = FastAPI(
        title="DungeonMindBuddy Live Control",
        version="0.1.0",
        description="L3 live-play API over file-backed session state (query spine + surface/jobs).",
    )
    application.include_router(live_router)
    application.include_router(recap_ingest_router)

    @application.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return application


app = create_app()
