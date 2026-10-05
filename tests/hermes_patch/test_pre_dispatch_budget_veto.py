from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
PATCHED_SOURCE = REPOSITORY_ROOT / "out" / "hermes-agent"
UPSTREAM_TEST = PATCHED_SOURCE / "tests" / "agent" / "test_pre_dispatch_budget_veto.py"


def test_pinned_hermes_dispatch_boundary_suite() -> None:
    assert UPSTREAM_TEST.is_file(), "prepare patched Hermes before running this owning-boundary test"
    env = os.environ.copy()
    env["PYTHONPATH"] = str(PATCHED_SOURCE)
    completed = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", str(UPSTREAM_TEST)],
        cwd=PATCHED_SOURCE,
        env=env,
        capture_output=True,
        check=False,
        text=True,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert "12 passed" in completed.stdout
