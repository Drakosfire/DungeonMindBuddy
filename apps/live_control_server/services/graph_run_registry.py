"""Canonical exact ExtractionRun registry."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field, ValidationError

from apps.live_control_server.services.registry_file_lock import (
    registry_mutation_lock,
    registry_token,
)
from apps.live_control_server.services.source_artifact_registry import (
    SourceArtifactRegistryError,
    get_source_artifact,
)
from graph_memory.evidence.source_artifact import GraphMemorySourceArtifact
from graph_memory.ingestion.extraction_run import (
    FROZEN_COMPONENT_STATUSES,
    TERMINAL_EXTRACTION_RUN_STATUSES,
    ExtractionRun,
    ExtractionRunComponentKind,
    ExtractionRunComponentRef,
    ExtractionRunDiagnostics,
    ExtractionRunStatus,
    assert_allowed_extraction_run_transition,
    normalize_content_digest,
    validate_extraction_run_lineage,
    validate_extraction_run_record,
)
from graph_memory.source_span import validate_source_span_index
from src.live_play.live_store import load_json, write_json

DEFAULT_EXTRACTION_RUN_REGISTRY_REL = "out/registries/extraction_runs.json"
EXTRACTION_RUN_REGISTRY_SCHEMA = "dmb_extraction_run_registry_v1"

# Statuses that necessarily originated from a complete reviewable bundle.
_REVIEW_BUNDLE_STATUSES = frozenset(
    {
        ExtractionRunStatus.REVIEWABLE,
        ExtractionRunStatus.PROMOTED,
    }
)


class GraphRunRegistryError(ValueError):
    status_code: int = 404

    def __init__(self, message: str, *, status_code: int = 404) -> None:
        super().__init__(message)
        self.status_code = status_code


class ExtractionRunRegistryDocument(BaseModel):
    schema_version: str = EXTRACTION_RUN_REGISTRY_SCHEMA
    records: list[ExtractionRun] = Field(default_factory=list)


def _utc_now_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def extraction_runs_path(root: Path) -> Path:
    return root / DEFAULT_EXTRACTION_RUN_REGISTRY_REL


def _resolve_repo_contained_uri(root: Path, uri: str) -> Path:
    raw = uri or ""
    if not raw:
        raise GraphRunRegistryError("component uri is required", status_code=422)
    if raw != raw.strip():
        raise GraphRunRegistryError(f"unsafe component uri: {uri}", status_code=422)
    value = raw
    if value.startswith("repo://"):
        value = value[len("repo://") :]
    if value.startswith("file:"):
        raise GraphRunRegistryError(f"unsafe component uri: {uri}", status_code=422)
    if "\\" in value:
        raise GraphRunRegistryError(f"unsafe component uri: {uri}", status_code=422)
    candidate = Path(value)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise GraphRunRegistryError(f"unsafe component uri: {uri}", status_code=422)
    resolved_root = root.resolve()
    resolved = (resolved_root / value).resolve()
    if not resolved.is_relative_to(resolved_root):
        raise GraphRunRegistryError(f"component uri escapes repository root: {uri}", status_code=422)
    return resolved


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _component_by_kind(
    components: dict[str, ExtractionRunComponentRef],
    kind: ExtractionRunComponentKind,
) -> ExtractionRunComponentRef | None:
    return components.get(kind.value)


def assert_run_reviewable_evidence(root: Path, run: ExtractionRun) -> None:
    """Server-side evidence resolution required for reviewable/promoted runs."""
    try:
        artifact = get_source_artifact(root, run.source_artifact_id)
    except SourceArtifactRegistryError as exc:
        raise GraphRunRegistryError(
            f"unknown source_artifact_id: {run.source_artifact_id}",
            status_code=422,
        ) from exc

    if str(artifact.source_domain) != run.source_domain:
        raise GraphRunRegistryError(
            "extraction run source_domain does not match SourceArtifact",
            status_code=422,
        )
    if artifact.campaign_id != run.campaign_id:
        raise GraphRunRegistryError(
            "extraction run campaign_id does not match SourceArtifact",
            status_code=422,
        )
    if artifact.session_id != run.session_id:
        raise GraphRunRegistryError(
            "extraction run session_id does not match SourceArtifact",
            status_code=422,
        )

    source_component = _component_by_kind(
        run.components, ExtractionRunComponentKind.SOURCE_ARTIFACT
    )
    span_component = _component_by_kind(
        run.components, ExtractionRunComponentKind.SOURCE_SPAN_INDEX
    )
    graph_component = _component_by_kind(
        run.components, ExtractionRunComponentKind.CANDIDATE_GRAPH
    )
    if source_component is None or span_component is None or graph_component is None:
        raise GraphRunRegistryError(
            "reviewable runs require source_artifact, source_span_index, and candidate_graph",
            status_code=422,
        )

    _assert_component_bytes(root, source_component, expected_digest=artifact.content_sha256)
    _assert_source_component_matches_artifact(source_component, artifact)

    span_path = _assert_component_bytes(root, span_component)
    try:
        from graph_memory.source_span import source_span_index_from_dict

        index = source_span_index_from_dict(load_json(span_path))
        validate_source_span_index(
            index,
            source_artifact_id=artifact.source_artifact_id,
            content_sha256=artifact.content_sha256 or "",
        )
    except (TypeError, ValueError, KeyError) as exc:
        raise GraphRunRegistryError(
            f"source_span_index is not bound to source artifact: {exc}",
            status_code=422,
        ) from exc

    _assert_component_bytes(root, graph_component)


def assert_immutable_component_refs(root: Path, run: ExtractionRun) -> None:
    """Validate any supplied immutable component references present on a run."""
    artifact: GraphMemorySourceArtifact | None = None
    for component in run.components.values():
        if not component.uri.strip() or not (component.sha256 or "").strip():
            continue
        if component.kind == ExtractionRunComponentKind.SOURCE_ARTIFACT:
            if artifact is None:
                try:
                    artifact = get_source_artifact(root, run.source_artifact_id)
                except SourceArtifactRegistryError as exc:
                    raise GraphRunRegistryError(
                        f"unknown source_artifact_id: {run.source_artifact_id}",
                        status_code=422,
                    ) from exc
            _assert_component_bytes(
                root, component, expected_digest=artifact.content_sha256
            )
            _assert_source_component_matches_artifact(component, artifact)
            continue
        path = _assert_component_bytes(root, component)
        if component.kind == ExtractionRunComponentKind.SOURCE_SPAN_INDEX:
            if artifact is None:
                try:
                    artifact = get_source_artifact(root, run.source_artifact_id)
                except SourceArtifactRegistryError as exc:
                    raise GraphRunRegistryError(
                        f"unknown source_artifact_id: {run.source_artifact_id}",
                        status_code=422,
                    ) from exc
            try:
                from graph_memory.source_span import source_span_index_from_dict

                index = source_span_index_from_dict(load_json(path))
                validate_source_span_index(
                    index,
                    source_artifact_id=artifact.source_artifact_id,
                    content_sha256=artifact.content_sha256 or "",
                )
            except (TypeError, ValueError, KeyError) as exc:
                raise GraphRunRegistryError(
                    f"source_span_index is not bound to source artifact: {exc}",
                    status_code=422,
                ) from exc


def _assert_source_component_matches_artifact(
    component: ExtractionRunComponentRef,
    artifact: GraphMemorySourceArtifact,
) -> None:
    uri = component.uri
    if uri != uri.strip():
        raise GraphRunRegistryError(
            "source_artifact component uri is whitespace-contaminated",
            status_code=422,
        )
    expected = artifact.uri
    if uri.startswith("repo://"):
        if uri != expected:
            raise GraphRunRegistryError(
                "source_artifact component uri does not match SourceArtifact",
                status_code=422,
            )
    else:
        expected_rel = expected.removeprefix("repo://")
        if uri != expected_rel:
            raise GraphRunRegistryError(
                "source_artifact component uri does not match SourceArtifact",
                status_code=422,
            )
    if normalize_content_digest(component.sha256) != normalize_content_digest(
        artifact.content_sha256
    ):
        raise GraphRunRegistryError(
            "source_artifact component digest does not match SourceArtifact",
            status_code=422,
        )


def _assert_component_bytes(
    root: Path,
    component: ExtractionRunComponentRef,
    *,
    expected_digest: str | None = None,
) -> Path:
    path = _resolve_repo_contained_uri(root, component.uri)
    if not path.is_file():
        raise GraphRunRegistryError(
            f"component file missing: {component.uri}",
            status_code=422,
        )
    digest = _file_sha256(path)
    claimed = normalize_content_digest(component.sha256)
    if not claimed:
        raise GraphRunRegistryError(
            f"component digest required: {component.kind.value}",
            status_code=422,
        )
    if claimed != digest:
        raise GraphRunRegistryError(
            f"component digest mismatch: {component.kind.value}",
            status_code=422,
        )
    if expected_digest is not None and digest != normalize_content_digest(expected_digest):
        raise GraphRunRegistryError(
            f"component digest does not match expected source digest: {component.kind.value}",
            status_code=422,
        )
    return path


def _assert_persisted_run_integrity(root: Path, run: ExtractionRun) -> None:
    if run.status in _REVIEW_BUNDLE_STATUSES:
        assert_run_reviewable_evidence(root, run)
        return
    if run.status in TERMINAL_EXTRACTION_RUN_STATUSES:
        assert_immutable_component_refs(root, run)


def _validate_persisted_runs(root: Path, records: list[ExtractionRun]) -> None:
    seen: set[str] = set()
    for run in records:
        try:
            validate_extraction_run_record(run)
        except ValueError as exc:
            raise GraphRunRegistryError(
                f"malformed extraction run registry record: {exc}",
                status_code=500,
            ) from exc
        if run.run_id in seen:
            raise GraphRunRegistryError(
                f"duplicate extraction run id: {run.run_id}",
                status_code=500,
            )
        seen.add(run.run_id)
        try:
            _assert_persisted_run_integrity(root, run)
        except GraphRunRegistryError as exc:
            raise GraphRunRegistryError(
                f"extraction run failed integrity validation: {exc}",
                status_code=500,
            ) from exc
    try:
        validate_extraction_run_lineage(records)
    except ValueError as exc:
        raise GraphRunRegistryError(
            f"malformed extraction run lineage: {exc}",
            status_code=500,
        ) from exc


def _load_unlocked(root: Path) -> tuple[ExtractionRunRegistryDocument, str]:
    path = extraction_runs_path(root)
    token = registry_token(path)
    if not path.is_file():
        return ExtractionRunRegistryDocument(), token
    try:
        document = ExtractionRunRegistryDocument.model_validate(load_json(path))
    except (ValidationError, TypeError, ValueError) as exc:
        raise GraphRunRegistryError(
            f"malformed extraction run registry: {exc}",
            status_code=500,
        ) from exc
    _validate_persisted_runs(root, document.records)
    return document, token


def _load(root: Path) -> ExtractionRunRegistryDocument:
    document, _token = _load_unlocked(root)
    return document


def _save_cas(
    root: Path,
    document: ExtractionRunRegistryDocument,
    *,
    expected_token: str,
) -> None:
    _validate_persisted_runs(root, document.records)
    path = extraction_runs_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    current = registry_token(path)
    if current != expected_token:
        raise GraphRunRegistryError(
            "extraction run registry changed concurrently",
            status_code=409,
        )
    write_json(path, document.model_dump(mode="json"))


def _bind_run_to_artifact(
    root: Path,
    *,
    source_artifact_id: str,
    source_domain: str,
    campaign_id: str | None,
    session_id: str | None,
) -> GraphMemorySourceArtifact:
    if not source_artifact_id.strip():
        raise GraphRunRegistryError("source_artifact_id is required", status_code=422)
    try:
        artifact = get_source_artifact(root, source_artifact_id)
    except SourceArtifactRegistryError as exc:
        raise GraphRunRegistryError(
            f"unknown source_artifact_id: {source_artifact_id}",
            status_code=422,
        ) from exc
    if str(artifact.source_domain) != source_domain:
        raise GraphRunRegistryError(
            "source_domain does not match SourceArtifact",
            status_code=422,
        )
    resolved_campaign = campaign_id if campaign_id is not None else artifact.campaign_id
    resolved_session = session_id if session_id is not None else artifact.session_id
    if resolved_campaign != artifact.campaign_id:
        raise GraphRunRegistryError(
            "campaign_id does not match SourceArtifact",
            status_code=422,
        )
    if resolved_session != artifact.session_id:
        raise GraphRunRegistryError(
            "session_id does not match SourceArtifact",
            status_code=422,
        )
    if source_domain == "worldbuilding" and resolved_session is not None:
        raise GraphRunRegistryError(
            "worldbuilding extraction runs must not fabricate session_id",
            status_code=422,
        )
    return artifact


def get_extraction_run(root: Path, run_id: str) -> ExtractionRun:
    document = _load(root)
    for record in document.records:
        if record.run_id == run_id:
            return record
    raise GraphRunRegistryError(f"extraction run not found: {run_id}", status_code=404)


def _connected_lineage_records(
    records: list[ExtractionRun], run: ExtractionRun
) -> list[ExtractionRun]:
    """Collect the selected run plus its reciprocal supersession chain."""
    by_id = {record.run_id: record for record in records}
    connected_ids: set[str] = {run.run_id}
    frontier = [run.run_id]
    while frontier:
        current_id = frontier.pop()
        current = by_id.get(current_id)
        if current is None:
            continue
        for linked_id in (current.supersedes_run_id, current.superseded_by_run_id):
            if linked_id and linked_id not in connected_ids:
                connected_ids.add(linked_id)
                frontier.append(linked_id)
    return [by_id[run_id] for run_id in connected_ids if run_id in by_id]


def get_reviewable_extraction_run(root: Path, run_id: str) -> ExtractionRun:
    """Load one REVIEWABLE ExtractionRun and assert its current evidence integrity.

    Unlike ``get_extraction_run()``, this does not re-validate every sibling
    record's evidence bundle — only the selected run — so a damaged sibling
    cannot poison lineage checks for an otherwise healthy REVIEWABLE run.
    SourceArtifact existence, scope, immutable source bytes, SourceSpanIndex
    binding, and candidate digests are still enforced via
    ``assert_run_reviewable_evidence``.

    Registry-document invariants that still apply:
    - every ``run_id`` must be unique
    - the selected run's connected supersession lineage must be valid
    """
    path = extraction_runs_path(root)
    if not path.is_file():
        raise GraphRunRegistryError(f"extraction run not found: {run_id}", status_code=404)
    try:
        document = ExtractionRunRegistryDocument.model_validate(load_json(path))
    except (ValidationError, TypeError, ValueError) as exc:
        raise GraphRunRegistryError(
            f"malformed extraction run registry: {exc}",
            status_code=500,
        ) from exc

    seen: set[str] = set()
    matches: list[ExtractionRun] = []
    for record in document.records:
        if record.run_id in seen:
            raise GraphRunRegistryError(
                f"duplicate extraction run id: {record.run_id}",
                status_code=500,
            )
        seen.add(record.run_id)
        if record.run_id == run_id:
            matches.append(record)
    if not matches:
        raise GraphRunRegistryError(f"extraction run not found: {run_id}", status_code=404)
    if len(matches) != 1:
        raise GraphRunRegistryError(
            f"duplicate extraction run id: {run_id}",
            status_code=500,
        )
    run = matches[0]
    try:
        validate_extraction_run_record(run)
    except ValueError as exc:
        raise GraphRunRegistryError(
            f"malformed extraction run registry record: {exc}",
            status_code=500,
        ) from exc
    try:
        validate_extraction_run_lineage(_connected_lineage_records(document.records, run))
    except ValueError as exc:
        raise GraphRunRegistryError(
            f"malformed extraction run lineage: {exc}",
            status_code=500,
        ) from exc
    if run.status != ExtractionRunStatus.REVIEWABLE:
        raise GraphRunRegistryError(
            f"extraction run is not reviewable: {run.status.value}",
            status_code=422,
        )
    assert_run_reviewable_evidence(root, run)
    return run


def create_extraction_run(
    root: Path,
    *,
    source_artifact_id: str,
    source_domain: str,
    campaign_id: str | None = None,
    session_id: str | None = None,
    profile_id: str | None = None,
    components: dict[str, ExtractionRunComponentRef] | None = None,
    status: ExtractionRunStatus = ExtractionRunStatus.DRAFT,
    diagnostics: ExtractionRunDiagnostics | None = None,
    lineage: dict[str, Any] | None = None,
) -> ExtractionRun:
    artifact = _bind_run_to_artifact(
        root,
        source_artifact_id=source_artifact_id,
        source_domain=source_domain,
        campaign_id=campaign_id,
        session_id=session_id,
    )
    if status in TERMINAL_EXTRACTION_RUN_STATUSES:
        raise GraphRunRegistryError(
            "cannot create an extraction run directly in a terminal status",
            status_code=422,
        )

    now = _utc_now_iso()
    run = ExtractionRun(
        run_id=str(uuid4()),
        source_artifact_id=artifact.source_artifact_id,
        source_domain=str(artifact.source_domain),
        status=status,
        revision=1,
        campaign_id=artifact.campaign_id,
        session_id=artifact.session_id,
        profile_id=profile_id,
        created_at=now,
        updated_at=now,
        components=components or {},
        diagnostics=diagnostics or ExtractionRunDiagnostics(),
        lineage=dict(lineage or {}),
    )
    if status == ExtractionRunStatus.REVIEWABLE:
        assert_run_reviewable_evidence(root, run)

    path = extraction_runs_path(root)
    with registry_mutation_lock(path):
        document, token = _load_unlocked(root)
        document.records.append(run)
        _save_cas(root, document, expected_token=token)
    return run


def update_extraction_run_status(
    root: Path,
    run_id: str,
    *,
    status: ExtractionRunStatus,
    expected_revision: int,
    components: dict[str, ExtractionRunComponentRef] | None = None,
    diagnostics: ExtractionRunDiagnostics | None = None,
    lineage: dict[str, Any] | None = None,
) -> ExtractionRun:
    path = extraction_runs_path(root)
    with registry_mutation_lock(path):
        document, token = _load_unlocked(root)
        existing = next((row for row in document.records if row.run_id == run_id), None)
        if existing is None:
            raise GraphRunRegistryError(f"extraction run not found: {run_id}", status_code=404)
        if existing.revision != expected_revision:
            raise GraphRunRegistryError(
                f"revision mismatch: expected {expected_revision}, current {existing.revision}",
                status_code=409,
            )
        if existing.status in TERMINAL_EXTRACTION_RUN_STATUSES:
            raise GraphRunRegistryError(
                f"extraction run status {existing.status.value} is terminal",
                status_code=409,
            )
        try:
            assert_allowed_extraction_run_transition(existing.status, status)
        except ValueError as exc:
            raise GraphRunRegistryError(str(exc), status_code=422) from exc

        if components is not None and existing.status in FROZEN_COMPONENT_STATUSES:
            raise GraphRunRegistryError(
                "cannot replace components for a frozen extraction run",
                status_code=409,
            )

        next_components = existing.components if components is None else components
        next_diagnostics = existing.diagnostics if diagnostics is None else diagnostics
        next_lineage = existing.lineage if lineage is None else dict(lineage)
        updated = existing.model_copy(
            update={
                "status": status,
                "revision": existing.revision + 1,
                "updated_at": _utc_now_iso(),
                "components": next_components,
                "diagnostics": next_diagnostics,
                "lineage": next_lineage,
            }
        )
        if status in _REVIEW_BUNDLE_STATUSES:
            assert_run_reviewable_evidence(root, updated)
        elif status in TERMINAL_EXTRACTION_RUN_STATUSES:
            assert_immutable_component_refs(root, updated)

        document.records = [
            updated if row.run_id == run_id else row for row in document.records
        ]
        _save_cas(root, document, expected_token=token)
        return updated


def supersede_extraction_run(
    root: Path,
    run_id: str,
    *,
    expected_revision: int,
    profile_id: str | None = None,
    components: dict[str, ExtractionRunComponentRef] | None = None,
    status: ExtractionRunStatus = ExtractionRunStatus.DRAFT,
) -> ExtractionRun:
    """Mark an exact run superseded and create a successor in one registry write."""
    if status in TERMINAL_EXTRACTION_RUN_STATUSES:
        raise GraphRunRegistryError(
            "cannot create an extraction run directly in a terminal status",
            status_code=422,
        )

    path = extraction_runs_path(root)
    with registry_mutation_lock(path):
        document, token = _load_unlocked(root)
        existing = next((row for row in document.records if row.run_id == run_id), None)
        if existing is None:
            raise GraphRunRegistryError(f"extraction run not found: {run_id}", status_code=404)
        if existing.revision != expected_revision:
            raise GraphRunRegistryError(
                f"revision mismatch: expected {expected_revision}, current {existing.revision}",
                status_code=409,
            )
        if existing.status == ExtractionRunStatus.SUPERSEDED:
            raise GraphRunRegistryError("extraction run is already superseded", status_code=409)

        now = _utc_now_iso()
        successor_id = str(uuid4())
        successor = ExtractionRun(
            run_id=successor_id,
            source_artifact_id=existing.source_artifact_id,
            source_domain=existing.source_domain,
            status=status,
            revision=1,
            campaign_id=existing.campaign_id,
            session_id=existing.session_id,
            profile_id=profile_id if profile_id is not None else existing.profile_id,
            created_at=now,
            updated_at=now,
            components=components if components is not None else dict(existing.components),
            supersedes_run_id=existing.run_id,
        )
        if status == ExtractionRunStatus.REVIEWABLE:
            assert_run_reviewable_evidence(root, successor)

        predecessor = existing.model_copy(
            update={
                "status": ExtractionRunStatus.SUPERSEDED,
                "revision": existing.revision + 1,
                "updated_at": now,
                "superseded_by_run_id": successor_id,
            }
        )
        if predecessor.superseded_by_run_id != successor.run_id:
            raise GraphRunRegistryError("supersession lineage is not reciprocal", status_code=500)
        if successor.supersedes_run_id != predecessor.run_id:
            raise GraphRunRegistryError("supersession lineage is not reciprocal", status_code=500)

        document.records = [
            predecessor if row.run_id == run_id else row for row in document.records
        ]
        document.records.append(successor)
        _save_cas(root, document, expected_token=token)
        return successor
