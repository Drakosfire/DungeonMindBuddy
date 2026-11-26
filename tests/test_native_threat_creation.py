"""Provider-free native HTTP creation through real draft, Core and WK owners."""
from copy import deepcopy
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from dungeonmind.application.vnext import EntityReadService, EvidenceReadService, open_admitted_native_text
from worldkeeper.application import contracts as wk

from apps.live_control_server.models.threat_draft import CreateWorldThreatDraftRequest, UpdateThreatDraftRequest
from apps.live_control_server.models.statblock_mechanics_acceptance import AcceptedMechanicsRefV1
from apps.live_control_server.routes.threat_drafts import router
from apps.live_control_server.services import native_threat_creation as service
from apps.live_control_server.services import threat_draft_store as drafts
from apps.live_control_server.services import graph_object_authoring_prepare as signing
from apps.live_control_server.integrations.worldkeeper import registry_standing_consumer as transport
from graph_memory.vnext.domain_runtime import GM_LABEL
from tests.test_native_recap_preparation import lane as recap_lane, TOKEN  # noqa: F401
from tests.test_hosted_native_graph_access import hosted  # noqa: F401


@pytest.fixture
def creature(request, monkeypatch):
    lane = request.getfixturevalue("recap_lane")
    bound = {"managed_world_id": "managed", **lane.bound}
    def binding(world):
        if world != "managed":
            raise ValueError("foreign World")
        return deepcopy(bound)
    monkeypatch.setattr(service.native, "binding", binding)
    monkeypatch.setattr(service.native, "repository", lambda: lane.repo)
    monkeypatch.setattr(service.native, "read_repository", lambda: lane.repo)
    monkeypatch.setenv("DMB_ARTIFACT_DATA_ROOT", str(lane.tmp_path))
    draft = drafts.create_threat_draft(lane.tmp_path, CreateWorldThreatDraftRequest(
        scope_mode="world", world_id="managed", campaign_id=None, name="Synthetic rolling ooze",
        description="A proposed synthetic creature, not an event that has happened.", threat_kind="creature",
        generation_intent={"ruleset": {"system": "dnd5e", "edition": "2024"}},
        graph_context_snapshot={"graph_revision_id": None}, created_by="gm"))
    # Fixture authoring state only. This publisher never consumes DMS authority;
    # mechanics acceptance and association have their separate owning tests.
    draft = drafts.attach_accepted_mechanics_ref(lane.tmp_path, draft_id=draft.draft_id, expected_version=1,
        locator=AcceptedMechanicsRefV1(statblock_id="sb_fixture", revision_id="rev_fixture",
            contract="dungeonmind.dungeonbuddy-statblocks", contract_version="1.0.0",
            definition_digest="sha256:" + "a" * 64, accepted_from_draft_version=1,
            accepted_at="2026-11-08T00:00:00Z"))
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app, client=("127.0.0.1", 50000), headers={"Authorization": "Bearer " + TOKEN})
    url = f"/api/live/threat-drafts/{draft.draft_id}/native-creature"
    request = dict(world_id="managed", expected_draft_version=draft.version)
    return SimpleNamespace(**locals())


def prepare(c):
    response = c.client.post(c.url + "/prepare", json=c.request)
    assert response.status_code == 200, response.text
    assert response.json()["state"] == "prepared"
    return response.json()


def confirm(c, packet):
    return c.client.post(c.url + "/confirm", json={key: packet[key] for key in ("review", "prepared", "token")})


def test_native_source_then_explicit_confirmation_and_current_readback(creature):
    c = creature
    packet = prepare(c)
    assert "pdf_evidence_ids" not in packet["review"]
    assert packet["source_text"] == service.body(c.draft)
    assert service.existing(c.lane.repo, c.bound, c.draft.draft_id) is None
    assert c.client.get(c.url + "?world_id=managed").json() is None
    response = confirm(c, packet)
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["state"] == "published" and result["replayed"] is False
    assert result["node_id"].startswith("ent:")
    read, access, *_ = service.native.read_context(c.lane.repo, c.bound["native_world_id"],
        result["published_revision_id"], None, "gm", scope_mode="world")
    entity = EntityReadService().get_complete_entity(read, result["node_id"])
    assert entity.found and len(entity.assertions) == 2
    assert {a.predicate for a in entity.assertions} == {"dnd5e:name", "dnd5e:classification"}
    for assertion in entity.assertions:
        assert assertion.metadata.scope == ()
        assert assertion.metadata.claim_mode == "dungeonbuddy.claim:plan"
        assert assertion.metadata.standing == "provisional"
        assert assertion.metadata.epistemic_basis == "asserted"
        evidence = EvidenceReadService().get_assertion_evidence(read, assertion.assertion_id)
        assert evidence.available
        support = [e for e in evidence.evidence if e.evidence_role == "support"]
        assert len(support) == 1
        opened = open_admitted_native_text(access, support[0].evidence_ref_id)
        assert opened.status == "available" and opened.body_text == service.body(c.draft)
    player, player_access, *_ = service.native.read_context(c.lane.repo, c.bound["native_world_id"],
        result["published_revision_id"], None, "player", scope_mode="world")
    assert not EntityReadService().get_complete_entity(player, result["node_id"]).assertions
    assert open_admitted_native_text(player_access, packet["review"]["source_evidence_id"]).status == "unavailable"
    assert c.client.get(c.url + "?world_id=managed").json()["node_id"] == result["node_id"]


def test_same_confirmation_recovers_without_rereading_changed_draft(creature, monkeypatch):
    c = creature
    packet = prepare(c)
    first = confirm(c, packet)
    assert first.status_code == 200, first.text
    monkeypatch.setattr(service, "owned_draft", lambda *args: pytest.fail("Replay read changed draft"))
    replay = confirm(c, packet)
    assert replay.status_code == 200, replay.text
    assert replay.json() == {**first.json(), "replayed": True}


def test_repeat_prepare_after_commit_returns_one_original_identity(creature):
    c = creature
    packet = prepare(c)
    first = confirm(c, packet)
    assert first.status_code == 200, first.text
    drafts.update_threat_draft(c.lane.tmp_path, c.draft.draft_id,
        UpdateThreatDraftRequest(expected_version=c.draft.version, name=c.draft.name,
            threat_kind=c.draft.threat_kind, generation_intent=c.draft.generation_intent,
            graph_context_snapshot=c.draft.graph_context_snapshot, description="New draft notes retained."))
    repeat = c.client.post(c.url + "/prepare", json=c.request)
    assert repeat.status_code == 200, repeat.text
    assert repeat.json() == {**first.json(), "replayed": True}


@pytest.mark.parametrize("change", ["draft", "binding", "head", "token", "prepared", "review", "path"])
def test_changed_review_never_publishes_creature(creature, change):
    c = creature
    packet = prepare(c)
    if change == "draft":
        drafts.update_threat_draft(c.lane.tmp_path, c.draft.draft_id,
            UpdateThreatDraftRequest(expected_version=c.draft.version, name=c.draft.name,
            threat_kind=c.draft.threat_kind, generation_intent=c.draft.generation_intent,
            graph_context_snapshot=c.draft.graph_context_snapshot, description="Changed source."))
    elif change == "binding":
        c.bound["binding_version"] += 1
    elif change == "head":
        metadata = wk.AssertionMetadata(scope=(), visibility=wk.Visibility("labels_any", (GM_LABEL,)),
            epistemic_basis="asserted", claim_mode="dungeonbuddy.claim:plan", standing="provisional",
            temporal_scope=wk.TemporalScope(kind="unknown"), evidence_ref_ids=(c.lane.support_ids["first"],))
        runtime = transport.runtime(c.lane.repo, c.lane.domain, c.lane.profile,
                                    now=datetime.now(UTC), operation_id="concurrent-fixture")
        runtime.commit_prepared_change(runtime.prepare_change(wk.WorldChangeIntent(c.bound["native_world_id"],
            "fixture", (wk.CreateObject("other", (wk.CreateFact("other.name", "dnd5e:name",
                wk.LiteralFactValue("Another proposed object"), metadata),)),))), confirmed_by="gm")
    elif change == "token":
        packet["token"] += "tampered"
    elif change == "prepared":
        packet["prepared"]["value"]["fields"]["producer"] = "another-producer"
    elif change == "review":
        packet["review"]["label"] = "Another creature"
    elif change == "path":
        c.url = c.url.replace(c.draft.draft_id, str(uuid4()))
    response = confirm(c, packet)
    assert response.status_code == 409, response.text
    assert service.existing(c.lane.repo, c.bound, c.draft.draft_id) is None


def test_expired_review_refuses_first_write_but_recovers_existing_commit(creature, monkeypatch):
    c = creature
    packet = prepare(c)
    expiry = datetime.fromisoformat(packet["review"]["expires_at"]) + timedelta(seconds=1)
    class Late(datetime):
        @classmethod
        def now(cls, tz=None):
            return expiry
    with monkeypatch.context() as clock:
        clock.setattr(signing, "datetime", Late)
        assert confirm(c, packet).status_code == 409
    assert confirm(c, packet).status_code == 200
    monkeypatch.setattr(signing, "datetime", Late)
    response = confirm(c, packet)
    assert response.status_code == 200, response.text
    assert response.json()["replayed"] is True


def test_auth_scope_and_draft_cas_fail_before_source_admission(creature):
    c = creature
    head = c.lane.repo.get_head(c.bound["native_world_id"])
    c.client.headers.pop("Authorization")
    assert c.client.post(c.url + "/prepare", json=c.request).status_code == 401
    c.client.headers["Authorization"] = "Bearer " + TOKEN
    assert c.client.post(c.url + "/prepare", json={**c.request, "world_id": "foreign"}).status_code == 409
    assert c.client.post(c.url + "/prepare", json={**c.request, "expected_draft_version": 999}).status_code == 409
    assert c.lane.repo.get_head(c.bound["native_world_id"]) == head


def test_lost_commit_acknowledgement_recovers_same_native_identity(creature, monkeypatch):
    from psycopg import Error as DatabaseError
    c = creature
    packet = prepare(c)
    factory = transport.runtime
    lost = False
    class Runtime:
        def __init__(self, inner):
            self.inner = inner
        def commit_prepared_change(self, *args, **kwargs):
            nonlocal lost
            result = self.inner.commit_prepared_change(*args, **kwargs)
            if not lost:
                lost = True
                raise DatabaseError("Synthetic lost acknowledgement after native commit")
            return result
    monkeypatch.setattr(transport, "runtime", lambda *args, **kwargs: Runtime(factory(*args, **kwargs)))
    first = confirm(c, packet)
    assert first.status_code == 503
    retained = c.client.get(c.url + "?world_id=managed").json()
    recovered = confirm(c, packet)
    assert recovered.status_code == 200, recovered.text
    assert recovered.json() == retained
    assert recovered.json()["replayed"] is True


def test_repeating_prepare_reuses_source_and_creates_no_facts(creature):
    c = creature
    first = prepare(c)
    head = c.lane.repo.get_head(c.bound["native_world_id"])
    second = prepare(c)
    assert first["review"]["source_evidence_id"] == second["review"]["source_evidence_id"]
    assert c.lane.repo.get_head(c.bound["native_world_id"]) == head
    assert service.existing(c.lane.repo, c.bound, c.draft.draft_id) is None


@pytest.fixture
def creation_core_dsn(monkeypatch):
    from tests.test_native_recap_source_admission import native_core_dsn
    yield from native_core_dsn.__wrapped__(monkeypatch)


def test_postgres_publication_survives_fresh_core_repository(creation_core_dsn, monkeypatch, tmp_path):
    import tests.test_native_recap_preparation as recap_tests
    from dungeonmind.infrastructure.postgres import PostgresDatabase, PostgresNativeSourceEvidenceRepository
    repo = PostgresNativeSourceEvidenceRepository(PostgresDatabase(creation_core_dsn))
    monkeypatch.setattr(recap_tests, "InMemoryNativeSourceEvidenceRepository", lambda: repo)
    lane = recap_lane.__wrapped__(monkeypatch, tmp_path, SimpleNamespace(param=None))
    case = creature.__wrapped__(SimpleNamespace(getfixturevalue=lambda name: lane), monkeypatch)
    from hashlib import sha256
    from io import BytesIO

    from dungeonmind.contracts.vnext.pdf_region import NativePdfSourceAdmissionV1
    from pypdf import PdfWriter

    writer = PdfWriter()
    writer.add_blank_page(width=100, height=100)
    output = BytesIO()
    writer.write(output)
    pdf = output.getvalue()
    digest = sha256(pdf).hexdigest()
    source = repo.retain_native_pdf_source(
        NativePdfSourceAdmissionV1(
            space_id=case.bound["native_world_id"], admission_id="fixture:statblock-pdf",
            created_at=datetime.now(UTC), content_sha256=digest,
            source_classification="dungeonbuddy.source:worldbuilding",
            authority="primary", visibility={"kind": "public"},
        ),
        pdf,
    )
    case.request["pdf_regions"] = [dict(
        source_revision_id=source.source_revision_id, content_sha256=digest,
        page=1, left=0.1, top=0.1, right=0.9, bottom=0.9,
    )]
    from apps.live_control_server.services import build_pdf_region_render

    # The blank PDF exercises real storage and locator validation. Supply the
    # extractor output to keep text extraction independent of this contract.
    monkeypatch.setattr(build_pdf_region_render, "read_region_text", lambda *_: "Reviewed mechanics.")
    packet = prepare(case)
    response = confirm(case, packet)
    assert response.status_code == 200, response.text
    fresh = PostgresNativeSourceEvidenceRepository(PostgresDatabase(creation_core_dsn))
    monkeypatch.setattr(service.native, "repository", lambda: fresh)
    monkeypatch.setattr(service.native, "read_repository", lambda: fresh)
    result = case.client.get(case.url + "?world_id=managed")
    assert result.status_code == 200 and result.json()["node_id"] == response.json()["node_id"]
    from dungeonmind.application.vnext.native_pdf_access import open_native_pdf_region
    from dungeonmind.contracts.vnext.pdf_region import NativePdfRegionV1

    _, access = service.native.access_context(fresh, case.bound["native_world_id"])
    (evidence_id,) = packet["review"]["pdf_evidence_ids"]
    ref = access.parsed.get_evidence(evidence_id)
    assert ref is not None and ref.source_locator is not None
    locator = NativePdfRegionV1.model_validate_json(ref.source_locator)
    assert open_native_pdf_region(
        locator, authorized_space_id=case.bound["native_world_id"],
        audience=frozenset(), declared_labels=frozenset(), load=fresh.get_native_pdf_source,
    ) == pdf
    from apps.live_control_server.models.native_graph_inspection import InspectionRead
    from apps.live_control_server.services import native_graph_inspection
    from apps.live_control_server.services.agent_graph_auth import NativeGraphPrincipal
    from application_state.agent_conversation.authored_graph_references import AuthoredGraphReferenceV1

    monkeypatch.setattr(native_graph_inspection, "_repository", lambda: fresh)
    creature_ref = AuthoredGraphReferenceV1(
        managed_world_id="managed", native_world_id=case.bound["native_world_id"],
        binding_version=case.bound["binding_version"],
        graph_revision=fresh.get_head(case.bound["native_world_id"]).head_revision_id,
        node_id=result.json()["node_id"], label="Fixture creature",
    )
    principal = NativeGraphPrincipal("local_operator", "gm", "local_operator")
    (stored_id,) = packet["review"]["stored_region_evidence_ids"]

    def no_pdf_read(*args):
        pytest.fail("Conversation retrieval tried to load the original PDF")

    with monkeypatch.context() as storage:
        storage.setattr(fresh, "get_native_pdf_source", no_pdf_read)
        support = native_graph_inspection.statblock_pdf_support(creature_ref, (locator,), principal)
        (selected,) = support["support"]
        assert selected["evidence_ref_id"] == stored_id
        assert selected["text"] == "Reviewed mechanics."
        stored = native_graph_inspection.inspect(
            InspectionRead.model_validate({"scope": support["scope"], "selection": {
                "kind": "source", "assertion_id": selected["assertion_id"], "evidence_ref_id": stored_id,
            }}), principal,
        )
        assert stored["schema"] == "dmb_native_graph_source_v1"
        assert stored["source"]["text"] == selected["text"]

    support = native_graph_inspection.statblock_pdf_support(creature_ref, (locator,), principal)
    assert [item["evidence_ref_id"] for item in support["support"]] == [stored_id]
    epoch = access.source_view.epoch
    assert native_graph_inspection.statblock_pdf_support(
        creature_ref, (locator,), principal, expected_source_epoch=epoch,
    ) == support
    with pytest.raises(native_graph_inspection.InspectionUnavailable, match="statblock_pdf_source_epoch_changed"):
        native_graph_inspection.statblock_pdf_support(
            creature_ref, (locator,), principal, expected_source_epoch=epoch + 1,
        )
    from base64 import b64decode
    from PIL import Image

    (selected,) = support["support"]
    request = InspectionRead.model_validate({
        "scope": support["scope"],
        "selection": {"kind": "source", "assertion_id": selected["assertion_id"],
                      "evidence_ref_id": evidence_id},
    })
    reopened = native_graph_inspection.inspect(request, principal)
    assert reopened["schema"] == "dmb_native_graph_pdf_region_v1"
    assert reopened["region"] == locator.model_dump(mode="json")
    with Image.open(BytesIO(b64decode(reopened["png_base64"]))) as image:
        assert image.size == (800, 800)
    other_crop = locator.model_copy(update={"left": 0.2})
    assert native_graph_inspection.statblock_pdf_support(
        creature_ref, (other_crop,), principal,
    )["support"] == []
    with pytest.raises(native_graph_inspection.InspectionUnavailable, match="statblock_pdf_review_incomplete"):
        native_graph_inspection.statblock_pdf_support(
            creature_ref, (other_crop,), principal, expected_source_epoch=epoch,
        )
    replay = confirm(case, packet)
    assert replay.status_code == 200 and replay.json()["node_id"] == response.json()["node_id"]
    assert replay.json()["replayed"] is True

    load = native_graph_inspection.open_admitted_native_text

    def load_then_withdraw(context, requested_id):
        exact = load(context, requested_id)
        assert requested_id == stored_id and exact.status == "available"
        fresh.withdraw_native_source(space_id=creature_ref.native_world_id,
            source_artifact_id=exact.source_artifact_id, source_revision_id=exact.source_revision_id)
        return exact

    monkeypatch.setattr(native_graph_inspection, "open_admitted_native_text", load_then_withdraw)
    monkeypatch.setattr(fresh, "get_native_pdf_source", no_pdf_read)
    with pytest.raises(native_graph_inspection.InspectionUnavailable, match="statblock_pdf_source_epoch_changed"):
        native_graph_inspection.statblock_pdf_support(
            creature_ref, (locator,), principal, expected_source_epoch=epoch,
        )
    assert fresh.get_head(creature_ref.native_world_id).head_revision_id == creature_ref.graph_revision


@pytest.mark.parametrize("change", ["principal", "support"])
def test_other_operator_or_unavailable_support_cannot_confirm(creature, monkeypatch, change):
    from apps.live_control_server.services.agent_graph_auth import NativeGraphPrincipal
    from dungeonmind.contracts.vnext.native_source import NativeTextSourceAccessV1
    c = creature
    packet = prepare(c)
    if change == "principal":
        monkeypatch.setattr(
            "apps.live_control_server.services.agent_graph_auth.authenticate_native_graph_principal",
            lambda request: NativeGraphPrincipal("other-gm", "gm", "local_operator"),
        )
    else:
        monkeypatch.setattr(service, "open_admitted_native_text", lambda *args: NativeTextSourceAccessV1(status="unavailable"))
    response = confirm(c, packet)
    assert response.status_code == 409, response.text
    assert service.existing(c.lane.repo, c.bound, c.draft.draft_id) is None


@pytest.mark.parametrize("from_saved_mechanics", [False, True])
def test_pdf_region_is_bound_to_signed_native_threat_review(creature, monkeypatch, from_saved_mechanics):
    from hashlib import sha256

    from dungeonmind.application.vnext.native_source_admission import build_native_pdf_source_records
    from dungeonmind.contracts.vnext.pdf_region import NativePdfSourceAdmissionV1

    c = creature
    space_id = c.bound["native_world_id"]
    pdf = b"%PDF-1.7\n"
    digest = sha256(pdf).hexdigest()
    artifact, revision = build_native_pdf_source_records(
        NativePdfSourceAdmissionV1(
            space_id=space_id, admission_id="fixture:pdf", created_at=datetime.now(UTC),
            source_classification="dungeonbuddy.source:worldbuilding", authority="primary",
            content_sha256=digest, visibility={"kind": "public"},
        ),
        pdf,
    )

    def load_pdf(space, source):
        if (space, source) == (space_id, revision.source_revision_id):
            return artifact, revision, 1, pdf
        return None

    monkeypatch.setattr(c.lane.repo, "get_native_pdf_source", load_pdf, raising=False)
    region = dict(source_revision_id=revision.source_revision_id, content_sha256=digest,
                  page=1, left=0.1, top=0.2, right=0.7, bottom=0.8)
    if from_saved_mechanics:
        locator = c.draft.accepted_mechanics_ref.to_mechanics_locator().model_dump(mode="json")
        c.request["mechanics_locator"] = locator
        exact = SimpleNamespace(provenance={"accepted_through": {
            service.PDF_REVIEW_PROVENANCE: {"world_id": c.draft.world_id, "regions": [region]},
        }})
        monkeypatch.setattr(service, "resolve_saved_source", lambda *args, **kwargs: (
            c.draft, None, "acceptance-id", None, exact,
        ))
        recorded = deepcopy(exact.provenance)
        monkeypatch.setattr(service, "get_acceptance_operation", lambda *args, **kwargs: (
            SimpleNamespace(request_body=recorded)
        ))
        exact.provenance = {}
        assert c.client.post(c.url + "/prepare", json=c.request).status_code == 409
        exact.provenance = deepcopy(recorded)
    else:
        c.request["pdf_regions"] = [region]
    packet = prepare(c)
    if from_saved_mechanics:
        assert packet["review"]["mechanics_locator"] == locator
        changed = deepcopy(packet)
        changed["review"]["mechanics_locator"]["revision_id"] = "rev_other"
        assert confirm(c, changed).status_code == 409
    (evidence_id,) = packet["review"]["pdf_evidence_ids"]
    assert evidence_id.startswith("pdf-region:")
    assert service.existing(c.lane.repo, c.bound, c.draft.draft_id) is None

    assert packet["review"]["pdf_regions"][0]["page"] == 1
    altered_region = deepcopy(packet)
    altered_region["review"]["pdf_regions"][0]["left"] = 0.3
    assert confirm(c, altered_region).status_code == 409

    tampered = deepcopy(packet)
    tampered["review"]["pdf_evidence_ids"] = []
    assert confirm(c, tampered).status_code == 409
    assert service.existing(c.lane.repo, c.bound, c.draft.draft_id) is None

    response = confirm(c, packet)
    assert response.status_code == 200, response.text
    _, access = service.native.access_context(c.lane.repo, space_id)
    evidence = access.parsed.get_evidence(evidence_id)
    assert evidence is not None
    assert evidence.source_revision_id == revision.source_revision_id
    assert evidence.source_locator is not None
    import json

    assert json.loads(evidence.source_locator) == region | {
        "schema_version": "dm_native_pdf_region_v1",
    }


def test_hosted_native_creature_publication_and_replay(creature, hosted, monkeypatch):
    from tests.test_hosted_native_graph_access import OTHER_OWNER, OWNER

    c = creature
    monkeypatch.setattr(service.native, "binding", c.binding)
    monkeypatch.setattr(service.native, "repository", lambda: c.lane.repo)
    monkeypatch.setattr(service.native, "read_repository", lambda: c.lane.repo)
    prepare_path = c.url + "/prepare"
    confirm_path = c.url + "/confirm"
    status_path = c.url + "?world_id=managed"
    assert hosted.client.request("POST", prepare_path, json=c.request, origin=None).status_code == 403
    assert hosted.client.request("GET", status_path).json() is None
    owner_record = hosted.records["managed"]
    space = c.bound["native_world_id"]
    initial_head = c.lane.repo.get_head(space)
    original_receipt = c.lane.repo.get_native_source_admission_receipt

    source_lookups = 0

    def revoke_after_source_lookup(*args):
        nonlocal source_lookups
        receipt = original_receipt(*args)
        source_lookups += 1
        if source_lookups == 2:
            hosted.records["managed"] = owner_record.model_copy(update={"owner_subject": OTHER_OWNER})
        return receipt

    with monkeypatch.context() as lookup:
        lookup.setattr(c.lane.repo, "get_native_source_admission_receipt", revoke_after_source_lookup)
        denied = hosted.client.request("POST", prepare_path, json=c.request)
    assert denied.status_code == 403, denied.text
    assert source_lookups == 2
    assert c.lane.repo.get_head(space) == initial_head
    hosted.records["managed"] = owner_record
    prepared = hosted.client.request("POST", prepare_path, json=c.request)
    assert prepared.status_code == 200, prepared.text
    packet = prepared.json()
    assert packet["review"]["principal"] == f"hosted_dms:{OWNER}"
    assert hosted.client.request("GET", status_path).json() is None
    confirmation = {key: packet[key] for key in ("review", "prepared", "token")}
    assert hosted.client.request("POST", confirm_path, json=confirmation, session="other-session").status_code == 403
    prepared_head = c.lane.repo.get_head(space)
    original_descriptors = service.native.descriptors

    def revoke_after_descriptors(*args):
        descriptors = original_descriptors(*args)
        hosted.records["managed"] = owner_record.model_copy(update={"owner_subject": OTHER_OWNER})
        return descriptors

    with monkeypatch.context() as lookup:
        lookup.setattr(service.native, "descriptors", revoke_after_descriptors)
        denied = hosted.client.request("POST", confirm_path, json=confirmation)
    assert denied.status_code == 403, denied.text
    assert c.lane.repo.get_head(space) == prepared_head
    hosted.records["managed"] = owner_record
    confirmed = hosted.client.request("POST", confirm_path, json=confirmation)
    assert confirmed.status_code == 200, confirmed.text
    published = confirmed.json()
    assert published["state"] == "published" and published["replayed"] is False
    assert hosted.client.request("GET", status_path).json()["node_id"] == published["node_id"]
    head = c.lane.repo.get_head(c.bound["native_world_id"])
    replay = hosted.client.request("POST", confirm_path, json=confirmation)
    assert replay.status_code == 200, replay.text
    assert replay.json() == {**published, "replayed": True}
    assert c.lane.repo.get_head(c.bound["native_world_id"]) == head



def test_postgres_world_draft_admits_older_native_pin_without_core_mutation(
    creation_core_dsn, application_state_dsn, monkeypatch, tmp_path,
):
    """Mounted draft CRUD reads an exact native revision, never classic genesis.

    The existing lane seeds the SQL native space/source. Advancing its head is
    fixture setup; the fingerprint boundary below covers only draft POST/PUT.
    """
    import tests.test_native_recap_preparation as recap_tests
    from dungeonmind.contracts.vnext.knowledge import PublishKnowledgeRevisionCommand
    from dungeonmind.infrastructure.postgres import PostgresDatabase, PostgresNativeSourceEvidenceRepository
    from apps.live_control_server.routes import threat_drafts as draft_routes
    from apps.live_control_server.ports import world_graph_authority_access
    from apps.live_control_server.services.world_container_registry import create_world_container
    from tests.application_state.world_catalog_fixtures import store_world
    from tests.test_database_graph_object_authoring_evidence import _database_rows_fingerprint

    repo = PostgresNativeSourceEvidenceRepository(PostgresDatabase(creation_core_dsn))
    monkeypatch.setattr(recap_tests, "InMemoryNativeSourceEvidenceRepository", lambda: repo)
    lane = recap_lane.__wrapped__(monkeypatch, tmp_path, SimpleNamespace(param=None))
    space = lane.bound["native_world_id"]
    pin = repo.get_head(space).head_revision_id
    snapshot = repo.get_revision(space, pin)
    later = repo.publish_revision(PublishKnowledgeRevisionCommand(
        space_id=space, parent_revision_id=pin, expected_parent_revision_id=pin,
        operation_ids=["fixture:threat-draft-later-head"],
        graph_schema=snapshot.revision.graph_schema, graph_payload=snapshot.graph_payload,
        domain_contract_ref=snapshot.revision.domain_contract_ref,
        semantic_profile_ref=snapshot.revision.semantic_profile_ref,
        created_at=datetime.now(UTC),
    ))
    assert repo.get_head(space).head_revision_id == later.revision.revision_id != pin
    world = create_world_container(name="Native-only draft pin fixture")
    store_world(world.model_copy(update={"native_graph_binding": {
        "status": "active", "native_world_id": space, "binding_version": 1,
        "validated_at": "2026-11-20T00:00:00Z", "validated_head_revision_id": pin,
    }}))
    monkeypatch.setattr(draft_routes, "repo_root", lambda: tmp_path)
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app, client=("127.0.0.1", 50000))
    fresh = PostgresNativeSourceEvidenceRepository(PostgresDatabase(creation_core_dsn))
    reads = []
    original_read = fresh.get_revision
    def read_exact(space_id, revision_id):
        assert (space_id, revision_id) == (space, pin)
        reads.append((space_id, revision_id))
        return original_read(space_id, revision_id)
    monkeypatch.setattr(fresh, "get_revision", read_exact)
    monkeypatch.setattr(draft_routes.native, "read_repository", lambda: fresh)
    def forbidden(*args, **kwargs):
        pytest.fail("Draft pin admission opened head/source/classic/publication authority")
    monkeypatch.setattr(world_graph_authority_access, "get_world_graph_authority", forbidden)
    monkeypatch.setattr(draft_routes.native, "repository", forbidden)
    for name in ("get_head", "publish_revision", "open_native_source_view"):
        monkeypatch.setattr(PostgresNativeSourceEvidenceRepository, name, forbidden)
    before = _database_rows_fingerprint(creation_core_dsn, core=True)
    # This fixture has native knowledge revisions but no classic graph genesis.
    assert before["dungeonmind.graph_revisions"][0] == 0
    assert before["dungeonmind.world_graph_heads"][0] == 0
    payload = dict(
        scope_mode="world", world_id=world.world_id, campaign_id=None,
        name="A pinned draft", description="Unpublished local authoring state.", threat_kind="creature",
        generation_intent={"ruleset": {"system": "dnd5e", "edition": "2024"}},
        graph_context_snapshot={"graph_revision_id": pin, "selected_node_ids": [],
                                "admitted_source_anchor_ids": []}, created_by="gm",
    )
    response = client.post("/api/live/threat-drafts", json=payload)
    assert response.status_code == 200, response.text
    created = response.json()
    assert created["graph_context_snapshot"]["graph_revision_id"] == pin
    assert reads == [(space, pin)]
    assert _database_rows_fingerprint(creation_core_dsn, core=True) == before
    update = {key: value for key, value in payload.items()
              if key not in {"world_id", "campaign_id", "scope_mode", "created_by"}}
    update.update(expected_version=created["version"], description="Still pinned after a later native head.")
    response = client.put(f"/api/live/threat-drafts/{created['draft_id']}", json=update)
    assert response.status_code == 200, response.text
    assert response.json()["version"] == created["version"] + 1
    assert response.json()["graph_context_snapshot"]["graph_revision_id"] == pin
    assert reads == [(space, pin), (space, pin)]
    assert _database_rows_fingerprint(creation_core_dsn, core=True) == before
