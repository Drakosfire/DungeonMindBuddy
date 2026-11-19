"""Explicit transition authority over real APP bindings and public Core/WK ports."""

from copy import deepcopy
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from dungeonmind.application.vnext import (
    initialize_empty_knowledge_space,
    publish_native_text_source_evidence,
)
from dungeonmind.application.vnext.authority import revision_from_command
from dungeonmind.contracts.vnext.knowledge import PublishKnowledgeRevisionCommand
from dungeonmind.contracts.vnext.native_source import NativeTextSourceAdmissionV1
from dungeonmind.infrastructure.memory.vnext_sources import (
    InMemoryNativeSourceEvidenceRepository,
)
from worldkeeper.application import contracts as wk
from worldkeeper.integrations.dungeonmind import DungeonMindWorldKeeperRuntime
from application_state.world_catalog.service import create_world
from apps.live_control_server.models.native_profile_transition import (
    ProfileTransitionContent,
)
from apps.live_control_server.routes.native_profile_transition import router
from apps.live_control_server.services import native_profile_transition as service
from apps.live_control_server.services.graph_object_authoring_prepare import (
    sign_publication_intent,
)
from graph_memory.vnext.domain_runtime import (
    dungeonbuddy_world_domain_contract,
    dungeonbuddy_dnd5e_semantic_profile,
    dungeonbuddy_dnd5e_custom_predicate_profile,
    dungeonbuddy_dnd5e_observation_profile,
    dungeonbuddy_dnd5e_manual_profile,
)
from tests.application_state.world_catalog_fixtures import change_binding, store_world
from application_state.world_catalog.types import NativeGraphBindingRecord

TOKEN = "profile-transition-fixture-token-with-adequate-length"
PATH = "/api/live/graph-authoring/native-profile-transition"


def seed(repo, profile, space):
    domain, now = (
        dungeonbuddy_world_domain_contract(),
        datetime(2026, 11, 19, tzinfo=UTC),
    )
    genesis = initialize_empty_knowledge_space(
        repository=repo,
        space_id=space,
        initialization_id="genesis",
        created_at=now,
        domain_contract=domain,
        semantic_profile=profile,
    )
    from hashlib import sha256

    body = "A traveller owns the towér.\r\n"
    root = publish_native_text_source_evidence(
        repository=repo,
        domain_contract=domain,
        semantic_profile=profile,
        request=NativeTextSourceAdmissionV1(
            space_id=space,
            admission_id="source",
            expected_parent_revision_id=genesis.published_revision_id,
            created_at=now,
            body_text=body,
            expected_body_sha256=sha256(body.encode()).hexdigest(),
            source_classification="dungeonbuddy.source:worldbuilding",
            authority="primary",
            visibility={"kind": "public"},
            spans=[
                dict(
                    client_ref="support",
                    evidence_role="support",
                    start_byte=0,
                    end_byte=len(body.encode()),
                    expected_slice_sha256=sha256(body.encode()).hexdigest(),
                )
            ],
        ),
    )
    meta = wk.AssertionMetadata(
        scope=(),
        visibility=wk.Visibility("public", ()),
        epistemic_basis="asserted",
        claim_mode="dungeonbuddy.claim:fact",
        standing="established",
        temporal_scope=wk.TemporalScope(kind="unknown"),
        evidence_ref_ids=(root.bindings[0].evidence_ref_id,),
    )
    runtime = DungeonMindWorldKeeperRuntime(
        repository=repo,
        domain_contract=domain,
        semantic_profile=profile,
        clock=lambda: now,
        prepared_id_factory=lambda: "initial-facts",
    )
    runtime.commit_prepared_change(
        runtime.prepare_change(
            wk.WorldChangeIntent(
                space,
                "retained facts",
                (
                    wk.CreateObject(
                        "place",
                        (
                            wk.CreateFact(
                                "name", "dnd5e:name", wk.LiteralFactValue("Towér"), meta
                            ),
                        ),
                    ),
                ),
            )
        ),
        confirmed_by="fixture",
    )
    return root, meta


@pytest.fixture
def transition_case(application_state_dsn, monkeypatch, request):
    monkeypatch.setenv("DMB_DEPLOYMENT_ENVIRONMENT", "local")
    monkeypatch.setenv("DMB_AUTH_MODE", "local_operator")
    monkeypatch.setenv("DMB_AGENT_GRAPH_AUTH_MODE", "local_operator")
    monkeypatch.setenv("DMB_AGENT_GRAPH_AUTH_ENVIRONMENT", "local")
    monkeypatch.setenv("DMB_AGENT_GRAPH_LOCAL_OPERATOR_TOKEN", TOKEN)
    monkeypatch.setenv(
        "DMB_GRAPH_REVIEW_PREPARE_BINDING_KEY", "profile-transition-test-only"
    )
    world = create_world(
        name="Transition World", owner_subject="transition-owner"
    ).record
    space = world.native_graph_binding.native_world_id
    repo = InMemoryNativeSourceEvidenceRepository()
    revision = getattr(request, "param", "2")
    profile = {
        "1": dungeonbuddy_dnd5e_semantic_profile,
        "2": dungeonbuddy_dnd5e_custom_predicate_profile,
        "3": dungeonbuddy_dnd5e_observation_profile,
    }[revision]()
    root, meta = seed(repo, profile, space)
    world = store_world(
        world.model_copy(
            update={
                "native_graph_binding": NativeGraphBindingRecord(
                    native_world_id=space,
                    status="active",
                    binding_version=3,
                    validated_at=datetime.now(UTC).isoformat(),
                    validated_head_revision_id=repo.get_head(space).head_revision_id,
                )
            }
        )
    )
    monkeypatch.setattr(service.native, "repository", lambda: repo)
    app = FastAPI()
    app.include_router(router)
    client = TestClient(
        app, client=("127.0.0.1", 50123), headers={"Authorization": "Bearer " + TOKEN}
    )
    body = {
        "schema": "dmb_native_profile_transition_prepare_v1",
        "managedWorldId": world.world_id,
        "expectedNativeWorldId": space,
        "expectedBindingVersion": 3,
        "expectedParentRevisionId": repo.get_head(space).head_revision_id,
        "publicationId": "explicit-profile",
    }
    return SimpleNamespace(**locals())


def prepare(case):
    r = case.client.post(PATH + "/prepare", json=case.body)
    assert r.status_code == 200, r.text
    return {"schema": "dmb_native_profile_transition_confirm_v1", **r.json()}


def confirm(case, packet):
    return case.client.post(PATH + "/confirm", json=packet)


def state(case):
    return deepcopy(
        {k: v for k, v in vars(case.repo).items() if k != "_lock" and not callable(v)}
    )


def resign(packet):
    p = deepcopy(packet)
    content = ProfileTransitionContent.model_validate(
        {k: v for k, v in p["plan"].items() if k != "token"}
    )
    p["plan"]["token"] = sign_publication_intent(
        content.model_dump(mode="json", by_alias=True)
    )
    return p


def descendant(case):
    stored = case.repo.get_revision(
        case.space, case.repo.get_head(case.space).head_revision_id
    )
    case.repo.publish_revision(
        PublishKnowledgeRevisionCommand(
            space_id=case.space,
            parent_revision_id=stored.revision.revision_id,
            expected_parent_revision_id=stored.revision.revision_id,
            operation_ids=["later"],
            graph_schema=stored.revision.graph_schema,
            graph_payload=stored.graph_payload,
            domain_contract_ref=stored.revision.domain_contract_ref,
            semantic_profile_ref=stored.revision.semantic_profile_ref,
            migration_origin_ref=stored.revision.migration_origin_ref,
            created_at=datetime.now(UTC),
        )
    )


@pytest.mark.parametrize("transition_case", ["1", "2", "3"], indirect=True)
def test_explicit_transition_unchanged_payload_one_event_and_readonly_expired_recovery(
    transition_case, monkeypatch
):
    c = transition_case
    before = state(c)
    packet = prepare(c)
    assert state(c) == before
    parent = c.repo.get_revision(c.space, c.body["expectedParentRevisionId"])
    events = c.repo.head_events(c.space)
    committed = confirm(c, packet)
    assert committed.status_code == 200, committed.text
    receipt = committed.json()["receipt"]
    child = c.repo.get_revision(c.space, receipt["published_revision_id"])
    assert child.graph_payload == parent.graph_payload
    assert child.revision.migration_origin_ref == parent.revision.migration_origin_ref
    assert child.revision.semantic_profile_ref.profile_revision == "4"
    assert len(c.repo.head_events(c.space)) == len(events) + 1
    descendant(c)
    now = packet["plan"]["expiresAt"]

    class Future(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime.fromisoformat(now) + timedelta(days=2)

    monkeypatch.setattr(service, "datetime", Future)
    before = state(c)

    def forbidden(*a, **k):
        pytest.fail("immutable recovery consulted current state or wrote")

    with monkeypatch.context() as p:
        for method in [
            "get_head",
            "open_native_source_view",
            "publish_publication",
            "publish_revision",
        ]:
            p.setattr(c.repo, method, forbidden)
        recovered = confirm(c, packet)
    assert recovered.status_code == 200, recovered.text
    assert recovered.json()["recovered"] and recovered.json()["receipt"] == receipt
    assert state(c) == before


def test_same_id_changed_timestamp_same_child_id_conflicts(transition_case):
    c = transition_case
    one = prepare(c)
    two = prepare(c)
    two["plan"]["request"]["created_at"] = (
        datetime.fromisoformat(one["plan"]["request"]["created_at"])
        + timedelta(microseconds=1)
    ).isoformat()
    two = resign(two)
    a = service._expected(
        c.repo, service.ProfileTransitionConfirm.model_validate(one).plan
    )
    b = service._expected(
        c.repo, service.ProfileTransitionConfirm.model_validate(two).plan
    )
    assert revision_from_command(a).revision_id == revision_from_command(b).revision_id
    assert confirm(c, one).status_code == 200
    before = state(c)
    response = confirm(c, two)
    assert response.status_code == 409, response.text
    assert "idempotency" in response.text
    assert state(c) == before


@pytest.mark.parametrize(
    "field", ["parentPayloadSha256", "preparedBy", "bindingVersion", "request"]
)
def test_signature_tamper_zero_mutation(transition_case, field):
    c = transition_case
    packet = prepare(c)
    before = state(c)
    if field == "parentPayloadSha256":
        packet["plan"][field] = "0" * 64
    elif field == "preparedBy":
        packet["plan"][field] = "someone-else"
    elif field == "bindingVersion":
        packet["plan"][field] = 4
    else:
        packet["plan"]["request"]["publication_id"] = "changed"
    response = confirm(c, packet)
    assert response.status_code == 409
    assert state(c) == before


@pytest.mark.parametrize("failure", ["expired", "already4", "head", "binding"])
def test_fresh_commit_refusals_zero_mutation(transition_case, failure):
    c = transition_case
    packet = prepare(c)
    if failure == "expired":
        packet["plan"]["expiresAt"] = packet["plan"]["request"]["created_at"]
        # Keep internally valid envelope while making its whole original review old.
        old = datetime.now(UTC) - timedelta(days=2)
        packet["plan"]["request"]["created_at"] = old.isoformat()
        packet["plan"]["expiresAt"] = (old + timedelta(hours=1)).isoformat()
        packet = resign(packet)
    elif failure == "already4":
        other = deepcopy(c.body)
        other["publicationId"] = "other-operation"
        second = c.client.post(PATH + "/prepare", json=other).json()
        assert confirm(c, {"schema": packet["schema"], **second}).status_code == 200
    elif failure == "head":
        descendant(c)
    else:
        change_binding(c.world.world_id, binding_version=4)
    before = state(c)
    r = confirm(c, packet)
    assert r.status_code == 409, r.text
    assert not r.json()["detail"]["retry_original_packet"]
    assert state(c) == before


@pytest.mark.parametrize("transition_case", ["1", "2"], indirect=True)
def test_auth_before_core_io(transition_case, monkeypatch):
    c = transition_case
    monkeypatch.setattr(
        service.native, "repository", lambda: pytest.fail("unauthorized Core IO")
    )
    for token in ["", "Bearer wrong"]:
        r = c.client.post(
            PATH + "/prepare", json=c.body, headers={"Authorization": token}
        )
        assert r.status_code == 401


@pytest.mark.parametrize("transition_case", ["1", "2"], indirect=True)
def test_late_binding_denial_is_not_unknown(transition_case, monkeypatch):
    c = transition_case
    packet = prepare(c)
    before = state(c)
    original = service._binding
    count = 0

    def check(*args):
        nonlocal count
        count += 1
        if count == 2:
            raise service.TransitionRefused("profile_transition_binding_changed")
        return original(*args)

    monkeypatch.setattr(service, "_binding", check)
    r = confirm(c, packet)
    assert r.status_code == 409 and not r.json()["detail"]["outcome_unknown"]
    assert state(c) == before


@pytest.mark.parametrize("phase", ["prepare", "confirm"])
def test_unavailable_is_phase_aware(transition_case, monkeypatch, phase):
    from dungeonmind.domain.errors import PersistenceUnavailableError

    c = transition_case
    packet = prepare(c)

    def unavailable(*args):
        raise PersistenceUnavailableError("fixture unavailable")

    monkeypatch.setattr(service.native, "repository", unavailable)
    r = c.client.post(PATH + "/" + phase, json=c.body if phase == "prepare" else packet)
    assert r.status_code == 503
    assert r.json()["detail"]["outcome_unknown"] is False
    assert r.json()["detail"]["retry_original_packet"] is (phase == "confirm")


def test_immutable_conflict_is_zero_commit(transition_case, monkeypatch):
    from dungeonmind.domain.errors import ImmutableRevisionConflictError

    c = transition_case
    packet = prepare(c)
    before = state(c)

    def conflict(*args):
        raise ImmutableRevisionConflictError("fixture conflict")

    with monkeypatch.context() as patch:
        patch.setattr(c.repo, "publish_publication", conflict)
        r = confirm(c, packet)
        assert r.status_code == 409 and not r.json()["detail"]["outcome_unknown"]
    assert state(c) == before


@pytest.mark.parametrize(
    "damage", ["parent_missing", "child_missing", "child_corrupt", "receipt_corrupt"]
)
def test_committed_reference_corruption_never_writes(
    transition_case, monkeypatch, damage
):
    c = transition_case
    packet = prepare(c)
    committed = confirm(c, packet)
    assert committed.status_code == 200
    receipt = committed.json()["receipt"]
    parent = c.body["expectedParentRevisionId"]
    child = receipt["published_revision_id"]
    if damage == "parent_missing":
        c.repo._revisions.pop((c.space, parent))
    elif damage == "child_missing":
        c.repo._revisions.pop((c.space, child))
    elif damage == "child_corrupt":
        from dataclasses import replace

        c.repo._revisions[(c.space, child)] = replace(
            c.repo._revisions[(c.space, child)], _payload_json="{}"
        )
    else:
        key = (c.space, c.body["publicationId"])
        c.repo._receipts[key] = c.repo._receipts[key].model_copy(
            update={"graph_payload_sha256": "0" * 64}
        )
    before = state(c)
    with monkeypatch.context() as patch:
        patch.setattr(
            c.repo,
            "publish_publication",
            lambda *a: pytest.fail("corrupt receipt attempted write"),
        )
        r = confirm(c, packet)
    assert r.status_code == 409, r.text
    assert not r.json()["detail"]["outcome_unknown"]
    assert state(c) == before


@pytest.mark.parametrize(
    "mutation", ["from_digest", "to_revision", "domain_digest", "origin"]
)
def test_signed_original_authority_commitments_checked(transition_case, mutation):
    c = transition_case
    packet = prepare(c)
    if mutation == "from_digest":
        packet["plan"]["request"]["from_profile_ref"]["descriptor_sha256"] = "0" * 64
    elif mutation == "to_revision":
        packet["plan"]["request"]["to_profile_ref"]["profile_revision"] = "3"
    elif mutation == "domain_digest":
        packet["plan"]["request"]["domain_contract_ref"]["descriptor_sha256"] = "0" * 64
    else:
        packet["plan"]["migrationOriginRef"] = {
            "source_system": "fixture",
            "source_root_id": "fixture",
            "source_revision_id": "fixture",
            "source_payload_sha256": "0" * 64,
            "migration_manifest_sha256": "0" * 64,
        }
    packet = resign(packet)
    before = state(c)
    r = confirm(c, packet)
    assert r.status_code == 409, r.text
    assert state(c) == before


@pytest.fixture
def sql_case(application_state_dsn, monkeypatch, request):
    from tests.test_native_recap_source_admission import native_core_dsn
    from dungeonmind.infrastructure.postgres import (
        PostgresDatabase,
        PostgresNativeSourceEvidenceRepository,
    )
    import sys

    fixture = native_core_dsn.__wrapped__(monkeypatch)
    dsn = next(fixture)
    try:
        repo = PostgresNativeSourceEvidenceRepository(PostgresDatabase(dsn))
        monkeypatch.setattr(
            sys.modules[__name__],
            "InMemoryNativeSourceEvidenceRepository",
            lambda: repo,
        )
        case = transition_case.__wrapped__(
            application_state_dsn,
            monkeypatch,
            SimpleNamespace(param=getattr(request, "param", "3")),
        )
        case.dsn = dsn
        yield case
    finally:
        try:
            next(fixture)
        except StopIteration:
            pass


def sql_counts(c):
    import psycopg
    from psycopg import sql

    with psycopg.connect(c.dsn) as conn:
        names = [
            r[0]
            for r in conn.execute(
                "SELECT tablename FROM pg_tables WHERE schemaname='dungeonmind' ORDER BY tablename"
            )
        ]
        return {
            n: conn.execute(
                sql.SQL("SELECT count(*) FROM dungeonmind.{}").format(sql.Identifier(n))
            ).fetchone()[0]
            for n in names
        }


@pytest.mark.parametrize("sql_case", ["1", "3"], indirect=True)
def test_sql_atomic_rollback_then_exact_recovery(sql_case, monkeypatch):
    c = sql_case
    before = sql_counts(c)
    head = c.repo.get_head(c.space)
    epoch = c.repo.open_native_source_view(c.space).epoch
    packet = prepare(c)
    assert sql_counts(c) == before
    fired = []

    def fault():
        fired.append(True)
        raise ConnectionError("fixture after receipt insert rollback")

    with monkeypatch.context() as patch:
        patch.setattr(c.repo, "_after_receipt_insert", fault)
        failed = confirm(c, packet)
    assert fired == [True]
    assert failed.status_code == 503, failed.text
    assert failed.json()["detail"]["retry_original_packet"]
    assert sql_counts(c) == before and c.repo.get_head(c.space) == head
    committed = confirm(c, packet)
    assert committed.status_code == 200, committed.text
    descendant(c)
    after = sql_counts(c)
    with monkeypatch.context() as patch:
        for name in [
            "get_head",
            "open_native_source_view",
            "publish_publication",
            "publish_revision",
        ]:
            patch.setattr(
                c.repo,
                name,
                lambda *a, **k: pytest.fail("SQL recovery was not read-only"),
            )
        recovered = confirm(c, packet)
    assert recovered.status_code == 200 and recovered.json()["recovered"]
    assert recovered.json()["receipt"] == committed.json()["receipt"]
    assert (
        sql_counts(c) == after
        and c.repo.open_native_source_view(c.space).epoch == epoch
    )


@pytest.mark.parametrize("sql_case", ["1", "3"], indirect=True)
def test_sql_lost_ack_verifies_original_child(sql_case, monkeypatch):
    c = sql_case
    packet = prepare(c)
    events = c.repo.head_events(c.space)
    publish = c.repo.publish_publication

    def lost(*args):
        publish(*args)
        raise ConnectionError("fixture lost ack after commit")

    with monkeypatch.context() as patch:
        patch.setattr(c.repo, "publish_publication", lost)
        response = confirm(c, packet)
    assert response.status_code == 200, response.text
    assert len(c.repo.head_events(c.space)) == len(events) + 1
    before = sql_counts(c)
    retry = confirm(c, packet)
    assert (
        retry.status_code == 200
        and retry.json()["receipt"] == response.json()["receipt"]
    )
    assert retry.json()["recovered"] and sql_counts(c) == before


@pytest.mark.parametrize("phase", ["prepare", "confirm"])
def test_missing_signing_key_is_typed_before_core_io(
    transition_case, monkeypatch, phase
):
    c = transition_case
    packet = prepare(c)
    before = state(c)
    monkeypatch.delenv("DMB_GRAPH_REVIEW_PREPARE_BINDING_KEY")
    monkeypatch.setattr(
        service.native,
        "repository",
        lambda: pytest.fail("key unavailable reached Core IO"),
    )
    r = c.client.post(PATH + "/" + phase, json=c.body if phase == "prepare" else packet)
    assert r.status_code == 503, r.text
    assert r.json()["detail"]["code"] == "authority_unavailable"
    assert not r.json()["detail"]["outcome_unknown"]
    assert r.json()["detail"]["retry_original_packet"] is (phase == "confirm")
    assert state(c) == before


def test_transition_needs_no_current_source_access_or_epoch(
    transition_case, monkeypatch
):
    from dungeonmind.application.vnext import (
        open_native_text_source_access_context,
        open_admitted_native_text,
    )

    c = transition_case
    c.repo.withdraw_native_source(
        space_id=c.space,
        source_artifact_id=c.root.source_artifact_id,
        source_revision_id=c.root.source_revision_id,
    )
    epoch = c.repo.open_native_source_view(c.space).epoch
    with monkeypatch.context() as patch:
        patch.setattr(
            c.repo,
            "open_native_source_view",
            lambda *a: pytest.fail("transition demanded source authority"),
        )
        packet = prepare(c)
        r = confirm(c, packet)
    assert r.status_code == 200, r.text
    assert c.repo.open_native_source_view(c.space).epoch == epoch
    access = open_native_text_source_access_context(
        repository=c.repo,
        space_id=c.space,
        revision_id=c.repo.get_head(c.space).head_revision_id,
        domain_contract=dungeonbuddy_world_domain_contract(),
        audience_labels=(),
    )
    assert (
        open_admitted_native_text(access, c.root.bindings[0].evidence_ref_id).status
        == "unavailable"
    )


def test_player_denied_before_binding_or_core_io(transition_case, monkeypatch):
    from apps.live_control_server.services.agent_graph_auth import NativeGraphPrincipal
    from apps.live_control_server.services.hosted_native_graph_access import (
        native_graph_explorer_dependency,
    )

    c = transition_case
    c.app.dependency_overrides[native_graph_explorer_dependency] = lambda: (
        NativeGraphPrincipal("player", "player", "local_operator")
    )
    monkeypatch.setattr(
        service.native, "binding", lambda *a: pytest.fail("player reached binding")
    )
    monkeypatch.setattr(
        service.native, "repository", lambda: pytest.fail("player reached Core")
    )
    assert c.client.post(PATH + "/prepare", json=c.body).status_code == 403


@pytest.mark.parametrize("race", ["head", "binding"])
def test_prepare_rechecks_read_boundary_without_writing(
    transition_case, monkeypatch, race
):
    c = transition_case
    before = state(c)
    reads = []
    if race == "head":
        original = c.repo.get_head

        def head(*args):
            reads.append(True)
            return (
                original(*args)
                if len(reads) == 1
                else SimpleNamespace(head_revision_id="rev:changed")
            )

        monkeypatch.setattr(c.repo, "get_head", head)
    else:
        original = service.native.binding

        def binding(*args):
            reads.append(True)
            if len(reads) == 2:
                change_binding(c.world.world_id, binding_version=4)
            return original(*args)

        monkeypatch.setattr(service.native, "binding", binding)
    response = c.client.post(PATH + "/prepare", json=c.body)
    assert response.status_code == 409, response.text
    assert len(reads) == 2 and state(c) == before


def test_core_cas_rejects_head_race_at_publish(transition_case, monkeypatch):
    c = transition_case
    packet = prepare(c)
    events = c.repo.head_events(c.space)
    publish = c.repo.publish_publication

    def raced(*args):
        descendant(c)
        return publish(*args)

    with monkeypatch.context() as patch:
        patch.setattr(c.repo, "publish_publication", raced)
        response = confirm(c, packet)
    assert response.status_code == 409, response.text
    assert not response.json()["detail"]["outcome_unknown"]
    assert c.repo.get_publication_receipt(c.space, c.body["publicationId"]) is None
    assert len(c.repo.head_events(c.space)) == len(events) + 1  # External actor only.


def test_nonnull_origin_and_post4_observation_precedence_reads(transition_case):
    from dungeonmind.application.vnext import open_native_text_source_access_context
    from dungeonmind.contracts.vnext.knowledge import MigrationOriginRef
    from graph_memory.vnext.domain_runtime import (
        DungeonBuddyVNextProjectionInput,
        build_dungeonbuddy_read_context,
    )

    c = transition_case
    parent = c.repo.get_revision(c.space, c.body["expectedParentRevisionId"])
    origin = MigrationOriginRef(
        source_system="fixture-origin-only",
        source_root_id="fixture-root",
        source_revision_id="fixture-revision",
        source_payload_sha256=parent.graph_payload_sha256,
        migration_manifest_sha256="1" * 64,
    )
    # Synthetic origin metadata fixture: not a claim to reconstruct legacy history.
    c.repo.publish_revision(
        PublishKnowledgeRevisionCommand(
            space_id=c.space,
            parent_revision_id=parent.revision.revision_id,
            expected_parent_revision_id=parent.revision.revision_id,
            operation_ids=["origin-fixture"],
            graph_schema=parent.revision.graph_schema,
            graph_payload=parent.graph_payload,
            domain_contract_ref=parent.revision.domain_contract_ref,
            semantic_profile_ref=parent.revision.semantic_profile_ref,
            migration_origin_ref=origin,
            created_at=datetime.now(UTC),
        )
    )
    c.body["expectedParentRevisionId"] = c.repo.get_head(c.space).head_revision_id
    packet = prepare(c)
    committed = confirm(c, packet)
    assert committed.status_code == 200, committed.text
    child = c.repo.get_revision(
        c.space, committed.json()["receipt"]["published_revision_id"]
    )
    assert (
        child.revision.migration_origin_ref == origin
        and child.graph_payload == parent.graph_payload
    )
    runtime = DungeonMindWorldKeeperRuntime(
        repository=c.repo,
        domain_contract=dungeonbuddy_world_domain_contract(),
        semantic_profile=dungeonbuddy_dnd5e_manual_profile(),
        clock=lambda: datetime.now(UTC),
        prepared_id_factory=lambda: "post4-proof",
    )
    prepared = runtime.prepare_change(
        wk.WorldChangeIntent(
            c.space,
            "explicit fixture facts",
            (
                wk.CreateObject(
                    "earlier",
                    (
                        wk.CreateFact(
                            "observed",
                            "dungeonbuddy:reviewed_source_observation",
                            wk.LiteralFactValue("A traveller owns the towér."),
                            c.meta,
                        ),
                    ),
                ),
                wk.CreateObject("later"),
                wk.CreateRelationship(
                    "precedes",
                    wk.ResultOf("earlier"),
                    "dungeonbuddy.custom:precedes",
                    wk.ResultOf("later"),
                    c.meta,
                ),
            ),
        )
    )
    result = runtime.commit_prepared_change(
        prepared, confirmed_by="fixture-explicit-review"
    )
    access = open_native_text_source_access_context(
        repository=c.repo,
        space_id=c.space,
        revision_id=result.child_revision_id,
        domain_contract=dungeonbuddy_world_domain_contract(),
        audience_labels=(),
    )
    context = build_dungeonbuddy_read_context(
        parsed_revision=access.parsed,
        projection_input=DungeonBuddyVNextProjectionInput(
            world_id=c.space, scope_mode="world", role="gm"
        ),
        source_reader=access.source_view,
    )
    ids = [r.durable_assertion_id for r in result.assertion_results]
    assert set(context.admit_candidates(ids).admitted_assertion_ids) == set(ids)


@pytest.mark.parametrize("transition_case", ["1", "2"], indirect=True)
def test_accepted_target_declaration_drift_refused(transition_case, monkeypatch):
    from graph_memory.vnext import domain_runtime

    c = transition_case
    constructor = domain_runtime.dungeonbuddy_dnd5e_manual_profile

    def drifted():
        profile = constructor()
        profile.predicates.pop()
        return profile

    monkeypatch.setattr(domain_runtime, "dungeonbuddy_dnd5e_manual_profile", drifted)
    before = state(c)
    response = c.client.post(PATH + "/prepare", json=c.body)
    assert response.status_code == 409, response.text
    assert "descriptor_drift" in response.text
    assert state(c) == before


@pytest.mark.parametrize("phase", ["prepare", "confirm"])
@pytest.mark.parametrize(
    "failure,code,status",
    [
        ("missing_world", "managed_world_not_found", 404),
        ("missing_binding", "native_graph_binding_missing", 409),
        ("inactive", "native_graph_binding_inactive", 409),
        ("unavailable", "managed_world_unavailable", 503),
    ],
)
def test_binding_service_errors_are_typed_before_core_io(
    transition_case, monkeypatch, phase, failure, code, status
):
    from application_state.world_catalog import service as catalog
    from apps.live_control_server.services import (
        managed_world_graph_projection as managed,
    )
    from apps.live_control_server.services.world_container_registry import (
        WorldContainerRegistryError,
    )

    c = transition_case
    packet = prepare(c)
    body = deepcopy(c.body if phase == "prepare" else packet)
    if failure == "missing_world":
        if phase == "prepare":
            body["managedWorldId"] = "absent-fixture-world"
        else:
            body["plan"]["managedWorldId"] = "absent-fixture-world"
            body = resign(body)
    elif failure == "missing_binding":
        stored = catalog.get_world(c.world.world_id)
        catalog.save_world(
            stored.record.model_copy(update={"native_graph_binding": None}),
            expected_revision=stored.revision,
        )
    elif failure == "inactive":
        change_binding(c.world.world_id, status="inactive")
    else:

        def unavailable(*args):
            raise WorldContainerRegistryError("fixture unavailable", status_code=503)

        monkeypatch.setattr(managed, "get_world_container", unavailable)
    before = state(c)
    monkeypatch.setattr(
        service.native,
        "repository",
        lambda: pytest.fail("binding refusal reached Core IO"),
    )
    response = c.client.post(PATH + "/" + phase, json=body)
    assert response.status_code == status, response.text
    assert response.json()["detail"]["code"] == code
    assert not response.json()["detail"]["outcome_unknown"]
    assert response.json()["detail"]["retry_original_packet"] is (
        phase == "confirm" and status == 503
    )
    assert state(c) == before


def test_late_inactive_binding_keeps_typed_denial_without_receipt_probe(
    transition_case, monkeypatch
):
    c = transition_case
    packet = prepare(c)
    before = state(c)
    binding = service.native.binding
    reads = []

    def revoke(*args):
        reads.append(True)
        if len(reads) == 2:
            change_binding(c.world.world_id, status="inactive")
        return binding(*args)

    monkeypatch.setattr(service.native, "binding", revoke)
    response = confirm(c, packet)
    assert len(reads) == 2
    assert response.status_code == 409, response.text
    assert response.json()["detail"]["code"] == "native_graph_binding_inactive"
    assert not response.json()["detail"]["outcome_unknown"]
    assert state(c) == before


@pytest.mark.parametrize("token,status", [("é", 422), ("v1.invalid.invalid", 409)])
def test_invalid_token_is_typed_before_core_io(
    transition_case, monkeypatch, token, status
):
    c = transition_case
    packet = prepare(c)
    assert packet["plan"]["token"].isascii()
    packet["plan"]["token"] = token
    before = state(c)
    monkeypatch.setattr(
        service.native,
        "repository",
        lambda: pytest.fail("invalid token reached Core IO"),
    )
    response = confirm(c, packet)
    assert response.status_code == status, response.text
    if status == 409:
        assert (
            response.json()["detail"]["code"] == "profile_transition_signature_invalid"
        )
    else:
        assert any(error["loc"][-1] == "token" for error in response.json()["detail"])
    assert state(c) == before
