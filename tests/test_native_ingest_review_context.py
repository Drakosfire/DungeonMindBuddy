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

    monkeypatch.setattr("apps.live_control_server.integrations.dungeonmind.native_registry_source.config.world_graph_authority_database_url", lambda:
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
        nodes=[{"node_id": node_id, "label": label}], source_admission=None,
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


def test_actual_authenticated_http_composes_native_context(context, recap_admission, monkeypatch):
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
            assert {item["evidence_role"] for item in packet["native_context"]["source_evidence"]} == {"support"}
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


@pytest.fixture
def recap_admission(context, native_world, monkeypatch):
    """Real native source/admission verifier with synthetic APP read ports only."""
    from apps.live_control_server.services import native_recap_source_admission as owner
    from apps.live_control_server.integrations.dungeonmind import native_recap_source_admission as bridge
    from apps.live_control_server.integrations.dungeonmind import native_registry_source
    from graph_memory.ingestion.native_recap_source import Record, KEY, PROFILE
    from graph_memory.ingestion.extraction_run import ExtractionRun
    from graph_memory.evidence.source_artifact import GraphMemorySourceArtifact
    from dungeonmind.application.vnext import publish_native_source_evidence_extension
    from dungeonmind.contracts.vnext.native_source import NativeSourceEvidenceExtensionV1

    source = context.source
    source.created_at, source.media_type = NOW, "text/markdown"
    scope = dict(managed_world_id="world-a", native_world_id="native-a", binding_version=2,
                 campaign_id="c1", session_id="session-29")
    descriptor = GraphMemorySourceArtifact(
        source_artifact_id=source.source_artifact_id, source_domain="recap", artifact_kind="recap_markdown",
        world_id="native-a", campaign_id="c1", session_id="session-29",
        content_sha256=source.content_sha256, uri="unused://not-source-authority",
    )
    monkeypatch.setattr(owner, "get_source_artifact", lambda *args: descriptor)
    monkeypatch.setattr(owner.config, "managed_world_data_root", lambda root: context.root)
    monkeypatch.setattr(bridge, "resolve_managed_source_identity", lambda *args, **kwargs: context.binding)
    monkeypatch.setattr(native_registry_source, "read_repository", lambda: native_world.repository)
    authority = bridge.NativeRecapAuthority(context.root, repository=native_world.repository)
    record = Record(
        managed_world_id="world-a", native_world_id="native-a", binding_version=2,
        campaign_id="c1", session_id="session-29", app_source_artifact_id=source.source_artifact_id,
        app_source_revision_id=source.source_revision_id, app_body_sha256=source.content_sha256,
        created_by="synthetic-setup", created_authority_basis="local_gm", created_at=NOW,
    )
    record = record.model_copy(update={"commands": [authority.prepare(record, source.markdown)]})
    receipt = authority.dispatch(record, source.markdown)
    record = record.model_copy(update={"receipt": receipt})
    # Support has no assertion supporters: this is prepublication inspection.
    raw = source.markdown.encode()
    start = raw.rfind("Ari".encode())
    end = len(raw.rstrip(b"\n"))
    extension = publish_native_source_evidence_extension(
        repository=native_world.repository, domain_contract=native.dungeonbuddy_world_domain_contract(),
        semantic_profile=dungeonbuddy_dnd5e_semantic_profile(),
        audience_labels=(native.GM_LABEL,),
        request=NativeSourceEvidenceExtensionV1(
            space_id="native-a", extension_id="fixture-recap-support",
            original_admission_id=record.admission_id, source_artifact_id=receipt.source_artifact_id,
            source_revision_id=receipt.source_revision_id, expected_body_sha256=source.content_sha256,
            expected_parent_revision_id=native_world.repository.get_head("native-a").head_revision_id,
            expected_source_authority_epoch=native_world.repository.open_native_source_view("native-a").epoch,
            created_at=NOW, spans=[NativeTextEvidenceSpanRequestV1(
                client_ref="selected-paragraph", evidence_role="support", start_byte=start,
                end_byte=end, expected_slice_sha256=hashlib.sha256(raw[start:end]).hexdigest(),
            )],
        ),
    )
    operation = ExtractionRun(
        run_id=record.run_id, source_artifact_id=source.source_artifact_id, source_domain="recap",
        campaign_id="c1", session_id="session-29", profile_id=PROFILE,
        revision=4, lineage={KEY: record.model_dump(mode="json")},
    )
    monkeypatch.setattr(owner.ingest, "get_extraction_run_optional", lambda run_id: operation if run_id == record.run_id else None)
    monkeypatch.setattr(owner.ingest, "get_extraction_run", lambda run_id: operation if run_id == record.run_id else pytest.fail("foreign run"))
    monkeypatch.setattr(owner, "create_extraction_run", lambda *a, **k: pytest.fail("read created intent"))
    monkeypatch.setattr(owner, "_execute", lambda *a, **k: pytest.fail("read dispatched source"))
    monkeypatch.setattr(owner, "_cas", lambda *a, **k: pytest.fail("read mutated intent"))
    monkeypatch.setattr(source_tests.service, "inspect_saved_source", owner.inspect_saved_source)
    monkeypatch.setattr(source_tests.service, "resolve_native_review_context", native.resolve_native_review_context)
    return SimpleNamespace(owner=owner, operation=operation, record=record, scope=scope, receipt=receipt,
                           extension=extension, authority=authority, bridge=bridge, native=native_world)


def test_exact_native_support_without_published_assertion_is_inspectable(context, recap_admission):
    repository = recap_admission.native.repository
    before = deepcopy({k: v for k, v in repository.__dict__.items() if k != "_lock"})
    app_before = recap_admission.operation.model_dump(mode="json")
    result = source_tests.resolve(context)
    packet = result["native_context"]
    assert packet["source_admission"] == {
        "state": "admitted", "run_id": recap_admission.record.run_id,
        "run_revision": 4, "opening_state": "verified", "failure_code": None,
    }
    refs = packet["source_evidence"]
    assert {ref["evidence_role"] for ref in refs} == {"support"}
    assert recap_admission.receipt.bindings[0].evidence_ref_id not in {ref["evidence_ref_id"] for ref in refs}
    support = next(ref for ref in refs if ref["evidence_role"] == "support")
    assert support["evidence_ref_id"] == recap_admission.extension.bindings[0].evidence_ref_id
    opening = support["opening"]
    assert opening["span_text"] == "Ari 🐉 visits cafe\u0301."
    assert opening["source_artifact_id"] == recap_admission.receipt.source_artifact_id
    assert opening["source_revision_id"] == recap_admission.receipt.source_revision_id
    assert opening["source_revision_id"] != result["source_revision_id"]
    assert "body_text" not in opening
    assert packet["semantic_support_verified"] is False and packet["identity_approval"] is False
    assert result["permissions"] == {"graph_write": False, "candidate_write": False, "provider_call": False}
    assert recap_admission.operation.model_dump(mode="json") == app_before
    for key, value in before.items():
        assert repository.__dict__[key] == value


@pytest.mark.parametrize("namespace", ["unrelated-owner", "dungeonbuddy.app-recap-source.v1"])
def test_same_bytes_from_another_admission_are_not_review_evidence(context, recap_admission, namespace):
    from dungeonmind.contracts.vnext.native_source import NativeTextSourceOriginV1
    repository = recap_admission.native.repository
    raw = context.source.markdown.encode()
    foreign = publish_native_text_source_evidence(
        repository=repository, domain_contract=native.dungeonbuddy_world_domain_contract(),
        semantic_profile=dungeonbuddy_dnd5e_semantic_profile(),
        request=NativeTextSourceAdmissionV1(
            space_id="native-a", admission_id="foreign-same-bytes",
            expected_parent_revision_id=repository.get_head("native-a").head_revision_id,
            created_at=NOW, body_text=context.source.markdown, expected_body_sha256=hashlib.sha256(raw).hexdigest(),
            source_classification="dungeonbuddy.source:session_recap", authority="primary",
            visibility={"kind": "public"},
            origin=NativeTextSourceOriginV1(namespace=namespace, object_id=context.source.source_artifact_id,
                                            revision_id=str(context.source.source_revision_id)),
            spans=[NativeTextEvidenceSpanRequestV1(client_ref="foreign", evidence_role="support",
                start_byte=0, end_byte=len(raw), expected_slice_sha256=hashlib.sha256(raw).hexdigest())],
        ),
    )
    refs = source_tests.resolve(context)["native_context"]["source_evidence"]
    assert foreign.bindings[0].evidence_ref_id not in {ref["evidence_ref_id"] for ref in refs}
    assert len(refs) == 1


def test_missing_admission_does_not_create_or_dispatch(context, recap_admission, monkeypatch):
    monkeypatch.setattr(recap_admission.owner.ingest, "get_extraction_run_optional", lambda _: None)
    result = source_tests.resolve(context)["native_context"]
    assert result["source_admission"] == {"state": "not_found"}
    assert result["source_evidence"] == []


def test_unverified_admission_does_not_expose_support(context, recap_admission, monkeypatch):
    from graph_memory.ingestion.native_recap_source import Opening
    monkeypatch.setattr(recap_admission.bridge.NativeRecapAuthority, "verify", lambda *a: Opening(state="unavailable"))
    result = source_tests.resolve(context)["native_context"]
    assert result["source_admission"]["opening_state"] == "unavailable"
    assert result["source_evidence"] == []


@pytest.mark.parametrize("origin_change", [
    None, {"namespace": "wrong"}, {"object_id": "another-source"},
    {"revision_id": "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"},
])
def test_mismatched_saved_receipt_origin_refuses_review(context, recap_admission, origin_change):
    from apps.live_control_server.services.extract_promote import ExtractPromoteError
    raw = recap_admission.operation.lineage["native_recap_source"]["receipt"]["origin"]
    if origin_change is None:
        recap_admission.operation.lineage["native_recap_source"]["receipt"]["origin"] = None
    else:
        raw.update(origin_change)
    with pytest.raises(ExtractPromoteError, match="native_recap_intent_invalid") as error:
        source_tests.resolve(context)
    assert error.value.status_code == 409


def test_native_epoch_drift_rejects_even_without_head_drift(context, recap_admission, monkeypatch):
    repository = recap_admission.native.repository
    original = repository.open_native_source_view
    calls = 0

    def changed(space):
        nonlocal calls
        calls += 1
        view = original(space)
        # Owner receipt opening first, current review acquisition second, final check third.
        return view if calls < 3 else SimpleNamespace(epoch=view.epoch + 1)

    monkeypatch.setattr(repository, "open_native_source_view", changed)
    from apps.live_control_server.services.extract_promote import ExtractPromoteError
    with pytest.raises(ExtractPromoteError, match="source authority changed") as error:
        source_tests.resolve(context)
    assert error.value.status_code == 409


def test_missing_native_support_span_is_not_returned_as_available(context, recap_admission, monkeypatch):
    repository = recap_admission.native.repository
    original = repository.open_native_source_view
    support_span = recap_admission.extension.bindings[0].span_id

    class MissingSupport:
        def __init__(self, view):
            self.view = view

        def __getattr__(self, name):
            return getattr(self.view, name)

        def get_native_text_source(self, **kwargs):
            return None if kwargs["span_id"] == support_span else self.view.get_native_text_source(**kwargs)

    monkeypatch.setattr(repository, "open_native_source_view", lambda space: MissingSupport(original(space)))
    refs = source_tests.resolve(context)["native_context"]["source_evidence"]
    support = next(ref for ref in refs if ref["evidence_role"] == "support")
    assert support["opening"]["status"] == "unavailable"
    assert "span_text" not in support["opening"]
    assert support["opening"]["source_artifact_id"] is None


def test_native_support_body_digest_mismatch_is_not_an_identity_fallback(context, recap_admission, monkeypatch):
    from apps.live_control_server.services.extract_promote import ExtractPromoteError
    original = native._preview

    def changed(access, identifier):
        value = original(access, identifier)
        if identifier == recap_admission.extension.bindings[0].evidence_ref_id:
            value["body_sha256"] = "0" * 64
        return value

    monkeypatch.setattr(native, "_preview", changed)
    with pytest.raises(ExtractPromoteError, match="saved source bytes") as error:
        source_tests.resolve(context)
    assert error.value.status_code == 409
