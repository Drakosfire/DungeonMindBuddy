"""CLI-boundary tests for the PR006D2 bootstrap contract."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

SCRIPT = Path("scripts/activate_eldyrwild_world_bootstrap.py")


def _run(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = {
        **os.environ,
        "PYTHONPATH": f"{Path.cwd() / 'src'}:{Path.cwd()}",
    }
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args, "--root", str(root)],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )


def test_cli_status_prepare_confirm_and_repeat_use_same_contract(tmp_path: Path) -> None:
    status = _run(tmp_path, "status")
    assert status.returncode == 0
    assert json.loads(status.stdout)["state"] == "ready"

    prepared = _run(tmp_path, "prepare", "--actor", "gm")
    assert prepared.returncode == 0
    prepared_payload = json.loads(prepared.stdout)
    assert prepared_payload["schema"] == "dmb_world_graph_bootstrap_prepare_v1"

    confirmed = _run(
        tmp_path,
        "confirm",
        "--actor",
        "gm",
        "--proposal-id",
        prepared_payload["proposalId"],
        "--confirm-token",
        prepared_payload["confirmToken"],
    )
    assert confirmed.returncode == 0
    assert json.loads(confirmed.stdout)["published"] is True

    repeated = _run(
        tmp_path,
        "confirm",
        "--actor",
        "gm",
        "--proposal-id",
        prepared_payload["proposalId"],
        "--confirm-token",
        prepared_payload["confirmToken"],
    )
    assert repeated.returncode == 0
    repeated_payload = json.loads(repeated.stdout)
    assert repeated_payload["published"] is False
    assert repeated_payload["state"] == "active"


def test_cli_errors_are_structured_and_nonzero(tmp_path: Path) -> None:
    result = _run(tmp_path, "prepare", "--actor", "")

    assert result.returncode != 0
    payload = json.loads(result.stdout)
    assert payload["schema"] == "dmb_world_graph_bootstrap_error_v1"
    assert payload["code"] == "invalid_actor"
    assert payload["statusCode"] == 422


def test_cli_exposes_no_arbitrary_bundle_or_force_controls() -> None:
    env = {
        **os.environ,
        "PYTHONPATH": f"{Path.cwd() / 'src'}:{Path.cwd()}",
    }
    help_result = subprocess.run(
        [sys.executable, str(SCRIPT), "prepare", "--help"],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )

    assert help_result.returncode == 0
    assert "--bundle" not in help_result.stdout
    assert "--force" not in help_result.stdout
    assert "--skip-validation" not in help_result.stdout
