"""Guard: live recap-ingest packaging must not depend on eval-only code.

``evals/graph_memory_layer/graph_preview_runner.py`` packaging (GraphIngest
manifest/artifact construction) moved to a production-owned module
(``src.graph_memory.extraction.graph_ingest_packaging``). Live services under
``apps/live_control_server/services/`` must import the production module, not
the evals compatibility shim.

This guard is scoped to the ``graph_preview_runner`` packaging module
specifically. Other evals imports in ``apps/live_control_server/services/``
(gold-review comparison helpers, gold fixtures) are explicitly out of scope for
this move and are allowed to remain.
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


def test_recap_graph_preview_ingest_does_not_import_evals_packaging_shim() -> None:
    target = SERVICES_DIR / "recap_graph_preview_ingest.py"
    assert target.is_file()
    assert not _imports_forbidden_module(target), (
        f"{target} must import GraphIngest packaging from "
        "src.graph_memory.extraction.graph_ingest_packaging, not the evals shim"
    )


def test_recap_graph_preview_ingest_imports_production_packaging_module() -> None:
    target = SERVICES_DIR / "recap_graph_preview_ingest.py"
    tree = ast.parse(target.read_text(encoding="utf-8"), filename=str(target))
    production_module = "src.graph_memory.extraction.graph_ingest_packaging"
    found = any(
        isinstance(node, ast.ImportFrom) and node.module == production_module
        for node in ast.walk(tree)
    )
    assert found, f"{target} must import from {production_module}"


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
        f"({FORBIDDEN_MODULE}); import src.graph_memory.extraction.graph_ingest_packaging instead"
    )
