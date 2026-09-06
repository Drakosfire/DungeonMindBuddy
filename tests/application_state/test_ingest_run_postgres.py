from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import psycopg
import pytest

from application_state.cli import _current_and_head
from application_state.errors import (
    ApplicationStateConflictError,
    ApplicationStateIntegrityError,
    ApplicationStateNotFoundError,
    ApplicationStateValidationError,
)
from application_state.ingest.service import (
    create_extraction_run,
    get_extraction_run,
    inspect_ingest_authority,
    list_extraction_runs,
    supersede_extraction_run,
    update_extraction_run,
)
from graph_memory.ingestion.extraction_run import (
    ExtractionRun,
    ExtractionRunComponentKind,
    ExtractionRunComponentRef,
    ExtractionRunStatus,
)


def _run(*, run_id: str | None = None, **overrides) -> ExtractionRun:
    now = "2026-09-02T18:00:00Z"
    payload = {
        "run_id": run_id or f"er_{uuid4().hex[:12]}",
        "source_artifact_id": "sa_world_1",
        "source_domain": "worldbuilding",
        "status": ExtractionRunStatus.DRAFT,
        "revision": 1,
        "campaign_id": "eldyrwild",
        "session_id": None,
        "created_at": now,
        "updated_at": now,
    }
    payload.update(overrides)
    return ExtractionRun.model_validate(payload)


def _review_components() -> dict[str, ExtractionRunComponentRef]:
    return {
        "source_artifact": ExtractionRunComponentRef(
            kind=ExtractionRunComponentKind.SOURCE_ARTIFACT,
            uri="repo://source.md",
            sha256="a" * 64,
        ),
        "source_span_index": ExtractionRunComponentRef(
            kind=ExtractionRunComponentKind.SOURCE_SPAN_INDEX,
            uri="repo://spans.json",
            sha256="b" * 64,
        ),
        "candidate_graph": ExtractionRunComponentRef(
            kind=ExtractionRunComponentKind.CANDIDATE_GRAPH,
            uri="repo://graph.json",
            sha256="c" * 64,
        ),
    }


def _model_valid_terminal_run(status: ExtractionRunStatus) -> ExtractionRun:
    extras: dict = {"status": status}
    if status == ExtractionRunStatus.PROMOTED:
        extras["components"] = _review_components()
    if status == ExtractionRunStatus.SUPERSEDED:
        extras["superseded_by_run_id"] = "er_other"
    return _run(**extras)


def test_alembic_head_is_source_0006(application_state_dsn: str) -> None:
    current, head = _current_and_head(application_state_dsn)
    assert current == head == "20260906_0006"


@pytest.mark.parametrize(
    "status",
    [
        ExtractionRunStatus.PROMOTED,
        ExtractionRunStatus.REJECTED,
        ExtractionRunStatus.FAILED,
        ExtractionRunStatus.SUPERSEDED,
    ],
)
def test_create_rejects_terminal_status(
    application_state_dsn: str, status: ExtractionRunStatus
) -> None:
    with pytest.raises(
        ApplicationStateValidationError,
        match="cannot create an extraction run directly in a terminal status",
    ):
        create_extraction_run(_model_valid_terminal_run(status))
    assert list_extraction_runs() == []


def test_supersede_rejects_terminal_successor(application_state_dsn: str) -> None:
    created = create_extraction_run(_run())
    successor = _run(
        run_id="er_terminal_successor",
        status=ExtractionRunStatus.FAILED,
        supersedes_run_id=created.run_id,
    )
    with pytest.raises(
        ApplicationStateValidationError,
        match="cannot create an extraction run directly in a terminal status",
    ):
        supersede_extraction_run(
            created.run_id,
            expected_revision=created.revision,
            successor=successor,
        )
    loaded = get_extraction_run(created.run_id)
    assert loaded.status == ExtractionRunStatus.DRAFT
    assert loaded.superseded_by_run_id is None
    with pytest.raises(ApplicationStateNotFoundError):
        get_extraction_run("er_terminal_successor")


def test_create_list_get_independent_of_worktree_files(
    tmp_path: Path, application_state_dsn: str
) -> None:
    created = create_extraction_run(_run())
    missing_registry = tmp_path / "out/registries/extraction_runs.json"
    missing_runs = tmp_path / "out/graph_memory/runs"
    assert not missing_registry.exists()
    assert not missing_runs.exists()
    loaded = get_extraction_run(created.run_id)
    assert loaded.run_id == created.run_id
    assert loaded.revision == 1
    listed = list_extraction_runs()
    assert [row.run_id for row in listed] == [created.run_id]


def test_mounted_reads_ignore_conflicting_legacy_file(
    tmp_path: Path, application_state_dsn: str
) -> None:
    created = create_extraction_run(_run(run_id="er_db_truth"))
    path = tmp_path / "out/registries/extraction_runs.json"
    path.parent.mkdir(parents=True)
    path.write_text(
        '{"schema_version":"dmb_extraction_run_registry_v1","records":[{'
        '"schema_version":"dmb_extraction_run_v1","version":"1.0",'
        '"run_id":"er_file_only","source_artifact_id":"sa_world_1",'
        '"source_domain":"worldbuilding","status":"draft","revision":1,'
        '"campaign_id":"eldyrwild","components":{},"diagnostics":{},'
        '"lineage":{}}]}',
        encoding="utf-8",
    )
    from apps.live_control_server.services.graph_run_registry import get_extraction_run as mounted_get

    loaded = mounted_get(tmp_path, created.run_id)
    assert loaded.run_id == "er_db_truth"
    with pytest.raises(Exception, match="not found"):
        mounted_get(tmp_path, "er_file_only")
    assert list_extraction_runs()[0].run_id == "er_db_truth"


def test_create_does_not_write_legacy_registry(
    tmp_path: Path, application_state_dsn: str
) -> None:
    from apps.live_control_server.services.source_artifact_registry import (
        create_source_artifact_from_workspace_document,
    )
    from apps.live_control_server.services.workspace_document_registry import (
        create_workspace_document,
        mark_workspace_document_committed,
    )
    from apps.live_control_server.services.graph_run_registry import create_extraction_run as mounted_create

    record = create_workspace_document(
        tmp_path,
        title="Lore",
        campaign_id="eldyrwild",
        kind="worldbuilding_source",
        source_domain="worldbuilding",
        document_class="lore",
        authority_state="draft",
        visibility_state="internal",
    )
    committed = mark_workspace_document_committed(
        tmp_path, record.document_id, expected_revision=1
    )
    target = tmp_path / committed.target_relpath
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("# Lore\n", encoding="utf-8")
    artifact = create_source_artifact_from_workspace_document(
        tmp_path,
        document_id=committed.document_id,
        expected_revision=committed.revision,
    )
    mounted_create(
        tmp_path,
        source_artifact_id=artifact.source_artifact_id,
        source_domain="worldbuilding",
    )
    assert not (tmp_path / "out/registries/extraction_runs.json").exists()


def test_cas_stale_revision_cannot_overwrite(application_state_dsn: str) -> None:
    created = create_extraction_run(_run())
    first = update_extraction_run(
        created.run_id,
        status=ExtractionRunStatus.PREPARED,
        expected_revision=1,
    )
    assert first.revision == 2
    with pytest.raises(ApplicationStateConflictError, match="revision mismatch"):
        update_extraction_run(
            created.run_id,
            status=ExtractionRunStatus.EXTRACTED,
            expected_revision=1,
        )
    loaded = get_extraction_run(created.run_id)
    assert loaded.status == ExtractionRunStatus.PREPARED
    assert loaded.revision == 2


def test_supersede_is_atomic_on_injected_failure(
    application_state_dsn: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    created = create_extraction_run(_run())
    prepared = update_extraction_run(
        created.run_id,
        status=ExtractionRunStatus.PREPARED,
        expected_revision=created.revision,
    )

    def boom(_conn, _run):
        raise RuntimeError("injected supersede failure")

    monkeypatch.setattr(
        "application_state.ingest.service.repo.insert_run",
        boom,
    )
    successor = _run(
        run_id="er_successor",
        supersedes_run_id=prepared.run_id,
    )
    with pytest.raises(RuntimeError, match="injected"):
        supersede_extraction_run(
            prepared.run_id,
            expected_revision=prepared.revision,
            successor=successor,
        )
    loaded = get_extraction_run(prepared.run_id)
    assert loaded.status == ExtractionRunStatus.PREPARED
    assert loaded.superseded_by_run_id is None
    with pytest.raises(ApplicationStateNotFoundError):
        get_extraction_run("er_successor")


def test_supersede_commits_reciprocal_lineage(application_state_dsn: str) -> None:
    created = create_extraction_run(_run())
    prepared = update_extraction_run(
        created.run_id,
        status=ExtractionRunStatus.PREPARED,
        expected_revision=created.revision,
    )
    successor = _run(
        run_id="er_next",
        source_artifact_id=prepared.source_artifact_id,
        supersedes_run_id=prepared.run_id,
    )
    created_successor = supersede_extraction_run(
        prepared.run_id,
        expected_revision=prepared.revision,
        successor=successor,
    )
    predecessor = get_extraction_run(prepared.run_id)
    assert predecessor.status == ExtractionRunStatus.SUPERSEDED
    assert predecessor.superseded_by_run_id == created_successor.run_id
    assert created_successor.supersedes_run_id == predecessor.run_id
    assert predecessor.revision == prepared.revision + 1


def test_inspect_empty_catalog(application_state_dsn: str) -> None:
    snapshot = inspect_ingest_authority()
    assert snapshot.run_count == 0


def test_malformed_row_is_integrity_not_empty(application_state_dsn: str) -> None:
    with psycopg.connect(application_state_dsn) as conn:
        conn.execute(
            """
            INSERT INTO ingest.run (
                run_id, schema_version, record_version, source_artifact_id,
                source_domain, status, revision, components, diagnostics, lineage
            ) VALUES (
                'er_bad', 'not-a-schema', '1.0', 'sa_world_1',
                'worldbuilding', 'draft', 1, '{}'::jsonb, '{}'::jsonb, '{}'::jsonb
            )
            """
        )
        conn.commit()
    with pytest.raises(ApplicationStateIntegrityError, match="cannot be interpreted"):
        inspect_ingest_authority()
    with pytest.raises(ApplicationStateIntegrityError):
        get_extraction_run("er_bad")


def test_missing_component_bytes_do_not_hide_catalog_row(
    tmp_path: Path, application_state_dsn: str
) -> None:
    from apps.live_control_server.services.graph_run_registry import (
        GraphRunRegistryError,
        get_extraction_run as mounted_get,
        get_reviewable_extraction_run,
    )
    from application_state.ingest.repository import insert_run
    from application_state.unit_of_work import unit_of_work

    components = {
        "source_artifact": ExtractionRunComponentRef(
            kind=ExtractionRunComponentKind.SOURCE_ARTIFACT,
            uri="repo://missing-source.md",
            sha256="a" * 64,
        ),
        "source_span_index": ExtractionRunComponentRef(
            kind=ExtractionRunComponentKind.SOURCE_SPAN_INDEX,
            uri="repo://missing-spans.json",
            sha256="b" * 64,
        ),
        "candidate_graph": ExtractionRunComponentRef(
            kind=ExtractionRunComponentKind.CANDIDATE_GRAPH,
            uri="repo://missing-graph.json",
            sha256="c" * 64,
        ),
    }
    run = _run(
        status=ExtractionRunStatus.REVIEWABLE,
        components=components,
    )
    with unit_of_work(application_state_dsn) as conn:
        insert_run(conn, run)
    catalog = mounted_get(tmp_path, run.run_id)
    assert catalog.run_id == run.run_id
    with pytest.raises(GraphRunRegistryError, match="component file missing|unknown source_artifact"):
        get_reviewable_extraction_run(tmp_path, run.run_id)


def test_boot_does_not_migrate_or_import(
    tmp_path: Path, application_state_dsn: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    from apps.live_control_server.services.runtime_preflight import run_runtime_preflight

    monkeypatch.setenv("DUNGEONBUDDY_APPLICATION_STATE_DATABASE_URL", application_state_dsn)
    called = {"upgrade": 0, "import": 0}

    def fake_upgrade(*, dsn=None):
        called["upgrade"] += 1

    def fake_import(*_args, **_kwargs):
        called["import"] += 1
        raise AssertionError("import must not run on boot/preflight")

    monkeypatch.setattr("application_state.cli.upgrade_to_head", fake_upgrade)
    monkeypatch.setattr(
        "application_state.ingest.import_legacy.import_extraction_runs_from_registry",
        fake_import,
    )
    report = run_runtime_preflight(repo_root=tmp_path, load_env=False)
    ingest = next(check for check in report.checks if check.id == "ingest_registry")
    assert ingest.status == "EMPTY"
    assert called["upgrade"] == 0
    assert called["import"] == 0
