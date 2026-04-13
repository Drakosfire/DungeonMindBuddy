"""Pytest hooks: load repo ``.env`` so live tests see ``OPENAI_API_KEY`` without shell ``export``."""

from __future__ import annotations

import pytest

from src.bootstrap_env import load_dungeonmindbuddy_dotenv


@pytest.fixture(scope="session", autouse=True)
def _dungeonmindbuddy_dotenv_session() -> None:
    load_dungeonmindbuddy_dotenv()
