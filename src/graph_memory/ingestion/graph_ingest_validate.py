from __future__ import annotations

import json
from pathlib import PurePosixPath
from typing import Any, Mapping

from pydantic import ValidationError

from graph_memory.ingestion.graph_ingest_run import (
    GRAPH_INGEST_RUN_MANIFEST_SCHEMA,
    GraphIngestArtifactKind,
    GraphIngestRunManifest,
    GraphIngestRunStatus,
)

FORBIDDEN_DIAGNOSTIC_FLAGS = (
    "canon_promotion",
    "approved_memory_write",
    "corpus_mutation",
    "production_retrieval",
)
TERMINAL_STATUSES = {
    GraphIngestRunStatus.READY_FOR_PROJECTION,
    GraphIngestRunStatus.FAILED,
}
SOURCE_READY_ORDER = {
    GraphIngestRunStatus.NOT_STARTED: 0,
    GraphIngestRunStatus.SOURCE_READY: 1,
    GraphIngestRunStatus.SOURCE_SPAN_BUNDLE_READY: 2,
    GraphIngestRunStatus.CANDIDATE_EXTRACTION_READY: 3,
    GraphIngestRunStatus.CANDIDATE_VALIDATION_READY: 4,
    GraphIngestRunStatus.PREVIEW_UNION_STORE_READY: 5,
    GraphIngestRunStatus.READY_FOR_PROJECTION: 6,
    GraphIngestRunStatus.FAILED: 99,
}
URI_FIELD_SUFFIXES = ("_uri", "_path")


def _error(errors: list[str], message: str) -> None:
    errors.append(message)


def _warning(warnings: list[str], message: str) -> None:
    warnings.append(message)


def _is_safe_repo_relative_uri(value: str) -> bool:
    if value.startswith(("/", "file:/")):
        return False
    # Allow API endpoints in locators, but artifact/source file locations stay repo-relative.
    path = PurePosixPath(value)
    return ".." not in path.parts


def _collect_path_values(
    value: Any, path: str = "$", *, include_uri_key: bool = False
) -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []
    if isinstance(value, Mapping):
        for key, child in value.items():
            key_str = str(key)
            child_path = f"{path}.{key_str}"
            is_uri_key = key_str == "uri" or key_str.endswith(URI_FIELD_SUFFIXES)
            found.extend(
                _collect_path_values(child, child_path, include_uri_key=is_uri_key)
            )
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found.extend(
                _collect_path_values(
                    child, f"{path}[{index}]", include_uri_key=include_uri_key
                )
            )
    elif include_uri_key and isinstance(value, str):
        found.append((path, value))
    return found


def _artifact_kinds(manifest: GraphIngestRunManifest) -> list[str]:
    kinds = {artifact.kind.value for artifact in manifest.artifacts.values()}
    for step in manifest.steps:
        kinds.update(ref.kind.value for ref in step.artifact_refs)
    return sorted(kinds)


def validate_graph_ingest_run_manifest(payload: Mapping[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []

    if payload.get("schema") != GRAPH_INGEST_RUN_MANIFEST_SCHEMA:
        _error(errors, "unknown schema")

    for field in ("run_id", "campaign_id", "session_id"):
        if not payload.get(field):
            _error(errors, f"missing {field}")

    try:
        json.dumps(payload, sort_keys=True)
    except (TypeError, ValueError) as exc:
        _error(errors, f"non-JSON-safe value: {exc}")

    for path, value in _collect_path_values(payload):
        if path.endswith("projection.projection_endpoint"):
            continue
        if not _is_safe_repo_relative_uri(value):
            _error(errors, f"unsafe repo-relative path at {path}: {value}")

    manifest: GraphIngestRunManifest | None = None
    try:
        manifest = GraphIngestRunManifest.model_validate(payload)
    except ValidationError as exc:
        _error(errors, f"manifest model validation failed: {exc}")

    if manifest is not None:
        for flag in FORBIDDEN_DIAGNOSTIC_FLAGS:
            if getattr(manifest.diagnostics, flag):
                _error(errors, f"forbidden diagnostic flag is true: {flag}")
        if manifest.diagnostics.preview_only is not True:
            _error(errors, "diagnostics.preview_only must be true")

        status_order = SOURCE_READY_ORDER[manifest.status]
        if (
            status_order >= SOURCE_READY_ORDER[GraphIngestRunStatus.SOURCE_READY]
            and not manifest.source.normalized_recap_sha256
        ):
            msg = "missing normalized recap SHA for source-ready manifest"
            if manifest.status in TERMINAL_STATUSES:
                _error(errors, msg)
            else:
                _warning(warnings, msg)

        artifact_kinds = _artifact_kinds(manifest)
        if (
            status_order
            >= SOURCE_READY_ORDER[GraphIngestRunStatus.CANDIDATE_EXTRACTION_READY]
            and GraphIngestArtifactKind.SOURCE_SPAN_BUNDLE.value not in artifact_kinds
            and not manifest.source.source_span_bundle_uri
        ):
            _warning(warnings, "missing source span bundle before candidate extraction")

        if (
            manifest.health.evidence_ref_count
            and manifest.health.resolvable_evidence_ref_count
            > manifest.health.evidence_ref_count
        ):
            _warning(
                warnings, "resolvable evidence ref count exceeds evidence ref count"
            )
        if (
            manifest.health.evidence_ref_count
            and manifest.health.openable_evidence_ref_count
            > manifest.health.evidence_ref_count
        ):
            _warning(warnings, "openable evidence ref count exceeds evidence ref count")
        if (
            manifest.health.evidence_ref_count
            and manifest.health.highlightable_evidence_ref_count
            > manifest.health.evidence_ref_count
        ):
            _warning(
                warnings, "highlightable evidence ref count exceeds evidence ref count"
            )

        if not manifest.next_actions:
            _warning(warnings, "no next_actions declared")

        if manifest.diagnostics.candidate_extraction and (
            manifest.health.model_id is None
            or manifest.health.estimated_cost_usd is None
        ):
            _warning(
                warnings,
                "candidate extraction has nullable model_id or estimated_cost_usd",
            )

        if manifest.status == GraphIngestRunStatus.READY_FOR_PROJECTION:
            if GraphIngestArtifactKind.PREVIEW_UNION_STORE.value not in artifact_kinds:
                _error(
                    errors,
                    "ready_for_projection requires a preview_union_store artifact",
                )
            if (
                manifest.projection is None
                or manifest.projection.projection_ready is not True
            ):
                _error(errors, "ready_for_projection requires a projection locator")
    else:
        artifact_kinds = []

    return {
        "valid": not errors,
        "errors": errors,
        "warnings": warnings,
        "campaign_id": payload.get("campaign_id"),
        "session_id": payload.get("session_id"),
        "status": payload.get("status"),
        "artifact_kinds": artifact_kinds,
        "preview_only": None if manifest is None else manifest.diagnostics.preview_only,
        "projection_ready": False
        if manifest is None or manifest.projection is None
        else manifest.projection.projection_ready,
    }
