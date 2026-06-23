from __future__ import annotations

import json
import subprocess
import sys

from evals.graph_memory_layer.validate_source_span_resolver_fixture import FIXTURE_PATH, build_registries, load_fixture
from src.graph_memory.source_span import (
    DEFAULT_CONTEXT_MAX_CHARS,
    DEFAULT_SNIPPET_MAX_CHARS,
    EvidenceResolutionIssue,
    EvidenceResolutionReport,
    SourceSpanRef,
    analyze_evidence_resolution,
    evidence_resolution_report_to_dict,
    resolved_evidence_to_dict,
    resolve_many_source_span_refs,
    resolve_source_span_ref,
    source_span_ref_from_dict,
    source_span_ref_to_dict,
)


def _fixture_resolved():
    fixture = load_fixture()
    texts, structured, refs = build_registries(fixture)
    return fixture, texts, structured, refs, resolve_many_source_span_refs(refs, text_artifacts=texts, structured_artifacts=structured)


def _codes(evidence):
    return {json.loads(w)["code"] for w in evidence.warnings}


def test_fixture_and_cli_paths() -> None:
    assert FIXTURE_PATH.is_file()
    fixture = load_fixture()
    assert fixture["schema"] == "dmb_source_span_evidence_resolver_fixture_v0"
    assert fixture["version"] == "0.1"
    assert fixture["text_artifacts"]
    assert fixture["structured_artifacts"]
    assert fixture["source_span_refs"]
    assert subprocess.run([sys.executable, "-m", "evals.graph_memory_layer.validate_source_span_resolver_fixture"], check=False).returncode == 0
    assert subprocess.run([sys.executable, "-m", "evals.graph_memory_layer.report_source_span_resolver_fixture"], check=False).returncode == 0


def test_text_resolution_valid_spans_and_context() -> None:
    _, _, _, _, resolved = _fixture_resolved()
    single = resolved[0]
    assert single.preview_snippet.startswith("The party returned")
    assert single.start_line == 8 and single.end_line == 8
    assert single.can_open_source is True
    assert single.can_highlight_span is True
    assert len(single.preview_snippet) <= DEFAULT_SNIPPET_MAX_CHARS
    multi = resolved[1]
    assert "unsigned warning" in multi.preview_snippet
    assert "previous watch" in multi.preview_snippet
    assert multi.surrounding_context is not None
    assert len(multi.surrounding_context) <= DEFAULT_CONTEXT_MAX_CHARS


def test_line_numbers_are_one_based() -> None:
    _, texts, _, _, _ = _fixture_resolved()
    ref = SourceSpanRef("source-ref:normalized_recap_markdown:dogfood", "source-artifact:normalized_recap_markdown:dogfood", start_line=1, end_line=1)
    evidence = resolve_source_span_ref(ref, text_artifacts=texts)
    assert evidence.preview_snippet == "# Dogfood Session Recap: Redacted Lantern Archive"


def test_structured_resolution() -> None:
    _, _, _, _, resolved = _fixture_resolved()
    top = resolved[3]
    nested = resolved[4]
    assert top.structured_value_preview == "source-span-resolver-v0"
    assert nested.structured_value_preview == "12"
    assert top.can_open_source and nested.can_open_source
    assert top.can_highlight_span and nested.can_highlight_span


def test_invalid_resolution_visible_issues() -> None:
    _, texts, structured, refs, resolved = _fixture_resolved()
    assert "missing_source_artifact" in _codes(resolved[5])
    assert "span_out_of_range" in _codes(resolved[6])
    assert "structured_path_missing" in _codes(resolved[7])
    mismatch = resolve_source_span_ref(SourceSpanRef("bad", refs[0].source_artifact_id, start_line=8, end_line=8), text_artifacts=texts)
    assert "source_ref_mismatch" in _codes(mismatch)
    bad_char = resolve_source_span_ref(SourceSpanRef(refs[0].source_ref_id, refs[0].source_artifact_id, start_line=8, end_line=8, start_char=500), text_artifacts=texts)
    assert "span_out_of_range" in _codes(bad_char)
    ambiguous = resolve_source_span_ref(SourceSpanRef(refs[0].source_ref_id, refs[0].source_artifact_id, start_line=8, end_line=8, structured_path="fixture"), text_artifacts=texts, structured_artifacts=structured)
    assert "ambiguous_source_span_ref" in _codes(ambiguous)


def test_safety_boundaries() -> None:
    _, texts, _, _, resolved = _fixture_resolved()
    serialized = json.dumps([resolved_evidence_to_dict(item) for item in resolved], sort_keys=True)
    for artifact in texts.values():
        assert artifact.text not in serialized
    assert "/workspace/" not in serialized and "/home/" not in serialized
    for token in ("_normalized/", "_breadcrumbed/", ".records_meta.jsonl", "adapter_payload", "plan_payload", "agent_interaction", "runtime_ui_payload", "entity", "alias", "relationship", "fact_promotion", "canon_promotion"):
        assert token not in serialized
    assert all(len(item.preview_snippet) <= DEFAULT_SNIPPET_MAX_CHARS for item in resolved)
    assert all(item.surrounding_context is None or len(item.surrounding_context) <= DEFAULT_CONTEXT_MAX_CHARS for item in resolved)


def test_serialization_round_trips_and_report_counts() -> None:
    ref = SourceSpanRef("ref", "artifact", start_line=1, end_line=1)
    assert source_span_ref_from_dict(source_span_ref_to_dict(ref)) == ref
    _, _, _, refs, resolved = _fixture_resolved()
    assert "preview_snippet" in resolved_evidence_to_dict(resolved[0])
    report = analyze_evidence_resolution(refs, resolved)
    data = evidence_resolution_report_to_dict(report)
    assert data["issue_counts"]["blocker"] >= 1
    assert data["schema"] == "dmb_source_span_evidence_resolver_v0"
    assert EvidenceResolutionReport(**{**data, "issues": tuple(EvidenceResolutionIssue(**i) for i in data["issues"])})
