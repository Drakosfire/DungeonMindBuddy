"""Actual pinned Core/WK and authenticated routes, never a full-ingestion score."""

import hashlib
import os
from copy import deepcopy
from dataclasses import replace
from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest
from dungeonmind.application.vnext import initialize_empty_knowledge_space
from dungeonmind.contracts.vnext.knowledge import PublishKnowledgeRevisionCommand
from dungeonmind.infrastructure.memory.vnext_sources import (
    InMemoryNativeSourceEvidenceRepository,
)
from fastapi import FastAPI
from fastapi.testclient import TestClient
from worldkeeper.application import contracts as wk

from apps.live_control_server.integrations.worldkeeper import (
    registry_standing_consumer as transport,
)
from apps.live_control_server.integrations.worldkeeper import (
    source_statements as mapping,
)
from apps.live_control_server.models.source_statements import (
    ConfirmStatement,
    StatementSelection,
)
from apps.live_control_server.services import source_statements as service
from apps.live_control_server.services.agent_graph_auth import NativeGraphPrincipal
from graph_memory.vnext.domain_runtime import (
    CAMPAIGN_SCOPE_AXIS,
    GM_LABEL,
    dungeonbuddy_dnd5e_custom_predicate_profile,
    dungeonbuddy_world_domain_contract,
)
from tests.test_demo_j1_native_world_source_admission import (
    _admit,
    _committed_source,
)
from tests.test_demo_j1_native_world_source_admission import (
    native as sources,
)

NOW = datetime(2026, 10, 29, tzinfo=UTC)
GM = NativeGraphPrincipal("operator", "gm", "local_operator")
BODY = "A reports that B fled; uncertain.\nAnother source-local episode.\n"


@pytest.fixture
def lane(application_state_dsn, tmp_path, monkeypatch):
    return make_lane(tmp_path, monkeypatch)


def make_lane(tmp_path, monkeypatch, *, repo=None, narrow=False, multiple=False):
    monkeypatch.setenv("DMB_GRAPH_REVIEW_PREPARE_BINDING_KEY", "statement-tests")
    repo = repo if repo is not None else InMemoryNativeSourceEvidenceRepository()
    monkeypatch.setattr(sources, "_repository", lambda: repo)
    from apps.live_control_server.services.world_container_registry import (
        create_world_container,
    )
    world = create_world_container(tmp_path, name="Statement fixture " + uuid4().hex)
    world, record = _committed_source(tmp_path, markdown=BODY, world=world)
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
    if narrow or multiple:
        from dungeonmind.application.vnext import publish_native_text_source_evidence
        from dungeonmind.contracts.vnext.native_source import (
            NativeTextSourceAdmissionV1,
        )
        size = len(BODY.splitlines(keepends=True)[0].encode())
        spans = [{"client_ref": "first", "evidence_role": "support", "start_byte": 0,
                  "end_byte": size, "expected_slice_sha256": hashlib.sha256(BODY.encode()[:size]).hexdigest()}]
        if multiple:
            spans.append({"client_ref": "second", "evidence_role": "support", "start_byte": size,
                          "end_byte": len(BODY.encode()), "expected_slice_sha256": hashlib.sha256(BODY.encode()[size:]).hexdigest()})
        root = publish_native_text_source_evidence(
            repository=repo, domain_contract=domain, semantic_profile=profile,
            request=NativeTextSourceAdmissionV1(
                space_id=world.world_id, admission_id="source:narrow",
                expected_parent_revision_id=repo.get_head(world.world_id).head_revision_id,
                created_at=NOW, body_text=BODY,
                expected_body_sha256=hashlib.sha256(BODY.encode()).hexdigest(),
                source_classification="dungeonbuddy.source:worldbuilding",
                authority="primary", visibility={"kind": "labels_any", "labels": [GM_LABEL]},
                origin={"namespace": "test.document", "object_id": record.document_id, "revision_id": "1"},
                spans=spans,
            ),
        )
        source = SimpleNamespace(admission_id=root.admission_id, evidence_ref_id=root.bindings[0].evidence_ref_id)
    else:
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
        authenticate_native_graph_principal,
        native_graph_gm_dependency,
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


@pytest.fixture
def extension_lane(tmp_path, monkeypatch, request):
    repo = None
    if getattr(request, "param", "memory") == "postgres":
        from urllib.parse import urlsplit

        from dungeonmind.infrastructure.postgres import (
            PostgresDatabase,
            PostgresNativeSourceEvidenceRepository,
        )
        dsn = os.environ.get("DMB_NATIVE_SOURCE_EXTENSION_TEST_DATABASE_URL")
        if not dsn:
            pytest.skip("requires an owned disposable migrated native PostgreSQL database")
        assert urlsplit(dsn).path.removeprefix("/").startswith("test_native_extension_")
        repo = PostgresNativeSourceEvidenceRepository(PostgresDatabase(dsn))
    return make_lane(tmp_path, monkeypatch, repo=repo, narrow=True)


def extension_request(lane):
    from apps.live_control_server.models.source_statements import ExtendSourceEvidence

    root = lane.repo.get_native_source_admission_receipt(lane.world.world_id, lane.selection.source_admission_id)
    start = len(BODY.splitlines(keepends=True)[0].encode())
    return ExtendSourceEvidence(
        managed_world_id=lane.world.world_id, extension_id="extension:second-clause",
        original_admission_id=root.admission_id,
        source_artifact_id=root.source_artifact_id, source_revision_id=root.source_revision_id,
        expected_body_sha256=lane.selection.source_sha256,
        expected_parent_revision_id=lane.repo.get_head(lane.world.world_id).head_revision_id,
        expected_source_authority_epoch=lane.repo.open_native_source_view(lane.world.world_id).epoch,
        created_at=NOW.isoformat(),
        spans=[{"client_ref": "second", "evidence_role": "support", "start_byte": start,
                "end_byte": len(BODY.encode()),
                "expected_slice_sha256": hashlib.sha256(BODY.encode()[start:]).hexdigest()}],
    )


def extension_selection(lane, receipt):
    from apps.live_control_server.models.source_statements import StatementSelection

    start = len(BODY.splitlines(keepends=True)[0].encode())
    data = lane.selection.model_dump()
    data.update(source_admission_id=None, source_evidence_extension_id=receipt["extension_id"],
                evidence_ref_id=receipt["bindings"][0]["evidence_ref_id"],
                expected_parent_revision_id=receipt["publication_receipt"]["published_revision_id"],
                start_byte=start, end_byte=len(BODY.encode()),
                clause_sha256=hashlib.sha256(BODY.encode()[start:]).hexdigest(),
                meaning="Another source-local episode", mode="narrator", reporter=None,
                episode="episode-2", uncertainty=[], qualifications={"source_local": "only the second clause"})
    return StatementSelection(**data)


def exercise_extension(lane):
    request = extension_request(lane)
    root_before = lane.repo.get_native_source_admission_receipt(lane.world.world_id, request.original_admission_id)
    # A readable retained body does not authorize a clause outside the original span.
    data = lane.selection.model_dump()
    data.update(start_byte=request.spans[0].start_byte, end_byte=request.spans[0].end_byte,
                clause_sha256=request.spans[0].expected_slice_sha256)
    with pytest.raises(service.StatementError) as refused:
        service.prepare(StatementSelection(**data), GM)
    assert refused.value.code == "statement_span_invalid"
    original_prepared = packet(lane)
    receipt = service.extend_source_evidence(request, GM)["receipt"]
    lane.selection = extension_selection(lane, receipt)
    prepared, result = commit(lane)
    final = read(lane, result["result"]["receipt"]["published_revision_id"])
    assert final["status"] == "complete" and len(final["statements"]) == 1
    assert final["statements"][0]["payload"] == prepared.envelope["payload"]
    assert final["statements"][0]["payload"]["proof"] == {
        "source_evidence_extension_id": request.extension_id,
        "evidence_ref_id": receipt["bindings"][0]["evidence_ref_id"],
    }
    advance(lane)
    head = lane.repo.get_head(lane.world.world_id)
    assert service.extend_source_evidence(request, GM)["receipt"] == receipt
    assert service.confirm(prepared, GM)["recovered"]
    assert service.prepare(lane.selection, GM)["recovered"]
    assert lane.repo.get_head(lane.world.world_id) == head
    assert lane.repo.get_native_source_admission_receipt(lane.world.world_id, request.original_admission_id) == root_before
    assert original_prepared.envelope["payload"]["proof"]["source_admission_id"] == root_before.admission_id
    return request, receipt, prepared


def test_extension_delivers_second_clause_and_recovers_after_descendants(extension_lane):
    exercise_extension(extension_lane)


@pytest.mark.parametrize("change", ["both", "neither", "unknown"])
def test_explicit_proof_choice_is_closed(lane, change):
    from pydantic import ValidationError

    data = lane.selection.model_dump(exclude_none=True)
    if change == "both":
        data["source_evidence_extension_id"] = "extension:wrong"
    elif change == "neither":
        del data["source_admission_id"]
    else:
        data["source_proof_alias"] = "anything"
    with pytest.raises(ValidationError):
        StatementSelection(**data)


@pytest.mark.parametrize("change", ["root", "publication", "membership", "source", "origin", "body", "outside", "slice", "original-id-alias"])
def test_extension_proof_tamper_refuses_before_publication(extension_lane, monkeypatch, change):
    lane = extension_lane
    request = extension_request(lane)
    receipt = service.extend_source_evidence(request, GM)["receipt"]
    lane.selection = extension_selection(lane, receipt)
    head = lane.repo.get_head(lane.world.world_id)
    if change in {"root", "publication", "membership", "source", "origin"}:
        original = lane.repo.get_native_source_evidence_extension_receipt
        def tampered(*args):
            value = original(*args)
            if value is None:
                return value
            update = {
                "root": {"original_admission_sha256": "0" * 64},
                "publication": {"publication_receipt": value.publication_receipt.model_copy(update={"publication_id": "wrong"})},
                "membership": {"bindings": []},
                "source": {"source_revision_id": "wrong"},
                "origin": {"origin": None},
            }[change]
            return value.model_copy(update=update)
        monkeypatch.setattr(lane.repo, "get_native_source_evidence_extension_receipt", tampered)
    else:
        changes = {
            "body": {"source_sha256": "0" * 64},
            "outside": {"start_byte": 0},
            "slice": {"clause_sha256": "0" * 64},
            "original-id-alias": {"source_admission_id": request.extension_id, "source_evidence_extension_id": None},
        }[change]
        lane.selection = lane.selection.model_copy(update=changes)
    with pytest.raises(service.StatementError):
        service.prepare(lane.selection, GM)
    assert lane.repo.get_head(lane.world.world_id) == head


def extension_client(principal=GM):
    from apps.live_control_server.routes.source_statements import router
    from apps.live_control_server.services.agent_graph_auth import (
        authenticate_native_graph_principal,
    )
    app = FastAPI()
    app.include_router(router)
    if principal is not None:
        app.dependency_overrides[authenticate_native_graph_principal] = lambda: principal
    return TestClient(app, client=("127.0.0.1", 50000))


def test_http_extension_prepare_confirm_read_and_replay(extension_lane):
    lane = extension_lane
    request = extension_request(lane)
    with extension_client() as client:
        url = "/api/live/source-statements/extend-evidence"
        reply = client.post(url, json=request.model_dump())
        assert reply.status_code == 200, reply.text
        receipt = reply.json()["receipt"]
        lane.selection = extension_selection(lane, receipt)
        staged = client.post("/api/live/source-statements/prepare", json=lane.selection.model_dump(exclude_none=True))
        assert staged.status_code == 200, staged.text
        body = {k: staged.json()[k] for k in ("envelope", "prepared", "token")}
        delivered = client.post("/api/live/source-statements/confirm", json=body)
        assert delivered.status_code == 200, delivered.text
        revision = delivered.json()["result"]["receipt"]["published_revision_id"]
        opened = client.get(f"/api/live/source-statements/{lane.world.world_id}/subjects/{lane.ids['B']}",
                            params={"revision_id": revision, "campaign_id": "c1"})
        assert opened.status_code == 200 and opened.json()["status"] == "complete"
        advance(lane)
        assert client.post(url, json=request.model_dump()).json()["receipt"] == receipt
        conflict = request.model_dump()
        conflict["spans"][0]["client_ref"] = "changed-intent"
        response = client.post(url, json=conflict)
        assert response.status_code == 409
        assert response.json()["detail"]["code"] == "knowledge_publication_idempotency_conflict"


@pytest.mark.parametrize("role", ["anonymous", "player", "wrong-world"])
def test_http_extension_authority_refusal_before_core_io(extension_lane, monkeypatch, role):
    from fastapi import HTTPException
    lane = extension_lane
    request = extension_request(lane)
    monkeypatch.setenv("DMB_AGENT_GRAPH_AUTH_MODE", "local_operator")
    monkeypatch.setenv("DMB_AGENT_GRAPH_AUTH_ENVIRONMENT", "local")
    monkeypatch.setenv("DMB_AGENT_GRAPH_LOCAL_OPERATOR_TOKEN", "x" * 40)
    monkeypatch.setattr(service.native, "repository", lambda: pytest.fail("unauthorized Core I/O"))
    if role == "wrong-world":
        def refused(_):
            raise HTTPException(404, "managed World has no native binding")
        monkeypatch.setattr(service.native, "binding", refused)
    principal = None if role == "anonymous" else replace(GM, role="player") if role == "player" else GM
    with extension_client(principal) as client:
        response = client.post("/api/live/source-statements/extend-evidence", json=request.model_dump())
        assert response.status_code == {"anonymous": 401, "player": 403, "wrong-world": 404}[role]


def test_http_extension_unknown_outcome_preserves_exact_recovery_key(extension_lane, monkeypatch):
    from dungeonmind.application.vnext.errors import (
        KnowledgePublicationOutcomeUnknownError,
    )
    lane = extension_lane
    request = extension_request(lane)
    publish = service.publish_native_source_evidence_extension
    def lost(**kwargs):
        result = publish(**kwargs)
        raise KnowledgePublicationOutcomeUnknownError(
            space_id=result.space_id, publication_id=result.extension_id,
            expected_published_revision_id=result.publication_receipt.published_revision_id,
            reason="synthetic lost acknowledgement",
        )
    monkeypatch.setattr(service, "publish_native_source_evidence_extension", lost)
    with extension_client() as client:
        failed = client.post("/api/live/source-statements/extend-evidence", json=request.model_dump())
        assert failed.status_code == 409
        assert failed.json()["detail"]["retry_original_packet"] is True
        assert failed.json()["detail"]["recovery"]["action"] == "retry_exact_request"
        assert failed.json()["detail"]["recovery"]["publication_id"] == request.extension_id
        monkeypatch.setattr(service, "publish_native_source_evidence_extension", publish)
        recovered = client.post("/api/live/source-statements/extend-evidence", json=request.model_dump())
        assert recovered.status_code == 200
        assert recovered.json()["receipt"]["extension_id"] == request.extension_id


@pytest.mark.skipif(
    not os.environ.get("DMB_NATIVE_SOURCE_EXTENSION_TEST_DATABASE_URL"),
    reason="requires an owned disposable migrated native PostgreSQL database",
)
def test_postgres_extension_http_wk_statement_reopen_and_recovery(
    tmp_path, monkeypatch, application_state_dsn,
):
    from urllib.parse import urlsplit

    from dungeonmind.infrastructure.postgres import (
        PostgresDatabase,
        PostgresNativeSourceEvidenceRepository,
    )

    dsn = os.environ["DMB_NATIVE_SOURCE_EXTENSION_TEST_DATABASE_URL"]
    assert urlsplit(dsn).path.removeprefix("/").startswith("test_native_extension_")
    database = PostgresDatabase(dsn)
    repo = PostgresNativeSourceEvidenceRepository(database)
    lane = make_lane(tmp_path, monkeypatch, repo=repo, narrow=True)
    test_http_extension_prepare_confirm_read_and_replay(lane)
    reopened = PostgresNativeSourceEvidenceRepository(database)
    monkeypatch.setattr(service.native, "repository", lambda: reopened)
    lane.repo = reopened
    head = repo.get_head(lane.world.world_id)
    output = read(lane, head.head_revision_id)
    assert output["status"] == "complete" and len(output["statements"]) == 1
    staged = service.prepare(lane.selection, GM)
    assert staged["recovered"]
    assert reopened.get_head(lane.world.world_id) == head


@pytest.mark.parametrize("change", ["both", "neither", "body", "authority"])
def test_http_closed_requests_refuse_before_repository(extension_lane, monkeypatch, change):
    lane = extension_lane
    if change in {"both", "neither"}:
        body = lane.selection.model_dump(exclude_none=True)
        if change == "both":
            body["source_evidence_extension_id"] = "extension:wrong"
        else:
            del body["source_admission_id"]
        url = "/api/live/source-statements/prepare"
    else:
        body = extension_request(lane).model_dump()
        body["body_text" if change == "body" else "authority"] = "untrusted"
        url = "/api/live/source-statements/extend-evidence"
    monkeypatch.setattr(service.native, "repository", lambda: pytest.fail("invalid request reached Core"))
    with extension_client() as client:
        assert client.post(url, json=body).status_code == 422


def test_extension_selected_clause_must_not_split_utf8(tmp_path, monkeypatch):
    import sys
    monkeypatch.setattr(sys.modules[__name__], "BODY", "A reports that B fled; uncertain.\nÉpisode local.\n")
    lane = make_lane(tmp_path, monkeypatch, narrow=True)
    request = extension_request(lane)
    receipt = service.extend_source_evidence(request, GM)["receipt"]
    selection = extension_selection(lane, receipt)
    selection = selection.model_copy(update={"end_byte": selection.start_byte + 1})
    head = lane.repo.get_head(lane.world.world_id)
    with pytest.raises(service.StatementError, match="splits UTF8"):
        service.prepare(selection, GM)
    assert lane.repo.get_head(lane.world.world_id) == head


def test_original_signed_statement_recovers_unchanged_after_extension(extension_lane):
    lane = extension_lane
    prepared, result = commit(lane)
    original_payload = deepcopy(prepared.envelope["payload"])
    service.extend_source_evidence(extension_request(lane), GM)
    head = lane.repo.get_head(lane.world.world_id)
    assert service.confirm(prepared, GM)["result"] == result["result"]
    assert service.prepare(lane.selection, GM)["result"] == result["result"]
    assert prepared.envelope["payload"] == original_payload
    assert lane.repo.get_head(lane.world.world_id) == head

pytestmark = pytest.mark.usefixtures("application_state_dsn")
