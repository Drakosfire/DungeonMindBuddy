"""Owning Core stages and actual existing Buddy routes; only disposable authority."""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit
from uuid import uuid4

import pytest

from tests.test_reviewed_corpus_publication import (
    corpus_case,
    execute,
    procedure,
    observation_packet,
)


@pytest.fixture
def postgres_case(tmp_path, monkeypatch):
    admin = os.environ.get("DMB_REVIEWED_CORPUS_TEST_ADMIN_DSN", "")
    checkout = os.environ.get("DMB_REVIEWED_CORPUS_TEST_CORE_CHECKOUT", "")
    if not admin or not checkout:
        pytest.skip(
            "explicit disposable PostgreSQL admin and exact Core checkout required"
        )
    import psycopg
    from psycopg import sql
    from alembic import command
    from alembic.config import Config
    from dungeonmind.infrastructure.postgres import (
        PostgresDatabase,
        PostgresRepositoryBundle,
    )

    parts = urlsplit(admin)
    assert (
        parts.hostname in ("127.0.0.1", "localhost")
        and parts.port == 55443
        and parts.path == "/postgres"
    )
    name = "dmb_reviewed_corpus_test_" + uuid4().hex[:12]
    dsn = urlunsplit(parts._replace(path="/" + name))
    with psycopg.connect(admin, autocommit=True) as conn:
        conn.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
    try:
        monkeypatch.setenv("DUNGEONMIND_DATABASE_URL", dsn)
        configuration = Config(str(Path(checkout) / "alembic.ini"))
        configuration.set_main_option(
            "script_location", str(Path(checkout) / "migrations")
        )
        command.upgrade(
            configuration, "head"
        )  # external fixture prerequisite, never procedure/CLI
        case = corpus_case(tmp_path, PostgresRepositoryBundle(PostgresDatabase(dsn)))
        monkeypatch.setenv("DUNGEONMIND_WORLD_GRAPH_AUTHORITY_DATABASE_URL", dsn)
        monkeypatch.setenv("DUNGEONMIND_WORLD_GRAPH_AUTHORITY", "dungeonmind")
        monkeypatch.setenv("DMB_ARTIFACT_DATA_ROOT", str(case.root))
        monkeypatch.setenv("DMB_MANAGED_WORLD_DATA_ROOT", str(case.registry))
        yield case
    finally:
        with psycopg.connect(admin, autocommit=True) as conn:
            conn.execute(
                "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname=%s",
                (name,),
            )
            conn.execute(sql.SQL("DROP DATABASE {}").format(sql.Identifier(name)))


@pytest.mark.parametrize(
    "observation_only",
    [False, True],
    ids=["nodes-and-relationship", "standing-observation-only"],
)
def test_postgres_resume_and_actual_selected_world_and_source_routes(
    postgres_case, monkeypatch, observation_only
):
    case = postgres_case
    # Actual interrupted operation: source and finalized review survive independently.
    assert execute(case, stop_after="review")["status"] == "committed_stage"
    first = case.store.read(case.packet.operation_id)
    result = execute(case)
    if result["verification"].get("status") == "unavailable":
        case.backend.verify(case.packet, case.backend.publication_probe(case.packet))
    assert result["status"] == "verified", result["verification"]
    if observation_only:
        parent = case.bundle.world_graph.get_revision(
            case.packet.native_world_id, result["published_revision_id"]
        )
        case.packet = observation_packet(case)
        assert execute(case, stop_after="review")["status"] == "committed_stage"
        first = case.store.read(case.packet.operation_id)
        result = execute(case)
        assert result["status"] == "verified", result["verification"]
        assert result["verification"]["effects"]["changed_object_ids"] == []
        assert result["verification"]["effects"]["introduced_evidence_ids"] == []
        assert result["verification"]["verified_assertion_ids"] == [
            "assertion:observation"
        ]
        child_record = case.bundle.world_graph.get_revision(
            case.packet.native_world_id, result["published_revision_id"]
        )
        assert parent.graph_payload["objects"] == child_record.graph_payload["objects"]
    verification = result["verification"]
    assert (
        verification["core_verified"]
        and verification["selected_world_service_verified"]
    )
    assert verification["source_open_status"] == "verified"
    assert (
        verification["buddy_http_route_status"] == "not_exercised"
        and not result["product_ready"]
    )
    for stage, value in first["stages"].items():
        assert case.store.read(case.packet.operation_id)["stages"][stage] == value
    assert len(verification["effects"]["introduced_evidence_ids"]) == (
        0 if observation_only else 1
    )
    child = result["published_revision_id"]
    before = {p.name: p.read_bytes() for p in case.store.directory.iterdir()}
    inspected = procedure(case).run(
        case.packet, selected_world_id=case.packet.managed_world_id
    )
    assert inspected["status"] == "verified"
    assert before == {p.name: p.read_bytes() for p in case.store.directory.iterdir()}
    # The independent mounted-route proof is deliberately not promoted to product readiness.
    import httpx
    from fastapi import FastAPI
    from apps.live_control_server.routes.world_graph_projection import (
        router as projection_router,
    )
    from apps.live_control_server.routes.world_graph_retrieval import (
        router as retrieval_router,
    )

    token = "synthetic-reviewed-corpus-route-credential-32-chars"
    monkeypatch.setenv("DMB_AGENT_GRAPH_AUTH_MODE", "local_operator")
    monkeypatch.setenv("DMB_AGENT_GRAPH_AUTH_ENVIRONMENT", "development")
    monkeypatch.setenv("DMB_AGENT_GRAPH_LOCAL_OPERATOR_TOKEN", token)
    app = FastAPI()
    app.include_router(projection_router)
    app.include_router(retrieval_router)

    async def mounted():
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app, client=("127.0.0.1", 42000)),
            base_url="http://isolated",
        ) as client:
            query = {
                "schema": "dmb_managed_world_graph_projection_request_v1",
                "managedWorldId": case.packet.managed_world_id,
                "revisionPin": child,
            }
            denied = await client.post(
                "/api/live/world-graph/managed-projection", json=query
            )
            assert denied.status_code == 401
            headers = {"Authorization": "Bearer " + token}
            queried = await client.post(
                "/api/live/world-graph/managed-projection", json=query, headers=headers
            )
            assert queried.status_code == 200
            view = queried.json()
            assert (
                view["managedWorldId"] == case.packet.managed_world_id
                and view["nativeWorldId"] == case.packet.native_world_id
            )
            assert (
                view["bindingVersion"] == case.packet.binding_version
                and view["projection"]["snapshot"]["revisionId"] == child
            )
            for opened in verification["opened_sources"]:
                response = await client.post(
                    "/api/live/world-graph/retrieval/source-anchor/read",
                    headers=headers,
                    json={
                        "schema": "dmb_world_graph_source_anchor_read_request_v1",
                        "worldId": case.packet.native_world_id,
                        "campaignId": "",
                        "scopeMode": "world",
                        "focus": {"kind": "none"},
                        "admissibility": "gm",
                        "revisionPin": child,
                        "anchorId": opened["anchor_id"],
                        "maxChars": 12000,
                    },
                )
                assert response.status_code == 200
                assert (
                    hashlib.sha256(response.json()["content"].encode()).hexdigest()
                    == opened["content_sha256"]
                )

    asyncio.run(mounted())
    assert (
        case.bundle.world_graph.get_head(case.packet.native_world_id).head_revision_id
        == child
    )
    assert "Synthetic reviewed statement" not in json.dumps(
        case.store.read(case.packet.operation_id)
    )
