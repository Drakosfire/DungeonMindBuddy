"""Provider-free PDF Event publication on disposable application and Core stores."""
from base64 import b64decode
from dataclasses import replace
from datetime import UTC, datetime
from hashlib import sha256
from io import BytesIO
from secrets import token_urlsafe
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient
from pypdf import PdfWriter
import pytest

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


@pytest.mark.parametrize("reserved", [False, True])
def test_pdf_event_preserves_review_and_reopens_citation(
    native_core_dsn, application_state_dsn, tmp_path, monkeypatch, reserved,
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
    if not reserved:
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
        for boundary in ("source", "parent"):
            with monkeypatch.context() as change:
                source_reads = 0
                revoked = False
                original_revision = repo.get_revision
                original_load = repo.get_native_pdf_source
                original_authorize = pdf_adventure_events.require_build_pdf_access

                def load_source(*args):
                    nonlocal source_reads, revoked
                    source = original_load(*args)
                    source_reads += 1
                    if boundary == "source" and source_reads == 2:
                        revoked = True
                    return source

                def read_revision(*args):
                    nonlocal revoked
                    result = original_revision(*args)
                    if boundary == "parent" and source_reads == 2:
                        revoked = True
                    return result

                def authorize(request, world_id):
                    if revoked:
                        raise pdf_adventure_events.HTTPException(403)
                    return original_authorize(request, world_id)

                change.setattr(native, "repository", lambda: repo)
                change.setattr(repo, "get_native_pdf_source", load_source)
                change.setattr(repo, "get_revision", read_revision)
                change.setattr(pdf_adventure_events, "require_build_pdf_access", authorize)
                denied = client.post(events + "/prepare", json=draft, headers=auth)
                assert denied.status_code == 403, denied.text
                assert source_reads == 2
                assert repo.get_head(space) == before
        review = client.post(events + "/prepare", json=draft, headers=auth)
        assert review.status_code == 200, review.text
        packet = review.json()
        foreign_world = create_world_container(name="Unrelated PDF Event fixture")
        foreign_events = f"/api/live/worlds/{foreign_world.world_id}/pdf-adventure-events"
        foreign = client.post(foreign_events + "/confirm", json=packet, headers=auth)
        assert foreign.status_code == 409, foreign.text
        foreign_space = foreign_world.native_graph_binding.native_world_id
        assert repo.get_head(foreign_space) is None
        before = repo.get_head(space).head_revision_id
        tampered = packet | {"draft": draft | {"name": "Changed"}}
        assert client.post(events + "/confirm", json=tampered, headers=auth).status_code == 409
        assert repo.get_head(space).head_revision_id == before
        with monkeypatch.context() as change:
            revoked = False
            original_descriptors = native.descriptors
            original_authorize = pdf_adventure_events.require_build_pdf_access

            def descriptors(*args):
                nonlocal revoked
                result = original_descriptors(*args)
                revoked = True
                return result

            def authorize(request, world_id):
                if revoked:
                    raise pdf_adventure_events.HTTPException(403)
                return original_authorize(request, world_id)

            change.setattr(native, "descriptors", descriptors)
            change.setattr(pdf_adventure_events, "require_build_pdf_access", authorize)
            denied = client.post(events + "/confirm", json=packet, headers=auth)
            assert denied.status_code == 403, denied.text
            assert repo.get_head(space).head_revision_id == before
        if reserved:
            from apps.live_control_server.services import world_graph_binding
            assert catalog_owner.get_world(world.world_id).record.native_graph_binding.status == "provisioning"

            def interrupt_catalog(*args, **kwargs):
                raise world_graph_binding.WorldGraphBindingError("Simulated catalog conflict")

            with monkeypatch.context() as failure:
                failure.setattr(world_graph_binding, "_save_binding_record", interrupt_catalog)
                interrupted = client.post(events + "/confirm", json=packet, headers=auth)
                assert interrupted.status_code == 503, interrupted.text
                assert interrupted.json()["detail"]["code"] == "event_publication_outcome_unknown"
            saved_head = repo.get_head(space).head_revision_id
            assert saved_head != before
            assert catalog_owner.get_world(world.world_id).record.native_graph_binding.status == "provisioning"
            from apps.live_control_server.services.managed_world_graph_projection import resolve_managed_source_identity

            identity = resolve_managed_source_identity(world.world_id)
            for supplied_identity, revision, message in (
                (replace(identity, provisioning_id="provision:" + "0" * 32), saved_head, "reservation changed"),
                (identity, "rev:unrelated", "does not descend"),
            ):
                with pytest.raises(world_graph_binding.WorldGraphBindingError, match=message):
                    world_graph_binding.activate_native_source_graph(
                        world.world_id, identity=supplied_identity,
                        repository=repo, published_revision_id=revision,
                    )
                assert catalog_owner.get_world(world.world_id).record.native_graph_binding.status == "provisioning"
                assert repo.get_head(space).head_revision_id == saved_head
        committed = client.post(events + "/confirm", json=packet, headers=auth)
        assert committed.status_code == 200, committed.text
        receipt = committed.json()
        if reserved:
            assert receipt["replayed"]
            assert receipt["published_revision_id"] == saved_head
            assert catalog_owner.get_world(world.world_id).record.native_graph_binding.status == "active"
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
    principal = NativeGraphPrincipal(subject="local_operator", role="gm", auth_method="local_operator")
    monkeypatch.setattr(pdf_adventure_events, "require_build_pdf_access", lambda *_: principal)

    def sign(*_args, authorize_write):
        authorize_write()
        return sign_publication_intent({})

    with pytest.raises(HTTPException) as caught:
        pdf_adventure_events._invoke(sign, "fixture-world", None, None)
    assert caught.value.status_code == 503
    assert caught.value.detail["code"] == "authority_unavailable"
