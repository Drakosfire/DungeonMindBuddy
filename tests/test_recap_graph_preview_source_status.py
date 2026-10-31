"""Recap status projects exact APP runs, never operational file manifests."""

from copy import deepcopy
from pathlib import Path

import psycopg
import pytest
from fastapi.testclient import TestClient

from apps.live_control_server.main import create_app
from apps.live_control_server.routes import recap_ingest as route
from apps.live_control_server.services import ingest_run_catalog as catalog
from apps.live_control_server.services import recap_graph_preview_ingest as service
from graph_memory.ingestion.extraction_run import ExtractionRunStatus as Status
from src.graph_memory.extraction.graph_preview_runner import (
    ProductionExtractionRequest,
    run_production_extraction,
)
from src.graph_memory.extraction.recap_extraction_profile import (
    RECAP_PROFILE_ID,
    RECAP_PROFILE_VERSION,
)
from tests.test_graph_preview_runner import (
    FixtureClient,
    _admit_recap,
    _first_paragraph_span_id,
    _recap_run_lineage,
)
from tests.test_recap_managed_standing_context import seed_binding

pytestmark = pytest.mark.usefixtures("application_state_dsn")
CONTEXT = {
    "schema": "dm_world_campaign_ingest_context_v1",
    "managed_world_id": "elderwyld",
    "native_world_id": "world:elderwyld",
    "binding_version": 3,
    "campaign_id": "longmont-c2",
    "head_revision_id": "rev:observed",
    "graph_schema": "dm_graph_v1",
    "graph_payload_sha256": "a" * 64,
}


@pytest.fixture
def setup(tmp_path, monkeypatch):
    monkeypatch.setenv("DMB_MANAGED_WORLD_DATA_ROOT", str(tmp_path))
    monkeypatch.setenv("DMB_ARTIFACT_DATA_ROOT", str(tmp_path))
    monkeypatch.setenv("DMB_DEPLOYMENT_ENVIRONMENT", "local")
    monkeypatch.setenv("DMB_AUTH_MODE", "local_operator")
    seed_binding(tmp_path, "elderwyld", "world:elderwyld", version=3)
    return tmp_path


def _case(root, *, mode="ok", context=None):
    if context and (
        context["native_world_id"] != CONTEXT["native_world_id"]
        or context["campaign_id"] != CONTEXT["campaign_id"]
    ):
        from apps.live_control_server.services.source_artifact_registry import (
            create_recap_source_artifact,
        )
        from tests.test_graph_preview_runner import _normalized_from_artifact

        path = root / "recap.md"
        path.write_text("Mirathorn is a river city.\n\nGuards watch the gate.\n")
        artifact = create_recap_source_artifact(
            root,
            world_id=context["native_world_id"],
            campaign_id=context["campaign_id"],
            session_id="session-24",
            recap_path=path,
        )
        source = _normalized_from_artifact(root, artifact.source_artifact_id)
    else:
        source = _admit_recap(root)
    client = FixtureClient(mode=mode, span_ref=_first_paragraph_span_id(source))
    result = run_production_extraction(
        ProductionExtractionRequest(
            repo_root=root,
            source=source,
            profile_id=RECAP_PROFILE_ID,
            profile_version=RECAP_PROFILE_VERSION,
            allow_llm=True,
            category_client=client,
            initial_lineage={
                **_recap_run_lineage(source),
                "world_campaign_ingest_context": context or CONTEXT,
            },
        )
    )
    assert result.run.status == (Status.REVIEWABLE if mode == "ok" else Status.FAILED)
    return source, result.run


def _client(root, monkeypatch, *, input_path=None):
    monkeypatch.setattr(route, "repo_root", lambda: root)
    monkeypatch.setattr(route, "_pipeline_corpus_root", lambda: None)
    status = {
        "schema": "dmb_raw_recap_ingest_status_v1",
        "campaign_id": "longmont-c2",
        "session": 24,
        "status": "recap_applied",
        "states": ["recap_applied", "normalized_current"],
        "paths": {"normalized_recap": str(input_path)} if input_path else {},
        "authority": {},
        "warnings": [],
        "errors": [],
        "next_actions": [],
        "ingest_report": {},
        "entity_spelling_audit": [],
    }
    monkeypatch.setattr(
        route, "inspect_recap_ingest_status", lambda **kwargs: deepcopy(status)
    )
    return TestClient(create_app(), client=("127.0.0.1", 50000))


def _inspect(client, **updates):
    return client.post(
        "/api/live/recap-ingest",
        json={
            "operation": "inspect_status",
            "managed_world_id": "elderwyld",
            "campaign_id": "longmont-c2",
            "session": 24,
            **updates,
        },
    )


def test_status_reloads_database_run_after_mirrors_are_deleted(setup, monkeypatch):
    root = setup
    _, run = _case(root)
    with _client(root, monkeypatch) as client:
        for path in root.rglob("*"):
            if path.is_file():
                path.unlink()
        def guarded(path, *args, **kwargs):
            pytest.fail(f"status reopened a retired file: {path}")

        with monkeypatch.context() as guard:
            guard.setattr(Path, "open", guarded)
            response = _inspect(client)
    assert response.status_code == 200, response.text
    graph = response.json()["ingest_report"]["graph_preview"]
    assert graph["extraction_run_id"] == run.run_id
    assert graph["status"] == "candidate_validation_ready"
    assert graph["source_match_mode"] == "retained_database"
    assert graph["node_count"] > 0
    assert graph["next_actions"] == ["review_candidate"]
    assert "manifest_path" not in graph and "candidate_graph_path" not in graph


def test_a_file_manifest_cannot_invent_an_extraction_run(setup, monkeypatch):
    root = setup
    folder = root / "out/graph_memory/runs/fake"
    folder.mkdir(parents=True)
    (folder / "graph_ingest_run_manifest.json").write_text(
        '{"status":"candidate_validation_ready","campaign_id":"longmont-c2","session_id":"session-24","diagnostics":{"extraction_run_id":"file-only"}}'
    )
    with _client(root, monkeypatch) as client:
        response = _inspect(client)
    assert response.status_code == 200, response.text
    graph = response.json()["ingest_report"]["graph_preview"]
    assert graph["status"] == "missing" and not graph.get("extraction_run_id")


@pytest.mark.parametrize(
    "field,value",
    [
        ("managed_world_id", "other-world"),
        ("native_world_id", "world:other"),
        ("binding_version", 4),
        ("campaign_id", "other-campaign"),
    ],
)
def test_saved_context_cannot_cross_the_current_scope(setup, monkeypatch, field, value):
    _case(setup, context={**CONTEXT, field: value})
    with _client(setup, monkeypatch) as client:
        response = _inspect(client)
    assert response.status_code == 200, response.text
    assert response.json()["ingest_report"]["graph_preview"]["status"] == "missing"


def test_missing_world_does_not_read_campaign_global_records(setup, monkeypatch):
    def forbidden(**kwargs):
        pytest.fail("unscoped request read database run catalog")

    monkeypatch.setattr(catalog, "list_extraction_runs", forbidden)
    with _client(setup, monkeypatch) as client:
        response = _inspect(client, managed_world_id=None)
    assert response.status_code == 200, response.text
    graph = response.json()["ingest_report"]["graph_preview"]
    assert graph["status"] == "missing" and graph["next_actions"] == []


@pytest.mark.parametrize(
    "kind", ["source_artifact", "candidate_graph", "source_span_index"]
)
@pytest.mark.parametrize("violation", ["missing", "corrupt"])
def test_file_mirrors_cannot_rescue_bad_database_evidence(
    setup, monkeypatch, application_state_dsn, kind, violation
):
    _, run = _case(setup)
    with psycopg.connect(application_state_dsn) as conn:
        if kind == "source_artifact":
            if violation == "missing":
                conn.execute(
                    "DELETE FROM source.revision WHERE source_artifact_id=%s",
                    (run.source_artifact_id,),
                )
            else:
                conn.execute(
                    "UPDATE source.revision SET markdown='corrupt' WHERE source_artifact_id=%s",
                    (run.source_artifact_id,),
                )
        elif violation == "missing":
            conn.execute(
                "DELETE FROM ingest.component_payload WHERE run_id=%s AND kind=%s",
                (run.run_id, kind),
            )
        else:
            conn.execute(
                "UPDATE ingest.component_payload SET payload=%s WHERE run_id=%s AND kind=%s",
                (b"corrupt", run.run_id, kind),
            )
    with _client(setup, monkeypatch) as client:
        response = _inspect(client)
    assert response.status_code in {409, 422, 500}, response.text
    assert response.json()["detail"]["code"] == catalog.CODE_INTEGRITY


def test_current_import_digest_does_not_select_another_source(setup, monkeypatch):
    source, run = _case(setup)
    original = setup / "original.md"
    original.write_text(source.source_text)
    with _client(setup, monkeypatch, input_path=original) as client:
        response = _inspect(client)
        graph = response.json()["ingest_report"]["graph_preview"]
        assert (
            graph["extraction_run_id"] == run.run_id
            and graph["source_match_mode"] == "content_digest"
        )
        original.write_text("Different source.\n")
        changed = _inspect(client)
    assert changed.status_code == 200, changed.text
    assert changed.json()["ingest_report"]["graph_preview"]["status"] == "missing"


def test_graph_head_changes_do_not_hide_source_bound_work(setup, monkeypatch):
    _, run = _case(
        setup,
        context={
            **CONTEXT,
            "head_revision_id": "rev:older",
            "graph_payload_sha256": "b" * 64,
        },
    )
    with _client(setup, monkeypatch) as client:
        response = _inspect(client)
    assert response.status_code == 200, response.text
    assert (
        response.json()["ingest_report"]["graph_preview"]["extraction_run_id"]
        == run.run_id
    )


def test_saved_failure_is_visible_without_reexecuting_or_leaking_details(
    setup, monkeypatch
):
    _, run = _case(setup, mode="refusal")
    monkeypatch.setattr(
        service,
        "run_recap_production_extraction",
        lambda **kwargs: pytest.fail("inspection ran extraction"),
    )
    with _client(setup, monkeypatch) as client:
        response = _inspect(client)
    assert response.status_code == 200, response.text
    graph = response.json()["ingest_report"]["graph_preview"]
    assert graph["extraction_run_id"] == run.run_id
    assert graph["status"] == "failed" and graph["extraction_mode"] == "llm_blocked"
    assert graph["next_actions"] == ["force_graph_run"]
    assert "model refused" not in response.text


@pytest.mark.parametrize("content", [b"", b" \n", b"\xff"])
def test_invalid_current_input_is_not_a_path_only_match(setup, monkeypatch, content):
    _case(setup)
    selected = setup / "selected.md"
    selected.write_bytes(content)
    with _client(setup, monkeypatch, input_path=selected) as client:
        response = _inspect(client)
    assert response.status_code == 200, response.text
    graph = response.json()["ingest_report"]["graph_preview"]
    assert graph["status"] == "source_unverified" and "extraction_run_id" not in graph


@pytest.mark.parametrize(
    "error_name,code",
    [
        ("ApplicationStateUnavailableError", catalog.CODE_UNAVAILABLE),
        ("ApplicationStateMigrationError", catalog.CODE_SCHEMA_UNAVAILABLE),
    ],
)
def test_database_outage_is_not_missing_work(setup, monkeypatch, error_name, code):
    from application_state import errors

    def fail(**kwargs):
        raise getattr(errors, error_name)("Database unavailable")

    monkeypatch.setattr(catalog, "list_extraction_runs", fail)
    with _client(setup, monkeypatch) as client:
        response = _inspect(client)
    assert response.status_code == 503, response.text
    assert response.json()["detail"]["code"] == code


def test_latest_failed_attempt_does_not_hide_behind_an_older_candidate(
    setup, monkeypatch
):
    _case(setup)
    _, latest = _case(setup, mode="refusal")
    with _client(setup, monkeypatch) as client:
        response = _inspect(client)
    assert response.status_code == 200, response.text
    graph = response.json()["ingest_report"]["graph_preview"]
    assert graph["extraction_run_id"] == latest.run_id and graph["status"] == "failed"


def test_corrupt_latest_attempt_does_not_fall_back_to_an_older_success(
    setup, monkeypatch, application_state_dsn
):
    _case(setup)
    _, latest = _case(setup)
    with psycopg.connect(application_state_dsn) as conn:
        conn.execute(
            "UPDATE ingest.component_payload SET payload=%s WHERE run_id=%s AND kind='candidate_graph'",
            (b"corrupt", latest.run_id),
        )
    with _client(setup, monkeypatch) as client:
        response = _inspect(client)
    assert response.status_code in {409, 422, 500}, response.text
    assert response.json()["detail"]["code"] == catalog.CODE_INTEGRITY


def test_run_without_managed_scope_is_not_selected(setup, monkeypatch):
    source = _admit_recap(setup)
    result = run_production_extraction(
        ProductionExtractionRequest(
            repo_root=setup,
            source=source,
            profile_id=RECAP_PROFILE_ID,
            profile_version=RECAP_PROFILE_VERSION,
            allow_llm=True,
            category_client=FixtureClient(span_ref=_first_paragraph_span_id(source)),
            initial_lineage=_recap_run_lineage(source),
        )
    )
    assert result.run.status == Status.REVIEWABLE
    with _client(setup, monkeypatch) as client:
        response = _inspect(client)
    assert response.status_code == 200, response.text
    assert response.json()["ingest_report"]["graph_preview"]["status"] == "missing"


def test_corrupt_source_world_cannot_use_matching_run_context(
    setup, monkeypatch, application_state_dsn
):
    _, run = _case(setup)
    with psycopg.connect(application_state_dsn) as conn:
        conn.execute(
            "UPDATE source.artifact SET input_descriptor=jsonb_set(input_descriptor, '{world_id}', '\"foreign\"') WHERE source_artifact_id=%s",
            (run.source_artifact_id,),
        )
    with _client(setup, monkeypatch) as client:
        response = _inspect(client)
    assert response.status_code in {409, 422, 500}, response.text
    assert response.json()["detail"]["code"] == catalog.CODE_INTEGRITY


@pytest.mark.parametrize("candidate", [b"[]", b"{}", b"not json"])
def test_matching_hash_does_not_make_a_malformed_candidate_reviewable(
    setup, monkeypatch, application_state_dsn, candidate
):
    import hashlib
    from psycopg.types.json import Jsonb

    _, run = _case(setup)
    digest = hashlib.sha256(candidate).hexdigest()
    with psycopg.connect(application_state_dsn) as conn:
        # Simulate coherently rebound corrupt storage, not just a hash mismatch.
        conn.execute(
            "UPDATE ingest.run SET components=jsonb_set(components, '{candidate_graph,sha256}', %s) WHERE run_id=%s",
            (Jsonb(digest), run.run_id),
        )
        conn.execute(
            "UPDATE ingest.component_payload SET payload=%s, content_sha256=%s WHERE run_id=%s AND kind='candidate_graph'",
            (candidate, digest, run.run_id),
        )
    with _client(setup, monkeypatch) as client:
        response = _inspect(client)
    assert response.status_code == 409, response.text
    assert response.json()["detail"]["code"] == catalog.CODE_INTEGRITY


def test_catalog_validation_errors_do_not_expose_private_context(setup, monkeypatch):
    from application_state.errors import ApplicationStateIntegrityError

    secret = "PRIVATE_MODEL_OUTPUT_/retained/private/path"

    def fail(**kwargs):
        raise ApplicationStateIntegrityError("bad persisted record: " + secret)

    monkeypatch.setattr(catalog, "list_extraction_runs", fail)
    with _client(setup, monkeypatch) as client:
        response = _inspect(client)
    assert response.status_code == 500
    assert response.json()["detail"]["code"] == catalog.CODE_INTEGRITY
    assert secret not in response.text
