"""Component-only native witnesses; these do not establish real recap integration."""

from copy import deepcopy
from dataclasses import replace
from datetime import UTC, datetime
import hashlib
import json
from types import SimpleNamespace

import pytest

from apps.live_control_server.integrations.dungeonmind import vnext_review_context as native
from dungeonmind.application.vnext import (
    initialize_empty_knowledge_space,
    publish_native_text_source_evidence,
)
from dungeonmind.contracts.vnext.knowledge import PublishKnowledgeRevisionCommand
from dungeonmind.contracts.vnext.native_source import (
    NativeTextSourceAdmissionV1, NativeTextEvidenceSpanRequestV1,
)
from dungeonmind.infrastructure.memory.vnext_sources import InMemoryNativeSourceEvidenceRepository
from graph_memory.vnext.domain_runtime import dungeonbuddy_dnd5e_semantic_profile
from tests import test_ingest_selection_context as source_tests

context = source_tests.context

NOW = datetime(2026, 10, 28, tzinfo=UTC)


def test_host_repository_adds_read_only_without_dropping_existing_options(monkeypatch):
    from psycopg.conninfo import conninfo_to_dict

    monkeypatch.setattr(native, "world_graph_authority_database_url", lambda:
                        "postgresql://localhost/example?options=-c%20statement_timeout%3D5000")
    repository = native._repository()
    options = conninfo_to_dict(repository._database._database_url)["options"]
    assert options == "-c statement_timeout=5000 -c default_transaction_read_only=on"


def test_missing_native_head_cannot_fall_back_to_classic_graph(monkeypatch):
    monkeypatch.setattr(native, "_repository", InMemoryNativeSourceEvidenceRepository)
    with pytest.raises(native.NativeReviewConflict, match="no current revision"):
        read()


@pytest.fixture
def native_world(monkeypatch):
    repository = InMemoryNativeSourceEvidenceRepository()
    domain = native.dungeonbuddy_world_domain_contract()
    profile = dungeonbuddy_dnd5e_semantic_profile()
    genesis = initialize_empty_knowledge_space(
        repository=repository, space_id="native-a", initialization_id="fixture-init",
        created_at=NOW, domain_contract=domain, semantic_profile=profile,
    )
    # Two campaign claims share one World-owned source, but separate exact spans.
    text = "Ari serves C1.\nAri serves C2.\n"
    spans = []
    offset = 0
    for index, line in enumerate(text.splitlines(keepends=True), 1):
        data = line.encode()
        spans.append(NativeTextEvidenceSpanRequestV1(
            client_ref=f"c{index}", evidence_role="support", start_byte=offset,
            end_byte=offset + len(data), expected_slice_sha256=hashlib.sha256(data).hexdigest(),
        ))
        offset += len(data)
    receipt = publish_native_text_source_evidence(
        repository=repository, domain_contract=domain, semantic_profile=profile,
        request=NativeTextSourceAdmissionV1(
            space_id="native-a", admission_id="fixture-source",
            expected_parent_revision_id=genesis.published_revision_id,
            created_at=NOW, body_text=text,
            expected_body_sha256=hashlib.sha256(text.encode()).hexdigest(),
            source_classification="dungeonbuddy.source:worldbuilding",
            authority="primary", visibility={"kind": "public"}, spans=spans,
        ),
    )
    stored = repository.get_revision("native-a", receipt.published_revision_id)
    payload = deepcopy(stored.graph_payload)
    payload["entities"] = [
        {"schema_version": "dm_entity_v1", "entity_id": key}
        for key in ("ari", "ari-other", "bare")
    ]
    bindings = {binding.client_ref: binding for binding in receipt.bindings}
    assertions = []
    for campaign, entity in (("c1", "ari"), ("c2", "ari"), ("c1", "ari-other")):
        assertions.append({
            "schema_version": "dm_assertion_v1",
            "assertion_id": f"name-{campaign}-{entity}",
            "subject_entity_id": entity, "predicate": "dnd5e:name",
            "value": {"kind": "literal", "value": "Ari"},
            "metadata": {
                "scope": [{"axis": "dungeonbuddy.scope:campaign", "value": campaign}],
                "visibility": {"kind": "public"}, "epistemic_basis": "asserted",
                "claim_mode": "dungeonbuddy.claim:fact", "standing": "established",
                "evidence_ref_ids": [bindings[campaign].evidence_ref_id],
                "temporal_scope": {"kind": "timeless"},
            },
        })
    payload["assertions"] = assertions
    command = PublishKnowledgeRevisionCommand(
        space_id="native-a", parent_revision_id=stored.revision.revision_id,
        expected_parent_revision_id=stored.revision.revision_id,
        operation_ids=["fixture-component-facts"], graph_schema=stored.revision.graph_schema,
        graph_payload=payload, domain_contract_ref=stored.revision.domain_contract_ref,
        semantic_profile_ref=stored.revision.semantic_profile_ref, created_at=NOW,
    )
    repository.publish_revision(command)
    monkeypatch.setattr(native, "_repository", lambda: repository)
    return SimpleNamespace(repository=repository, command=command, payload=payload)


def read(campaign="c1", node_id="ari", label="Ari"):
    return native.resolve_native_review_context(
        scope={"native_world_id": "native-a", "campaign_id": campaign, "session_id": "s1"},
        nodes=[{"node_id": node_id, "label": label}],
    )


def test_native_campaign_support_does_not_widen_to_shared_body(native_world):
    before = deepcopy({key: value for key, value in native_world.repository.__dict__.items()
                       if key != "_lock"})
    packet = read("c2")
    selection = packet["selections"][0]
    assert selection["status"] == "supported_facts"
    target = selection["alternatives"][0]
    assert target["entity_id"] == "ari"
    assert [a["assertion_id"] for a in target["entity_result"]["assertions"]] == ["name-c2-ari"]
    preview = target["source_inspection"][0]
    assert preview["span_text"] == "Ari serves C2.\n"
    assert "body_text" not in preview
    assert "name-c1" not in json.dumps(packet)
    assert target["identity_approved"] is False
    request = packet["projection_request"]
    assert request["scope_selector"]["wildcard_axes"] == []
    assert request["scope_selector"]["bindings"][0]["value"] == "c2"
    assert request["standing_selector"] == ["established", "provisional"]
    # Read operations leave native revision/source/receipt dictionaries intact.
    for key, value in before.items():
        if key != "_lock":
            assert native_world.repository.__dict__[key] == value


def test_multiple_supported_names_remain_ambiguous(native_world):
    selection = read()["selections"][0]
    assert selection["status"] == "ambiguous"
    assert len(selection["alternatives"]) == 2
    assert all(not item["identity_approved"] for item in selection["alternatives"])


def test_exact_identity_with_no_admitted_facts_is_insufficient(native_world):
    selection = read(node_id="bare", label="bare")["selections"][0]
    assert selection["status"] == "insufficient_support"
    assert selection["alternatives"][0]["entity_result"]["assertions"] == []


def test_absent_and_unknown_campaign_do_not_invent_support(native_world):
    assert read(node_id="missing", label="missing")["selections"][0]["status"] == "absent"
    selection = read("unknown")["selections"][0]
    assert selection["status"] == "insufficient_support"
    assert selection["alternatives"][0]["entity_result"]["assertions"] == []


def test_native_head_drift_rejects_instead_of_refreshing(native_world, monkeypatch):
    original = native_world.repository.get_head
    calls = 0

    def changed(space_id):
        nonlocal calls
        calls += 1
        head = original(space_id)
        return head if calls == 1 else head.model_copy(update={"head_revision_id": "changed"})

    monkeypatch.setattr(native_world.repository, "get_head", changed)
    with pytest.raises(native.NativeReviewConflict, match="head changed"):
        read()


def publish_fixture_child(world, payload):
    parent = world.repository.get_head("native-a").head_revision_id
    world.repository.publish_revision(world.command.model_copy(update={
        "parent_revision_id": parent, "expected_parent_revision_id": parent,
        "operation_ids": ["fixture-control-child"], "graph_payload": payload,
    }))


def test_provisional_facts_and_conflicting_kinds_are_exposed_without_identity_choice(native_world):
    payload = deepcopy(native_world.payload)
    base = deepcopy(payload["assertions"][1])
    for standing, term in (("established", "dnd5e:npc"), ("provisional", "dnd5e:location")):
        assertion = deepcopy(base)
        assertion.update(assertion_id=f"classification-{standing}", predicate="dnd5e:classification",
                         value={"kind": "term_ref", "term": term})
        assertion["metadata"]["standing"] = standing
        payload["assertions"].append(assertion)
    publish_fixture_child(native_world, payload)
    alternative = read("c2")["selections"][0]["alternatives"][0]
    assertions = alternative["entity_result"]["assertions"]
    assert {item["assertion_id"] for item in assertions} == {
        "name-c2-ari", "classification-established", "classification-provisional",
    }
    assert alternative["identity_approved"] is False


def test_missing_preview_is_distinct_from_corrupt_source(native_world, monkeypatch):
    from dungeonmind.domain.errors import PersistenceIntegrityError
    original = native_world.repository.open_native_source_view

    class MissingPreview:
        def __init__(self, view):
            self.view = view

        def __getattr__(self, name):
            return getattr(self.view, name)

        def get_native_text_source(self, **kwargs):
            return None

    monkeypatch.setattr(native_world.repository, "open_native_source_view",
                        lambda world: MissingPreview(original(world)))
    alternative = read("c2")["selections"][0]["alternatives"][0]
    assert alternative["source_inspection"][0]["status"] == "unavailable"
    monkeypatch.setattr(native_world.repository, "open_native_source_view", original)
    for key, record in list(native_world.repository._native_records.items()):
        damaged = replace(record, body=b"damaged")
        native_world.repository._native_records[key] = damaged
        for revision_key, indexed in list(native_world.repository._by_revision.items()):
            if indexed is record:
                native_world.repository._by_revision[revision_key] = damaged
        for span_key, (indexed, proof) in list(native_world.repository._by_span.items()):
            if indexed is record:
                native_world.repository._by_span[span_key] = (damaged, proof)
    with pytest.raises(PersistenceIntegrityError):
        read("c2")


def test_actual_authenticated_http_composes_native_context(context, native_world, monkeypatch):
    import asyncio
    import httpx
    from fastapi import FastAPI
    from apps.live_control_server.routes.extract_promote import router
    from apps.live_control_server.services.agent_graph_auth import (
        NativeGraphPrincipal, native_graph_gm_dependency,
    )

    monkeypatch.setattr(source_tests.service, "resolve_native_review_context", native.resolve_native_review_context)
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[native_graph_gm_dependency] = lambda: NativeGraphPrincipal(
        subject="operator:integration", role="gm", auth_method="local_operator",
    )

    async def exercise():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            url = "/api/live/extract-promote/runs/test-run/selection-context"
            result = await client.post(url, json=context.body)
            assert result.status_code == 200, result.text
            packet = result.json()
            assert packet["schema"] == "dmb_ingest_native_review_context_v2"
            assert packet["scope"]["admitted_world_facts_included"] is True
            assert packet["nodes"][0]["identity_authority"] == "candidate_only"
            assert packet["native_context"]["selections"][0]["status"] == "ambiguous"
            sha = packet.pop("context_sha256")
            assert sha == source_tests.service._record_hash(packet)
            app.dependency_overrides.clear()
            monkeypatch.setattr(native, "_repository", lambda: pytest.fail("unauthorized native read"))
            assert (await client.post(url, json=context.body)).status_code in (401, 503)

    asyncio.run(exercise())


def test_actual_agent_reconstructs_native_packet_before_provider(
    context, native_world, application_state_dsn, monkeypatch, record_property,
):
    from urllib.parse import urlparse
    from application_state.agent_conversation import AgentConversationService
    from tests.test_agent_selected_knowledge_context import request_for, execute, RecordingRuntime

    record_property("disposable_app_database", urlparse(application_state_dsn).path.removeprefix("/"))
    monkeypatch.setattr(source_tests.service, "resolve_native_review_context", native.resolve_native_review_context)
    request = request_for(context)
    runtime = RecordingRuntime()
    response = execute(context, request, runtime, AgentConversationService())
    assert response.answer.status == "ok"
    assert len(runtime.invocations) == 1
    packet = runtime.invocations[0].context_packet.selected_knowledge_context
    assert packet["context_sha256"] == request.selected_knowledge.expected_context_sha256
    assert packet["native_context"]["revision_id"] == native_world.repository.get_head("native-a").head_revision_id
    assert "name-c1-ari" in runtime.requests[0].question
    assert "source_inspection" in runtime.requests[0].question
