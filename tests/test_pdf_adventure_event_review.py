"""Provider-free PDF Event publication on disposable application and Core stores."""
from base64 import b64decode
from datetime import UTC, datetime
from hashlib import sha256
from io import BytesIO
from secrets import token_urlsafe
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient
from pypdf import PdfWriter

from application_state.world_catalog import service as catalog_owner
from application_state.world_catalog.types import NativeGraphBindingRecord
from apps.live_control_server.config import WORLD_GRAPH_AUTHORITY_DATABASE_URL_ENV
from apps.live_control_server.integrations.dungeonmind import native_registry_source as native
from apps.live_control_server.routes import agent, native_graph_inspection, pdf_adventure_events
from apps.live_control_server.services.agent_graph_auth import NativeGraphPrincipal
from apps.live_control_server.services.world_container_registry import create_world_container
from apps.live_control_server.models.native_graph_inspection import InspectionPin
from apps.live_control_server.services.native_graph_inspection import catalog
from tests.test_native_recap_source_admission import native_core_dsn as native_core_dsn
from tests.test_source_statements import (
    NOW,
    dungeonbuddy_dnd5e_custom_predicate_profile,
    dungeonbuddy_world_domain_contract,
    initialize_empty_knowledge_space,
)


def test_pdf_event_preserves_review_and_reopens_citation(
    native_core_dsn, application_state_dsn, tmp_path, monkeypatch,
):
    token = token_urlsafe(32)
    for key, value in {
        WORLD_GRAPH_AUTHORITY_DATABASE_URL_ENV: native_core_dsn,
        "DMB_MANAGED_WORLD_DATA_ROOT": str(tmp_path),
        "DMB_DEPLOYMENT_ENVIRONMENT": "local",
        "DMB_AUTH_MODE": "local_operator",
        "DMB_AGENT_GRAPH_AUTH_ENVIRONMENT": "local",
        "DMB_AGENT_GRAPH_AUTH_MODE": "local_operator",
        "DMB_AGENT_GRAPH_LOCAL_OPERATOR_TOKEN": token,
        "DMB_GRAPH_REVIEW_PREPARE_BINDING_KEY": token_urlsafe(32),
    }.items():
        monkeypatch.setenv(key, value)
    world = create_world_container(name="PDF Event fixture")
    space = world.native_graph_binding.native_world_id
    repo = native.repository()
    initialize_empty_knowledge_space(
        repository=repo, space_id=space, initialization_id="pdf-event-fixture",
        created_at=NOW, domain_contract=dungeonbuddy_world_domain_contract(),
        semantic_profile=dungeonbuddy_dnd5e_custom_predicate_profile(),
    )
    binding = NativeGraphBindingRecord(
        native_world_id=space, status="active", binding_version=1,
        validated_at=datetime.now(UTC).isoformat(),
        validated_head_revision_id=repo.get_head(space).head_revision_id,
    )
    stored = catalog_owner.get_world(world.world_id)
    catalog_owner.save_world(
        world.model_copy(update={"native_graph_binding": binding}),
        expected_revision=stored.revision,
    )
    pdf = BytesIO()
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=300)
    writer.write(pdf)
    auth = {"Authorization": f"Bearer {token}"}
    app = FastAPI()
    app.include_router(agent.router)
    app.include_router(pdf_adventure_events.router)
    app.include_router(native_graph_inspection.router)
    source = f"/agent/worlds/{world.world_id}/build-pdf-sources"
    events = f"/api/live/worlds/{world.world_id}/pdf-adventure-events"
    with TestClient(app, client=("127.0.0.1", 50000)) as client:
        upload = client.post(source, params={"admission_id": str(uuid4())},
            content=pdf.getvalue(), headers=auth | {
                "Content-Type": "application/pdf", "X-Pdf-Created-At": NOW.isoformat(),
            })
        assert upload.status_code == 200, upload.text
        assert upload.json()["content_sha256"] == sha256(pdf.getvalue()).hexdigest()
        region = upload.json() | {"page": 1, "left": 0, "top": 0, "right": 1, "bottom": 1}
        draft = {"operation_id": str(uuid4()), "region": region,
                 "name": "Alarm", "description": "The bell calls the villagers."}
        assert client.post(events + "/prepare", json=draft).status_code == 401
        before = repo.get_head(space)
        with monkeypatch.context() as without_signing:
            without_signing.delenv("DMB_GRAPH_REVIEW_PREPARE_BINDING_KEY")
            unavailable = client.post(events + "/prepare", json=draft, headers=auth)
        assert unavailable.status_code == 503, unavailable.text
        assert unavailable.json()["detail"]["code"] == "authority_unavailable"
        assert repo.get_head(space) == before
        wrong = draft | {"region": region | {"content_sha256": "0" * 64}}
        assert client.post(events + "/prepare", json=wrong, headers=auth).status_code == 409
        review = client.post(events + "/prepare", json=draft, headers=auth)
        assert review.status_code == 200, review.text
        packet = review.json()
        before = repo.get_head(space).head_revision_id
        tampered = packet | {"draft": draft | {"name": "Changed"}}
        assert client.post(events + "/confirm", json=tampered, headers=auth).status_code == 409
        assert repo.get_head(space).head_revision_id == before
        committed = client.post(events + "/confirm", json=packet, headers=auth)
        assert committed.status_code == 200, committed.text
        receipt = committed.json()
        retry = client.post(events + "/confirm", json=packet, headers=auth)
        assert retry.status_code == 200, retry.text
        assert retry.json() == receipt | {"replayed": True}
        assert repo.get_head(space).head_revision_id == receipt["published_revision_id"]
        pin = InspectionPin(managed_world_id=world.world_id, native_world_id=space,
            binding_version=1, revision_id=receipt["published_revision_id"])
        principal = NativeGraphPrincipal(subject="local_operator", role="gm", auth_method="local_operator")
        assertion = next(row for row in catalog(pin, principal)["assertions"]
            if row["subject_entity_id"] == receipt["node_id"] and row["predicate"] == "dnd5e:summary")
        assert assertion["metadata"]["claim_mode"] == "dungeonbuddy.claim:plan"
        verified = client.post("/api/live/native-graph-inspection/read", headers=auth, json={
            "scope": pin.model_dump(mode="json"),
            "selection": {"kind": "source", "assertion_id": assertion["assertion_id"],
                          "evidence_ref_id": receipt["evidence_ref_id"]},
        })
        assert verified.status_code == 200, verified.text
        assert verified.json()["region"] == packet["draft"]["region"]
        assert b64decode(verified.json()["png_base64"]).startswith(b"\x89PNG\r\n\x1a\n")


def test_missing_signing_authority_is_reported_unavailable(monkeypatch):
    from fastapi import HTTPException
    import pytest
    from apps.live_control_server.services.graph_object_authoring_prepare import sign_publication_intent

    monkeypatch.delenv("DMB_GRAPH_REVIEW_PREPARE_BINDING_KEY", raising=False)
    with pytest.raises(HTTPException) as caught:
        pdf_adventure_events._invoke(lambda *_: sign_publication_intent({}), None, None, None)
    assert caught.value.status_code == 503
    assert caught.value.detail["code"] == "authority_unavailable"
