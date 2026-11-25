import asyncio

import pytest

from apps.live_control_server import hosted_worker


@pytest.mark.parametrize(
    ("scope_type", "message_type", "expected_gc"),
    (
        ("lifespan", "lifespan.startup.complete", ["collect", "freeze"]),
        ("lifespan", "lifespan.startup.failed", []),
        ("lifespan", "lifespan.shutdown.complete", []),
        ("http", "http.response.start", []),
    ),
)
def test_hosted_worker_freezes_before_startup_completion(
    monkeypatch, scope_type, message_type, expected_gc
):
    order = []
    original = {"type": message_type}

    async def app(scope, receive, send):
        await send(original)

    async def receive():
        raise AssertionError("A standalone lifecycle message needs no receive")

    async def send(message):
        assert message is original
        order.append("forward")

    monkeypatch.setattr(hosted_worker.gc, "collect", lambda: order.append("collect"))
    monkeypatch.setattr(hosted_worker.gc, "freeze", lambda: order.append("freeze"))
    worker = hosted_worker.with_startup_gc(app)
    asyncio.run(worker({"type": scope_type}, receive, send))
    assert order == [*expected_gc, "forward"]
