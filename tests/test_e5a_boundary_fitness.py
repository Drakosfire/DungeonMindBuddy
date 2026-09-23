"""E5A architecture fitness: freeze Buddy's current inference and knowledge debt.

These tests do not endorse the allowlisted imports. They make today's direct
OpenAI SDK use and DungeonMind internal/write coupling fail-closed so the debt
cannot grow unnoticed. Later migration PRs must shrink the matching baseline
in the same change that removes the import.

Harvested by AST from apps/ and src/ on Buddy main
``ff79374fffad38f07c4ce1807e3037015d74f451``. Original harvest was
``94ae1ea927d6aa6c239085466973a11bff5cc605`` (historical provenance).
Cycle 2 re-ran the scan on the accepted baseline; allowlists were
identical. evals/, scripts/, tools/, and tests/ are intentionally out
of scope.
"""

from __future__ import annotations

import ast
from collections.abc import Callable
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCAN_ROOTS = (ROOT / "apps", ROOT / "src")
INTEGRATION_PREFIX = "apps/live_control_server/integrations/dungeonmind/"

PROVIDER_MODULE_PREFIXES = (
    "openai",
    "fal",
    "fal_client",
    "anthropic",
    "together",
    "groq",
    "google.genai",
    "vertexai",
)
DUNGEONMIND_ROOTS = ("dungeonmind", "dungeonmind_dnd")
GENERATIONENGINE_ROOTS = ("generationengine",)

# (repo-relative path, imported module string from the AST node)
BASELINE_PROVIDER_IMPORTS: frozenset[tuple[str, str]] = frozenset(
    {
        ("src/agent/document_planner.py", "openai"),
        ("src/agent/planner.py", "openai"),
        ("src/cli.py", "openai"),
        ("src/graph_memory/extraction/category_candidate_graph_extractor.py", "openai"),
        ("src/graph_memory/extraction/preview_candidate_graph_extractor.py", "openai"),
        ("src/graph_memory/extraction/staged_edge_extraction.py", "openai"),
        ("src/ingestion/entity_extractor.py", "openai"),
        ("src/ingestion/fact_extractor.py", "openai"),
        ("src/ingestion/openai_batch_pipeline.py", "openai"),
        ("src/ingestion/openai_batch_pipeline.py", "openai.lib._parsing._responses"),
        ("src/ingestion/schema_repair_batch.py", "openai"),
        ("src/live_play/live_query_context.py", "openai"),
    }
)

BASELINE_PYDANTIC_AI_OPENAI_IMPORTS: frozenset[tuple[str, str]] = frozenset(
    {
        (
            "apps/live_control_server/services/pydantic_ai_agent_runtime.py",
            "pydantic_ai.models.openai",
        ),
    }
)

BASELINE_DUNGEONMIND_IMPORTS: frozenset[tuple[str, str]] = frozenset(
    {
        (
            "apps/live_control_server/integrations/dungeonmind/assertion_qualification.py",
            "dungeonmind_dnd.application.world_object_vocabulary",
        ),
        (
            "apps/live_control_server/integrations/dungeonmind/contribution_mapping.py",
            "dungeonmind.contracts.contribution",
        ),
        (
            "apps/live_control_server/integrations/dungeonmind/contribution_mapping.py",
            "dungeonmind.contracts.evidence",
        ),
        (
            "apps/live_control_server/integrations/dungeonmind/contribution_mapping.py",
            "dungeonmind.contracts.identity",
        ),
        (
            "apps/live_control_server/integrations/dungeonmind/contribution_mapping.py",
            "dungeonmind.contracts.vocabulary",
        ),
        (
            "apps/live_control_server/integrations/dungeonmind/contribution_mapping.py",
            "dungeonmind.domain.canonical",
        ),
        (
            "apps/live_control_server/integrations/dungeonmind/world_graph_initialization_adapter.py",
            "dungeonmind.application.reviewed_world_initialization",
        ),
        (
            "apps/live_control_server/integrations/dungeonmind/world_graph_initialization_adapter.py",
            "dungeonmind.application.semantic_profiles",
        ),
        (
            "apps/live_control_server/integrations/dungeonmind/world_graph_initialization_adapter.py",
            "dungeonmind.contracts.contribution",
        ),
        (
            "apps/live_control_server/integrations/dungeonmind/world_graph_initialization_adapter.py",
            "dungeonmind.contracts.evidence",
        ),
        (
            "apps/live_control_server/integrations/dungeonmind/world_graph_initialization_adapter.py",
            "dungeonmind.contracts.reviewed_world_initialization",
        ),
        (
            "apps/live_control_server/integrations/dungeonmind/world_graph_initialization_adapter.py",
            "dungeonmind.contracts.semantic_profile",
        ),
        (
            "apps/live_control_server/integrations/dungeonmind/world_graph_initialization_adapter.py",
            "dungeonmind.domain.errors",
        ),
        (
            "apps/live_control_server/integrations/dungeonmind/world_graph_initialization_adapter.py",
            "dungeonmind_dnd.application.world_object_vocabulary",
        ),
        (
            "apps/live_control_server/integrations/dungeonmind/world_graph_reads.py",
            "dungeonmind.application.graph_snapshot",
        ),
        (
            "apps/live_control_server/integrations/dungeonmind/world_graph_reads.py",
            "dungeonmind.application.world_graph_projection",
        ),
        (
            "apps/live_control_server/integrations/dungeonmind/world_graph_reads.py",
            "dungeonmind.application.world_graph_retrieval",
        ),
        (
            "apps/live_control_server/integrations/dungeonmind/world_graph_reads.py",
            "dungeonmind.contracts.evidence",
        ),
        (
            "apps/live_control_server/integrations/dungeonmind/world_graph_reads.py",
            "dungeonmind.contracts.projection",
        ),
        (
            "apps/live_control_server/integrations/dungeonmind/world_graph_reads.py",
            "dungeonmind.contracts.projection_v2",
        ),
        (
            "apps/live_control_server/integrations/dungeonmind/world_graph_reads.py",
            "dungeonmind.domain.errors",
        ),
        (
            "apps/live_control_server/integrations/dungeonmind/world_graph_reads.py",
            "dungeonmind.infrastructure.postgres",
        ),
        (
            "apps/live_control_server/integrations/dungeonmind/world_graph_reads.py",
            "dungeonmind.infrastructure.semantic_profiles",
        ),
        (
            "apps/live_control_server/integrations/dungeonmind/world_graph_reads.py",
            "dungeonmind_dnd.application.world_object_vocabulary",
        ),
        (
            "apps/live_control_server/integrations/dungeonmind/world_graph_source_admission_adapter.py",
            "dungeonmind.contracts.evidence",
        ),
        (
            "apps/live_control_server/integrations/dungeonmind/world_graph_source_admission_adapter.py",
            "dungeonmind.contracts.vocabulary",
        ),
        (
            "apps/live_control_server/integrations/dungeonmind/world_graph_source_admission_adapter.py",
            "dungeonmind.domain.errors",
        ),
        (
            "apps/live_control_server/integrations/dungeonmind/world_graph_source_admission_adapter.py",
            "dungeonmind.infrastructure.postgres",
        ),
        (
            "apps/live_control_server/integrations/dungeonmind/world_graph_writes.py",
            "dungeonmind.application.contribution_review_v2",
        ),
        (
            "apps/live_control_server/integrations/dungeonmind/world_graph_writes.py",
            "dungeonmind.application.graph_snapshot",
        ),
        (
            "apps/live_control_server/integrations/dungeonmind/world_graph_writes.py",
            "dungeonmind.application.review_publication",
        ),
        (
            "apps/live_control_server/integrations/dungeonmind/world_graph_writes.py",
            "dungeonmind.contracts.capability",
        ),
        (
            "apps/live_control_server/integrations/dungeonmind/world_graph_writes.py",
            "dungeonmind.contracts.contribution",
        ),
        (
            "apps/live_control_server/integrations/dungeonmind/world_graph_writes.py",
            "dungeonmind.contracts.contribution_review",
        ),
        (
            "apps/live_control_server/integrations/dungeonmind/world_graph_writes.py",
            "dungeonmind.contracts.contribution_review_v2",
        ),
        (
            "apps/live_control_server/integrations/dungeonmind/world_graph_writes.py",
            "dungeonmind.contracts.identity",
        ),
        (
            "apps/live_control_server/integrations/dungeonmind/world_graph_writes.py",
            "dungeonmind.contracts.projection",
        ),
        (
            "apps/live_control_server/integrations/dungeonmind/world_graph_writes.py",
            "dungeonmind.contracts.semantic_profile",
        ),
        (
            "apps/live_control_server/integrations/dungeonmind/world_graph_writes.py",
            "dungeonmind.domain.canonical",
        ),
        (
            "apps/live_control_server/integrations/dungeonmind/world_graph_writes.py",
            "dungeonmind.domain.errors",
        ),
        (
            "apps/live_control_server/integrations/dungeonmind/world_graph_writes.py",
            "dungeonmind.infrastructure.postgres",
        ),
        (
            "apps/live_control_server/integrations/dungeonmind/world_graph_writes.py",
            "dungeonmind.infrastructure.semantic_profiles",
        ),
        (
            "apps/live_control_server/integrations/dungeonmind/world_graph_writes.py",
            "dungeonmind_dnd.application.world_object_vocabulary",
        ),
        (
            "apps/live_control_server/services/candidate_graph_admission.py",
            "dungeonmind.domain.errors",
        ),
        (
            "apps/live_control_server/services/runtime_preflight.py",
            "dungeonmind.infrastructure.postgres",
        ),
    }
)

BASELINE_DUNGEONMIND_OUTSIDE_INTEGRATION: frozenset[str] = frozenset(
    {
        "apps/live_control_server/services/candidate_graph_admission.py",
        "apps/live_control_server/services/runtime_preflight.py",
    }
)

BASELINE_GENERATIONENGINE_IMPORTS: frozenset[tuple[str, str]] = frozenset(
    {
        ("src/agent/synthesis.py", "generationengine"),
        ("src/compiler/wiki_compiler.py", "generationengine"),
        ("src/ingestion/frontmatter_inference.py", "generationengine"),
        ("src/live_play/live_turn_classifier_client.py", "generationengine"),
        ("src/npc_statblock_pipeline/canonical_intent.py", "generationengine"),
    }
)


def _posix(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def _imported_modules(tree: ast.AST) -> set[str]:
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            found.add(node.module)
    return found


def _matches_prefix(module: str, prefixes: tuple[str, ...]) -> bool:
    for prefix in prefixes:
        if module == prefix or module.startswith(prefix + "."):
            return True
    return False


def _scan(matcher: Callable[[str], bool]) -> frozenset[tuple[str, str]]:
    found: set[tuple[str, str]] = set()
    for scan_root in SCAN_ROOTS:
        assert scan_root.is_dir(), f"E5A scan root missing: {scan_root}"
        for path in scan_root.rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            rel = _posix(path)
            for module in _imported_modules(tree):
                if matcher(module):
                    found.add((rel, module))
    return frozenset(found)


def _diff_message(
    kind: str,
    actual: frozenset[tuple[str, str]],
    baseline: frozenset[tuple[str, str]],
) -> str:
    added = sorted(actual - baseline)
    removed = sorted(baseline - actual)
    lines = [
        f"E5A {kind} import baseline drifted. This is a debt freeze, not a target architecture.",
        "Update the allowlist in the same PR that adds or removes the import.",
    ]
    if added:
        lines.append("New imports (debt grew):")
        lines.extend(f"  {path} -> {module}" for path, module in added)
    if removed:
        lines.append("Missing baseline entries (shrink the allowlist if the import is gone):")
        lines.extend(f"  {path} -> {module}" for path, module in removed)
    return "\n".join(lines)


def _is_dungeonmind_internal(module: str) -> bool:
    if module.startswith("dungeonmind.contracts."):
        return False
    return _matches_prefix(module, DUNGEONMIND_ROOTS)


def test_direct_provider_sdk_imports_match_e5a_baseline() -> None:
    actual = _scan(lambda module: _matches_prefix(module, PROVIDER_MODULE_PREFIXES))
    assert actual == BASELINE_PROVIDER_IMPORTS, _diff_message(
        "direct provider SDK", actual, BASELINE_PROVIDER_IMPORTS
    )


def test_pydantic_ai_openai_adapter_imports_match_e5a_baseline() -> None:
    actual = _scan(lambda module: module.startswith("pydantic_ai.models.openai"))
    assert actual == BASELINE_PYDANTIC_AI_OPENAI_IMPORTS, _diff_message(
        "PydanticAI OpenAI adapter", actual, BASELINE_PYDANTIC_AI_OPENAI_IMPORTS
    )


def test_generationengine_imports_match_bounded_migration_baseline() -> None:
    """Active GenerationEngine imports exactly match the bounded migration baseline."""
    actual = _scan(lambda module: _matches_prefix(module, GENERATIONENGINE_ROOTS))
    assert actual == BASELINE_GENERATIONENGINE_IMPORTS, _diff_message(
        "GenerationEngine", actual, BASELINE_GENERATIONENGINE_IMPORTS
    )


def test_dungeonmind_imports_match_e5a_baseline() -> None:
    actual = _scan(lambda module: _matches_prefix(module, DUNGEONMIND_ROOTS))
    assert actual == BASELINE_DUNGEONMIND_IMPORTS, _diff_message(
        "DungeonMind", actual, BASELINE_DUNGEONMIND_IMPORTS
    )


def test_dungeonmind_imports_outside_integration_boundary_are_exact() -> None:
    actual_files = frozenset(
        path
        for path, _module in _scan(lambda module: _matches_prefix(module, DUNGEONMIND_ROOTS))
        if not path.startswith(INTEGRATION_PREFIX)
    )
    assert actual_files == BASELINE_DUNGEONMIND_OUTSIDE_INTEGRATION, (
        "New DungeonMind imports must live in "
        f"{INTEGRATION_PREFIX} or this extra-boundary allowlist must change "
        "with an architecture handoff.\n"
        f"new={sorted(actual_files - BASELINE_DUNGEONMIND_OUTSIDE_INTEGRATION)}\n"
        f"missing={sorted(BASELINE_DUNGEONMIND_OUTSIDE_INTEGRATION - actual_files)}"
    )


def test_dungeonmind_internal_imports_are_explicit_debt() -> None:
    actual = frozenset(
        pair
        for pair in _scan(lambda module: _matches_prefix(module, DUNGEONMIND_ROOTS))
        if _is_dungeonmind_internal(pair[1])
    )
    baseline = frozenset(
        pair for pair in BASELINE_DUNGEONMIND_IMPORTS if _is_dungeonmind_internal(pair[1])
    )
    assert actual == baseline, _diff_message(
        "DungeonMind internal/application/infrastructure/domain",
        actual,
        baseline,
    )


def test_model_policy_remains_buddy_owned_transition_policy() -> None:
    """E1B authority stays Buddy-local; E5A does not delete or rewrite the file."""
    from src.model_policy import buddy_model_policy_path, load_buddy_model_policy

    path = buddy_model_policy_path()
    assert path.is_file()
    payload = load_buddy_model_policy(strict=True)
    assert payload.get("status") == "buddy_owned_transition_policy"
