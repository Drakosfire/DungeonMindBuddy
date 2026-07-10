"""CI-enforced Graph Kernel boundary guards (PR003).

These tests are intended to fail in CI when unmarked illegal imports or
preview/latest-ingest selectors are introduced.
"""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]

EXEMPTION_MARKERS = (
    "PR003_LEGACY_GRAPH_PREVIEW_EXEMPTION",
    "PR003_INTERNAL_GRAPH_KERNEL_EXEMPTION",
)

WORLD_STORAGE_INTERNALS = (
    "graph_memory.world_supergraph.storage",
    "graph_memory.world_supergraph.paths",
    "graph_memory.world_supergraph.integrity",
    "graph_memory.world_supergraph.model",
)

UNION_PREVIEW_INTERNALS = (
    "graph_memory.union_supergraph.load",
    "graph_memory.union_supergraph.validate",
    "graph_memory.union_supergraph.preview_import",
    "graph_memory.union_supergraph.preview_run_materialize",
)

# Packages allowed to import world storage internals without an exemption marker.
WORLD_STORAGE_ALLOW_PREFIXES = (
    "src/graph_memory/kernel/",
    "src/graph_memory/world_supergraph/",
)

BANNED_TS_SELECTORS = (
    "useLatestGraphIngest",
    "previewSource",
    "previewUnionStorePath",
    "graphRunManifestPath",
    "storePath",
    "manifestPath",
    "latestIngest",
    "preview_source",
    "preview_union_store_path",
    "graph_run_manifest_path",
    "store_path",
    "manifest_path",
)

_TS_SELECTOR_RE = re.compile(
    r"\b(" + "|".join(re.escape(name) for name in BANNED_TS_SELECTORS) + r")\b"
)


@dataclass(frozen=True)
class BoundaryViolation:
    path: Path
    line: int
    offending: str
    required_fix: str

    def format(self) -> str:
        try:
            rel = self.path.relative_to(REPO_ROOT)
        except ValueError:
            rel = self.path
        return (
            f"{rel}:{self.line}: {self.offending}\n"
            f"  required fix: {self.required_fix}"
        )


def _file_has_exemption(path: Path) -> bool:
    text = path.read_text(encoding="utf-8")
    return any(marker in text for marker in EXEMPTION_MARKERS)


def _normalize_module(module: str) -> str:
    if module.startswith("src."):
        return module[len("src.") :]
    return module


def _iter_python_files(*relative_roots: str) -> list[Path]:
    files: list[Path] = []
    for relative in relative_roots:
        root = REPO_ROOT / relative
        if not root.exists():
            continue
        files.extend(sorted(p for p in root.rglob("*.py") if p.is_file()))
    return files


def _imported_modules(node: ast.AST) -> list[tuple[str, int]]:
    found: list[tuple[str, int]] = []
    if isinstance(node, ast.Import):
        for alias in node.names:
            found.append((_normalize_module(alias.name), node.lineno))
    elif isinstance(node, ast.ImportFrom):
        if node.module:
            found.append((_normalize_module(node.module), node.lineno))
    return found


def _scan_python_imports(
    files: list[Path],
    *,
    banned_prefixes: tuple[str, ...],
    allow_path_prefixes: tuple[str, ...] = (),
    required_fix: str,
) -> list[BoundaryViolation]:
    violations: list[BoundaryViolation] = []
    for path in files:
        try:
            rel = path.relative_to(REPO_ROOT).as_posix()
        except ValueError:
            rel = path.as_posix()
        if any(rel.startswith(prefix) for prefix in allow_path_prefixes):
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except SyntaxError as exc:
            violations.append(
                BoundaryViolation(
                    path=path,
                    line=exc.lineno or 1,
                    offending=f"syntax error while parsing for boundary scan: {exc.msg}",
                    required_fix="fix syntax, then re-run boundary tests",
                )
            )
            continue

        exempt = _file_has_exemption(path)
        for node in ast.walk(tree):
            for module, lineno in _imported_modules(node):
                if any(
                    module == banned or module.startswith(banned + ".")
                    for banned in banned_prefixes
                ):
                    if exempt:
                        continue
                    violations.append(
                        BoundaryViolation(
                            path=path,
                            line=lineno,
                            offending=f"illegal import of {module}",
                            required_fix=required_fix,
                        )
                    )
    return violations


def _format_violations(violations: list[BoundaryViolation]) -> str:
    return "Graph Kernel boundary violations:\n" + "\n".join(v.format() for v in violations)


def test_apps_do_not_import_world_storage_internals_without_exemption() -> None:
    files = _iter_python_files("apps")
    violations = _scan_python_imports(
        files,
        banned_prefixes=WORLD_STORAGE_INTERNALS,
        required_fix=(
            "import via graph_memory.kernel, or add "
            "PR003_LEGACY_GRAPH_PREVIEW_EXEMPTION / PR003_INTERNAL_GRAPH_KERNEL_EXEMPTION "
            "with a named deletion PR"
        ),
    )
    assert not violations, _format_violations(violations)


def test_apps_do_not_import_union_preview_internals_without_exemption() -> None:
    files = _iter_python_files("apps")
    violations = _scan_python_imports(
        files,
        banned_prefixes=UNION_PREVIEW_INTERNALS,
        required_fix=(
            "route durable graph access through graph_memory.kernel, or mark the file with "
            "PR003_LEGACY_GRAPH_PREVIEW_EXEMPTION (delete in PR006/PR007/PR008)"
        ),
    )
    assert not violations, _format_violations(violations)


def test_src_outside_kernel_does_not_import_world_storage_internals_without_exemption() -> None:
    files = _iter_python_files("src", "tests")
    violations = _scan_python_imports(
        files,
        banned_prefixes=WORLD_STORAGE_INTERNALS,
        allow_path_prefixes=WORLD_STORAGE_ALLOW_PREFIXES,
        required_fix=(
            "use graph_memory.kernel for durable world graph access, or add "
            "PR003_INTERNAL_GRAPH_KERNEL_EXEMPTION / PR003_LEGACY_GRAPH_PREVIEW_EXEMPTION"
        ),
    )
    assert not violations, _format_violations(violations)


def test_surface_api_types_do_not_introduce_unmarked_preview_selectors() -> None:
    ui_root = REPO_ROOT / "apps" / "live-control-ui" / "src"
    violations: list[BoundaryViolation] = []
    for path in sorted(ui_root.rglob("*")):
        if path.suffix not in {".ts", ".tsx"} or not path.is_file():
            continue
        if "/node_modules/" in path.as_posix():
            continue
        text = path.read_text(encoding="utf-8")
        if any(marker in text for marker in EXEMPTION_MARKERS):
            continue
        for match in _TS_SELECTOR_RE.finditer(text):
            line = text.count("\n", 0, match.start()) + 1
            violations.append(
                BoundaryViolation(
                    path=path,
                    line=line,
                    offending=f"banned preview/session graph selector {match.group(0)!r}",
                    required_fix=(
                        "remove the selector from production-facing API types, or add "
                        "PR003_LEGACY_GRAPH_PREVIEW_EXEMPTION (delete in PR007/PR008)"
                    ),
                )
            )
    assert not violations, _format_violations(violations)


def test_boundary_scanner_detects_illegal_import(tmp_path: Path) -> None:
    """Meta-test: prove the AST guard can fail."""
    sample = tmp_path / "bad_adapter.py"
    sample.write_text(
        "from graph_memory.world_supergraph.storage import open_world_graph_head\n",
        encoding="utf-8",
    )
    violations = _scan_python_imports(
        [sample],
        banned_prefixes=WORLD_STORAGE_INTERNALS,
        required_fix="use graph_memory.kernel",
    )
    assert len(violations) == 1
    assert "world_supergraph.storage" in violations[0].offending
