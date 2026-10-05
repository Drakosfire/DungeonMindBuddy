from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
PREPARE_SCRIPT = REPOSITORY_ROOT / "scripts" / "prepare_patched_hermes.py"
PATCH_PATH = REPOSITORY_ROOT / "patches" / "hermes-agent" / "0001-pre-dispatch-budget-veto.patch"
SOURCE_PATH = REPOSITORY_ROOT / "out" / "hermes-agent"


def test_prepared_hermes_identity_and_installed_subprocess_import() -> None:
    verified = subprocess.run(
        [sys.executable, str(PREPARE_SCRIPT), "--verify"],
        cwd=REPOSITORY_ROOT,
        capture_output=True,
        check=True,
        text=True,
    )
    manifest = json.loads(verified.stdout)
    patch_sha = hashlib.sha256(PATCH_PATH.read_bytes()).hexdigest()
    assert manifest["patch_sha256"] == patch_sha
    assert manifest["upstream_commit"] == "861d69c7bba8d2ea6a1cd170e989c901c74d32d1"
    assert manifest["tree_sha"] == manifest["expected_tree_sha"]
    assert (SOURCE_PATH / "agent" / "api_request_budget.py").is_file()

    import_probe = """
import json
from pathlib import Path
from importlib.metadata import distribution
import agent.api_request_budget as budget

print(json.dumps({
    "module": str(Path(budget.__file__).resolve()),
    "distribution": str(Path(distribution("hermes-agent").locate_file("")).resolve()),
    "veto_is_terminal": issubclass(budget.ApiRequestBudgetVeto, BaseException)
        and not issubclass(budget.ApiRequestBudgetVeto, Exception),
}))
"""
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    imported = subprocess.run(
        [sys.executable, "-c", import_probe],
        cwd=REPOSITORY_ROOT,
        env=env,
        capture_output=True,
        check=True,
        text=True,
    )
    result = json.loads(imported.stdout)
    module_path = Path(result["module"])
    assert module_path.is_relative_to(Path(result["distribution"]))
    assert not module_path.is_relative_to(SOURCE_PATH)
    assert result["veto_is_terminal"] is True
