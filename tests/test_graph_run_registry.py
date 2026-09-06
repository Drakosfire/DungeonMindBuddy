from __future__ import annotations

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
    source_span_index_relpath,
)
from apps.live_control_server.services.workspace_document_registry import (
    create_workspace_document,
    mark_workspace_document_committed,
)
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
    target = root / record.target_relpath
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _committed_worldbuilding(root: Path, markdown: str = "# Lore\n\nBody.\n"):
    record = create_workspace_document(
        root,
        title="Lore",
        campaign_id="eldyrwild",
        kind="worldbuilding_source",
        source_domain="worldbuilding",
        document_class="lore",
        authority_state="draft",
        visibility_state="internal",
    )
    committed = mark_workspace_document_committed(
        root, record.document_id, expected_revision=1
    )
    digest = _write_committed_markdown(root, committed, markdown)
    return committed, digest


def _reviewable_components(root: Path, artifact, graph_payload: dict | None = None):
    source_path = root / artifact.uri.removeprefix("repo://")
    source_digest = hashlib.sha256(source_path.read_bytes()).hexdigest()
    span_rel = source_span_index_relpath(artifact.source_artifact_id)
    span_path = root / span_rel
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


def test_source_artifact_reads_committed_file_not_client_markdown(tmp_path: Path) -> None:
    record, digest = _committed_worldbuilding(tmp_path, "# Canon\n\nFrom disk.\n")
    artifact = create_source_artifact_from_workspace_document(
        tmp_path,
        document_id=record.document_id,
        expected_revision=record.revision,
    )
    assert artifact.content_sha256 == digest
    assert artifact.uri.endswith(record.target_relpath)
    assert artifact.session_id is None
    loaded = get_source_artifact(tmp_path, artifact.source_artifact_id)
    assert loaded.source_artifact_id == artifact.source_artifact_id


def test_source_artifact_rejects_missing_committed_target(tmp_path: Path) -> None:
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
    with pytest.raises(SourceArtifactRegistryError, match="missing"):
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

    # Corrupt registry foreign key while keeping the same id prefix path.
    registry_path = tmp_path / "out/registries/source_artifacts.json"
    payload = json.loads(registry_path.read_text(encoding="utf-8"))
    payload["records"][0]["campaign_id"] = "other-world"
    registry_path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(SourceArtifactRegistryError, match="collision|malformed|campaign"):
        create_source_artifact_from_workspace_document(
            tmp_path,
            document_id=record.document_id,
            expected_revision=record.revision,
        )


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


def test_reviewable_rejects_unknown_paths_and_hash_mismatch(tmp_path: Path) -> None:
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
    components = _reviewable_components(tmp_path, artifact)
    components["candidate_graph"] = ExtractionRunComponentRef(
        kind=ExtractionRunComponentKind.CANDIDATE_GRAPH,
        uri="repo://../escape.json",
        sha256="a" * 64,
    )
    prepared = update_extraction_run_status(
        tmp_path,
        run.run_id,
        status=ExtractionRunStatus.PREPARED,
        expected_revision=run.revision,
        components=components,
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
    with pytest.raises(GraphRunRegistryError, match="unsafe|escape"):
        update_extraction_run_status(
            tmp_path,
            validated.run_id,
            status=ExtractionRunStatus.REVIEWABLE,
            expected_revision=validated.revision,
        )

    components = _reviewable_components(tmp_path, artifact)
    components["candidate_graph"] = components["candidate_graph"].model_copy(
        update={"sha256": "0" * 64}
    )
    run2 = create_extraction_run(
        tmp_path,
        source_artifact_id=artifact.source_artifact_id,
        source_domain="worldbuilding",
        components=components,
    )
    prepared2 = update_extraction_run_status(
        tmp_path,
        run2.run_id,
        status=ExtractionRunStatus.PREPARED,
        expected_revision=run2.revision,
    )
    extracted2 = update_extraction_run_status(
        tmp_path,
        prepared2.run_id,
        status=ExtractionRunStatus.EXTRACTED,
        expected_revision=prepared2.revision,
    )
    validated2 = update_extraction_run_status(
        tmp_path,
        extracted2.run_id,
        status=ExtractionRunStatus.VALIDATED,
        expected_revision=extracted2.revision,
    )
    with pytest.raises(GraphRunRegistryError, match="digest mismatch"):
        update_extraction_run_status(
            tmp_path,
            validated2.run_id,
            status=ExtractionRunStatus.REVIEWABLE,
            expected_revision=validated2.revision,
        )


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


def _advance_to_reviewable(tmp_path: Path, run, components):
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


def test_promoted_run_integrity_checked_on_load(tmp_path: Path) -> None:
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

    with pytest.raises(GraphRunRegistryError, match="integrity|digest mismatch"):
        assert_run_reviewable_evidence(tmp_path, catalog)


def test_whitespace_contaminated_component_uri_is_rejected(tmp_path: Path) -> None:
    record, _digest = _committed_worldbuilding(tmp_path)
    artifact = create_source_artifact_from_workspace_document(
        tmp_path,
        document_id=record.document_id,
        expected_revision=record.revision,
    )
    components = _reviewable_components(tmp_path, artifact)
    components["candidate_graph"] = components["candidate_graph"].model_copy(
        update={"uri": " repo://out/registries/test_candidate_graph.json "}
    )
    run = create_extraction_run(
        tmp_path,
        source_artifact_id=artifact.source_artifact_id,
        source_domain="worldbuilding",
        components=components,
    )
    prepared = update_extraction_run_status(
        tmp_path,
        run.run_id,
        status=ExtractionRunStatus.PREPARED,
        expected_revision=run.revision,
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
    with pytest.raises(GraphRunRegistryError, match="unsafe component uri"):
        update_extraction_run_status(
            tmp_path,
            validated.run_id,
            status=ExtractionRunStatus.REVIEWABLE,
            expected_revision=validated.revision,
        )


def test_source_artifact_snapshot_waits_across_commit_barrier(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Artifact creation must not observe target bytes between write and registry commit."""
    import threading

    from apps.live_control_server.services.tiptap_markdown_write import (
        TiptapMarkdownWriteCommitRequest,
        TiptapMarkdownWritePrepareRequest,
        commit_tiptap_markdown_write,
        prepare_tiptap_markdown_write,
    )
    from apps.live_control_server.services.workspace_document_registry import (
        mark_workspace_document_committed_unlocked,
    )

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
    v1 = "# Lore\n\nRevision one.\n"
    prepared_v1 = prepare_tiptap_markdown_write(
        root=tmp_path,
        request=TiptapMarkdownWritePrepareRequest(
            document_id=record.document_id,
            markdown=v1,
            expected_revision=1,
        ),
    )
    committed_v1 = commit_tiptap_markdown_write(
        root=tmp_path,
        request=TiptapMarkdownWriteCommitRequest(
            document_id=record.document_id,
            markdown=v1,
            writer_confirm_token=prepared_v1.writer_confirm_token or "",
            expected_revision=1,
        ),
    )
    prior_revision = committed_v1.registry_revision
    prior_digest = hashlib.sha256(v1.encode("utf-8")).hexdigest()

    v2 = "# Lore\n\nRevision two.\n"
    prepared_v2 = prepare_tiptap_markdown_write(
        root=tmp_path,
        request=TiptapMarkdownWritePrepareRequest(
            document_id=record.document_id,
            markdown=v2,
            expected_revision=prior_revision,
        ),
    )

    entered_mark = threading.Event()
    release_mark = threading.Event()
    real_mark = mark_workspace_document_committed_unlocked

    def delayed_mark(*args, **kwargs):
        entered_mark.set()
        assert release_mark.wait(timeout=5), "timed out waiting to release commit barrier"
        return real_mark(*args, **kwargs)

    monkeypatch.setattr(
        "apps.live_control_server.services.tiptap_markdown_write.mark_workspace_document_committed_unlocked",
        delayed_mark,
    )

    commit_errors: list[BaseException] = []
    commit_result: list[object] = []

    def commit_worker() -> None:
        try:
            commit_result.append(
                commit_tiptap_markdown_write(
                    root=tmp_path,
                    request=TiptapMarkdownWriteCommitRequest(
                        document_id=record.document_id,
                        markdown=v2,
                        writer_confirm_token=prepared_v2.writer_confirm_token or "",
                        expected_revision=prior_revision,
                    ),
                )
            )
        except BaseException as exc:  # noqa: BLE001 - surface to main thread
            commit_errors.append(exc)

    commit_thread = threading.Thread(target=commit_worker)
    commit_thread.start()
    assert entered_mark.wait(timeout=5), "commit never reached post-write registry mark"

    # Target already has v2 bytes, but registry still reports prior_revision.
    target_path = tmp_path / record.target_relpath
    assert target_path.read_text(encoding="utf-8") == v2
    from apps.live_control_server.services.workspace_document_registry import (
        get_workspace_document,
    )

    assert get_workspace_document(tmp_path, record.document_id).revision == prior_revision

    snapshot_started = threading.Event()
    snapshot_done = threading.Event()
    snapshot_errors: list[BaseException] = []
    snapshot_result: list[object] = []

    def snapshot_worker() -> None:
        snapshot_started.set()
        try:
            snapshot_result.append(
                create_source_artifact_from_workspace_document(
                    tmp_path,
                    document_id=record.document_id,
                    expected_revision=prior_revision,
                )
            )
        except BaseException as exc:  # noqa: BLE001 - surface to main thread
            snapshot_errors.append(exc)
        finally:
            snapshot_done.set()

    snapshot_thread = threading.Thread(target=snapshot_worker)
    snapshot_thread.start()
    assert snapshot_started.wait(timeout=5)
    # Snapshot must block on the shared document lock while commit is between write and mark.
    assert not snapshot_done.wait(timeout=0.3)

    release_mark.set()
    commit_thread.join(timeout=5)
    snapshot_thread.join(timeout=5)
    assert not commit_thread.is_alive()
    assert not snapshot_thread.is_alive()
    assert not commit_errors
    assert commit_result

    # After commit, prior_revision is stale; snapshot must not certify v2 bytes as prior_revision.
    assert not snapshot_result
    assert snapshot_errors
    assert isinstance(snapshot_errors[0], SourceArtifactRegistryError)
    assert "revision mismatch" in str(snapshot_errors[0])

    committed_v2_revision = commit_result[0].registry_revision
    artifact = create_source_artifact_from_workspace_document(
        tmp_path,
        document_id=record.document_id,
        expected_revision=committed_v2_revision,
    )
    assert artifact.workspace_document_revision == committed_v2_revision
    assert artifact.content_sha256 == hashlib.sha256(v2.encode("utf-8")).hexdigest()
    assert artifact.content_sha256 != prior_digest


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


def test_source_artifact_snapshot_blocks_concurrent_discard(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Discard cannot change status while a snapshot holds the document lock."""
    import threading

    from apps.live_control_server.services import source_artifact_registry as sar
    from apps.live_control_server.services.workspace_document_registry import (
        discard_workspace_document,
        get_workspace_document,
    )

    record, _digest = _committed_worldbuilding(tmp_path)
    entered_read = threading.Event()
    release_read = threading.Event()
    real_read_fn = sar._read_committed_target_markdown

    def delayed_read(*args, **kwargs):
        entered_read.set()
        assert release_read.wait(timeout=5), "timed out waiting to release snapshot barrier"
        return real_read_fn(*args, **kwargs)

    monkeypatch.setattr(sar, "_read_committed_target_markdown", delayed_read)

    snapshot_errors: list[BaseException] = []
    snapshot_result: list[object] = []

    def snapshot_worker() -> None:
        try:
            snapshot_result.append(
                create_source_artifact_from_workspace_document(
                    tmp_path,
                    document_id=record.document_id,
                    expected_revision=record.revision,
                )
            )
        except BaseException as exc:  # noqa: BLE001 - surface to main thread
            snapshot_errors.append(exc)

    snapshot_thread = threading.Thread(target=snapshot_worker)
    snapshot_thread.start()
    assert entered_read.wait(timeout=5)

    discard_started = threading.Event()
    discard_done = threading.Event()
    discard_errors: list[BaseException] = []
    discard_result: list[object] = []

    def discard_worker() -> None:
        discard_started.set()
        try:
            discard_result.append(
                discard_workspace_document(
                    tmp_path,
                    record.document_id,
                    expected_revision=record.revision,
                )
            )
        except BaseException as exc:  # noqa: BLE001 - surface to main thread
            discard_errors.append(exc)
        finally:
            discard_done.set()

    discard_thread = threading.Thread(target=discard_worker)
    discard_thread.start()
    assert discard_started.wait(timeout=5)
    # Discard must block on the shared document lock while snapshot is mid-flight.
    assert not discard_done.wait(timeout=0.3)
    assert get_workspace_document(tmp_path, record.document_id).status == "active"

    release_read.set()
    snapshot_thread.join(timeout=5)
    discard_thread.join(timeout=5)
    assert not snapshot_thread.is_alive()
    assert not discard_thread.is_alive()
    assert not snapshot_errors
    assert snapshot_result
    assert snapshot_result[0].workspace_document_revision == record.revision
    assert not discard_errors
    assert discard_result[0].status == "discarded"
    assert get_workspace_document(tmp_path, record.document_id).status == "discarded"

    with pytest.raises(SourceArtifactRegistryError, match="discarded"):
        create_source_artifact_from_workspace_document(
            tmp_path,
            document_id=record.document_id,
            expected_revision=discard_result[0].revision,
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
        campaign_id="longmont-c2",
        session_id="session-23",
        recap_text=recap_text,
    )
    source_path = tmp_path / artifact.uri.removeprefix("repo://")
    source_digest = hashlib.sha256(source_path.read_bytes()).hexdigest()
    uri = component_uri or artifact.uri
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


def test_historical_recap_inspection_reads_validated_run(tmp_path: Path) -> None:
    from apps.live_control_server.services.graph_run_registry import (
        get_historical_recap_inspection,
    )

    run, _artifact, _source_path = _validated_recap_run(tmp_path)
    before = get_extraction_run(tmp_path, run.run_id)
    inspection = get_historical_recap_inspection(tmp_path, run.run_id)
    after = get_extraction_run(tmp_path, run.run_id)

    assert inspection.source_status == "available"
    assert inspection.run_status == "validated"
    assert "# Session Recap" in (inspection.source_prose or "")
    assert inspection.source_uri
    assert inspection.source_sha256
    assert before.model_dump() == after.model_dump()


def test_historical_recap_inspection_does_not_require_source_registry(
    tmp_path: Path,
) -> None:
    from apps.live_control_server.services.graph_run_registry import (
        get_historical_recap_inspection,
    )
    from apps.live_control_server.services.source_artifact_registry import (
        source_artifacts_path,
    )

    run, _artifact, source_path = _validated_recap_run(tmp_path)
    source_registry_path = source_artifacts_path(tmp_path)
    source_registry_path.unlink()

    inspection = get_historical_recap_inspection(tmp_path, run.run_id)

    assert source_path.is_file()
    assert inspection.source_status == "available"
    assert inspection.source_prose == "# Session Recap\n\nA paragraph.\n"


def test_historical_recap_inspection_reads_prepared_run(tmp_path: Path) -> None:
    from apps.live_control_server.services.graph_run_registry import (
        get_historical_recap_inspection,
    )

    run, _artifact, _source_path = _validated_recap_run(
        tmp_path, status=ExtractionRunStatus.PREPARED
    )
    inspection = get_historical_recap_inspection(tmp_path, run.run_id)
    assert inspection.source_status == "available"
    assert inspection.run_status == "prepared"


def test_historical_recap_inspection_missing_source_is_unavailable(tmp_path: Path) -> None:
    from apps.live_control_server.services.graph_run_registry import (
        get_historical_recap_inspection,
    )

    run, _artifact, source_path = _validated_recap_run(tmp_path)
    source_path.unlink()
    inspection = get_historical_recap_inspection(tmp_path, run.run_id)
    assert inspection.source_status == "unavailable"
    assert inspection.source_prose is None
    assert "not available" in (inspection.unavailable_reason or "")


def test_historical_recap_inspection_does_not_fallback_to_sibling_bytes(
    tmp_path: Path,
) -> None:
    from apps.live_control_server.services.graph_run_registry import (
        get_historical_recap_inspection,
    )
    from apps.live_control_server.services.source_artifact_registry import (
        create_recap_source_artifact,
    )

    sibling = create_recap_source_artifact(
        tmp_path,
        campaign_id="longmont-c2",
        session_id="session-23",
        recap_text="# Sibling recap\n\nDifferent bytes.\n",
    )
    run, _artifact, _source_path = _validated_recap_run(
        tmp_path,
        component_uri="repo://out/registries/missing/recap.md",
        component_digest=hashlib.sha256(b"missing").hexdigest(),
    )
    sibling_path = tmp_path / sibling.uri.removeprefix("repo://")
    assert sibling_path.is_file()
    missing_path = tmp_path / "out/registries/missing/recap.md"
    assert not missing_path.is_file()

    inspection = get_historical_recap_inspection(tmp_path, run.run_id)
    assert inspection.source_status == "unavailable"
    assert inspection.source_prose is None


def test_historical_recap_inspection_missing_digest_is_unavailable(tmp_path: Path) -> None:
    from apps.live_control_server.services.graph_run_registry import (
        get_historical_recap_inspection,
    )

    run, _artifact, _source_path = _validated_recap_run(tmp_path, component_digest=None)
    inspection = get_historical_recap_inspection(tmp_path, run.run_id)
    assert inspection.source_status == "unavailable"
    assert "digest" in (inspection.unavailable_reason or "")


def test_historical_recap_inspection_unsafe_uri_fails_closed(tmp_path: Path) -> None:
    from apps.live_control_server.services.graph_run_registry import (
        get_historical_recap_inspection,
    )

    run, _artifact, _source_path = _validated_recap_run(
        tmp_path, component_uri="repo://../escape.md"
    )
    with pytest.raises(GraphRunRegistryError, match="unsafe"):
        get_historical_recap_inspection(tmp_path, run.run_id)


def test_historical_recap_inspection_digest_mismatch_fails_closed(tmp_path: Path) -> None:
    from apps.live_control_server.services.graph_run_registry import (
        get_historical_recap_inspection,
    )

    run, _artifact, _source_path = _validated_recap_run(
        tmp_path, component_digest="f" * 64
    )
    with pytest.raises(GraphRunRegistryError, match="digest mismatch"):
        get_historical_recap_inspection(tmp_path, run.run_id)


def test_historical_recap_inspection_unknown_run_is_404(tmp_path: Path) -> None:
    from apps.live_control_server.services.graph_run_registry import (
        get_historical_recap_inspection,
    )

    with pytest.raises(GraphRunRegistryError, match="not found|missing"):
        get_historical_recap_inspection(tmp_path, "missing-run")


def test_historical_recap_inspection_rejects_worldbuilding_run(tmp_path: Path) -> None:
    from apps.live_control_server.services.graph_run_registry import (
        get_historical_recap_inspection,
    )

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
    with pytest.raises(GraphRunRegistryError, match="not applicable"):
        get_historical_recap_inspection(tmp_path, run.run_id)


def test_get_reviewable_extraction_run_still_rejects_validated(tmp_path: Path) -> None:
    run, _artifact, _source_path = _validated_recap_run(tmp_path)
    with pytest.raises(GraphRunRegistryError, match="not reviewable"):
        get_reviewable_extraction_run(tmp_path, run.run_id)
