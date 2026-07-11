"""CLI tests for materialize_eldyrwild_c2_world_graph.py (PR006)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts/materialize_eldyrwild_c2_world_graph.py"
MANIFEST = REPO_ROOT / "config/graph_memory/eldyrwild_c2_acceptance_manifest.json"
MINIMAL_MANIFEST = REPO_ROOT / "tests/fixtures/graph_memory/pr006/minimal_acceptance_manifest.json"
MINIMAL_BUNDLE = REPO_ROOT / "tests/fixtures/graph_memory/pr006/minimal_candidate_bundle.json"


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def test_cli_inventory_minimal_manifest(tmp_path: Path) -> None:
    out_path = tmp_path / "inventory.json"
    proc = _run(
        "inventory",
        "--repo-root",
        str(REPO_ROOT),
        "--manifest",
        str(MINIMAL_MANIFEST),
        "--output",
        str(out_path),
    )
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(out_path.read_text(encoding="utf-8"))
    assert payload["world_id"] == "eldyrwild"
    assert payload["recap_count"] == 2


def test_cli_validate_bundle(tmp_path: Path) -> None:
    proc = _run(
        "validate-bundle",
        "--repo-root",
        str(REPO_ROOT),
        "--manifest",
        str(MINIMAL_MANIFEST),
        "--bundle",
        str(MINIMAL_BUNDLE),
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["ok"] is True


def test_cli_materialize_fresh_root(tmp_path: Path) -> None:
    store = tmp_path / "world-store"
    report = tmp_path / "report.json"
    proc = _run(
        "materialize",
        "--repo-root",
        str(REPO_ROOT),
        "--manifest",
        str(MINIMAL_MANIFEST),
        "--bundle",
        str(MINIMAL_BUNDLE),
        "--store-root",
        str(store),
        "--fresh-root",
        "--report",
        str(report),
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["ok"] is True
    assert report.is_file()
