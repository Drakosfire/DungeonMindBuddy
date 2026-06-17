from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = REPO_ROOT / "evals" / "graph_memory_layer" / "baseline_cases.json"
REQUIRED_BASELINE_FAMILIES = {
    "roster_identity",
    "clean_control",
    "location_hierarchy",
    "alias_identity_bridge",
    "session_scoped_final_beat",
    "breadcrumb_natural_query",
    "unresolved_hook_resurfacing",
    "hub_over_attraction",
    "authority_boundary",
    "citation_grounding",
}


def load_manifest() -> dict[str, Any]:
    with MANIFEST_PATH.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    assert isinstance(data, dict)
    return data


def test_baseline_case_manifest_exists() -> None:
    assert MANIFEST_PATH.is_file()


def test_baseline_case_validator_exits_zero() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "evals.graph_memory_layer.validate_baseline_cases"],
        cwd=REPO_ROOT,
        check=False,
        text=True,
        capture_output=True,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "- baseline case manifest: ready" in result.stdout


def test_baseline_case_ids_are_unique() -> None:
    cases = load_manifest()["cases"]
    case_ids = [case["case_id"] for case in cases]

    assert len(case_ids) == len(set(case_ids))


def test_required_baseline_families_are_present() -> None:
    cases = load_manifest()["cases"]
    families = {case["failure_family"] for case in cases}

    assert REQUIRED_BASELINE_FAMILIES <= families


def test_every_case_has_must_preserve() -> None:
    cases = load_manifest()["cases"]

    assert all(case.get("must_preserve") for case in cases)
    assert all(isinstance(case["must_preserve"], list) for case in cases)


def test_every_case_has_must_improve_or_measure() -> None:
    cases = load_manifest()["cases"]

    assert all(case.get("must_improve_or_measure") for case in cases)
    assert all(isinstance(case["must_improve_or_measure"], list) for case in cases)


def test_every_case_has_future_graph_expectation() -> None:
    cases = load_manifest()["cases"]

    assert all(case.get("future_graph_expectation") for case in cases)
    assert all(isinstance(case["future_graph_expectation"], str) for case in cases)
