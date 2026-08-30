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
os.environ.setdefault(
    "DUNGEONMIND_WORLD_GRAPH_AUTHORITY_DATABASE_URL",
    "postgresql://unused",
)

# Import witness body only after the blocker is armed.
from tests._cutover_d3a_excision_witness_body import run_witness

run_witness()
'''


def test_fresh_interpreter_mounted_graph_engine_excision() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        env = os.environ.copy()
        env["DMB_D3A_WITNESS_ROOT"] = tmp
        env["PYTHONPATH"] = str(REPO_ROOT)
        # Required PG witnesses must not skip: pin the local cutover test DSN when unset.
        env.setdefault(
            "DMB_CUTOVER_TEST_DATABASE_URL",
            "postgresql://dungeonmind:dungeonmind-dev@127.0.0.1:54329/dmb_cutover_test",
        )
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


def test_mounted_projection_retrieval_source_has_no_kernel_escape() -> None:
    """Static proof: mounted projection/retrieval cannot call Kernel/passthrough."""
    from tests._cutover_d3a_excision_witness_body import (
        _assert_mounted_services_have_no_kernel_escape,
    )

    _assert_mounted_services_have_no_kernel_escape()
