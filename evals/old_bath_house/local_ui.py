"""Serve the pinned image's SPA in its isolated local-operator runtime."""

from pathlib import Path

from apps.live_control_server.hosted_worker import app as buddy
from starlette.responses import FileResponse

_DIST = Path("/app/apps/live-control-ui/dist").resolve()


async def app(scope, receive, send):
    if scope["type"] == "http" and scope["method"] in {"GET", "HEAD"}:
        path = scope["path"]
        requested = (_DIST / path.lstrip("/")).resolve()
        if requested.is_relative_to(_DIST):
            if path.startswith("/assets/") and requested.is_file():
                await FileResponse(requested)(scope, receive, send)
                return
            if path in {"/", "/build", "/statblock", "/combat", "/plan", "/play"}:
                await FileResponse(_DIST / "index.html")(scope, receive, send)
                return
    await buddy(scope, receive, send)
