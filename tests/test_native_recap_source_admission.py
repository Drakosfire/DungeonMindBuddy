"""Provider-free ordinary HTTP with disposable APP and Core PostgreSQL authority."""

from __future__ import annotations
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace
import json
import os
from uuid import uuid4
from psycopg.conninfo import conninfo_to_dict
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from alembic import command
from alembic.config import Config
from dungeonmind.application.vnext import initialize_empty_knowledge_space
from dungeonmind.infrastructure.postgres import (
    PostgresDatabase,
    PostgresNativeSourceEvidenceRepository,
)
from application_state.ingest import service as ingest
from application_state.errors import ApplicationStateConflictError
from application_state.source import service as sources
from graph_memory.ingestion.native_recap_source import KEY, Record
from graph_memory.vnext.domain_runtime import (
    dungeonbuddy_world_domain_contract,
    dungeonbuddy_dnd5e_custom_predicate_profile,
)
from apps.live_control_server import config
from apps.live_control_server.routes import recap_ingest as route
from apps.live_control_server.services import native_recap_source_admission as service
from apps.live_control_server.services.world_container_registry import (
    create_world_container,
)
from apps.live_control_server.integrations.dungeonmind.native_recap_source_admission import (
    NativeRecapAuthority,
)

TOKEN = "synthetic-operator-credential-for-recap-boundary-tests"
NOW = datetime(2026, 10, 30, tzinfo=UTC)


@pytest.fixture
def native_core_dsn(monkeypatch):
    import psycopg
    from psycopg import sql

    admin = os.environ.get("DMB_NATIVE_RECAP_TEST_ADMIN_DSN", "")
    if not admin:
        pytest.skip(
            "DMB_NATIVE_RECAP_TEST_ADMIN_DSN requires an existing vector-capable disposable-test service"
        )
    assert conninfo_to_dict(admin)["host"] in {"127.0.0.1", "localhost", "::1"}
    name = "dmb_recap_source_test_" + uuid4().hex[:12]
    with psycopg.connect(admin, autocommit=True) as conn:
        conn.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
    print("NATIVE_FIXTURE_CREATED", name)
    from sqlalchemy import URL
    params = conninfo_to_dict(admin)
    dsn = URL.create("postgresql", username=params.get("user"),
                     password=params.get("password"), host=params["host"],
                     port=int(params.get("port", "5432")), database=name).render_as_string(hide_password=False)
    try:
        import dungeonmind

        monkeypatch.setenv("DUNGEONMIND_DATABASE_URL", dsn)
        cfg = Config()
        cfg.set_main_option(
            "script_location",
            str(Path(os.environ.get("DMB_NATIVE_RECAP_TEST_CORE_ROOT",
                                    str(Path(dungeonmind.__file__).resolve().parent.parent))) / "migrations"),
        )
        command.upgrade(cfg, "head")
        yield dsn
    finally:
        with psycopg.connect(admin, autocommit=True) as conn:
            conn.execute(
                "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname=%s",
                (name,),
            )
            conn.execute(sql.SQL("DROP DATABASE {}").format(sql.Identifier(name)))
        print("NATIVE_FIXTURE_DROPPED", name)


@pytest.fixture
def lane(tmp_path, monkeypatch, application_state_dsn, native_core_dsn):
    # One existing fixture-owned disposable database, two explicitly namespaced owners.
    from psycopg.conninfo import conninfo_to_dict

    assert conninfo_to_dict(application_state_dsn)["dbname"].startswith(
        "dungeonbuddy_app_state_test_"
    )
    monkeypatch.setenv(config.ARTIFACT_DATA_ROOT_ENV, str(tmp_path))
    monkeypatch.setenv(config.MANAGED_WORLD_DATA_ROOT_ENV, str(tmp_path))
    monkeypatch.setenv("DMB_DEPLOYMENT_ENVIRONMENT", "local")
    monkeypatch.setenv("DMB_AUTH_MODE", "local_operator")
    monkeypatch.setenv("DMB_AGENT_GRAPH_AUTH_MODE", "local_operator")
    monkeypatch.setenv("DMB_AGENT_GRAPH_AUTH_ENVIRONMENT", "local")
    monkeypatch.setenv("DMB_AGENT_GRAPH_LOCAL_OPERATOR_TOKEN", TOKEN)
    monkeypatch.setattr(
        config, "world_graph_authority_database_url", lambda: native_core_dsn
    )
    world = create_world_container(
        tmp_path, name="Native recap fixture", owner_subject="recap-owner"
    )
    native = world.native_graph_binding.native_world_id
    repo = PostgresNativeSourceEvidenceRepository(PostgresDatabase(native_core_dsn))
    initialize_empty_knowledge_space(
        repository=repo,
        space_id=native,
        initialization_id="fixture-native-genesis",
        created_at=NOW,
        domain_contract=dungeonbuddy_world_domain_contract(),
        semantic_profile=dungeonbuddy_dnd5e_custom_predicate_profile(),
    )
    text = "# Session 8\n\nTorbin reported strange meat and an Arcana result.\n"
    selection = register_source(tmp_path, native, text)
    context = SimpleNamespace(
        managed_world_id=world.world_id,
        native_world_id=native,
        binding_version=1,
        campaign_id="campaign",
    )
    monkeypatch.setattr(route, "repo_root", lambda: tmp_path)
    for name in ("_pipeline_corpus_root", "inspect_recap_ingest_status",
                 "_normalized_recap_graph_path", "_request_recap_context"):
        monkeypatch.setattr(route, name, lambda *_a, **_k: pytest.fail("Source intake used legacy file/broker selection"))
    import httpx

    monkeypatch.setattr(
        httpx.HTTPTransport,
        "handle_request",
        lambda *_: pytest.fail(
            "No external/provider HTTP transport in source-only tests"
        ),
    )
    app = FastAPI()
    app.include_router(route.router)
    client = TestClient(app, client=("127.0.0.1", 50000))
    body = {
        "operation": "build_graph_preview_bundle",
        "managed_world_id": world.world_id,
        "campaign_id": "campaign",
        "session": 8,
        "include_graph_extraction": False,
        "native_recap_source": selection,
    }
    return SimpleNamespace(
        root=tmp_path,
        world=world,
        repo=repo,
        text=text,
        selection=selection,
        context=context,
        client=client,
        body=body,
        headers={"Authorization": "Bearer " + TOKEN},
        dsn=application_state_dsn,
    )


def register_source(root, world, text):
    from apps.live_control_server.services.source_artifact_registry import create_recap_source_artifact
    artifact = create_recap_source_artifact(
        root, world_id=world, campaign_id="campaign", session_id="session-8", recap_text=text
    )
    source = sources.get_source_markdown(source_artifact_id=artifact.source_artifact_id,
                                         content_sha256=artifact.content_sha256)
    return {"source_artifact_id": artifact.source_artifact_id,
            "source_revision_id": str(source.source_revision_id),
            "content_sha256": source.content_sha256}


def post(lane, **extra):
    body = {**lane.body, **extra}
    if extra.get("native_recap_resume") is not None or extra.get("native_recap_run_id") is not None:
        body.pop("native_recap_source", None)
    return lane.client.post("/api/live/recap-ingest", json=body, headers=lane.headers)


def native(response):
    assert response.status_code == 200, response.text
    return response.json()["native_recap_source"]


def inspection(lane, status):
    return lane.client.post(
        status["status_request"]["path"],
        json=status["status_request"]["body"],
        headers=lane.headers,
    )


def resume(status):
    return {
        "run_id": status["run_id"],
        "expected_run_revision": status["run_revision"],
        "command_sha256": status["command_sha256"],
    }


def tree(root):
    return {
        str(p.relative_to(root)): sha256(p.read_bytes()).hexdigest()
        for p in root.rglob("*")
        if p.is_file()
    }


def test_ordinary_http_admits_exact_APP_version_and_reopens_without_provider(
    lane, monkeypatch
):
    monkeypatch.setattr(
        route,
        "extract_recap",
        lambda **_: pytest.fail("Classic preview/model path is not source admission"),
    )
    before = lane.repo.get_head(lane.context.native_world_id)
    value = native(post(lane))
    assert value["state"] == "admitted", value
    assert value["admission_committed"] and value["opening"]["state"] == "verified"
    assert value["schema_version"] == "dmb_native_recap_source_status_v2"
    assert "raw_original_sha256" not in value and "normalization_policy" not in value
    canonical = lane.text
    assert value["app_body_sha256"] == sha256(canonical.encode()).hexdigest()
    run = ingest.get_extraction_run(value["run_id"])
    assert run.components == {} and run.status.value == "draft"
    record = Record.model_validate(run.lineage[KEY])
    assert "body_text" not in record.command.request
    source = sources.get_source_markdown(
        source_artifact_id=value["app_source_artifact_id"],
        content_sha256=value["app_body_sha256"],
    )
    assert str(source.source_revision_id) == value["app_source_revision_id"]
    assert source.markdown == canonical
    assert value["app_source_revision_id"] == lane.selection["source_revision_id"]
    assert "raw_original_sha256" not in record.model_dump()
    after = lane.repo.get_head(lane.context.native_world_id)
    assert after != before
    assert native(post(lane)) == value
    before_files = tree(lane.root)
    monkeypatch.setattr(
        service.PublicationProgressStore,
        "exclusive",
        lambda *_: pytest.fail("Read-only inspection acquired a file lock"),
    )
    monkeypatch.setattr(
        service, "_cas", lambda *_: pytest.fail("Read-only inspection wrote APP")
    )
    monkeypatch.setattr(
        NativeRecapAuthority,
        "dispatch",
        lambda *_: pytest.fail("Read-only inspection published"),
    )
    assert native(inspection(lane, value)) == value
    assert (
        tree(lane.root) == before_files
        and lane.repo.get_head(lane.context.native_world_id) == after
    )


def test_auth_and_foreign_scope_refuse_before_source_effects(lane, monkeypatch):
    monkeypatch.setattr(
        service,
        "get_source_artifact",
        lambda *_: pytest.fail("unauthorized request read sensitive source context"),
    )
    before = tree(lane.root)
    assert lane.client.post("/api/live/recap-ingest", json=lane.body).status_code == 401
    assert (
        lane.client.post(
            "/api/live/recap-ingest",
            json=lane.body,
            headers={"Authorization": "Bearer wrong"},
        ).status_code
        == 401
    )
    assert tree(lane.root) == before and not ingest.list_extraction_runs()


def test_unknown_delivery_preserves_first_failure_and_only_explicit_resume_replays(
    lane, monkeypatch
):
    original = NativeRecapAuthority.dispatch
    calls = []

    def lost(self, record, body):
        calls.append(record.command.resolve(body).model_dump(mode="json"))
        raise ConnectionError("synthetic transport loss")

    monkeypatch.setattr(NativeRecapAuthority, "dispatch", lost)
    failed = native(post(lane))
    assert (
        failed["state"] == "unknown"
        and failed["failure_code"] == "native_recap_dispatch_unknown"
    )
    assert native(post(lane)) == failed and len(calls) == 1
    monkeypatch.setattr(
        NativeRecapAuthority,
        "dispatch",
        lambda self, r, b: (
            calls.append(r.command.resolve(b).model_dump(mode="json"))
            or original(self, r, b)
        ),
    )
    recovered = native(post(lane, native_recap_resume=resume(failed)))
    assert recovered["state"] == "admitted"
    assert calls[0] == calls[1]
    record = Record.model_validate(
        ingest.get_extraction_run(recovered["run_id"]).lineage[KEY]
    )
    assert [d.state for d in record.command.deliveries] == ["unknown", "committed"]
    assert len(record.commands) == 1 and recovered["run_id"] == failed["run_id"]


def test_commit_then_response_loss_is_visible_without_settlement_and_explicitly_recoverable(
    lane, monkeypatch
):
    original = NativeRecapAuthority.dispatch

    def lost(self, record, body):
        original(self, record, body)
        raise ConnectionError("synthetic acknowledgement loss")

    monkeypatch.setattr(NativeRecapAuthority, "dispatch", lost)
    value = native(post(lane))
    assert value["admission_committed"] and value["state"] == "admitted"
    record = Record.model_validate(
        ingest.get_extraction_run(value["run_id"]).lineage[KEY]
    )
    assert record.receipt is None and record.state == "unknown"
    monkeypatch.setattr(
        NativeRecapAuthority,
        "dispatch",
        lambda *_: pytest.fail("Committed effect was redispatched"),
    )
    assert native(inspection(lane, value)) == value
    wrong = {**resume(value), "expected_run_revision": value["run_revision"] + 1}
    assert post(lane, native_recap_resume=wrong).status_code == 409
    value = native(post(lane, native_recap_resume=resume(value)))
    assert value["admission_committed"]
    assert (
        Record.model_validate(
            ingest.get_extraction_run(value["run_id"]).lineage[KEY]
        ).receipt
        is not None
    )


def test_player_foreign_request_and_wrong_status_scope_fail_closed(lane, monkeypatch):
    from apps.live_control_server.services import agent_graph_auth as auth

    original = auth.authenticate_native_graph_principal
    monkeypatch.setattr(
        auth,
        "authenticate_native_graph_principal",
        lambda _: auth.NativeGraphPrincipal(
            subject="player", role="player", auth_method="local_operator"
        ),
    )
    assert post(lane).status_code == 403 and not ingest.list_extraction_runs()
    monkeypatch.setattr(auth, "authenticate_native_graph_principal", original)
    assert (
        post(lane, managed_world_id="foreign-world").status_code == 409
        and not ingest.list_extraction_runs()
    )
    value = native(post(lane))
    request = {**value["status_request"]["body"], "session": 9}
    assert (
        lane.client.post(
            "/api/live/recap-ingest", json=request, headers=lane.headers
        ).status_code
        == 409
    )
    assert native(inspection(lane, value)) == value


def test_changed_source_gets_new_origin_and_bad_APP_or_generic_update_refuses(lane):
    from application_state.errors import ApplicationStateConflictError
    from graph_memory.ingestion.extraction_run import ExtractionRunStatus

    first = native(post(lane))
    selection = register_source(lane.root, lane.context.native_world_id,
                                lane.text + "Another independently imported paragraph.\n")
    second = native(post(lane, native_recap_source=selection))
    assert (
        first["app_source_revision_id"] != second["app_source_revision_id"]
        and first["admission_id"] != second["admission_id"]
    )
    assert native(inspection(lane, first))["opening"]["state"] == "verified"
    run = ingest.get_extraction_run(first["run_id"])
    with pytest.raises(ApplicationStateConflictError):
        ingest.update_extraction_run(
            run.run_id,
            status=ExtractionRunStatus.PREPARED,
            expected_revision=run.revision,
            lineage={},
        )
    value = run.lineage[KEY].copy()
    value["app_body_sha256"] = "a" * 64
    with pytest.raises(ApplicationStateConflictError):
        ingest.update_native_recap_source(
            run.run_id, expected_revision=run.revision, record=value
        )
    assert ingest.get_extraction_run(first["run_id"]) == run


def test_definitive_prewrite_stale_requires_explicit_new_parent_and_keeps_attempt(
    lane, monkeypatch
):
    from dungeonmind.application.vnext import publish_native_text_source_evidence

    original = NativeRecapAuthority.prepare
    count = []

    def advanced(self, record, body):
        frozen = original(self, record, body)
        if not count:
            count.append(True)
            request = frozen.resolve(body).model_copy(
                update={"admission_id": "unrelated-source-head-advance"}
            )
            publish_native_text_source_evidence(
                repository=lane.repo,
                request=request,
                domain_contract=dungeonbuddy_world_domain_contract(),
                semantic_profile=dungeonbuddy_dnd5e_custom_predicate_profile(),
            )
        return frozen

    monkeypatch.setattr(NativeRecapAuthority, "prepare", advanced)
    first = native(post(lane))
    assert (
        first["state"] == "conflict"
        and first["failure_code"] == "native_recap_prewrite_stale"
    )
    assert native(post(lane)) == first
    second = native(post(lane, native_recap_resume=resume(first)))
    assert second["state"] == "admitted"
    record = Record.model_validate(
        ingest.get_extraction_run(second["run_id"]).lineage[KEY]
    )
    assert len(record.commands) == 2
    assert (
        record.commands[0].deliveries[0].state == "stale"
        and record.commands[0].request["expected_parent_revision_id"]
        != record.commands[1].request["expected_parent_revision_id"]
    )


def test_commit_survives_opening_and_APP_settlement_failure(lane, monkeypatch):
    actual = service._cas

    def failed_settlement(run, record):
        if record.receipt:
            raise ApplicationStateConflictError("synthetic private-command-SENTINEL")
        return actual(run, record)

    monkeypatch.setattr(service, "_cas", failed_settlement)
    response = post(lane)
    assert response.status_code == 409 and "SENTINEL" not in response.text
    (run,) = ingest.list_extraction_runs()
    body = {
        "operation": "inspect_status",
        "managed_world_id": lane.world.world_id,
        "campaign_id": "campaign",
        "session": 8,
        "native_recap_run_id": run.run_id,
    }
    value = native(
        lane.client.post("/api/live/recap-ingest", json=body, headers=lane.headers)
    )
    assert value["admission_committed"] and value["state"] == "admitted"
    monkeypatch.setattr(service, "_cas", actual)
    original_verify = NativeRecapAuthority.verify
    monkeypatch.setattr(
        NativeRecapAuthority, "verify", lambda *_: service.Opening(state="unavailable")
    )
    retained = native(post(lane, native_recap_resume=resume(value)))
    assert retained["admission_committed"] and retained["state"] == "unavailable"
    assert (
        Record.model_validate(
            ingest.get_extraction_run(run.run_id).lineage[KEY]
        ).receipt
        is not None
    )
    monkeypatch.setattr(NativeRecapAuthority, "verify", original_verify)
    assert native(inspection(lane, retained))["state"] == "admitted"


def test_process_contention_hard_crash_and_exact_same_command_recovery(
    lane, monkeypatch
):
    import multiprocessing

    ctx = multiprocessing.get_context("fork")
    parent, child = ctx.Pipe()
    original = NativeRecapAuthority.dispatch

    def entered(self, record, body):
        child.send(record.command.resolve(body).model_dump(mode="json"))
        child.recv()
        return original(self, record, body)

    monkeypatch.setattr(NativeRecapAuthority, "dispatch", entered)
    worker = ctx.Process(target=lambda: post(lane))
    worker.start()
    try:
        assert parent.poll(15), "Child never entered durable dispatch"
        frozen = parent.recv()
        (run,) = ingest.list_extraction_runs()
        record = Record.model_validate(run.lineage[KEY])
        assert record.state == "entered"
        busy = native(
            post(
                lane,
                native_recap_resume={
                    "run_id": run.run_id,
                    "expected_run_revision": run.revision,
                    "command_sha256": record.command.sha256,
                },
            )
        )
        assert (
            busy["failure_code"] == "native_recap_operation_busy"
            and ingest.get_extraction_run(run.run_id).revision == run.revision
        )
        worker.kill()
        worker.join(5)
        assert not worker.is_alive()
        monkeypatch.setattr(NativeRecapAuthority, "dispatch", original)
        # No clock/age inference: the process lock is released by the kernel.
        pending = native(post(lane))
        assert pending["state"] == "dispatching"
        actual = []
        monkeypatch.setattr(
            NativeRecapAuthority,
            "dispatch",
            lambda self, r, b: (
                actual.append(r.command.resolve(b).model_dump(mode="json"))
                or original(self, r, b)
            ),
        )
        recovered = native(post(lane, native_recap_resume=resume(pending)))
        assert recovered["state"] == "admitted" and actual == [frozen]
        record = Record.model_validate(
            ingest.get_extraction_run(run.run_id).lineage[KEY]
        )
        assert [d.state for d in record.command.deliveries] == ["entered", "committed"]
    finally:
        if worker.is_alive():
            worker.kill()
            worker.join(5)
        parent.close()
        child.close()


def test_public_run_routes_and_catalog_omit_only_private_lineage(lane, monkeypatch):
    value = native(post(lane))
    run = ingest.get_extraction_run(value["run_id"])
    poisoned = run.model_copy(
        update={
            "lineage": {
                **run.lineage,
                "public-note": "keep",
                "native_recap_source": {"secret": "private-SENTINEL"},
            }
        }
    )
    assert "private-SENTINEL" not in json.dumps(service.public_run(poisoned))
    assert poisoned.lineage[KEY] == {"secret": "private-SENTINEL"}
    from apps.live_control_server.services import ingest_run_catalog as catalog

    monkeypatch.setattr(catalog, "list_extraction_runs", lambda: [poisoned])
    assert catalog.list_canonical_extraction_runs()["runs"][0]["lineage"] == {
        k: v for k, v in poisoned.lineage.items() if k != KEY
    }
    from apps.live_control_server.routes import graph_preview
    from apps.live_control_server.services import graph_run_registry

    monkeypatch.setattr(graph_run_registry, "get_extraction_run", lambda *_: poisoned)
    assert "private-SENTINEL" not in json.dumps(
        graph_preview.get_extraction_run_by_id(run.run_id)
    )
    assert KEY in ingest.get_extraction_run(run.run_id).lineage


def hosted_client(lane, monkeypatch, subject="recap-owner"):
    from apps.live_control_server import main
    from apps.live_control_server.services.dms_principal import DmsPrincipal

    monkeypatch.setenv("DMB_DEPLOYMENT_ENVIRONMENT", "production")
    monkeypatch.setenv("DMB_AUTH_MODE", "hosted_dms")
    monkeypatch.setenv("DMB_NATIVE_RECAP_EXECUTION_SCOPE", "single_host_shared_root")
    monkeypatch.setenv("AUTH_TRUSTED_FRONTEND_ORIGINS", "https://buddy.dungeonmind.net")
    monkeypatch.setenv(
        "DMB_HOSTED_WORLD_ACCESS_JSON",
        json.dumps(
            {
                lane.world.world_id: ["recap-owner", "recap-reader"],
            }
        ),
    )
    application = main.create_app()
    assert not any(
        getattr(r, "path", "").startswith("/api/live/graph-preview/")
        for r in application.routes
    )

    async def resolve(_):
        return DmsPrincipal(subject=subject) if subject else None

    application.state.dms_principal_resolver = resolve
    return TestClient(application, client=("127.0.0.1", 50000))


def test_status_has_no_file_scan_or_mutation_and_survives_production_router_omission(
    lane, monkeypatch
):
    value = native(post(lane))
    client = hosted_client(lane, monkeypatch)
    monkeypatch.setattr(
        route, "_pipeline_corpus_root", lambda: pytest.fail("Status scanned corpus")
    )
    monkeypatch.setattr(
        service.PublicationProgressStore,
        "exclusive",
        lambda *_: pytest.fail("Status created lock files"),
    )
    monkeypatch.setattr(service, "_cas", lambda *_: pytest.fail("Status wrote APP"))
    before_files = tree(lane.root)
    assert (
        native(
            client.post(
                "/api/live/recap-ingest",
                json=value["status_request"]["body"],
                headers={"Origin": "https://buddy.dungeonmind.net"},
            )
        )
        == value
    )
    assert tree(lane.root) == before_files


def test_hosted_owner_admits_with_real_subject_and_authority_basis(lane, monkeypatch):
    client = hosted_client(lane, monkeypatch)
    value = native(
        client.post(
            "/api/live/recap-ingest",
            json=lane.body,
            headers={"Origin": "https://buddy.dungeonmind.net"},
        )
    )
    assert value["admission_committed"]
    record = Record.model_validate(
        ingest.get_extraction_run(value["run_id"]).lineage[KEY]
    )
    assert (record.created_by, record.created_authority_basis) == (
        "recap-owner",
        "world_manage",
    )
    assert (
        record.command.deliveries[0].actor,
        record.command.deliveries[0].authority_basis,
    ) == ("recap-owner", "world_manage")


def test_hosted_boundary_refuses_before_sensitive_IO_and_never_falls_back(
    lane, monkeypatch
):
    from apps.live_control_server.services.world_container_registry import (
        grant_world_access,
    )

    grant_world_access(
        lane.root,
        lane.world.world_id,
        actor_subject="recap-owner",
        subject="recap-reader",
        permissions=["read"],
    )
    client = hosted_client(lane, monkeypatch, "recap-reader")
    monkeypatch.setattr(
        route,
        "_request_recap_context",
        lambda *_: pytest.fail("Unauthorized source read"),
    )
    monkeypatch.setattr(
        service, "inspect", lambda *_: pytest.fail("Unauthorized APP/native read")
    )
    headers = {**lane.headers, "Origin": "https://buddy.dungeonmind.net"}
    before_files = tree(lane.root)
    assert (
        client.post(
            "/api/live/recap-ingest", json=lane.body, headers=headers
        ).status_code
        == 403
    )
    client = hosted_client(lane, monkeypatch, None)
    assert (
        client.post(
            "/api/live/recap-ingest", json=lane.body, headers=headers
        ).status_code
        == 401
    )
    client = hosted_client(lane, monkeypatch)
    assert (
        client.post(
            "/api/live/recap-ingest", json=lane.body, headers=lane.headers
        ).status_code
        == 403
    )
    for changes in (
        {"operation": "generate_recap_memory"},
        {"extract_graph": True},
        {"unknown_field": "private-SENTINEL"},
        {"managed_world_id": "unknown-world"},
    ):
        response = client.post(
            "/api/live/recap-ingest", json={**lane.body, **changes}, headers=headers
        )
        assert response.status_code == 403
        assert "private-SENTINEL" not in response.text
    monkeypatch.setenv("DMB_AUTH_MODE", "local_operator")
    assert (
        client.post(
            "/api/live/recap-ingest", json=lane.body, headers=headers
        ).status_code
        == 503
    )
    assert tree(lane.root) == before_files


def test_hosted_status_cannot_use_owned_world_to_read_foreign_run(lane, monkeypatch):
    value = native(post(lane))
    foreign = create_world_container(
        lane.root, name="Other owned World", owner_subject="recap-owner"
    )
    client = hosted_client(lane, monkeypatch)
    monkeypatch.setenv(
        "DMB_HOSTED_WORLD_ACCESS_JSON", json.dumps({foreign.world_id: ["recap-owner"]})
    )
    response = client.post(
        "/api/live/recap-ingest",
        json={
            **value["status_request"]["body"],
            "managed_world_id": foreign.world_id,
        },
        headers={"Origin": "https://buddy.dungeonmind.net"},
    )
    assert response.status_code == 409
    assert "source_revision_id" not in response.text


def test_production_registration_is_shared_with_configuration_validation(
    lane, monkeypatch
):
    from apps.live_control_server import main
    from apps.live_control_server.services import hosted_auth

    hosted_client(lane, monkeypatch)
    # Configuration validation does not connect. Distinct role names model the hosted least-privilege roles;
    # the owning repository calls above use the existing disposable-test database credentials.
    environment = dict(os.environ)
    environment.update(
        {
            "DUNGEONMIND_SERVER_API_ORIGIN": "https://auth.example.test",
            "DUNGEONBUDDY_APPLICATION_STATE_DATABASE_URL": "postgresql://app_owner@localhost/app_fixture",
            "DUNGEONMIND_WORLD_GRAPH_AUTHORITY_DATABASE_URL": "postgresql://native_owner@localhost/native_fixture",
            "DUNGEONMIND_LIVE_SESSION_DIR": str(lane.root),
            "DUNGEONMIND_WORLD_GRAPH_ROOT": str(lane.root),
        }
    )
    assert (
        hosted_auth.validate_hosted_auth_configuration(
            environment, world_scope_resolvers=main.HOSTED_WORLD_SCOPE_RESOLVERS
        )
        == ()
    )
    assert (
        hosted_auth.HOSTED_WORLD_ROUTE_POLICY_ERROR
        in hosted_auth.validate_hosted_auth_configuration(environment)
    )
    environment.pop("DUNGEONMIND_SERVER_API_ORIGIN")
    assert (
        "DUNGEONMIND_SERVER_API_ORIGIN"
        in hosted_auth.validate_hosted_auth_configuration(
            environment, world_scope_resolvers=main.HOSTED_WORLD_SCOPE_RESOLVERS
        )
    )


def test_live_Core_commit_retains_mutex_until_kill_then_settles_without_redispatch(
    lane, monkeypatch
):
    import multiprocessing

    ctx = multiprocessing.get_context("fork")
    parent, child = ctx.Pipe()
    original = NativeRecapAuthority.dispatch

    def slow_response(self, record, body):
        receipt = original(self, record, body)
        child.send(receipt.model_dump(mode="json"))
        child.recv()  # Core has committed; the caller still owns the operation.
        return receipt

    monkeypatch.setattr(NativeRecapAuthority, "dispatch", slow_response)
    worker = ctx.Process(target=lambda: post(lane))
    worker.start()
    try:
        assert parent.poll(15), "Core never committed the child request"
        receipt = parent.recv()
        (run,) = ingest.list_extraction_runs()
        record = Record.model_validate(run.lineage[KEY])
        assert record.receipt is None and record.state == "entered"
        status = service.inspect(
            lane.root, run.run_id, lane.world.world_id, "campaign", 8
        )
        assert status.admission_committed and status.opening.state == "verified"
        before = run.revision
        busy = native(
            post(lane, native_recap_resume=resume(status.model_dump(mode="json")))
        )
        assert busy["failure_code"] == "native_recap_operation_busy"
        assert ingest.get_extraction_run(run.run_id).revision == before
        worker.kill()
        worker.join(5)
        assert not worker.is_alive()
        monkeypatch.setattr(
            NativeRecapAuthority,
            "dispatch",
            lambda *_: pytest.fail("Redispatched committed effect"),
        )
        final = native(
            post(lane, native_recap_resume=resume(status.model_dump(mode="json")))
        )
        settled = Record.model_validate(
            ingest.get_extraction_run(run.run_id).lineage[KEY]
        )
        assert (
            final["state"] == "admitted"
            and settled.receipt.model_dump(mode="json") == receipt
        )
        assert settled.command.deliveries[0].state == "committed"
    finally:
        if worker.is_alive():
            worker.kill()
            worker.join(5)
        parent.close()
        child.close()


def test_hosted_execution_requires_explicit_single_host_topology(lane, monkeypatch):
    client = hosted_client(lane, monkeypatch)
    monkeypatch.delenv("DMB_NATIVE_RECAP_EXECUTION_SCOPE")
    before = tree(lane.root)
    response = client.post(
        "/api/live/recap-ingest",
        json=lane.body,
        headers={"Origin": "https://buddy.dungeonmind.net"},
    )
    assert response.status_code == 503
    assert (
        response.json()["detail"]["code"]
        == "native_recap_execution_topology_unsupported"
    )
    assert tree(lane.root) == before and ingest.list_extraction_runs() == []


def test_generic_run_cannot_inject_or_drop_source_admission_intent(lane):
    from application_state.errors import ApplicationStateValidationError
    from graph_memory.ingestion.extraction_run import ExtractionRunStatus

    status = native(post(lane))
    run = ingest.get_extraction_run(status["run_id"])
    with pytest.raises(ApplicationStateValidationError):
        ingest.create_extraction_run(
            run.model_copy(update={"run_id": str(uuid4()), "lineage": {}})
        )
    ordinary = ingest.create_extraction_run(
        run.model_copy(
            update={
                "run_id": str(uuid4()),
                "lineage": {},
                "profile_id": "ordinary-extraction",
            }
        )
    )
    with pytest.raises(ApplicationStateConflictError):
        ingest.update_extraction_run(
            ordinary.run_id,
            status=ExtractionRunStatus.PREPARED,
            expected_revision=ordinary.revision,
            lineage=run.lineage,
        )
    assert ingest.get_extraction_run(ordinary.run_id) == ordinary


def test_source_budget_is_enforced_by_native_preflight(lane):
    from dungeonmind.contracts.vnext.native_source import MAX_NATIVE_TEXT_BYTES
    selection = register_source(lane.root, lane.context.native_world_id,
                                "x" * (MAX_NATIVE_TEXT_BYTES + 1))
    before = lane.repo.get_head(lane.context.native_world_id)
    value = native(post(lane, native_recap_source=selection))
    assert value["state"] == "reserved" and value["failure_code"]
    assert not value["admission_committed"]
    assert lane.repo.get_head(lane.context.native_world_id) == before


@pytest.mark.parametrize("changes", [
    {"source_domain": "worldbuilding"}, {"artifact_kind": "image"},
    {"world_id": None}, {"world_id": "foreign"}, {"campaign_id": "foreign"},
    {"session_id": "session-9"}, {"content_sha256": "a" * 64},
    {"status": "superseded"}, {"source_artifact_id": "artifact:recap:v2:" + "a" * 64},
])
def test_descriptor_mismatch_refuses_before_native_effects(lane, monkeypatch, changes):
    actual = service.get_source_artifact
    monkeypatch.setattr(service, "get_source_artifact",
                        lambda *a: actual(*a).model_copy(update=changes))
    before = lane.repo.get_head(lane.context.native_world_id)
    assert post(lane).status_code == 409
    assert not ingest.list_extraction_runs()
    assert lane.repo.get_head(lane.context.native_world_id) == before


def test_reader_fence_preserves_old_rows_blocks_old_writers_and_refuses_downgrade(
    lane, monkeypatch
):
    from application_state import cli
    from application_state.errors import ApplicationStateMigrationError
    from graph_memory.ingestion.extraction_run import ExtractionRun, ExtractionRunStatus

    cfg = cli.alembic_config()
    head = cli._alembic_head()
    assert cli._read_current_revision(lane.dsn) == head
    retained = ingest.create_extraction_run(
        ExtractionRun.model_validate(
            {
                "run_id": "er_older_" + uuid4().hex,
                "source_artifact_id": "sa_older_fixture",
                "source_domain": "recap",
                "status": "draft",
                "revision": 1,
                "campaign_id": "campaign",
                "session_id": "session-8",
                "created_at": NOW.isoformat(),
                "updated_at": NOW.isoformat(),
                "components": {},
                "lineage": {},
            }
        )
    )
    assert ingest.get_extraction_run(retained.run_id) == retained
    status = native(post(lane))
    run = ingest.get_extraction_run(status["run_id"])
    with monkeypatch.context() as older:
        older.setattr(cli, "_alembic_head", lambda: "20261030_0095")
        with pytest.raises(ApplicationStateMigrationError):
            ingest.get_extraction_run(run.run_id)
        with pytest.raises(ApplicationStateMigrationError):
            ingest.update_extraction_run(
                run.run_id,
                status=ExtractionRunStatus.PREPARED,
                expected_revision=run.revision,
                lineage={},
            )
        with pytest.raises(ApplicationStateMigrationError):
            ingest.supersede_extraction_run(
                run.run_id,
                expected_revision=run.revision,
                successor=retained.model_copy(
                    update={"run_id": str(uuid4()), "supersedes_run_id": run.run_id}
                ),
            )
    assert ingest.get_extraction_run(run.run_id) == run
    with pytest.raises(RuntimeError, match="recovery forward"):
        command.downgrade(cfg, "20261030_0095")
    assert cli._read_current_revision(lane.dsn) == head
    assert native(inspection(lane, status)) == status
    assert ingest.get_extraction_run(retained.run_id) == retained


@pytest.mark.parametrize("changes", [
    {"source_revision_id": "00000000-0000-0000-0000-000000000001"},
    {"content_sha256": "a" * 64},
])
def test_wrong_exact_snapshot_refuses_without_native_effects(lane, changes):
    before = lane.repo.get_head(lane.context.native_world_id)
    assert post(lane, native_recap_source={**lane.selection, **changes}).status_code == 409
    assert not ingest.list_extraction_runs()
    assert lane.repo.get_head(lane.context.native_world_id) == before


@pytest.mark.parametrize("extra", [
    {"raw_text": "new input"}, {"include_graph_extraction": True},
    {"title": "another selector"}, {"force_graph_run": True},
    {"native_recap_run_id": "00000000-0000-0000-0000-000000000001"},
])
def test_exact_selection_cannot_mix_other_pipeline_actions(lane, extra):
    body = {**lane.body, **extra}
    assert lane.client.post("/api/live/recap-ingest", json=body, headers=lane.headers).status_code == 422
    assert not ingest.list_extraction_runs()


def test_missing_selection_refuses_before_source_io(lane, monkeypatch):
    monkeypatch.setattr(service, "get_source_artifact", lambda *_: pytest.fail("Missing selector read source"))
    response = post(lane, native_recap_source=None)
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "native_recap_source_selection_required"


@pytest.mark.parametrize("managed_override", [True, False])
def test_database_source_does_not_require_source_directory_or_uri(lane, monkeypatch, managed_override):
    if not managed_override:
        monkeypatch.delenv(config.MANAGED_WORLD_DATA_ROOT_ENV)
    actual = service.get_source_artifact
    monkeypatch.setattr(service, "get_source_artifact", lambda *a: actual(*a).model_copy(
        update={"uri": "file:///nonexistent/retired-source/Session8.md"}))
    artifacts = lane.root / "separate-artifact-store"
    monkeypatch.setenv(config.ARTIFACT_DATA_ROOT_ENV, str(artifacts))
    artifacts.mkdir()
    assert not (lane.root / lane.world.source_root_relpath).exists()
    monkeypatch.setattr(sources, "persist_source_markdown", lambda **_: pytest.fail("Intake recreated source"))
    value = native(post(lane))
    assert value["state"] == "admitted" and value["opening"]["state"] == "verified"
    assert native(inspection(lane, value)) == value
    assert native(post(lane, native_recap_resume=resume(value))) == value


@pytest.mark.parametrize("committed", [False, True])
def test_explicit_recovery_uses_frozen_APP_source_after_live_file_removed(
    lane, monkeypatch, committed
):
    actual = NativeRecapAuthority.dispatch

    def interrupted(self, record, body):
        if committed:
            actual(self, record, body)
        raise RuntimeError("synthetic interrupted delivery")

    monkeypatch.setattr(NativeRecapAuthority, "dispatch", interrupted)
    first = native(post(lane))
    run = ingest.get_extraction_run(first["run_id"])
    record = Record.model_validate(run.lineage[KEY])
    frozen = record.command.sha256
    # Recovery resolves the same immutable APP revision; no live corpus lookup.
    monkeypatch.setattr(
        route,
        "inspect_recap_ingest_status",
        lambda **_: pytest.fail("Recovery scanned live corpus"),
    )
    monkeypatch.setattr(
        route,
        "_request_recap_context",
        lambda *_: pytest.fail("Recovery retargeted live context"),
    )
    calls = []

    def dispatch(self, record, body):
        calls.append(record.command.sha256)
        return actual(self, record, body)

    monkeypatch.setattr(NativeRecapAuthority, "dispatch", dispatch)
    recovered = native(post(lane, native_recap_resume=resume(first)))
    assert recovered["state"] == "admitted"
    assert calls == ([] if committed else [frozen])
    settled = Record.model_validate(
        ingest.get_extraction_run(first["run_id"]).lineage[KEY]
    )
    assert settled.app_source_revision_id == record.app_source_revision_id
    assert settled.command.sha256 == frozen and settled.receipt is not None
    assert settled.command.deliveries[0].failure_code is not None


@pytest.mark.parametrize(
    "changes", [{"session": 9}, {"campaign_id": "another-campaign"}]
)
def test_source_grouping_must_match_exact_APP_scope(lane, changes):
    response = post(lane, **changes)
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "native_recap_source_grouping_mismatch"
    assert ingest.list_extraction_runs() == []


def test_intake_preserves_exact_APP_bytes_without_frontmatter_or_normalization(lane):
    from graph_memory.evidence.source_artifact import (
        GraphMemorySourceArtifact, build_world_scoped_recap_source_artifact_id,
    )
    body = "# Exact snapshot\r\n\r\nNo frontmatter or terminal newline."
    digest = sha256(body.encode()).hexdigest()
    artifact_id = build_world_scoped_recap_source_artifact_id(
        world_id=lane.context.native_world_id, campaign_id="campaign",
        session_id="session-8", content_sha256=digest,
    )
    descriptor = GraphMemorySourceArtifact(
        source_artifact_id=artifact_id, source_domain="recap", artifact_kind="recap_markdown",
        world_id=lane.context.native_world_id, campaign_id="campaign", session_id="session-8",
        content_sha256=digest, uri="file:///nonexistent/retired-source/Session8.md",
    )
    source = sources.persist_source_markdown(
        source_artifact_id=artifact_id, source_domain="recap", world_id=lane.context.native_world_id,
        campaign_id="campaign", session_id="session-8", markdown=body, content_sha256=digest,
        input_descriptor=descriptor.model_dump(mode="json"),
    )
    selection = {"source_artifact_id": artifact_id, "source_revision_id": str(source.source_revision_id),
                 "content_sha256": digest}
    result = native(post(lane, native_recap_source=selection))
    assert result["state"] == "admitted" and result["opening"]["body_sha256"] == digest
    assert sources.get_source_markdown(**selection) == source
    assert native(inspection(lane, result)) == result


def test_native_admission_identity_is_stable_across_record_version():
    record = Record(
        managed_world_id="synthetic-source-world", native_world_id="synthetic-native-source",
        binding_version=1, campaign_id="synthetic-campaign", session_id="session-8",
        app_source_artifact_id="artifact:recap:v2:" + "a" * 64,
        app_source_revision_id="00000000-0000-0000-0000-000000000001",
        app_body_sha256="b" * 64, created_by="identity-witness",
        created_authority_basis="local_gm", created_at=NOW,
    )
    # Frozen from the actual V1 implementation, not a second copy of the recipe.
    assert record.admission_id == "dmb-recap-source:67d20ea263489b9fb302b07a54f4f9c0a437b3b942a6ea583faeffba690e2a17"
    assert record.run_id == "a048576e-7182-5934-9560-8952a0ff5ccb"
    assert "normalization_policy" not in record.model_dump()


def test_existing_core_receipt_without_saved_command_refuses_without_duplicate(lane, monkeypatch):
    from graph_memory.ingestion.native_recap_source import SourceScope
    # Exercise a real Core commit whose APP command capture was lost. This must
    # not mint a replacement admission identity or fabricate a recovery command.
    source = sources.get_source_markdown(**lane.selection)
    scope = SourceScope(**vars(lane.context))
    record = Record(**scope.model_dump(), session_id="session-8",
                    app_source_artifact_id=source.source_artifact_id,
                    app_source_revision_id=source.source_revision_id,
                    app_body_sha256=source.content_sha256, created_by="recap-owner",
                    created_authority_basis="local_gm", created_at=source.created_at)
    authority = NativeRecapAuthority(lane.root)
    cmd = authority.prepare(record, source.markdown)
    frozen = record.model_copy(update={"commands": [cmd]})
    receipt = authority.dispatch(frozen, source.markdown)
    before = lane.repo.get_head(lane.context.native_world_id)
    monkeypatch.setattr(NativeRecapAuthority, "dispatch", lambda *_: pytest.fail("Duplicate native admission"))
    response = post(lane)
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "native_recap_saved_command_missing"
    repeat = native(post(lane))
    assert repeat["failure_code"] == "native_recap_saved_command_missing"
    assert repeat["state"] == "unavailable" and not repeat["admission_committed"]
    assert repeat["admission_id"] == receipt.admission_id
    assert post(lane, native_recap_resume=resume(repeat)).status_code == 409
    assert lane.repo.get_head(lane.context.native_world_id) == before
    assert authority.receipt(record) == receipt


pytestmark = pytest.mark.usefixtures("application_state_dsn")
