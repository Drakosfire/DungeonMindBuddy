from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
PATCHED_SOURCE = REPOSITORY_ROOT / "out" / "hermes-agent"
UPSTREAM_TEST = PATCHED_SOURCE / "tests" / "agent" / "test_pre_dispatch_budget_veto.py"


def test_pinned_hermes_dispatch_boundary_suite() -> None:
    assert UPSTREAM_TEST.is_file(), "prepare patched Hermes before running this owning-boundary test"
    env = os.environ.copy()
    with tempfile.TemporaryDirectory(prefix="dmb-hermes-offline-test-") as stub_root:
        Path(stub_root, "sitecustomize.py").write_text(
            """
import os
from pathlib import Path
import faulthandler
import requests

faulthandler.dump_traceback_later(20, repeat=True)
Path(os.environ["DMB_HERMES_TEST_SITE_MARKER"]).write_text("loaded")

class _ModelsDevResponse:
    def raise_for_status(self):
        return None

    def json(self):
        return {"openai": {"models": {}}}

def _offline_get(url, *_args, **_kwargs):
    if url != "https://models.dev/api.json":
        raise AssertionError("unexpected HTTP request in offline Hermes guard test")
    return _ModelsDevResponse()

requests.get = _offline_get
requests.post = lambda *_args, **_kwargs: (_ for _ in ()).throw(
    AssertionError("unexpected HTTP request in offline Hermes guard test")
)
requests.request = lambda *_args, **_kwargs: (_ for _ in ()).throw(
    AssertionError("unexpected HTTP request in offline Hermes guard test")
)
""",
            encoding="utf-8",
        )
        env["PYTHONPATH"] = os.pathsep.join((stub_root, str(PATCHED_SOURCE)))
        env["DMB_HERMES_TEST_SITE_MARKER"] = str(Path(stub_root, "sitecustomize-ran"))
        try:
            completed = subprocess.run(
                [sys.executable, "-m", "pytest", "-vv", str(UPSTREAM_TEST)],
                cwd=PATCHED_SOURCE,
                env=env,
                capture_output=True,
                check=False,
                text=True,
                timeout=90,
            )
        except subprocess.TimeoutExpired as exc:
            stdout = (exc.stdout or b"").decode(errors="replace")
            stderr = (exc.stderr or b"").decode(errors="replace")
            pytest.fail(
                "pinned Hermes dispatch-boundary tests exceeded 90 seconds; "
                f"offline sitecustomize loaded: {Path(stub_root, 'sitecustomize-ran').is_file()}\n"
                + stdout
                + stderr
            )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert "12 passed" in completed.stdout
