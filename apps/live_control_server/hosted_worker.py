"""ASGI entry point for a dedicated hosted Buddy worker."""

import gc

from starlette.types import ASGIApp, Receive, Scope, Send

from .main import app as application


def with_startup_gc(app: ASGIApp) -> ASGIApp:
    async def worker(scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "lifespan":
            await app(scope, receive, send)
            return

        async def report(message):
            if message["type"] == "lifespan.startup.complete":
                # The worker has no in-flight requests. Collect existing cycles
                # before moving startup objects out of subsequent GC scans.
                gc.collect()
                gc.freeze()
            await send(message)

        await app(scope, receive, report)

    return worker


app = with_startup_gc(application)
