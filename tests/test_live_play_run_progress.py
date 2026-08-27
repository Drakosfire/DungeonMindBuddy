from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from apps.live_control_server.main import create_app
from apps.live_control_server.services.play_run_rebase import rebase_or_replay_play_run
from apps.live_control_server.services.play_run_registry import (
    PlayRunRegistryError,
    get_play_run,
)
from apps.live_control_server.services.play_run_reference_manifest import (
    get_play_run_reference_manifest,
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
from tests.application_state.playable_binding import (
    playable_binding,
    remember_committed_playable,
)
from tests.application_state.play_runtime_helpers import (
    corrupt_play_run_manifest_document,
    leftover_manifest_path,
)

pytest_plugins = ["tests.application_state.conftest"]

RUN_ID_A = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"

PROGRESS_MARKDOWN = "\n".join(
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


@pytest.fixture(autouse=True)
def _application_state(application_state_dsn: str) -> str:
    return application_state_dsn


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
    return remember_committed_playable(get_workspace_document_snapshot(root, record.document_id))


def _create_committed_runbook(root: Path) -> WorkspaceDocumentSnapshot:
    record = create_workspace_document(
        root,
        title="Runbook progress-http",
        campaign_id="longmont-c2",
        kind="runbook",
        target_relpath=(
            "evals/c2_live_prep/mireward-prep/content/tiptap/"
            "progress-http.md"
        ),
    )
    return _commit_record(root, record, PROGRESS_MARKDOWN)


def _run_request(snapshot: WorkspaceDocumentSnapshot) -> dict[str, object]:
    revision_n, sha = playable_binding(snapshot)
    return {
        "playable_artifact_id": snapshot.record.document_id,
        "expected_playable_revision": revision_n,
        "expected_playable_content_sha256": sha,
    }


def _progress_body(expected_run_revision: int = 1) -> dict[str, object]:
    return {
        "expected_run_revision": expected_run_revision,
        "progress": {
            "current_scene_id": "scene:gate",
            "current_beat_id": "beat:arrival",
            "resolved_beat_ids": ["beat:arrival"],
            "selections": {"choice:route": "option:fire"},
            "notes_by_element_id": {"choice:route": "They hesitated."},
        },
    }


def _create_run(client: TestClient, root: Path, snapshot: WorkspaceDocumentSnapshot) -> None:
    created = client.put(f"/api/live/play-runs/{RUN_ID_A}", json=_run_request(snapshot))
    assert created.status_code == 200


def test_progress_put_round_trip_and_get_includes_snapshot(
    client: TestClient,
    root: Path,
) -> None:
    snapshot = _create_committed_runbook(root)
    _create_run(client, root, snapshot)
    manifest_before = get_play_run_reference_manifest(root, RUN_ID_A)

    response = client.put(
        f"/api/live/play-runs/{RUN_ID_A}/progress",
        json=_progress_body(),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["run_revision"] == 2
    assert body["progress"]["current_scene_id"] == "scene:gate"
    assert body["progress"]["selections"] == {"choice:route": "option:fire"}
    assert body["progress"]["notes_by_element_id"]["choice:route"] == "They hesitated."

    fetched = client.get(f"/api/live/play-runs/{RUN_ID_A}")
    assert fetched.status_code == 200
    assert fetched.json() == body
    listed = client.get("/api/live/play-runs")
    assert listed.status_code == 200
    assert listed.json()["records"] == [body]
    assert get_play_run_reference_manifest(root, RUN_ID_A) == manifest_before
    assert not leftover_manifest_path(root, RUN_ID_A).exists()


def _create_and_seal(
    client: TestClient,
    root: Path,
) -> WorkspaceDocumentSnapshot:
    snapshot = _create_committed_runbook(root)
    _create_run(client, root, snapshot)
    return snapshot


def test_progress_put_rejects_partial_payload(client: TestClient, root: Path) -> None:
    _create_and_seal(client, root)
    response = client.put(
        f"/api/live/play-runs/{RUN_ID_A}/progress",
        json={"expected_run_revision": 1},
    )
    assert response.status_code == 422
    omitted = client.put(
        f"/api/live/play-runs/{RUN_ID_A}/progress",
        json={
            "expected_run_revision": 1,
            "progress": {
                "current_scene_id": "scene:gate",
                "current_beat_id": None,
                "resolved_beat_ids": [],
                "selections": {},
            },
        },
    )
    assert omitted.status_code == 422


def test_missing_manifest_is_409(client: TestClient, root: Path) -> None:
    snapshot = _create_committed_runbook(root)
    created = client.put(f"/api/live/play-runs/{RUN_ID_A}", json=_run_request(snapshot))
    assert created.status_code == 200
    record_before = get_play_run(root, RUN_ID_A)

    response = client.put(
        f"/api/live/play-runs/{RUN_ID_A}/progress",
        json=_progress_body(),
    )

    assert response.status_code == 200
    assert response.json()["run_revision"] == 2
    assert get_play_run(root, RUN_ID_A).run_revision == 2
    assert record_before.run_revision == 1
    assert not leftover_manifest_path(root, RUN_ID_A).exists()


def test_http_noop_and_lost_response_replay(client: TestClient, root: Path) -> None:
    _create_and_seal(client, root)
    first = client.put(
        f"/api/live/play-runs/{RUN_ID_A}/progress",
        json=_progress_body(),
    )
    assert first.status_code == 200
    record_after = get_play_run(root, RUN_ID_A)

    noop = client.put(
        f"/api/live/play-runs/{RUN_ID_A}/progress",
        json=_progress_body(expected_run_revision=2),
    )
    assert noop.status_code == 200
    assert noop.json() == first.json()
    assert get_play_run(root, RUN_ID_A) == record_after

    replay = client.put(
        f"/api/live/play-runs/{RUN_ID_A}/progress",
        json=_progress_body(expected_run_revision=1),
    )
    assert replay.status_code == 200
    assert replay.json() == first.json()
    assert get_play_run(root, RUN_ID_A) == record_after


def test_stale_different_state_is_409(client: TestClient, root: Path) -> None:
    _create_and_seal(client, root)
    first = client.put(
        f"/api/live/play-runs/{RUN_ID_A}/progress",
        json=_progress_body(),
    )
    assert first.status_code == 200
    stale = _progress_body(expected_run_revision=1)
    stale["progress"]["current_beat_id"] = None
    response = client.put(f"/api/live/play-runs/{RUN_ID_A}/progress", json=stale)
    assert response.status_code == 409
    assert client.get(f"/api/live/play-runs/{RUN_ID_A}").json() == first.json()


def test_unknown_reference_is_422(client: TestClient, root: Path) -> None:
    _create_and_seal(client, root)
    body = _progress_body()
    body["progress"]["current_scene_id"] = "scene:ghost"
    response = client.put(f"/api/live/play-runs/{RUN_ID_A}/progress", json=body)
    assert response.status_code == 422
    assert client.get(f"/api/live/play-runs/{RUN_ID_A}").json()["run_revision"] == 1


V2_HTTP_MARKDOWN = "\n".join(
    [
        "<!-- dmb-playable-element:v2 kind=beat id=beat:z-opening beat_kind=spine -->",
        "## Opening",
        "",
        "<!-- dmb-playable-element:v2 kind=choice id=choice:x -->",
        "### Decision X",
        "",
        "Choice X unique prose.",
        "",
        "<!-- dmb-playable-element:v2 kind=option id=option:x1 -->",
        "- Option X1 unique text",
        "",
        "<!-- dmb-playable-element:v2 kind=beat id=beat:a-later beat_kind=optional -->",
        "## Later",
        "",
    ]
)


def _create_committed_v2_runbook(root: Path) -> WorkspaceDocumentSnapshot:
    record = create_workspace_document(
        root,
        title="Runbook v2-native-ready-http",
        campaign_id="longmont-c2",
        kind="runbook",
        target_relpath=(
            "evals/c2_live_prep/mireward-prep/content/tiptap/"
            "v2-native-ready-http.md"
        ),
    )
    return _commit_record(root, record, V2_HTTP_MARKDOWN)


def test_default_get_does_not_seed_empty_v2_progress(client: TestClient, root: Path) -> None:
    snapshot = _create_committed_v2_runbook(root)
    _create_run(client, root, snapshot)
    fetched = client.get(f"/api/live/play-runs/{RUN_ID_A}")
    assert fetched.status_code == 200
    assert fetched.json()["progress"]["current_beat_id"] is None
    assert fetched.json()["progress"]["current_scene_id"] is None
    assert fetched.json()["run_revision"] == 1


def test_native_ready_get_preflights_then_seeds_empty_v2_run(
    client: TestClient, root: Path
) -> None:
    snapshot = _create_committed_v2_runbook(root)
    _create_run(client, root, snapshot)
    empty = client.get(f"/api/live/play-runs/{RUN_ID_A}")
    assert empty.json()["progress"]["current_beat_id"] is None

    seeded = client.get(
        f"/api/live/play-runs/{RUN_ID_A}",
        params={"ensure_native_ready": "true"},
    )
    assert seeded.status_code == 200
    assert seeded.json()["progress"]["current_beat_id"] == "beat:z-opening"
    assert seeded.json()["progress"]["current_scene_id"] is None
    assert seeded.json()["run_revision"] == 2

    replayed = client.get(
        f"/api/live/play-runs/{RUN_ID_A}",
        params={"ensure_native_ready": "true"},
    )
    assert replayed.status_code == 200
    assert replayed.json()["run_revision"] == 2
    assert replayed.json()["progress"]["current_beat_id"] == "beat:z-opening"
    persisted = get_play_run(root, RUN_ID_A)
    assert persisted.progress.current_beat_id == "beat:z-opening"


def test_native_ready_get_does_not_seed_corrupted_sealed_beat_kind(
    client: TestClient, root: Path, application_state_dsn: str
) -> None:
    snapshot = _create_committed_v2_runbook(root)
    _create_run(client, root, snapshot)
    manifest = get_play_run_reference_manifest(root, RUN_ID_A)
    payload = manifest.model_dump(mode="json")
    first = payload["beats"][0]
    first["beat_kind"] = "optional" if first.get("beat_kind") == "spine" else "spine"
    payload["beats"][0] = first
    corrupt_play_run_manifest_document(application_state_dsn, RUN_ID_A, payload)

    refused = client.get(
        f"/api/live/play-runs/{RUN_ID_A}",
        params={"ensure_native_ready": "true"},
    )
    assert refused.status_code == 422
    assert "Beat kind" in refused.json()["detail"]
    unchanged = client.get(f"/api/live/play-runs/{RUN_ID_A}")
    assert unchanged.status_code == 200
    assert unchanged.json()["progress"]["current_beat_id"] is None
    assert unchanged.json()["run_revision"] == 1


def test_native_ready_get_does_not_seed_corrupted_manifest_binding(
    client: TestClient, root: Path, application_state_dsn: str
) -> None:
    snapshot = _create_committed_v2_runbook(root)
    _create_run(client, root, snapshot)
    manifest = get_play_run_reference_manifest(root, RUN_ID_A)
    payload = manifest.model_dump(mode="json")
    original_sha = payload["playable_content_sha256"]
    payload["playable_content_sha256"] = "0" * 64
    assert payload["playable_content_sha256"] != original_sha
    corrupt_play_run_manifest_document(application_state_dsn, RUN_ID_A, payload)

    refused = client.get(
        f"/api/live/play-runs/{RUN_ID_A}",
        params={"ensure_native_ready": "true"},
    )
    assert refused.status_code == 422
    assert "playable_content_sha256" in refused.json()["detail"]
    unchanged = client.get(f"/api/live/play-runs/{RUN_ID_A}")
    assert unchanged.status_code == 200
    assert unchanged.json()["progress"]["current_beat_id"] is None
    assert unchanged.json()["run_revision"] == 1


def test_native_ready_get_converges_when_rebase_changes_structure_during_first_admission(
    client: TestClient,
    root: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    snapshot = _create_committed_v2_runbook(root)
    _create_run(client, root, snapshot)
    current = get_workspace_document_snapshot(root, snapshot.record.document_id)
    rebased_markdown = V2_HTTP_MARKDOWN.replace(
        "id=beat:z-opening", "id=beat:new-opening"
    ).replace("## Opening", "## New Opening")
    assert "beat:z-opening" not in rebased_markdown
    assert "beat:new-opening" in rebased_markdown
    target = _commit_record(root, current.record, rebased_markdown)
    committed = get_committed_playable_revision(
        target.record.document_id,
        kind="runbook",
    )
    real_get = get_committed_playable_revision
    rebased = {"done": False}

    def straddle(*args: object, **kwargs: object):
        if not rebased["done"]:
            rebased["done"] = True
            rebase_or_replay_play_run(
                root,
                run_id=RUN_ID_A,
                expected_run_revision=1,
                target_playable_revision=committed.revision_n,
                target_playable_content_sha256=committed.content_sha256,
            )
        return real_get(*args, **kwargs)

    monkeypatch.setattr(
        "apps.live_control_server.services.workspace_document_registry.get_committed_playable_revision",
        straddle,
    )

    seeded = client.get(
        f"/api/live/play-runs/{RUN_ID_A}",
        params={"ensure_native_ready": "true"},
    )
    assert seeded.status_code == 200
    assert seeded.json()["progress"]["current_beat_id"] == "beat:new-opening"
    assert seeded.json()["playable_content_sha256"] == committed.content_sha256
    persisted = get_play_run(root, RUN_ID_A)
    assert persisted.progress.current_beat_id == "beat:new-opening"
    assert persisted.progress.current_beat_id != "beat:z-opening"
    assert persisted.playable_revision == committed.revision_n


def test_native_ready_get_does_not_retry_same_generation_seed_422(
    client: TestClient,
    root: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    snapshot = _create_committed_v2_runbook(root)
    _create_run(client, root, snapshot)
    calls = {"n": 0}

    def refuse_same_generation(*args: object, **kwargs: object):
        del args, kwargs
        calls["n"] += 1
        raise PlayRunRegistryError(
            "current_beat_id is not admitted by the sealed Playable reference manifest",
            status_code=422,
        )

    monkeypatch.setattr(
        "apps.live_control_server.services.play_run_registry.replace_play_run_progress",
        refuse_same_generation,
    )

    refused = client.get(
        f"/api/live/play-runs/{RUN_ID_A}",
        params={"ensure_native_ready": "true"},
    )
    assert refused.status_code == 422
    assert "current_beat_id" in refused.json()["detail"]
    assert calls["n"] == 1
    unchanged = client.get(f"/api/live/play-runs/{RUN_ID_A}")
    assert unchanged.status_code == 200
    assert unchanged.json()["progress"]["current_beat_id"] is None
    assert unchanged.json()["run_revision"] == 1
