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
from tests.application_state.conftest import application_state_dsn as application_state_dsn
from apps.live_control_server.models.source_statement_proposals import ProposalRequest
from apps.live_control_server.services import source_statement_proposals as service
from apps.live_control_server.services import source_statements

BATCH = {
    "mentions": [{"mention_id": "a", "label": "A", "quote": "A"},
                 {"mention_id": "b", "label": "B", "quote": "B"}],
    "proposals": [{"proposal_id": "p1", "quote": BODY.splitlines(keepends=True)[0],
        "meaning": "B fled", "mode": "reported", "reporter_mention": "a",
        "referent_mentions": ["b"], "uncertainty": ["uncertain"],
        "qualifications": {"source_local": "report only"}, "episode": "episode-1",
        "context_quotes": [], "unresolved": ["native identities need review"]}],
    "limitations": ["Extraction coverage is not established"],
}


class Wire:
    def __init__(self, raw=None, failure=False):
        self.requests = []
        self.raw = json.dumps(BATCH) if raw is None else raw
        outer = self

        class Transport(httpx.AsyncBaseTransport):
            async def handle_async_request(self, request):
                outer.requests.append(json.loads(request.content))
                if failure:
                    raise httpx.ReadTimeout("synthetic unknown", request=request)
                return httpx.Response(200, request=request, json={
                    "id": "resp_proposal", "object": "response", "created_at": 1,
                    "status": "completed", "model": "gpt-6-luna",
                    "output": [{"type": "message", "id": "msg_proposal", "role": "assistant",
                        "status": "completed", "content": [{"type": "output_text",
                        "text": outer.raw, "annotations": []}]}],
                    "usage": {"input_tokens": 200, "output_tokens": 100, "total_tokens": 300}})
            async def aclose(self):
                pass
        self.transport = Transport()


def request_for(lane):
    s = lane.selection
    return ProposalRequest(operation_id=uuid4(), managed_world_id=s.managed_world_id,
        campaign_id=s.campaign_id, read_revision_id=s.expected_parent_revision_id,
        source_admission_id=s.source_admission_id, evidence_ref_id=s.evidence_ref_id,
        source_sha256=s.source_sha256)


def client(monkeypatch, wire):
    from apps.live_control_server.routes import source_statements as routes
    from apps.live_control_server.services.agent_graph_auth import native_graph_gm_dependency
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
    response = c.post("/api/live/source-statements/proposals", json=req.model_dump(mode="json"))
    assert response.status_code == 200, response.text
    return req, response.json()


def url(req):
    return f"/api/live/source-statements/proposals/{req.operation_id}?managed_world_id={req.managed_world_id}"


def review_body(lane, record):
    return {"decision_id": str(uuid4()), "expected_revision": record["revision"],
            "proposal_id": "p1", "selection": lane.selection.model_dump(mode="json")}


def review_url(req):
    return f"/api/live/source-statements/proposals/{req.operation_id}/review?managed_world_id={req.managed_world_id}"


def test_routes_produce_reload_review_publish_and_replay(lane, application_state_dsn, monkeypatch):
    wire = Wire()
    with client(monkeypatch, wire) as c:
        req, record = produce(c, lane)
        assert record["state"] == "completed", record
        assert len(wire.requests) == 1
        assert [e["outcome"] for e in record["lifecycle"]] == ["sending", "response_received"]
        assert record["raw_output"] == wire.raw
        assert json.loads(record["wire"]) == wire.requests[0]
        sent = json.loads(wire.requests[0]["input"][0]["content"])
        assert sent["source"] == BODY
        assert {row["entity"]["entity_id"] for row in sent["world_identity_context"]["entities"]} == set(lane.ids.values())
        assert sent["authority"]["binding"]["native_world_id"] == req.managed_world_id
        assert c.get(url(req)).json() == record
        assert c.post("/api/live/source-statements/proposals", json=req.model_dump(mode="json")).json() == record
        assert len(wire.requests) == 1
        body = review_body(lane, record)
        reviewed = c.post(review_url(req), json=body)
        assert reviewed.status_code == 200, reviewed.text
        decision = reviewed.json()
        packet = decision["prepared_packet"]
        from apps.live_control_server.models.source_statements import ConfirmStatement
        published = source_statements.confirm(ConfirmStatement(**{k:packet[k] for k in ("envelope","prepared","token")}), GM)
        advance(lane)
        # Lost review acknowledgment returns exact packet after a native descendant.
        assert c.post(review_url(req), json=body).json() == decision
        read = source_statements.read_subject(managed_world_id=req.managed_world_id,
            campaign_id="c1", revision_id=published["result"]["receipt"]["published_revision_id"],
            entity_id=lane.ids["B"], principal=GM)
        assert len(read["statements"]) == 1
        assert read["statements"][0]["payload"]["embedded_content_factive"] is False
        body["selection"]["meaning"] = "different interpretation"
        assert c.post(review_url(req), json=body).status_code == 409


@pytest.mark.parametrize("raw", ["not JSON", '{"mentions":[],"mentions":[],"proposals":[],"limitations":[]}',
                                json.dumps({**BATCH, "proposals": [{**BATCH["proposals"][0], "quote": "not present"}]})])
def test_original_bad_output_preserved_no_redispatch(lane, application_state_dsn, monkeypatch, raw):
    wire = Wire(raw)
    with client(monkeypatch, wire) as c:
        req, record = produce(c, lane)
        assert record["state"] == "failed"
        assert record["raw_output"] == raw
        assert c.post("/api/live/source-statements/proposals", json=req.model_dump(mode="json")).json() == record
        assert len(wire.requests) == 1
        assert c.post(review_url(req), json=review_body(lane, record)).status_code == 409


def test_unknown_io_remains_nonretryable(lane, application_state_dsn, monkeypatch):
    wire = Wire(failure=True)
    with client(monkeypatch, wire) as c:
        req, record = produce(c, lane)
        assert record["state"] == "failed"
        assert "after_entry" in record["failure"]
        assert c.post("/api/live/source-statements/proposals", json=req.model_dump(mode="json")).json() == record
        assert len(wire.requests) == 1


@pytest.mark.parametrize("field,value", [
    ("campaign_id", "different"), ("source_sha256", "0"*64), ("source_admission_id","missing"),
])
def test_review_cannot_change_scope_or_source(lane, application_state_dsn, monkeypatch, field, value):
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
            service.get(req.operation_id, req.managed_world_id, replace(GM, subject="other"))
        assert c.get(url(req).replace(req.managed_world_id, "foreign")).status_code == 409
        changed = req.model_dump(mode="json") | {"campaign_id": "other"}
        assert c.post("/api/live/source-statements/proposals", json=changed).status_code == 409
        bad = request_for(lane).model_dump(mode="json") | {"source_sha256": "0"*64}
        assert c.post("/api/live/source-statements/proposals", json=bad).status_code == 409
        with pytest.raises(Exception):
            service.get(req.operation_id, req.managed_world_id, replace(GM, role="player"))
        assert record["reviews"] == []


def test_reviews_cas_does_not_return_losing_packet(lane, application_state_dsn, monkeypatch):
    with client(monkeypatch, Wire()) as c:
        req, record = produce(c, lane)
        first = review_body(lane, record)
        assert c.post(review_url(req), json=first).status_code == 200
        assert c.post(review_url(req), json=review_body(lane, record)).status_code == 409
        assert len(c.get(url(req)).json()["reviews"]) == 1


def test_quote_ambiguity_utf8_and_nonfactivity():
    from graph_memory.extraction.qualified_statement_proposals import parse, matches
    batch = deepcopy(BATCH)
    body = "é " + BODY + BODY
    parsed = parse(json.dumps(batch), body)
    location = parsed["locations"]["p1"]
    assert location["status"] == "ambiguous"
    assert location["matches"][0]["start_byte"] == 3
    assert len(location["matches"]) == 2
    assert matches("aaaa", "aa") == [
        {"start_byte": i, "end_byte": i+2, "clause_sha256": matches("aa","aa")[0]["clause_sha256"]}
        for i in range(3)]
    batch["mentions"][0]["mention_id"] = "ent:known"
    with pytest.raises(ValueError):
        parse(json.dumps(batch), body)


def test_review_rejects_unoffered_clause_and_foreign_endpoint(lane, application_state_dsn, monkeypatch):
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
        response = c.get(f"/api/live/source-statements/proposals/{uuid4()}?managed_world_id=private")
        assert response.status_code == 503


@pytest.mark.parametrize("change", [
    {"mode": "reported", "reporter_mention": None},
    {"referent_mentions": ["unknown"]},
    {"embedded_content_factive": True},
    {"qualifications": {}},
])
def test_proposal_cannot_erase_qualifications(change):
    from graph_memory.extraction.qualified_statement_proposals import parse
    batch = deepcopy(BATCH)
    batch["proposals"][0].update(change)
    with pytest.raises(ValueError):
        parse(json.dumps(batch), BODY)
