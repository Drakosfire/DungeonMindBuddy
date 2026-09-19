"""Run awaitables to completion from synchronous Buddy callers.

This module is an event-loop / thread bridge only. It does not select models
or providers, construct requests, apply prompts or schemas, retry, observe
inference, or encode product policy.
"""

from __future__ import annotations

import asyncio
import threading
from collections.abc import Awaitable, Callable
from typing import TypeVar

T = TypeVar("T")


def run_awaitable_sync(factory: Callable[[], Awaitable[T]]) -> T:
    """Run a coroutine to completion without nested ``asyncio.run()``.

    Ordinary sync callers get a fresh event loop. If this thread already has a
    running loop, the coroutine runs on a dedicated worker thread with its own
    loop and this call blocks until that worker finishes. The original exception
    is re-raised if the factory fails.
    """
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(factory())

    holder: list[T] = []
    error: list[BaseException] = []

    def _worker() -> None:
        try:
            holder.append(asyncio.run(factory()))
        except BaseException as exc:
            error.append(exc)

    thread = threading.Thread(target=_worker, name="generation-sync-bridge")
    thread.start()
    thread.join()
    if error:
        raise error[0]
    return holder[0]
