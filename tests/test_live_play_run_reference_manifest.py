from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from apps.live_control_server.main import create_app
from apps.live_control_server.services.play_run_registry import play_run_path
from apps.live_control_server.services.play_run_reference_manifest import (
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
    get_workspace_document_snapshot,
)

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
    return get_workspace_document_snapshot(root, record.document_id)


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
            "expected_playable_revision": snapshot.loaded_revision,
            "expected_playable_content_sha256": snapshot.content_sha256,
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
    run_bytes = play_run_path(root, RUN_ID_A).read_bytes()

    missing = client.get(f"/api/live/play-runs/{RUN_ID_A}/reference-manifest")
    assert missing.status_code == 404
    assert not play_run_reference_manifest_path(root, RUN_ID_A).exists()

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
    assert play_run_reference_manifest_path(root, RUN_ID_A).is_file()
    assert "The Gate" not in json.dumps(body)

    fetched = client.get(f"/api/live/play-runs/{RUN_ID_A}/reference-manifest")
    assert fetched.status_code == 200
    assert fetched.json() == body
    assert play_run_path(root, RUN_ID_A).read_bytes() == run_bytes


def test_request_body_is_rejected(client: TestClient, root: Path) -> None:
    snapshot = _create_committed_runbook(root)
    _create_run(client, snapshot)

    response = client.put(
        f"/api/live/play-runs/{RUN_ID_A}/reference-manifest",
        json={"elements": [{"kind": "scene", "element_id": "scene:forged"}]},
    )
    assert response.status_code == 422
    assert not play_run_reference_manifest_path(root, RUN_ID_A).exists()


def test_stale_bound_version_returns_409_and_no_file(
    client: TestClient,
    root: Path,
) -> None:
    old = _create_committed_runbook(root, name="stale-live-manifest")
    created = _create_run(client, old)
    advanced = _commit_record(root, old.record, ADVANCED_MARKDOWN)
    assert advanced.loaded_revision == created["playable_revision"] + 1

    response = client.put(f"/api/live/play-runs/{RUN_ID_A}/reference-manifest")
    assert response.status_code == 409
    assert not play_run_reference_manifest_path(root, RUN_ID_A).exists()


def test_replay_after_advance_returns_exact_sidecar(
    client: TestClient,
    root: Path,
) -> None:
    snapshot = _create_committed_runbook(root)
    created = _create_run(client, snapshot)
    first = client.put(f"/api/live/play-runs/{RUN_ID_A}/reference-manifest")
    assert first.status_code == 200
    bytes_before = play_run_reference_manifest_path(root, RUN_ID_A).read_bytes()

    advanced = _commit_record(root, snapshot.record, ADVANCED_MARKDOWN)
    assert advanced.loaded_revision > created["playable_revision"]

    replayed = client.put(f"/api/live/play-runs/{RUN_ID_A}/reference-manifest")
    assert replayed.status_code == 200
    assert replayed.json() == first.json()
    assert play_run_reference_manifest_path(root, RUN_ID_A).read_bytes() == bytes_before
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
    assert corrupt.status_code == 500
    assert path.read_text(encoding="utf-8") == "{nope"
