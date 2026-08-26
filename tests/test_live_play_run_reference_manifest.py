from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from apps.live_control_server.main import create_app
from apps.live_control_server.services.play_run_registry import play_run_path
from apps.live_control_server.services.play_run_reference_manifest import (
    get_play_run_reference_manifest,
    play_run_reference_manifest_path,
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
    get_committed_playable_revision,
    get_workspace_document_snapshot,
)

pytest_plugins = ["tests.application_state.conftest"]

_PLAYABLE_BY_SHA: dict[tuple[str, str], int] = {}


@pytest.fixture(autouse=True)
def _application_state(application_state_dsn: str) -> str:
    _PLAYABLE_BY_SHA.clear()
    return application_state_dsn


def _remember_playable(snapshot: WorkspaceDocumentSnapshot) -> WorkspaceDocumentSnapshot:
    if snapshot.record.kind != "runbook":
        return snapshot
    committed = get_committed_playable_revision(snapshot.record.document_id, kind=None)
    if committed.content_sha256 == snapshot.content_sha256:
        _PLAYABLE_BY_SHA[(snapshot.record.document_id, snapshot.content_sha256)] = (
            committed.revision_n
        )
    return snapshot


def _playable(snapshot: WorkspaceDocumentSnapshot) -> tuple[int, str]:
    key = (snapshot.record.document_id, snapshot.content_sha256)
    remembered = _PLAYABLE_BY_SHA.get(key)
    if remembered is not None:
        return remembered, snapshot.content_sha256
    committed = get_committed_playable_revision(snapshot.record.document_id, kind=None)
    return committed.revision_n, committed.content_sha256


RUN_ID_A = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"

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


@pytest.fixture
def root(tmp_path: Path) -> Path:
    return tmp_path


@pytest.fixture
def client(root: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setattr(
        "apps.live_control_server.routes.play_runs.repo_root",
        lambda: root,
    )
    return TestClient(create_app())


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
    return _remember_playable(get_workspace_document_snapshot(root, record.document_id))


def _create_committed_runbook(
    root: Path,
    *,
    name: str = "live-reference-manifest",
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


def _create_run(client: TestClient, snapshot: WorkspaceDocumentSnapshot) -> dict[str, object]:
    response = client.put(
        f"/api/live/play-runs/{RUN_ID_A}",
        json={
            "playable_artifact_id": snapshot.record.document_id,
            "expected_playable_revision": _playable(snapshot)[0],
            "expected_playable_content_sha256": _playable(snapshot)[1],
        },
    )
    assert response.status_code == 200
    return response.json()


def test_real_app_mount_seals_gets_and_does_not_create_on_get(
    client: TestClient,
    root: Path,
) -> None:
    snapshot = _create_committed_runbook(root)
    created = _create_run(client, snapshot)

    sealed = client.put(f"/api/live/play-runs/{RUN_ID_A}/reference-manifest")
    assert sealed.status_code == 200
    body = sealed.json()
    assert body["schema_version"] == "dmb_play_run_reference_manifest_v1"
    assert body["run_id"] == RUN_ID_A
    assert body["playable_artifact_id"] == created["playable_artifact_id"]
    assert body["playable_revision"] == created["playable_revision"]
    assert body["playable_content_sha256"] == created["playable_content_sha256"]
    assert [element["element_id"] for element in body["elements"]] == sorted(
        ["scene:gate", "beat:arrival", "choice:route", "option:fire", "option:wait"]
    )
    assert "scene_id" not in body["elements"][4]
    assert not play_run_reference_manifest_path(root, RUN_ID_A).exists()
    assert "The Gate" not in json.dumps(body)

    fetched = client.get(f"/api/live/play-runs/{RUN_ID_A}/reference-manifest")
    assert fetched.status_code == 200
    assert fetched.json() == body

    missing = client.get(f"/api/live/play-runs/bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb/reference-manifest")
    assert missing.status_code == 404


def test_request_body_is_rejected(client: TestClient, root: Path) -> None:
    snapshot = _create_committed_runbook(root)
    _create_run(client, snapshot)

    response = client.put(
        f"/api/live/play-runs/{RUN_ID_A}/reference-manifest",
        json={"elements": [{"kind": "scene", "element_id": "scene:forged"}]},
    )
    assert response.status_code == 422
    assert not play_run_reference_manifest_path(root, RUN_ID_A).exists()


def test_first_seal_still_uses_bound_revision_after_newer_commit(
    client: TestClient,
    root: Path,
) -> None:
    old = _create_committed_runbook(root, name="stale-live-manifest")
    created = _create_run(client, old)
    advanced = _commit_record(root, old.record, ADVANCED_MARKDOWN)
    assert _playable(advanced)[0] == created["playable_revision"] + 1

    response = client.put(f"/api/live/play-runs/{RUN_ID_A}/reference-manifest")
    assert response.status_code == 200
    assert not play_run_reference_manifest_path(root, RUN_ID_A).exists()


def test_replay_after_advance_returns_exact_sidecar(
    client: TestClient,
    root: Path,
) -> None:
    snapshot = _create_committed_runbook(root)
    created = _create_run(client, snapshot)
    first = client.put(f"/api/live/play-runs/{RUN_ID_A}/reference-manifest")
    assert first.status_code == 200
    manifest_before = get_play_run_reference_manifest(root, RUN_ID_A)

    advanced = _commit_record(root, snapshot.record, ADVANCED_MARKDOWN)
    assert advanced.loaded_revision > created["playable_revision"]

    replayed = client.put(f"/api/live/play-runs/{RUN_ID_A}/reference-manifest")
    assert replayed.status_code == 200
    assert replayed.json() == first.json()
    assert get_play_run_reference_manifest(root, RUN_ID_A) == manifest_before
    assert not play_run_reference_manifest_path(root, RUN_ID_A).exists()
    assert "scene:harbor" not in json.dumps(replayed.json())


def test_invalid_and_unknown_runs_fail_closed_over_http(
    client: TestClient,
    root: Path,
) -> None:
    unknown = client.put(f"/api/live/play-runs/{RUN_ID_A}/reference-manifest")
    assert unknown.status_code == 404

    invalid = client.put("/api/live/play-runs/not-a-uuid/reference-manifest")
    assert invalid.status_code == 422

    snapshot = _create_committed_runbook(root)
    _create_run(client, snapshot)
    path = play_run_reference_manifest_path(root, RUN_ID_A)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{nope", encoding="utf-8")
    corrupt = client.get(f"/api/live/play-runs/{RUN_ID_A}/reference-manifest")
    assert corrupt.status_code == 200
    assert path.read_text(encoding="utf-8") == "{nope"
V2_MARKDOWN = (
    "<!-- dmb-playable-element:v2 kind=beat id=beat:hold-the-gate beat_kind=spine -->\n"
    "## Hold the gate\n"
    "\n"
    "<!-- dmb-playable-element:v2 kind=scene id=scene:gate-line -->\n"
    "### The gate line\n"
    "\n"
    "<!-- dmb-playable-element:v2 kind=choice id=choice:who-gets-through scene=scene:gate-line -->\n"
    "### Who gets through first?\n"
    "\n"
    "<!-- dmb-playable-element:v2 kind=option id=option:cure-line-first activates=beat:panic-breaks -->\n"
    "- Prioritize the cure line\n"
    "\n"
    "<!-- dmb-playable-element:v2 kind=beat id=beat:panic-breaks beat_kind=optional -->\n"
    "## Panic breaks\n"
)


def test_v2_seal_and_replay_over_http(client: TestClient, root: Path) -> None:
    snapshot = _create_committed_runbook(root, name="v2-live-manifest", markdown=V2_MARKDOWN)
    created = _create_run(client, snapshot)

    sealed = client.put(f"/api/live/play-runs/{RUN_ID_A}/reference-manifest")
    assert sealed.status_code == 200
    body = sealed.json()
    assert body["schema_version"] == "dmb_play_run_reference_manifest_v2"
    assert body["run_id"] == RUN_ID_A
    assert body["playable_revision"] == created["playable_revision"]
    assert body["playable_content_sha256"] == created["playable_content_sha256"]
    assert body["beats"] == [
        {"beat_id": "beat:hold-the-gate", "beat_kind": "spine"},
        {"beat_id": "beat:panic-breaks", "beat_kind": "optional"},
    ]
    assert body["scenes"] == [
        {"scene_id": "scene:gate-line", "beat_id": "beat:hold-the-gate"},
    ]
    assert body["choices"] == [
        {
            "choice_id": "choice:who-gets-through",
            "beat_id": "beat:hold-the-gate",
            "scene_id": "scene:gate-line",
        },
    ]
    assert body["options"] == [
        {"option_id": "option:cure-line-first", "choice_id": "choice:who-gets-through"},
    ]
    assert body["edges"] == [
        {
            "option_id": "option:cure-line-first",
            "effect": "activate",
            "target_kind": "beat",
            "target_id": "beat:panic-breaks",
        },
    ]
    assert "elements" not in body

    fetched = client.get(f"/api/live/play-runs/{RUN_ID_A}/reference-manifest")
    assert fetched.status_code == 200
    assert fetched.json() == body


def test_v2_invalid_document_seal_returns_409_over_http(
    client: TestClient, root: Path
) -> None:
    snapshot = _create_committed_runbook(
        root,
        name="v2-live-invalid",
        markdown=(
            "<!-- dmb-playable-element:v2 kind=choice id=choice:orphan -->\n### Orphan\n"
        ),
    )
    created = client.put(
        f"/api/live/play-runs/{RUN_ID_A}",
        json={
            "playable_artifact_id": snapshot.record.document_id,
            "expected_playable_revision": _playable(snapshot)[0],
            "expected_playable_content_sha256": _playable(snapshot)[1],
        },
    )
    assert created.status_code in {409, 422}
    assert not play_run_reference_manifest_path(root, RUN_ID_A).exists()
    response = client.put(f"/api/live/play-runs/{RUN_ID_A}/reference-manifest")
    assert response.status_code == 404
