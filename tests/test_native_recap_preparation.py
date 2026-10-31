"""Authenticated review boundary and real WK/Core preparation, with read owners stubbed.

Core admission/extension/opening are real in memory; APP reads are stubbed. No DB/provider IO.
"""

import copy
import json
from hashlib import sha256
from types import SimpleNamespace
from uuid import uuid4
from datetime import UTC, datetime

from dungeonmind.application.vnext import publish_native_text_source_evidence, publish_native_source_evidence_extension
from dungeonmind.contracts.vnext.native_source import NativeTextSourceAdmissionV1, NativeSourceEvidenceExtensionV1
from dungeonmind.contracts.vnext.knowledge import PublishKnowledgeRevisionCommand
from dungeonmind.infrastructure.memory.vnext_sources import InMemoryNativeSourceEvidenceRepository

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
    _repository, SPACE_ID, CAMPAIGN_ID,
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
    monkeypatch.setenv("DMB_GRAPH_REVIEW_PREPARE_BINDING_KEY", "synthetic-native-recap-review-key")
    seed = _repository(evidence=False)
    snapshot = seed.get_revision(SPACE_ID, seed.get_head(SPACE_ID).head_revision_id)
    repo = InMemoryNativeSourceEvidenceRepository()
    repo.publish_revision(PublishKnowledgeRevisionCommand(
        space_id=SPACE_ID, operation_ids=["fixture-genesis"],
        graph_schema=snapshot.revision.graph_schema, graph_payload=snapshot.graph_payload,
        domain_contract_ref=snapshot.revision.domain_contract_ref,
        semantic_profile_ref=snapshot.revision.semantic_profile_ref,
        created_at=datetime(2026, 10, 31, tzinfo=UTC),
    ))
    bound = {"native_world_id": SPACE_ID, "binding_version": 3}
    source_id = "artifact:recap:v2:review-fixture"
    text = "A traveller met Pippa near the towér.\r\n\r\nThe traveller brought a lantern.\r\n\r\nAnother unrelated episode.\r\n"
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
    domain, profile = service.native.descriptors(repo, SPACE_ID, repo.get_head(SPACE_ID).head_revision_id)
    def span(ref, role, start, end):
        return dict(client_ref=ref, evidence_role=role, start_byte=start, end_byte=end,
                    expected_slice_sha256=sha256(text.encode()[start:end]).hexdigest())
    now = datetime(2026, 10, 31, tzinfo=UTC)
    receipt = publish_native_text_source_evidence(
        repository=repo, domain_contract=domain, semantic_profile=profile,
        request=NativeTextSourceAdmissionV1(
            space_id=SPACE_ID, admission_id="fixture-source",
            expected_parent_revision_id=repo.get_head(SPACE_ID).head_revision_id,
            created_at=now, body_text=text, expected_body_sha256=digest,
            source_classification="dungeonbuddy.source:session_recap", authority="primary",
            visibility=META["visibility"],
            origin=dict(namespace="test.recap", object_id=source_id, revision_id=str(source.source_revision_id)),
            spans=[span("context", "context", 0, len(text.encode()))],
        ),
    )
    raw_lines = text.splitlines(keepends=True)
    first_end = len(raw_lines[0].encode())
    second_start = len(''.join(raw_lines[:2]).encode())
    second_end = len(''.join(raw_lines[:3]).encode())
    third_start = len(''.join(raw_lines[:4]).encode())
    extension = publish_native_source_evidence_extension(
        repository=repo, domain_contract=domain, semantic_profile=profile,
        audience_labels=("dungeonbuddy.visibility:gm",),
        request=NativeSourceEvidenceExtensionV1(
            space_id=SPACE_ID, extension_id="fixture-support",
            original_admission_id=receipt.admission_id,
            source_artifact_id=receipt.source_artifact_id, source_revision_id=receipt.source_revision_id,
            expected_body_sha256=digest, created_at=now,
            expected_parent_revision_id=repo.get_head(SPACE_ID).head_revision_id,
            expected_source_authority_epoch=repo.open_native_source_view(SPACE_ID).epoch,
            spans=[span("first", "support", 0, first_end),
                   span("second", "support", second_start, second_end),
                   span("unrelated", "support", third_start, len(text.encode())),
                   span("contradiction", "contradiction", 0, 1),
                   span("partial", "support", 0, 2)],
        ),
    )
    support_ids = {binding.client_ref: binding.evidence_ref_id for binding in extension.bindings}
    monkeypatch.setitem(META, "evidence_ref_ids", [support_ids["first"]])
    admitted = SimpleNamespace(state="admitted", opening=SimpleNamespace(state="verified"),
        app_source_artifact_id=source_id, app_source_revision_id=source.source_revision_id,
        app_body_sha256=digest, native_world_id=SPACE_ID, binding_version=3,
        evidence_ref_id=receipt.bindings[0].evidence_ref_id, admission_id=receipt.admission_id,
        source_artifact_id=receipt.source_artifact_id, source_revision_id=receipt.source_revision_id)
    monkeypatch.setattr(service.config, "artifact_data_root", lambda: tmp_path)
    monkeypatch.setattr(service, "load_reviewable_extraction_data", lambda *_: data)
    monkeypatch.setattr(service.sources, "get_source_markdown", lambda **_: source)
    monkeypatch.setattr(service.admission, "inspect", lambda *_: admitted)
    monkeypatch.setattr(service.native, "binding", lambda _: copy.deepcopy(bound))
    monkeypatch.setattr(service.native, "repository", lambda: repo)
    parent = repo.get_head(SPACE_ID).head_revision_id
    context, access = service.native.access_context(repo, SPACE_ID)
    import httpx
    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", lambda *_: pytest.fail("provider HTTP forbidden"))
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app, client=("127.0.0.1", 50000))
    body = dict(managed_world_id="managed", campaign_id=CAMPAIGN_ID, run_id="saved-run",
        expected_run_revision=5, source_admission_run_id="admitted-run",
        expected_parent_revision_id=parent, expected_source_authority_epoch=access.source_view.epoch, selections=[choice("new"),
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
    assert all(f.metadata.evidence_ref_ids == (lane.support_ids["first"],) for op in operations[:-1] for f in op.facts)
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
    ("quote", "run_not_promotable"), ("epoch", "candidate_source_authority_stale"), ("dangling", "selected_edge_endpoint_held"),
])
def test_exact_owner_and_review_refusals(lane, fault, expected):
    if fault == "revision":
        lane.body["expected_run_revision"] = 4
    elif fault == "digest":
        lane.body["candidate_sha256"] = "0" * 64
    elif fault == "uuid":
        lane.admitted.app_source_revision_id = uuid4()
    elif fault == "scope":
        lane.source.campaign_id = "foreign"
    elif fault == "binding":
        lane.bound["binding_version"] = 4
    elif fault == "unavailable":
        lane.admitted.opening.state = "unavailable"
    elif fault == "source":
        lane.source.markdown += "changed"
    elif fault == "parent":
        lane.body["expected_parent_revision_id"] = "rev:stale"
    elif fault == "epoch":
        lane.body["expected_source_authority_epoch"] += 1
    elif fault == "quote":
        lane.payload["nodes"][0]["evidence_refs"][0]["anchor_quotes"] = ["invented text"]
        lane.refresh()
    elif fault == "dangling":
        lane.body["selections"][1] = choice("existing", action="defer", fields=())
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
        lambda b: b["selections"][0]["facts"][0]["metadata"].update(scope=["caller-invented"]),
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
                if race == "binding":
                    lane.bound["binding_version"] += 1
                else:
                    monkeypatch.setattr(lane.repo, "get_head", lambda *_: SimpleNamespace(head_revision_id="rev:new"))
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


@pytest.mark.parametrize("target", ["field", "edge"])
@pytest.mark.parametrize("bad", ["context", "contradiction", "unrelated", "partial", "missing"])
def test_only_selected_support_in_saved_record_witness_is_accepted(lane, target, bad):
    metadata = (lane.body["selections"][0]["facts"][0]["metadata"] if target == "field"
                else lane.body["selections"][-1]["metadata"])
    identifier = (lane.admitted.evidence_ref_id if bad == "context" else
                  "ev:absent" if bad == "missing" else lane.support_ids[bad])
    metadata["evidence_ref_ids"] = [identifier]
    before = copy.deepcopy({k: v for k, v in lane.repo.__dict__.items() if k != "_lock"})
    response = lane.post()
    expected = ("candidate_support_required" if bad in {"context", "contradiction", "missing"}
                else "candidate_support_outside_witness")
    assert response.status_code == 409 and expected in response.text, response.text
    assert {k: v for k, v in lane.repo.__dict__.items() if k != "_lock"} == before


@pytest.mark.parametrize("empty", [True, False])
def test_each_fact_requires_explicit_nonempty_support_selection(lane, empty):
    metadata = lane.body["selections"][0]["facts"][0]["metadata"]
    if empty:
        metadata["evidence_ref_ids"] = []
    else:
        metadata.pop("evidence_ref_ids")
    assert lane.post().status_code == 422


def test_available_same_bytes_from_another_admitted_source_cannot_support_candidate(lane):
    other = publish_native_text_source_evidence(
        repository=lane.repo, domain_contract=lane.domain, semantic_profile=lane.profile,
        request=NativeTextSourceAdmissionV1(
            space_id=SPACE_ID, admission_id="different-source",
            expected_parent_revision_id=lane.repo.get_head(SPACE_ID).head_revision_id,
            created_at=lane.now, body_text=lane.text, expected_body_sha256=lane.digest,
            source_classification="dungeonbuddy.source:session_recap", authority="primary",
            visibility=META["visibility"],
            origin=dict(namespace="test.recap", object_id="another-session", revision_id="1"),
            spans=[lane.span("foreign", "support", 0, lane.first_end)],
        ),
    )
    lane.body["expected_parent_revision_id"] = lane.repo.get_head(SPACE_ID).head_revision_id
    lane.body["expected_source_authority_epoch"] = lane.repo.open_native_source_view(SPACE_ID).epoch
    lane.body["selections"][0]["facts"][0]["metadata"]["evidence_ref_ids"] = [other.bindings[0].evidence_ref_id]
    response = lane.post()
    assert response.status_code == 409 and "candidate_support_source_mismatch" in response.text


def test_per_field_multi_span_choices_survive_actual_WK_materialization(lane):
    second = copy.deepcopy(lane.evidence[0])
    second.update(source_span_ref_id=lane.spans.spans[1].source_span_id,
                  anchor_quotes=["The traveller brought a lantern"])
    lane.payload["nodes"][0]["evidence_refs"].append(second)
    lane.payload["edges"][0]["evidence_refs"] = [second]
    lane.refresh()
    lane.body["selections"][0]["facts"][1]["metadata"]["evidence_ref_ids"] = [
        lane.support_ids["first"], lane.support_ids["second"]]
    lane.body["selections"][-1]["metadata"]["evidence_ref_ids"] = [lane.support_ids["second"]]
    before = lane.repo.get_head(SPACE_ID)
    response = lane.post()
    assert response.status_code == 200, response.text
    result = response.json()
    prepared = transport.decode_prepared(result["prepared"])
    assert prepared.prepared_operations[0].facts[0].metadata.evidence_ref_ids == (lane.support_ids["first"],)
    assert prepared.prepared_operations[0].facts[1].metadata.evidence_ref_ids == (
        lane.support_ids["first"], lane.support_ids["second"])
    assert prepared.prepared_operations[-1].metadata.evidence_ref_ids == (lane.support_ids["second"],)
    assert result["expected_source_authority_epoch"] == lane.body["expected_source_authority_epoch"]
    assert lane.repo.get_head(SPACE_ID) == before  # HTTP preparation never publishes.
    # Exercise the existing commit owner, not an invented HTTP confirmation path.
    runtime = transport.runtime(lane.repo, lane.domain, lane.profile,
                                now=prepared.prepared_at, operation_id=prepared.prepared_change_id)
    committed = runtime.commit_prepared_change(prepared, confirmed_by="fixture-operator")
    _, access = service.native.access_context(lane.repo, SPACE_ID)
    assert access.revision_id == committed.child_revision_id
    assert {w.evidence_ref_id for w in prepared.evidence_witnesses} == {
        lane.support_ids["first"], lane.support_ids["second"]}
    for row in committed.assertion_results:
        assertion = access.parsed.get_assertion(row.durable_assertion_id)
        assert assertion.metadata.evidence_ref_ids and set(assertion.metadata.evidence_ref_ids) <= {
            lane.support_ids["first"], lane.support_ids["second"]}


def test_source_epoch_race_after_preparation_refuses(lane, monkeypatch):
    original = transport.runtime
    def racing(*args, **kwargs):
        actual = original(*args, **kwargs)
        class Runtime:
            def prepare_change(self, intent):
                result = actual.prepare_change(intent)
                lane.repo._native_epoch += 1
                return result
        return Runtime()
    monkeypatch.setattr(transport, "runtime", racing)
    response = lane.post()
    assert response.status_code == 409 and "candidate_source_authority_changed" in response.text


def test_missing_owner_source_refuses_without_falling_back_to_APP_bytes(lane):
    lane.repo._native_records.clear()
    response = lane.post()
    assert response.status_code == 409 and "candidate_support_unavailable" in response.text


@pytest.mark.parametrize("unknown", ["record", "field"])
def test_support_does_not_authorize_unselected_candidate_content(lane, unknown):
    if unknown == "record":
        lane.body["selections"][0]["record_id"] = "not-in-saved-candidate"
        expected = "unknown_candidate_selection"
    else:
        lane.body["selections"][0]["facts"][0].update(field="session_actions", index=3)
        expected = "unknown_candidate_field"
    response = lane.post()
    assert response.status_code == 409 and expected in response.text


def confirmation(lane):
    response = lane.post()
    assert response.status_code == 200, response.text
    return {key: response.json()[key] for key in ("envelope", "prepared", "token")}


def confirm(lane, packet):
    return lane.client.post("/api/live/extract-promote/native-confirm", json=packet,
                           headers={"Authorization": "Bearer " + TOKEN})


def test_ordinary_confirmation_commits_once_and_selected_query_opens_support(lane):
    from apps.live_control_server.services.agent_graph_auth import NativeGraphPrincipal
    from apps.live_control_server.services.native_plan_statements import prepare_query
    from apps.live_control_server.services.native_plan_assertions import read_selected
    from application_state.agent_conversation.native_plan_assertions import NativePlanAssertionReadAuthorizedV1
    packet = confirmation(lane)
    before = len(lane.repo.head_events(SPACE_ID))
    response = confirm(lane, packet)
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["status"] == "committed" and not result["recovered"]
    replay = confirm(lane, packet)
    assert replay.status_code == 200, replay.text
    assert replay.json()["recovered"] and replay.json()["result"] == result["result"]
    assert len(lane.repo.head_events(SPACE_ID)) == before + 1
    child = lane.repo.get_revision(SPACE_ID, result["result"]["child_revision_id"])
    assert len(child.graph_payload["assertions"]) == 6  # selected fields and exact edge only
    edge = next(a for a in child.graph_payload["assertions"] if a["predicate"] == "dungeonbuddy.custom:met_at")
    assert edge["value"] == {"kind": "entity_ref", "entity_id": "ent:pippa"}
    principal = NativeGraphPrincipal(subject="test:gm", role="gm", auth_method="local_operator")
    binding = SimpleNamespace(managed_world_id="managed", **lane.bound)
    context, query = prepare_query("managed", "new", principal, repository=lane.repo,
        resolve_binding=lambda _: binding, scope_mode="campaign", campaign_id=CAMPAIGN_ID)
    assert query.assertion_matches
    grant = NativePlanAssertionReadAuthorizedV1(event_id=uuid4(), sequence=0,
        provider_attempt_id=uuid4(), query_sha256=query.sha256,
        assertion_ids=tuple(match.assertion_id for match in query.assertion_matches))
    reads, unavailable = read_selected(context, grant, principal)
    assert reads and not unavailable
    assert all(r.spans[0].evidence_ref_id == lane.support_ids["first"] for r in reads)
    assert all(r.spans[0].text == lane.text.splitlines(keepends=True)[0] for r in reads)


@pytest.mark.parametrize("fault", ["token", "digest", "principal", "packet", "purpose", "extra", "naive_expiry", "binding", "expiry", "parent", "epoch"])
def test_confirmation_refuses_invalid_authority_without_publication(lane, monkeypatch, fault):
    from datetime import timedelta
    packet = confirmation(lane)
    if fault == "token":
        packet["token"] += "x"
    elif fault == "digest":
        packet["envelope"]["prepared_digest"] = "0" * 64
    elif fault == "principal":
        packet["envelope"]["principal"] = "other:gm"
        packet["token"] = service.sign_publication_intent(packet["envelope"])
    elif fault == "packet":
        packet["prepared"]["value"]["fields"]["producer"] = "foreign"
    elif fault == "purpose":
        packet["envelope"]["purpose"] = "another_review"
    elif fault == "extra":
        packet["envelope"]["skip_checks"] = True
    elif fault == "naive_expiry":
        packet["envelope"]["expires_at"] = "2026-10-31T12:00:00"
    elif fault == "binding":
        lane.bound["binding_version"] += 1
    elif fault == "expiry":
        class Later(datetime):
            @classmethod
            def now(cls, tz):
                return datetime.now(tz) + timedelta(hours=2)
        monkeypatch.setattr(service, "datetime", Later)
    else:
        original = service.native.access_context
        def changed(*args):
            context, access = original(*args)
            context["revision_id" if fault == "parent" else "source_epoch"] = "rev:new" if fault == "parent" else context["source_epoch"] + 1
            return context, access
        monkeypatch.setattr(service.native, "access_context", changed)
    before = len(lane.repo.head_events(SPACE_ID))
    response = confirm(lane, packet)
    assert response.status_code in (409, 422), response.text
    expected = {"expiry": "candidate_review_expired", "binding": "candidate_binding_changed",
                "parent": "candidate_parent_stale", "epoch": "candidate_source_authority_stale"}
    if fault in expected:
        assert response.json()["detail"]["code"] == expected[fault]
    assert len(lane.repo.head_events(SPACE_ID)) == before
    assert lane.repo.get_publication_receipt(SPACE_ID, packet["envelope"]["prepared_change_id"]) is None


def test_confirmation_authentication_precedes_owner_io(lane, monkeypatch):
    from apps.live_control_server.services.agent_graph_auth import native_graph_gm_dependency, NativeGraphPrincipal
    packet = confirmation(lane)
    monkeypatch.setattr(service.native, "repository", lambda: pytest.fail("unauthorized owner access"))
    assert lane.client.post("/api/live/extract-promote/native-confirm", json=packet).status_code == 401
    lane.app.dependency_overrides[native_graph_gm_dependency] = lambda: NativeGraphPrincipal(
        subject="player", role="player", auth_method="local_operator")
    assert confirm(lane, packet).status_code == 403


@pytest.mark.parametrize("fault", ["missing", "corrupt", "epoch_race"])
def test_first_commit_requires_current_core_source_opening(lane, monkeypatch, fault):
    from dataclasses import replace
    packet = confirmation(lane)
    before = len(lane.repo.head_events(SPACE_ID))
    if fault == "missing":
        lane.repo._native_records.clear()
    elif fault == "corrupt":
        _, access = service.native.access_context(lane.repo, SPACE_ID)
        view_type = type(access.source_view)
        original = view_type.get_native_text_source
        def corrupt(self, *args, **kwargs):
            return replace(original(self, *args, **kwargs), body_bytes=b"tampered")
        monkeypatch.setattr(view_type, "get_native_text_source", corrupt)
    else:
        original = service.open_admitted_native_text
        def race(*args):
            opened = original(*args)
            view = lane.repo.open_native_source_view(SPACE_ID)
            monkeypatch.setattr(lane.repo, "open_native_source_view", lambda _: SimpleNamespace(epoch=view.epoch + 1))
            return opened
        monkeypatch.setattr(service, "open_admitted_native_text", race)
    response = confirm(lane, packet)
    assert response.status_code == 409, response.text
    assert ("candidate_support_unavailable" if fault == "missing" else
            "candidate_source_authority_changed" if fault == "epoch_race" else
            "native_text_source_access_integrity_error") in response.text
    assert len(lane.repo.head_events(SPACE_ID)) == before


def test_committed_recovery_survives_expiry_new_head_and_unavailable_sources(lane, monkeypatch):
    from datetime import timedelta
    packet = confirmation(lane)
    first = confirm(lane, packet)
    assert first.status_code == 200, first.text
    # Advance the service clock; replay the identical original signed packet.
    class Later(datetime):
        @classmethod
        def now(cls, tz):
            return datetime.now(tz) + timedelta(hours=2)
    monkeypatch.setattr(service, "datetime", Later)
    raw = b"A later unrelated source."
    publish_native_text_source_evidence(repository=lane.repo, domain_contract=lane.domain,
        semantic_profile=lane.profile, request=NativeTextSourceAdmissionV1(
            space_id=SPACE_ID, admission_id="later-source",
            expected_parent_revision_id=lane.repo.get_head(SPACE_ID).head_revision_id,
            created_at=datetime.now(UTC), body_text=raw.decode(), expected_body_sha256=sha256(raw).hexdigest(),
            source_classification="dungeonbuddy.source:session_recap", authority="primary",
            visibility=META["visibility"], spans=[dict(client_ref="context", evidence_role="context",
                start_byte=0, end_byte=len(raw), expected_slice_sha256=sha256(raw).hexdigest())]))
    lane.repo._native_records.clear()
    monkeypatch.setattr(service, "load_reviewable_extraction_data", lambda *_: pytest.fail("APP run reload"))
    monkeypatch.setattr(service.sources, "get_source_markdown", lambda **_: pytest.fail("APP source reload"))
    monkeypatch.setattr(service.native, "access_context", lambda *_: pytest.fail("current source view on recovery"))
    before = len(lane.repo.head_events(SPACE_ID))
    retry = confirm(lane, packet)
    assert retry.status_code == 200, retry.text
    assert retry.json()["recovered"] and retry.json()["result"] == first.json()["result"]
    assert len(lane.repo.head_events(SPACE_ID)) == before


def test_committed_child_unavailable_and_corrupt_never_report_success(lane, monkeypatch):
    from dungeonmind.domain.errors import PersistenceUnavailableError
    packet = confirmation(lane)
    first = confirm(lane, packet)
    assert first.status_code == 200, first.text
    child_id = first.json()["result"]["child_revision_id"]
    original = lane.repo.get_revision
    def unavailable(space, revision):
        if revision == child_id:
            raise PersistenceUnavailableError("fixture child offline")
        return original(space, revision)
    monkeypatch.setattr(lane.repo, "get_revision", unavailable)
    failed = confirm(lane, packet)
    assert failed.status_code == 503, failed.text
    assert failed.json()["detail"]["code"] == "native_recap_commit_verification_unavailable"
    assert failed.json()["detail"]["committed"] and failed.json()["detail"]["retry_original_packet"]
    monkeypatch.setattr(lane.repo, "get_revision", original)
    assert confirm(lane, packet).json()["result"] == first.json()["result"]
    # Receipt presence alone cannot establish successful exact-child verification.
    monkeypatch.setattr(lane.repo, "get_revision", lambda space, revision: None if revision == child_id else original(space, revision))
    failed = confirm(lane, packet)
    assert failed.status_code == 409, failed.text
    assert failed.json()["detail"]["code"] == "native_recap_committed_integrity_failure"
    assert failed.json()["detail"]["committed"] and not failed.json()["detail"]["retry_original_packet"]


def test_unknown_commit_outcome_retries_original_packet_without_second_effect(lane, monkeypatch):
    packet = confirmation(lane)
    publish = lane.repo.publish_prospective_publication
    lookup = lane.repo.get_prospective_publication
    state = {"written": False, "calls": 0}
    def interrupted(*args, **kwargs):
        state["calls"] += 1
        publish(*args, **kwargs)
        state["written"] = True
        raise TimeoutError("fixture lost acknowledgement")
    def unavailable(*args, **kwargs):
        if state["written"]:
            raise TimeoutError("fixture receipt temporarily unavailable")
        return lookup(*args, **kwargs)
    monkeypatch.setattr(lane.repo, "publish_prospective_publication", interrupted)
    monkeypatch.setattr(lane.repo, "get_prospective_publication", unavailable)
    before = len(lane.repo.head_events(SPACE_ID))
    failed = confirm(lane, packet)
    assert failed.status_code == 503, failed.text
    detail = failed.json()["detail"]
    assert detail["code"] == "native_recap_commit_outcome_unknown"
    assert detail["retry_original_packet"] and detail["committed"] is None
    assert detail["publication_id"] == packet["envelope"]["prepared_change_id"]
    monkeypatch.setattr(lane.repo, "get_prospective_publication", lookup)
    recovered = confirm(lane, packet)
    assert recovered.status_code == 200, recovered.text
    assert recovered.json()["recovered"] and state["calls"] == 2  # exact-ID replay, one durable effect
    assert len(lane.repo.head_events(SPACE_ID)) == before + 1


@pytest.mark.parametrize("fault,code", [
    ("producer", "candidate_review_invalid"), ("parent", "candidate_review_invalid"),
    ("meaning", "native_recap_prepared_invalid"),
])
def test_authenticated_packet_still_obeys_native_identity_and_WK_integrity(lane, fault, code):
    from dataclasses import replace
    packet = confirmation(lane)
    prepared = transport.decode_prepared(packet["prepared"])
    if fault == "producer":
        prepared = replace(prepared, producer="another:producer")
    elif fault == "parent":
        prepared = replace(prepared, expected_parent_revision_id="rev:foreign")
    else:
        op = prepared.prepared_operations[0]
        changed = replace(op.facts[0], value=service.wk.LiteralFactValue("changed meaning"))
        prepared = replace(prepared, prepared_operations=(replace(op, facts=(changed, *op.facts[1:])),
            *prepared.prepared_operations[1:]))
    packet["prepared"] = transport.encode_prepared(prepared)
    packet["envelope"]["prepared_digest"] = transport.digest(packet["prepared"])
    packet["token"] = service.sign_publication_intent(packet["envelope"])
    before = len(lane.repo.head_events(SPACE_ID))
    response = confirm(lane, packet)
    assert response.status_code == 409, response.text
    assert response.json()["detail"]["code"] == code
    assert len(lane.repo.head_events(SPACE_ID)) == before


def test_different_review_cannot_reuse_committed_publication_id(lane, monkeypatch):
    monkeypatch.setattr(service, "uuid4", lambda: "fixture-same-id")
    first = confirmation(lane)
    lane.body["selections"][0]["facts"].append(dict(field="description", metadata=copy.deepcopy(META)))
    second = confirmation(lane)
    assert first["envelope"]["prepared_change_id"] == second["envelope"]["prepared_change_id"]
    committed = confirm(lane, first)
    assert committed.status_code == 200, committed.text
    before = len(lane.repo.head_events(SPACE_ID))
    conflict = confirm(lane, second)
    assert conflict.status_code == 409, conflict.text
    assert conflict.json()["detail"]["code"] == "native_recap_commit_conflict"
    assert not conflict.json()["detail"]["retry_original_packet"]
    assert len(lane.repo.head_events(SPACE_ID)) == before
