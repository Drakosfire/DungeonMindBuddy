"""``src.bootstrap_env`` — repo dotenv loading."""

from __future__ import annotations

from src.bootstrap_env import load_dungeonmindbuddy_dotenv


def test_load_dungeonmindbuddy_dotenv_idempotent() -> None:
    load_dungeonmindbuddy_dotenv()
    load_dungeonmindbuddy_dotenv()
