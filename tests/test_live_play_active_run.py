from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from apps.live_control_server.main import create_app
from apps.live_control_server.services.play_active_run import play_active_run_path
from apps.live_control_server.services.play_run_reference_manifest import (
    seal_or_replay_play_run_reference_manifest,
)
from apps.live_control_server.services.play_run_registry import (
    create_or_replay_play_run,
)
from apps.live_control_server.services.tiptap_markdown_write import (
    TiptapMarkdownWriteCommitRequest,
    TiptapMarkdownWritePrepareRequest,
    commit_tiptap_markdown_write,
    prepare_tiptap_markdown_write,
)
from apps.live_control_server.services.workspace_document_registry import (
    create_workspace_document,
    get_workspace_document_snapshot,
)
from tests.application_state.playable_binding import (
    playable_binding,
    remember_committed_playable,
)

RUN_ID_A = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
RUN_ID_B = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setattr(
        "apps.live_control_server.routes.play_runs.repo_root",
        lambda: tmp_path,
    )
    return TestClient(create_app())


def _create_committed_run(root: Path, *, run_id: str, name: str):
    document = create_workspace_document(
        root,
        title=f"Runbook {name}",
        campaign_id="longmont-c2",
        kind="runbook",
        target_relpath=(
            "evals/c2_live_prep/mireward-prep/content/tiptap/"
            f"{name}.md"
        ),
    )
    markdown = f"# {name}\n\nAt the table.\n"
    prepared = prepare_tiptap_markdown_write(
        root=root,
        request=TiptapMarkdownWritePrepareRequest(
            document_id=document.document_id,
            markdown=markdown,
            expected_revision=document.revision,
        ),
    )
    assert prepared.writer_ok is True
    commit_tiptap_markdown_write(
        root=root,
        request=TiptapMarkdownWriteCommitRequest(
            document_id=document.document_id,
            markdown=markdown,
            writer_confirm_token=prepared.writer_confirm_token,
            expected_revision=document.revision,
        ),
    )
    snapshot = remember_committed_playable(
        get_workspace_document_snapshot(root, document.document_id)
    )
    revision_n, sha = playable_binding(snapshot)
    return create_or_replay_play_run(
        root,
        run_id=run_id,
        playable_artifact_id=document.document_id,
        expected_playable_revision=revision_n,
        expected_playable_content_sha256=sha,
    )


def test_missing_selection_is_returned_as_null(client: TestClient) -> None:
    response = client.get("/api/live/play-active-run")

    assert response.status_code == 200
    assert response.json() == {
        "schema_version": "dmb_play_active_run_v1",
        "run_id": None,
        "selected_at": None,
    }


def test_put_validates_uuid_and_requires_existing_sealed_run(
    client: TestClient,
    tmp_path: Path,
) -> None:
    malformed = client.put("/api/live/play-active-run", json={"run_id": RUN_ID_A.upper()})
    assert malformed.status_code == 422

    missing = client.put("/api/live/play-active-run", json={"run_id": RUN_ID_A})
    assert missing.status_code == 404
    assert not play_active_run_path(tmp_path).exists()

    _create_committed_run(tmp_path, run_id=RUN_ID_A, name="already-sealed")
    sealed = client.put("/api/live/play-active-run", json={"run_id": RUN_ID_A})
    assert sealed.status_code == 200
    assert play_active_run_path(tmp_path).is_file()


def test_valid_selection_is_idempotent_and_last_explicit_run_wins(
    client: TestClient,
    tmp_path: Path,
) -> None:
    _create_committed_run(tmp_path, run_id=RUN_ID_A, name="north-gate")
    _create_committed_run(tmp_path, run_id=RUN_ID_B, name="south-wall")
    seal_or_replay_play_run_reference_manifest(tmp_path, RUN_ID_A)
    seal_or_replay_play_run_reference_manifest(tmp_path, RUN_ID_B)

    first_response = client.put("/api/live/play-active-run", json={"run_id": RUN_ID_A})
    assert first_response.status_code == 200
    first = first_response.json()
    bytes_before = play_active_run_path(tmp_path).read_bytes()

    replay_response = client.put("/api/live/play-active-run", json={"run_id": RUN_ID_A})
    assert replay_response.status_code == 200
    assert replay_response.json() == first
    assert play_active_run_path(tmp_path).read_bytes() == bytes_before

    replaced = client.put("/api/live/play-active-run", json={"run_id": RUN_ID_B})
    assert replaced.status_code == 200
    assert replaced.json()["run_id"] == RUN_ID_B

    reread = client.get("/api/live/play-active-run")
    assert reread.status_code == 200
    assert reread.json() == replaced.json()


def test_malformed_selection_fails_closed_over_http(
    client: TestClient,
    tmp_path: Path,
) -> None:
    path = play_active_run_path(tmp_path)
    path.parent.mkdir(parents=True)
    path.write_text('{"schema_version":"dmb_play_active_run_v1","run_id":"broken"}\n')

    response = client.get("/api/live/play-active-run")

    assert response.status_code == 500
    assert "malformed persisted" in response.json()["detail"]
