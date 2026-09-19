"""Shared async-to-sync execution helper. Event-loop mechanics only."""

from __future__ import annotations

import asyncio

import pytest

from src.llm.generation_sync import run_awaitable_sync


async def _ok() -> int:
    return 7


async def _boom() -> int:
    raise ValueError("nope")


def test_run_awaitable_sync_without_running_loop() -> None:
    assert run_awaitable_sync(_ok) == 7


def test_run_awaitable_sync_with_running_loop() -> None:
    async def _inside() -> int:
        return run_awaitable_sync(_ok)

    assert asyncio.run(_inside()) == 7


def test_run_awaitable_sync_reraises() -> None:
    with pytest.raises(ValueError, match="nope"):
        run_awaitable_sync(_boom)


def test_run_awaitable_sync_reraises_from_running_loop() -> None:
    async def _inside() -> int:
        return run_awaitable_sync(_boom)

    with pytest.raises(ValueError, match="nope"):
        asyncio.run(_inside())
