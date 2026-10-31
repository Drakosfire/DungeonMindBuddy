"""Live services cannot depend on the legacy evaluation packaging shim.

The remaining fixture-authoring surfaces are a separate D9 ownership audit.
Ordinary Process no longer imports either packaging entrypoint.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SERVICES_DIR = REPO_ROOT / "apps/live_control_server/services"
FORBIDDEN_MODULE = "evals.graph_memory_layer.graph_preview_runner"


def _service_files() -> list[Path]:
    return sorted(SERVICES_DIR.glob("*.py"))


def _imports_forbidden_module(path: Path) -> bool:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if module == FORBIDDEN_MODULE or module.startswith(FORBIDDEN_MODULE + "."):
                return True
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == FORBIDDEN_MODULE or alias.name.startswith(
                    FORBIDDEN_MODULE + "."
                ):
                    return True
    return False


@pytest.mark.parametrize("path", _service_files(), ids=lambda p: p.name)
def test_live_control_server_services_do_not_import_evals_graph_preview_runner(
    path: Path,
) -> None:
    """No file under apps/live_control_server/services/ may import the evals shim.

    Other evals imports (gold review, gold fixtures) are unaffected — this only
    forbids the specific packaging module that moved to production.
    """
    assert not _imports_forbidden_module(path), (
        f"{path} imports the evals GraphIngest packaging shim "
        f"({FORBIDDEN_MODULE}); use the canonical saved extraction owner instead"
    )
