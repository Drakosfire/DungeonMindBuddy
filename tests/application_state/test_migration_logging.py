"""Regression for logger state changed by the real Alembic environment."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from textwrap import dedent


def test_alembic_environment_preserves_existing_agent_trace_logger() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    env = os.environ.copy()
    env["DUNGEONBUDDY_APPLICATION_STATE_DATABASE_URL"] = (
        "postgresql://unused:unused@127.0.0.1/dmb_migration_logging_test"
    )
    for name in (
        "DUNGEONMIND_WORLD_GRAPH_AUTHORITY_DATABASE_URL",
        "DUNGEONMIND_DATABASE_URL",
        "DMB_CUTOVER_TEST_DATABASE_URL",
    ):
        env[name] = ""
    env["PYTHONPATH"] = os.pathsep.join(
        (str(repo_root / "src"), str(repo_root))
    )
    script = dedent(
        """
        import logging
        from io import StringIO

        from alembic import command
        from application_state.cli import alembic_config

        trace_logger = logging.getLogger("dmb.agent.turn_trace")
        trace_logger.disabled = False
        command.upgrade(alembic_config(), "head", sql=True)

        stream = StringIO()
        trace_handler = logging.StreamHandler(stream)
        trace_logger.addHandler(trace_handler)
        trace_logger.setLevel(logging.INFO)
        trace_logger.info("dmb.agent.turn_trace regression sentinel")
        trace_handler.flush()
        event_captured = (
            "dmb.agent.turn_trace regression sentinel" in stream.getvalue()
        )
        print(f"DMB_TRACE_LOGGER_DISABLED={trace_logger.disabled}")
        print(f"DMB_TRACE_EVENT_CAPTURED={event_captured}")
        """
    )

    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=repo_root,
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "DMB_TRACE_LOGGER_DISABLED=False" in result.stdout
    assert "DMB_TRACE_EVENT_CAPTURED=True" in result.stdout
