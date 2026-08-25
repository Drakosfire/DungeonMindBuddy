"""Pytest hooks: load repo ``.env`` so live tests see ``OPENAI_API_KEY`` without shell ``export``.

Switched Content kinds (plan, runbook) own PostgreSQL. Register the disposable
application-state fixture once here and request it for the Content/Play/workspace
regression surface, rather than sprinkling ``pytest_plugins`` through globals.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from apps.live_control_server.config import SESSION_DIR_ENV
from src.bootstrap_env import load_dungeonmindbuddy_dotenv
from tests.application_state.isolate_dsn import needs_disposable_application_state

pytest_plugins = ["tests.application_state.conftest"]


@pytest.fixture(scope="session", autouse=True)
def _dungeonmindbuddy_dotenv_session() -> None:
    load_dungeonmindbuddy_dotenv()


@pytest.fixture(autouse=True)
def _disposable_postgres_for_switched_content_kinds(
    request: pytest.FixtureRequest,
) -> None:
    if not needs_disposable_application_state(request.node.nodeid):
        return
    request.getfixturevalue("application_state_dsn")
    from tests.application_state.playable_binding import clear_playable_bindings

    clear_playable_bindings()


@pytest.fixture(autouse=True)
def _live_play_classifier_heuristic_fallback(monkeypatch: pytest.MonkeyPatch, request: pytest.FixtureRequest) -> None:
    """Keep L2/L3 live-play tests deterministic without mandating an LLM call per assertion."""
    if "test_live_play" in request.node.nodeid:
        monkeypatch.setenv("LIVE_TURN_CLASSIFIER_ALLOW_HEURISTIC_FALLBACK", "1")


@pytest.fixture(autouse=True)
def _isolate_live_server_session_dir(
    monkeypatch: pytest.MonkeyPatch,
    request: pytest.FixtureRequest,
    tmp_path: Path,
) -> None:
    """Prevent tests from mutating tracked ``evals/.../session_22`` fixtures."""
    if "tests/test_live_" not in request.node.nodeid:
        return

    repo_root = Path(__file__).resolve().parents[1]
    seed_session = repo_root / "evals/c2_live_prep/live/session_22"
    isolated = tmp_path / "live_session"
    isolated.mkdir(parents=True, exist_ok=True)
    for name in ("live_packet.json", "surface_layout.json", "current_state.json"):
        shutil.copy2(seed_session / name, isolated / name)
    (isolated / "event_log.jsonl").write_text("", encoding="utf-8")
    (isolated / "job_queue.jsonl").write_text("", encoding="utf-8")
    monkeypatch.setenv(SESSION_DIR_ENV, str(isolated))
