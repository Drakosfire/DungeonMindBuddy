"""CI-enforced Graph Kernel boundary guards (PR003).

These tests are intended to fail in CI when unmarked illegal imports or
preview/latest-ingest selectors are introduced.

TypeScript exemptions are an explicit allowlist of ``(file, selector)`` pairs —
a file-level ``PR003_LEGACY_GRAPH_PREVIEW_EXEMPTION`` comment does **not**
bypass the guard.
"""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass
from pathlib import Path

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

# Graph-identity selectors only. Generic ``manifest_path`` / ``storePath`` are
# excluded — they appear in agent-trace and eval fixtures that are not graph
# selection APIs. Graph-specific path selectors remain banned.
BANNED_TS_SELECTORS = (
    "useLatestGraphIngest",
    "previewSource",
    "previewUnionStorePath",
    "graphRunManifestPath",
    "latestIngest",
    "preview_source",
    "preview_union_store_path",
    "graph_run_manifest_path",
)

# Exact file → exact banned selector names still allowed as legacy until
# PR006–PR008. New banned selectors in these files (or any selector in
# non-listed files) fail the guard.
TS_LEGACY_SELECTOR_ALLOWLIST: dict[str, frozenset[str]] = {
    "apps/live-control-ui/src/api/liveApi.ts": frozenset(
        {
            "useLatestGraphIngest",
            "previewSource",
            "previewUnionStorePath",
            "graphRunManifestPath",
            "preview_source",
            "preview_union_store_path",
            "graph_run_manifest_path",
        }
    ),
    "apps/live-control-ui/src/api/liveApi.test.ts": frozenset(
        {
            "useLatestGraphIngest",
            "previewSource",
            "preview_source",
        }
    ),
    "apps/live-control-ui/src/api/types.ts": frozenset(
        {
            "previewUnionStorePath",
            "preview_union_store_path",
        }
    ),
    "apps/live-control-ui/src/modules/IngestionModule.tsx": frozenset(
        {
            "preview_union_store_path",
        }
    ),
    "apps/live-control-ui/src/modules/IngestionModule.test.tsx": frozenset(
        {
            "preview_union_store_path",
        }
    ),
    "apps/live-control-ui/src/planSurface/graphPreview/GraphIngestProjectionPanel.tsx": frozenset(
        {
            "useLatestGraphIngest",
            "preview_union_store_path",
        }
    ),
    "apps/live-control-ui/src/planSurface/graphPreview/RecapGraphModule.tsx": frozenset(
        {
            "useLatestGraphIngest",
            "graphRunManifestPath",
        }
    ),
    "apps/live-control-ui/src/planSurface/graphPreview/RecapGraphModule.test.tsx": frozenset(
        {
            "useLatestGraphIngest",
            "graphRunManifestPath",
        }
    ),
    "apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphMergeReconciliationMaterializationPanel.tsx": frozenset(
        {
            "previewUnionStorePath",
        }
    ),
    "apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphMergeReconciliationMaterializationPanel.test.tsx": frozenset(
        {
            "previewUnionStorePath",
        }
    ),
    "apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphObjectAuthoringPrepareCommitPanel.tsx": frozenset(
        {
            "previewUnionStorePath",
        }
    ),
    "apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphObjectAuthoringPrepareCommitPanel.test.tsx": frozenset(
        {
            "previewUnionStorePath",
        }
    ),
    "apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphObjectAuthoringSurface.tsx": frozenset(
        {
            "previewUnionStorePath",
        }
    ),
    "apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewAuthorDraftWorkspace.test.tsx": frozenset(
        {
            "preview_union_store_path",
        }
    ),
    "apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewAuthoringRail.tsx": frozenset(
        {
            "previewUnionStorePath",
            "preview_union_store_path",
        }
    ),
    "apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewLiveProjectionPanel.tsx": frozenset(
        {
            "preview_union_store_path",
        }
    ),
    "apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewLiveProjectionPanel.test.tsx": frozenset(
        {
            "useLatestGraphIngest",
            "graphRunManifestPath",
            "previewUnionStorePath",
            "preview_union_store_path",
        }
    ),
    "apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewLoadSurface.test.tsx": frozenset(
        {
            "preview_union_store_path",
        }
    ),
    "apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewWorkbenchModule.test.tsx": frozenset(
        {
            "preview_union_store_path",
        }
    ),
    "apps/live-control-ui/src/planSurface/graphReviewWorkbench/graphReviewLiveReviewState.ts": frozenset(
        {
            "graphRunManifestPath",
            "previewUnionStorePath",
            "preview_union_store_path",
        }
    ),
    "apps/live-control-ui/src/planSurface/graphReviewWorkbench/graphReviewReferenceLaneUtils.ts": frozenset(
        {
            "preview_union_store_path",
        }
    ),
    "apps/live-control-ui/src/planSurface/graphReviewWorkbench/graphReviewReferenceLaneUtils.test.ts": frozenset(
        {
            "preview_union_store_path",
        }
    ),
    "apps/live-control-ui/src/planSurface/graphReviewWorkbench/graphReviewWorkbenchUtils.ts": frozenset(
        {
            "preview_union_store_path",
        }
    ),
    "apps/live-control-ui/src/planSurface/graphReviewWorkbench/graphReviewWorkbenchUtils.test.ts": frozenset(
        {
            "preview_union_store_path",
        }
    ),
    "apps/live-control-ui/src/planSurface/graphReviewWorkbench/useGraphObjectAuthoringQuickCommit.ts": frozenset(
        {
            "previewUnionStorePath",
        }
    ),
    "apps/live-control-ui/src/planSurface/reference/usePlanGraphReferenceResolver.ts": frozenset(
        {
            "useLatestGraphIngest",
        }
    ),
}

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


def _imported_modules(
    node: ast.AST, *, banned_prefixes: tuple[str, ...]
) -> list[tuple[str, int]]:
    """Return fully-qualified modules referenced by an import statement.

    Catches both direct submodule imports and parent-package attribute imports::

        from graph_memory.world_supergraph.storage import X
        from graph_memory.world_supergraph import storage
        from graph_memory.world_supergraph import paths as world_paths
        import graph_memory.world_supergraph.paths
    """
    banned_set = set(banned_prefixes)
    found: list[tuple[str, int]] = []
    if isinstance(node, ast.Import):
        for alias in node.names:
            found.append((_normalize_module(alias.name), node.lineno))
    elif isinstance(node, ast.ImportFrom):
        if not node.module:
            return found
        parent = _normalize_module(node.module)
        found.append((parent, node.lineno))
        for alias in node.names:
            if alias.name == "*":
                continue
            candidate = f"{parent}.{alias.name}"
            # Only expand parent.attr when that exact path is a banned module
            # (e.g. ``from graph_memory.world_supergraph import paths``).
            if candidate in banned_set:
                found.append((candidate, node.lineno))
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
        seen: set[tuple[int, str]] = set()
        for node in ast.walk(tree):
            for module, lineno in _imported_modules(
                node, banned_prefixes=banned_prefixes
            ):
                if not any(
                    module == banned or module.startswith(banned + ".")
                    for banned in banned_prefixes
                ):
                    continue
                key = (lineno, module)
                if key in seen:
                    continue
                seen.add(key)
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


def _scan_ts_banned_selectors(
    files: list[Path],
    *,
    allowlist: dict[str, frozenset[str]],
) -> list[BoundaryViolation]:
    violations: list[BoundaryViolation] = []
    for path in files:
        try:
            rel = path.relative_to(REPO_ROOT).as_posix()
        except ValueError:
            rel = path.as_posix()
        text = path.read_text(encoding="utf-8")
        allowed = allowlist.get(rel, frozenset())
        for match in _TS_SELECTOR_RE.finditer(text):
            name = match.group(0)
            if name in allowed:
                continue
            line = text.count("\n", 0, match.start()) + 1
            violations.append(
                BoundaryViolation(
                    path=path,
                    line=line,
                    offending=(
                        f"banned preview/session graph selector {name!r} "
                        f"(file-level exemption markers do not bypass; "
                        f"allowlist has {sorted(allowed)!r})"
                    ),
                    required_fix=(
                        "remove the selector, or add this exact file+selector pair to "
                        "TS_LEGACY_SELECTOR_ALLOWLIST with a named deletion PR "
                        "(PR007/PR008)"
                    ),
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
    files = [
        path
        for path in sorted(ui_root.rglob("*"))
        if path.suffix in {".ts", ".tsx"}
        and path.is_file()
        and "/node_modules/" not in path.as_posix()
    ]
    violations = _scan_ts_banned_selectors(files, allowlist=TS_LEGACY_SELECTOR_ALLOWLIST)
    assert not violations, _format_violations(violations)


def test_boundary_scanner_detects_illegal_import(tmp_path: Path) -> None:
    """Meta-test: prove the AST guard can fail on a direct submodule import."""
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


def test_boundary_scanner_detects_parent_module_attribute_import(tmp_path: Path) -> None:
    """Meta-test: parent-package imports of banned submodules must fail."""
    sample = tmp_path / "alias_bypass.py"
    sample.write_text(
        "\n".join(
            [
                "from graph_memory.world_supergraph import paths",
                "from graph_memory.world_supergraph import storage",
                "from graph_memory.world_supergraph import paths as world_paths",
                "",
            ]
        ),
        encoding="utf-8",
    )
    violations = _scan_python_imports(
        [sample],
        banned_prefixes=WORLD_STORAGE_INTERNALS,
        required_fix="use graph_memory.kernel",
    )
    offending = {v.offending for v in violations}
    assert any("world_supergraph.paths" in item for item in offending)
    assert any("world_supergraph.storage" in item for item in offending)
    # Three import lines → at least three violations (paths appears twice).
    assert len(violations) >= 3


def test_ts_selector_guard_ignores_file_level_exemption_marker(tmp_path: Path) -> None:
    """Meta-test: a file-level exemption marker must not allow new banned selectors."""
    sample = tmp_path / "legacy_marked_but_new_selector.ts"
    sample.write_text(
        "\n".join(
            [
                "// PR003_LEGACY_GRAPH_PREVIEW_EXEMPTION:",
                "// Retained until PR007/PR008 — but this must NOT blanket-bypass.",
                "export const query = { useLatestGraphIngest: true };",
                "",
            ]
        ),
        encoding="utf-8",
    )
    # Empty allowlist: even with the marker, the selector is a violation.
    violations = _scan_ts_banned_selectors([sample], allowlist={})
    assert len(violations) == 1
    assert "useLatestGraphIngest" in violations[0].offending


def test_ts_selector_allowlist_is_selector_specific(tmp_path: Path) -> None:
    """Meta-test: allowlisting one selector must not permit a different banned name."""
    sample = tmp_path / "partial_allow.ts"
    # Place under a fake relative path by scanning with an allowlist key that
    # won't match tmp paths — use empty allowlist for the tmp file path, and a
    # separate in-repo-style check via direct call with crafted allowlist keyed
    # by the absolute-as-posix path... Instead: write under REPO tmp is hard.
    # Use allowlist keyed to the path's as_posix() when outside repo — the
    # scanner uses relative_to failure → full path. Pass allowlist for that.
    rel_key = sample.as_posix()
    sample.write_text(
        "\n".join(
            [
                "// PR003_LEGACY_GRAPH_PREVIEW_EXEMPTION: present but irrelevant",
                "export const a = { previewSource: 'x', useLatestGraphIngest: true };",
                "",
            ]
        ),
        encoding="utf-8",
    )
    violations = _scan_ts_banned_selectors(
        [sample],
        allowlist={rel_key: frozenset({"previewSource"})},
    )
    assert len(violations) == 1
    assert "useLatestGraphIngest" in violations[0].offending
