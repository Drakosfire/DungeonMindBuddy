"""Canonical APP-STATE ExtractionRun catalog adapter.

This is a presentation adapter over ``list_extraction_runs()``. It does not
consult the legacy GraphIngest file registry and does not invent collection
revisions or manifest identity.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from application_state.errors import (
    ApplicationStateError,
    ApplicationStateIntegrityError,
    ApplicationStateMigrationError,
    ApplicationStateUnavailableError,
)
from application_state.ingest.service import list_extraction_runs
from apps.live_control_server.services import graph_run_registry as runs
from apps.live_control_server.services.source_artifact_registry import (
    SourceArtifactRegistryError,
    get_source_artifact,
)
from graph_memory.ingestion.extraction_run import (
    ExtractionRun,
    ExtractionRunStatus,
    normalize_content_digest,
)
from src.graph_memory.candidate_document_integrity import (
    classify_candidate_document_integrity,
)

CODE_UNAVAILABLE = "ingest_run_catalog_unavailable"
CODE_SCHEMA_UNAVAILABLE = "ingest_run_catalog_schema_unavailable"
CODE_INTEGRITY = "ingest_run_catalog_integrity_error"
CODE_ERROR = "ingest_run_catalog_error"


class IngestRunCatalogError(Exception):
    def __init__(self, message: str, *, code: str, status_code: int) -> None:
        super().__init__(message)
        self.code = code
        self.status_code = status_code


def _catalog_records(**filters: str | None) -> list[ExtractionRun]:
    try:
        records = list_extraction_runs(**filters)
    except ApplicationStateUnavailableError as exc:
        raise IngestRunCatalogError(
            "The extraction database is unavailable.",
            code=CODE_UNAVAILABLE,
            status_code=exc.status_code,
        ) from exc
    except ApplicationStateMigrationError as exc:
        raise IngestRunCatalogError(
            "The extraction database schema is unavailable.",
            code=CODE_SCHEMA_UNAVAILABLE,
            status_code=exc.status_code,
        ) from exc
    except ApplicationStateIntegrityError as exc:
        raise IngestRunCatalogError(
            "The saved extraction catalog failed integrity checks.",
            code=CODE_INTEGRITY,
            status_code=exc.status_code,
        ) from exc
    except ApplicationStateError as exc:
        raise IngestRunCatalogError(
            "The extraction catalog could not be read.",
            code=CODE_ERROR,
            status_code=exc.status_code,
        ) from exc

    return records


def _source_key(run: ExtractionRun) -> tuple[str, str] | None:
    components = [
        component
        for component in run.components.values()
        if component.kind.value == "source_artifact"
    ]
    if len(components) != 1 or not components[0].sha256:
        return None
    digest = normalize_content_digest(components[0].sha256).removeprefix("sha256:")
    if len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
        return None
    return run.source_artifact_id, digest


def _saved_rows(records: list[ExtractionRun], native_world_id: str):
    from application_state.source import service as sources
    from apps.live_control_server.models.saved_recap_runs import SavedRecapRun

    keys = {key for run in records if (key := _source_key(run)) is not None}
    metadata = {
        (row.source_artifact_id, row.content_sha256): row
        for row in sources.get_source_revision_metadata(
            bindings=list(keys), world_id=native_world_id
        )
    }
    rows = []
    for run in records:
        source = metadata.get(_source_key(run))
        reason = None
        if _source_key(run) is None:
            reason = "This run has no frozen source revision component."
        elif source is None:
            reason = "The exact saved source revision is unavailable."
        elif (
            source.source_domain != "recap"
            or source.campaign_id != run.campaign_id
            or source.session_id != run.session_id
            or source.media_type != "text/markdown"
            or source.encoding != "utf-8"
        ):
            raise IngestRunCatalogError(
                "Saved run and source scope disagree.",
                code=CODE_INTEGRITY,
                status_code=409,
            )
        rows.append(
            SavedRecapRun(
                run_id=run.run_id,
                run_revision=run.revision,
                run_status=run.status.value,
                source_artifact_id=run.source_artifact_id,
                campaign_id=run.campaign_id,
                session_id=run.session_id,
                profile_id=run.profile_id,
                created_at=run.created_at,
                updated_at=run.updated_at,
                source_revision_id=source.source_revision_id if source else None,
                source_sha256=source.content_sha256 if source else None,
                unavailable_reason=reason,
            )
        )
    return rows


def _stable_scope(root: Path, managed_world_id: str):
    from apps.live_control_server.services.managed_world_graph_projection import (
        resolve_managed_source_identity,
    )

    return resolve_managed_source_identity(managed_world_id, root=root)


def _require_scope_unchanged(root: Path, scope) -> None:
    if _stable_scope(root, scope.managed_world_id) != scope:
        raise IngestRunCatalogError(
            "Selected World source binding changed.",
            code=CODE_INTEGRITY,
            status_code=409,
        )


def list_saved_recap_runs(
    *, root: Path, managed_world_id: str, campaign_id: str | None
):
    """Previous extraction work, not a complete source catalogue. No body reads."""
    from apps.live_control_server.models.saved_recap_runs import SavedRecapRunsResponse

    scope = _stable_scope(root, managed_world_id)
    records = _catalog_records(
        world_id=scope.native_world_id, source_domain="recap", campaign_id=campaign_id
    )
    rows = _saved_rows(records, scope.native_world_id)
    _require_scope_unchanged(root, scope)
    return SavedRecapRunsResponse(
        managed_world_id=scope.managed_world_id,
        native_world_id=scope.native_world_id,
        binding_version=scope.binding_version,
        runs=rows,
    )


def read_saved_recap_source(
    *,
    root: Path,
    managed_world_id: str,
    run_id: str,
    expected_run_revision: int,
    source_revision_id,
):
    """Open the exact selected APP revision after World and run checks; never a file."""
    import hashlib
    from application_state.ingest import service as ingest
    from application_state.source import service as sources
    from apps.live_control_server.models.saved_recap_runs import (
        SavedRecapSourceResponse,
    )

    scope = _stable_scope(root, managed_world_id)
    run = ingest.get_extraction_run(run_id, world_id=scope.native_world_id)
    if run.source_domain != "recap":
        raise IngestRunCatalogError(
            "Saved source inspection requires a Recap run.",
            code=CODE_INTEGRITY,
            status_code=422,
        )
    if run.revision != expected_run_revision:
        raise IngestRunCatalogError(
            "Selected extraction run changed; reload its metadata.",
            code=CODE_INTEGRITY,
            status_code=409,
        )
    row = _saved_rows([run], scope.native_world_id)[0]
    if row.unavailable_reason:
        raise IngestRunCatalogError(
            row.unavailable_reason, code=CODE_INTEGRITY, status_code=409
        )
    if row.source_revision_id != source_revision_id:
        raise IngestRunCatalogError(
            "Selected source revision does not belong to this run.",
            code=CODE_INTEGRITY,
            status_code=409,
        )
    _require_scope_unchanged(root, scope)
    source = sources.get_source_markdown(
        source_artifact_id=row.source_artifact_id,
        content_sha256=row.source_sha256,
        source_revision_id=source_revision_id,
        world_id=scope.native_world_id,
    )
    if (
        source is None
        or (
            source.world_id,
            source.source_domain,
            source.campaign_id,
            source.session_id,
        )
        != (scope.native_world_id, "recap", run.campaign_id, run.session_id)
        or hashlib.sha256(source.markdown.encode("utf-8")).hexdigest()
        != row.source_sha256
    ):
        raise IngestRunCatalogError(
            "Exact saved source failed integrity checks.",
            code=CODE_INTEGRITY,
            status_code=409,
        )
    # A response must not silently describe an attempt that changed during reading.
    if (
        ingest.get_extraction_run(run_id, world_id=scope.native_world_id).revision
        != expected_run_revision
    ):
        raise IngestRunCatalogError(
            "Selected extraction run changed during reading.",
            code=CODE_INTEGRITY,
            status_code=409,
        )
    _require_scope_unchanged(root, scope)
    return SavedRecapSourceResponse(
        managed_world_id=scope.managed_world_id,
        native_world_id=scope.native_world_id,
        binding_version=scope.binding_version,
        run=row,
        source_prose=source.markdown,
    )


def _same_recap_ingest_context_authority(
    extracted: Any, current: Mapping[str, Any]
) -> bool:
    """A recap extraction depends on its source, not the Graph head it observed."""
    if not isinstance(extracted, Mapping):
        return False
    try:
        prior = runs.read_recap_source_scope(dict(extracted), campaign_id=current.get("campaign_id"))
        selected = {key: current.get(key) for key in ("managed_world_id", "native_world_id", "binding_version", "campaign_id")}
        return prior.model_dump() == runs.read_recap_source_scope(selected, campaign_id=current.get("campaign_id")).model_dump()
    except runs.GraphRunRegistryError:
        return False



def _scoped_recap_runs(
    campaign_id: str, session_id: str, context: Mapping[str, Any]
) -> list[ExtractionRun]:
    records = [
        run
        for run in _catalog_records(campaign_id=campaign_id, session_id=session_id)
        if run.source_domain == "recap"
        and _same_recap_ingest_context_authority(
            run.lineage.get("world_campaign_ingest_context"), context
        )
    ]
    # Latest selects an attempt, never authority. Do not revive an older success
    # around a failed, corrupt or differently configured newest source match.
    return sorted(
        records, key=lambda run: (run.created_at or "", run.run_id), reverse=True
    )


def project_recap_extraction_run(
    *,
    root: Path,
    run: ExtractionRun,
    context: Mapping[str, Any],
    source_content_sha256: str | None,
) -> dict[str, Any] | None:
    """Project exact saved source/components through their existing owners.

    This is presentation, not admission or publication authority. Operational
    copies and legacy manifests cannot substitute for missing database evidence.
    """
    try:
        if source_content_sha256:
            # Select by the immutable source owner's descriptor before opening
            # output bytes from any run. Unselected outputs grant no authority
            # and cannot block the requested source; matching bytes are still
            # fully verified below by the existing source/component owner.
            source = get_source_artifact(root, run.source_artifact_id)
            if normalize_content_digest(
                source.content_sha256
            ) != normalize_content_digest(source_content_sha256):
                return None
        data = None
        if run.status == ExtractionRunStatus.REVIEWABLE:
            data = runs.load_reviewable_extraction_data(root, run.run_id)
            run = data.run
            artifact = data.source_artifact
        else:
            artifact, _ = runs.load_run_source_input(root, run)
        if (
            not _same_recap_ingest_context_authority(
                run.lineage.get("world_campaign_ingest_context"), context
            )
            or artifact.world_id != context["native_world_id"]
        ):
            raise runs.GraphRunRegistryError(
                "Saved extraction scope changed", status_code=409
            )
        if source_content_sha256 and normalize_content_digest(
            artifact.content_sha256
        ) != normalize_content_digest(source_content_sha256):
            return None
        result = {
            "status": run.status.value,
            "extraction_run_id": run.run_id,
            "extraction_run_status": run.status.value,
            "source_artifact_id": artifact.source_artifact_id,
            "model_id": run.lineage.get("model_id"),
            "source_match_mode": "content_digest"
            if source_content_sha256
            else "retained_database",
            "next_actions": [],
            "blocked_reason": None,
        }
        if data is not None:
            candidate = json.loads(data.candidate_bytes)
            if not isinstance(candidate, dict):
                raise ValueError("Candidate must be an object")
            classification = classify_candidate_document_integrity(candidate)
            if (
                classification.is_document_integrity_failure
                or classification.preview is None
            ):
                raise ValueError("Saved candidate failed document integrity")
            preview = classification.preview
            result.update(
                {
                    "status": "candidate_validation_ready",
                    "extraction_mode": "category_decomposed",
                    "node_count": len(preview.nodes),
                    "edge_count": len(preview.edges),
                    "candidate_node_count": len(preview.nodes),
                    "candidate_edge_count": len(preview.edges),
                    "candidate_beat_count": len(preview.beats),
                    "evidence_ref_count": sum(
                        len(row.evidence_refs)
                        for row in (
                            *preview.nodes,
                            *preview.edges,
                            *preview.beats,
                            *preview.source_observations,
                        )
                    ),
                    "next_actions": ["review_candidate"],
                }
            )
        elif run.status in {ExtractionRunStatus.FAILED, ExtractionRunStatus.INCOMPLETE}:
            result.update(
                {
                    "status": "failed",
                    "extraction_mode": "llm_blocked",
                    "blocked_reason": "The saved extraction did not complete. Review the attempt before retrying.",
                    "next_actions": ["force_graph_run"],
                }
            )
        return result
    except (
        runs.GraphRunRegistryError,
        SourceArtifactRegistryError,
        ValueError,
        TypeError,
        KeyError,
    ) as exc:
        raise IngestRunCatalogError(
            "Saved extraction evidence is unavailable or failed integrity checks.",
            code=CODE_INTEGRITY,
            status_code=getattr(exc, "status_code", 409),
        ) from exc


def inspect_recap_extraction_status(
    *,
    root: Path,
    campaign_id: str,
    session_id: str,
    context: Mapping[str, Any],
    source_content_sha256: str | None,
) -> dict[str, Any] | None:
    for run in _scoped_recap_runs(campaign_id, session_id, context):
        status = project_recap_extraction_run(
            root=root,
            run=run,
            context=context,
            source_content_sha256=source_content_sha256,
        )
        if status is not None:
            return status
    return None


def _same_session_evidence(run: ExtractionRun, supplemental_evidence: dict | None) -> bool:
    """Reopen the selected immutable Play revisions; locators confer no authority."""
    from apps.live_control_server.models.session_evidence import SessionEvidenceRef
    from apps.live_control_server.services.session_evidence import resolve_evidence_refs

    stored = run.lineage.get("session_evidence")
    if stored is not None and not isinstance(stored, dict):
        raise IngestRunCatalogError(
            "Saved supplemental evidence has invalid revision pins.",
            code=CODE_INTEGRITY, status_code=409,
        )
    if (stored or {}).get("sha256") != (supplemental_evidence or {}).get("sha256"):
        return False
    if stored is None:
        return True
    try:
        sources = stored["sources"]
        if not isinstance(sources, list):
            raise TypeError("session evidence must be a list")
        pins = [SessionEvidenceRef.model_validate({
            key: item[key] for key in ("run_id", "review_revision", "sha256")
        }).model_dump() for item in sources]
        world_id = run.lineage["world_campaign_ingest_context"]["managed_world_id"]
        bundle = resolve_evidence_refs(world_id, pins)
        exact_sources = [{
            key: item[key] for key in ("run_id", "review_revision", "sha256", "citation_url")
        } for item in bundle["sessions"]]
        if bundle["sha256"] != stored["sha256"] or exact_sources != sources:
            raise ValueError("saved session evidence binding differs")
    except ApplicationStateUnavailableError as exc:
        raise IngestRunCatalogError(
            "The supplemental evidence database is unavailable.",
            code=CODE_UNAVAILABLE, status_code=exc.status_code,
        ) from exc
    except ApplicationStateMigrationError as exc:
        raise IngestRunCatalogError(
            "The supplemental evidence database schema is unavailable.",
            code=CODE_SCHEMA_UNAVAILABLE, status_code=exc.status_code,
        ) from exc
    except (ApplicationStateError, KeyError, ValueError, TypeError) as exc:
        raise IngestRunCatalogError(
            "Saved supplemental evidence is unavailable or failed integrity checks.",
            code=CODE_INTEGRITY, status_code=409,
        ) from exc
    return True


def reusable_recap_extraction(
    *,
    root: Path,
    campaign_id: str,
    session_id: str,
    context: Mapping[str, Any],
    source_content_sha256: str,
    profile_id: str,
    model_id: str,
    supplemental_evidence: dict | None,
) -> dict[str, Any] | None:
    for run in _scoped_recap_runs(campaign_id, session_id, context):
        status = project_recap_extraction_run(
            root=root,
            run=run,
            context=context,
            source_content_sha256=source_content_sha256,
        )
        if status is None:
            continue
        if (
            run.status != ExtractionRunStatus.REVIEWABLE
            or run.profile_id != profile_id
            or run.lineage.get("model_id") != model_id
            or not _same_session_evidence(run, supplemental_evidence)
        ):
            return None
        return status
    return None
