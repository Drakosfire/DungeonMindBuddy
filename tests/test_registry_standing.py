"""Real Core/WK component lifecycle; synthetic corpus never counts as full-world proof."""

from copy import deepcopy
from dataclasses import replace
from datetime import UTC, datetime, timedelta
import hashlib
import json
from types import SimpleNamespace
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from apps.live_control_server.models.registry_standing import (
    SourceRequest,
    PrepareRequest,
    ConfirmRequest,
    IdentityChoice,
)
from apps.live_control_server.services import registry_standing as service
from apps.live_control_server.services.agent_graph_auth import NativeGraphPrincipal
from apps.live_control_server.integrations.dungeonmind import (
    native_registry_source as native,
)
from apps.live_control_server.integrations.worldkeeper import (
    registry_standing_consumer as wk,
)
from graph_memory.vnext.domain_runtime import (
    dungeonbuddy_world_domain_contract,
    dungeonbuddy_dnd5e_semantic_profile,
    dungeonbuddy_dnd5e_custom_predicate_profile,
)
from dungeonmind.application.vnext import initialize_empty_knowledge_space
from dungeonmind.contracts.vnext.knowledge import PublishKnowledgeRevisionCommand
from dungeonmind.infrastructure.memory.vnext_sources import (
    InMemoryNativeSourceEvidenceRepository,
)

NOW = datetime(2026, 10, 28, 20, tzinfo=UTC)
GM = NativeGraphPrincipal("test-operator", "gm", "local_operator")
NAMES = ["Ada", "Bea", "Cai", "Dee", "Eli", "Fay"]


@pytest.fixture(params=("1", "2"))
def lane(tmp_path, monkeypatch, request):
    monkeypatch.setenv("DMB_GRAPH_REVIEW_PREPARE_BINDING_KEY", "standing-test-key")
    repo = InMemoryNativeSourceEvidenceRepository()
    domain = dungeonbuddy_world_domain_contract()
    profile = (
        dungeonbuddy_dnd5e_custom_predicate_profile()
        if request.param == "2"
        else dungeonbuddy_dnd5e_semantic_profile()
    )
    initial = initialize_empty_knowledge_space(
        repository=repo,
        space_id="test-world",
        initialization_id="standing-fixture",
        created_at=NOW,
        domain_contract=domain,
        semantic_profile=profile,
    )
    bound = dict(
        managed_world_id="test",
        native_world_id="test-world",
        binding_version=1,
        source_root_relpath="corpus/test",
    )
    campaign = tmp_path / "corpus/test/Longmont Campaign/Campaign 1"
    campaign.mkdir(parents=True)
    registry = dict(
        schema="party_registry_v1",
        campaign_id="longmont-c1",
        session_pc_rosters={"1": [n.lower() for n in NAMES]},
    )
    data = json.dumps(registry).encode()
    (campaign / "_party_registry.json").write_bytes(data)
    hashes = {}
    for name in NAMES:
        slug = name.lower()
        path = campaign / f"PCs/{slug}/{slug}_character_dossier.md"
        path.parent.mkdir(parents=True)
        text = (
            "---\ncampaign_id: longmont-c1\ntemporal_scope: campaign_stateful\n"
            "session: null\nsource_class: authored_dossier\nsubject_class: pc\n---\n"
            f"**{name}** is a core PC in Longmont Campaign 1.\n"
        )
        path.write_text(text)
        hashes[slug] = hashlib.sha256(text.encode()).hexdigest()
    monkeypatch.setattr(native.config, "managed_world_data_root", lambda: tmp_path)
    monkeypatch.setattr(native, "binding", lambda _: bound.copy())
    monkeypatch.setattr(native, "repository", lambda: repo)
    request = SourceRequest(
        managed_world_id="test",
        campaign_id="longmont-c1",
        roster_key="1",
        operation_id=uuid4(),
        created_at=NOW,
        expected_parent_revision_id=initial.published_revision_id,
        registry_sha256=hashlib.sha256(data).hexdigest(),
        dossier_sha256=hashes,
    )
    return SimpleNamespace(repo=repo, request=request, bound=bound, root=tmp_path)


def sources(lane):
    return service.source(lane.request, GM)


def prepared(lane, source=None, choices=None):
    source = source or sources(lane)
    return service.prepare(
        PrepareRequest(
            operation_id=uuid4(),
            **source,
            choices=choices
            or [IdentityChoice(slug=n.lower(), action="create") for n in NAMES],
        ),
        GM,
    )


def advance(repo):
    head = repo.get_head("test-world")
    old = repo.get_revision("test-world", head.head_revision_id)
    return repo.publish_revision(
        PublishKnowledgeRevisionCommand(
            space_id="test-world",
            parent_revision_id=head.head_revision_id,
            expected_parent_revision_id=head.head_revision_id,
            operation_ids=[str(uuid4())],
            graph_schema=old.revision.graph_schema,
            graph_payload=deepcopy(old.graph_payload),
            domain_contract_ref=old.revision.domain_contract_ref,
            semantic_profile_ref=old.revision.semantic_profile_ref,
            created_at=NOW,
        )
    )


def test_complete_real_core_wk_component_and_exact_retry(lane):
    source = sources(lane)
    assert len(source["source_packet"]["rows"]) == 6
    head = lane.repo.get_head("test-world")
    assert (
        sources(lane)["source_packet"]["context"]["revision_id"]
        == head.head_revision_id
    )
    assert lane.repo.get_head("test-world") == head
    packet = prepared(lane, source)
    decoded = wk.decode_prepared(packet["prepared"])
    assert decoded._domain_contract_json and decoded._semantic_profile_json
    assert wk.decode_prepared(wk.encode_prepared(decoded)) == decoded
    assert all(
        f.metadata.temporal_scope.kind == "unknown"
        for op in decoded.prepared_operations
        for f in op.facts
    )
    committed = service.confirm(ConfirmRequest(**packet), GM)
    assert len(committed["result"]["object_results"]) == 6
    assert len(committed["result"]["assertion_results"]) == 12
    after = lane.repo.get_head("test-world")
    again = service.confirm(ConfirmRequest(**packet), GM)
    assert again["recovered"] and again["result"] == committed["result"]
    assert lane.repo.get_head("test-world") == after


def test_completed_expired_recovery_after_descendants_never_reads_current_sources(
    lane, monkeypatch
):
    packet = prepared(lane)
    result = service.confirm(ConfirmRequest(**packet), GM)
    advance(lane.repo)
    head = lane.repo.get_head("test-world")
    packet["envelope"]["expires_at"] = (
        service._now() - timedelta(seconds=1)
    ).isoformat()
    packet["token"] = service.sign_publication_intent(packet["envelope"])

    def forbidden(*_, **__):
        raise AssertionError("completed replay read current source/context")

    monkeypatch.setattr(service, "_validate_current", forbidden)
    again = service.confirm(ConfirmRequest(**packet), GM)
    assert again["result"] == result["result"] and again["recovered"]
    assert lane.repo.get_head("test-world") == head


def test_expired_uncommitted_cannot_call_writer(lane, monkeypatch):
    packet = prepared(lane)
    packet["envelope"]["expires_at"] = (
        service._now() - timedelta(seconds=1)
    ).isoformat()
    packet["token"] = service.sign_publication_intent(packet["envelope"])
    monkeypatch.setattr(
        wk, "runtime", lambda *a, **k: pytest.fail("expired writer called")
    )
    with pytest.raises(ValueError, match="no committed receipt"):
        service.confirm(ConfirmRequest(**packet), GM)


@pytest.mark.parametrize(
    "field", ["principal", "purpose", "schema", "prepared_digest", "operation_id"]
)
def test_envelope_tamper_refuses(lane, field):
    packet = prepared(lane)
    head = lane.repo.get_head("test-world")
    packet["envelope"][field] = "tampered"
    with pytest.raises(ValueError):
        service.confirm(ConfirmRequest(**packet), GM)
    assert lane.repo.get_head("test-world") == head


def test_complete_transport_refuses_unknown_missing_and_wrong_typed_fields(lane):
    packet = prepared(lane)["prepared"]
    bad = deepcopy(packet)
    bad["value"]["fields"].pop("_domain_contract_json")
    with pytest.raises(ValueError):
        wk.decode_prepared(bad)
    bad = deepcopy(packet)
    bad["value"]["fields"]["prepared_operations"]["items"][0]["type"] = (
        "CreateRelationship"
    )
    with pytest.raises(ValueError):
        wk.decode_prepared(bad)
    bad = deepcopy(packet)
    bad["schema"] = "other"
    with pytest.raises(ValueError):
        wk.decode_prepared(bad)


def test_prepare_internal_parent_race_is_never_signed(lane, monkeypatch):
    source = sources(lane)
    real = wk.runtime

    def racing(*a, **k):
        runtime = real(*a, **k)
        return SimpleNamespace(
            prepare_change=lambda intent: (
                advance(lane.repo),
                runtime.prepare_change(intent),
            )[1]
        )

    monkeypatch.setattr(wk, "runtime", racing)
    monkeypatch.setattr(
        service,
        "sign_publication_intent",
        lambda _: pytest.fail("raced preparation signed"),
    )
    with pytest.raises(ValueError, match="changed during WK"):
        prepared(lane, source)


def test_stale_confirm_and_core_cas_refuse_without_rebase(lane):
    packet = prepared(lane)
    decoded = wk.decode_prepared(packet["prepared"])
    advance(lane.repo)
    head = lane.repo.get_head("test-world")
    with pytest.raises(ValueError, match="context changed"):
        service.confirm(ConfirmRequest(**packet), GM)
    from worldkeeper.application.commit import PreparedChangeStale

    domain, profile = native.descriptors(
        lane.repo, "test-world", lane.repo.get_head("test-world").head_revision_id
    )
    with pytest.raises(PreparedChangeStale):
        wk.runtime(
            lane.repo, domain, profile, now=NOW, operation_id=decoded.prepared_change_id
        ).commit_prepared_change(decoded, GM.subject)
    assert lane.repo.get_head("test-world") == head


def test_source_partial_failure_resumes_exactly(lane, monkeypatch):
    real = native.publish_native_text_source_evidence
    calls = []

    def fail(*a, **k):
        calls.append(k["request"].admission_id)
        if len(calls) == 3:
            raise ValueError("interrupted")
        return real(*a, **k)

    monkeypatch.setattr(native, "publish_native_text_source_evidence", fail)
    with pytest.raises(ValueError, match="interrupted"):
        sources(lane)
    partial = lane.repo.get_head("test-world")
    assert partial.head_revision_id != lane.request.expected_parent_revision_id
    monkeypatch.setattr(native, "publish_native_text_source_evidence", real)
    packet = sources(lane)
    assert len(packet["source_packet"]["rows"]) == 6
    sources(lane)  # replay of all six has no new child
    assert (
        lane.repo.get_head("test-world").head_revision_id
        == packet["source_packet"]["context"]["revision_id"]
    )


def test_changed_cohort_or_dossier_refuses_before_source_write(lane):
    head = lane.repo.get_head("test-world")
    bad = lane.request.model_copy(update={"registry_sha256": "0" * 64})
    with pytest.raises(ValueError, match="registry"):
        service.source(bad, GM)
    p = (
        lane.root
        / "corpus/test/Longmont Campaign/Campaign 1/PCs/ada/ada_character_dossier.md"
    )
    p.write_text(p.read_text() + "drift")
    with pytest.raises(ValueError, match="dossier bytes"):
        sources(lane)
    assert lane.repo.get_head("test-world") == head


def test_choices_exact_and_reuse_not_bare_id(lane):
    source = sources(lane)
    choices = [IdentityChoice(slug=n.lower(), action="create") for n in NAMES]
    choices[0] = IdentityChoice(
        slug="ada", action="use_existing", entity_id="ent:missing"
    )
    with pytest.raises(ValueError, match="lacks admitted support"):
        prepared(lane, source, choices)
    choices[-1] = choices[0]
    with pytest.raises(ValueError, match="exactly"):
        prepared(lane, source, choices)


def test_http_auth_precedes_all_source_or_native_io(lane, monkeypatch):
    from apps.live_control_server.routes.registry_standing import router

    app = FastAPI()
    app.include_router(router)
    monkeypatch.setenv("DMB_AGENT_GRAPH_AUTH_MODE", "local_operator")
    monkeypatch.setenv("DMB_AGENT_GRAPH_AUTH_ENVIRONMENT", "local")
    monkeypatch.setenv("DMB_AGENT_GRAPH_LOCAL_OPERATOR_TOKEN", "x" * 40)
    monkeypatch.setattr(native, "binding", lambda _: pytest.fail("unauthorized IO"))
    client = TestClient(app, client=("127.0.0.1", 45000))
    response = client.post(
        "/api/live/extract-promote/registry-standing/source",
        json=lane.request.model_dump(mode="json"),
    )
    assert response.status_code == 401
    response = client.post(
        "/api/live/extract-promote/registry-standing/source",
        content='{"a":1,"a":2}',
        headers={"Authorization": "Bearer " + "x" * 40},
    )
    assert response.status_code == 422


def test_player_service_cannot_read_or_write(lane, monkeypatch):
    from fastapi import HTTPException

    monkeypatch.setattr(native, "binding", lambda _: pytest.fail("player IO"))
    with pytest.raises(HTTPException) as exc:
        service.source(lane.request, replace(GM, role="player"))
    assert exc.value.status_code == 403


def test_existing_supported_person_reused_and_campaign_reads_isolated(lane):
    first = prepared(lane)
    committed = service.confirm(ConfirmRequest(**first), GM)
    ids = {
        r["client_op_id"]: r["durable_object_id"]
        for r in committed["result"]["object_results"]
    }
    source = sources(lane)  # exact source replay, fresh reviewed head
    choices = [
        IdentityChoice(slug=n.lower(), action="use_existing", entity_id=ids[n.lower()])
        for n in NAMES
    ]
    second = prepared(lane, source, choices)
    result = service.confirm(ConfirmRequest(**second), GM)
    assert result["result"]["object_results"] == []
    from graph_memory.vnext.domain_runtime import (
        DungeonBuddyVNextProjectionInput,
        build_dungeonbuddy_read_context,
    )
    from dungeonmind.application.vnext import EntityReadService

    context, access = native.access_context(lane.repo, "test-world")
    for campaign, expected in [("longmont-c1", 4), ("synthetic-c2", 0)]:
        read = build_dungeonbuddy_read_context(
            parsed_revision=access.parsed,
            projection_input=DungeonBuddyVNextProjectionInput(
                world_id="test-world",
                scope_mode="campaign",
                role="gm",
                campaign_id=campaign,
                revision_id=context["revision_id"],
            ),
            source_reader=access.source_view,
        )
        entity = EntityReadService().get_entity(read, ids["ada"])
        assert len(entity.assertions) == expected


def test_same_operation_different_prepared_meaning_cannot_publish_twice(lane):
    source = sources(lane)
    request = PrepareRequest(
        operation_id=uuid4(),
        **source,
        choices=[IdentityChoice(slug=n.lower(), action="create") for n in NAMES],
    )
    first = service.prepare(request, GM)
    second = service.prepare(request, GM)
    assert first["envelope"]["prepared_id"] == second["envelope"]["prepared_id"]
    service.confirm(ConfirmRequest(**first), GM)
    head = lane.repo.get_head("test-world")
    from worldkeeper.application.commit import PreparedChangeConflict

    with pytest.raises(PreparedChangeConflict):
        service.confirm(ConfirmRequest(**second), GM)
    assert lane.repo.get_head("test-world") == head
    with pytest.raises(ValueError, match="already committed"):
        service.prepare(request, GM)


def test_codec_rejects_primitive_in_operation_tuple(lane):
    packet = prepared(lane)["prepared"]
    packet["value"]["fields"]["prepared_operations"]["items"][0] = "not-an-operation"
    with pytest.raises(ValueError, match="wrong typed"):
        wk.decode_prepared(packet)


def test_synthetic_c2_existing_person_fact_addition_does_not_leak_to_c1(lane):
    from worldkeeper.application import contracts as contracts
    from dungeonmind.application.vnext import EntityReadService
    from graph_memory.vnext.domain_runtime import (
        DungeonBuddyVNextProjectionInput,
        build_dungeonbuddy_read_context,
    )

    packet = prepared(lane)
    result = service.confirm(ConfirmRequest(**packet), GM)
    target = next(
        r["durable_object_id"]
        for r in result["result"]["object_results"]
        if r["client_op_id"] == "ada"
    )
    original = wk.decode_prepared(packet["prepared"])
    first_fact = original.prepared_operations[0].facts[0]
    # Name support is the exact synthetic Ada passage. This does not assert a real C2 PC role.
    fact = replace(
        first_fact,
        client_op_id="synthetic-c2-name",
        metadata=replace(
            first_fact.metadata,
            scope=(
                contracts.ScopeBinding("dungeonbuddy.scope:campaign", "synthetic-c2"),
            ),
        ),
    )
    intent = contracts.WorldChangeIntent(
        "test-world", "test:synthetic-c2", (contracts.UseExisting(target, (fact,)),)
    )
    domain, profile = native.descriptors(
        lane.repo, "test-world", lane.repo.get_head("test-world").head_revision_id
    )
    runtime = wk.runtime(
        lane.repo, domain, profile, now=NOW, operation_id="synthetic-c2-reuse"
    )
    change = runtime.prepare_change(intent)
    committed = runtime.commit_prepared_change(change, GM.subject)
    assert committed.object_results == ()
    context, access = native.access_context(lane.repo, "test-world")
    for campaign, expected in [("longmont-c1", 2), ("synthetic-c2", 1)]:
        read = build_dungeonbuddy_read_context(
            parsed_revision=access.parsed,
            projection_input=DungeonBuddyVNextProjectionInput(
                world_id="test-world",
                scope_mode="campaign",
                role="gm",
                campaign_id=campaign,
                revision_id=context["revision_id"],
            ),
            source_reader=access.source_view,
        )
        assert len(EntityReadService().get_entity(read, target).assertions) == expected


@pytest.mark.parametrize("change", ["graph_sha256", "domain_ref", "profile_ref"])
def test_returned_parent_contract_drift_is_refused(lane, change):
    packet = prepared(lane)
    prepared_value = wk.decode_prepared(packet["prepared"])
    context = deepcopy(packet["envelope"]["source"]["context"])
    if change == "graph_sha256":
        context[change] = "0" * 64
    else:
        context[change]["descriptor_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="changed during WK"):
        wk.verify_prepared_parent(prepared_value, context)


def test_forwarded_or_wrong_principal_never_gets_standing_authority(lane, monkeypatch):
    from apps.live_control_server.routes.registry_standing import router
    from apps.live_control_server.services.graph_object_authoring_prepare import (
        GraphObjectAuthoringError,
    )

    app = FastAPI()
    app.include_router(router)
    monkeypatch.setenv("DMB_AGENT_GRAPH_AUTH_MODE", "local_operator")
    monkeypatch.setenv("DMB_AGENT_GRAPH_AUTH_ENVIRONMENT", "local")
    monkeypatch.setenv("DMB_AGENT_GRAPH_LOCAL_OPERATOR_TOKEN", "x" * 40)
    client = TestClient(app, client=("127.0.0.1", 45000))
    response = client.post(
        "/api/live/extract-promote/registry-standing/source",
        json=lane.request.model_dump(mode="json"),
        headers={"Authorization": "Bearer " + "x" * 40, "X-Forwarded-For": "192.0.2.1"},
    )
    assert response.status_code == 403
    packet = prepared(lane)
    with pytest.raises((ValueError, GraphObjectAuthoringError)):
        service.confirm(ConfirmRequest(**packet), replace(GM, subject="other-operator"))


@pytest.mark.parametrize(
    "field,change,code",
    (
        (
            "domain_contract_ref",
            {"domain_id": "foreign.world"},
            "descriptor_unsupported",
        ),
        ("domain_contract_ref", {"domain_revision": "99"}, "descriptor_unsupported"),
        ("domain_contract_ref", {"descriptor_sha256": "0" * 64}, "descriptor_mismatch"),
        ("semantic_profile_ref", {"profile_revision": "99"}, "descriptor_unsupported"),
        (
            "semantic_profile_ref",
            {"descriptor_sha256": "0" * 64},
            "descriptor_mismatch",
        ),
    ),
)
def test_registry_rejects_unrecognized_parent_before_source_write(
    lane, monkeypatch, field, change, code
):
    from graph_memory.vnext.domain_runtime import DungeonBuddyDescriptorError

    head = lane.repo.get_head("test-world")
    original = lane.repo.get_revision

    def invalid_revision(space_id, revision_id):
        snapshot = original(space_id, revision_id)
        ref = getattr(snapshot.revision, field).model_copy(update=change)
        return SimpleNamespace(
            revision=snapshot.revision.model_copy(update={field: ref})
        )

    def forbidden_write(**_):
        raise AssertionError("Invalid parent descriptors reached source mutation")

    monkeypatch.setattr(lane.repo, "get_revision", invalid_revision)
    monkeypatch.setattr(native, "publish_native_text_source_evidence", forbidden_write)
    with pytest.raises(DungeonBuddyDescriptorError) as caught:
        sources(lane)
    assert caught.value.code == code
    assert lane.repo.get_head("test-world") == head
