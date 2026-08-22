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
    PlayRunReferenceManifestV2,
    derive_play_run_reference_elements,
    derive_play_run_reference_elements_v2,
    detect_playable_grammar_version,
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

    tilde_fenced = "\n".join(
        [
            "<!-- dmb-playable-element:v1 kind=scene id=scene:gate -->",
            "## The Gate",
            "",
            "~~~md",
            "<!-- dmb-playable-element:v1 kind=scene id=scene:tilde -->",
            "## Tilde example",
            "~~~",
            "",
        ]
    )
    assert [
        element.element_id for element in derive_play_run_reference_elements(tilde_fenced)
    ] == ["scene:gate"]

    long_open_short_close = "\n".join(
        [
            "<!-- dmb-playable-element:v1 kind=scene id=scene:gate -->",
            "## The Gate",
            "",
            "````md",
            "<!-- dmb-playable-element:v1 kind=scene id=scene:unclosed -->",
            "## Still inside",
            "```",
            "<!-- dmb-playable-element:v1 kind=scene id=scene:leaked -->",
            "## Must not admit",
            "````",
            "",
        ]
    )
    assert [
        element.element_id
        for element in derive_play_run_reference_elements(long_open_short_close)
    ] == ["scene:gate"]

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


def test_persisted_membership_must_resolve_inside_manifest(tmp_path: Path) -> None:
    snapshot = _create_committed_runbook(tmp_path)
    _create_run(tmp_path, snapshot)
    first = seal_or_replay_play_run_reference_manifest(tmp_path, RUN_ID_A)
    original = play_run_reference_manifest_path(tmp_path, RUN_ID_A)

    missing_choice = first.model_dump(mode="json", exclude_none=True)
    for element in missing_choice["elements"]:
        if element["element_id"] == "option:fire":
            element["choice_id"] = "choice:missing"
    original.write_text(json.dumps(missing_choice) + "\n", encoding="utf-8")
    with pytest.raises(PlayRunReferenceManifestError) as missing:
        get_play_run_reference_manifest(tmp_path, RUN_ID_A)
    assert missing.value.status_code == 500

    other_scene = first.model_dump(mode="json", exclude_none=True)
    other_scene["elements"].append({"kind": "scene", "element_id": "scene:harbor"})
    other_scene["elements"].sort(key=lambda element: element["element_id"])
    for element in other_scene["elements"]:
        if element["element_id"] == "option:fire":
            element["scene_id"] = "scene:harbor"
    original.write_text(json.dumps(other_scene) + "\n", encoding="utf-8")
    with pytest.raises(PlayRunReferenceManifestError) as crossed:
        get_play_run_reference_manifest(tmp_path, RUN_ID_A)
    assert crossed.value.status_code == 500

    missing_scene = first.model_dump(mode="json", exclude_none=True)
    for element in missing_scene["elements"]:
        if element["kind"] == "beat":
            element["scene_id"] = "scene:missing"
    original.write_text(json.dumps(missing_scene) + "\n", encoding="utf-8")
    with pytest.raises(PlayRunReferenceManifestError) as beat:
        get_play_run_reference_manifest(tmp_path, RUN_ID_A)
    assert beat.value.status_code == 500
    assert original.is_file()


def test_corrupted_membership_replay_fails_without_rewriting_sidecar(
    tmp_path: Path,
) -> None:
    snapshot = _create_committed_runbook(tmp_path)
    _create_run(tmp_path, snapshot)
    first = seal_or_replay_play_run_reference_manifest(tmp_path, RUN_ID_A)
    path = play_run_reference_manifest_path(tmp_path, RUN_ID_A)
    payload = first.model_dump(mode="json", exclude_none=True)
    for element in payload["elements"]:
        if element["element_id"] == "option:fire":
            element["choice_id"] = "choice:missing"
    path.write_text(json.dumps(payload) + "\n", encoding="utf-8")
    bytes_before = path.read_bytes()

    with pytest.raises(PlayRunReferenceManifestError) as exc_info:
        seal_or_replay_play_run_reference_manifest(tmp_path, RUN_ID_A)

    assert exc_info.value.status_code == 500
    assert path.read_bytes() == bytes_before


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


# ---------------------------------------------------------------------------
# Beat-first (v2) grammar and manifest evidence
# ---------------------------------------------------------------------------

# Representative C2S27-shaped Beat/Scene/Decision/Option document (HANDOFF
# BF1 section 6.3): spine Beat with a Scene and a Decision whose Options carry
# activates/suppresses edges, an optional Beat with its own Scene, and an
# interrupt Beat.
C2S27_SHAPED_V2_MARKDOWN = "\n".join(
    [
        "# Session 27 North Gate Runbook",
        "",
        "Ordinary prose before any structural directive stays non-semantic.",
        "",
        "<!-- dmb-playable-element:v2 kind=beat id=beat:hold-the-gate beat_kind=spine -->",
        "## Hold the gate",
        "",
        "Triage at the gate line while the refugee crush builds.",
        "",
        "<!-- dmb-playable-element:v2 kind=scene id=scene:gate-line -->",
        "### The gate line",
        "",
        "Guards waver while Lysandro works the crowd.",
        "",
        "<!-- dmb-playable-element:v2 kind=choice id=choice:who-gets-through scene=scene:gate-line -->",
        "### Who gets through first?",
        "",
        "<!-- dmb-playable-element:v2 kind=option id=option:cure-line-first activates=beat:panic-breaks -->",
        "- Prioritize the cure line",
        "",
        "<!-- dmb-playable-element:v2 kind=option id=option:families-first suppresses=beat:meat-flank -->",
        "- Keep families together",
        "",
        "<!-- dmb-playable-element:v2 kind=beat id=beat:panic-breaks beat_kind=optional -->",
        "## Panic breaks",
        "",
        "<!-- dmb-playable-element:v2 kind=scene id=scene:the-crush -->",
        "### The crush",
        "",
        "The line surges against the wagons.",
        "",
        "<!-- dmb-playable-element:v2 kind=beat id=beat:meat-flank beat_kind=interrupt -->",
        "## Meat flank",
        "",
        "The sewer meat creature hits the last wagon.",
        "",
    ]
)


def test_v2_representative_document_membership_and_edges() -> None:
    assert detect_playable_grammar_version(C2S27_SHAPED_V2_MARKDOWN) == 2
    membership = derive_play_run_reference_elements_v2(C2S27_SHAPED_V2_MARKDOWN)
    assert [beat.beat_id for beat in membership.beats] == [
        "beat:hold-the-gate",
        "beat:meat-flank",
        "beat:panic-breaks",
    ]
    assert {beat.beat_id: beat.beat_kind for beat in membership.beats} == {
        "beat:hold-the-gate": "spine",
        "beat:panic-breaks": "optional",
        "beat:meat-flank": "interrupt",
    }
    assert {scene.scene_id: scene.beat_id for scene in membership.scenes} == {
        "scene:gate-line": "beat:hold-the-gate",
        "scene:the-crush": "beat:panic-breaks",
    }
    choices = {choice.choice_id: choice for choice in membership.choices}
    assert choices["choice:who-gets-through"].beat_id == "beat:hold-the-gate"
    assert choices["choice:who-gets-through"].scene_id == "scene:gate-line"
    assert {option.option_id: option.choice_id for option in membership.options} == {
        "option:cure-line-first": "choice:who-gets-through",
        "option:families-first": "choice:who-gets-through",
    }
    assert [
        (edge.option_id, edge.effect, edge.target_kind, edge.target_id)
        for edge in membership.edges
    ] == [
        ("option:cure-line-first", "activate", "beat", "beat:panic-breaks"),
        ("option:families-first", "suppress", "beat", "beat:meat-flank"),
    ]


def test_v2_fail_closed_validation() -> None:
    cases = {
        "duplicate id": "\n".join(
            [
                "<!-- dmb-playable-element:v2 kind=beat id=beat:a -->",
                "## A",
                "<!-- dmb-playable-element:v2 kind=beat id=beat:a -->",
                "## A2",
            ]
        ),
        "scene outside beat": (
            "<!-- dmb-playable-element:v2 kind=scene id=scene:s -->\n### S\n"
        ),
        "choice outside beat": (
            "<!-- dmb-playable-element:v2 kind=choice id=choice:c -->\n### C\n"
        ),
        "option outside choice": "\n".join(
            [
                "<!-- dmb-playable-element:v2 kind=beat id=beat:a -->",
                "## A",
                "<!-- dmb-playable-element:v2 kind=option id=option:o -->",
                "- go",
            ]
        ),
        "option not a list item": "\n".join(
            [
                "<!-- dmb-playable-element:v2 kind=beat id=beat:a -->",
                "## A",
                "<!-- dmb-playable-element:v2 kind=choice id=choice:c -->",
                "### C",
                "<!-- dmb-playable-element:v2 kind=option id=option:o -->",
                "plain paragraph",
            ]
        ),
        "scene association unknown": "\n".join(
            [
                "<!-- dmb-playable-element:v2 kind=beat id=beat:a -->",
                "## A",
                "<!-- dmb-playable-element:v2 kind=choice id=choice:c scene=scene:ghost -->",
                "### C",
            ]
        ),
        "scene association across beats": "\n".join(
            [
                "<!-- dmb-playable-element:v2 kind=beat id=beat:a -->",
                "## A",
                "<!-- dmb-playable-element:v2 kind=scene id=scene:s -->",
                "### S",
                "<!-- dmb-playable-element:v2 kind=beat id=beat:b -->",
                "## B",
                "<!-- dmb-playable-element:v2 kind=choice id=choice:c scene=scene:s -->",
                "### C",
            ]
        ),
        "edge to unknown id": "\n".join(
            [
                "<!-- dmb-playable-element:v2 kind=beat id=beat:a -->",
                "## A",
                "<!-- dmb-playable-element:v2 kind=choice id=choice:c -->",
                "### C",
                "<!-- dmb-playable-element:v2 kind=option id=option:o activates=beat:ghost -->",
                "- go",
            ]
        ),
        "edge to unsupported target kind": "\n".join(
            [
                "<!-- dmb-playable-element:v2 kind=beat id=beat:a -->",
                "## A",
                "<!-- dmb-playable-element:v2 kind=choice id=choice:c -->",
                "### C",
                "<!-- dmb-playable-element:v2 kind=option id=option:o activates=choice:c -->",
                "- go",
            ]
        ),
        "mixed v1 and v2 directives": "\n".join(
            [
                "<!-- dmb-playable-element:v2 kind=beat id=beat:a -->",
                "## A",
                "<!-- dmb-playable-element:v1 kind=scene id=scene:s -->",
                "## S",
            ]
        ),
        "unknown beat_kind": (
            "<!-- dmb-playable-element:v2 kind=beat id=beat:a beat_kind=weird -->\n## A\n"
        ),
        "unknown marker version": (
            "<!-- dmb-playable-element:v3 kind=beat id=beat:a -->\n## A\n"
        ),
        "activate and suppress same target": "\n".join(
            [
                "<!-- dmb-playable-element:v2 kind=beat id=beat:a -->",
                "## A",
                "<!-- dmb-playable-element:v2 kind=choice id=choice:c -->",
                "### C",
                "<!-- dmb-playable-element:v2 kind=option id=option:o activates=beat:a suppresses=beat:a -->",
                "- go",
            ]
        ),
        "scene heading at wrong level": "\n".join(
            [
                "<!-- dmb-playable-element:v2 kind=beat id=beat:a -->",
                "## A",
                "<!-- dmb-playable-element:v2 kind=scene id=scene:s -->",
                "#### S",
            ]
        ),
    }
    for name, markdown in cases.items():
        with pytest.raises(PlayRunReferenceManifestError) as excinfo:
            derive_play_run_reference_elements_v2(markdown)
        assert excinfo.value.status_code == 409, name


def test_v2_fenced_code_interiors_stay_literal() -> None:
    markdown = "\n".join(
        [
            "<!-- dmb-playable-element:v2 kind=beat id=beat:a -->",
            "## A",
            "",
            "~~~",
            "<!-- dmb-playable-element:v2 kind=scene id=scene:fake -->",
            "### Fake",
            "~~~",
            "",
            "````",
            "<!-- dmb-playable-element:v2 kind=beat id=beat:also-fake -->",
            "## Also fake",
            "````",
            "",
        ]
    )
    membership = derive_play_run_reference_elements_v2(markdown)
    assert [beat.beat_id for beat in membership.beats] == ["beat:a"]
    assert membership.scenes == []


def test_v2_seal_replay_and_binding(tmp_path: Path) -> None:
    snapshot = _create_committed_runbook(
        tmp_path, name="v2-seal", markdown=C2S27_SHAPED_V2_MARKDOWN
    )
    record = _create_run(tmp_path, snapshot)
    manifest = seal_or_replay_play_run_reference_manifest(tmp_path, record.run_id)
    assert isinstance(manifest, PlayRunReferenceManifestV2)
    assert manifest.schema_version == "dmb_play_run_reference_manifest_v2"
    assert manifest.run_id == record.run_id
    assert manifest.playable_revision == snapshot.loaded_revision
    assert manifest.playable_content_sha256 == snapshot.content_sha256
    assert len(manifest.beats) == 3
    assert len(manifest.scenes) == 2
    assert len(manifest.choices) == 1
    assert len(manifest.options) == 2
    assert len(manifest.edges) == 2

    # Replay returns the identical sealed manifest.
    replayed = seal_or_replay_play_run_reference_manifest(tmp_path, record.run_id)
    assert replayed == manifest

    # Immutable replay: advancing the workspace after seal must not change the
    # sealed sidecar, and replay must not consult current workspace state.
    _advance_runbook(tmp_path, snapshot, ADVANCED_MARKDOWN)
    loaded = get_play_run_reference_manifest(tmp_path, record.run_id)
    assert loaded == manifest


def test_v2_first_seal_refuses_when_workspace_advanced(tmp_path: Path) -> None:
    snapshot = _create_committed_runbook(
        tmp_path, name="v2-stale", markdown=C2S27_SHAPED_V2_MARKDOWN
    )
    record = _create_run(tmp_path, snapshot)
    _advance_runbook(tmp_path, snapshot, ADVANCED_MARKDOWN)
    with pytest.raises(PlayRunReferenceManifestError) as excinfo:
        seal_or_replay_play_run_reference_manifest(tmp_path, record.run_id)
    assert excinfo.value.status_code == 409
    assert not play_run_reference_manifest_path(tmp_path, record.run_id).exists()


def test_v2_seal_fails_closed_on_invalid_document(tmp_path: Path) -> None:
    snapshot = _create_committed_runbook(
        tmp_path,
        name="v2-invalid",
        markdown=(
            "<!-- dmb-playable-element:v2 kind=scene id=scene:orphan -->\n"
            "### Orphan scene outside any Beat\n"
        ),
    )
    record = _create_run(tmp_path, snapshot)
    with pytest.raises(PlayRunReferenceManifestError) as excinfo:
        seal_or_replay_play_run_reference_manifest(tmp_path, record.run_id)
    assert excinfo.value.status_code == 409
    assert not play_run_reference_manifest_path(tmp_path, record.run_id).exists()


def test_unknown_manifest_schema_version_fails_closed(tmp_path: Path) -> None:
    snapshot = _create_committed_runbook(tmp_path, name="v1-unknown-schema")
    record = _create_run(tmp_path, snapshot)
    manifest = seal_or_replay_play_run_reference_manifest(tmp_path, record.run_id)
    path = play_run_reference_manifest_path(tmp_path, record.run_id)
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["schema_version"] = "dmb_play_run_reference_manifest_v99"
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    assert manifest.run_id == record.run_id
    with pytest.raises(PlayRunReferenceManifestError):
        get_play_run_reference_manifest(tmp_path, record.run_id)


def test_v2_run_creation_and_seal_leave_progress_untouched(tmp_path: Path) -> None:
    snapshot = _create_committed_runbook(
        tmp_path, name="v2-progress", markdown=C2S27_SHAPED_V2_MARKDOWN
    )
    record = _create_run(tmp_path, snapshot)
    before = record.model_dump(mode="json")
    manifest = seal_or_replay_play_run_reference_manifest(tmp_path, record.run_id)
    assert isinstance(manifest, PlayRunReferenceManifestV2)
    after = get_play_run_reference_manifest(tmp_path, record.run_id)
    assert after == manifest
    from apps.live_control_server.services.play_run_registry import get_play_run

    reloaded = get_play_run(tmp_path, record.run_id)
    assert reloaded.model_dump(mode="json") == before
