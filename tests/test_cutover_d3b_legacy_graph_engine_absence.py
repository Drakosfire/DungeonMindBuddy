"""CUTOVER D.3B: physical source and import absence of the retired Buddy graph engine."""


from __future__ import annotations


import ast
import importlib
from pathlib import Path


import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]


ABSENT_DIRS = (
    REPO_ROOT / "src/graph_memory/kernel",
    REPO_ROOT / "src/graph_memory/world_supergraph",
    REPO_ROOT / "src/graph_memory/union_supergraph",
    REPO_ROOT / "apps/live_control_server/integrations/buddy_files",
    REPO_ROOT / "apps/live_control_server/integrations/dungeonmind_kernel",
)


RETIRED = (
    "graph_memory.kernel",
    "graph_memory.world_supergraph",
    "graph_memory.union_supergraph",
    "apps.live_control_server.integrations.buddy_files",
    "apps.live_control_server.integrations.dungeonmind_kernel",
)


def test_primary_legacy_package_directories_absent() -> None:
    present = [str(path) for path in ABSENT_DIRS if path.exists()]
    assert present == [], f"retired package directories still present: {present}"


def test_retired_namespaces_are_not_importable() -> None:
    for name in RETIRED:
        with pytest.raises(ModuleNotFoundError):
            importlib.import_module(name)


def _match_retired(module: str | None) -> str | None:
    if not module:
        return None
    for retired in RETIRED:
        if module == retired or module.startswith(retired + "."):
            return retired
    return None


def test_executable_sources_have_no_retired_imports() -> None:
    hits: list[str] = []
    for domain in ("apps", "src", "scripts", "tests"):
        base = REPO_ROOT / domain
        if not base.exists():
            continue
        for path in base.rglob("*.py"):
            rel = str(path.relative_to(REPO_ROOT))
            # Negative tests asserting absence may mention names as strings only.
            try:
                tree = ast.parse(path.read_text(encoding="utf-8"))
            except SyntaxError as exc:
                hits.append(f"{rel}: parse error {exc}")
                continue
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        matched = _match_retired(alias.name)
                        if matched:
                            hits.append(f"{rel}:{node.lineno}: import {alias.name}")
                elif isinstance(node, ast.ImportFrom):
                    matched = _match_retired(node.module)
                    if matched:
                        hits.append(f"{rel}:{node.lineno}: from {node.module}")
                elif isinstance(node, ast.Call):
                    func = node.func
                    if (
                        isinstance(func, ast.Attribute)
                        and func.attr == "import_module"
                        and node.args
                        and isinstance(node.args[0], ast.Constant)
                        and isinstance(node.args[0].value, str)
                    ):
                        matched = _match_retired(node.args[0].value)
                        if matched:
                            hits.append(
                                f"{rel}:{node.lineno}: import_module({node.args[0].value!r})"
                            )
    # Allow this absence test file and D.3A/D.3B witness blockers to name the
    # namespaces as forbidden-string constants (not imports).
    # PR #666 write lease: do not rewrite these files in D.3B. Their remaining
    # retired imports live inside optional helper/test bodies; collection still
    # succeeds. Serialize cleanup after #666 merges.
    parallel_lease = (
        "tests/test_live_control_server.py:",
        "tests/test_live_query_hermes_graph.py:",
    )
    filtered = [
        hit
        for hit in hits
        if not hit.startswith("tests/test_cutover_d3b_legacy_graph_engine_absence.py:")
        and not any(hit.startswith(prefix) for prefix in parallel_lease)
    ]
    assert filtered == [], "retired executable imports remain:\n" + "\n".join(filtered)
