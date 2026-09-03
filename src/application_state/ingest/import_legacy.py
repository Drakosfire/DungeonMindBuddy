"""Explicit, idempotent adoption of file-backed ExtractionRun records."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, ValidationError

from application_state.cli import assert_at_head
from application_state.config import load_runtime_dsn
from application_state.errors import (
    ApplicationStateConflictError,
    ApplicationStateIntegrityError,
)
from application_state.ingest import repository as repo
from application_state.unit_of_work import unit_of_work
from graph_memory.ingestion.extraction_run import (
    ExtractionRun,
    validate_extraction_run_lineage,
)

LEGACY_EXTRACTION_RUN_REGISTRY_REL = "out/registries/extraction_runs.json"
LEGACY_EXTRACTION_RUN_REGISTRY_SCHEMA = "dmb_extraction_run_registry_v1"


class ExtractionRunRegistryDocument(BaseModel):
    schema_version: Literal["dmb_extraction_run_registry_v1"] = (
        LEGACY_EXTRACTION_RUN_REGISTRY_SCHEMA
    )
    records: list[ExtractionRun] = Field(default_factory=list)


class ImportReport(BaseModel):
    source_count: int = 0
    imported: int = 0
    noop: int = 0
    conflict: int = 0
    run_ids: list[str] = Field(default_factory=list)
    source_path: str | None = None
    source_absent: bool = False


def legacy_extraction_runs_path(root: Path) -> Path:
    return root / LEGACY_EXTRACTION_RUN_REGISTRY_REL


def _durable_payload(run: ExtractionRun) -> dict:
    return run.model_dump(mode="json")


def _load_legacy_document(path: Path) -> ExtractionRunRegistryDocument:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ApplicationStateIntegrityError(
            f"malformed extraction run registry: {exc}"
        ) from exc
    try:
        document = ExtractionRunRegistryDocument.model_validate(raw)
    except (ValidationError, TypeError, ValueError) as exc:
        raise ApplicationStateIntegrityError(
            f"malformed extraction run registry: {exc}"
        ) from exc
    try:
        validate_extraction_run_lineage(document.records)
    except ValueError as exc:
        raise ApplicationStateIntegrityError(
            f"malformed extraction run lineage: {exc}"
        ) from exc
    return document


def import_extraction_runs_from_registry(
    root: Path,
    *,
    dry_run: bool = False,
) -> ImportReport:
    """Import canonical file-backed ExtractionRun records into APP-STATE.

    Validates the whole source document before mutation. One transaction.
    Absent destination row inserts; field-equivalent row no-ops; same ID with
    differing durable fields conflicts and rolls back. Source file is not deleted.
    """
    dsn = load_runtime_dsn()
    assert_at_head(dsn=dsn)
    path = legacy_extraction_runs_path(root)
    report = ImportReport(source_path=str(path))
    if not path.is_file():
        report.source_absent = True
        return report
    document = _load_legacy_document(path)
    report.source_count = len(document.records)
    report.run_ids = [run.run_id for run in document.records]
    if dry_run:
        dsn_check = load_runtime_dsn()
        with unit_of_work(dsn_check) as conn:
            for run in document.records:
                existing = repo.get_run(conn, run.run_id)
                if existing is None:
                    report.imported += 1
                elif _durable_payload(existing) == _durable_payload(run):
                    report.noop += 1
                else:
                    report.conflict += 1
                    raise ApplicationStateConflictError(
                        f"extraction run {run.run_id} already exists with different durable fields"
                    )
        return report

    with unit_of_work(dsn) as conn:
        for run in document.records:
            existing = repo.get_run(conn, run.run_id)
            if existing is None:
                repo.insert_run(conn, run)
                report.imported += 1
                continue
            if _durable_payload(existing) == _durable_payload(run):
                report.noop += 1
                continue
            report.conflict += 1
            raise ApplicationStateConflictError(
                f"extraction run {run.run_id} already exists with different durable fields"
            )
        try:
            validate_extraction_run_lineage(repo.list_runs(conn))
        except ValueError as exc:
            raise ApplicationStateIntegrityError(
                f"malformed extraction run lineage: {exc}"
            ) from exc
    return report


def read_legacy_extraction_runs(root: Path) -> list[ExtractionRun]:
    """Migration-only reader. Not a production fallback."""
    path = legacy_extraction_runs_path(root)
    if not path.is_file():
        return []
    return list(_load_legacy_document(path).records)
