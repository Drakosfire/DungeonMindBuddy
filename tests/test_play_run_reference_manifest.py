from __future__ import annotations

import json
from pathlib import Path
from threading import Event, Thread

import pytest

from apps.live_control_server.services import play_run_reference_manifest as manifest_mod
from apps.live_control_server.services.play_run_registry import (
    create_or_replay_play_run,
    play_run_path,
)
from apps.live_control_server.services.play_run_reference_manifest import (
    PlayRunReferenceManifestError,
    derive_play_run_reference_elements,
    get_play_run_reference_manifest,
    play_run_reference_manifest_path,
    play_run_reference_manifests_dir,
    seal_or_replay_play_run_reference_manifest,
)
from apps.live_control_server.services.tiptap_markdown_write import (
    TiptapMarkdownWriteCommitRequest,
    TiptapMarkdownWritePrepareRequest,
    commit_tiptap_markdown_write,
    prepare_tiptap_markdown_write,
)
from apps.live_control_server.services.workspace_document_registry import (
    WorkspaceDocumentRecord,
    WorkspaceDocumentSnapshot,
    create_workspace_document,
    get_workspace_document_snapshot,
    update_workspace_document_metadata,
)

RUN_ID_A = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
RUN_ID_B = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"

CANONICAL_MARKDOWN = "\n".join(
    [
        "<!-- dmb-playable-element:v1 kind=scene id=scene:gate -->",
        "## The Gate",
        "",
        "<!-- dmb-playable-element:v1 kind=beat id=beat:arrival -->",
        "### Arrival",
        "",
        "<!-- dmb-playable-element:v1 kind=choice id=choice:route -->",
        "### Which route do they take?",
        "",
        "<!-- dmb-playable-element:v1 kind=option id=option:fire -->",
        "#### Burn through the growth",
        "",
        "<!-- dmb-playable-element:v1 kind=option id=option:wait -->",
        "#### Wait and watch",
        "",
    ]
)

ADVANCED_MARKDOWN = "\n".join(
    [
        "<!-- dmb-playable-element:v1 kind=scene id=scene:harbor -->",
        "## Harbor",
        "",
        "<!-- dmb-playable-element:v1 kind=beat id=beat:dock -->",
        "### Dock",
        "",
    ]
)


def _commit_record(
    root: Path,
    record: WorkspaceDocumentRecord,
    markdown: str,
) -> WorkspaceDocumentSnapshot:
    prepared = prepare_tiptap_markdown_write(
        root=root,
        request=TiptapMarkdownWritePrepareRequest(
            document_id=record.document_id,
            markdown=markdown,
            expected_revision=record.revision,
        ),
    )
    assert prepared.writer_ok is True
    assert prepared.writer_confirm_token
    commit_tiptap_markdown_write(
        root=root,
        request=TiptapMarkdownWriteCommitRequest(
            document_id=record.document_id,
            markdown=markdown,
            writer_confirm_token=prepared.writer_confirm_token,
            expected_revision=record.revision,
        ),
    )
    return get_workspace_document_snapshot(root, record.document_id)


def _create_committed_runbook(
    root: Path,
    *,
    name: str = "reference-manifest",
    markdown: str = CANONICAL_MARKDOWN,
) -> WorkspaceDocumentSnapshot:
    record = create_workspace_document(
        root,
        title=f"Runbook {name}",
        campaign_id="longmont-c2",
        kind="runbook",
        target_relpath=(
            "evals/c2_live_prep/mireward-prep/content/tiptap/"
            f"{name}.md"
        ),
    )
    return _commit_record(root, record, markdown)


def _advance_runbook(
    root: Path,
    snapshot: WorkspaceDocumentSnapshot,
    markdown: str,
) -> WorkspaceDocumentSnapshot:
    return _commit_record(root, snapshot.record, markdown)


def _create_run(
    root: Path,
    snapshot: WorkspaceDocumentSnapshot,
    *,
    run_id: str = RUN_ID_A,
):
    return create_or_replay_play_run(
        root,
        run_id=run_id,
        playable_artifact_id=snapshot.record.document_id,
        expected_playable_revision=snapshot.loaded_revision,
        expected_playable_content_sha256=snapshot.content_sha256,
    )


def test_canonical_four_kind_parse_is_ids_and_membership_only() -> None:
    elements = derive_play_run_reference_elements(CANONICAL_MARKDOWN)
    by_id = {element.element_id: element for element in elements}
    assert set(by_id) == {
        "scene:gate",
        "beat:arrival",
        "choice:route",
        "option:fire",
        "option:wait",
    }
    assert by_id["scene:gate"].kind == "scene"
    assert by_id["scene:gate"].scene_id is None
    assert by_id["beat:arrival"].scene_id == "scene:gate"
    assert by_id["choice:route"].scene_id == "scene:gate"
    assert by_id["option:fire"].scene_id == "scene:gate"
    assert by_id["option:fire"].choice_id == "choice:route"
    assert by_id["option:wait"].choice_id == "choice:route"
    dumped = [element.model_dump(exclude_none=True) for element in elements]
    assert all("title" not in item and "text" not in item for item in dumped)


def test_malformed_orphan_and_level_mismatch_block() -> None:
    with pytest.raises(PlayRunReferenceManifestError) as malformed:
        derive_play_run_reference_elements(
            "<!-- dmb-playable-element:v1 kind=scene -->\n## Arrival\n"
        )
    assert malformed.value.status_code == 409

    with pytest.raises(PlayRunReferenceManifestError) as orphan:
        derive_play_run_reference_elements(
            "<!-- dmb-playable-element:v1 kind=scene id=scene:gate -->\n\n## The Gate\n"
        )
    assert orphan.value.status_code == 409

    with pytest.raises(PlayRunReferenceManifestError) as level:
        derive_play_run_reference_elements(
            "<!-- dmb-playable-element:v1 kind=scene id=scene:gate -->\n### Arrival\n"
        )
    assert level.value.status_code == 409


def test_duplicate_id_and_orphan_membership_block() -> None:
    with pytest.raises(PlayRunReferenceManifestError):
        derive_play_run_reference_elements(
            "\n".join(
                [
                    "<!-- dmb-playable-element:v1 kind=scene id=scene:gate -->",
                    "## One",
                    "",
                    "<!-- dmb-playable-element:v1 kind=scene id=scene:gate -->",
                    "## Two",
                    "",
                ]
            )
        )
    with pytest.raises(PlayRunReferenceManifestError):
        derive_play_run_reference_elements(
            "<!-- dmb-playable-element:v1 kind=beat id=beat:arrival -->\n### Arrival\n"
        )
    with pytest.raises(PlayRunReferenceManifestError):
        derive_play_run_reference_elements(
            "<!-- dmb-playable-element:v1 kind=choice id=choice:route -->\n### Route\n"
        )
    with pytest.raises(PlayRunReferenceManifestError):
        derive_play_run_reference_elements(
            "\n".join(
                [
                    "<!-- dmb-playable-element:v1 kind=scene id=scene:gate -->",
                    "## Gate",
                    "",
                    "<!-- dmb-playable-element:v1 kind=option id=option:fire -->",
                    "#### Fire",
                    "",
                ]
            )
        )


def test_fenced_marker_is_literal_and_near_marker_outside_fence_blocks() -> None:
    fenced = "\n".join(
        [
            "<!-- dmb-playable-element:v1 kind=scene id=scene:gate -->",
            "## The Gate",
            "",
            "```md",
            "<!-- dmb-playable-element:v1 kind=scene id=scene:example -->",
            "## Example",
            "```",
            "",
        ]
    )
    elements = derive_play_run_reference_elements(fenced)
    assert [element.element_id for element in elements] == ["scene:gate"]

    with pytest.raises(PlayRunReferenceManifestError):
        derive_play_run_reference_elements(
            "> <!-- dmb-playable-element:v1 kind=scene id=scene:gate -->\n> ## Arrival\n"
        )
    with pytest.raises(PlayRunReferenceManifestError):
        derive_play_run_reference_elements(
            "  <!-- dmb-playable-element:v1 kind=scene id=scene:gate -->\n## Arrival\n"
        )


def test_exact_first_seal_persists_without_mutating_run_or_runbook(tmp_path: Path) -> None:
    snapshot_before = _create_committed_runbook(tmp_path)
    record = _create_run(tmp_path, snapshot_before)
    run_bytes_before = play_run_path(tmp_path, RUN_ID_A).read_bytes()

    manifest = seal_or_replay_play_run_reference_manifest(tmp_path, RUN_ID_A)

    path = play_run_reference_manifest_path(tmp_path, RUN_ID_A)
    assert path == tmp_path / "out/runtime/play/reference-manifests" / f"{RUN_ID_A}.json"
    assert path.is_file()
    assert manifest.run_id == record.run_id
    assert manifest.playable_artifact_id == record.playable_artifact_id
    assert manifest.playable_revision == record.playable_revision
    assert manifest.playable_content_sha256 == record.playable_content_sha256
    assert [element.element_id for element in manifest.elements] == sorted(
        ["scene:gate", "beat:arrival", "choice:route", "option:fire", "option:wait"]
    )
    raw = json.loads(path.read_text(encoding="utf-8"))
    assert set(raw) == {
        "schema_version",
        "run_id",
        "playable_artifact_id",
        "playable_revision",
        "playable_content_sha256",
        "elements",
        "sealed_at",
    }
    assert all(
        set(element) <= {"kind", "element_id", "scene_id", "choice_id"}
        for element in raw["elements"]
    )
    assert "The Gate" not in path.read_text(encoding="utf-8")
    assert play_run_path(tmp_path, RUN_ID_A).read_bytes() == run_bytes_before

    snapshot_after = get_workspace_document_snapshot(
        tmp_path,
        snapshot_before.record.document_id,
    )
    assert snapshot_after.loaded_revision == snapshot_before.loaded_revision
    assert snapshot_after.content_sha256 == snapshot_before.content_sha256
    assert snapshot_after.markdown == snapshot_before.markdown

    reloaded = get_play_run_reference_manifest(tmp_path, RUN_ID_A)
    assert reloaded == manifest


def test_identical_replay_returns_existing_bytes_and_skips_workspace(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    snapshot = _create_committed_runbook(tmp_path)
    _create_run(tmp_path, snapshot)
    first = seal_or_replay_play_run_reference_manifest(tmp_path, RUN_ID_A)
    path = play_run_reference_manifest_path(tmp_path, RUN_ID_A)
    bytes_before = path.read_bytes()

    def boom(*args: object, **kwargs: object) -> None:
        raise AssertionError("replay must not read current workspace state")

    monkeypatch.setattr(manifest_mod, "get_workspace_document_snapshot_unlocked", boom)
    second = seal_or_replay_play_run_reference_manifest(tmp_path, RUN_ID_A)

    assert second == first
    assert path.read_bytes() == bytes_before


def test_replay_after_runbook_advance_does_not_reread_workspace(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    snapshot = _create_committed_runbook(tmp_path)
    record = _create_run(tmp_path, snapshot)
    first = seal_or_replay_play_run_reference_manifest(tmp_path, RUN_ID_A)
    bytes_before = play_run_reference_manifest_path(tmp_path, RUN_ID_A).read_bytes()

    advanced = _advance_runbook(tmp_path, snapshot, ADVANCED_MARKDOWN)
    assert advanced.loaded_revision > snapshot.loaded_revision
    assert "scene:harbor" in advanced.markdown

    def boom(*args: object, **kwargs: object) -> None:
        raise AssertionError("replay after advance must not consult current workspace")

    monkeypatch.setattr(manifest_mod, "get_workspace_document_snapshot_unlocked", boom)
    replayed = seal_or_replay_play_run_reference_manifest(tmp_path, RUN_ID_A)

    assert replayed == first
    assert replayed.playable_revision == record.playable_revision
    assert "scene:harbor" not in {
        element.element_id for element in replayed.elements
    }
    assert play_run_reference_manifest_path(tmp_path, RUN_ID_A).read_bytes() == bytes_before


def test_runbook_advance_before_first_seal_refuses_without_sidecar(tmp_path: Path) -> None:
    old = _create_committed_runbook(tmp_path, name="stale-manifest")
    record = _create_run(tmp_path, old)
    current = _advance_runbook(tmp_path, old, ADVANCED_MARKDOWN)
    assert current.loaded_revision == old.loaded_revision + 1

    with pytest.raises(PlayRunReferenceManifestError) as exc_info:
        seal_or_replay_play_run_reference_manifest(tmp_path, RUN_ID_A)

    assert exc_info.value.status_code == 409
    assert not play_run_reference_manifest_path(tmp_path, record.run_id).exists()
    assert not play_run_reference_manifests_dir(tmp_path).exists() or not any(
        play_run_reference_manifests_dir(tmp_path).glob("*.json")
    )


def test_get_absent_does_not_create(tmp_path: Path) -> None:
    snapshot = _create_committed_runbook(tmp_path)
    _create_run(tmp_path, snapshot)

    with pytest.raises(PlayRunReferenceManifestError) as exc_info:
        get_play_run_reference_manifest(tmp_path, RUN_ID_A)

    assert exc_info.value.status_code == 404
    assert not play_run_reference_manifest_path(tmp_path, RUN_ID_A).exists()


def test_unknown_and_invalid_run_ids_fail_closed(tmp_path: Path) -> None:
    with pytest.raises(Exception) as unknown:
        seal_or_replay_play_run_reference_manifest(tmp_path, RUN_ID_A)
    assert unknown.value.status_code == 404

    with pytest.raises(Exception) as invalid:
        seal_or_replay_play_run_reference_manifest(tmp_path, "not-a-uuid")
    assert invalid.value.status_code == 422


def test_filename_and_binding_mismatch_fail_closed(tmp_path: Path) -> None:
    snapshot = _create_committed_runbook(tmp_path)
    record = _create_run(tmp_path, snapshot)
    first = seal_or_replay_play_run_reference_manifest(tmp_path, RUN_ID_A)
    original = play_run_reference_manifest_path(tmp_path, RUN_ID_A)
    payload = first.model_dump(mode="json", exclude_none=True)
    payload["run_id"] = RUN_ID_B
    original.write_text(json.dumps(payload) + "\n", encoding="utf-8")

    with pytest.raises(PlayRunReferenceManifestError) as renamed:
        get_play_run_reference_manifest(tmp_path, RUN_ID_A)
    assert renamed.value.status_code == 500

    payload = first.model_dump(mode="json", exclude_none=True)
    payload["playable_revision"] = record.playable_revision + 9
    original.write_text(json.dumps(payload) + "\n", encoding="utf-8")
    with pytest.raises(PlayRunReferenceManifestError) as binding:
        get_play_run_reference_manifest(tmp_path, RUN_ID_A)
    assert binding.value.status_code == 500
    assert original.is_file()


def test_corrupt_manifest_fails_closed_without_rebuild(tmp_path: Path) -> None:
    snapshot = _create_committed_runbook(tmp_path)
    _create_run(tmp_path, snapshot)
    path = play_run_reference_manifest_path(tmp_path, RUN_ID_A)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{not-json", encoding="utf-8")

    with pytest.raises(PlayRunReferenceManifestError) as exc_info:
        get_play_run_reference_manifest(tmp_path, RUN_ID_A)
    assert exc_info.value.status_code == 500
    assert path.read_text(encoding="utf-8") == "{not-json"


def test_seal_holds_runbook_mutation_lock_through_atomic_write(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    snapshot = _create_committed_runbook(tmp_path)
    record = _create_run(tmp_path, snapshot)
    write_entered = Event()
    allow_write = Event()
    mutation_started = Event()
    mutation_done = Event()
    seal_errors: list[BaseException] = []
    mutation_errors: list[BaseException] = []
    sealed = []
    real_write_json = manifest_mod.write_json

    def blocking_write_json(path: Path, data: object) -> None:
        write_entered.set()
        if not allow_write.wait(timeout=2.0):
            raise AssertionError("timed out waiting to release manifest write")
        real_write_json(path, data)

    monkeypatch.setattr(manifest_mod, "write_json", blocking_write_json)

    def seal() -> None:
        try:
            sealed.append(seal_or_replay_play_run_reference_manifest(tmp_path, RUN_ID_A))
        except BaseException as exc:  # pragma: no cover - surfaced below
            seal_errors.append(exc)

    def mutate_runbook() -> None:
        mutation_started.set()
        try:
            update_workspace_document_metadata(
                tmp_path,
                snapshot.record.document_id,
                title="Advanced after manifest seal",
                expected_revision=snapshot.loaded_revision,
            )
        except BaseException as exc:  # pragma: no cover - surfaced below
            mutation_errors.append(exc)
        finally:
            mutation_done.set()

    seal_thread = Thread(target=seal, daemon=True)
    seal_thread.start()
    assert write_entered.wait(timeout=2.0)

    mutation_thread = Thread(target=mutate_runbook, daemon=True)
    mutation_thread.start()
    assert mutation_started.wait(timeout=2.0)

    try:
        assert not mutation_done.wait(timeout=0.1)
    finally:
        allow_write.set()

    seal_thread.join(timeout=2.0)
    mutation_thread.join(timeout=2.0)

    assert not seal_thread.is_alive()
    assert not mutation_thread.is_alive()
    assert seal_errors == []
    assert mutation_errors == []
    assert len(sealed) == 1
    assert sealed[0].playable_revision == record.playable_revision
    assert sealed[0].playable_content_sha256 == record.playable_content_sha256
