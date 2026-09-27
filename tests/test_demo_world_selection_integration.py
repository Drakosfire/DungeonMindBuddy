"""Two managed Worlds share one APP-STATE connection and one registry root."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from apps.live_control_server.main import create_app
from apps.live_control_server.services.tiptap_markdown_write import (
    TiptapMarkdownWriteCommitRequest,
    TiptapMarkdownWritePrepareRequest,
    commit_tiptap_markdown_write,
    prepare_tiptap_markdown_write,
)
from apps.live_control_server.services.workspace_document_registry import (
    create_workspace_document,
    get_committed_playable_revision,
)
from apps.live_control_server.services.world_container_registry import create_world_container

pytest_plugins = ["tests.application_state.conftest"]


def _commit_runbook(root: Path, document_id: str, revision: int) -> tuple[int, str]:
    markdown = "# At the table\n\nA bounded synthetic scene.\n"
    prepared = prepare_tiptap_markdown_write(
        root=root,
        request=TiptapMarkdownWritePrepareRequest(
            document_id=document_id,
            markdown=markdown,
            expected_revision=revision,
        ),
    )
    assert prepared.writer_ok and prepared.writer_confirm_token
    commit_tiptap_markdown_write(
        root=root,
        request=TiptapMarkdownWriteCommitRequest(
            document_id=document_id,
            markdown=markdown,
            writer_confirm_token=prepared.writer_confirm_token,
            expected_revision=revision,
        ),
    )
    committed = get_committed_playable_revision(document_id, kind=None)
    return committed.revision_n, committed.content_sha256


def test_same_registry_and_database_filter_two_worlds(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    application_state_dsn: str,
) -> None:
    # The fixture creates one disposable PostgreSQL database. All records below
    # use it; this is not an isolation claim based on two deployments.
    assert application_state_dsn
    for route in ("workspace_documents", "play_runs", "world_containers", "live"):
        monkeypatch.setattr(
            f"apps.live_control_server.routes.{route}.repo_root", lambda: tmp_path
        )
    client = TestClient(create_app())
    world_a = create_world_container(tmp_path, name="Synthetic World A")
    world_b = create_world_container(tmp_path, name="Synthetic World B")

    for world in (world_a, world_b):
        source = create_workspace_document(
            tmp_path,
            title=f"{world.name} source",
            campaign_id=world.world_id,
            world_id=world.world_id,
            kind="worldbuilding_source",
            source_domain="worldbuilding",
            document_class="lore",
            authority_state="draft",
            visibility_state="internal",
        )
        plan = create_workspace_document(
            tmp_path,
            title=f"{world.name} prep",
            campaign_id=world.world_id,
            kind="plan",
        )
        runbook = create_workspace_document(
            tmp_path,
            title=f"{world.name} runbook",
            campaign_id=world.world_id,
            kind="runbook",
        )
        playable_revision, playable_sha = _commit_runbook(
            tmp_path, runbook.document_id, runbook.revision
        )
        run_id = (
            "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
            if world == world_a
            else "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"
        )
        created = client.put(
            f"/api/live/play-runs/{run_id}",
            json={
                "playable_artifact_id": runbook.document_id,
                "expected_playable_revision": playable_revision,
                "expected_playable_content_sha256": playable_sha,
            },
        )
        assert created.status_code == 200, created.text
        assert created.json()["campaign_id"] == world.world_id
        for kind, expected_id in (
            ("worldbuilding_source", source.document_id),
            ("plan", plan.document_id),
            ("runbook", runbook.document_id),
        ):
            listed = client.get(
                "/api/live/workspace-documents",
                params={"campaign_id": world.world_id, "kind": kind},
            )
            assert listed.status_code == 200, listed.text
            assert [item["document_id"] for item in listed.json()["records"]] == [
                expected_id
            ]
        runs = client.get(
            "/api/live/play-runs", params={"campaign_id": world.world_id}
        )
        assert runs.status_code == 200, runs.text
        assert [item["run_id"] for item in runs.json()["records"]] == [run_id]
        plan_view = client.get(
            "/api/live/plan-view", params={"world_id": world.world_id}
        )
        assert plan_view.status_code == 200, plan_view.text
        assert plan_view.json()["campaign_id"] == world.world_id
        assert plan_view.json()["world_id"] == world.world_id

    listed_worlds = client.get("/api/live/world-containers")
    assert listed_worlds.status_code == 200
    assert {item["world_id"] for item in listed_worlds.json()["records"]} == {
        world_a.world_id,
        world_b.world_id,
    }
