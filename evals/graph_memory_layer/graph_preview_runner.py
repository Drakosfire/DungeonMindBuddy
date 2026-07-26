"""Compatibility shim — GraphIngest packaging moved to a production-owned module.

# PR003_LEGACY_GRAPH_PREVIEW_EXEMPTION:
# Retained until PR006/PR007 replaces live Graph Review preview materialization.

The packaging implementation (``GraphPreviewRunnerOptions``, ``run_graph_preview_extraction``,
and their helpers) now lives in
``src.graph_memory.extraction.graph_ingest_packaging`` so
``apps/live_control_server/services/recap_graph_preview_ingest.py`` (the live
recap-ingest path) does not import eval-only code for production packaging.

This module re-exports the same public API unchanged so existing eval/dogfood
callers and tests keep working without modification. Do not add new packaging
logic here — add it to the production module instead.
"""

from __future__ import annotations

from src.graph_memory.extraction.graph_ingest_packaging import (
    CandidateValidationResult,
    ComparisonMode,
    GraphExtractionProfile,
    GraphPreviewRunnerOptions,
    GraphPreviewRunnerResult,
    category_options_for_graph_extraction_profile,
    compute_sha256,
    ensure_output_dir,
    graph_extraction_profile_options,
    normalize_graph_extraction_profile,
    run_graph_preview_extraction,
    safe_relative_artifact_uri,
    write_json,
)
from src.graph_memory.extraction.graph_ingest_packaging import (
    _artifact,
    _assert_packaged_source_artifact_identity,
    _candidate_counts,
    _copy_source_recap,
    _graph_list_fields,
    _is_full_text_span_id,
    _is_paragraph_span_id,
    _line_number_at,
    _now_iso,
    _repo_root,
    _require_candidate_graph_identity,
    _resolve_packaged_source_artifact_id,
    _session_number,
    _slug,
    _span_identity,
    _split_recap_paragraph_spans,
    _validate_safe_relative_path,
    _with_candidate_graph_identity,
    _write_canonical_source_span_bundle,
    _write_source_span_bundle,
    _write_validation_report,
)

__all__ = [
    "CandidateValidationResult",
    "ComparisonMode",
    "GraphExtractionProfile",
    "GraphPreviewRunnerOptions",
    "GraphPreviewRunnerResult",
    "category_options_for_graph_extraction_profile",
    "compute_sha256",
    "ensure_output_dir",
    "graph_extraction_profile_options",
    "normalize_graph_extraction_profile",
    "run_graph_preview_extraction",
    "safe_relative_artifact_uri",
    "write_json",
    # Underscore-prefixed helpers re-exported for existing test/dogfood call sites
    # that reach into module internals (e.g. `_with_candidate_graph_identity` to
    # stamp fixture candidates). Not part of the intended public surface.
    "_artifact",
    "_assert_packaged_source_artifact_identity",
    "_candidate_counts",
    "_copy_source_recap",
    "_graph_list_fields",
    "_is_full_text_span_id",
    "_is_paragraph_span_id",
    "_line_number_at",
    "_now_iso",
    "_repo_root",
    "_require_candidate_graph_identity",
    "_resolve_packaged_source_artifact_id",
    "_session_number",
    "_slug",
    "_span_identity",
    "_split_recap_paragraph_spans",
    "_validate_safe_relative_path",
    "_with_candidate_graph_identity",
    "_write_canonical_source_span_bundle",
    "_write_source_span_bundle",
    "_write_validation_report",
]
