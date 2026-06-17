from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from evals.graph_memory_layer.run_smoke import validate_git_branch


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
    assert "- experiment doc: found (" in result.stdout


def test_graph_memory_scaffold_files_exist() -> None:
    repo_root = Path(__file__).resolve().parents[1]

    assert (repo_root / "Docs/Experiments/GRAPH-MEMORY-FORK-TRACKING.md").is_file()
    assert (repo_root / "evals/graph_memory_layer/README.md").is_file()
    assert (repo_root / "evals/graph_memory_layer/run_smoke.py").is_file()
    assert (
        repo_root / "evals/graph_memory_layer/artifacts/baseline/BASELINE-NOTES.md"
    ).is_file()


def test_graph_memory_branch_validation_allows_root_branch() -> None:
    assert validate_git_branch("experiment/graph-memory-layer") == []


def test_graph_memory_branch_validation_allows_any_graph_exp_branch() -> None:
    assert validate_git_branch("graph-exp/01-freeze-baseline-reports") == []


def test_graph_memory_branch_validation_blocks_main() -> None:
    assert validate_git_branch("main")


def test_graph_memory_branch_validation_blocks_master() -> None:
    assert validate_git_branch("master")


def test_graph_memory_branch_validation_blocks_codex_branch_in_strict_mode() -> None:
    assert validate_git_branch("codex/add-fork-tracking-and-baseline-scaffold")


def test_graph_memory_branch_validation_supports_expected_branch() -> None:
    assert (
        validate_git_branch(
            "graph-exp/01-freeze-baseline-reports",
            expected_branch="graph-exp/01-freeze-baseline-reports",
        )
        == []
    )


def test_graph_memory_branch_validation_allows_exact_codex_branch() -> None:
    assert (
        validate_git_branch(
            "codex/add-fork-tracking-and-baseline-scaffold",
            expected_branch="codex/add-fork-tracking-and-baseline-scaffold",
        )
        == []
    )


def test_graph_memory_branch_validation_reports_expected_branch_mismatch() -> None:
    assert validate_git_branch(
        "graph-exp/02-graph-ir-schema",
        expected_branch="graph-exp/01-freeze-baseline-reports",
    )
