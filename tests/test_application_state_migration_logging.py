"""Regression coverage for application loggers during Alembic setup."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from textwrap import dedent


def test_offline_alembic_environment_preserves_agent_trace_logger() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    script = dedent(
        """
        import logging

        from alembic import command
        from application_state.cli import alembic_config
        from apps.live_control_server.services.agent_turn_trace import LOGGER

        captured = []

        class CaptureTrace(logging.Handler):
            def emit(self, record):
                captured.append(record)

        handler = CaptureTrace()
        handler.setLevel(logging.INFO)
        LOGGER.setLevel(logging.INFO)
        LOGGER.addHandler(handler)

        assert LOGGER.disabled is False
        command.upgrade(alembic_config(), "head", sql=True)
        assert LOGGER.disabled is False
        LOGGER.info("offline migration trace logger regression")
        assert len(captured) == 1
        assert captured[0].name == "dmb.agent.turn_trace"
        assert captured[0].getMessage() == "offline migration trace logger regression"
        """
    )
    env = os.environ.copy()
    pythonpath = [str(repo_root / "src"), str(repo_root)]
    if env.get("PYTHONPATH"):
        pythonpath.append(env["PYTHONPATH"])
    env["PYTHONPATH"] = os.pathsep.join(pythonpath)
    env["DUNGEONBUDDY_APPLICATION_STATE_DATABASE_URL"] = (
        "postgresql://offline:offline@127.0.0.1:1/rake_logger_offline"
    )

    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=repo_root,
        env=env,
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )

    assert result.returncode == 0, f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
