"""Ordinary proposal routes, real disposable APP and actual Core/WK fixtures."""

import json
from copy import deepcopy
from dataclasses import replace
from uuid import uuid4
import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from tests.test_source_statements import lane as lane, GM, BODY, advance
from tests.application_state.conftest import (
    application_state_dsn as application_state_dsn,
)
from apps.live_control_server.models.source_statement_proposals import ProposalRequest
from apps.live_control_server.services import source_statement_proposals as service
from apps.live_control_server.services import source_statements

BATCH = {
    "contract": "qualified_source_handles_v2",
    "catalog_sha256": "TEST_CATALOG",
    "mentions": [
        {"mention_id": "a", "label": "A", "source_unit_ids": ["u1"]},
        {"mention_id": "b", "label": "B", "source_unit_ids": ["u1"]},
    ],
    "proposals": [
        {
            "proposal_id": "p1",
            "source_unit_ids": ["u1"],
            "context_unit_ids": [],
            "meaning": "B fled",
            "mode": "reported",
            "reporter_mention": "a",
            "referent_mentions": ["b"],
            "uncertainty": ["uncertain"],
            "qualifications": {"source_local": "report only"},
            "episode": "episode-1",
            "unresolved": ["native identities need review"],
        }
    ],
    "dispositions": [
        {
            "unit_id": "u1",
            "status": "proposed",
            "proposal_ids": ["p1"],
            "reason": "report",
        }
    ],
    "limitations": ["Extraction coverage is not established"],
}


def sent_body(packet):
    return "".join(unit["text"] for unit in packet["source_catalog"]["units"])


class Wire:
    def __init__(self, raw=None, failure=False, *, incomplete=False, output_tokens=100):
        self.requests = []
        self.raw = json.dumps(BATCH) if raw is None else raw
        outer = self

        class Transport(httpx.AsyncBaseTransport):
            async def handle_async_request(self, request):
                outer.requests.append(json.loads(request.content))
                if "TEST_CATALOG" in outer.raw:
                    packet = json.loads(outer.requests[-1]["input"][0]["content"])
                    outer.raw = outer.raw.replace(
                        "TEST_CATALOG", packet["source_catalog"]["catalog_sha256"]
                    )
                if failure:
                    raise httpx.ReadTimeout("synthetic unknown", request=request)
                return httpx.Response(
                    200,
                    request=request,
                    json={
                        "id": "resp_proposal",
                        "object": "response",
                        "created_at": 1,
                        "status": "incomplete" if incomplete else "completed",
                        "model": "gpt-6-luna",
                        "incomplete_details": {"reason": "max_output_tokens"}
                        if incomplete
                        else None,
                        "output": [
                            {
                                "type": "message",
                                "id": "msg_proposal",
                                "role": "assistant",
                                "status": "completed",
                                "content": [
                                    {
                                        "type": "output_text",
                                        "text": outer.raw,
                                        "annotations": [],
                                    }
                                ],
                            }
                        ],
                        "usage": {
                            "input_tokens": 200,
                            "output_tokens": output_tokens,
                            "total_tokens": 200 + output_tokens,
                        },
                    },
                )

            async def aclose(self):
                pass

        self.transport = Transport()


def request_for(lane):
    s = lane.selection
    return ProposalRequest(
        operation_id=uuid4(),
        managed_world_id=s.managed_world_id,
        campaign_id=s.campaign_id,
        read_revision_id=s.expected_parent_revision_id,
        source_admission_id=s.source_admission_id,
        evidence_ref_id=s.evidence_ref_id,
        source_sha256=s.source_sha256,
    )


def client(monkeypatch, wire):
    from apps.live_control_server.routes import source_statements as routes
    from apps.live_control_server.services.agent_graph_auth import (
        native_graph_gm_dependency,
    )

    monkeypatch.setenv("OPENAI_API_KEY", "synthetic-not-a-provider-key")
    original = service.produce

    async def produce(request, principal):
        return await original(request, principal, transport=wire.transport)

    monkeypatch.setattr(service, "produce", produce)
    app = FastAPI()
    app.include_router(routes.router)
    app.dependency_overrides[native_graph_gm_dependency] = lambda: GM
    return TestClient(app)


def produce(c, lane):
    req = request_for(lane)
    response = c.post(
        "/api/live/source-statements/proposals", json=req.model_dump(mode="json")
    )
    assert response.status_code == 200, response.text
    return req, response.json()


def url(req):
    return f"/api/live/source-statements/proposals/{req.operation_id}?managed_world_id={req.managed_world_id}"


def review_body(lane, record):
    return {
        "decision_id": str(uuid4()),
        "expected_revision": record["revision"],
        "proposal_id": "p1",
        "selection": lane.selection.model_dump(mode="json"),
    }


def review_url(req):
    return f"/api/live/source-statements/proposals/{req.operation_id}/review?managed_world_id={req.managed_world_id}"


def test_routes_produce_reload_review_publish_and_replay(
    lane, application_state_dsn, monkeypatch
):
    wire = Wire()
    with client(monkeypatch, wire) as c:
        req, record = produce(c, lane)
        assert record["state"] == "completed", record
        assert len(wire.requests) == 1
        assert [e["outcome"] for e in record["lifecycle"]] == [
            "sending",
            "response_received",
        ]
        assert record["raw_output"] == wire.raw
        assert json.loads(record["wire"]) == wire.requests[0]
        sent = json.loads(wire.requests[0]["input"][0]["content"])
        assert sent_body(sent) == BODY
        assert {
            row["entity"]["entity_id"]
            for row in sent["world_identity_context"]["entities"]
        } == set(lane.ids.values())
        assert sent["authority"]["binding"]["native_world_id"] == req.managed_world_id
        assert c.get(url(req)).json() == record
        assert (
            c.post(
                "/api/live/source-statements/proposals",
                json=req.model_dump(mode="json"),
            ).json()
            == record
        )
        assert len(wire.requests) == 1
        body = review_body(lane, record)
        reviewed = c.post(review_url(req), json=body)
        assert reviewed.status_code == 200, reviewed.text
        decision = reviewed.json()
        packet = decision["prepared_packet"]
        from apps.live_control_server.models.source_statements import ConfirmStatement

        published = source_statements.confirm(
            ConfirmStatement(
                **{k: packet[k] for k in ("envelope", "prepared", "token")}
            ),
            GM,
        )
        advance(lane)
        # Lost review acknowledgment returns exact packet after a native descendant.
        assert c.post(review_url(req), json=body).json() == decision
        read = source_statements.read_subject(
            managed_world_id=req.managed_world_id,
            campaign_id="c1",
            revision_id=published["result"]["receipt"]["published_revision_id"],
            entity_id=lane.ids["B"],
            principal=GM,
        )
        assert len(read["statements"]) == 1
        assert read["statements"][0]["payload"]["embedded_content_factive"] is False
        body["selection"]["meaning"] = "different interpretation"
        assert c.post(review_url(req), json=body).status_code == 409


@pytest.mark.parametrize(
    "raw",
    [
        "not JSON",
        '{"mentions":[],"mentions":[],"proposals":[],"limitations":[]}',
        json.dumps(
            {
                **BATCH,
                "proposals": [
                    {**BATCH["proposals"][0], "source_unit_ids": ["unknown"]}
                ],
            }
        ),
    ],
)
def test_original_bad_output_preserved_no_redispatch(
    lane, application_state_dsn, monkeypatch, raw
):
    wire = Wire(raw)
    with client(monkeypatch, wire) as c:
        req, record = produce(c, lane)
        assert record["state"] == "failed"
        assert record["raw_output"] == wire.raw
        assert (
            c.post(
                "/api/live/source-statements/proposals",
                json=req.model_dump(mode="json"),
            ).json()
            == record
        )
        assert len(wire.requests) == 1
        assert (
            c.post(review_url(req), json=review_body(lane, record)).status_code == 409
        )


def test_unknown_io_remains_nonretryable(lane, application_state_dsn, monkeypatch):
    wire = Wire(failure=True)
    with client(monkeypatch, wire) as c:
        req, record = produce(c, lane)
        assert record["state"] == "failed"
        assert "after_entry" in record["failure"]
        assert (
            c.post(
                "/api/live/source-statements/proposals",
                json=req.model_dump(mode="json"),
            ).json()
            == record
        )
        assert len(wire.requests) == 1


@pytest.mark.parametrize(
    "field,value",
    [
        ("campaign_id", "different"),
        ("source_sha256", "0" * 64),
        ("source_admission_id", "missing"),
    ],
)
def test_review_cannot_change_scope_or_source(
    lane, application_state_dsn, monkeypatch, field, value
):
    with client(monkeypatch, Wire()) as c:
        req, record = produce(c, lane)
        body = review_body(lane, record)
        body["selection"][field] = value
        assert c.post(review_url(req), json=body).status_code == 409


def test_stale_parent_and_explicit_descendant(lane, application_state_dsn, monkeypatch):
    with client(monkeypatch, Wire()) as c:
        req, record = produce(c, lane)
        child = advance(lane)
        body = review_body(lane, record)
        assert c.post(review_url(req), json=body).status_code == 409
        body["selection"]["expected_parent_revision_id"] = child.revision.revision_id
        response = c.post(review_url(req), json=body)
        assert response.status_code == 200, response.text


def test_owner_source_and_operation_conflicts(lane, application_state_dsn, monkeypatch):
    with client(monkeypatch, Wire()) as c:
        req, record = produce(c, lane)
        with pytest.raises(Exception, match="owner/World"):
            service.get(
                req.operation_id, req.managed_world_id, replace(GM, subject="other")
            )
        assert (
            c.get(url(req).replace(req.managed_world_id, "foreign")).status_code == 409
        )
        changed = req.model_dump(mode="json") | {"campaign_id": "other"}
        assert (
            c.post("/api/live/source-statements/proposals", json=changed).status_code
            == 409
        )
        bad = request_for(lane).model_dump(mode="json") | {"source_sha256": "0" * 64}
        assert (
            c.post("/api/live/source-statements/proposals", json=bad).status_code == 409
        )
        with pytest.raises(Exception):
            service.get(
                req.operation_id, req.managed_world_id, replace(GM, role="player")
            )
        assert record["reviews"] == []


def test_reviews_cas_does_not_return_losing_packet(
    lane, application_state_dsn, monkeypatch
):
    with client(monkeypatch, Wire()) as c:
        req, record = produce(c, lane)
        first = review_body(lane, record)
        assert c.post(review_url(req), json=first).status_code == 200
        assert (
            c.post(review_url(req), json=review_body(lane, record)).status_code == 409
        )
        assert len(c.get(url(req)).json()["reviews"]) == 1


def test_review_rejects_wrong_clause_digest_and_foreign_endpoint(
    lane, application_state_dsn, monkeypatch
):
    with client(monkeypatch, Wire()) as c:
        req, record = produce(c, lane)
        body = review_body(lane, record)
        body["selection"]["end_byte"] -= 1
        assert c.post(review_url(req), json=body).status_code == 409
        body = review_body(lane, record)
        body["selection"]["referents"] = ["ent:missing"]
        assert c.post(review_url(req), json=body).status_code == 409
        assert c.get(url(req)).json()["reviews"] == []


def test_real_route_requires_authentication(monkeypatch):
    from apps.live_control_server.routes.source_statements import router

    monkeypatch.delenv("DMB_AGENT_GRAPH_AUTH_MODE", raising=False)
    app = FastAPI()
    app.include_router(router)
    with TestClient(app) as c:
        response = c.get(
            f"/api/live/source-statements/proposals/{uuid4()}?managed_world_id=private"
        )
        assert response.status_code == 503


@pytest.mark.parametrize(
    "change",
    [
        {"mode": "reported", "reporter_mention": None},
        {"referent_mentions": ["unknown"]},
        {"embedded_content_factive": True},
        {"qualifications": {}},
    ],
)
def test_proposal_cannot_erase_qualifications(change):
    from graph_memory.extraction.qualified_statement_proposals import parse
    from graph_memory.extraction.statement_source_catalog import catalog

    source = catalog(BODY, {})
    batch = deepcopy(BATCH)
    batch["catalog_sha256"] = source["catalog_sha256"]
    batch["proposals"][0].update(change)
    with pytest.raises(ValueError):
        parse(json.dumps(batch), source)


def source_lane(lane, body, *, partial=True):
    """An actual new synthetic source whose registered evidence is one clause."""
    from datetime import UTC, datetime
    from hashlib import sha256
    from dungeonmind.application.vnext import publish_native_text_source_evidence
    from dungeonmind.contracts.vnext.native_source import NativeTextSourceAdmissionV1
    from types import SimpleNamespace

    repo = lane.repo
    selected = lane.selection
    _, access, domain, profile = source_statements._context(
        repo, lane.world.world_id, selected.expected_parent_revision_id, "c1"
    )
    old = repo.get_native_source_admission_receipt(
        lane.world.world_id, selected.source_admission_id
    )
    material = access.source_view.get_native_text_source(
        source_artifact_id=old.source_artifact_id,
        source_revision_id=old.source_revision_id,
        span_id=old.bindings[0].span_id,
    )
    artifact = material.source_artifact
    admission = publish_native_text_source_evidence(
        repository=repo,
        domain_contract=domain,
        semantic_profile=profile,
        request=NativeTextSourceAdmissionV1(
            space_id=lane.world.world_id,
            admission_id="synthetic-partial-span-source",
            expected_parent_revision_id=selected.expected_parent_revision_id,
            created_at=datetime(2026, 10, 29, tzinfo=UTC),
            body_text=body,
            expected_body_sha256=sha256(body.encode()).hexdigest(),
            source_classification=artifact.source_classification,
            authority=artifact.authority,
            visibility=artifact.visibility,
            domain_metadata=list(artifact.domain_metadata),
            origin={
                "namespace": "synthetic-test",
                "object_id": "partial-source",
                "revision_id": sha256(body.encode()).hexdigest(),
            },
            spans=[
                {
                    "client_ref": "first-clause",
                    "evidence_role": "support",
                    "start_byte": 0,
                    "end_byte": selected.end_byte if partial else len(body.encode()),
                    "expected_slice_sha256": selected.clause_sha256
                    if partial
                    else sha256(body.encode()).hexdigest(),
                }
            ],
        ),
    )
    changed = selected.model_copy(
        update={
            "expected_parent_revision_id": admission.published_revision_id,
            "source_admission_id": admission.admission_id,
            "source_sha256": sha256(body.encode()).hexdigest(),
            "evidence_ref_id": admission.bindings[0].evidence_ref_id,
        }
    )
    return SimpleNamespace(
        repo=repo, world=lane.world, selection=changed, ids=lane.ids, meta=lane.meta
    )


@pytest.fixture
def partial_span_lane(lane):
    return source_lane(lane, BODY)


@pytest.mark.parametrize("kind", ["context", "cross_unit", "valid_narrowing"])
def test_review_requires_one_primary_unit(
    lane, application_state_dsn, monkeypatch, kind
):
    from hashlib import sha256

    body = BODY.splitlines(keepends=True)[0] + "\nContext only.\n"
    lane = source_lane(lane, body, partial=False)
    batch = deepcopy(BATCH)
    batch["proposals"][0]["context_unit_ids"] = ["u2"]
    batch["dispositions"].append(
        {
            "unit_id": "u2",
            "status": "skipped",
            "proposal_ids": [],
            "reason": "context only",
        }
    )
    with client(monkeypatch, Wire(json.dumps(batch))) as c:
        req, row = produce(c, lane)
        assert row["state"] == "completed"
        review = review_body(lane, row)
        if kind != "valid_narrowing":
            start = (
                row["result"]["passages"]["p1"]["context"][0]["start_byte"]
                if kind == "context"
                else 0
            )
            review["selection"].update(
                start_byte=start,
                end_byte=len(body.encode()),
                clause_sha256=sha256(body.encode()[start:]).hexdigest(),
            )
        response = c.post(review_url(req), json=review)
        assert response.status_code == (200 if kind == "valid_narrowing" else 409), (
            response.text
        )
        if kind != "valid_narrowing":
            assert "one primary source unit" in response.text


def test_partial_evidence_allows_inspection_without_publication_widening(
    partial_span_lane, application_state_dsn, monkeypatch
):
    from hashlib import sha256
    from application_state.statement_proposals import service as store

    lane = partial_span_lane
    second = BODY.splitlines(keepends=True)[1]
    batch = deepcopy(BATCH)
    batch["proposals"].append(
        {
            **batch["proposals"][0],
            "proposal_id": "p2",
            "meaning": "Another episode is described",
            "mode": "narrator",
            "reporter_mention": None,
            "episode": "episode-2",
        }
    )
    batch["dispositions"][0]["proposal_ids"].append("p2")
    wire = Wire(json.dumps(batch))
    before_head = lane.repo.get_head(lane.world.world_id)
    before_epoch = lane.repo.open_native_source_view(lane.world.world_id).epoch
    with client(monkeypatch, wire) as c:
        req, record = produce(c, lane)
        assert record["state"] == "completed", record
        sent = json.loads(wire.requests[0]["input"][0]["content"])
        assert sent_body(sent) == BODY
        assert "registered_evidence_extent" not in sent
        assert (
            record["review_eligibility"]["p1"]["status"]
            == "requires_explicit_clause_selection"
        )
        assert (
            record["review_eligibility"]["p2"]["status"]
            == "requires_explicit_clause_selection"
        )
        assert all(
            row["semantic_acceptance"] == "not_established"
            for row in record["review_eligibility"].values()
        )
        persisted = store.read(req.operation_id, GM.subject, req.managed_world_id)
        assert "review_eligibility" not in persisted
        assert c.get(url(req)).json() == record
        assert (
            c.post(
                "/api/live/source-statements/proposals",
                json=req.model_dump(mode="json"),
            ).json()
            == record
        )
        assert len(wire.requests) == 1
        assert (
            store.read(req.operation_id, GM.subject, req.managed_world_id) == persisted
        )
        outside = review_body(lane, record)
        outside["proposal_id"] = "p2"
        outside["selection"].update(
            start_byte=lane.selection.end_byte,
            end_byte=len(BODY.encode()),
            clause_sha256=sha256(second.encode()).hexdigest(),
        )
        refused = c.post(review_url(req), json=outside)
        assert refused.status_code == 409, refused.text
        assert "outside its admitted evidence span" in refused.text
        assert c.get(url(req)).json()["reviews"] == []
        inside = c.post(review_url(req), json=review_body(lane, record))
        assert inside.status_code == 200, inside.text
    assert lane.repo.get_head(lane.world.world_id) == before_head
    assert lane.repo.open_native_source_view(lane.world.world_id).epoch == before_epoch


@pytest.mark.parametrize(
    "bad_field,bad_value",
    [
        ("source_admission_id", "missing"),
        ("source_sha256", "0" * 64),
        ("managed_world_id", "foreign"),
    ],
)
def test_partial_source_bad_proof_refuses_before_claim_or_provider(
    partial_span_lane, application_state_dsn, monkeypatch, bad_field, bad_value
):
    from application_state.statement_proposals import service as store

    wire = Wire()
    lane = partial_span_lane
    req = request_for(lane)
    bad = req.model_dump(mode="json") | {bad_field: bad_value}
    with client(monkeypatch, wire) as c:
        assert (
            c.post("/api/live/source-statements/proposals", json=bad).status_code == 409
        )
    assert wire.requests == []
    assert store.read(req.operation_id, GM.subject, bad["managed_world_id"]) is None


def test_partial_source_visibility_denial_precedes_claim(
    partial_span_lane, application_state_dsn, monkeypatch
):
    from application_state.statement_proposals import service as store

    lane = partial_span_lane
    original = source_statements._context

    def no_audience(*args, **kwargs):
        read, access, domain, profile = original(*args, **kwargs)
        return read, replace(access, audience_labels=frozenset()), domain, profile

    monkeypatch.setattr(source_statements, "_context", no_audience)
    wire = Wire()
    req = request_for(lane)
    with client(monkeypatch, wire) as c:
        assert (
            c.post(
                "/api/live/source-statements/proposals",
                json=req.model_dump(mode="json"),
            ).status_code
            == 409
        )
    assert wire.requests == []
    assert store.read(req.operation_id, GM.subject, req.managed_world_id) is None


def test_corrupt_native_body_never_becomes_proposal_input(
    partial_span_lane, application_state_dsn, monkeypatch
):
    from application_state.statement_proposals import service as store

    lane = partial_span_lane
    receipt = lane.repo.get_native_source_admission_receipt(
        lane.world.world_id, lane.selection.source_admission_id
    )
    key = (lane.world.world_id, receipt.source_artifact_id)
    # Fault injection into actual repository: Core must reject its stale fingerprint.
    lane.repo._native_records[key] = replace(
        lane.repo._native_records[key], body=b"corrupt"
    )
    req, wire = request_for(lane), Wire()
    with client(monkeypatch, wire) as c:
        response = c.post(
            "/api/live/source-statements/proposals", json=req.model_dump(mode="json")
        )
        assert response.status_code == 409, response.text
    assert wire.requests == []
    assert store.read(req.operation_id, GM.subject, req.managed_world_id) is None


def test_unit_eligibility_is_a_derived_view_not_clause_acceptance():
    from graph_memory.extraction.qualified_statement_proposals import parse
    from graph_memory.extraction.statement_source_catalog import catalog

    source = catalog(BODY, {})
    batch = deepcopy(BATCH) | {"catalog_sha256": source["catalog_sha256"]}
    original = {"result": parse(json.dumps(batch), source)}
    before = deepcopy(original)
    view = service._view(original, {"start_byte": 0, "end_byte": 5})
    assert original == before
    offered = view["review_eligibility"]["p1"]
    assert offered["status"] == "requires_explicit_clause_selection"
    assert offered["candidate_extents"] == [
        {"unit_id": "u1", "start_byte": 0, "end_byte": 5}
    ]
    assert offered["semantic_acceptance"] == "not_established"


def test_producer_budget_does_not_mutate_answer_policy(monkeypatch):
    from apps.live_control_server.services import agent_turn_service

    original = agent_turn_service._policy_request_budget()
    monkeypatch.setattr(agent_turn_service, "_policy_request_budget", lambda: original)
    assert service._producer_budget() == original | {"outputReserveTokens": 128_000}
    assert original["outputReserveTokens"] == 8192


def test_completed_output_beyond_old_limit_persists_exactly(
    lane, application_state_dsn, monkeypatch
):
    batch = deepcopy(BATCH)
    # SDK fixture usage represents output above the old ceiling, not a live-model measurement.
    batch["limitations"] = ["synthetic coverage caveat " * 9000]
    wire = Wire(json.dumps(batch), output_tokens=9000)
    with client(monkeypatch, wire) as c:
        req, record = produce(c, lane)
        assert record["state"] == "completed", record
        assert wire.requests[0]["max_output_tokens"] == 128_000
        assert sent_body(json.loads(wire.requests[0]["input"][0]["content"])) == BODY
        assert record["raw_output"] == wire.raw
        assert record["result"]["batch"] == json.loads(wire.raw)
        assert c.get(url(req)).json() == record
        assert len(wire.requests) == 1


def test_old_incomplete_operation_replay_after_budget_change(
    lane, application_state_dsn, monkeypatch
):
    current = service._producer_budget
    monkeypatch.setattr(
        service, "_producer_budget", lambda: current() | {"outputReserveTokens": 8192}
    )
    wire = Wire('{"mentions":[', incomplete=True, output_tokens=8192)
    with client(monkeypatch, wire) as c:
        req, record = produce(c, lane)
        assert record["state"] == "failed"
        raw = json.loads(record["raw_output"])
        assert raw["status"] == "incomplete"
        assert raw["incomplete_details"]["reason"] == "max_output_tokens"
        assert raw["usage"]["output_tokens"] == 8192
        assert json.loads(record["wire"])["max_output_tokens"] == 8192
        assert record["result"] is None
        monkeypatch.setattr(service, "_producer_budget", current)
        assert service._producer_budget()["outputReserveTokens"] == 128_000
        assert (
            c.post(
                "/api/live/source-statements/proposals",
                json=req.model_dump(mode="json"),
            ).json()
            == record
        )
        assert c.get(url(req)).json() == record
        assert len(wire.requests) == 1


@pytest.mark.parametrize(
    "change",
    [
        {"model": "unverified"},
        {"provider": "unverified"},
        {"contextLimitTokens": 128_000},
        {"maxProviderRequestBytes": 1},
    ],
)
def test_unverified_or_oversized_producer_refuses_before_transport(
    lane, application_state_dsn, monkeypatch, change
):
    from apps.live_control_server.services import agent_turn_service

    original = agent_turn_service._policy_request_budget()
    monkeypatch.setattr(
        agent_turn_service, "_policy_request_budget", lambda: original | change
    )
    wire = Wire()
    with client(monkeypatch, wire) as c:
        _, record = produce(c, lane)
        assert record["state"] == "failed"
        assert record["failure"] == "proposal_generation_not_dispatched"
        assert record["wire"] is None
        assert record["result"] is None
        assert wire.requests == []


def test_prepared_output_budget_drift_refuses_before_transport(
    lane, application_state_dsn, monkeypatch
):
    import generationengine

    original = generationengine.TextRequest
    monkeypatch.setattr(
        generationengine,
        "TextRequest",
        lambda **kwargs: original(**(kwargs | {"max_output_tokens": 8192})),
    )
    wire = Wire()
    with client(monkeypatch, wire) as c:
        _, record = produce(c, lane)
        assert record["state"] == "failed"
        assert record["failure"] == "proposal_generation_not_dispatched"
        assert record["wire"] is None
        assert wire.requests == []


def test_forged_catalog_commitment_fails_without_repair(
    lane, application_state_dsn, monkeypatch
):
    batch = deepcopy(BATCH) | {"catalog_sha256": "0" * 64}
    wire = Wire(json.dumps(batch))
    with client(monkeypatch, wire) as c:
        _, record = produce(c, lane)
        assert record["state"] == "failed"
        assert record["result"] is None
        assert record["raw_output"] == wire.raw


@pytest.mark.parametrize("entered", [True, False])
def test_actual_v1_failed_contract_replays_without_current_rendering(
    lane, application_state_dsn, monkeypatch, entered
):
    from application_state.statement_proposals import service as store
    from graph_memory.extraction.qualified_statement_proposals import canonical

    req = request_for(lane)
    _, _, old_input, _ = service._acquire(req, GM)
    old_input["output_schema"] = {"title": "Original V1 output schema"}
    row, _ = store.claim(
        req.operation_id, GM.subject, req.model_dump(mode="json"), old_input
    )
    if entered:
        wire = canonical(
            {
                "input": [{"role": "user", "content": canonical(old_input)}],
                "instructions": "original literal-copy prompt",
                "max_output_tokens": 8192,
            }
        )
        row = store.change(row, state="entered", wire=wire)
    failed = store.change(
        row,
        state="failed",
        raw_output="original nonliteral output",
        failure="original_failure",
    )

    def no_render(*args):
        raise AssertionError("Historical failure must not use current rendering")

    monkeypatch.setattr(service, "_render", no_render)
    transport = Wire()
    with client(monkeypatch, transport) as c:
        assert c.get(url(req)).json() == failed | {"review_eligibility": {}}
        assert c.post(
            "/api/live/source-statements/proposals", json=req.model_dump(mode="json")
        ).json() == failed | {"review_eligibility": {}}
    assert transport.requests == []
    assert store.read(req.operation_id, GM.subject, req.managed_world_id) == failed


@pytest.mark.parametrize("tamper", ["result", "input", "wire"])
def test_stored_result_and_wire_input_tampering_refuse(
    lane, application_state_dsn, monkeypatch, tamper
):
    from application_state.unit_of_work import unit_of_work
    from psycopg.types.json import Jsonb

    with client(monkeypatch, Wire()) as c:
        req, row = produce(c, lane)
        with unit_of_work(application_state_dsn) as conn:
            if tamper == "result":
                changed = deepcopy(row["result"])
                changed["passages"]["p1"]["primary"][0]["text"] = "altered"
                conn.execute(
                    "UPDATE ingest.statement_proposal_operation SET payload=jsonb_set(payload,'{result}',%s) WHERE operation_id=%s",
                    (Jsonb(changed), req.operation_id),
                )
            elif tamper == "input":
                changed = deepcopy(row["input"])
                changed["source_catalog"]["units"][0]["text"] = "altered"
                conn.execute(
                    "UPDATE ingest.statement_proposal_operation SET payload=jsonb_set(payload,'{input}',%s) WHERE operation_id=%s",
                    (Jsonb(changed), req.operation_id),
                )
            else:
                from hashlib import sha256

                changed = json.loads(row["wire"])
                changed["input"] = []
                raw = json.dumps(changed)
                conn.execute(
                    "UPDATE ingest.statement_proposal_operation SET payload=jsonb_set(jsonb_set(payload,'{wire}',%s),'{wire_digest}',%s) WHERE operation_id=%s",
                    (
                        Jsonb(raw),
                        Jsonb(sha256(raw.encode()).hexdigest()),
                        req.operation_id,
                    ),
                )
        assert c.get(url(req)).status_code == 409


def test_review_narrows_same_unit_but_conflicting_clause_meaning_refuses(
    lane, application_state_dsn, monkeypatch
):
    batch = deepcopy(BATCH)
    batch["proposals"].append(
        batch["proposals"][0]
        | {"proposal_id": "p2", "meaning": "another interpretation"}
    )
    batch["dispositions"][0]["proposal_ids"].append("p2")
    with client(monkeypatch, Wire(json.dumps(batch))) as c:
        req, row = produce(c, lane)
        # The host passage includes BOTH lines, while explicit review narrows to line one.
        assert row["result"]["passages"]["p1"]["primary"][0]["text"] == BODY
        body = review_body(lane, row)
        first = c.post(review_url(req), json=body)
        assert first.status_code == 200, first.text
        packet = first.json()["prepared_packet"]
        from apps.live_control_server.models.source_statements import ConfirmStatement

        source_statements.confirm(
            ConfirmStatement(
                **{k: packet[k] for k in ("envelope", "prepared", "token")}
            ),
            GM,
        )
        updated = c.get(url(req)).json()
        other = review_body(lane, updated)
        other["proposal_id"] = "p2"
        other["selection"]["meaning"] = "conflicting interpretation"
        other["selection"]["expected_parent_revision_id"] = lane.repo.get_head(
            lane.world.world_id
        ).head_revision_id
        response = c.post(review_url(req), json=other)
        assert response.status_code == 409, response.text
