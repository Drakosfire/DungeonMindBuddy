from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def test_graph_memory_smoke_runner_exits_zero() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "evals.graph_memory_layer.run_smoke"],
        cwd=Path(__file__).resolve().parents[1],
        check=False,
        text=True,
        capture_output=True,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "no-LLM baseline scaffold: ready" in result.stdout


def test_graph_memory_scaffold_files_exist() -> None:
    repo_root = Path(__file__).resolve().parents[1]

    assert (repo_root / "Docs/Experiments/GRAPH-MEMORY-FORK-TRACKING.md").is_file()
    assert (repo_root / "evals/graph_memory_layer/README.md").is_file()
    assert (repo_root / "evals/graph_memory_layer/run_smoke.py").is_file()
    assert (
        repo_root / "evals/graph_memory_layer/artifacts/baseline/BASELINE-NOTES.md"
    ).is_file()
