"""Authenticated review boundary and real WK/Core preparation, with read owners stubbed.

Core admission/extension/opening are real in memory; APP reads are stubbed. No DB/provider IO.
"""

from datetime import timedelta
from pathlib import Path
from pydantic import ValidationError
from apps.live_control_server.models.native_recap_preparation import (
    NativeRecapReviewEnvelope, RecordSelection, SelectedDescriptionExtent, SelectedFact,
)
from apps.live_control_server.services.graph_object_authoring_prepare import decode_publication_intent

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
from application_state.source.service import get_source_markdown as read_actual_source
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
def lane(monkeypatch, tmp_path, request):
    monkeypatch.setenv("DMB_AGENT_GRAPH_AUTH_MODE", "local_operator")
    monkeypatch.setenv("DMB_AGENT_GRAPH_AUTH_ENVIRONMENT", "local")
    monkeypatch.setenv("DMB_AGENT_GRAPH_LOCAL_OPERATOR_TOKEN", TOKEN)
    monkeypatch.setenv("DMB_GRAPH_REVIEW_PREPARE_BINDING_KEY", "synthetic-native-recap-review-key")
    seed = _repository(evidence=False, v3=getattr(request, "param", None) != "source_order_closed")
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
    source_order = getattr(request, "param", None) in {"source_order", "source_order_closed"}
    if source_order:
        text = ("An arrival happened. A discussion happened. Each occurred before a departure. "
                "Their relative order is not stated. Pippa is a person.\r\n\r\n"
                "The traveller brought a lantern.\r\n\r\nAnother unrelated episode.\r\n")
    digest = sha256(text.encode()).hexdigest()
    spans = build_source_span_index_for_text(source_artifact_id=source_id, content_sha256=digest, text=text)
    evidence = [dict(source_ref_id="source:fixture", source_artifact_id=source_id,
                     source_span_ref_id=spans.spans[0].source_span_id,
                     can_open_source=True, can_highlight_span=True,
                     evidence_role="source_evidence", anchor_quotes=[text.splitlines()[0] if source_order else "A traveller met Pippa"])]
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


def historical_context(lane, history):
    if history == "absent":
        lane.run.lineage = {"generation": {"retained": True}}
    elif history == "older_binding":
        lane.run.lineage["world_campaign_ingest_context"]["binding_version"] -= 1
    elif history == "foreign_binding":
        lane.run.lineage["world_campaign_ingest_context"].update(
            managed_world_id="foreign-managed", native_world_id="foreign-native")


@pytest.mark.parametrize("history", ["current", "absent", "older_binding"])
@pytest.mark.parametrize("fault,expected", [
    ("revision", "candidate_run_changed"), ("digest", "candidate_bytes_changed"),
    ("uuid", "candidate_admission_mismatch"), ("scope", "candidate_source_mismatch"),
    ("binding", "candidate_admission_mismatch"), ("unavailable", "candidate_source_not_admitted"),
    ("source", "candidate_source_mismatch"), ("parent", "candidate_parent_stale"),
    ("quote", "run_not_promotable"), ("epoch", "candidate_source_authority_stale"), ("dangling", "selected_edge_endpoint_held"),
    ("source_world", "candidate_source_mismatch"),
    ("descriptor_world", "candidate_source_mismatch"),
    ("admission_world", "candidate_admission_mismatch"),
    ("admission_digest", "candidate_admission_mismatch"),
    ("source_digest", "candidate_source_mismatch"),
    ("session", "candidate_source_mismatch"),
    ("candidate_source", "candidate_document_scope_mismatch"),
    ("candidate_session", "candidate_document_scope_mismatch"),
])
def test_exact_owner_and_review_refusals(lane, fault, expected, history):
    historical_context(lane, history)
    generation_history = copy.deepcopy(lane.run.lineage)
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
    elif fault == "source_world":
        lane.source.world_id = "foreign-world"
    elif fault == "descriptor_world":
        lane.artifact.world_id = "foreign-world"
    elif fault == "admission_world":
        lane.admitted.native_world_id = "foreign-world"
    elif fault == "admission_digest":
        lane.admitted.app_body_sha256 = "0" * 64
    elif fault == "source_digest":
        lane.source.content_sha256 = "0" * 64
    elif fault == "session":
        lane.source.session_id = "session-9"
    elif fault == "candidate_source":
        lane.payload["source_artifact_ids"] = ["artifact:foreign"]
        lane.refresh()
    elif fault == "candidate_session":
        lane.payload["session_id"] = "session-9"
        lane.refresh()
    before = copy.deepcopy({key: value for key, value in lane.repo.__dict__.items() if key != "_lock"})
    response = lane.post()
    assert response.status_code in (409, 422), response.text
    assert expected in response.text
    assert {key: value for key, value in lane.repo.__dict__.items() if key != "_lock"} == before
    assert lane.run.lineage == generation_history


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


@pytest.mark.parametrize("history", ["current", "absent", "older_binding", "foreign_binding"])
def test_ordinary_confirmation_commits_once_and_selected_query_opens_support(lane, history):
    historical_context(lane, history)
    def retained():
        return (vars(lane.run), vars(lane.source), vars(lane.artifact),
                lane.data.source_bytes, lane.data.candidate_bytes, lane.data.span_index)
    original = copy.deepcopy(retained())
    from apps.live_control_server.services.agent_graph_auth import NativeGraphPrincipal
    from apps.live_control_server.services.native_graph_reads import prepare_query, read_selected
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
    assert retained() == original


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


@pytest.mark.parametrize("fixture", ["lane", "world_lane"])
def test_committed_recovery_survives_expiry_new_head_and_unavailable_sources(request, fixture, monkeypatch):
    lane = request.getfixturevalue(fixture)
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
    monkeypatch.setattr(service.world_admission, "get_native_world_source_status", lambda *a, **k: pytest.fail("APP workspace reload on recovery"))
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


@pytest.fixture
def world_lane(lane, application_state_dsn, monkeypatch):
    """Real committed APP page/source + existing World admission owner + WK/Core."""
    from tests.test_demo_j1_native_world_source_admission import _committed_source
    from tests.application_state.world_catalog_fixtures import change_binding
    from apps.live_control_server.services.source_artifact_registry import create_source_artifact_from_workspace_document
    from apps.live_control_server.services.workspace_document_registry import get_committed_page_snapshot
    monkeypatch.setattr(service.sources, "get_source_markdown", read_actual_source)
    world, record = _committed_source(lane.tmp_path, markdown=lane.text)
    change_binding(world.world_id, native_world_id=SPACE_ID, binding_version=3)
    artifact = create_source_artifact_from_workspace_document(lane.tmp_path,
        document_id=record.document_id, expected_revision=record.revision)
    source = read_actual_source(source_artifact_id=artifact.source_artifact_id,
                               content_sha256=artifact.content_sha256)
    lane.text = source.markdown
    lane.data.source_bytes = source.markdown.encode("utf-8")
    monkeypatch.setattr(service.world_admission, "_repository", lambda: lane.repo)
    admitted = service.world_admission.admit_native_world_source(lane.tmp_path,
        record.document_id, expected_revision=record.revision,
        expected_body_sha256=source.content_sha256)
    first_end = len(lane.text.splitlines(keepends=True)[0].encode())
    extension = publish_native_source_evidence_extension(
        repository=lane.repo, domain_contract=lane.domain, semantic_profile=lane.profile,
        audience_labels=("dungeonbuddy.visibility:gm",),
        request=NativeSourceEvidenceExtensionV1(
            space_id=SPACE_ID, extension_id="world-fixture-support",
            original_admission_id=admitted.admission_id,
            source_artifact_id=admitted.source_artifact_id,
            source_revision_id=admitted.source_revision_id,
            expected_body_sha256=admitted.body_sha256, created_at=datetime.now(UTC),
            expected_parent_revision_id=lane.repo.get_head(SPACE_ID).head_revision_id,
            expected_source_authority_epoch=lane.repo.open_native_source_view(SPACE_ID).epoch,
            spans=[dict(client_ref="first", evidence_role="support", start_byte=0,
                end_byte=first_end, expected_slice_sha256=sha256(lane.text.encode()[:first_end]).hexdigest())]))
    evidence_id = extension.bindings[0].evidence_ref_id
    lane.world, lane.record = world, record
    lane.source, lane.artifact, lane.world_admitted = source, artifact, admitted
    lane.data.source_artifact = artifact
    lane.run.source_domain, lane.run.campaign_id, lane.run.session_id = "worldbuilding", world.world_id, None
    lane.run.lineage = {"generation": {"historical": True}}
    spans = build_source_span_index_for_text(source_artifact_id=artifact.source_artifact_id,
                                            content_sha256=artifact.content_sha256, text=lane.text)
    lane.data.span_index = spans
    lane.payload.update(campaign_id=world.world_id, session_id=None,
                        source_artifact_ids=[artifact.source_artifact_id])
    for kind in ("nodes", "edges", "beats", "ignored_items", "deferred_items"):
        for row in lane.payload[kind]:
            for ref in row["evidence_refs"]:
                ref.update(source_artifact_id=artifact.source_artifact_id,
                           source_span_ref_id=spans.spans[0].source_span_id)
    lane.refresh()
    selections = copy.deepcopy(lane.body["selections"])
    selections = [s for s in selections if s["kind"] != "beat"]
    for selection in selections:
        for fact in selection.get("facts", []):
            fact["metadata"]["evidence_ref_ids"] = [evidence_id]
        if selection.get("metadata"):
            selection["metadata"]["evidence_ref_ids"] = [evidence_id]
    lane.body.update(managed_world_id=world.world_id,
        workspace_document_id=record.document_id, workspace_document_revision=record.revision,
        expected_parent_revision_id=lane.repo.get_head(SPACE_ID).head_revision_id,
        expected_source_authority_epoch=lane.repo.open_native_source_view(SPACE_ID).epoch,
        selections=selections)
    del lane.body["campaign_id"], lane.body["source_admission_run_id"]
    monkeypatch.setattr(service.admission, "inspect", lambda *_: pytest.fail("recap source owner used for World source"))
    lane.evidence_id = evidence_id
    lane.saved_page = get_committed_page_snapshot(lane.tmp_path, record.document_id)
    return lane


def test_current_worldbuilding_review_uses_same_native_graph_and_world_scope(world_lane):
    from apps.live_control_server.services.native_graph_reads import prepare_query, read_selected
    from apps.live_control_server.services.agent_graph_auth import NativeGraphPrincipal
    from application_state.agent_conversation.native_plan_assertions import NativePlanAssertionReadAuthorizedV1
    from apps.live_control_server.services.workspace_document_registry import get_committed_page_snapshot
    x = world_lane
    before = copy.deepcopy({key: value for key, value in x.repo.__dict__.items() if key != "_lock"})
    event_count = len(x.repo.head_events(SPACE_ID))
    packet = confirmation(x)
    assert {key: value for key, value in x.repo.__dict__.items() if key != "_lock"} == before
    assert packet["envelope"]["producer"] == "dungeonbuddy:reviewed-worldbuilding"
    assert packet["envelope"]["purpose"] == "dmb_native_worldbuilding_confirm_v1"
    prepared = transport.decode_prepared(packet["prepared"])
    assert all(not f.metadata.scope for op in prepared.prepared_operations[:-1] for f in op.facts)
    assert not prepared.prepared_operations[-1].metadata.scope
    first = confirm(x, packet)
    assert first.status_code == 200, first.text
    assert confirm(x, packet).json()["result"] == first.json()["result"]
    assert len(x.repo.head_events(SPACE_ID)) == event_count + 1
    principal = NativeGraphPrincipal(subject="test:gm", role="gm", auth_method="local_operator")
    binding = SimpleNamespace(managed_world_id=x.world.world_id, **x.bound)
    context, query = prepare_query(x.world.world_id, "new", principal, repository=x.repo,
        resolve_binding=lambda _: binding, scope_mode="world")
    assert query.assertion_matches
    grant = NativePlanAssertionReadAuthorizedV1(event_id=uuid4(), sequence=0,
        provider_attempt_id=uuid4(), query_sha256=query.sha256,
        assertion_ids=tuple(match.assertion_id for match in query.assertion_matches))
    reads, unavailable = read_selected(context, grant, principal)
    assert reads and not unavailable
    assert all(r.spans[0].evidence_ref_id == x.evidence_id for r in reads)
    assert all(r.spans[0].text == x.text.splitlines(keepends=True)[0] for r in reads)
    assert get_committed_page_snapshot(x.tmp_path, x.record.document_id) == x.saved_page
    assert x.data.source_bytes == x.source.markdown.encode()


@pytest.mark.parametrize("fault,code", [
    ("old_revision", "source_revision_changed"),
    ("edited_page", "source_revision_changed"),
    ("unadmitted", "candidate_source_not_admitted"),
    ("source_world", "candidate_source_mismatch"),
    ("missing_document", "candidate_workspace_source_required"),
    ("candidate_bytes", "candidate_bytes_changed"),
    ("wrong_support", "candidate_support_source_mismatch"),
    ("parent", "candidate_parent_stale"),
    ("epoch", "candidate_source_authority_stale"),
])
def test_worldbuilding_review_refuses_without_mutation(world_lane, monkeypatch, fault, code):
    x = world_lane
    if fault == "old_revision":
        x.data.source_artifact = x.artifact.model_copy(update={"workspace_document_revision": x.record.revision - 1})
        x.body["workspace_document_revision"] -= 1
    elif fault == "edited_page":
        from apps.live_control_server.services.tiptap_markdown_write import (
            TiptapMarkdownWritePrepareRequest, TiptapMarkdownWriteCommitRequest,
            prepare_tiptap_markdown_write, commit_tiptap_markdown_write,
        )
        updated = x.source.markdown + "\nNew authored text must be preserved.\n"
        prepared = prepare_tiptap_markdown_write(root=x.tmp_path,
            request=TiptapMarkdownWritePrepareRequest(document_id=x.record.document_id,
                markdown=updated, expected_revision=x.record.revision, write_mode="authoring"))
        commit_tiptap_markdown_write(root=x.tmp_path,
            request=TiptapMarkdownWriteCommitRequest(document_id=x.record.document_id,
                markdown=updated, expected_revision=x.record.revision, write_mode="authoring",
                writer_confirm_token=prepared.writer_confirm_token))
    elif fault == "unadmitted":
        missing = x.world_admitted.model_copy(update={"state": "pending"})
        monkeypatch.setattr(service.world_admission, "get_native_world_source_status", lambda *a, **k: missing)
    elif fault == "source_world":
        x.data.source_artifact = x.artifact.model_copy(update={"world_id": "another-world"})
    elif fault == "missing_document":
        x.data.source_artifact = x.artifact.model_copy(update={"workspace_document_id": None})
    elif fault == "candidate_bytes":
        x.body["candidate_sha256"] = "0" * 64
    elif fault == "wrong_support":
        x.body["selections"][0]["facts"][0]["metadata"]["evidence_ref_ids"] = [x.support_ids["first"]]
    elif fault == "parent":
        x.body["expected_parent_revision_id"] = "rev:stale"
    elif fault == "epoch":
        x.body["expected_source_authority_epoch"] += 1
    before = x.repo.get_head(SPACE_ID)
    response = x.post()
    assert response.status_code == 409, response.text
    assert response.json()["detail"]["code"] == code
    assert x.repo.get_head(SPACE_ID) == before


@pytest.mark.parametrize("as_status", [True, False])
def test_world_source_owner_unavailability_preserves_failure_status(world_lane, monkeypatch, as_status):
    def unavailable(*args, **kwargs):
        if as_status:
            return world_lane.world_admitted.model_copy(update={"state": "pending",
                "code": "authority_unavailable", "message": "offline"})
        raise service.world_admission.NativeWorldSourceAdmissionError("authority_unavailable", "offline", status_code=503)
    monkeypatch.setattr(service.world_admission, "get_native_world_source_status", unavailable)
    response = world_lane.post()
    assert response.status_code == 503 and response.json()["detail"]["code"] == "authority_unavailable"


def test_recap_cannot_be_broadened_by_omitting_campaign(lane):
    del lane.body["campaign_id"], lane.body["source_admission_run_id"]
    lane.body.update(workspace_document_id="not-a-recap-selector", workspace_document_revision=1)
    before = lane.repo.get_head(SPACE_ID)
    response = lane.post()
    assert response.status_code == 409 and response.json()["detail"]["code"] == "candidate_scope_mismatch"
    assert lane.repo.get_head(SPACE_ID) == before


def test_worldbuilding_review_cannot_relabel_signed_recap_envelope(lane):
    packet = confirmation(lane)
    packet["envelope"]["producer"] = "dungeonbuddy:reviewed-worldbuilding"
    packet["envelope"]["purpose"] = "dmb_native_worldbuilding_confirm_v1"
    packet["token"] = service.sign_publication_intent(packet["envelope"])
    assert confirm(lane, packet).status_code == 422


def test_worldbuilding_request_cannot_inject_campaign_selector(world_lane):
    world_lane.body.update(campaign_id="foreign", source_admission_run_id="recap")
    assert world_lane.post().status_code == 422


@pytest.mark.parametrize("field,value", [("workspace_document_id", "another-document"),
                                          ("workspace_document_revision", 999)])
def test_worldbuilding_request_must_match_saved_typed_source(world_lane, field, value):
    world_lane.body[field] = value
    response = world_lane.post()
    assert response.status_code == 409 and response.json()["detail"]["code"] == "candidate_workspace_source_mismatch"


def test_worldbuilding_first_confirmation_refuses_edit_after_preparation(world_lane):
    from apps.live_control_server.services.tiptap_markdown_write import (
        TiptapMarkdownWritePrepareRequest, TiptapMarkdownWriteCommitRequest,
        prepare_tiptap_markdown_write, commit_tiptap_markdown_write,
    )
    from apps.live_control_server.services.workspace_document_registry import get_committed_page_snapshot
    x = world_lane
    packet = confirmation(x)
    updated = x.source.markdown + "\nNew authored text must be preserved.\n"
    edit = prepare_tiptap_markdown_write(root=x.tmp_path,
        request=TiptapMarkdownWritePrepareRequest(document_id=x.record.document_id,
            markdown=updated, expected_revision=x.record.revision, write_mode="authoring"))
    commit_tiptap_markdown_write(root=x.tmp_path,
        request=TiptapMarkdownWriteCommitRequest(document_id=x.record.document_id,
            markdown=updated, expected_revision=x.record.revision, write_mode="authoring",
            writer_confirm_token=edit.writer_confirm_token))
    current_page = get_committed_page_snapshot(x.tmp_path, x.record.document_id)
    head = x.repo.get_head(SPACE_ID)
    epoch = x.repo.open_native_source_view(SPACE_ID).epoch
    response = confirm(x, packet)
    assert response.status_code == 409 and response.json()["detail"]["code"] == "source_revision_changed"
    assert x.repo.get_head(SPACE_ID) == head and x.repo.open_native_source_view(SPACE_ID).epoch == epoch
    assert x.repo.get_publication_receipt(SPACE_ID, packet["envelope"]["prepared_change_id"]) is None
    assert get_committed_page_snapshot(x.tmp_path, x.record.document_id) == current_page


def test_existing_recap_envelope_wire_shape_has_no_new_world_fields(lane):
    packet = confirmation(lane)
    assert set(packet["envelope"]["review"]) == set(lane.body)
    assert "workspace_document_id" not in packet["envelope"]["review"]
    assert confirm(lane, packet).status_code == 200


# Exact retained-description selection through the existing publication boundary.
PREFIX = "  A traveller met Pippa near the towér."
DESCRIPTION = PREFIX + " The traveller then bought a castle."


def extent_fact(value=DESCRIPTION, start=0, end=None):
    end = len(PREFIX.encode()) if end is None else end
    metadata = copy.deepcopy(META)
    metadata.setdefault("evidence_ref_ids", ["ev:synthetic-selector-shape-test"])
    return {
        "field": "description",
        "extent": {"start_byte": start, "end_byte": end,
                   "expected_slice_sha256": sha256(value.encode()[start:end]).hexdigest()},
        "metadata": metadata,
    }


def select_extent(x):
    x.payload["nodes"][0]["description"] = DESCRIPTION
    x.refresh()
    x.body["selections"] = [{"kind": "node", "record_id": "new", "action": "create",
                              "facts": [extent_fact()]}]
    if hasattr(x, "evidence_id"):
        x.body["selections"][0]["facts"][0]["metadata"]["evidence_ref_ids"] = [x.evidence_id]


SECOND_FRAGMENT = "The traveller brought a lantern."
DISJOINT_DESCRIPTION = PREFIX + " Unsupported castle purchase. " + SECOND_FRAGMENT


def select_disjoint_extents(x, *, reverse=False):
    # The two genuine statements have independently opened source support.
    lines = x.text.splitlines(keepends=True)
    start = len(''.join(lines[:2]).encode())
    end = start + len(lines[2].encode())
    admitted = x.world_admitted if hasattr(x, "world_admitted") else x.admitted
    if hasattr(x, "world_admitted"):
        extension = publish_native_source_evidence_extension(
            repository=x.repo, domain_contract=x.domain, semantic_profile=x.profile,
            audience_labels=("dungeonbuddy.visibility:gm",),
            request=NativeSourceEvidenceExtensionV1(
                space_id=SPACE_ID, extension_id="disjoint-second-source-support",
                original_admission_id=admitted.admission_id,
                source_artifact_id=admitted.source_artifact_id,
                source_revision_id=admitted.source_revision_id,
                expected_body_sha256=sha256(x.text.encode()).hexdigest(),
                created_at=datetime.now(UTC),
                expected_parent_revision_id=x.repo.get_head(SPACE_ID).head_revision_id,
                expected_source_authority_epoch=x.repo.open_native_source_view(SPACE_ID).epoch,
                spans=[dict(client_ref="second", evidence_role="support", start_byte=start,
                            end_byte=end, expected_slice_sha256=sha256(x.text.encode()[start:end]).hexdigest())]))
        second_support = extension.bindings[0].evidence_ref_id
    else:
        second_support = x.support_ids["second"]
    ref = copy.deepcopy(x.payload["nodes"][0]["evidence_refs"][0])
    ref.update(source_span_ref_id=next(p.source_span_id for p in x.data.span_index.spans
                                      if p.start_line == 3), anchor_quotes=[SECOND_FRAGMENT])
    x.payload["nodes"][0]["evidence_refs"].append(ref)
    x.payload["nodes"][0]["description"] = DISJOINT_DESCRIPTION
    left = extent_fact(DISJOINT_DESCRIPTION)
    right = extent_fact(DISJOINT_DESCRIPTION, start=len(DISJOINT_DESCRIPTION.encode()) - len(SECOND_FRAGMENT.encode()),
                        end=len(DISJOINT_DESCRIPTION.encode()))
    left["metadata"]["evidence_ref_ids"] = [x.evidence_id if hasattr(x, "evidence_id") else x.support_ids["first"]]
    right["metadata"]["evidence_ref_ids"] = [second_support]
    x.body["selections"] = [{"kind": "node", "record_id": "new", "action": "create",
                            "facts": [right, left] if reverse else [left, right]}]
    x.body["expected_parent_revision_id"] = x.repo.get_head(SPACE_ID).head_revision_id
    x.body["expected_source_authority_epoch"] = x.repo.open_native_source_view(SPACE_ID).epoch
    x.refresh()


@pytest.mark.parametrize("fixture", ["lane", "world_lane"])
@pytest.mark.parametrize("reverse", [False, True])
@pytest.mark.parametrize("action", ["create", "use_existing"])
def test_disjoint_extents_commit_separate_literals_provenance_and_exact_held_union(request, fixture, reverse, action):
    x = request.getfixturevalue(fixture)
    select_disjoint_extents(x, reverse=reverse)
    if action == "use_existing":
        x.body["selections"][0].update(action=action, entity_id="ent:pippa")
    original = copy.deepcopy(x.payload)
    before = x.repo.get_head(SPACE_ID)
    response = x.post()
    assert response.status_code == 200, response.text
    packet = response.json()
    assert x.repo.get_head(SPACE_ID) == before
    record = packet["records"][0]
    assert "selected_description_extent" not in record
    traces = record["selected_description_extents"]
    assert [t["start_byte"] for t in traces] == [f["extent"]["start_byte"] for f in x.body["selections"][0]["facts"]]
    assert record["held_description_extents"] == [{"start_byte": len(PREFIX.encode()),
        "end_byte": len(DISJOINT_DESCRIPTION.encode()) - len(SECOND_FRAGMENT.encode())}]
    assert "description" in record["unselected_fields"] and record["selected_fields"] == []
    prepared = service.transport.decode_prepared(packet["prepared"])
    expected = [SECOND_FRAGMENT, PREFIX] if reverse else [PREFIX, SECOND_FRAGMENT]
    assert [f.value.value for f in prepared.prepared_operations[0].facts] == expected
    assert [f.client_op_id for f in prepared.prepared_operations[0].facts] == ["record:0.field:0", "record:0.field:1"]
    confirmation = {k: packet[k] for k in ("envelope", "prepared", "token")}
    committed = confirm(x, confirmation)
    assert committed.status_code == 200, committed.text
    _, access = service.native.access_context(x.repo, SPACE_ID)
    results = committed.json()["result"]["assertion_results"]
    assert len(results) == 2
    for result, value, trace in zip(results, expected, traces):
        actual = service.native.assertion_contract(access.parsed.assertions_by_id[result["durable_assertion_id"]]).model_dump(mode="json")
        assert actual["value"] == {"kind": "literal", "value": value}
        context = next(m["payload"] for m in actual["metadata"]["domain_metadata"] if m["schema"] == service.WORLD_CONTEXT)
        assert context[service.DESCRIPTION_SELECTION] == trace
    assert x.payload == original
    assert confirm(x, confirmation).json()["result"] == committed.json()["result"]


@pytest.mark.parametrize("ranges", [[(0, 10), (9, 20)], [(0, 10), (0, 10)], [(0, 20), (5, 10)]])
def test_overlapping_description_extents_rejected(ranges):
    with pytest.raises(ValidationError, match="overlapping description extents"):
        RecordSelection.model_validate({"kind": "node", "record_id": "new", "action": "create",
            "facts": [extent_fact(start=a, end=b) for a, b in ranges]})


def test_adjacent_proper_extents_cannot_jointly_accept_whole_description(lane):
    select_extent(lane)
    lane.body["selections"][0]["facts"].append(extent_fact(start=len(PREFIX.encode()), end=len(DESCRIPTION.encode())))
    head = lane.repo.get_head(SPACE_ID)
    response = lane.post()
    assert response.status_code == 409 and "candidate_description_extents_cover_whole_field" in response.text
    assert lane.repo.get_head(SPACE_ID) == head


def test_old_and_new_selector_variants_are_unambiguous():
    fact = extent_fact()
    fact.pop("extent")
    whole = RecordSelection.model_validate({"kind": "node", "record_id": "new",
        "action": "create", "facts": [fact]})
    assert isinstance(whole.facts[0], SelectedFact)
    assert "extent" not in whole.model_dump()["facts"][0]
    partial = RecordSelection.model_validate({"kind": "node", "record_id": "new",
        "action": "create", "facts": [extent_fact()]})
    assert isinstance(partial.facts[0], SelectedDescriptionExtent)


@pytest.mark.parametrize("change", [
    {"start_byte": True}, {"end_byte": "4"}, {"start_byte": -1},
    {"start_byte": 5, "end_byte": 5}, {"end_byte": 0},
    {"unexpected": 1}, {"expected_slice_sha256": "not-a-digest"},
])
def test_invalid_extent_shape_is_refused(change):
    fact = extent_fact()
    fact["extent"].update(change)
    with pytest.raises(ValidationError):
        RecordSelection.model_validate({"kind": "node", "record_id": "new",
            "action": "create", "facts": [fact]})


@pytest.mark.parametrize("field", ["label", "node_type", "summary", "title", "session_actions"])
def test_extent_cannot_clip_other_fields(field):
    fact = extent_fact()
    fact["field"] = field
    with pytest.raises(ValidationError):
        RecordSelection.model_validate({"kind": "node", "record_id": "new",
            "action": "create", "facts": [fact]})


@pytest.mark.parametrize("kind", ["beat", "edge"])
def test_extent_requires_node_and_cannot_clip_source_beats(kind):
    with pytest.raises(ValidationError):
        RecordSelection.model_validate({"kind": kind, "record_id": "new",
            "action": "create", "facts": [extent_fact()]})


@pytest.mark.parametrize("second", ["whole", "same"])
def test_existing_duplicate_field_rule_limits_one_description_choice(second):
    fact = extent_fact()
    other = ({"field": "description", "metadata": extent_fact()["metadata"]} if second == "whole"
             else copy.deepcopy(fact))
    with pytest.raises(ValidationError, match="duplicate selected field|overlapping description extents"):
        RecordSelection.model_validate({"kind": "node", "record_id": "new",
            "action": "create", "facts": [fact, other]})


@pytest.mark.parametrize("domain", ["recap", "worldbuilding"])
def test_prechange_signed_envelopes_normalize_exactly(domain, monkeypatch):
    fixture = json.loads((Path(__file__).parent / "fixtures" /
        "native_review_envelopes_before_description_extents.json").read_text())["cases"][domain]
    monkeypatch.setenv("DMB_GRAPH_REVIEW_PREPARE_BINDING_KEY",
                       "synthetic-description-extent-legacy-test-key")
    normalized = NativeRecapReviewEnvelope.model_validate(fixture["envelope"]).model_dump(mode="json")
    assert normalized == fixture["envelope"]
    assert decode_publication_intent(fixture["token"], allow_expired_recovery=True) == normalized


@pytest.mark.parametrize("fixture", ["lane", "world_lane"])
def test_extent_commits_exact_bytes_and_owner_trace_without_accepting_whole_field(request, fixture):
    x = request.getfixturevalue(fixture)
    select_extent(x)
    fact = x.body["selections"][0]["facts"][0]
    fact["metadata"]["domain_metadata"] = [{"schema_term": service.WORLD_CONTEXT,
        "payload": {"source_qualification": "Meeting only; no castle purchase is established."}}]
    original = copy.deepcopy(x.payload)
    before = len(x.repo.head_events(SPACE_ID))
    response = x.post()
    assert response.status_code == 200, response.text
    packet = response.json()
    assert len(x.repo.head_events(SPACE_ID)) == before
    record = packet["records"][0]
    assert record["selected_fields"] == []
    assert "description" in record["unselected_fields"]
    assert record["held_description_extents"] == [{"start_byte": len(PREFIX.encode()),
                                                   "end_byte": len(DESCRIPTION.encode())}]
    trace = record["selected_description_extents"][0]
    assert trace == {
        "schema_version": "dmb_candidate_description_extent_v1", "run_id": x.run.run_id,
        "run_revision": 5, "candidate_sha256": x.body["candidate_sha256"],
        "record_id": "new", "field": "description", "start_byte": 0,
        "end_byte": len(PREFIX.encode()), "slice_sha256": sha256(PREFIX.encode()).hexdigest(),
        "whole_field_selected": False,
    }
    prepared = service.transport.decode_prepared(packet["prepared"])
    assert len(prepared.prepared_operations) == 1
    prepared_fact = prepared.prepared_operations[0].facts[0]
    assert prepared_fact.value.value == PREFIX
    confirm_packet = {k: packet[k] for k in ["envelope", "prepared", "token"]}
    committed = confirm(x, confirm_packet)
    assert committed.status_code == 200, committed.text
    _, access = service.native.access_context(x.repo, SPACE_ID)
    added_id = committed.json()["result"]["assertion_results"][0]["durable_assertion_id"]
    actual = service.native.assertion_contract(access.parsed.assertions_by_id[added_id]).model_dump(mode="json")
    assert actual["predicate"] == "dnd5e:summary"
    assert actual["value"] == {"kind": "literal", "value": PREFIX}
    assert actual["metadata"]["domain_metadata"] == [{"schema": service.WORLD_CONTEXT, "payload": {
        "source_qualification": "Meeting only; no castle purchase is established.",
        service.DESCRIPTION_SELECTION: trace}}]
    assert x.payload == original
    assert confirm(x, confirm_packet).json()["result"] == committed.json()["result"]


@pytest.mark.parametrize("fault,code", [
    ("bounds", "candidate_description_extent_bounds"),
    ("unicode", "candidate_description_extent_invalid_utf8"),
    ("digest", "candidate_description_extent_digest_changed"),
    ("blank", "candidate_description_extent_blank"),
    ("whole", "candidate_description_extent_must_be_partial"),
])
def test_extent_resolution_refuses_without_writes_or_fallback(lane, fault, code):
    select_extent(lane)
    extent = lane.body["selections"][0]["facts"][0]["extent"]
    if fault == "bounds":
        extent["end_byte"] = len(DESCRIPTION.encode()) + 1
    elif fault == "unicode":
        extent["end_byte"] = DESCRIPTION.encode().index("é".encode()) + 1
    elif fault == "digest":
        extent["expected_slice_sha256"] = "f" * 64
    elif fault == "blank":
        extent.update(end_byte=2, expected_slice_sha256=sha256(b"  ").hexdigest())
    else:
        extent.update(end_byte=len(DESCRIPTION.encode()),
                      expected_slice_sha256=sha256(DESCRIPTION.encode()).hexdigest())
    before = copy.deepcopy({k: v for k, v in lane.repo.__dict__.items() if k != "_lock"})
    response = lane.post()
    assert response.status_code == 409 and code in response.text
    assert {k: v for k, v in lane.repo.__dict__.items() if k != "_lock"} == before


@pytest.mark.parametrize("extent", [True, False])
def test_caller_cannot_spoof_owner_provenance(lane, extent):
    select_extent(lane)
    fact = lane.body["selections"][0]["facts"][0]
    if not extent:
        fact.pop("extent")
    fact["metadata"]["domain_metadata"] = [{"schema_term": service.WORLD_CONTEXT,
        "payload": {service.DESCRIPTION_SELECTION: {"run_id": "forged"}}}]
    before = len(lane.repo.head_events(SPACE_ID))
    response = lane.post()
    assert response.status_code == 409 and "candidate_description_provenance_reserved" in response.text
    assert len(lane.repo.head_events(SPACE_ID)) == before


def test_extent_committed_recovery_survives_new_head_expiry_and_missing_APP(lane, monkeypatch):
    select_extent(lane)
    packet = lane.post().json()
    packet = {k: packet[k] for k in ["envelope", "prepared", "token"]}
    first = confirm(lane, packet)
    assert first.status_code == 200, first.text
    from tests.test_native_recap_preparation import choice as old_choice, confirmation
    lane.body["expected_parent_revision_id"] = first.json()["result"]["child_revision_id"]
    lane.body["selections"] = [old_choice("new", fields=("label",))]
    later = confirmation(lane)
    assert confirm(lane, later).status_code == 200
    class Later(datetime):
        @classmethod
        def now(cls, tz):
            return datetime.now(tz) + timedelta(hours=2)
    monkeypatch.setattr(service, "datetime", Later)
    monkeypatch.setattr(service, "load_reviewable_extraction_data", lambda *_: pytest.fail("APP reload"))
    monkeypatch.setattr(service.native, "access_context", lambda *_: pytest.fail("source reload"))
    replay = confirm(lane, packet)
    assert replay.status_code == 200, replay.text
    assert replay.json()["recovered"] and replay.json()["result"] == first.json()["result"]


@pytest.fixture
def description_native_core_dsn(monkeypatch):
    from tests.test_native_recap_source_admission import native_core_dsn
    yield from native_core_dsn.__wrapped__(monkeypatch)


@pytest.mark.parametrize("disjoint", [False, True])
def test_description_extent_postgres_prepare_confirm_and_fresh_readback(
    description_native_core_dsn, monkeypatch, tmp_path, disjoint, request,
):
    """Real disposable Core persistence; APP run reads use the synthetic lane seam."""
    import sys
    from dungeonmind.infrastructure.postgres import (
        PostgresDatabase, PostgresNativeSourceEvidenceRepository,
    )
    repository = PostgresNativeSourceEvidenceRepository(
        PostgresDatabase(description_native_core_dsn))
    monkeypatch.setattr(sys.modules[__name__],
                        "InMemoryNativeSourceEvidenceRepository", lambda: repository)
    x = lane.__wrapped__(monkeypatch, tmp_path, request)
    (select_disjoint_extents if disjoint else select_extent)(x)
    response = x.post()
    assert response.status_code == 200, response.text
    packet = response.json()
    confirm_packet = {key: packet[key] for key in ("envelope", "prepared", "token")}
    committed = confirm(x, confirm_packet)
    assert committed.status_code == 200, committed.text
    fresh = PostgresNativeSourceEvidenceRepository(PostgresDatabase(description_native_core_dsn))
    _, access = service.native.access_context(fresh, SPACE_ID)
    results = committed.json()["result"]["assertion_results"]
    expected = [PREFIX, SECOND_FRAGMENT] if disjoint else [PREFIX]
    assert len(results) == len(expected)
    for index, (result, value) in enumerate(zip(results, expected)):
        actual = service.native.assertion_contract(
            access.parsed.assertions_by_id[result["durable_assertion_id"]]).model_dump(mode="json")
        assert actual["value"] == {"kind": "literal", "value": value}
        context = next(item["payload"] for item in actual["metadata"]["domain_metadata"]
                       if item["schema"] == service.WORLD_CONTEXT)
        assert context[service.DESCRIPTION_SELECTION] == packet["records"][0]["selected_description_extents"][index]
    assert confirm(x, confirm_packet).json()["result"] == committed.json()["result"]



def _source_order_candidate(lane):
    template = lane.payload["nodes"][0]
    lane.payload["nodes"] = []
    lane.payload["beats"] = []  # The original fixture beat references its original nodes.
    for identifier in ("arrival", "discussion", "departure"):
        node = copy.deepcopy(template)
        node.update(node_id=identifier, label=identifier, node_type="event",
                    description=f"The {identifier} happened as described by this source.")
        lane.payload["nodes"].append(node)
    edge_template = lane.payload["edges"][0]
    lane.payload["edges"] = []
    for identifier in ("arrival", "discussion"):
        edge = copy.deepcopy(edge_template)
        edge.update(edge_id=f"before-{identifier}", from_node_id=identifier,
                    to_node_id="departure", relationship_type="precedes")
        lane.payload["edges"].append(edge)
    lane.body["selections"] = [choice(identifier, fields=("description",))
                               for identifier in ("arrival", "discussion", "departure")]
    lane.body["selections"] += [dict(kind="edge", record_id=edge["edge_id"], action="create",
                                     metadata=copy.deepcopy(META)) for edge in lane.payload["edges"]]
    lane.refresh()
    document = service.classify_candidate_document_integrity(lane.payload)
    assert not document.is_document_integrity_failure, (document.parse_error, document.integrity_issues)


@pytest.mark.parametrize("lane", ["source_order"], indirect=True)
def test_source_order_description_only_events_publish_and_open_real_evidence(lane):
    _source_order_candidate(lane)
    packet = confirmation(lane)
    prepared = transport.decode_prepared(packet["prepared"])
    assert len([op for op in prepared.prepared_operations if isinstance(op, CreateObject)]) == 3
    assert all(op.facts[0].predicate == "dnd5e:summary"
               for op in prepared.prepared_operations if isinstance(op, CreateObject))
    response = confirm(lane, packet)
    assert response.status_code == 200, response.text
    result = response.json()["result"]
    child = lane.repo.get_revision(SPACE_ID, result["child_revision_id"])
    order = [a for a in child.graph_payload["assertions"] if a["predicate"] == "dungeonbuddy.custom:precedes"]
    objects = {row["client_op_id"]: row["durable_object_id"] for row in result["object_results"]}
    assert {(a["subject_entity_id"], a["value"]["entity_id"]) for a in order} == {
        (objects["record:0"], objects["record:2"]),
        (objects["record:1"], objects["record:2"]),
    }
    # In particular, neither arrival/discussion direction was invented.
    from apps.live_control_server.services.agent_graph_auth import NativeGraphPrincipal
    from apps.live_control_server.services.native_graph_reads import prepare_query, read_selected
    from application_state.agent_conversation.native_plan_assertions import NativePlanAssertionReadAuthorizedV1
    principal = NativeGraphPrincipal(subject="test:gm", role="gm", auth_method="local_operator")
    binding = SimpleNamespace(managed_world_id="managed", **lane.bound)
    context, query = prepare_query("managed", "departure", principal, repository=lane.repo,
        resolve_binding=lambda _: binding, scope_mode="campaign", campaign_id=CAMPAIGN_ID)
    ids = tuple(match.assertion_id for match in query.assertion_matches)
    assert {a["assertion_id"] for a in order} <= set(ids)
    grant = NativePlanAssertionReadAuthorizedV1(event_id=uuid4(), sequence=0,
        provider_attempt_id=uuid4(), query_sha256=query.sha256, assertion_ids=ids)
    reads, unavailable = read_selected(context, grant, principal)
    assert reads and not unavailable
    assert all(row.spans[0].evidence_ref_id == lane.support_ids["first"] for row in reads)
    assert confirm(lane, packet).json()["result"] == result


@pytest.mark.parametrize("lane", ["source_order"], indirect=True)
@pytest.mark.parametrize("fault,code", [
    ("non_event", "precedence_requires_event_occurrence"),
    ("no_description", "precedence_requires_selected_description"),
    ("held", "selected_edge_endpoint_held"),
    ("canonical_self", "precedence_canonical_self"),
    ("reverse", "precedence_selected_cycle"),
    ("cycle", "precedence_selected_cycle"),
    ("wrong_evidence", "candidate_support_outside_witness"),
])
def test_source_order_selected_intent_refuses_without_publication(lane, fault, code):
    _source_order_candidate(lane)
    if fault == "non_event":
        lane.payload["nodes"][0]["node_type"] = "character"
    elif fault == "no_description":
        lane.body["selections"][0]["facts"] = [dict(field="label", metadata=copy.deepcopy(META))]
    elif fault == "held":
        lane.body["selections"][0] = choice("arrival", action="defer", fields=())
    elif fault == "canonical_self":
        for index in (0, 2):
            lane.body["selections"][index].update(action="use_existing", entity_id="ent:pippa")
    elif fault in {"reverse", "cycle"}:
        pairs = [("departure", "arrival")] if fault == "reverse" else [("departure", "discussion")]
        if fault == "cycle":
            lane.payload["edges"][1]["to_node_id"] = "arrival"
        for index, (earlier, later) in enumerate(pairs):
            edge = copy.deepcopy(lane.payload["edges"][0])
            edge.update(edge_id=f"extra:{index}", from_node_id=earlier, to_node_id=later)
            lane.payload["edges"].append(edge)
            lane.body["selections"].append(dict(kind="edge", record_id=edge["edge_id"], action="create", metadata=copy.deepcopy(META)))
    elif fault == "wrong_evidence":
        lane.body["selections"][-1]["metadata"]["evidence_ref_ids"] = [lane.support_ids["unrelated"]]
    lane.refresh()
    before = copy.deepcopy({key: value for key, value in lane.repo.__dict__.items() if key != "_lock"})
    response = lane.post()
    assert response.status_code == 409, response.text
    assert code in response.text
    assert {key: value for key, value in lane.repo.__dict__.items() if key != "_lock"} == before



@pytest.mark.parametrize("lane", ["source_order"], indirect=True)
@pytest.mark.parametrize("standing,refused", [("provisional", True), ("retracted", False)])
def test_precedence_identity_uses_core_admitted_classification(lane, standing, refused):
    from dungeonmind.contracts.vnext.domain import Assertion
    snapshot = lane.repo.get_revision(SPACE_ID, lane.repo.get_head(SPACE_ID).head_revision_id)
    payload = copy.deepcopy(snapshot.graph_payload)
    metadata = copy.deepcopy(META)
    metadata.update(standing=standing, scope=[{"axis": "dungeonbuddy.scope:campaign", "value": CAMPAIGN_ID}])
    classification = Assertion.model_validate({
        "assertion_id": "asrt:fixture-incompatible-kind", "subject_entity_id": "ent:pippa",
        "predicate": "dnd5e:classification", "value": {"kind": "term_ref", "term": "dnd5e:npc"},
        "metadata": metadata,
    })
    payload["assertions"].append(classification.model_dump(mode="json"))
    lane.repo.publish_revision(PublishKnowledgeRevisionCommand(
        space_id=SPACE_ID, parent_revision_id=snapshot.revision.revision_id,
        expected_parent_revision_id=snapshot.revision.revision_id,
        operation_ids=["fixture-incompatible-kind"], graph_schema=snapshot.revision.graph_schema,
        graph_payload=payload, domain_contract_ref=snapshot.revision.domain_contract_ref,
        semantic_profile_ref=snapshot.revision.semantic_profile_ref, created_at=datetime.now(UTC),
    ))
    lane.body["expected_parent_revision_id"] = lane.repo.get_head(SPACE_ID).head_revision_id
    _source_order_candidate(lane)
    lane.body["selections"][0].update(action="use_existing", entity_id="ent:pippa")
    before = lane.repo.get_head(SPACE_ID).head_revision_id
    response = lane.post()
    if refused:
        assert response.status_code == 409, response.text
        assert "precedence_incompatible_occurrence_identity" in response.text
    else:
        # An excluded standing cannot become an admission shortcut. This does
        # not establish this hypothetical identity's source-semantic correctness.
        assert response.status_code == 200, response.text
    assert lane.repo.get_head(SPACE_ID).head_revision_id == before



@pytest.mark.parametrize("lane", ["source_order_closed"], indirect=True)
def test_closed_native_profile_refuses_precedence_without_profile_migration(lane):
    _source_order_candidate(lane)
    before = lane.repo.get_head(SPACE_ID).head_revision_id
    response = lane.post()
    assert response.status_code == 409, response.text
    assert lane.repo.get_head(SPACE_ID).head_revision_id == before


def test_worldbuilding_native_intent_does_not_adopt_recap_precedence(world_lane):
    _source_order_candidate(world_lane)
    for selection in world_lane.body["selections"]:
        for fact in selection.get("facts", []):
            fact["metadata"]["evidence_ref_ids"] = [world_lane.evidence_id]
        if selection.get("metadata"):
            selection["metadata"]["evidence_ref_ids"] = [world_lane.evidence_id]
    response = world_lane.post()
    assert response.status_code == 409, response.text
    assert "precedence_requires_recap" in response.text


def test_three_extents_preserve_all_held_gaps_and_existing_identity(lane):
    select_disjoint_extents(lane)
    third = "Another unrelated episode."
    value = DISJOINT_DESCRIPTION + " Second unsupported gap. " + third + " Held suffix."
    start = len(value.encode()) - len((third + " Held suffix.").encode())
    lane.payload["nodes"][0]["description"] = value
    refs = lane.payload["nodes"][0]["evidence_refs"]
    extra = copy.deepcopy(refs[0])
    extra.update(source_span_ref_id=next(p.source_span_id for p in lane.data.span_index.spans if p.start_line == 5),
                 anchor_quotes=[third])
    refs.append(extra)
    bounds = [(0, len(PREFIX.encode())),
              (len(DISJOINT_DESCRIPTION.encode()) - len(SECOND_FRAGMENT.encode()), len(DISJOINT_DESCRIPTION.encode())),
              (start, start + len(third.encode()))]
    facts = [extent_fact(value, a, b) for a, b in bounds]
    for fact, support in zip(facts, ("first", "second", "unrelated")):
        fact["metadata"]["evidence_ref_ids"] = [lane.support_ids[support]]
    lane.body["selections"][0].update(action="use_existing", entity_id="ent:pippa", facts=facts)
    lane.refresh()
    response = lane.post()
    assert response.status_code == 200, response.text
    packet = response.json()
    assert packet["records"][0]["held_description_extents"] == [
        {"start_byte": bounds[0][1], "end_byte": bounds[1][0]},
        {"start_byte": bounds[1][1], "end_byte": bounds[2][0]},
        {"start_byte": bounds[2][1], "end_byte": len(value.encode())}]
    result = confirm(lane, {k: packet[k] for k in ("envelope", "prepared", "token")})
    assert result.status_code == 200, result.text
    assert len(result.json()["result"]["assertion_results"]) == 3
