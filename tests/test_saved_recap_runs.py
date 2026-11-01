"""Mounted authenticated HTTP + real APP owner, no files/providers/native Graph."""

from __future__ import annotations

from uuid import uuid4

import psycopg
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from psycopg.types.json import Jsonb

from application_state.ingest import service as ingest
from application_state.source import service as sources
from apps.live_control_server.routes import graph_preview
from apps.live_control_server.services.world_container_registry import (
    create_world_container,
)
from graph_memory.ingestion.extraction_run import (
    ExtractionRun,
    ExtractionRunComponentRef,
    ExtractionRunStatus,
)

TOKEN = "synthetic-saved-run-reader-operator-credential"
BASE = "/api/live/graph-preview/extraction-runs"


@pytest.fixture
def lane(application_state_dsn, tmp_path, monkeypatch):
    monkeypatch.setenv("DMB_DEPLOYMENT_ENVIRONMENT", "local")
    monkeypatch.setenv("DMB_AUTH_MODE", "local_operator")
    monkeypatch.setenv("DMB_AGENT_GRAPH_AUTH_MODE", "local_operator")
    monkeypatch.setenv("DMB_AGENT_GRAPH_AUTH_ENVIRONMENT", "local")
    monkeypatch.setenv("DMB_AGENT_GRAPH_LOCAL_OPERATOR_TOKEN", TOKEN)
    monkeypatch.setattr(graph_preview, "repo_root", lambda: tmp_path)
    world = create_world_container(tmp_path, name="Saved extraction World")
    other = create_world_container(tmp_path, name="Other extraction World")
    app = FastAPI()
    app.include_router(graph_preview.router)
    client = TestClient(app, client=("127.0.0.1", 50000))
    client.headers["Authorization"] = f"Bearer {TOKEN}"
    # Exploding discovery and body access prove the picker uses metadata only.
    monkeypatch.setattr(
        graph_preview,
        "discover_graph_ingest_runs",
        lambda **_: pytest.fail("file discovery"),
    )
    return client, world, other, application_state_dsn


def seed(
    world,
    *,
    status="reviewable",
    text="# Session 8\n\nAri found a sample.\n",
    session="session-8",
    domain="recap",
    components=True,
    digest=None,
):
    if domain == "worldbuilding":
        session = None
    artifact = "artifact:synthetic:" + uuid4().hex
    source = sources.persist_source_markdown(
        source_artifact_id=artifact,
        source_domain=domain,
        campaign_id="campaign",
        session_id=session,
        world_id=world.native_graph_binding.native_world_id,
        markdown=text,
    )
    refs = {}
    if components:
        refs = {
            kind: ExtractionRunComponentRef(
                kind=kind, uri=f"repo://../poison/{kind}", sha256=value
            )
            for kind, value in [
                ("source_artifact", digest or source.content_sha256),
                ("source_span_index", "b" * 64),
                ("candidate_graph", "c" * 64),
            ]
        }
    run = ingest.create_extraction_run(
        ExtractionRun(
            run_id="saved-" + uuid4().hex,
            source_artifact_id=artifact,
            source_domain=domain,
            campaign_id="campaign",
            session_id=session,
            status="draft" if status == "failed" else status,
            revision=1,
            components=refs,
            created_at="2026-11-01T01:00:00Z",
            updated_at="2026-11-01T01:00:00Z",
            lineage={"private-sentinel": "not-selector-metadata"},
        )
    )
    if status == "failed":
        run = ingest.update_extraction_run(
            run.run_id,
            expected_revision=run.revision,
            status=ExtractionRunStatus.FAILED,
        )
    return run, source


def catalog(client, world, **extra):
    return client.get(BASE, params={"managed_world_id": world.world_id, **extra})


def read(client, world, run, source, **extra):
    return client.get(
        f"{BASE}/{run.run_id}/recap-inspection",
        params={
            "managed_world_id": world.world_id,
            "expected_run_revision": run.revision,
            "source_revision_id": str(source.source_revision_id),
            **extra,
        },
    )


def test_catalog_scopes_before_interpretation_and_never_opens_body(lane, monkeypatch):
    client, world, other, dsn = lane
    ready, source = seed(world)
    failed, _ = seed(world, status="failed")
    pending, _ = seed(world, status="draft", components=False)
    foreign, _ = seed(other)
    seed(world, domain="worldbuilding")
    with psycopg.connect(dsn) as conn:
        conn.execute(
            "UPDATE ingest.run SET components=%s WHERE run_id=%s",
            (Jsonb({"bad": "foreign malformed payload"}), foreign.run_id),
        )
    monkeypatch.setattr(
        sources,
        "get_source_markdown",
        lambda **_: pytest.fail("catalog opened Markdown"),
    )
    response = catalog(client, world)
    assert response.status_code == 200, response.text
    assert response.headers["cache-control"] == "no-store"
    body = response.json()
    assert body["managedWorldId"] == world.world_id
    assert body["nativeWorldId"] == world.native_graph_binding.native_world_id
    assert {row["runId"] for row in body["runs"]} == {
        ready.run_id,
        failed.run_id,
        pending.run_id,
    }
    rows = {row["runId"]: row for row in body["runs"]}
    assert rows[ready.run_id]["sourceRevisionId"] == str(source.source_revision_id)
    assert rows[ready.run_id]["sourceSha256"] == source.content_sha256
    assert rows[failed.run_id]["runStatus"] == "failed"
    assert rows[pending.run_id]["unavailableReason"]
    assert "not-selector-metadata" not in response.text
    assert "Ari found" not in response.text
    assert catalog(client, world, campaign_id="unrelated").json()["runs"] == []
    # Foreign corruption is not even interpreted by the exact scoped load.
    assert read(client, world, foreign, source).status_code == 404


def test_exact_source_uses_frozen_revision_not_files_or_latest(lane):
    client, world, _, _ = lane
    run, source = seed(world)
    sources.persist_source_markdown(
        source_artifact_id=source.source_artifact_id,
        source_domain="recap",
        campaign_id="campaign",
        session_id="session-8",
        world_id=source.world_id,
        markdown="Newer different text.",
    )
    before = ingest.get_extraction_run(run.run_id).model_dump()
    response = read(client, world, run, source)
    assert response.status_code == 200, response.text
    assert response.json()["sourceProse"] == source.markdown
    assert response.json()["run"]["sourceRevisionId"] == str(source.source_revision_id)
    assert response.headers["cache-control"] == "no-store"
    assert ingest.get_extraction_run(run.run_id).model_dump() == before


@pytest.mark.parametrize("change", ["foreign_world", "revision", "source_uuid"])
def test_swapped_selectors_refuse_before_body(lane, monkeypatch, change):
    client, world, other, _ = lane
    run, source = seed(world)
    monkeypatch.setattr(
        sources,
        "get_source_markdown",
        lambda **_: pytest.fail("body before selectors verified"),
    )
    params = (
        {"expected_run_revision": 2}
        if change == "revision"
        else {"source_revision_id": str(uuid4())}
        if change == "source_uuid"
        else {}
    )
    response = read(
        client, other if change == "foreign_world" else world, run, source, **params
    )
    assert response.status_code == (404 if change == "foreign_world" else 409)


@pytest.mark.parametrize("digest", [None, "f" * 64])
def test_missing_exact_source_stays_visible_but_cannot_read(lane, monkeypatch, digest):
    client, world, _, _ = lane
    run, source = seed(
        world, status="draft", components=digest is not None, digest=digest
    )
    row = catalog(client, world).json()["runs"][0]
    assert row["runId"] == run.run_id and row["unavailableReason"]
    assert row["sourceRevisionId"] is None
    monkeypatch.setattr(
        sources,
        "get_source_markdown",
        lambda **_: pytest.fail("missing source body fallback"),
    )
    assert read(client, world, run, source).status_code == 409


def test_scope_mismatch_refuses_before_body(lane, monkeypatch):
    client, world, _, dsn = lane
    run, source = seed(world)
    with psycopg.connect(dsn) as conn:
        conn.execute(
            "UPDATE ingest.run SET session_id='session-99' WHERE run_id=%s",
            (run.run_id,),
        )
    monkeypatch.setattr(
        sources, "get_source_markdown", lambda **_: pytest.fail("scope mismatch body")
    )
    assert catalog(client, world).json()["runs"] == []
    assert read(client, world, run, source).status_code == 404


def test_corrupt_body_refuses(lane):
    client, world, _, dsn = lane
    run, source = seed(world)
    with psycopg.connect(dsn) as conn:
        conn.execute(
            "UPDATE source.revision SET markdown='Corrupted retained bytes' WHERE source_revision_id=%s",
            (source.source_revision_id,),
        )
    assert read(client, world, run, source).status_code == 409


def test_auth_and_selector_validation_before_any_read(lane, monkeypatch):
    client, world, _, _ = lane
    run, source = seed(world)
    monkeypatch.setattr(
        sources, "get_source_markdown", lambda **_: pytest.fail("unauthorized body")
    )
    client.headers.pop("Authorization")
    assert catalog(client, world).status_code == 401
    assert read(client, world, run, source).status_code == 401
    client.headers["Authorization"] = f"Bearer {TOKEN}"
    for path in (BASE, f"{BASE}/{run.run_id}/recap-inspection"):
        assert client.get(path).status_code == 422
        assert (
            client.get(
                path,
                params=[
                    ("managed_world_id", world.world_id),
                    ("managed_world_id", world.world_id),
                ],
            ).status_code
            == 422
        )
    assert catalog(client, world, unknown="x").status_code == 422
    assert (
        read(client, world, run, source, expected_run_revision="x").status_code == 422
    )


def test_empty_world_and_database_failure_are_not_file_fallback(lane, monkeypatch):
    client, world, _, _ = lane
    assert catalog(client, world).json()["runs"] == []
    from application_state.errors import ApplicationStateUnavailableError
    import apps.live_control_server.services.ingest_run_catalog as service

    def unavailable(**_):
        raise ApplicationStateUnavailableError("database unavailable")

    monkeypatch.setattr(service, "list_extraction_runs", unavailable)
    assert catalog(client, world).status_code == 503


def test_selected_world_corruption_fails_closed(lane):
    client, world, _, dsn = lane
    run, source = seed(world)
    with psycopg.connect(dsn) as conn:
        conn.execute(
            "UPDATE ingest.run SET components=%s WHERE run_id=%s",
            (Jsonb({"bad": "malformed"}), run.run_id),
        )
    assert catalog(client, world).status_code == 500
    assert read(client, world, run, source).status_code == 500


def test_missing_owned_run_is_404(lane):
    client, world, _, _ = lane
    response = client.get(
        f"{BASE}/missing/recap-inspection",
        params={
            "managed_world_id": world.world_id,
            "expected_run_revision": 1,
            "source_revision_id": str(uuid4()),
        },
    )
    assert response.status_code == 404


def test_worldbuilding_run_does_not_become_recap_source(lane):
    client, world, _, _ = lane
    run, source = seed(world, domain="worldbuilding")
    assert catalog(client, world).json()["runs"] == []
    assert read(client, world, run, source).status_code == 422


def test_revision_change_during_body_read_refuses(lane, monkeypatch):
    client, world, _, _ = lane
    run, source = seed(world)
    original = sources.get_source_markdown

    def changed(**kwargs):
        body = original(**kwargs)
        ingest.update_extraction_run(
            run.run_id,
            expected_revision=run.revision,
            status=ExtractionRunStatus.PROMOTED,
        )
        return body

    monkeypatch.setattr(sources, "get_source_markdown", changed)
    assert read(client, world, run, source).status_code == 409


def test_superseded_history_and_newer_failed_attempt_remain_distinct(lane):
    client, world, _, _ = lane
    run, source = seed(world)
    child = run.model_copy(
        update={
            "run_id": "saved-child-" + uuid4().hex,
            "revision": 1,
            "supersedes_run_id": run.run_id,
            "status": ExtractionRunStatus.DRAFT,
        }
    )
    child = ingest.supersede_extraction_run(
        run.run_id, expected_revision=run.revision, successor=child
    )
    child = ingest.update_extraction_run(
        child.run_id,
        expected_revision=child.revision,
        status=ExtractionRunStatus.FAILED,
    )
    rows = {row["runId"]: row for row in catalog(client, world).json()["runs"]}
    assert rows[run.run_id]["runStatus"] == "superseded"
    assert rows[child.run_id]["runStatus"] == "failed"
    assert rows[child.run_id]["sourceRevisionId"] == str(source.source_revision_id)
    assert read(client, world, child, source).status_code == 200
    # The old selected revision is now stale, even though its source is readable.
    assert read(client, world, run, source).status_code == 409


def test_managed_binding_change_during_read_refuses(lane, monkeypatch):
    client, world, _, _ = lane
    run, source = seed(world)
    from dataclasses import replace
    from apps.live_control_server.services import (
        managed_world_graph_projection as owner,
    )

    original = owner.resolve_managed_source_identity
    count = 0

    def changed(*args, **kwargs):
        nonlocal count
        count += 1
        scope = original(*args, **kwargs)
        return (
            replace(scope, binding_version=scope.binding_version + 1)
            if count > 2
            else scope
        )

    monkeypatch.setattr(owner, "resolve_managed_source_identity", changed)
    assert read(client, world, run, source).status_code == 409


@pytest.mark.parametrize(
    "field,value",
    [
        ("campaign_id", "wrong-campaign"),
        ("session_id", "session-99"),
        ("source_domain", "worldbuilding"),
    ],
)
def test_incomplete_run_cannot_advertise_unverified_source_scope(
    lane, monkeypatch, field, value
):
    client, world, _, dsn = lane
    run, source = seed(world, status="draft", components=False)
    # Corrupt the run while keeping the actual source descriptor unchanged.
    from psycopg import sql

    with psycopg.connect(dsn) as conn:
        conn.execute(
            sql.SQL("UPDATE ingest.run SET {}=%s WHERE run_id=%s").format(
                sql.Identifier(field)
            ),
            (value, run.run_id),
        )
    monkeypatch.setattr(
        sources,
        "get_source_markdown",
        lambda **_: pytest.fail("unverified incomplete source read"),
    )
    assert catalog(client, world).json()["runs"] == []
    assert catalog(client, world, campaign_id="wrong-campaign").json()["runs"] == []
    assert read(client, world, run, source).status_code == 404
