from __future__ import annotations

import hashlib
import json
from pathlib import Path, PurePosixPath
from typing import Any, Mapping

from pydantic import ValidationError

from graph_memory.extraction.known_entity_mention_schema import (
    KNOWN_ENTITY_MENTION_SIDECAR_SCHEMA,
    KNOWN_ENTITY_MENTION_SIDECAR_VERSION,
    KnownEntityMentionSidecar,
)
from graph_memory.ingestion.extraction_run import normalize_content_digest
from graph_memory.ingestion.graph_ingest_run import (
    GRAPH_INGEST_RUN_MANIFEST_SCHEMA,
    GraphIngestArtifactKind,
    GraphIngestRunManifest,
    GraphIngestRunStatus,
)
from graph_memory.source_span import (
    source_span_index_from_dict,
    validate_source_span_index,
)

FORBIDDEN_DIAGNOSTIC_FLAGS = (
    "canon_promotion",
    "approved_memory_write",
    "corpus_mutation",
    "production_retrieval",
)
TERMINAL_STATUSES = {GraphIngestRunStatus.READY_FOR_PROJECTION}
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
CANDIDATE_READY_STATUSES = {
    GraphIngestRunStatus.CANDIDATE_VALIDATION_READY,
    GraphIngestRunStatus.PREVIEW_UNION_STORE_READY,
    GraphIngestRunStatus.READY_FOR_PROJECTION,
}


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


def _iter_artifact_refs(manifest: GraphIngestRunManifest):
    yield from manifest.artifacts.values()
    for step in manifest.steps:
        yield from step.artifact_refs


def _artifact_kinds(manifest: GraphIngestRunManifest) -> list[str]:
    return sorted({artifact.kind.value for artifact in _iter_artifact_refs(manifest)})


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

        for artifact in _iter_artifact_refs(manifest):
            if artifact.preview_only is not True:
                _error(
                    errors,
                    f"artifact must be preview_only: {artifact.kind.value} {artifact.uri}",
                )

        status_order = SOURCE_READY_ORDER[manifest.status]
        if manifest.status != GraphIngestRunStatus.FAILED:
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
                if not manifest.projection.projection_endpoint:
                    _error(
                        errors,
                        "ready_for_projection requires projection.projection_endpoint",
                    )
                if manifest.projection.query.get("session_id") != manifest.session_id:
                    _error(
                        errors,
                        "projection query session_id must match manifest session_id",
                    )
                if not manifest.projection.query.get("preview_union_store_path"):
                    _error(
                        errors,
                        "ready_for_projection requires projection query preview_union_store_path",
                    )
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


def _resolve_manifest_uri(repo_root: Path, uri: str) -> Path:
    raw = uri.removeprefix("repo://") if uri.startswith("repo://") else uri
    path = (repo_root / raw).resolve() if not Path(raw).is_absolute() else Path(raw).resolve()
    path.relative_to(repo_root.resolve())
    return path


def validate_manifest_source_span_index_linkage(
    repo_root: Path,
    payload: Mapping[str, Any],
) -> list[str]:
    """Fail closed when SourceSpanIndex is missing, malformed, or unbound to source.

    Requires projection and artifact URIs to resolve to the same file, then parses
    with ``source_span_index_from_dict`` and re-validates against the manifest's
    ``source_artifact_id`` and the packaged recap file's actual bytes.
    """
    errors: list[str] = []
    source = payload.get("source") if isinstance(payload.get("source"), dict) else {}
    artifacts = payload.get("artifacts") if isinstance(payload.get("artifacts"), dict) else {}
    expected_artifact_id = str(source.get("source_artifact_id") or "").strip()
    claimed_source_digest = normalize_content_digest(source.get("normalized_recap_sha256"))
    if not expected_artifact_id:
        errors.append("source.source_artifact_id is required for SourceSpanIndex linkage")
    if not claimed_source_digest:
        errors.append("source.normalized_recap_sha256 is required for SourceSpanIndex linkage")

    normalized_recap_path = source.get("normalized_recap_path")
    if not isinstance(normalized_recap_path, str) or not normalized_recap_path.strip():
        errors.append("source.normalized_recap_path is required for SourceSpanIndex linkage")
        return errors
    try:
        recap_path = _resolve_manifest_uri(repo_root, normalized_recap_path)
    except ValueError as exc:
        errors.append(f"source.normalized_recap_path escapes repo root: {exc}")
        return errors
    if not recap_path.is_file():
        errors.append("source.normalized_recap_path file is missing")
        return errors
    actual_recap_digest = hashlib.sha256(recap_path.read_bytes()).hexdigest().lower()
    if claimed_source_digest and actual_recap_digest != claimed_source_digest:
        errors.append(
            "packaged recap bytes do not match source.normalized_recap_sha256"
        )
        return errors
    artifact_recap = artifacts.get("normalized_recap")
    if isinstance(artifact_recap, dict):
        artifact_digest = normalize_content_digest(artifact_recap.get("sha256"))
        if artifact_digest and artifact_digest != actual_recap_digest:
            errors.append(
                "packaged recap bytes do not match artifacts.normalized_recap.sha256"
            )
            return errors

    span_ref = artifacts.get(GraphIngestArtifactKind.SOURCE_SPAN_INDEX.value)
    if not isinstance(span_ref, dict):
        errors.append("artifacts.source_span_index is required")
        return errors
    span_uri = span_ref.get("uri")
    if not isinstance(span_uri, str) or not span_uri.strip():
        errors.append("artifacts.source_span_index.uri is required")
        return errors
    claimed_digest = span_ref.get("sha256")
    if not isinstance(claimed_digest, str) or not claimed_digest.strip():
        errors.append("artifacts.source_span_index.sha256 is required")
        return errors
    source_span_uri = source.get("source_span_index_uri")
    if not isinstance(source_span_uri, str) or not source_span_uri.strip():
        errors.append("source.source_span_index_uri is required")
        return errors

    try:
        artifact_path = _resolve_manifest_uri(repo_root, span_uri)
        projection_path = _resolve_manifest_uri(repo_root, source_span_uri)
    except ValueError as exc:
        errors.append(f"SourceSpanIndex URI escapes repo root: {exc}")
        return errors
    if not artifact_path.is_file() or not projection_path.is_file():
        errors.append("SourceSpanIndex file is missing")
        return errors
    if artifact_path.resolve() != projection_path.resolve():
        errors.append(
            "source.source_span_index_uri must resolve to the same file as "
            "artifacts.source_span_index"
        )
        return errors

    span_bytes = artifact_path.read_bytes()
    actual_digest = hashlib.sha256(span_bytes).hexdigest().lower()
    if normalize_content_digest(claimed_digest) != actual_digest:
        errors.append("artifacts.source_span_index.sha256 does not match file bytes")
        return errors

    try:
        index_payload = json.loads(span_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        errors.append(f"SourceSpanIndex is not valid JSON: {exc}")
        return errors
    if not isinstance(index_payload, dict):
        errors.append("SourceSpanIndex payload must be an object")
        return errors

    try:
        index = source_span_index_from_dict(index_payload)
        if normalize_content_digest(index.content_sha256) != actual_recap_digest:
            errors.append(
                "SourceSpanIndex.content_sha256 does not match packaged recap bytes"
            )
            return errors
        if expected_artifact_id:
            validate_source_span_index(
                index,
                source_artifact_id=expected_artifact_id,
                content_sha256=actual_recap_digest,
            )
    except (TypeError, ValueError, KeyError) as exc:
        errors.append(f"SourceSpanIndex failed canonical validation: {exc}")
    return errors


def validate_manifest_known_entity_mentions(
    repo_root: Path,
    payload: Mapping[str, Any],
) -> list[str]:
    """Fail closed when known-entity sidecar is missing, undigested, or malformed."""
    errors: list[str] = []
    artifacts = payload.get("artifacts") if isinstance(payload.get("artifacts"), dict) else {}
    artifact = artifacts.get(GraphIngestArtifactKind.KNOWN_ENTITY_MENTIONS.value)
    if not isinstance(artifact, dict):
        errors.append("artifacts.known_entity_mentions is required")
        return errors
    uri = artifact.get("uri")
    if not isinstance(uri, str) or not uri.strip():
        errors.append("artifacts.known_entity_mentions.uri is required")
        return errors
    claimed_digest = artifact.get("sha256")
    if not isinstance(claimed_digest, str) or not claimed_digest.strip():
        errors.append("artifacts.known_entity_mentions.sha256 is required")
        return errors

    try:
        sidecar_path = _resolve_manifest_uri(repo_root, uri)
    except ValueError as exc:
        errors.append(f"known_entity_mentions URI escapes repo root: {exc}")
        return errors
    if not sidecar_path.is_file():
        errors.append("known_entity_mentions file is missing")
        return errors

    sidecar_bytes = sidecar_path.read_bytes()
    actual_digest = hashlib.sha256(sidecar_bytes).hexdigest().lower()
    if normalize_content_digest(claimed_digest) != actual_digest:
        errors.append("artifacts.known_entity_mentions.sha256 does not match file bytes")
        return errors

    try:
        sidecar_payload = json.loads(sidecar_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        errors.append(f"known_entity_mentions is not valid JSON: {exc}")
        return errors
    if not isinstance(sidecar_payload, dict):
        errors.append("known_entity_mentions payload must be an object")
        return errors

    # Validate the raw payload before coercion so defaults cannot invent a contract.
    for key in ("schema", "version", "campaign_id", "session_id"):
        value = sidecar_payload.get(key)
        if key not in sidecar_payload or not isinstance(value, str) or not value.strip():
            errors.append(f"known_entity_mentions.{key} is required")
    if "mentions" not in sidecar_payload or not isinstance(
        sidecar_payload.get("mentions"), list
    ):
        errors.append("known_entity_mentions.mentions must be a list")
    if "ambiguous_surfaces" not in sidecar_payload or not isinstance(
        sidecar_payload.get("ambiguous_surfaces"), list
    ):
        errors.append("known_entity_mentions.ambiguous_surfaces must be a list")
    if errors:
        return errors

    if sidecar_payload["schema"] != KNOWN_ENTITY_MENTION_SIDECAR_SCHEMA:
        errors.append(
            f"known_entity_mentions schema must be {KNOWN_ENTITY_MENTION_SIDECAR_SCHEMA}"
        )
    if sidecar_payload["version"] != KNOWN_ENTITY_MENTION_SIDECAR_VERSION:
        errors.append(
            f"known_entity_mentions version must be {KNOWN_ENTITY_MENTION_SIDECAR_VERSION}"
        )

    campaign_id = str(payload.get("campaign_id") or "").strip()
    session_id = str(payload.get("session_id") or "").strip()
    sidecar_campaign = str(sidecar_payload["campaign_id"]).strip()
    sidecar_session = str(sidecar_payload["session_id"]).strip()
    if sidecar_campaign != campaign_id:
        errors.append("known_entity_mentions.campaign_id does not match manifest")
    if sidecar_session != session_id:
        errors.append("known_entity_mentions.session_id does not match manifest")
    if errors:
        return errors

    try:
        KnownEntityMentionSidecar.from_mapping(sidecar_payload)
    except (TypeError, ValueError, KeyError) as exc:
        errors.append(f"known_entity_mentions failed schema parse: {exc}")
    return errors


def assert_candidate_ready_evidence(repo_root: Path, payload: Mapping[str, Any]) -> None:
    """Raise when a candidate-ready GraphIngest run lacks usable evidence linkage."""
    errors = validate_manifest_source_span_index_linkage(repo_root, payload)
    errors.extend(validate_manifest_known_entity_mentions(repo_root, payload))
    if errors:
        raise ValueError(
            "candidate-ready GraphIngest evidence is unusable: " + "; ".join(errors)
        )


def known_entity_mentions_digest(repo_root: Path, payload: Mapping[str, Any]) -> str | None:
    """Return the verified known-entity sidecar digest, or None when unusable."""
    errors = validate_manifest_known_entity_mentions(repo_root, payload)
    if errors:
        return None
    artifacts = payload.get("artifacts") if isinstance(payload.get("artifacts"), dict) else {}
    artifact = artifacts.get(GraphIngestArtifactKind.KNOWN_ENTITY_MENTIONS.value)
    if not isinstance(artifact, dict):
        return None
    return normalize_content_digest(artifact.get("sha256")) or None
