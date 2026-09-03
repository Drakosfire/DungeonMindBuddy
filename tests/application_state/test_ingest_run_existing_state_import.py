from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

import pytest

from application_state.errors import (
    ApplicationStateConflictError,
    ApplicationStateIntegrityError,
)
from application_state.ingest.import_legacy import (
    LEGACY_EXTRACTION_RUN_REGISTRY_REL,
    ExtractionRunRegistryDocument,
    import_extraction_runs_from_registry,
)
from application_state.ingest.service import get_extraction_run, list_extraction_runs
from graph_memory.ingestion.extraction_run import ExtractionRun, ExtractionRunStatus


def _run(*, run_id: str | None = None, **overrides) -> ExtractionRun:
    now = "2026-09-02T18:00:00Z"
    payload = {
        "run_id": run_id or f"er_{uuid4().hex[:12]}",
        "source_artifact_id": "sa_world_1",
        "source_domain": "worldbuilding",
        "status": ExtractionRunStatus.DRAFT,
        "revision": 3,
        "campaign_id": "eldyrwild",
        "session_id": None,
        "created_at": now,
        "updated_at": now,
        "profile_id": "worldbuilding_plumbing_v0@0.1",
    }
    payload.update(overrides)
    return ExtractionRun.model_validate(payload)


def _write_registry(root: Path, records: list[ExtractionRun]) -> Path:
    path = root / LEGACY_EXTRACTION_RUN_REGISTRY_REL
    path.parent.mkdir(parents=True, exist_ok=True)
    document = ExtractionRunRegistryDocument(records=records)
    path.write_text(
        json.dumps(document.model_dump(mode="json"), indent=2) + "\n",
        encoding="utf-8",
    )
    return path


def test_import_inserts_then_replays_as_noop(
    tmp_path: Path, application_state_dsn: str
) -> None:
    run = _run(run_id="er_import_exact")
    _write_registry(tmp_path, [run])
    first = import_extraction_runs_from_registry(tmp_path)
    assert first.source_count == 1
    assert first.imported == 1
    assert first.noop == 0
    loaded = get_extraction_run("er_import_exact")
    assert loaded.revision == 3
    assert loaded.profile_id == "worldbuilding_plumbing_v0@0.1"
    replay = import_extraction_runs_from_registry(tmp_path)
    assert replay.imported == 0
    assert replay.noop == 1
    assert get_extraction_run("er_import_exact").revision == 3


def test_import_conflict_rolls_back_all_changes(
    tmp_path: Path, application_state_dsn: str
) -> None:
    first = _run(run_id="er_keep")
    second = _run(run_id="er_conflict", revision=2)
    _write_registry(tmp_path, [first])
    import_extraction_runs_from_registry(tmp_path)
    conflict_first = first.model_copy(update={"revision": 9})
    _write_registry(tmp_path, [conflict_first, second])
    with pytest.raises(ApplicationStateConflictError, match="different durable fields"):
        import_extraction_runs_from_registry(tmp_path)
    assert [row.run_id for row in list_extraction_runs()] == ["er_keep"]
    assert get_extraction_run("er_keep").revision == 3


def test_import_absent_source_is_empty(
    tmp_path: Path, application_state_dsn: str
) -> None:
    report = import_extraction_runs_from_registry(tmp_path)
    assert report.source_absent is True
    assert report.source_count == 0
    assert report.imported == 0
    assert list_extraction_runs() == []


def test_dry_run_does_not_write(tmp_path: Path, application_state_dsn: str) -> None:
    run = _run(run_id="er_dry")
    _write_registry(tmp_path, [run])
    report = import_extraction_runs_from_registry(tmp_path, dry_run=True)
    assert report.imported == 1
    assert list_extraction_runs() == []


def test_import_rejects_unknown_registry_schema_with_zero_mutation(
    tmp_path: Path, application_state_dsn: str
) -> None:
    run = _run(run_id="er_wrong_schema")
    path = tmp_path / LEGACY_EXTRACTION_RUN_REGISTRY_REL
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": "dmb_extraction_run_registry_v99",
        "records": [run.model_dump(mode="json")],
    }
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    with pytest.raises(ApplicationStateIntegrityError, match="malformed extraction run registry"):
        import_extraction_runs_from_registry(tmp_path)
    assert list_extraction_runs() == []


def test_import_preserves_historical_terminal_status(
    tmp_path: Path, application_state_dsn: str
) -> None:
    run = _run(run_id="er_hist_failed", status=ExtractionRunStatus.FAILED, revision=4)
    _write_registry(tmp_path, [run])
    report = import_extraction_runs_from_registry(tmp_path)
    assert report.imported == 1
    loaded = get_extraction_run("er_hist_failed")
    assert loaded.status == ExtractionRunStatus.FAILED
    assert loaded.revision == 4
