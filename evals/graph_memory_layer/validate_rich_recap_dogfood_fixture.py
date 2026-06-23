from __future__ import annotations

import json
import re
import sys
from typing import Any

from evals.graph_memory_layer.rich_recap_dogfood import (
    FIXTURE_ID,
    REQUIREMENTS_SCHEMA,
    SOURCE_SPAN_REFS_SCHEMA,
    build_rich_recap_materializer_inputs,
    build_rich_recap_source_span_registries,
    load_rich_recap_manifest,
    load_rich_recap_requirements,
    load_rich_recap_source_span_refs,
    validate_rich_recap_manifest,
)
from src.graph_memory.recap_ingestion_materialize import materialize_recap_ingestion_source_artifacts
from src.graph_memory.recap_ingestion_materializer_report import analyze_recap_ingestion_materializer_output, recap_ingestion_materializer_report_to_dict
from src.graph_memory.recap_ingestion_projection_readiness import assess_recap_ingestion_projection_readiness, recap_ingestion_projection_readiness_to_dict
from src.graph_memory.source_span import DEFAULT_CONTEXT_MAX_CHARS, DEFAULT_SNIPPET_MAX_CHARS, resolved_evidence_to_dict, resolve_many_source_span_refs

ABSOLUTE_PATH_RE = re.compile(r"(/workspace/|/home/|/mnt/|\b[A-Za-z]:\\)")
FORBIDDEN_KEYS = {"full_text", "raw_text", "raw_content", "content", "path", "input_path", "raw_path", "file_path", "adapter_payload", "projection_card", "plan_payload", "plan_card", "plan_items", "agent_interaction", "agent_payload", "runtime_ui_payload", "ui_payload", "query", "graph_query", "nodes", "edges", "proposed_writes", "candidate_graph_preview", "gold_graph", "llm_generated", "fact_promotion", "canon_promotion"}
FORBIDDEN_TEXT = ("_normalized/", "_breadcrumbed/", ".records_meta.jsonl")


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _walk_keys(obj: Any) -> list[str]:
    if isinstance(obj, dict):
        return [str(k) for k in obj] + [k for value in obj.values() for k in _walk_keys(value)]
    if isinstance(obj, list):
        return [k for value in obj for k in _walk_keys(value)]
    return []


def _assert_requirements(requirements: dict[str, object]) -> None:
    _require(requirements.get("schema") == REQUIREMENTS_SCHEMA and requirements.get("version") == "0.1", "bad requirements schema/version")
    _require(requirements.get("fixture_id") == FIXTURE_ID, "bad requirements fixture_id")
    mins = requirements.get("minimum_requirements")
    declared = requirements.get("declared_contents")
    _require(isinstance(mins, dict) and isinstance(declared, dict), "requirements must include minimums and declarations")
    for key, minimum in mins.items():
        declared_key = "unnamed_important_concepts" if key == "unnamed_important_relationship_opportunities" else key
        if key == "named_entity_relationship_opportunities":
            declared_key = key
        values = declared.get(declared_key)
        _require(isinstance(values, list) and len(values) >= int(minimum), f"declared richness below minimum: {key}")


def validate_fixture() -> None:
    manifest = load_rich_recap_manifest(); validate_rich_recap_manifest(manifest)
    inputs = build_rich_recap_materializer_inputs()
    materialization = materialize_recap_ingestion_source_artifacts(inputs)
    _require(len(materialization.artifacts) == len(materialization.anchors) == len(materialization.units) == 5, "materializer must emit five artifacts/anchors/units")
    report = analyze_recap_ingestion_materializer_output(materialization)
    readiness = assess_recap_ingestion_projection_readiness(materialization, report)
    _require(readiness.readiness_status == "ready", "projection readiness must be ready")
    requirements = load_rich_recap_requirements(); _assert_requirements(requirements)
    refs_doc = load_rich_recap_source_span_refs()
    _require(refs_doc.get("schema") == SOURCE_SPAN_REFS_SCHEMA and refs_doc.get("version") == "0.1", "bad source span refs schema/version")
    refs_raw = refs_doc.get("source_span_refs")
    _require(isinstance(refs_raw, list) and len(refs_raw) >= 12, "at least twelve source span refs required")
    _require(sum(1 for r in refs_raw if isinstance(r, dict) and r.get("start_line") is not None) >= 8, "at least eight text refs required")
    _require(sum(1 for r in refs_raw if isinstance(r, dict) and r.get("structured_path")) >= 2, "at least two structured refs required")
    text_artifacts, structured_artifacts, refs = build_rich_recap_source_span_registries()
    resolved = resolve_many_source_span_refs(refs, text_artifacts=text_artifacts, structured_artifacts=structured_artifacts)
    _require(all(r.can_open_source for r in resolved), "all refs must open source")
    _require(all(r.can_highlight_span for r in resolved), "all refs must highlight")
    _require(all(len(r.preview_snippet) <= DEFAULT_SNIPPET_MAX_CHARS for r in resolved), "snippet exceeds cap")
    _require(all(r.surrounding_context is None or len(r.surrounding_context) <= DEFAULT_CONTEXT_MAX_CHARS for r in resolved), "context exceeds cap")
    labels = "\n".join(str(r.get("label", "")) for r in refs_raw if isinstance(r, dict)).lower()
    for token in ("open unresolved", "ignored table noise", "archive search clue", "gm-private"):
        _require(token in labels, f"missing coverage label: {token}")
    serialized = json.dumps({"materializer_report": recap_ingestion_materializer_report_to_dict(report), "readiness": recap_ingestion_projection_readiness_to_dict(readiness), "resolved": [resolved_evidence_to_dict(r) for r in resolved]}, sort_keys=True)
    for explicit_input in inputs:
        _require(explicit_input.path.read_text(encoding="utf-8").strip() not in serialized, f"full raw source leaked: {explicit_input.path.name}")
    _require(not ABSOLUTE_PATH_RE.search(serialized), "absolute path leaked")
    _require(not any(token in serialized for token in FORBIDDEN_TEXT), "raw ingestion internals leaked")
    _require(not (set(_walk_keys(json.loads(serialized))) & FORBIDDEN_KEYS), "forbidden output fields leaked")
    diagnostics = manifest.get("diagnostics", {})
    _require(isinstance(diagnostics, dict), "diagnostics missing")
    for flag in ("corpus_scan_required", "runtime_required", "production_behavior", "llm_required", "graph_extraction_performed"):
        _require(diagnostics.get(flag) is False, f"diagnostics flag must be false: {flag}")


def main() -> int:
    print("Graph Memory rich recap dogfood fixture validation")
    validate_fixture()
    for label in ("manifest", "explicit artifact inputs", "recap materializer", "materializer report", "projection readiness", "dogfood requirements", "declared richness", "source span refs", "source evidence openability", "source evidence highlightability", "bounded snippets", "no full raw source leakage", "no absolute path leakage", "no graph preview output", "no extraction/LLM output", "no adapter/plan/agent/runtime leakage", "rich recap dogfood fixture"):
        print(f"- {label}: ready")
    return 0

if __name__ == "__main__":
    try:
        sys.exit(main())
    except (AssertionError, ValueError, json.JSONDecodeError) as exc:
        print(f"- rich recap dogfood fixture: blocked ({exc})", file=sys.stderr)
        sys.exit(1)
