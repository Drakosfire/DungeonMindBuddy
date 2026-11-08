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
    lane = recap_lane.__wrapped__(monkeypatch, tmp_path)
    case = creature.__wrapped__(SimpleNamespace(getfixturevalue=lambda name: lane), monkeypatch)
    packet = prepare(case)
    response = confirm(case, packet)
    assert response.status_code == 200, response.text
    fresh = PostgresNativeSourceEvidenceRepository(PostgresDatabase(creation_core_dsn))
    monkeypatch.setattr(service.native, "repository", lambda: fresh)
    monkeypatch.setattr(service.native, "read_repository", lambda: fresh)
    result = case.client.get(case.url + "?world_id=managed")
    assert result.status_code == 200 and result.json()["node_id"] == response.json()["node_id"]
    replay = confirm(case, packet)
    assert replay.status_code == 200 and replay.json()["node_id"] == response.json()["node_id"]
    assert replay.json()["replayed"] is True


@pytest.mark.parametrize("change", ["principal", "support"])
def test_other_operator_or_unavailable_support_cannot_confirm(creature, monkeypatch, change):
    from apps.live_control_server.services.agent_graph_auth import NativeGraphPrincipal, native_graph_gm_dependency
    from dungeonmind.contracts.vnext.native_source import NativeTextSourceAccessV1
    c = creature
    packet = prepare(c)
    if change == "principal":
        c.app.dependency_overrides[native_graph_gm_dependency] = lambda: NativeGraphPrincipal("other-gm", "gm", "local_operator")
    else:
        monkeypatch.setattr(service, "open_admitted_native_text", lambda *args: NativeTextSourceAccessV1(status="unavailable"))
    response = confirm(c, packet)
    assert response.status_code == 409, response.text
    assert service.existing(c.lane.repo, c.bound, c.draft.draft_id) is None
