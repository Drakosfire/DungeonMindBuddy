"""Mounted ExtractionRun facade over APP-STATE PostgreSQL.

Canonical run identity/lifecycle lives in ``ingest.run``. This module keeps the
existing function names and evidence-resolution checks so extraction/review
callers do not learn SQL. There is no file-registry fallback or dual write.
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, NoReturn
from uuid import uuid4

from application_state.errors import ApplicationStateError
from application_state.ingest import service as ingest_service
from application_state.source import service as source_service
from apps.live_control_server.services.source_artifact_registry import (
    SourceArtifactRegistryError,
    get_source_artifact,
    load_registered_source_artifact_text,
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
)
from graph_memory.source_span import validate_source_span_index
from src.live_play.live_store import load_json

if TYPE_CHECKING:
    from apps.live_control_server.models.historical_recap_inspection import (
        HistoricalRecapInspectionResponse,
    )

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


def _utc_now_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _raise_registry(exc: ApplicationStateError) -> NoReturn:
    raise GraphRunRegistryError(str(exc), status_code=exc.status_code) from exc


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
    from graph_memory.ingestion.extraction_run import normalize_content_digest

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
    from graph_memory.ingestion.extraction_run import normalize_content_digest

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


def _persist_recap_source_authority(
    root: Path,
    artifact: GraphMemorySourceArtifact,
) -> None:
    """Adopt new recap input before its ExtractionRun becomes canonical."""
    if str(artifact.source_domain) != "recap":
        return
    try:
        _registered_artifact, markdown = load_registered_source_artifact_text(
            root,
            artifact.source_artifact_id,
        )
        source_service.persist_source_markdown(
            source_artifact_id=artifact.source_artifact_id,
            source_domain=str(artifact.source_domain),
            campaign_id=artifact.campaign_id,
            session_id=artifact.session_id,
            world_id=artifact.world_id,
            markdown=markdown,
            content_sha256=artifact.content_sha256,
            lineage={"adopted_from_uri": artifact.uri},
        )
    except (SourceArtifactRegistryError, ApplicationStateError) as exc:
        raise GraphRunRegistryError(
            f"durable recap source persistence failed: {exc}",
            status_code=getattr(exc, "status_code", 409),
        ) from exc


def get_extraction_run(root: Path, run_id: str) -> ExtractionRun:
    del root
    try:
        return ingest_service.get_extraction_run(run_id)
    except ApplicationStateError as exc:
        _raise_registry(exc)
        raise


def get_historical_recap_inspection(
    root: Path, run_id: str
) -> "HistoricalRecapInspectionResponse":
    """Read-only exact-run recap source inspection from APP-STATE."""
    from apps.live_control_server.models.historical_recap_inspection import (
        HistoricalRecapInspectionResponse,
    )
    from graph_memory.ingestion.extraction_run import normalize_content_digest

    run = get_extraction_run(root, run_id)
    if run.source_domain != "recap":
        raise GraphRunRegistryError(
            "historical recap inspection is not applicable to this extraction run",
            status_code=422,
        )

    def _digest_label(digest: str) -> str:
        normalized = normalize_content_digest(digest)
        return normalized if normalized.startswith("sha256:") else f"sha256:{normalized}"

    def _unavailable(*, source_sha256: str | None = None, reason: str):
        return HistoricalRecapInspectionResponse(
            run_id=run.run_id,
            run_status=run.status.value,
            source_domain=run.source_domain,
            source_artifact_id=run.source_artifact_id,
            campaign_id=run.campaign_id,
            session_id=run.session_id,
            source_status="unavailable",
            source_uri=None,
            source_sha256=source_sha256,
            source_prose=None,
            unavailable_reason=reason,
        )

    source_component = _component_by_kind(
        run.components, ExtractionRunComponentKind.SOURCE_ARTIFACT
    )
    if source_component is None:
        return _unavailable(reason="source_artifact component is not recorded on this run")

    claimed_digest = normalize_content_digest(source_component.sha256)
    if not claimed_digest:
        return _unavailable(
            reason="source_artifact component digest is not recorded",
        )

    try:
        source = source_service.get_source_markdown(
            source_artifact_id=run.source_artifact_id,
            content_sha256=claimed_digest,
        )
    except ApplicationStateError as exc:
        return _unavailable(
            source_sha256=_digest_label(claimed_digest),
            reason=f"durable source authority is unavailable: {exc}",
        )
    if source is None:
        return _unavailable(
            source_sha256=_digest_label(claimed_digest),
            reason="exact historical source is not adopted into APP-STATE",
        )
    if (
        source.source_domain != run.source_domain
        or source.campaign_id != run.campaign_id
        or source.session_id != run.session_id
    ):
        raise GraphRunRegistryError(
            "durable source identity does not match the exact ExtractionRun",
            status_code=422,
        )

    return HistoricalRecapInspectionResponse(
        run_id=run.run_id,
        run_status=run.status.value,
        source_domain=run.source_domain,
        source_artifact_id=run.source_artifact_id,
        campaign_id=run.campaign_id,
        session_id=run.session_id,
        source_status="available",
        source_uri=None,
        source_sha256=_digest_label(source.content_sha256),
        source_prose=source.markdown,
        unavailable_reason=None,
    )


def get_reviewable_extraction_run(root: Path, run_id: str) -> ExtractionRun:
    """Load one REVIEWABLE ExtractionRun and assert its current evidence integrity.

    Catalog identity comes from APP-STATE. Missing component bytes fail here,
    not by pretending the run is absent.
    """
    try:
        run = ingest_service.get_extraction_run(run_id)
    except ApplicationStateError as exc:
        _raise_registry(exc)
        raise
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
    _persist_recap_source_authority(root, artifact)

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
    try:
        return ingest_service.create_extraction_run(run)
    except ApplicationStateError as exc:
        _raise_registry(exc)
        raise


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
    try:
        existing = ingest_service.get_extraction_run(run_id)
    except ApplicationStateError as exc:
        _raise_registry(exc)
    if components is not None and existing.status in FROZEN_COMPONENT_STATUSES:
        raise GraphRunRegistryError(
            "cannot replace components for a frozen extraction run",
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
    next_components = existing.components if components is None else components
    next_diagnostics = existing.diagnostics if diagnostics is None else diagnostics
    next_lineage = existing.lineage if lineage is None else dict(lineage)
    proposed = existing.model_copy(
        update={
            "status": status,
            "revision": existing.revision + 1,
            "components": next_components,
            "diagnostics": next_diagnostics,
            "lineage": next_lineage,
        }
    )
    if status in _REVIEW_BUNDLE_STATUSES:
        assert_run_reviewable_evidence(root, proposed)
    elif status in TERMINAL_EXTRACTION_RUN_STATUSES:
        assert_immutable_component_refs(root, proposed)
    try:
        return ingest_service.update_extraction_run(
            run_id,
            status=status,
            expected_revision=expected_revision,
            components=components,
            diagnostics=diagnostics,
            lineage=lineage,
        )
    except ApplicationStateError as exc:
        _raise_registry(exc)
        raise


def supersede_extraction_run(
    root: Path,
    run_id: str,
    *,
    expected_revision: int,
    profile_id: str | None = None,
    components: dict[str, ExtractionRunComponentRef] | None = None,
    status: ExtractionRunStatus = ExtractionRunStatus.DRAFT,
) -> ExtractionRun:
    """Mark an exact run superseded and create a successor in one transaction."""
    if status in TERMINAL_EXTRACTION_RUN_STATUSES:
        raise GraphRunRegistryError(
            "cannot create an extraction run directly in a terminal status",
            status_code=422,
        )
    try:
        existing = ingest_service.get_extraction_run(run_id)
    except ApplicationStateError as exc:
        _raise_registry(exc)
        raise
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
    try:
        return ingest_service.supersede_extraction_run(
            run_id,
            expected_revision=expected_revision,
            successor=successor,
        )
    except ApplicationStateError as exc:
        _raise_registry(exc)
        raise
