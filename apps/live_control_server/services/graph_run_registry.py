"""Canonical exact ExtractionRun registry."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from pydantic import BaseModel, Field

from src.live_play.live_store import load_json, write_json
from graph_memory.ingestion.extraction_run import (
    ExtractionRun,
    ExtractionRunComponentRef,
    ExtractionRunStatus,
    assert_run_not_reviewable_when_incomplete,
)

DEFAULT_EXTRACTION_RUN_REGISTRY_REL = "out/registries/extraction_runs.json"
EXTRACTION_RUN_REGISTRY_SCHEMA = "dmb_extraction_run_registry_v1"


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


def _load(root: Path) -> ExtractionRunRegistryDocument:
    path = extraction_runs_path(root)
    if not path.is_file():
        return ExtractionRunRegistryDocument()
    return ExtractionRunRegistryDocument.model_validate(load_json(path))


def _save(root: Path, document: ExtractionRunRegistryDocument) -> None:
    path = extraction_runs_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    write_json(path, document.model_dump(mode="json"))


def get_extraction_run(root: Path, run_id: str) -> ExtractionRun:
    document = _load(root)
    for record in document.records:
        if record.run_id == run_id:
            return record
    raise GraphRunRegistryError(f"extraction run not found: {run_id}", status_code=404)


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
) -> ExtractionRun:
    if not source_artifact_id.strip():
        raise GraphRunRegistryError("source_artifact_id is required", status_code=422)
    if source_domain == "worldbuilding" and session_id is not None:
        raise GraphRunRegistryError(
            "worldbuilding extraction runs must not fabricate session_id",
            status_code=422,
        )

    now = _utc_now_iso()
    run = ExtractionRun(
        run_id=str(uuid4()),
        source_artifact_id=source_artifact_id,
        source_domain=source_domain,
        status=status,
        campaign_id=campaign_id,
        session_id=session_id,
        profile_id=profile_id,
        created_at=now,
        updated_at=now,
        components=components or {},
    )
    try:
        assert_run_not_reviewable_when_incomplete(run)
    except ValueError as exc:
        raise GraphRunRegistryError(str(exc), status_code=422) from exc

    document = _load(root)
    document.records.append(run)
    _save(root, document)
    return run


def update_extraction_run_status(
    root: Path,
    run_id: str,
    *,
    status: ExtractionRunStatus,
    components: dict[str, ExtractionRunComponentRef] | None = None,
) -> ExtractionRun:
    document = _load(root)
    existing = next((row for row in document.records if row.run_id == run_id), None)
    if existing is None:
        raise GraphRunRegistryError(f"extraction run not found: {run_id}", status_code=404)

    updated = existing.model_copy(
        update={
            "status": status,
            "updated_at": _utc_now_iso(),
            **({"components": components} if components is not None else {}),
        }
    )
    try:
        assert_run_not_reviewable_when_incomplete(updated)
    except ValueError as exc:
        raise GraphRunRegistryError(str(exc), status_code=422) from exc

    document.records = [
        updated if row.run_id == run_id else row for row in document.records
    ]
    _save(root, document)
    return updated
