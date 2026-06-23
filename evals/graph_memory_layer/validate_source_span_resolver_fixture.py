from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

from src.graph_memory.source_span import (
    DEFAULT_CONTEXT_MAX_CHARS,
    DEFAULT_SNIPPET_MAX_CHARS,
    SourceArtifactStructured,
    SourceArtifactText,
    analyze_evidence_resolution,
    resolved_evidence_to_dict,
    resolve_many_source_span_refs,
    source_span_ref_from_dict,
)

FIXTURE_PATH = Path(__file__).parent / "examples" / "source_span_resolver_fixture.json"
SCHEMA = "dmb_source_span_evidence_resolver_fixture_v0"
VERSION = "0.1"
ABSOLUTE_PATH_RE = re.compile(r"(/workspace/|/home/|/mnt/|\b[A-Za-z]:\\)")
FORBIDDEN_KEYS = {
    "full_text", "raw_text", "raw_content", "content", "path", "input_path", "raw_path", "file_path",
    "adapter_payload", "projection_card", "plan_payload", "plan_card", "plan_items", "agent_interaction",
    "agent_payload", "runtime_ui_payload", "ui_payload", "query", "graph_query", "entity", "entities",
    "alias", "aliases", "relationship", "relationships", "fact", "facts", "canon_promotion", "fact_promotion",
}
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


def load_fixture() -> dict[str, Any]:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def build_registries(fixture: dict[str, Any]):
    texts = {item["source_artifact_id"]: SourceArtifactText(**item) for item in fixture["text_artifacts"]}
    structured = {item["source_artifact_id"]: SourceArtifactStructured(**item) for item in fixture["structured_artifacts"]}
    refs = tuple(source_span_ref_from_dict(item) for item in fixture["source_span_refs"])
    return texts, structured, refs


def validate_fixture() -> dict[str, Any]:
    _require(FIXTURE_PATH.is_file(), "fixture missing")
    fixture = load_fixture()
    _require(fixture.get("schema") == SCHEMA and fixture.get("version") == VERSION, "bad schema/version")
    _require(fixture.get("source_family") == "recap_ingestion_source_artifacts", "bad source family")
    _require(fixture.get("text_artifacts"), "text artifacts required")
    _require(fixture.get("structured_artifacts"), "structured artifacts required")
    _require(len(fixture.get("source_span_refs", [])) >= 8, "at least eight source span refs required")
    text_artifacts, structured_artifacts, refs = build_registries(fixture)
    resolved = resolve_many_source_span_refs(refs, text_artifacts=text_artifacts, structured_artifacts=structured_artifacts)
    report = analyze_evidence_resolution(refs, resolved)
    expected = fixture["expected"]
    for key in ("total_refs", "resolved_refs", "unresolved_refs", "highlightable_refs", "structured_refs", "text_span_refs"):
        _require(getattr(report, key) == expected[key], f"expected count mismatch: {key}")
    valid = [item for item in resolved if not any('"severity": "error"' in w or '"severity": "blocker"' in w for w in item.warnings)]
    _require(all(item.can_open_source for item in valid), "valid refs must open source")
    _require(all(item.can_highlight_span for item in valid), "valid refs must highlight")
    _require(all(len(item.preview_snippet) <= DEFAULT_SNIPPET_MAX_CHARS for item in resolved), "snippet exceeds cap")
    _require(all(item.surrounding_context is None or len(item.surrounding_context) <= DEFAULT_CONTEXT_MAX_CHARS for item in resolved), "context exceeds cap")
    _require(any(issue.severity in {"error", "blocker"} for issue in report.issues), "invalid refs must surface issues")
    _require(all(item.structured_value_preview for item in valid if item.structured_path), "structured previews missing")
    serialized = json.dumps([resolved_evidence_to_dict(item) for item in resolved], sort_keys=True)
    for artifact in text_artifacts.values():
        _require(artifact.text not in serialized, "full raw artifact text leaked")
    _require(not ABSOLUTE_PATH_RE.search(serialized), "absolute path leaked")
    _require(not any(token in serialized for token in FORBIDDEN_TEXT), "raw ingestion internals leaked")
    _require(not (set(_walk_keys(json.loads(serialized))) & FORBIDDEN_KEYS), "forbidden payload fields leaked")
    diagnostics = fixture.get("diagnostics", {})
    for flag in ("full_raw_source_included_in_resolved_output", "absolute_paths_included", "runtime_required", "corpus_scan_required", "llm_required"):
        _require(diagnostics.get(flag) is False, f"diagnostic flag must be false: {flag}")
    return fixture


def main() -> int:
    print("Graph Memory source span evidence resolver validation")
    validate_fixture()
    for label in ("fixture", "text artifacts", "structured artifacts", "source span refs", "valid text spans", "valid structured paths", "invalid refs surface issues", "bounded snippets", "source openability", "highlightability", "no full raw source leakage", "no absolute path leakage", "no adapter/runtime payload leakage", "source span evidence resolver"):
        print(f"- {label}: ready")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (AssertionError, json.JSONDecodeError, ValueError) as exc:
        print(f"- source span evidence resolver: blocked ({exc})", file=sys.stderr)
        sys.exit(1)
