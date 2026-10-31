"""Authenticated review boundary and real WK/Core preparation, with read owners stubbed.

Persistent source admission is covered separately; these tests perform no DB/provider IO.
"""

import copy
import json
from hashlib import sha256
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from worldkeeper.application import CreateObject, CreateRelationship, DurableObjectRef, ResultOf, UseExisting

from apps.live_control_server.routes.extract_promote import router
from apps.live_control_server.services import native_recap_preparation as service
from apps.live_control_server.integrations.worldkeeper import registry_standing_consumer as transport
from graph_memory.candidate_graph_preview import NODE_TYPES
from graph_memory.source_span import build_source_span_index_for_text
from tests.test_con_ready_play_worldkeeper_consumer import (
    _repository, SPACE_ID, CAMPAIGN_ID, EVIDENCE_ID,
)

TOKEN = "synthetic-native-recap-review-operator-credential"
META = {
    "visibility": {"kind": "labels_any", "labels": ["dungeonbuddy.visibility:gm"]},
    "epistemic_basis": "asserted", "claim_mode": "dungeonbuddy.claim:fact",
    "standing": "provisional", "temporal_scope": {"kind": "timeless"},
}


def choice(identifier, kind="node", action="create", fields=("label", "node_type"), **extra):
    return dict(kind=kind, record_id=identifier, action=action,
                facts=[dict(field=f, metadata=copy.deepcopy(META)) for f in fields], **extra)


@pytest.fixture
def lane(monkeypatch, tmp_path):
    monkeypatch.setenv("DMB_AGENT_GRAPH_AUTH_MODE", "local_operator")
    monkeypatch.setenv("DMB_AGENT_GRAPH_AUTH_ENVIRONMENT", "local")
    monkeypatch.setenv("DMB_AGENT_GRAPH_LOCAL_OPERATOR_TOKEN", TOKEN)
    repo = _repository()
    bound = {"native_world_id": SPACE_ID, "binding_version": 3}
    source_id = "artifact:recap:v2:review-fixture"
    text = "A traveller met Pippa near the tower.\n"
    digest = sha256(text.encode()).hexdigest()
    spans = build_source_span_index_for_text(source_artifact_id=source_id, content_sha256=digest, text=text)
    evidence = [dict(source_ref_id="source:fixture", source_artifact_id=source_id,
                     source_span_ref_id=spans.spans[0].source_span_id,
                     can_open_source=True, can_highlight_span=True,
                     evidence_role="source_evidence", anchor_quotes=["A traveller met Pippa"])]
    state = dict(canon_state="candidate_extraction", lifecycle_state="candidate",
                 evidence_role="source_evidence", authority_state="llm_generated", visibility_state="gm_private")
    def node(identifier, kind):
        return dict(node_id=identifier, label=identifier, node_type=kind, description="Exact saved description",
                    importance="high", semantic_state=state, evidence_refs=evidence,
                    proposed_action="create", confidence="high")
    payload = dict(
        schema="dmb_candidate_graph_preview_v0", version="0.1", preview_id="preview:fixture",
        campaign_id=CAMPAIGN_ID, session_id="session-8", source_artifact_ids=[source_id], status="preview",
        nodes=[node("new", "character"), node("existing", "location")],
        edges=[dict(edge_id="edge", from_node_id="new", to_node_id="existing", label="met",
                    relationship_type="met_at", semantic_state=state, evidence_refs=evidence,
                    proposed_action="create", confidence="high")],
        beats=[dict(beat_id="beat", title="A meeting", summary="A traveller met Pippa", order=1,
                    involved_node_ids=["new"], evidence_refs=evidence)],
        ignored_items=[dict(item_id="ignored", label="Aside", reason="not fact", evidence_refs=evidence)],
        deferred_items=[dict(item_id="deferred", label="Possibility", reason="unresolved", evidence_refs=evidence)],
        proposed_writes=[], diagnostics=dict(preview_only=True, extraction_performed=False, llm_used=False,
            runtime_connected=False, plan_connected=False, agent_interaction_connected=False,
            corpus_scanned=False, corpus_mutated=False, facts_promoted=False, canon_promoted=False,
            unresolved_evidence_refs=0, missing_evidence_objects=0, warning_count=0),
    )
    payload["nodes"][0].update(aliases=["Someone"], session_actions=["Met Pippa"],
        corpus_ref=dict(type="pc", ref_id="not-a-native-identity", resolution="resolved"))
    artifact = SimpleNamespace(source_artifact_id=source_id, content_sha256=digest, world_id=SPACE_ID,
                               source_domain="recap", campaign_id=CAMPAIGN_ID, session_id="session-8")
    source = SimpleNamespace(**vars(artifact), source_revision_id=uuid4(), media_type="text/markdown",
                             encoding="utf-8", markdown=text)
    run = SimpleNamespace(run_id="saved-run", revision=5, source_domain="recap", campaign_id=CAMPAIGN_ID,
                          session_id="session-8", lineage={"world_campaign_ingest_context": dict(
                              managed_world_id="managed", campaign_id=CAMPAIGN_ID, **bound)})
    data = SimpleNamespace(run=run, source_artifact=artifact, source_bytes=text.encode(), span_index=spans)
    admitted = SimpleNamespace(state="admitted", opening=SimpleNamespace(state="verified"),
        app_source_artifact_id=source_id, app_source_revision_id=source.source_revision_id,
        app_body_sha256=digest, native_world_id=SPACE_ID, binding_version=3,
        evidence_ref_id=EVIDENCE_ID, admission_id="admitted:fixture")
    monkeypatch.setattr(service.config, "artifact_data_root", lambda: tmp_path)
    monkeypatch.setattr(service, "load_reviewable_extraction_data", lambda *_: data)
    monkeypatch.setattr(service.sources, "get_source_markdown", lambda **_: source)
    monkeypatch.setattr(service.admission, "inspect", lambda *_: admitted)
    monkeypatch.setattr(service.native, "binding", lambda _: copy.deepcopy(bound))
    monkeypatch.setattr(service.native, "repository", lambda: repo)
    parent = repo.get_head(SPACE_ID).head_revision_id
    snapshot = repo.get_revision(SPACE_ID, parent)
    def ref(value, name):
        return dict(authority_id=getattr(value, name + "_id"), revision=getattr(value, name + "_revision"),
                    descriptor_sha256=value.descriptor_sha256)
    context = dict(space_id=SPACE_ID, revision_id=parent, graph_sha256=snapshot.graph_payload_sha256,
                   domain_ref=ref(snapshot.revision.domain_contract_ref, "domain"),
                   profile_ref=ref(snapshot.revision.semantic_profile_ref, "profile"))
    monkeypatch.setattr(service.native, "access_context", lambda *_: (context, None))
    import httpx
    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", lambda *_: pytest.fail("provider HTTP forbidden"))
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app, client=("127.0.0.1", 50000))
    body = dict(managed_world_id="managed", campaign_id=CAMPAIGN_ID, run_id="saved-run",
        expected_run_revision=5, source_admission_run_id="admitted-run",
        expected_parent_revision_id=parent, selections=[choice("new"),
            choice("existing", action="use_existing", entity_id="ent:pippa", fields=()),
            choice("beat", kind="beat", fields=("title", "node_type", "summary")),
            dict(kind="edge", record_id="edge", action="create", metadata=copy.deepcopy(META))])
    def refresh():
        data.candidate_bytes = json.dumps(payload).encode()
        body["candidate_sha256"] = sha256(data.candidate_bytes).hexdigest()
    refresh()
    def post(body_override=None):
        return client.post("/api/live/extract-promote/native-prepare", json=body_override or body,
                           headers={"Authorization": "Bearer " + TOKEN})
    return SimpleNamespace(**locals())


def test_ordinary_HTTP_exact_choices_real_WK_preparation_without_writes(lane):
    before = copy.deepcopy({key: value for key, value in lane.repo.__dict__.items() if key != "_lock"})
    response = lane.post()
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["publication"] == "not_performed" and result["status"] == "prepared"
    prepared = transport.decode_prepared(result["prepared"])
    operations = prepared.prepared_operations
    assert isinstance(operations[0], CreateObject)
    assert operations[0].facts[1].value.term == "dungeonbuddy:character"  # neither NPC nor PC
    assert isinstance(operations[1], UseExisting) and operations[1].durable_object_id == "ent:pippa"
    assert operations[2].facts[1].value.term == "dungeonbuddy:session_beat"
    assert len([op for op in operations if isinstance(op, CreateRelationship)]) == 1
    edge = operations[-1]
    assert edge.source == ResultOf("record:0") and edge.target == DurableObjectRef("ent:pippa")
    assert edge.predicate == "dungeonbuddy.custom:met_at"
    assert all(f.metadata.evidence_ref_ids == (EVIDENCE_ID,) for op in operations[:-1] for f in op.facts)
    assert operations[0].facts[0].metadata.standing == "provisional"
    assert len(result["records"]) == 6
    assert result["records"][0]["held_aliases"] == ["Someone"]
    assert "session_actions:0" in result["records"][0]["unselected_fields"]
    assert {key: value for key, value in lane.repo.__dict__.items() if key != "_lock"} == before


@pytest.mark.parametrize("fault,expected", [
    ("revision", "candidate_run_changed"), ("digest", "candidate_bytes_changed"),
    ("uuid", "candidate_admission_mismatch"), ("scope", "candidate_source_mismatch"),
    ("binding", "candidate_world_binding_mismatch"), ("unavailable", "candidate_source_not_admitted"),
    ("source", "candidate_source_mismatch"), ("parent", "candidate_parent_stale"),
    ("quote", "run_not_promotable"), ("dangling", "selected_edge_endpoint_held"),
])
def test_exact_owner_and_review_refusals(lane, fault, expected):
    if fault == "revision": lane.body["expected_run_revision"] = 4
    elif fault == "digest": lane.body["candidate_sha256"] = "0" * 64
    elif fault == "uuid": lane.admitted.app_source_revision_id = uuid4()
    elif fault == "scope": lane.source.campaign_id = "foreign"
    elif fault == "binding": lane.bound["binding_version"] = 4
    elif fault == "unavailable": lane.admitted.opening.state = "unavailable"
    elif fault == "source": lane.source.markdown += "changed"
    elif fault == "parent": lane.body["expected_parent_revision_id"] = "rev:stale"
    elif fault == "quote":
        lane.payload["nodes"][0]["evidence_refs"][0]["anchor_quotes"] = ["invented text"]
        lane.refresh()
    elif fault == "dangling": lane.body["selections"][1] = choice("existing", action="defer", fields=())
    before = copy.deepcopy({key: value for key, value in lane.repo.__dict__.items() if key != "_lock"})
    response = lane.post()
    assert response.status_code in (409, 422), response.text
    assert expected in response.text
    assert {key: value for key, value in lane.repo.__dict__.items() if key != "_lock"} == before


def test_auth_and_closed_request_before_read_owners(lane, monkeypatch):
    monkeypatch.setattr(service, "load_reviewable_extraction_data", lambda *_: pytest.fail("unauthorized read"))
    assert lane.client.post("/api/live/extract-promote/native-prepare", json=lane.body).status_code == 401
    for mutate in (
        lambda b: b.update(evidence_ref_id="ev:forged"),
        lambda b: b["selections"].append(b["selections"][0]),
        lambda b: b["selections"][0]["facts"][0]["metadata"].update(evidence_ref_ids=["ev:forged"]),
        lambda b: b["selections"][0].update(entity_id="ent:guessed"),
        lambda b: b["selections"][0]["facts"].append(b["selections"][0]["facts"][0]),
    ):
        body = copy.deepcopy(lane.body)
        mutate(body)
        assert lane.post(body).status_code == 422
    raw = json.dumps(lane.body).replace('"run_id": "saved-run"', '"run_id":"other","run_id":"saved-run"')
    assert lane.client.post("/api/live/extract-promote/native-prepare", content=raw,
        headers={"Authorization": "Bearer " + TOKEN, "Content-Type": "application/json"}).status_code == 422


@pytest.mark.parametrize("race", ["binding", "parent"])
def test_race_after_actual_preparation_refuses(lane, monkeypatch, race):
    runtime = transport.runtime
    def prepare_then_change(*args, **kwargs):
        actual = runtime(*args, **kwargs)
        class Racing:
            def prepare_change(self, intent):
                result = actual.prepare_change(intent)
                if race == "binding": lane.bound["binding_version"] += 1
                else: monkeypatch.setattr(lane.repo, "get_head", lambda *_: SimpleNamespace(head_revision_id="rev:new"))
                return result
        return Racing()
    monkeypatch.setattr(transport, "runtime", prepare_then_change)
    response = lane.post()
    assert response.status_code == 409
    assert ("candidate_binding_changed" if race == "binding" else "candidate_parent_stale") in response.text


def test_all_current_kinds_and_explicit_action_fact(lane):
    lane.body["selections"] = [choice("new")]
    for kind in sorted(NODE_TYPES):
        lane.payload["nodes"][0]["node_type"] = kind
        lane.refresh()
        response = lane.post()
        assert response.status_code == 200, response.text
        prepared = transport.decode_prepared(response.json()["prepared"])
        assert prepared.prepared_operations[0].facts[1].value.term.endswith(":" + kind)
    lane.payload["nodes"][0]["node_type"] = "invented_kind"
    lane.refresh()
    assert "unsupported_candidate_kind" in lane.post().text
    lane.payload["nodes"][0]["node_type"] = "character"
    lane.refresh()
    lane.body["selections"][0]["facts"] = [dict(field="session_actions", index=0, metadata=copy.deepcopy(META))]
    response = lane.post()
    assert response.status_code == 200, response.text
    fact = transport.decode_prepared(response.json()["prepared"]).prepared_operations[0].facts[0]
    assert fact.value.value == "Met Pippa"


def test_whole_115_record_inventory_and_no_automatic_acceptance(lane):
    node, edge, beat = (copy.deepcopy(lane.payload[k][0]) for k in ("nodes", "edges", "beats"))
    lane.payload["nodes"] = [dict(node, node_id=f"node:{i}") for i in range(51)]
    lane.payload["edges"] = [dict(edge, edge_id=f"edge:{i}", from_node_id="node:0", to_node_id="node:1") for i in range(46)]
    lane.payload["beats"] = [dict(beat, beat_id=f"beat:{i}", involved_node_ids=["node:0"], order=i+1) for i in range(12)]
    for kind in ("ignored_items", "deferred_items"):
        lane.payload[kind] = [dict(lane.payload[kind][0], item_id=f"{kind}:{i}") for i in range(3)]
    lane.refresh()
    lane.body["selections"] = []
    response = lane.post()
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["prepared"] is None and result["status"] == "held"
    assert len(result["records"]) == 115
    assert all(record["disposition"] == "held" for record in result["records"])


def test_reviewed_metadata_and_temporal_qualification_survive(lane):
    lane.body["selections"] = [choice("new", fields=("description",))]
    metadata = lane.body["selections"][0]["facts"][0]["metadata"]
    metadata.update(claim_mode="dungeonbuddy.claim:belief", epistemic_basis="asserted",
        temporal_scope={"kind": "domain_ref", "schema_term": "dungeonbuddy.time:fictional_anchor_v1",
                        "payload": {"episode": "session-8", "qualified": True}},
        domain_metadata=[{"schema_term": "dungeonbuddy.domain_metadata:world_context_v1",
                          "payload": {"uncertain": ["who reported it"]}}])
    response = lane.post()
    assert response.status_code == 200, response.text
    fact = transport.decode_prepared(response.json()["prepared"]).prepared_operations[0].facts[0]
    from worldkeeper.application.contracts import thaw_json
    assert fact.metadata.claim_mode == "dungeonbuddy.claim:belief"
    assert thaw_json(fact.metadata.temporal_scope.payload) == {"episode": "session-8", "qualified": True}
    assert thaw_json(fact.metadata.domain_metadata[0].payload) == {"uncertain": ["who reported it"]}


def test_owner_unavailable_error_keeps_failure_status(lane, monkeypatch):
    from application_state.errors import ApplicationStateUnavailableError
    def unavailable(**_):
        raise ApplicationStateUnavailableError("synthetic owner unavailable")
    monkeypatch.setattr(service.sources, "get_source_markdown", unavailable)
    response = lane.post()
    assert response.status_code == 503 and "synthetic owner unavailable" in response.text


def test_native_contract_rejects_unknown_epistemic_basis(lane):
    lane.body["selections"] = [choice("new", fields=("description",))]
    lane.body["selections"][0]["facts"][0]["metadata"]["epistemic_basis"] = "unregistered"
    response = lane.post()
    assert response.status_code == 409 and "malformed_semantic_contract" in response.text


@pytest.mark.parametrize('body', [b'{"a":1,"a":2}', b'{"a":NaN}', b'{"a":Infinity}', b'not-json'])
def test_shared_json_gate_refuses_before_review_owner_io(lane, monkeypatch, body):
    monkeypatch.setattr(service, 'load_reviewable_extraction_data',
                        lambda *_: pytest.fail('Malformed JSON reached source owner'))
    response = lane.client.post('/api/live/extract-promote/native-prepare', content=body,
        headers={'Authorization': 'Bearer ' + TOKEN, 'Content-Type': 'application/json'})
    assert response.status_code == 422
    assert response.json()['detail']['code'] == 'invalid_json'


def test_actual_app_retires_directory_standing_without_removing_native_consumers():
    from apps.live_control_server.main import create_app
    paths = {getattr(route, 'path', '') for route in create_app().routes}
    assert not any(path.startswith('/api/live/extract-promote/registry-standing') for path in paths)
    assert '/api/live/extract-promote/native-prepare' in paths
    assert '/api/live/source-statements/extend-evidence' in paths
