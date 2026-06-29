from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
GATE_PATH = REPO_ROOT / "evals" / "graph_memory_layer" / "real_structure_materialization_gate.json"
GUIDE_PATH = REPO_ROOT / "evals" / "graph_memory_layer" / "REAL-STRUCTURE-MATERIALIZATION-GATE.md"
VALIDATOR_PATH = REPO_ROOT / "evals" / "graph_memory_layer" / "validate_real_structure_gate.py"
FORBIDDEN_MATERIALIZER_PATHS = {
    "src/graph_memory/session_memory_materializer.py",
    "src/graph_memory/corpus_materializer.py",
    "src/graph_memory/manifest_materializer.py",
}
FORBIDDEN_IMPORT_SNIPPETS = {
    "src.agent.session_memory_query",
    "src.agent.planner_retrieval_router",
    "src.live_play.manifest_context_query",
    "src.session_memory.capture",
    "src.session_memory.breadcrumb_normalize",
    "openai",
    "anthropic",
}


def load_gate() -> dict:
    with GATE_PATH.open(encoding="utf-8") as handle:
        return json.load(handle)


def candidate_by_id(candidate_id: str) -> dict:
    return next(candidate for candidate in load_gate()["candidate_source_families"] if candidate["id"] == candidate_id)


def test_gate_manifest_exists() -> None:
    assert GATE_PATH.is_file()


def test_gate_validator_exits_zero() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "evals.graph_memory_layer.validate_real_structure_gate"],
        cwd=REPO_ROOT,
        check=False,
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "- real-structure gate: ready" in result.stdout


def test_exactly_one_source_family_is_admitted() -> None:
    candidates = load_gate()["candidate_source_families"]
    assert sum(candidate["status"] == "admitted_next" for candidate in candidates) == 1
    assert sum(candidate["admitted_for_next_materializer"] is True for candidate in candidates) == 1


def test_admitted_family_matches_gate_decision() -> None:
    gate = load_gate()
    admitted = [candidate for candidate in gate["candidate_source_families"] if candidate["status"] == "admitted_next"]
    assert admitted[0]["id"] == gate["gate_decision"]["admitted_source_family"]


def test_admitted_family_is_session_memory_sentence_units() -> None:
    assert load_gate()["gate_decision"]["admitted_source_family"] == "session_memory_jsonl_sentence_units"


def test_blocked_and_deferred_families_are_not_admitted() -> None:
    for candidate in load_gate()["candidate_source_families"]:
        if candidate["status"] in {"blocked", "deferred"}:
            assert candidate["admitted_for_next_materializer"] is False


def test_global_constraints_include_no_retrieval_corpus_llm_extraction_and_promotion() -> None:
    constraints = load_gate()["global_constraints"]
    for key in [
        "no_production_retrieval_changes",
        "no_corpus_mutation",
        "no_llm_calls",
        "no_entity_extraction",
        "no_alias_resolution",
        "no_relationship_inference",
        "no_promoted_records",
        "diagnostic_only_default",
    ]:
        assert constraints[key] is True


def test_admitted_family_requires_validation_rules_and_reporting() -> None:
    gate = load_gate()
    admitted = candidate_by_id(gate["gate_decision"]["admitted_source_family"])
    assert gate["global_constraints"]["must_run_validation_rules"] is True
    assert gate["global_constraints"]["must_emit_report"] is True
    assert "validation issue summary" in admitted["required_reports"]
    assert admitted["required_reports"]


def test_admitted_family_forbids_corpus_live_and_retrieval_surfaces() -> None:
    admitted = candidate_by_id("session_memory_jsonl_sentence_units")
    forbidden = "\n".join(admitted["forbidden_read_surfaces"]).lower()
    assert "corpus" in forbidden
    assert "live-play" in forbidden
    assert "retrieval" in forbidden


def test_human_readable_gate_guide_exists() -> None:
    assert GUIDE_PATH.is_file()
    guide = GUIDE_PATH.read_text(encoding="utf-8")
    assert "# Graph Memory Real-Structure Materialization Gate v0" in guide
    assert "## Gate Decision" in guide
    assert "session_memory_jsonl_sentence_units" in guide


def test_gate_files_do_not_mention_production_writes_as_allowed_behavior() -> None:
    combined = GATE_PATH.read_text(encoding="utf-8") + "\n" + GUIDE_PATH.read_text(encoding="utf-8")
    lowered = combined.lower()
    forbidden_allowed_write_phrases = [
        "allow production writes",
        "allowed production writes",
        "production writes are allowed",
        "write to production data stores",
    ]
    for phrase in forbidden_allowed_write_phrases[:3]:
        assert phrase not in lowered
    assert "must not" in lowered and forbidden_allowed_write_phrases[3] in lowered


def test_no_source_reading_code_is_introduced_in_this_pr() -> None:
    changed = subprocess.run(
        ["git", "diff", "--name-only", "HEAD"],
        cwd=REPO_ROOT,
        check=True,
        text=True,
        capture_output=True,
    ).stdout.splitlines()
    assert not (set(changed) & FORBIDDEN_MATERIALIZER_PATHS)
    assert not [path for path in changed if path.startswith("src/graph_memory/") and "materializer" in path]

    for path in [GATE_PATH, GUIDE_PATH, VALIDATOR_PATH]:
        source = path.read_text(encoding="utf-8")
        for snippet in FORBIDDEN_IMPORT_SNIPPETS:
            assert snippet not in source
