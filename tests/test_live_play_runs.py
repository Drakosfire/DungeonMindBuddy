from __future__ import annotations

import hashlib
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from apps.live_control_server.main import create_app
from apps.live_control_server.services.play_run_registry import play_run_path, play_runs_dir
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
    discard_workspace_document,
    get_workspace_document_snapshot,
)

pytest_plugins = ["tests.application_state.conftest"]

RUN_ID_A = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
RUN_ID_B = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"


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
    name: str = "live-play-run",
    markdown: str = "# Runbook\n\nAt the table.\n",
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


def _request(snapshot: WorkspaceDocumentSnapshot) -> dict[str, object]:
    return {
        "playable_artifact_id": snapshot.record.document_id,
        "expected_playable_revision": snapshot.loaded_revision,
        "expected_playable_content_sha256": snapshot.content_sha256,
    }


def test_real_app_mount_creates_gets_and_lists_exact_binding(
    client: TestClient,
    root: Path,
) -> None:
    before = _create_committed_runbook(root)

    created_response = client.put(f"/api/live/play-runs/{RUN_ID_A}", json=_request(before))

    assert created_response.status_code == 200
    created = created_response.json()
    assert created["schema_version"] == "dmb_play_run_record_v1"
    assert created["run_id"] == RUN_ID_A
    assert created["campaign_id"] == "longmont-c2"
    assert created["playable_artifact_id"] == before.record.document_id
    assert created["playable_revision"] == before.loaded_revision
    assert created["playable_content_sha256"] == before.content_sha256
    assert created["run_revision"] == 1
    assert created["created_at"] == created["updated_at"]
    assert play_run_path(root, RUN_ID_A).is_file()

    get_response = client.get(f"/api/live/play-runs/{RUN_ID_A}")
    assert get_response.status_code == 200
    assert get_response.json() == created

    list_response = client.get("/api/live/play-runs")
    assert list_response.status_code == 200
    assert list_response.json() == {
        "schema_version": "dmb_play_runs_list_v1",
        "records": [created],
    }

    by_campaign = client.get("/api/live/play-runs?campaign_id=longmont-c2")
    assert by_campaign.status_code == 200
    assert by_campaign.json()["records"] == [created]

    by_artifact = client.get(
        "/api/live/play-runs",
        params={"playable_artifact_id": before.record.document_id},
    )
    assert by_artifact.status_code == 200
    assert by_artifact.json()["records"] == [created]

    after = get_workspace_document_snapshot(root, before.record.document_id)
    assert after.loaded_revision == before.loaded_revision
    assert after.content_sha256 == before.content_sha256
    assert after.markdown == before.markdown


def test_identical_put_replay_is_exact_and_does_not_rewrite_file(
    client: TestClient,
    root: Path,
) -> None:
    snapshot = _create_committed_runbook(root, name="replay")
    first = client.put(f"/api/live/play-runs/{RUN_ID_A}", json=_request(snapshot))
    assert first.status_code == 200
    path = play_run_path(root, RUN_ID_A)
    bytes_before = path.read_bytes()

    second = client.put(f"/api/live/play-runs/{RUN_ID_A}", json=_request(snapshot))

    assert second.status_code == 200
    assert second.json() == first.json()
    assert second.json()["run_revision"] == 1
    assert path.read_bytes() == bytes_before


def test_replay_after_runbook_advances_returns_stored_binding(
    client: TestClient,
    root: Path,
) -> None:
    snapshot = _create_committed_runbook(root, name="replay-after-advance")
    first = client.put(f"/api/live/play-runs/{RUN_ID_A}", json=_request(snapshot))
    assert first.status_code == 200
    bytes_before = play_run_path(root, RUN_ID_A).read_bytes()

    advanced = _commit_record(
        root,
        snapshot.record,
        "# Runbook\n\nChanged after the Run began.\n",
    )
    assert advanced.loaded_revision > snapshot.loaded_revision

    replay = client.put(f"/api/live/play-runs/{RUN_ID_A}", json=_request(snapshot))

    assert replay.status_code == 200
    assert replay.json() == first.json()
    assert play_run_path(root, RUN_ID_A).read_bytes() == bytes_before


def test_same_run_uuid_different_binding_returns_409_and_preserves_original(
    client: TestClient,
    root: Path,
) -> None:
    first_snapshot = _create_committed_runbook(root, name="collision-a")
    second_snapshot = _create_committed_runbook(root, name="collision-b")
    first = client.put(
        f"/api/live/play-runs/{RUN_ID_A}",
        json=_request(first_snapshot),
    )
    assert first.status_code == 200
    path = play_run_path(root, RUN_ID_A)
    bytes_before = path.read_bytes()

    conflict = client.put(
        f"/api/live/play-runs/{RUN_ID_A}",
        json=_request(second_snapshot),
    )

    assert conflict.status_code == 409
    assert client.get(f"/api/live/play-runs/{RUN_ID_A}").json() == first.json()
    assert path.read_bytes() == bytes_before


def test_stale_revision_after_workspace_advance_returns_409_and_no_file(
    client: TestClient,
    root: Path,
) -> None:
    old = _create_committed_runbook(root, name="stale-route")
    current = _commit_record(
        root,
        old.record,
        "# Runbook\n\nCurrent revision.\n",
    )
    assert current.loaded_revision == old.loaded_revision + 1

    response = client.put(f"/api/live/play-runs/{RUN_ID_A}", json=_request(old))

    assert response.status_code == 409
    assert not play_run_path(root, RUN_ID_A).exists()


def test_stale_sha_returns_409_and_no_file(client: TestClient, root: Path) -> None:
    snapshot = _create_committed_runbook(root, name="stale-sha-route")
    body = _request(snapshot)
    body["expected_playable_content_sha256"] = hashlib.sha256(b"wrong").hexdigest()

    response = client.put(f"/api/live/play-runs/{RUN_ID_A}", json=body)

    assert response.status_code == 409
    assert not play_run_path(root, RUN_ID_A).exists()


def test_non_runbook_draft_and_discarded_are_rejected_over_http(
    client: TestClient,
    root: Path,
    application_state_dsn: str,
) -> None:
    plan = create_workspace_document(
        root,
        title="Plan",
        campaign_id="longmont-c2",
        kind="plan",
    )
    committed_plan = _commit_record(root, plan, "# Plan\n")
    plan_response = client.put(
        f"/api/live/play-runs/{RUN_ID_A}",
        json=_request(committed_plan),
    )
    assert plan_response.status_code == 422
    assert not play_run_path(root, RUN_ID_A).exists()

    draft = create_workspace_document(
        root,
        title="Draft Runbook",
        campaign_id="longmont-c2",
        kind="runbook",
        target_relpath=(
            "evals/c2_live_prep/mireward-prep/content/tiptap/live-draft.md"
        ),
    )
    draft_snapshot = get_workspace_document_snapshot(root, draft.document_id)
    draft_response = client.put(
        f"/api/live/play-runs/{RUN_ID_A}",
        json=_request(draft_snapshot),
    )
    assert draft_response.status_code == 409
    assert not play_run_path(root, RUN_ID_A).exists()

    committed = _create_committed_runbook(root, name="live-discarded")
    discarded = discard_workspace_document(
        root,
        committed.record.document_id,
        expected_revision=committed.loaded_revision,
    )
    discarded_snapshot = get_workspace_document_snapshot(root, discarded.document_id)
    discarded_response = client.put(
        f"/api/live/play-runs/{RUN_ID_A}",
        json=_request(discarded_snapshot),
    )
    assert discarded_response.status_code == 409
    assert not play_run_path(root, RUN_ID_A).exists()


def test_two_run_ids_can_share_one_playable_binding(
    client: TestClient,
    root: Path,
) -> None:
    snapshot = _create_committed_runbook(root, name="two-runs")

    first = client.put(f"/api/live/play-runs/{RUN_ID_A}", json=_request(snapshot))
    second = client.put(f"/api/live/play-runs/{RUN_ID_B}", json=_request(snapshot))

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["run_id"] != second.json()["run_id"]
    assert first.json()["playable_artifact_id"] == second.json()["playable_artifact_id"]
    assert first.json()["playable_revision"] == second.json()["playable_revision"]


def test_invalid_unknown_and_malformed_runs_fail_closed_over_http(
    client: TestClient,
    root: Path,
) -> None:
    invalid = client.get("/api/live/play-runs/not-a-uuid")
    assert invalid.status_code == 422

    unknown = client.get(f"/api/live/play-runs/{RUN_ID_A}")
    assert unknown.status_code == 404

    path = play_runs_dir(root) / f"{RUN_ID_A}.json"
    path.parent.mkdir(parents=True)
    path.write_text("{broken\n", encoding="utf-8")

    malformed_get = client.get(f"/api/live/play-runs/{RUN_ID_A}")
    malformed_list = client.get("/api/live/play-runs")
    assert malformed_get.status_code == 500
    assert malformed_list.status_code == 500
    assert path.read_text(encoding="utf-8") == "{broken\n"


def test_request_contract_rejects_noncanonical_and_extra_input(
    client: TestClient,
    root: Path,
) -> None:
    snapshot = _create_committed_runbook(root, name="request-validation")
    body = _request(snapshot)

    uppercase_run = client.put(
        f"/api/live/play-runs/{RUN_ID_A.upper()}",
        json=body,
    )
    assert uppercase_run.status_code == 422

    uppercase_sha = {**body, "expected_playable_content_sha256": snapshot.content_sha256.upper()}
    sha_response = client.put(f"/api/live/play-runs/{RUN_ID_A}", json=uppercase_sha)
    assert sha_response.status_code == 422

    extra_response = client.put(
        f"/api/live/play-runs/{RUN_ID_A}",
        json={**body, "current_scene_id": "scene:not-allowed"},
    )
    assert extra_response.status_code == 422
