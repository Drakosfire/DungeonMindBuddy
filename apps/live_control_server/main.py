from __future__ import annotations

from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
import os
from pathlib import Path
from urllib.parse import urlencode

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import (
    FileResponse,
    JSONResponse,
    PlainTextResponse,
    RedirectResponse,
    Response,
)
from apps.live_control_server.routes.conversation_library import router as conversation_library_router
from apps.live_control_server.routes.conversation_work_plans import router as conversation_work_plans_router
from apps.live_control_server.routes.rules_lookup import router as rules_lookup_router

from apps.live_control_server.routes.media_images import router as media_images_router

from apps.live_control_server.routes.graph_authoring import router as graph_authoring_router
from apps.live_control_server.routes.agent_graph_local_session import (
    router as agent_graph_local_session_router,
)
from apps.live_control_server.routes.combat_encounters import router as combat_encounters_router
from apps.live_control_server.routes.combat_run_encounters import router as combat_run_encounters_router
from apps.live_control_server.routes.combat_scene_templates import router as combat_scene_templates_router
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
from apps.live_control_server.services.dms_principal import (
    DMS_SESSION_COOKIE_NAME,
    DmsPrincipalResolver,
    fixed_dms_api_origin,
)
from apps.live_control_server.services.hosted_auth import (
    AUTH_SESSION_PATH,
    CURRENT_USER_PATH,
    DMS_API_ORIGIN_ENV,
    HOSTED_MODE,
    LOGIN_PATH,
    LOGOUT_PATH,
    PRODUCTION_ENVIRONMENT,
    auth_mode,
    deployment_environment,
    install_hosted_request_boundary,
    safe_hosted_return_path,
    validate_hosted_auth_configuration,
)
from apps.live_control_server.services.trusted_cookie_origin import require_cookie_write_origin
from src.bootstrap_env import load_dungeonmindbuddy_dotenv

load_dungeonmindbuddy_dotenv()


def _load_graph_preview_router():
    """Keep fixture-backed gold review out of the hosted production package.

    This developer surface imports evaluation fixtures containing campaign
    material. Production images exclude evals; local source checkouts retain
    the route when those tracked sources are present.
    """
    if deployment_environment() == PRODUCTION_ENVIRONMENT:
        return None
    try:
        from apps.live_control_server.routes.graph_preview import router
    except ModuleNotFoundError as exc:
        if exc.name == "evals" or (exc.name and exc.name.startswith("evals.")):
            return None
        raise
    return router


@asynccontextmanager
async def lifespan(_application: FastAPI) -> AsyncIterator[None]:
    """Prepare local Agent dependencies and own deterministic host shutdown."""
    dms_http_client: httpx.AsyncClient | None = None
    if deployment_environment() == PRODUCTION_ENVIRONMENT:
        config_errors = validate_hosted_auth_configuration()
        if config_errors:
            raise RuntimeError(
                "hosted_auth_configuration_invalid:" + ",".join(config_errors)
            )
        dms_http_client = httpx.AsyncClient(timeout=5.0, follow_redirects=False)
        _application.state.dms_principal_resolver = DmsPrincipalResolver(
            api_origin=os.environ[DMS_API_ORIGIN_ENV],
            http_client=dms_http_client,
        )
        _application.state.dms_http_client = dms_http_client
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
        if dms_http_client is not None:
            await dms_http_client.aclose()


def create_app() -> FastAPI:
    graph_preview_router = _load_graph_preview_router()
    application = FastAPI(
        title="DungeonMindBuddy Live Control",
        version="0.1.0",
        description="L3 live-play API over file-backed session state (query spine + surface/jobs).",
        lifespan=lifespan,
    )
    application.include_router(live_router)
    application.include_router(conversation_library_router)
    application.include_router(conversation_work_plans_router)
    application.include_router(combat_encounters_router)
    application.include_router(combat_scene_templates_router)
    application.include_router(combat_run_encounters_router)
    application.include_router(world_mechanics_router)
    application.include_router(media_images_router)
    application.include_router(agent_graph_local_session_router)
    if graph_preview_router is not None:
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

    install_hosted_request_boundary(application)

    @application.get(CURRENT_USER_PATH, include_in_schema=False)
    async def current_user(request: Request) -> dict[str, str]:
        principal = getattr(request.state, "dms_principal", None)
        if principal is None:
            raise HTTPException(status_code=401, detail="Authentication required")
        return {"sub": principal.subject}

    @application.get(LOGIN_PATH, include_in_schema=False)
    async def hosted_login(request: Request) -> Response:
        environment = deployment_environment()
        mode = auth_mode()
        if environment in {"local", "development", "dev"} and mode == "local_operator":
            return JSONResponse(
                status_code=409,
                content={"detail": {"code": "hosted_login_not_required"}},
            )
        if environment != PRODUCTION_ENVIRONMENT or mode != HOSTED_MODE:
            return JSONResponse(
                status_code=503,
                content={"detail": {"code": "hosted_auth_unavailable"}},
            )
        api_origin = fixed_dms_api_origin(os.environ.get(DMS_API_ORIGIN_ENV, ""))
        if api_origin is None:
            return JSONResponse(
                status_code=503,
                content={"detail": {"code": "hosted_auth_unavailable"}},
            )
        return_values = request.query_params.getlist("return_to")
        return_to = safe_hosted_return_path(
            return_values[0] if len(return_values) == 1 else "/"
        )
        query = urlencode({"frontend": "buddy", "redirect": return_to})
        return RedirectResponse(
            url=f"{api_origin}/api/auth/login?{query}",
            status_code=302,
        )

    @application.get(AUTH_SESSION_PATH, include_in_schema=False)
    async def auth_session(request: Request) -> Response:
        environment = deployment_environment()
        mode = auth_mode()
        if environment in {"local", "development", "dev"} and mode == "local_operator":
            return JSONResponse(content={"status": "local_operator"})
        if environment != PRODUCTION_ENVIRONMENT or mode != HOSTED_MODE:
            return JSONResponse(
                status_code=503,
                content={"status": "unavailable"},
            )
        resolver = getattr(request.app.state, "dms_principal_resolver", None)
        if resolver is None or not hasattr(resolver, "resolve"):
            return JSONResponse(status_code=503, content={"status": "unavailable"})
        result = await resolver.resolve(request)
        if result.status == "authenticated" and result.principal is not None:
            return JSONResponse(content={"status": "authenticated"})
        if result.status == "signed_out":
            return JSONResponse(status_code=401, content={"status": "signed_out"})
        return JSONResponse(status_code=503, content={"status": "unavailable"})

    @application.post(LOGOUT_PATH, status_code=204, include_in_schema=False)
    async def logout(request: Request) -> Response:
        if deployment_environment() != PRODUCTION_ENVIRONMENT or auth_mode() != HOSTED_MODE:
            raise HTTPException(status_code=503, detail="Hosted logout is unavailable")
        require_cookie_write_origin(
            request,
            trusted_origins=tuple(
                item.strip()
                for item in os.environ.get("AUTH_TRUSTED_FRONTEND_ORIGINS", "").split(",")
                if item.strip()
            ),
        )
        origins = request.headers.getlist("origin")
        cookie_value = request.cookies.get(DMS_SESSION_COOKIE_NAME)
        headers = {"Origin": origins[0]}
        if cookie_value:
            headers["Cookie"] = f"{DMS_SESSION_COOKIE_NAME}={cookie_value}"
        client: httpx.AsyncClient | None = getattr(request.app.state, "dms_http_client", None)
        if client is None:
            raise HTTPException(status_code=503, detail="Hosted logout is unavailable")
        dms_url = f"{os.environ[DMS_API_ORIGIN_ENV].rstrip('/')}/api/auth/logout"
        try:
            response = await client.post(dms_url, headers=headers, follow_redirects=False)
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=503, detail="Authentication service unavailable") from exc
        try:
            if response.status_code != 204:
                raise HTTPException(
                    status_code=response.status_code if response.status_code in {401, 403} else 503,
                    detail="Authentication service rejected logout",
                )
            outgoing = Response(status_code=204)
            for name, value in response.headers.multi_items():
                if name.lower() == "set-cookie":
                    outgoing.headers.append(name, value)
            return outgoing
        finally:
            await response.aclose()

    @application.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @application.get("/health/live")
    def health_live() -> dict[str, str]:
        return {"status": "live"}

    @application.get("/health/ready", response_model=None)
    def health_ready() -> dict[str, str] | Response:
        if deployment_environment() != PRODUCTION_ENVIRONMENT:
            return {"status": "ready"}
        config_errors = validate_hosted_auth_configuration()
        if config_errors:
            return JSONResponse(
                status_code=503,
                content={"status": "not_ready", "code": "hosted_configuration_invalid"},
            )
        from apps.live_control_server.services.runtime_preflight import run_runtime_preflight
        from apps.live_control_server.config import repo_root

        report = run_runtime_preflight(repo_root=repo_root(), load_env=False)
        if report.status != "READY":
            return JSONResponse(
                status_code=503,
                content={"status": "not_ready", "code": "runtime_preflight_failed"},
            )
        return {"status": "ready"}

    async def serve_frontend(request: Request, spa_path: str = "") -> Response:
        if deployment_environment() != PRODUCTION_ENVIRONMENT:
            return PlainTextResponse("Not found", status_code=404)
        static_root = (Path(__file__).resolve().parents[1] / "live-control-ui" / "dist").resolve()
        index_path = static_root / "index.html"
        if not index_path.is_file():
            return PlainTextResponse("Frontend build is unavailable", status_code=503)
        requested = (static_root / spa_path).resolve()
        if not requested.is_relative_to(static_root):
            return PlainTextResponse("Not found", status_code=404)
        if requested.is_file():
            return FileResponse(requested)
        if request.headers.get("accept", "").lower().find("text/html") >= 0:
            return FileResponse(index_path)
        return PlainTextResponse("Not found", status_code=404)

    application.add_api_route(
        "/", serve_frontend, methods=["GET", "HEAD"], include_in_schema=False
    )
    application.add_api_route(
        "/{spa_path:path}", serve_frontend, methods=["GET", "HEAD"], include_in_schema=False
    )

    return application


app = create_app()

