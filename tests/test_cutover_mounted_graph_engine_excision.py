"""CUTOVER D.3A owning witness: mounted app without legacy graph engine."""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]


WITNESS_SCRIPT = r'''
import os
import sys
from pathlib import Path

FORBIDDEN = (
    "graph_memory.kernel",
    "graph_memory.world_supergraph",
    "graph_memory.union_supergraph",
)


class Blocker:
    def find_spec(self, fullname, path=None, target=None):
        if fullname in FORBIDDEN or any(fullname.startswith(f + ".") for f in FORBIDDEN):
            raise ImportError(f"blocked legacy import: {fullname}")
        return None


# Blocker MUST be installed before app import.
sys.meta_path.insert(0, Blocker())

root = Path(os.environ["DMB_D3A_WITNESS_ROOT"])
os.environ["DUNGEONMIND_WORLD_GRAPH_ROOT"] = str(root)
os.environ.pop("DUNGEONMIND_WORLD_GRAPH_AUTHORITY", None)

legacy = root / "graph_memory" / "worlds"
assert not legacy.exists(), "legacy graph filesystem must be absent before boot"

from apps.live_control_server.main import create_app
from fastapi.testclient import TestClient

app = create_app()
with TestClient(app) as client:
    assert client.get("/health").status_code == 200
    union = client.get("/api/live/graph-preview/union-supergraph/projection")
    assert union.status_code == 410
    assert union.json()["detail"]["code"] == "union_supergraph_preview_retired"
    boot = client.get("/api/live/world-graph-bootstrap/status")
    assert boot.status_code == 410
    assert boot.json()["detail"]["code"] == "world_graph_bootstrap_retired"
    merge = client.post("/api/live/graph-authoring/merge-reconciliation/prepare", json={})
    assert merge.status_code == 410
    assert merge.json()["detail"]["code"] == "graph_authoring_store_retired"
    # Retained Graph Review prepare route stays registered (validation 422 ≠ 404/410).
    prep = client.post("/api/live/graph-authoring/prepare", json={})
    assert prep.status_code != 404
    assert prep.status_code != 410

assert not legacy.exists(), "legacy graph filesystem must remain absent after boot"
loaded = [
    name
    for name in sys.modules
    if any(name == f or name.startswith(f + ".") for f in FORBIDDEN)
]
assert loaded == [], f"forbidden modules loaded: {loaded}"
print("WITNESS_OK")
'''


def test_fresh_interpreter_mounted_graph_engine_excision() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        env = os.environ.copy()
        env["DMB_D3A_WITNESS_ROOT"] = tmp
        env["PYTHONPATH"] = str(REPO_ROOT)
        proc = subprocess.run(
            [sys.executable, "-c", WITNESS_SCRIPT],
            cwd=REPO_ROOT,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        if proc.returncode != 0:
            pytest.fail(
                "mounted excision witness failed\n"
                f"stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
            )
        assert "WITNESS_OK" in proc.stdout
