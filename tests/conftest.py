"""Pytest hooks: load repo ``.env`` so live tests see ``OPENAI_API_KEY`` without shell ``export``."""

from __future__ import annotations

import pytest

from src.bootstrap_env import load_dungeonmindbuddy_dotenv


@pytest.fixture(scope="session", autouse=True)
def _dungeonmindbuddy_dotenv_session() -> None:
    load_dungeonmindbuddy_dotenv()


@pytest.fixture(autouse=True)
def _live_play_classifier_heuristic_fallback(monkeypatch: pytest.MonkeyPatch, request: pytest.FixtureRequest) -> None:
    """Keep L2/L3 live-play tests deterministic without mandating an LLM call per assertion."""
    if "test_live_play" in request.node.nodeid:
        monkeypatch.setenv("LIVE_TURN_CLASSIFIER_ALLOW_HEURISTIC_FALLBACK", "1")
