"""Opaque APP keys through ordinary intake; real APP PostgreSQL and memory Core."""

from datetime import UTC, datetime
from hashlib import sha256
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError

from application_state.ingest import service as ingest
from application_state.source import service as sources
from dungeonmind.application.vnext import initialize_empty_knowledge_space
from dungeonmind.infrastructure.memory.vnext_sources import InMemoryNativeSourceEvidenceRepository
from graph_memory.evidence.source_artifact import GraphMemorySourceArtifact, build_world_scoped_recap_source_artifact_id
from graph_memory.ingestion.native_recap_source import KEY, Record, SourceSelection
from graph_memory.vnext.domain_runtime import dungeonbuddy_dnd5e_custom_predicate_profile, dungeonbuddy_world_domain_contract
from apps.live_control_server import config
from apps.live_control_server.integrations.dungeonmind.native_recap_source_admission import NativeRecapAuthority
from apps.live_control_server.routes import recap_ingest as route
from apps.live_control_server.services import native_recap_source_admission as service
from apps.live_control_server.services.world_container_registry import create_world_container

TOKEN = "synthetic-source-identity-operator"
IDS = ["artifact:recap:campaign:session-8:retained", "opaque/database/source-key", "generated-current-key"]


@pytest.fixture(params=IDS)
def lane(request, tmp_path, monkeypatch, application_state_dsn):
    # The existing fixture owns/drops only its freshly named APP database.
    assert "dungeonbuddy_app_state_test_" in application_state_dsn
    monkeypatch.setenv(config.ARTIFACT_DATA_ROOT_ENV, str(tmp_path))
    monkeypatch.setenv(config.MANAGED_WORLD_DATA_ROOT_ENV, str(tmp_path))
    for key, value in {"DMB_DEPLOYMENT_ENVIRONMENT": "local", "DMB_AUTH_MODE": "local_operator",
                       "DMB_AGENT_GRAPH_AUTH_MODE": "local_operator", "DMB_AGENT_GRAPH_AUTH_ENVIRONMENT": "local",
                       "DMB_AGENT_GRAPH_LOCAL_OPERATOR_TOKEN": TOKEN}.items():
        monkeypatch.setenv(key, value)
    world = create_world_container(tmp_path, name="Opaque source keys", owner_subject="fixture")
    space = world.native_graph_binding.native_world_id
    repo = InMemoryNativeSourceEvidenceRepository()
    initialize_empty_knowledge_space(repository=repo, space_id=space, initialization_id="fixture",
        created_at=datetime(2026, 10, 31, tzinfo=UTC), domain_contract=dungeonbuddy_world_domain_contract(),
        semantic_profile=dungeonbuddy_dnd5e_custom_predicate_profile())
    monkeypatch.setattr(service, "NativeRecapAuthority", lambda root: NativeRecapAuthority(root, repository=repo))
    monkeypatch.setattr(route, "repo_root", lambda: tmp_path)
    import httpx
    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", lambda *_: pytest.fail("Provider HTTP forbidden"))
    text = "# Exact retained source\r\n\r\nA supported observation without terminal newline."
    digest = sha256(text.encode()).hexdigest()
    identifier = (build_world_scoped_recap_source_artifact_id(world_id=space, campaign_id="campaign",
                  session_id="session-8", content_sha256=digest) if request.param == "generated-current-key" else request.param)
    descriptor = GraphMemorySourceArtifact(source_artifact_id=identifier, source_domain="recap",
        artifact_kind="recap_markdown", world_id=space, campaign_id="campaign", session_id="session-8",
        content_sha256=digest, uri="file:///nonexistent/unused.md")
    source = sources.persist_source_markdown(source_artifact_id=identifier, source_domain="recap",
        world_id=space, campaign_id="campaign", session_id="session-8", markdown=text,
        input_descriptor=descriptor.model_dump(mode="json"))
    selection = dict(source_artifact_id=identifier, source_revision_id=str(source.source_revision_id), content_sha256=digest)
    body = dict(operation="build_graph_preview_bundle", include_graph_extraction=False,
                managed_world_id=world.world_id, campaign_id="campaign", session=8, native_recap_source=selection)
    app = FastAPI()
    app.include_router(route.router)
    client = TestClient(app, client=("127.0.0.1", 50000), headers={"Authorization": "Bearer " + TOKEN})
    return client, body, source, repo, space


def test_exact_opaque_key_admits_preserves_origin_and_replays(lane):
    client, body, source, repo, space = lane
    response = client.post("/api/live/recap-ingest", json=body)
    assert response.status_code == 200, response.text
    value = response.json()["native_recap_source"]
    assert value["state"] == "admitted" and value["opening"]["state"] == "verified"
    assert value["app_source_artifact_id"] == source.source_artifact_id
    assert value["origin"]["object_id"] == source.source_artifact_id
    assert value["origin"]["revision_id"] == str(source.source_revision_id)
    assert value["opening"]["body_sha256"] == source.content_sha256
    run = ingest.get_extraction_run(value["run_id"])
    record = Record.model_validate(run.lineage[KEY])
    assert record.app_source_artifact_id == source.source_artifact_id
    assert Record.model_validate(record.model_dump()).admission_id == record.admission_id == value["admission_id"]
    assert record.run_id == value["run_id"]
    head = repo.get_head(space)
    assert client.post("/api/live/recap-ingest", json=body).json() == response.json()
    status = value["status_request"]
    assert client.post(status["path"], json=status["body"]).json()["native_recap_source"] == value
    assert repo.get_head(space) == head and len(ingest.list_extraction_runs()) == 1
    assert sources.get_source_markdown(**body["native_recap_source"]) == source


def test_opaque_key_still_requires_exact_source_and_scope(lane, monkeypatch):
    monkeypatch.setattr(service, "create_extraction_run",
        lambda *a, **k: pytest.fail("invalid source reached generic candidate storage"))
    client, body, source, repo, space = lane
    before = repo.get_head(space)
    for changes in [{"source_artifact_id": "unknown/exact-key"}, {"source_revision_id": str(uuid4())},
                    {"content_sha256": "0" * 64}]:
        rejected = client.post("/api/live/recap-ingest", json={**body,
            "native_recap_source": {**body["native_recap_source"], **changes}})
        assert rejected.status_code == 409, rejected.text
    for changes in [{"campaign_id": "foreign"}, {"session": 9}]:
        rejected = client.post("/api/live/recap-ingest", json={**body, **changes})
        assert rejected.status_code == 409, rejected.text
        assert rejected.json()["detail"]["code"] == "native_recap_source_grouping_mismatch"
    for suffix, world, domain in [("foreign-world", space + "-other", "recap"), ("foreign-domain", space, "external")]:
        identifier = "opaque/" + suffix
        descriptor = GraphMemorySourceArtifact(source_artifact_id=identifier, source_domain=domain,
            artifact_kind="recap_markdown", world_id=world, campaign_id="campaign", session_id="session-8",
            content_sha256=source.content_sha256, uri="file:///unused.md")
        other = sources.persist_source_markdown(source_artifact_id=identifier, source_domain=domain,
            world_id=world, campaign_id="campaign", session_id="session-8", markdown=source.markdown,
            input_descriptor=descriptor.model_dump(mode="json"))
        rejected = client.post("/api/live/recap-ingest", json={**body, "native_recap_source": dict(
            source_artifact_id=identifier, source_revision_id=str(other.source_revision_id), content_sha256=other.content_sha256)})
        assert rejected.status_code == 409, rejected.text
        expected = "native_recap_source_world_mismatch" if suffix == "foreign-world" else "native_recap_source_descriptor_mismatch"
        assert rejected.json()["detail"]["code"] == expected
    assert repo.get_head(space) == before and ingest.list_extraction_runs() == []
    assert sources.get_source_markdown(**body["native_recap_source"]) == source


@pytest.mark.parametrize("identifier", ["", " ", "\t\n"])
def test_blank_identity_rejected_without_normalizing(identifier):
    selection = dict(source_artifact_id=identifier, source_revision_id=str(uuid4()), content_sha256="a" * 64)
    with pytest.raises(ValidationError):
        SourceSelection.model_validate(selection)
    record = dict(managed_world_id="world", native_world_id="world", binding_version=1,
        campaign_id="campaign", session_id="session-8", app_source_artifact_id=identifier,
        app_source_revision_id=selection["source_revision_id"], app_body_sha256="a" * 64,
        created_by="fixture", created_authority_basis="local_gm", created_at=datetime.now(UTC))
    with pytest.raises(ValidationError):
        Record.model_validate(record)
