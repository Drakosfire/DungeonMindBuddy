from __future__ import annotations
from tests.page_fixtures import create_page_fixture, save_page
from apps.live_control_server.services.workspace_document_registry import get_workspace_document

import hashlib
import json
from pathlib import Path

import pytest

from apps.live_control_server.services.graph_run_registry import (
    GraphRunRegistryError,
    create_extraction_run,
    get_extraction_run,
    get_reviewable_extraction_run,
    supersede_extraction_run,
    update_extraction_run_status,
)
from apps.live_control_server.services.source_artifact_registry import (
    SourceArtifactRegistryError,
    create_source_artifact_from_workspace_document,
    get_source_artifact,
    resolve_worldbuilding_source_span,
    load_source_span_index,
    load_registered_source_artifact_bytes,
    source_span_index_relpath,
)
from graph_memory.source_span import source_span_index_to_dict
from graph_memory.ingestion.extraction_run import (
    ExtractionRunComponentKind,
    ExtractionRunComponentRef,
    ExtractionRunStatus,
)


@pytest.fixture(autouse=True)
def _ingest_application_state(application_state_dsn: str) -> str:
    return application_state_dsn


def _corrupt_ingest_run(dsn: str, run_id: str, **fields: object) -> None:
    import psycopg

    assignments = ", ".join(f"{key} = %s" for key in fields)
    values = list(fields.values()) + [run_id]
    with psycopg.connect(dsn) as conn:
        conn.execute(
            f"UPDATE ingest.run SET {assignments} WHERE run_id = %s",
            values,
        )
        conn.commit()


def _write_committed_markdown(root: Path, record, markdown: str) -> str:
    content = markdown.rstrip("\n") + "\n"
    record = save_page(root, record.document_id, content)
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _committed_worldbuilding(root: Path, markdown: str = "# Lore\n\nBody.\n"):
    record = create_page_fixture(
        root,
        title="Lore",
        campaign_id="eldyrwild",
        kind="worldbuilding_source",
        source_domain="worldbuilding",
        document_class="lore",
        authority_state="draft",
        visibility_state="internal",
    )
    committed = get_workspace_document(root, record.document_id)
    digest = _write_committed_markdown(root, committed, markdown)
    return get_workspace_document(root, committed.document_id), digest


def _reviewable_components(root: Path, artifact, graph_payload: dict | None = None):
    source_digest = hashlib.sha256(load_registered_source_artifact_bytes(root, artifact.source_artifact_id)[1]).hexdigest()
    span_rel = source_span_index_relpath(artifact.source_artifact_id)
    span_path = root / span_rel
    span_path.parent.mkdir(parents=True, exist_ok=True)
    span_path.write_text(json.dumps(source_span_index_to_dict(
        load_source_span_index(root, artifact.source_artifact_id)), indent=2, ensure_ascii=False) + "\n")
    span_digest = hashlib.sha256(span_path.read_bytes()).hexdigest()
    graph_rel = "out/registries/test_candidate_graph.json"
    graph_path = root / graph_rel
    graph_path.parent.mkdir(parents=True, exist_ok=True)
    graph_path.write_text(
        json.dumps(graph_payload or {"nodes": [], "edges": []}),
        encoding="utf-8",
    )
    graph_digest = hashlib.sha256(graph_path.read_bytes()).hexdigest()
    return {
        "source_artifact": ExtractionRunComponentRef(
            kind=ExtractionRunComponentKind.SOURCE_ARTIFACT,
            uri=artifact.uri,
            sha256=source_digest,
        ),
        "source_span_index": ExtractionRunComponentRef(
            kind=ExtractionRunComponentKind.SOURCE_SPAN_INDEX,
            uri=f"repo://{span_rel}",
            sha256=span_digest,
        ),
        "candidate_graph": ExtractionRunComponentRef(
            kind=ExtractionRunComponentKind.CANDIDATE_GRAPH,
            uri=f"repo://{graph_rel}",
            sha256=graph_digest,
        ),
    }


def _store_fixture_outputs(root: Path, run):
    from application_state.ingest.components import persist_component_payload

    for key, ref in run.components.items():
        if key != "source_artifact":
            persist_component_payload(run_id=run.run_id, expected_revision=run.revision,
                kind=key, payload=(root / ref.uri.removeprefix("repo://")).read_bytes())


def test_source_artifact_reads_committed_page_not_client_markdown(tmp_path: Path) -> None:
    record, digest = _committed_worldbuilding(tmp_path, "# Canon\n\nFrom disk.\n")
    artifact = create_source_artifact_from_workspace_document(
        tmp_path,
        document_id=record.document_id,
        expected_revision=record.revision,
    )
    assert artifact.content_sha256 == digest
    assert artifact.uri == f"object://{artifact.source_artifact_id}"
    assert artifact.workspace_document_revision == record.revision
    assert artifact.session_id is None
    loaded = get_source_artifact(tmp_path, artifact.source_artifact_id)
    assert loaded.source_artifact_id == artifact.source_artifact_id


def test_source_artifact_rejects_uncommitted_page(tmp_path: Path) -> None:
    record = create_page_fixture(
        tmp_path,
        title="Lore",
        campaign_id="eldyrwild",
        kind="worldbuilding_source",
        source_domain="worldbuilding",
        document_class="lore",
        authority_state="draft",
        visibility_state="internal",
    )
    committed = get_workspace_document(tmp_path, record.document_id)
    with pytest.raises(SourceArtifactRegistryError, match="active committed Page"):
        create_source_artifact_from_workspace_document(
            tmp_path,
            document_id=committed.document_id,
            expected_revision=committed.revision,
        )


def test_source_artifact_expected_digest_assertion(tmp_path: Path) -> None:
    record, digest = _committed_worldbuilding(tmp_path)
    with pytest.raises(SourceArtifactRegistryError, match="expected_content_sha256"):
        create_source_artifact_from_workspace_document(
            tmp_path,
            document_id=record.document_id,
            expected_revision=record.revision,
            expected_content_sha256="0" * 64,
        )
    artifact = create_source_artifact_from_workspace_document(
        tmp_path,
        document_id=record.document_id,
        expected_revision=record.revision,
        expected_content_sha256=digest,
    )
    assert artifact.content_sha256 == digest


def test_source_artifact_idempotent_and_collision_safe(tmp_path: Path) -> None:
    record, _digest = _committed_worldbuilding(tmp_path)
    first = create_source_artifact_from_workspace_document(
        tmp_path,
        document_id=record.document_id,
        expected_revision=record.revision,
    )
    second = create_source_artifact_from_workspace_document(
        tmp_path,
        document_id=record.document_id,
        expected_revision=record.revision,
    )
    assert first.source_artifact_id == second.source_artifact_id

    # The immutable input owner rejects registration with changed scope.
    from apps.live_control_server.services.source_artifact_registry import (
        _register_source_input, load_registered_source_artifact_text,
    )
    content = load_registered_source_artifact_text(tmp_path, first.source_artifact_id)[1]
    with pytest.raises(SourceArtifactRegistryError, match="identity does not match the persisted source") as exc:
        _register_source_input(content=content,
            artifact=first.model_copy(update={"campaign_id": "other-world"}))
    assert exc.value.status_code == 409
    assert get_source_artifact(tmp_path, first.source_artifact_id) == first


def test_worldbuilding_span_persists_and_resolves(tmp_path: Path) -> None:
    record, _digest = _committed_worldbuilding(tmp_path, "# Lore\n\nBody paragraph.\n")
    artifact = create_source_artifact_from_workspace_document(
        tmp_path,
        document_id=record.document_id,
        expected_revision=record.revision,
    )
    evidence = resolve_worldbuilding_source_span(
        tmp_path, artifact.source_artifact_id, span_index=1
    )
    assert evidence.can_open_source is True
    assert evidence.can_highlight_span is True
    assert "Body paragraph" in evidence.preview_snippet
    assert evidence.source_artifact_id == artifact.source_artifact_id
    assert evidence.source_anchor_id is not None
    assert artifact.content_sha256[:12] in evidence.source_anchor_id


def test_extraction_run_requires_known_artifact(tmp_path: Path) -> None:
    with pytest.raises(GraphRunRegistryError, match="unknown source_artifact_id"):
        create_extraction_run(
            tmp_path,
            source_artifact_id="artifact:worldbuilding:missing",
            source_domain="worldbuilding",
            campaign_id="eldyrwild",
            session_id=None,
        )


def test_extraction_run_exact_reload_and_no_latest(tmp_path: Path) -> None:
    record, _digest = _committed_worldbuilding(tmp_path)
    artifact = create_source_artifact_from_workspace_document(
        tmp_path,
        document_id=record.document_id,
        expected_revision=record.revision,
    )
    run = create_extraction_run(
        tmp_path,
        source_artifact_id=artifact.source_artifact_id,
        source_domain="worldbuilding",
        campaign_id="eldyrwild",
        session_id=None,
    )
    loaded = get_extraction_run(tmp_path, run.run_id)
    assert loaded.run_id == run.run_id
    assert loaded.revision == 1
    with pytest.raises(GraphRunRegistryError) as exc_info:
        get_extraction_run(tmp_path, "missing-run")
    assert exc_info.value.status_code == 404


def test_extraction_run_rejects_fabricated_worldbuilding_session(tmp_path: Path) -> None:
    record, _digest = _committed_worldbuilding(tmp_path)
    artifact = create_source_artifact_from_workspace_document(
        tmp_path,
        document_id=record.document_id,
        expected_revision=record.revision,
    )
    with pytest.raises(GraphRunRegistryError, match="session_id"):
        create_extraction_run(
            tmp_path,
            source_artifact_id=artifact.source_artifact_id,
            source_domain="worldbuilding",
            session_id="session-1",
        )


def test_reviewable_requires_resolvable_evidence(tmp_path: Path) -> None:
    record, _digest = _committed_worldbuilding(tmp_path)
    artifact = create_source_artifact_from_workspace_document(
        tmp_path,
        document_id=record.document_id,
        expected_revision=record.revision,
    )
    run = create_extraction_run(
        tmp_path,
        source_artifact_id=artifact.source_artifact_id,
        source_domain="worldbuilding",
    )
    prepared = update_extraction_run_status(
        tmp_path,
        run.run_id,
        status=ExtractionRunStatus.PREPARED,
        expected_revision=run.revision,
        components={
            "source_artifact": ExtractionRunComponentRef(
                kind=ExtractionRunComponentKind.SOURCE_ARTIFACT,
                uri="repo://x.md",
                exists=True,
                sha256="a" * 64,
            ),
        },
    )
    extracted = update_extraction_run_status(
        tmp_path,
        prepared.run_id,
        status=ExtractionRunStatus.EXTRACTED,
        expected_revision=prepared.revision,
    )
    validated = update_extraction_run_status(
        tmp_path,
        extracted.run_id,
        status=ExtractionRunStatus.VALIDATED,
        expected_revision=extracted.revision,
    )
    with pytest.raises(GraphRunRegistryError, match="incomplete|require|digest|missing|uri"):
        update_extraction_run_status(
            tmp_path,
            validated.run_id,
            status=ExtractionRunStatus.REVIEWABLE,
            expected_revision=validated.revision,
        )


def test_file_only_outputs_do_not_grant_reviewable(tmp_path: Path) -> None:
    record, _ = _committed_worldbuilding(tmp_path)
    artifact = create_source_artifact_from_workspace_document(tmp_path, document_id=record.document_id, expected_revision=record.revision)
    run = create_extraction_run(tmp_path, source_artifact_id=artifact.source_artifact_id,
        source_domain="worldbuilding", components=_reviewable_components(tmp_path, artifact),
        status=ExtractionRunStatus.VALIDATED)
    with pytest.raises(GraphRunRegistryError, match="not durable"):
        update_extraction_run_status(tmp_path, run.run_id, status=ExtractionRunStatus.REVIEWABLE, expected_revision=run.revision)
    assert get_extraction_run(tmp_path, run.run_id) == run



def test_reviewable_happy_path_and_terminal_protection(tmp_path: Path) -> None:
    record, _digest = _committed_worldbuilding(tmp_path)
    artifact = create_source_artifact_from_workspace_document(
        tmp_path,
        document_id=record.document_id,
        expected_revision=record.revision,
    )
    components = _reviewable_components(tmp_path, artifact)
    run = create_extraction_run(
        tmp_path,
        source_artifact_id=artifact.source_artifact_id,
        source_domain="worldbuilding",
        components=components,
    )
    _store_fixture_outputs(tmp_path, run)
    for status in (
        ExtractionRunStatus.PREPARED,
        ExtractionRunStatus.EXTRACTED,
        ExtractionRunStatus.VALIDATED,
        ExtractionRunStatus.REVIEWABLE,
    ):
        run = update_extraction_run_status(
            tmp_path,
            run.run_id,
            status=status,
            expected_revision=run.revision,
        )
    assert run.status == ExtractionRunStatus.REVIEWABLE
    mutated = dict(run.components)
    mutated["candidate_graph"] = ExtractionRunComponentRef(
        kind=ExtractionRunComponentKind.CANDIDATE_GRAPH,
        uri="repo://out/registries/other_candidate_graph.json",
        sha256="f" * 64,
    )
    with pytest.raises(GraphRunRegistryError, match="frozen|already|invalid"):
        update_extraction_run_status(
            tmp_path,
            run.run_id,
            status=ExtractionRunStatus.REVIEWABLE,
            expected_revision=run.revision,
            components=mutated,
        )
    promoted = update_extraction_run_status(
        tmp_path,
        run.run_id,
        status=ExtractionRunStatus.PROMOTED,
        expected_revision=run.revision,
    )
    with pytest.raises(GraphRunRegistryError, match="terminal"):
        update_extraction_run_status(
            tmp_path,
            promoted.run_id,
            status=ExtractionRunStatus.DRAFT,
            expected_revision=promoted.revision,
        )


def test_get_reviewable_extraction_run_ignores_duplicate_file_records(
    tmp_path: Path, application_state_dsn: str
) -> None:
    """File-registry duplicates are not mounted authority after the APP-STATE cutover."""
    from datetime import UTC, datetime

    from application_state.ingest.import_legacy import (
        ExtractionRunRegistryDocument,
        LEGACY_EXTRACTION_RUN_REGISTRY_REL,
    )
    from application_state.ingest.service import create_extraction_run as db_create
    from graph_memory.ingestion.extraction_run import ExtractionRun

    record, _digest = _committed_worldbuilding(tmp_path)
    artifact = create_source_artifact_from_workspace_document(
        tmp_path,
        document_id=record.document_id,
        expected_revision=record.revision,
    )
    components = _reviewable_components(tmp_path, artifact)
    now = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    duplicate_id = "er_duplicate_targeted_loader"
    first = ExtractionRun(
        run_id=duplicate_id,
        source_artifact_id=artifact.source_artifact_id,
        source_domain="worldbuilding",
        status=ExtractionRunStatus.REVIEWABLE,
        campaign_id=artifact.campaign_id,
        session_id=None,
        created_at=now,
        updated_at=now,
        components=components,
    )
    db_create(first)
    _store_fixture_outputs(tmp_path, first)
    path = tmp_path / LEGACY_EXTRACTION_RUN_REGISTRY_REL
    path.parent.mkdir(parents=True, exist_ok=True)
    document = ExtractionRunRegistryDocument(records=[first, first.model_copy(deep=True)])
    path.write_text(
        json.dumps(document.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    loaded = get_reviewable_extraction_run(tmp_path, duplicate_id)
    assert loaded.run_id == duplicate_id
    catalog = get_extraction_run(tmp_path, duplicate_id)
    assert catalog.run_id == duplicate_id


def test_get_reviewable_extraction_run_rejects_incoming_nonreciprocal_lineage(
    tmp_path: Path, application_state_dsn: str
) -> None:
    """Inbound supersession pointers must join the connected lineage set."""
    from datetime import UTC, datetime

    from application_state.ingest import repository as ingest_repo
    from application_state.unit_of_work import unit_of_work
    from graph_memory.ingestion.extraction_run import ExtractionRun

    record, _digest = _committed_worldbuilding(tmp_path)
    artifact = create_source_artifact_from_workspace_document(
        tmp_path,
        document_id=record.document_id,
        expected_revision=record.revision,
    )
    components = _reviewable_components(tmp_path, artifact)
    now = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    selected = ExtractionRun(
        run_id="er_selected_no_pointers",
        source_artifact_id=artifact.source_artifact_id,
        source_domain="worldbuilding",
        status=ExtractionRunStatus.REVIEWABLE,
        campaign_id=artifact.campaign_id,
        session_id=None,
        created_at=now,
        updated_at=now,
        components=components,
    )
    sibling = ExtractionRun(
        run_id="er_sibling_points_at_selected",
        source_artifact_id=artifact.source_artifact_id,
        source_domain="worldbuilding",
        status=ExtractionRunStatus.SUPERSEDED,
        campaign_id=artifact.campaign_id,
        session_id=None,
        created_at=now,
        updated_at=now,
        components=components,
        superseded_by_run_id=selected.run_id,
    )
    with unit_of_work(application_state_dsn) as conn:
        ingest_repo.insert_run(conn, selected)
        ingest_repo.insert_run(conn, sibling)

    with pytest.raises(GraphRunRegistryError, match="lineage|non-reciprocal|supersession"):
        get_reviewable_extraction_run(tmp_path, selected.run_id)


def test_stale_revision_and_supersession(tmp_path: Path) -> None:
    record, _digest = _committed_worldbuilding(tmp_path)
    artifact = create_source_artifact_from_workspace_document(
        tmp_path,
        document_id=record.document_id,
        expected_revision=record.revision,
    )
    run = create_extraction_run(
        tmp_path,
        source_artifact_id=artifact.source_artifact_id,
        source_domain="worldbuilding",
    )
    prepared = update_extraction_run_status(
        tmp_path,
        run.run_id,
        status=ExtractionRunStatus.PREPARED,
        expected_revision=run.revision,
    )
    with pytest.raises(GraphRunRegistryError, match="revision mismatch"):
        update_extraction_run_status(
            tmp_path,
            run.run_id,
            status=ExtractionRunStatus.EXTRACTED,
            expected_revision=run.revision,
        )
    prior_components = dict(prepared.components)
    successor = supersede_extraction_run(
        tmp_path,
        prepared.run_id,
        expected_revision=prepared.revision,
    )
    predecessor = get_extraction_run(tmp_path, prepared.run_id)
    assert predecessor.status == ExtractionRunStatus.SUPERSEDED
    assert predecessor.superseded_by_run_id == successor.run_id
    assert predecessor.components == prior_components
    assert successor.supersedes_run_id == prepared.run_id
    assert successor.status == ExtractionRunStatus.DRAFT


def test_malformed_registry_fails_closed_on_load(
    tmp_path: Path, application_state_dsn: str
) -> None:
    record, _digest = _committed_worldbuilding(tmp_path)
    artifact = create_source_artifact_from_workspace_document(
        tmp_path,
        document_id=record.document_id,
        expected_revision=record.revision,
    )
    run = create_extraction_run(
        tmp_path,
        source_artifact_id=artifact.source_artifact_id,
        source_domain="worldbuilding",
    )
    _corrupt_ingest_run(application_state_dsn, run.run_id, session_id="session-1")
    with pytest.raises(GraphRunRegistryError, match="malformed|cannot be interpreted|worldbuilding"):
        get_extraction_run(tmp_path, run.run_id)


def _advance_to_reviewable(tmp_path: Path, run, components, *, persist=True):
    if persist:
        _store_fixture_outputs(tmp_path, run.model_copy(update={"components": components}))
    current = run
    for status in (
        ExtractionRunStatus.PREPARED,
        ExtractionRunStatus.EXTRACTED,
        ExtractionRunStatus.VALIDATED,
        ExtractionRunStatus.REVIEWABLE,
    ):
        current = update_extraction_run_status(
            tmp_path,
            current.run_id,
            status=status,
            expected_revision=current.revision,
            components=components if status == ExtractionRunStatus.PREPARED else None,
        )
    return current


def test_concurrent_updates_with_same_expected_revision(tmp_path: Path) -> None:
    import threading

    record, _digest = _committed_worldbuilding(tmp_path)
    artifact = create_source_artifact_from_workspace_document(
        tmp_path,
        document_id=record.document_id,
        expected_revision=record.revision,
    )
    run = create_extraction_run(
        tmp_path,
        source_artifact_id=artifact.source_artifact_id,
        source_domain="worldbuilding",
    )
    barrier = threading.Barrier(2)
    results: list[object] = []

    def worker(profile_id: str) -> None:
        barrier.wait()
        try:
            updated = update_extraction_run_status(
                tmp_path,
                run.run_id,
                status=ExtractionRunStatus.PREPARED,
                expected_revision=run.revision,
                components={
                    "candidate_graph": ExtractionRunComponentRef(
                        kind=ExtractionRunComponentKind.CANDIDATE_GRAPH,
                        uri=f"repo://out/registries/{profile_id}.json",
                        sha256="a" * 64,
                    )
                },
            )
            results.append(updated)
        except GraphRunRegistryError as exc:
            results.append(exc)

    threads = [
        threading.Thread(target=worker, args=("alpha",)),
        threading.Thread(target=worker, args=("beta",)),
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    successes = [item for item in results if not isinstance(item, Exception)]
    failures = [item for item in results if isinstance(item, Exception)]
    assert len(successes) == 1
    assert len(failures) == 1
    assert failures[0].status_code == 409
    assert "revision mismatch" in str(failures[0]) or "concurrently" in str(failures[0])
    loaded = get_extraction_run(tmp_path, run.run_id)
    assert loaded.revision == run.revision + 1
    assert loaded.status == ExtractionRunStatus.PREPARED


def test_supersede_save_failure_leaves_predecessor_unchanged(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    record, _digest = _committed_worldbuilding(tmp_path)
    artifact = create_source_artifact_from_workspace_document(
        tmp_path,
        document_id=record.document_id,
        expected_revision=record.revision,
    )
    run = create_extraction_run(
        tmp_path,
        source_artifact_id=artifact.source_artifact_id,
        source_domain="worldbuilding",
    )
    prepared = update_extraction_run_status(
        tmp_path,
        run.run_id,
        status=ExtractionRunStatus.PREPARED,
        expected_revision=run.revision,
    )

    def boom_insert(_conn, _run):
        raise OSError("simulated ingest persist failure"        )

    monkeypatch.setattr(
        "application_state.ingest.service.repo.insert_run",
        boom_insert,
    )
    with pytest.raises(OSError, match="simulated ingest persist failure"):
        supersede_extraction_run(
            tmp_path,
            prepared.run_id,
            expected_revision=prepared.revision,
        )
    predecessor = get_extraction_run(tmp_path, prepared.run_id)
    assert predecessor.status == ExtractionRunStatus.PREPARED
    assert predecessor.superseded_by_run_id is None
    assert predecessor.revision == prepared.revision
    assert not (tmp_path / "out/registries/extraction_runs.json").exists()


def test_promoted_run_integrity_checked_on_load(tmp_path: Path, application_state_dsn: str) -> None:
    record, _digest = _committed_worldbuilding(tmp_path)
    artifact = create_source_artifact_from_workspace_document(
        tmp_path,
        document_id=record.document_id,
        expected_revision=record.revision,
    )
    components = _reviewable_components(tmp_path, artifact)
    run = create_extraction_run(
        tmp_path,
        source_artifact_id=artifact.source_artifact_id,
        source_domain="worldbuilding",
        components=components,
    )
    reviewable = _advance_to_reviewable(tmp_path, run, components)
    promoted = update_extraction_run_status(
        tmp_path,
        reviewable.run_id,
        status=ExtractionRunStatus.PROMOTED,
        expected_revision=reviewable.revision,
    )
    assert get_extraction_run(tmp_path, promoted.run_id).status == ExtractionRunStatus.PROMOTED

    graph_path = tmp_path / components["candidate_graph"].uri.removeprefix("repo://")
    graph_path.write_text(json.dumps({"nodes": [{"id": "tampered"}]}), encoding="utf-8")
    catalog = get_extraction_run(tmp_path, promoted.run_id)
    assert catalog.status == ExtractionRunStatus.PROMOTED
    from apps.live_control_server.services.graph_run_registry import (
        assert_run_reviewable_evidence,
    )

    assert_run_reviewable_evidence(tmp_path, catalog)
    import psycopg
    with psycopg.connect(application_state_dsn) as conn:
        conn.execute("UPDATE ingest.component_payload SET payload=%s WHERE run_id=%s AND kind='candidate_graph'", (b"corrupt", catalog.run_id))
    with pytest.raises(GraphRunRegistryError, match="integrity|digest mismatch"):
        assert_run_reviewable_evidence(tmp_path, catalog)


def test_component_uri_is_not_lifecycle_authority(tmp_path: Path) -> None:
    record, _ = _committed_worldbuilding(tmp_path)
    artifact = create_source_artifact_from_workspace_document(tmp_path, document_id=record.document_id, expected_revision=record.revision)
    components = _reviewable_components(tmp_path, artifact)
    run = create_extraction_run(tmp_path, source_artifact_id=artifact.source_artifact_id, source_domain="worldbuilding", components=components)
    _store_fixture_outputs(tmp_path, run)
    components = {key: ref.model_copy(update={"uri": " historical:never-open "}) for key, ref in components.items()}
    sealed = _advance_to_reviewable(tmp_path, run, components, persist=False)
    assert get_reviewable_extraction_run(tmp_path, sealed.run_id) == sealed





def test_one_sided_supersession_fails_closed_on_load(
    tmp_path: Path, application_state_dsn: str
) -> None:
    record, _digest = _committed_worldbuilding(tmp_path)
    artifact = create_source_artifact_from_workspace_document(
        tmp_path,
        document_id=record.document_id,
        expected_revision=record.revision,
    )
    run = create_extraction_run(
        tmp_path,
        source_artifact_id=artifact.source_artifact_id,
        source_domain="worldbuilding",
    )
    prepared = update_extraction_run_status(
        tmp_path,
        run.run_id,
        status=ExtractionRunStatus.PREPARED,
        expected_revision=run.revision,
    )
    successor = supersede_extraction_run(
        tmp_path,
        prepared.run_id,
        expected_revision=prepared.revision,
    )
    _corrupt_ingest_run(
        application_state_dsn,
        prepared.run_id,
        superseded_by_run_id=None,
        status="prepared",
    )
    with pytest.raises(GraphRunRegistryError, match="lineage|non-reciprocal|missing"):
        get_extraction_run(tmp_path, successor.run_id)


def test_source_artifact_snapshot_survives_later_page_discard(tmp_path: Path) -> None:
    from apps.live_control_server.services.workspace_document_registry import discard_workspace_document

    record, digest = _committed_worldbuilding(tmp_path)
    artifact = create_source_artifact_from_workspace_document(
        tmp_path, document_id=record.document_id, expected_revision=record.revision,
    )
    discarded = discard_workspace_document(tmp_path, record.document_id, expected_revision=record.revision)
    captured, raw = load_registered_source_artifact_bytes(tmp_path, artifact.source_artifact_id)
    assert captured.workspace_document_revision == record.revision
    assert hashlib.sha256(raw).hexdigest() == digest
    assert discarded.status == "discarded"
    with pytest.raises(SourceArtifactRegistryError, match="active committed Page"):
        create_source_artifact_from_workspace_document(
            tmp_path, document_id=record.document_id, expected_revision=discarded.revision,
        )


def test_reciprocal_lineage_with_unrelated_artifacts_fails_closed_on_load(
    tmp_path: Path, application_state_dsn: str
) -> None:
    record, _digest = _committed_worldbuilding(tmp_path)
    artifact = create_source_artifact_from_workspace_document(
        tmp_path,
        document_id=record.document_id,
        expected_revision=record.revision,
    )
    run = create_extraction_run(
        tmp_path,
        source_artifact_id=artifact.source_artifact_id,
        source_domain="worldbuilding",
    )
    prepared = update_extraction_run_status(
        tmp_path,
        run.run_id,
        status=ExtractionRunStatus.PREPARED,
        expected_revision=run.revision,
    )
    successor = supersede_extraction_run(
        tmp_path,
        prepared.run_id,
        expected_revision=prepared.revision,
    )
    _corrupt_ingest_run(
        application_state_dsn,
        successor.run_id,
        source_artifact_id="artifact:unrelated",
    )
    with pytest.raises(GraphRunRegistryError, match="lineage|source_artifact_id"):
        get_extraction_run(tmp_path, prepared.run_id)


def test_reciprocal_lineage_with_non_superseded_predecessor_fails_closed_on_load(
    tmp_path: Path, application_state_dsn: str
) -> None:
    record, _digest = _committed_worldbuilding(tmp_path)
    artifact = create_source_artifact_from_workspace_document(
        tmp_path,
        document_id=record.document_id,
        expected_revision=record.revision,
    )
    run = create_extraction_run(
        tmp_path,
        source_artifact_id=artifact.source_artifact_id,
        source_domain="worldbuilding",
    )
    prepared = update_extraction_run_status(
        tmp_path,
        run.run_id,
        status=ExtractionRunStatus.PREPARED,
        expected_revision=run.revision,
    )
    successor = supersede_extraction_run(
        tmp_path,
        prepared.run_id,
        expected_revision=prepared.revision,
    )
    _corrupt_ingest_run(application_state_dsn, prepared.run_id, status="prepared")
    with pytest.raises(GraphRunRegistryError, match="lineage|must be superseded"):
        get_extraction_run(tmp_path, successor.run_id)


def _validated_recap_run(
    tmp_path: Path,
    *,
    recap_text: str = "# Session Recap\n\nA paragraph.\n",
    component_uri: str | None = None,
    component_digest: str | None | object = ...,
    status: ExtractionRunStatus = ExtractionRunStatus.VALIDATED,
):
    from apps.live_control_server.services.source_artifact_registry import (
        create_recap_source_artifact,
    )

    artifact = create_recap_source_artifact(
        tmp_path,
        world_id="world:longmont-test",
        campaign_id="longmont-c2",
        session_id="session-23",
        recap_text=recap_text,
    )
    source_path = tmp_path / "historical-source-copy.md"
    source_path.write_bytes(load_registered_source_artifact_bytes(tmp_path, artifact.source_artifact_id)[1])
    source_digest = hashlib.sha256(source_path.read_bytes()).hexdigest()
    uri = component_uri or "repo://historical-source-copy.md"
    if component_digest is ...:
        digest: str | None = source_digest
    else:
        digest = component_digest
    components = {
        "source_artifact": ExtractionRunComponentRef(
            kind=ExtractionRunComponentKind.SOURCE_ARTIFACT,
            uri=uri,
            sha256=digest,
        ),
    }
    run = create_extraction_run(
        tmp_path,
        source_artifact_id=artifact.source_artifact_id,
        source_domain="recap",
        campaign_id="longmont-c2",
        session_id="session-23",
        lineage={"native_world_id": "world:longmont-test", "campaign_id": "longmont-c2"},
    )
    run = update_extraction_run_status(
        tmp_path,
        run.run_id,
        status=ExtractionRunStatus.PREPARED,
        expected_revision=run.revision,
        components=components,
    )
    if status != ExtractionRunStatus.PREPARED:
        run = update_extraction_run_status(
            tmp_path,
            run.run_id,
            status=ExtractionRunStatus.EXTRACTED,
            expected_revision=run.revision,
        )
    if status == ExtractionRunStatus.VALIDATED:
        run = update_extraction_run_status(
            tmp_path,
            run.run_id,
            status=ExtractionRunStatus.VALIDATED,
            expected_revision=run.revision,
        )
    return run, artifact, source_path


def test_get_reviewable_extraction_run_still_rejects_validated(tmp_path: Path) -> None:
    run, _artifact, _source_path = _validated_recap_run(tmp_path)
    with pytest.raises(GraphRunRegistryError, match="not reviewable"):
        get_reviewable_extraction_run(tmp_path, run.run_id)


def _frozen_snapshot_child(root: Path):
    """Current producer freezes source/spans together; a child only moves output."""
    record, _ = _committed_worldbuilding(root, "# Lore\n\nMira guards the crossing.\n")
    artifact = create_source_artifact_from_workspace_document(
        root, document_id=record.document_id, expected_revision=record.revision,
    )
    original = _reviewable_components(root, artifact)
    frozen = root / "out/runs/parent"
    frozen.mkdir(parents=True)
    components = {}
    names = {"source_artifact": "source.md", "source_span_index": "source_span_index.json", "candidate_graph": "candidate_graph.json"}
    for kind, ref in original.items():
        path = frozen / names[kind]
        path.write_bytes(load_registered_source_artifact_bytes(root, artifact.source_artifact_id)[1]
                         if kind == "source_artifact" else (root / ref.uri.removeprefix("repo://")).read_bytes())
        components[kind] = ref.model_copy(update={"uri": "repo://" + path.relative_to(root).as_posix()})
    parent = create_extraction_run(
        root, source_artifact_id=artifact.source_artifact_id, source_domain="worldbuilding",
        components=components, status=ExtractionRunStatus.VALIDATED,
        profile_id="worldbuilding_shepherds_flock_v0@0.1",
    )
    _store_fixture_outputs(root, parent)
    parent = update_extraction_run_status(root, parent.run_id, status=ExtractionRunStatus.REVIEWABLE, expected_revision=parent.revision)
    child_path = root / "out/derived/child/candidate_graph.json"
    child_path.parent.mkdir(parents=True)
    child_path.write_text('{"nodes": [], "edges": [], "reviewed": true}')
    child_components = dict(components)
    child_components["candidate_graph"] = components["candidate_graph"].model_copy(update={
        "uri": "repo://" + child_path.relative_to(root).as_posix(),
        "sha256": hashlib.sha256(child_path.read_bytes()).hexdigest(),
    })
    child = create_extraction_run(
        root, source_artifact_id=artifact.source_artifact_id, source_domain="worldbuilding",
        components=child_components, status=ExtractionRunStatus.VALIDATED,
        profile_id=parent.profile_id, lineage={"parent_run_id": parent.run_id},
    )
    _store_fixture_outputs(root, child)
    return parent, child, frozen, child_path


def test_corrected_child_seals_with_inherited_frozen_evidence_and_reopens_exactly(tmp_path: Path):
    from apps.live_control_server.services.promotable_ingest_run import resolve_promotable_ingest_run

    parent, child, frozen, child_path = _frozen_snapshot_child(tmp_path)
    before = {p.name: p.read_bytes() for p in frozen.iterdir()}
    sealed = update_extraction_run_status(
        tmp_path, child.run_id, status=ExtractionRunStatus.REVIEWABLE,
        expected_revision=child.revision,
    )
    assert get_reviewable_extraction_run(tmp_path, child.run_id) == sealed
    resolved = resolve_promotable_ingest_run(child.run_id, root=tmp_path)
    assert resolved.candidate_graph_path == child_path
    assert resolved.source_span_index_path == frozen / "source_span_index.json"
    assert resolved.normalized_recap_path.read_bytes() == before["source.md"]
    assert {p.name: p.read_bytes() for p in frozen.iterdir()} == before
    assert get_reviewable_extraction_run(tmp_path, parent.run_id) == parent
    assert sealed.components["source_artifact"] == parent.components["source_artifact"]
    assert sealed.components["source_span_index"] == parent.components["source_span_index"]


@pytest.mark.parametrize("tamper", ["span_bytes", "span_identity"])
def test_corrected_child_rejects_substituted_frozen_evidence(tmp_path: Path, application_state_dsn: str, tamper: str):
    parent, child, frozen, child_path = _frozen_snapshot_child(tmp_path)
    components = dict(child.components)
    if tamper == "span_bytes":
        import psycopg
        with psycopg.connect(application_state_dsn) as conn:
            conn.execute("UPDATE ingest.component_payload SET payload=%s WHERE run_id=%s AND kind='source_span_index'", (b"{}", child.run_id))
    elif tamper == "span_identity":
        path = frozen / "source_span_index.json"
        payload = json.loads(path.read_text())
        payload["source_artifact_id"] = "foreign-artifact"
        path.write_text(json.dumps(payload))
        components["source_span_index"] = components["source_span_index"].model_copy(update={
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        })
    if components != child.components:
        child = create_extraction_run(
            tmp_path, source_artifact_id=parent.source_artifact_id, source_domain="worldbuilding",
            components=components, status=ExtractionRunStatus.VALIDATED,
            profile_id=parent.profile_id, lineage={"parent_run_id": parent.run_id},
        )
        _store_fixture_outputs(tmp_path, child)
    with pytest.raises(GraphRunRegistryError):
        update_extraction_run_status(
            tmp_path, child.run_id, status=ExtractionRunStatus.REVIEWABLE,
            expected_revision=child.revision,
        )
    assert get_extraction_run(tmp_path, child.run_id).status == ExtractionRunStatus.VALIDATED
    assert get_extraction_run(tmp_path, parent.run_id) == parent
