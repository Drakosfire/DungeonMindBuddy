from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from apps.live_control_server.services.graph_run_registry import (
    GraphRunRegistryError,
    create_extraction_run,
    get_extraction_run,
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


def test_malformed_registry_fails_closed_on_load(tmp_path: Path) -> None:
    record, _digest = _committed_worldbuilding(tmp_path)
    artifact = create_source_artifact_from_workspace_document(
        tmp_path,
        document_id=record.document_id,
        expected_revision=record.revision,
    )
    create_extraction_run(
        tmp_path,
        source_artifact_id=artifact.source_artifact_id,
        source_domain="worldbuilding",
    )
    runs_path = tmp_path / "out/registries/extraction_runs.json"
    payload = json.loads(runs_path.read_text(encoding="utf-8"))
    payload["records"][0]["session_id"] = "session-1"
    runs_path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(GraphRunRegistryError, match="malformed"):
        get_extraction_run(tmp_path, payload["records"][0]["run_id"])


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

    def boom_write_json(_path: Path, _data: object) -> None:
        raise OSError("simulated registry save failure")

    monkeypatch.setattr(
        "apps.live_control_server.services.graph_run_registry.write_json",
        boom_write_json,
    )
    with pytest.raises(OSError, match="simulated registry save failure"):
        supersede_extraction_run(
            tmp_path,
            prepared.run_id,
            expected_revision=prepared.revision,
        )

    monkeypatch.undo()
    predecessor = get_extraction_run(tmp_path, prepared.run_id)
    assert predecessor.status == ExtractionRunStatus.PREPARED
    assert predecessor.superseded_by_run_id is None
    assert predecessor.revision == prepared.revision
    runs_path = tmp_path / "out/registries/extraction_runs.json"
    payload = json.loads(runs_path.read_text(encoding="utf-8"))
    assert len(payload["records"]) == 1
    assert payload["records"][0]["run_id"] == prepared.run_id


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
    with pytest.raises(GraphRunRegistryError, match="integrity|digest mismatch"):
        get_extraction_run(tmp_path, promoted.run_id)


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


def test_one_sided_supersession_fails_closed_on_load(tmp_path: Path) -> None:
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
    runs_path = tmp_path / "out/registries/extraction_runs.json"
    payload = json.loads(runs_path.read_text(encoding="utf-8"))
    for row in payload["records"]:
        if row["run_id"] == prepared.run_id:
            row["superseded_by_run_id"] = None
            row["status"] = "prepared"
        if row["run_id"] == successor.run_id:
            # Keep successor pointer so lineage is one-sided.
            pass
    runs_path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(GraphRunRegistryError, match="lineage|non-reciprocal|missing"):
        get_extraction_run(tmp_path, successor.run_id)
