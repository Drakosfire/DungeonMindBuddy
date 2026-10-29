"""Actual pinned Core/WK and authenticated routes, never a full-ingestion score."""

from copy import deepcopy
from dataclasses import replace
from datetime import UTC, datetime
import hashlib
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from dungeonmind.application.vnext import initialize_empty_knowledge_space
from dungeonmind.contracts.vnext.knowledge import PublishKnowledgeRevisionCommand
from dungeonmind.infrastructure.memory.vnext_sources import (
    InMemoryNativeSourceEvidenceRepository,
)
from graph_memory.vnext.domain_runtime import (
    dungeonbuddy_world_domain_contract,
    dungeonbuddy_dnd5e_custom_predicate_profile,
    CAMPAIGN_SCOPE_AXIS,
    GM_LABEL,
)
from tests.test_demo_j1_native_world_source_admission import (
    _committed_source,
    _admit,
    native as sources,
)
from apps.live_control_server.models.source_statements import (
    StatementSelection,
    ConfirmStatement,
)
from apps.live_control_server.services import source_statements as service
from apps.live_control_server.integrations.worldkeeper import (
    registry_standing_consumer as transport,
)
from apps.live_control_server.integrations.worldkeeper import (
    source_statements as mapping,
)
from apps.live_control_server.services.agent_graph_auth import NativeGraphPrincipal
from worldkeeper.application import contracts as wk

NOW = datetime(2026, 10, 29, tzinfo=UTC)
GM = NativeGraphPrincipal("operator", "gm", "local_operator")
BODY = "A reports that B fled; uncertain.\nAnother source-local episode.\n"


@pytest.fixture
def lane(tmp_path, monkeypatch):
    monkeypatch.setenv("DMB_GRAPH_REVIEW_PREPARE_BINDING_KEY", "statement-tests")
    repo = InMemoryNativeSourceEvidenceRepository()
    monkeypatch.setattr(sources, "_repository", lambda: repo)
    world, record = _committed_source(tmp_path, markdown=BODY)
    domain = dungeonbuddy_world_domain_contract()
    profile = dungeonbuddy_dnd5e_custom_predicate_profile()
    initialize_empty_knowledge_space(
        repository=repo,
        space_id=world.world_id,
        initialization_id="statement-fixture",
        created_at=NOW,
        domain_contract=domain,
        semantic_profile=profile,
    )
    source = _admit(tmp_path, record.document_id)
    meta = wk.AssertionMetadata(
        scope=(wk.ScopeBinding(CAMPAIGN_SCOPE_AXIS, "c1"),),
        visibility=wk.Visibility("labels_any", (GM_LABEL,)),
        epistemic_basis="asserted",
        claim_mode="dungeonbuddy.claim:fact",
        standing="established",
        evidence_ref_ids=(source.evidence_ref_id,),
        temporal_scope=wk.TemporalScope(kind="unknown"),
    )
    operations = tuple(
        wk.CreateObject(
            name,
            (
                wk.CreateFact(
                    name + ":name", "dnd5e:name", wk.LiteralFactValue(name), meta
                ),
            ),
        )
        for name in ("A", "B")
    )
    runtime = transport.runtime(
        repo, domain, profile, now=NOW, operation_id="fixture-endpoints"
    )
    result = runtime.commit_prepared_change(
        runtime.prepare_change(
            wk.WorldChangeIntent(world.world_id, "fixture", operations)
        ),
        confirmed_by=GM.subject,
    )
    ids = {r.client_op_id: r.durable_object_id for r in result.object_results}
    bound = {
        "managed_world_id": world.world_id,
        "native_world_id": world.world_id,
        "binding_version": 1,
    }
    monkeypatch.setattr(service.native, "repository", lambda: repo)
    monkeypatch.setattr(service.native, "binding", lambda _: bound.copy())
    clause = BODY.splitlines(keepends=True)[0].encode()
    selection = StatementSelection(
        managed_world_id=world.world_id,
        campaign_id="c1",
        expected_parent_revision_id=result.child_revision_id,
        source_admission_id=source.admission_id,
        evidence_ref_id=source.evidence_ref_id,
        source_sha256=hashlib.sha256(BODY.encode()).hexdigest(),
        start_byte=0,
        end_byte=len(clause),
        clause_sha256=hashlib.sha256(clause).hexdigest(),
        meaning="B fled",
        mode="reported",
        reporter=ids["A"],
        referents=[ids["B"]],
        uncertainty=["uncertain"],
        qualifications={"source_local": "report only"},
        episode="episode-1",
        source_order=[],
    )
    return SimpleNamespace(
        repo=repo, world=world, selection=selection, ids=ids, meta=meta
    )


def packet(lane):
    staged = service.prepare(lane.selection, GM)
    return ConfirmStatement(**{k: staged[k] for k in ("envelope", "prepared", "token")})


def commit(lane):
    prepared = packet(lane)
    return prepared, service.confirm(prepared, GM)


def advance(lane):
    head = lane.repo.get_head(lane.world.world_id)
    old = lane.repo.get_revision(lane.world.world_id, head.head_revision_id)
    return lane.repo.publish_revision(
        PublishKnowledgeRevisionCommand(
            space_id=lane.world.world_id,
            parent_revision_id=head.head_revision_id,
            expected_parent_revision_id=head.head_revision_id,
            operation_ids=[str(uuid4())],
            graph_schema=old.revision.graph_schema,
            graph_payload=old.graph_payload,
            domain_contract_ref=old.revision.domain_contract_ref,
            semantic_profile_ref=old.revision.semantic_profile_ref,
            created_at=NOW,
        )
    )


def read(lane, revision, principal=GM, campaign="c1"):
    return service.read_subject(
        managed_world_id=lane.world.world_id,
        campaign_id=campaign,
        revision_id=revision,
        entity_id=lane.ids["B"],
        principal=principal,
    )


def test_atomic_publish_discovery_and_no_event_fact(lane):
    prepared, result = commit(lane)
    output = read(lane, result["result"]["receipt"]["published_revision_id"])
    assert output["status"] == "complete" and len(output["statements"]) == 1
    bundle = output["statements"][0]
    assert bundle["payload"] == prepared.envelope["payload"]
    assert bundle["payload"]["embedded_content_factive"] is False
    assert len(bundle["assertion_ids"]) == 3
    assert service.confirm(prepared, GM)["result"] == result["result"]
    # Read begins from B; no pre-known statement ID is supplied.
    assert bundle["statement_id"] != lane.ids["B"]
    for principal, campaign in ((replace(GM, role="player"), "c1"), (GM, "c2")):
        hidden = read(lane, output["revision_id"], principal, campaign)
        assert hidden["status"] == "no_visible_statements" and not hidden["statements"]
        assert hidden["universal_absence_claimed"] is False


@pytest.mark.parametrize(
    "field",
    ["meaning", "episode", "reporter", "referents", "uncertainty", "qualifications"],
)
def test_same_clause_changed_meaning_conflicts_not_duplicate(lane, field):
    _, result = commit(lane)
    advance(lane)
    head = lane.repo.get_head(lane.world.world_id)
    changes = {
        "meaning": "B attacked A",
        "episode": "episode-2",
        "reporter": lane.ids["B"],
        "referents": [lane.ids["A"]],
        "uncertainty": [],
        "qualifications": {"different": "meaning"},
    }
    request = lane.selection.model_copy(
        update={
            field: changes[field],
            "expected_parent_revision_id": head.head_revision_id,
        }
    )
    with pytest.raises(service.StatementError, match="different reviewed meaning") as e:
        service.prepare(request, GM)
    assert e.value.code == "statement_semantic_conflict"
    assert lane.repo.get_head(lane.world.world_id) == head


def test_recover_after_descendant_before_current_head_and_actor_is_not_identity(
    lane, monkeypatch
):
    prepared, result = commit(lane)
    advance(lane)
    head = lane.repo.get_head(lane.world.world_id)
    monkeypatch.setattr(
        service,
        "_head_matches",
        lambda *_: pytest.fail("recovery consulted current head"),
    )
    assert service.confirm(prepared, GM)["result"] == result["result"]
    other = service.prepare(lane.selection, replace(GM, subject="another-gm"))
    assert other["recovered"] and other["result"] == result["result"]
    with pytest.raises(service.StatementError, match="authentication"):
        service.confirm(prepared, replace(GM, subject="another-gm"))
    assert lane.repo.get_head(lane.world.world_id) == head


@pytest.mark.parametrize(
    "changes",
    [
        {"source_sha256": "0" * 64},
        {"clause_sha256": "0" * 64},
        {"end_byte": 9999},
        {"referents": ["ent:missing"]},
        {"evidence_ref_id": "ev:missing"},
    ],
)
def test_invalid_source_or_endpoint_never_publishes(lane, changes):
    head = lane.repo.get_head(lane.world.world_id)
    with pytest.raises(ValueError):
        service.prepare(lane.selection.model_copy(update=changes), GM)
    assert lane.repo.get_head(lane.world.world_id) == head


def test_lost_acknowledgment_retries_original_receipt_no_second_publication(
    lane, monkeypatch
):
    prepared = packet(lane)
    original_publish = lane.repo.publish_prospective_publication
    calls = []

    def lost(*args, **kwargs):
        calls.append(1)
        original_publish(*args, **kwargs)
        raise TimeoutError("lost acknowledgment")

    monkeypatch.setattr(lane.repo, "publish_prospective_publication", lost)
    result = service.confirm(prepared, GM)
    advance(lane)
    assert service.confirm(prepared, GM)["result"] == result["result"]
    assert len(calls) == 1


@pytest.mark.parametrize(
    "bad",
    ["missing_summary", "malformed_summary", "hidden_reporter", "partial_native_read"],
)
def test_incomplete_discovered_bundle_is_partial_not_flattened(lane, monkeypatch, bad):
    _, result = commit(lane)
    original = service.EntityReadService.get_complete_entity
    statement_id = result["result"]["bundle"]["statement_id"]

    def incomplete(self, context, entity_id):
        value = original(self, context, entity_id)
        if entity_id == statement_id:
            assertions = value.assertions
            if bad == "missing_summary":
                assertions = tuple(
                    a for a in assertions if a.predicate != "dnd5e:summary"
                )
            if bad == "hidden_reporter":
                assertions = tuple(
                    a for a in assertions if a.predicate != mapping.REPORTED_BY
                )
            if bad == "malformed_summary":
                assertions = tuple(
                    replace(a, value=replace(a.value, value="{}"))
                    if a.predicate == "dnd5e:summary"
                    else a
                    for a in assertions
                )
            value = replace(value, assertions=assertions)
            if bad == "partial_native_read":
                value = replace(value, completeness=SimpleNamespace(status="partial"))
        return value

    monkeypatch.setattr(service.EntityReadService, "get_complete_entity", incomplete)
    output = read(lane, result["result"]["receipt"]["published_revision_id"])
    assert output["status"] == "partial" and not output["statements"]
    assert output["gap_codes"] == ["statement_bundle_unavailable"]


def test_authenticated_routes_and_strict_selection(lane):
    from apps.live_control_server.routes.source_statements import router
    from apps.live_control_server.services.agent_graph_auth import (
        native_graph_gm_dependency,
        authenticate_native_graph_principal,
    )

    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[native_graph_gm_dependency] = lambda: GM
    app.dependency_overrides[authenticate_native_graph_principal] = lambda: GM
    with TestClient(app) as client:
        bad = lane.selection.model_dump()
        bad["embedded_content_factive"] = True
        assert (
            client.post("/api/live/source-statements/prepare", json=bad).status_code
            == 422
        )
        staged = client.post(
            "/api/live/source-statements/prepare", json=lane.selection.model_dump()
        )
        assert staged.status_code == 200, staged.text
        body = {k: staged.json()[k] for k in ("envelope", "prepared", "token")}
        delivered = client.post("/api/live/source-statements/confirm", json=body)
        assert delivered.status_code == 200, delivered.text
        revision = delivered.json()["result"]["receipt"]["published_revision_id"]
        response = client.get(
            f"/api/live/source-statements/{lane.world.world_id}/subjects/{lane.ids['B']}",
            params={"campaign_id": "c1", "revision_id": revision},
        )
        assert response.status_code == 200 and response.json()["status"] == "complete"


def test_concurrent_preparations_share_original_publication(lane):
    first = packet(lane)
    second = packet(lane)
    one = service.confirm(first, GM)
    two = service.confirm(second, GM)
    assert one["result"] == two["result"] and two["recovered"]


def test_unknown_outcome_retains_original_packet_and_recovers(lane, monkeypatch):
    from worldkeeper.application.commit import CommittedChangeOutcomeUnknown

    prepared = packet(lane)
    publish = lane.repo.publish_prospective_publication
    lookup = lane.repo.get_prospective_publication
    state = {"written": False, "calls": 0}

    def interrupted(*args, **kwargs):
        state["calls"] += 1
        publish(*args, **kwargs)
        state["written"] = True
        raise TimeoutError("ack lost")

    def unavailable(*args, **kwargs):
        if state["written"]:
            raise TimeoutError("receipt temporarily unavailable")
        return lookup(*args, **kwargs)

    monkeypatch.setattr(lane.repo, "publish_prospective_publication", interrupted)
    monkeypatch.setattr(lane.repo, "get_prospective_publication", unavailable)
    with pytest.raises(CommittedChangeOutcomeUnknown):
        service.confirm(prepared, GM)
    monkeypatch.setattr(lane.repo, "get_prospective_publication", lookup)
    advance(lane)
    assert service.confirm(prepared, GM)["recovered"]
    assert state["calls"] == 1


def test_actual_native_missing_payload_is_partial(lane):
    # Actual native read: a new visible about edge points to an entity whose
    # summary was not published. Native read completeness must not become
    # qualified bundle completeness.
    domain = dungeonbuddy_world_domain_contract()
    profile = dungeonbuddy_dnd5e_custom_predicate_profile()
    runtime = transport.runtime(
        lane.repo, domain, profile, now=NOW, operation_id="incomplete-native-bundle"
    )
    change = wk.WorldChangeIntent(
        lane.world.world_id,
        "independent-fixture",
        (
            wk.CreateObject("incomplete", ()),
            wk.CreateRelationship(
                "index",
                wk.ResultOf("incomplete"),
                mapping.ABOUT,
                wk.DurableObjectRef(lane.ids["B"]),
                lane.meta,
            ),
        ),
    )
    result = runtime.commit_prepared_change(
        runtime.prepare_change(change), confirmed_by=GM.subject
    )
    output = read(lane, result.child_revision_id)
    assert output["status"] == "partial" and output["statements"] == []
    assert output["universal_absence_claimed"] is False


def test_tampered_prepared_packet_or_player_cannot_publish(lane):
    prepared = packet(lane)
    head = lane.repo.get_head(lane.world.world_id)
    tampered = deepcopy(prepared.prepared)
    tampered["value"]["fields"]["producer"] = "attacker"
    with pytest.raises(service.StatementError):
        service.confirm(prepared.model_copy(update={"prepared": tampered}), GM)
    from fastapi import HTTPException

    with pytest.raises(HTTPException):
        service.prepare(lane.selection, replace(GM, role="player"))
    assert lane.repo.get_head(lane.world.world_id) == head


def test_reviewed_source_byte_order_preserved_without_fictional_chronology(lane):
    first = BODY.splitlines(keepends=True)[0].encode()
    second = BODY.encode()[len(first) :]
    order = {
        "before_start": 0,
        "before_end": len(first),
        "before_sha256": hashlib.sha256(first).hexdigest(),
        "after_start": len(first),
        "after_end": len(BODY.encode()),
        "after_sha256": hashlib.sha256(second).hexdigest(),
    }
    request = StatementSelection.model_validate(
        {**lane.selection.model_dump(), "source_order": [order]}
    )
    staged = service.prepare(request, GM)
    result = service.confirm(
        ConfirmStatement(**{k: staged[k] for k in ("envelope", "prepared", "token")}),
        GM,
    )
    assert result["result"]["bundle"]["payload"]["source_order"] == [order]
    assert result["result"]["bundle"]["payload"]["embedded_content_factive"] is False
    for changed in (
        {
            **order,
            "before_start": len(first),
            "before_end": len(BODY.encode()),
            "after_start": 0,
            "after_end": len(first),
        },
    ):
        with pytest.raises(ValueError):
            StatementSelection.model_validate(
                {**request.model_dump(), "source_order": [changed]}
            )
    with pytest.raises(ValueError):
        StatementSelection.model_validate(
            {**request.model_dump(), "source_order": [order, order]}
        )
    with pytest.raises(ValueError):
        service.prepare(
            StatementSelection.model_validate(
                {
                    **request.model_dump(),
                    "source_order": [{**order, "after_sha256": "0" * 64}],
                }
            ),
            GM,
        )


@pytest.mark.parametrize("hidden_component", ["summary", "reporter"])
def test_actual_cross_scope_dependency_is_partial(lane, hidden_component):
    _, access, domain, profile = service._context(
        lane.repo, lane.world.world_id, lane.selection.expected_parent_revision_id, "c1"
    )
    payload = service._payload(lane.selection, lane.repo, lane.world.world_id, access)
    change = mapping.intent(
        lane.world.world_id, payload, lane.selection.evidence_ref_id
    )
    operations = list(change.operations)
    c2 = replace(lane.meta, scope=(wk.ScopeBinding(CAMPAIGN_SCOPE_AXIS, "c2"),))
    if hidden_component == "summary":
        operations[0] = replace(
            operations[0], facts=(replace(operations[0].facts[0], metadata=c2),)
        )
    else:
        operations[-1] = replace(operations[-1], metadata=c2)
    runtime = transport.runtime(
        lane.repo,
        domain,
        profile,
        now=NOW,
        operation_id="mixed-scope-" + hidden_component,
    )
    result = runtime.commit_prepared_change(
        runtime.prepare_change(replace(change, operations=tuple(operations))),
        confirmed_by=GM.subject,
    )
    output = read(lane, result.child_revision_id)
    assert output["status"] == "partial" and output["statements"] == []
