"""A fresh HTTP reader recovers exact Process bytes and candidate evidence from APP."""

import hashlib
import json
import shutil

import pytest
from fastapi.testclient import TestClient

from apps.live_control_server.main import create_app
from apps.live_control_server.services.graph_run_registry import (
    load_reviewable_extraction_data,
)
from tests.test_live_recap_ingest_graph_preview_api import (
    TOKEN,
    process_body,
)
from tests.test_live_recap_ingest_graph_preview_api import (
    client_env as client_env,
)
from tests.test_native_recap_source_admission import native_core_dsn as native_core_dsn


def test_ordinary_process_candidate_evidence_survives_fresh_exact_run_review_client(
    client_env,
):
    client, root = client_env
    request = process_body(session=29)
    response = client.post("/api/live/recap-ingest", json=request)
    assert response.status_code == 200, response.text
    graph = response.json()["ingest_report"]["graph_preview"]
    run_id = graph["extraction_run_id"]
    data = load_reviewable_extraction_data(root, run_id)
    candidate = json.loads(data.candidate_bytes)
    spans = json.loads(data.span_bytes)
    ids = {r["source_span_id"] for r in spans["spans"]}
    refs = [
        ref
        for k in ["nodes", "edges", "beats"]
        for item in candidate[k]
        for ref in item.get("evidence_refs", [])
    ]
    assert refs and all(
        r["source_artifact_id"] == graph["source_artifact_id"]
        and r["source_span_ref_id"] in ids
        for r in refs
    )
    original = data.source_bytes
    assert original == request["raw_text"].encode() + b"\n"
    shutil.rmtree(root / "out/graph_memory", ignore_errors=True)
    # Neither a current file nor a previous client is needed to open the exact run.
    with TestClient(
        create_app(),
        client=("127.0.0.1", 50000),
        headers={"Authorization": "Bearer " + TOKEN},
    ) as fresh:
        catalog = fresh.get(
            "/api/live/graph-preview/extraction-runs",
            params={"managed_world_id": "elderwyld", "campaign_id": "longmont-c2"},
        )
        assert catalog.status_code == 200, catalog.text
        row = next(r for r in catalog.json()["runs"] if r["runId"] == run_id)
        reply = fresh.get(
            f"/api/live/graph-preview/extraction-runs/{run_id}/recap-inspection",
            params={
                "managed_world_id": "elderwyld",
                "expected_run_revision": row["runRevision"],
                "source_revision_id": row["sourceRevisionId"],
            },
        )
        assert reply.status_code == 200, reply.text
        assert reply.json()["run"] == row
        assert reply.json()["sourceProse"].encode() == original
        assert hashlib.sha256(original).hexdigest() == row["sourceSha256"]
        recovered = load_reviewable_extraction_data(root, run_id)
        assert (
            recovered.candidate_bytes == data.candidate_bytes
            and recovered.span_bytes == data.span_bytes
        )


@pytest.mark.parametrize("prep_state", [
    None, {"authority_state": "gm_prep"},
    {"canon_state": "planning_scaffold"}, {"canon_state": "worldbuilding_draft"},
])
def test_ordinary_process_review_publish_and_fresh_database_readback(
    client_env, native_core_dsn, monkeypatch, record_property, prep_state,
):
    """One isolated APP/Core chain; provider fixtures do not claim model quality."""
    from datetime import UTC, datetime
    from dungeonmind.contracts.vnext.knowledge import PublishKnowledgeRevisionCommand
    import graph_memory.extraction.graph_preview_runner as producer
    from application_state.source import service as sources
    from apps.live_control_server import config
    from apps.live_control_server.integrations.dungeonmind import native_registry_source as native
    from dungeonmind.application.vnext import initialize_empty_knowledge_space, open_admitted_native_text
    from dungeonmind.infrastructure.postgres import PostgresDatabase, PostgresNativeSourceEvidenceRepository
    from graph_memory.vnext.domain_runtime import (
        dungeonbuddy_world_domain_contract, dungeonbuddy_dnd5e_custom_predicate_profile,
    )

    client, root = client_env
    monkeypatch.setattr(config, "world_graph_authority_database_url", lambda: native_core_dsn)
    monkeypatch.setenv("DMB_GRAPH_REVIEW_PREPARE_BINDING_KEY", "synthetic-joined-proof-signing-key")
    space = "world:elderwyld"
    repo = PostgresNativeSourceEvidenceRepository(PostgresDatabase(native_core_dsn))
    initialize_empty_knowledge_space(
        repository=repo, space_id=space, initialization_id="joined-fixture-genesis",
        created_at=datetime.now(UTC), domain_contract=dungeonbuddy_world_domain_contract(),
        semantic_profile=dungeonbuddy_dnd5e_custom_predicate_profile(),
    )
    extract = producer.extract_category_candidate_graph

    def extract_event(*args, **kwargs):
        result = extract(*args, **kwargs)
        result.candidate_graph["nodes"][0].update(
            label="The keeper scouts the road", node_type="event",
        )
        if prep_state:
            result.candidate_graph["nodes"][0]["semantic_state"].update(prep_state)
        return result

    monkeypatch.setattr(producer, "extract_category_candidate_graph", extract_event)
    processed = client.post("/api/live/recap-ingest", json=process_body())
    assert processed.status_code == 200, processed.text
    graph = processed.json()["ingest_report"]["graph_preview"]
    run_id = graph["extraction_run_id"]
    proposal, = graph["event_placement_proposals"]
    assert proposal["status"] == ("held" if prep_state else "needs_review")
    data = load_reviewable_extraction_data(root, run_id)
    frozen = (data.source_bytes, data.candidate_bytes, data.span_bytes)
    candidate = json.loads(data.candidate_bytes)
    assert len(candidate["nodes"]) == 1 and not candidate["edges"]
    node = candidate["nodes"][0]
    source = sources.get_source_markdown(
        source_artifact_id=data.run.source_artifact_id,
        content_sha256=hashlib.sha256(data.source_bytes).hexdigest(),
    )
    shutil.rmtree(root / "out/graph_memory", ignore_errors=True)

    # A new HTTP application reads the same frozen APP run without its files.
    with TestClient(create_app(), client=("127.0.0.1", 50000),
                    headers={"Authorization": "Bearer " + TOKEN}) as fresh:
        catalog = fresh.get("/api/live/graph-preview/extraction-runs", params={
            "managed_world_id": "elderwyld", "campaign_id": "longmont-c2",
        })
        assert catalog.status_code == 200, catalog.text
        saved = next(row for row in catalog.json()["runs"] if row["runId"] == run_id)
        review = fresh.get(f"/api/live/graph-preview/extraction-runs/{run_id}/recap-inspection", params={
            "managed_world_id": "elderwyld", "expected_run_revision": saved["runRevision"],
            "source_revision_id": saved["sourceRevisionId"],
        })
        assert review.status_code == 200, review.text
        assert review.json()["sourceProse"].encode() == data.source_bytes

        admitted_reply = fresh.post("/api/live/recap-ingest", json={
            "operation": "build_graph_preview_bundle", "managed_world_id": "elderwyld",
            "campaign_id": "longmont-c2", "session": 8, "include_graph_extraction": False,
            "native_recap_source": {"source_artifact_id": source.source_artifact_id,
                "source_revision_id": str(source.source_revision_id), "content_sha256": source.content_sha256},
        })
        assert admitted_reply.status_code == 200, admitted_reply.text
        admitted = admitted_reply.json()["native_recap_source"]
        assert admitted["state"] == "admitted" and admitted["opening"]["state"] == "verified"
        context, _ = native.access_context(repo, space)
        reviewed_text = process_body()["raw_text"].split("\n\n")[-1].encode()
        support_start = data.source_bytes.index(reviewed_text)
        support_end = support_start + len(reviewed_text)
        supported_reply = fresh.post("/api/live/source-statements/extend-evidence", json={
            "managed_world_id": "elderwyld", "extension_id": "joined-explicit-source-review",
            "original_admission_id": admitted["admission_id"],
            "source_artifact_id": admitted["source_artifact_id"],
            "source_revision_id": admitted["source_revision_id"],
            "expected_body_sha256": source.content_sha256,
            "expected_parent_revision_id": context["revision_id"],
            "expected_source_authority_epoch": context["source_epoch"],
            "created_at": datetime.now(UTC).isoformat(),
            "spans": [{"client_ref": "reviewed-fixture-source", "evidence_role": "support",
                "start_byte": support_start, "end_byte": support_end,
                "expected_slice_sha256": hashlib.sha256(reviewed_text).hexdigest()}],
        })
        assert supported_reply.status_code == 200, supported_reply.text
        evidence_id = supported_reply.json()["receipt"]["bindings"][0]["evidence_ref_id"]
        context, _ = native.access_context(repo, space)
        metadata = {"evidence_ref_ids": [evidence_id], "visibility": {
            "kind": "labels_any", "labels": ["dungeonbuddy.visibility:gm"]},
            "epistemic_basis": "asserted", "claim_mode": "dungeonbuddy.claim:fact",
            "standing": "provisional", "temporal_scope": {"kind": "timeless"}}
        parent = repo.get_revision(space, context["revision_id"])
        campaign_object = "ent:campaign-timeline"
        payload = parent.graph_payload
        payload["entities"].append({"schema_version": "dm_entity_v1", "entity_id": campaign_object})
        payload["assertions"].append({
            "assertion_id": "asrt:campaign-timeline",
            "subject_entity_id": campaign_object,
            "predicate": "dnd5e:classification",
            "value": {"kind": "term_ref", "term": "dungeonbuddy:campaign"},
            "metadata": metadata | {"scope": [
                {"axis": "dungeonbuddy.scope:campaign", "value": "longmont-c2"},
            ]},
        })
        repo.publish_revision(PublishKnowledgeRevisionCommand(
            space_id=space, parent_revision_id=context["revision_id"],
            expected_parent_revision_id=context["revision_id"],
            operation_ids=["joined-fixture-campaign"], graph_schema=parent.revision.graph_schema,
            graph_payload=payload, domain_contract_ref=parent.revision.domain_contract_ref,
            semantic_profile_ref=parent.revision.semantic_profile_ref, created_at=datetime.now(UTC),
        ))
        context, _ = native.access_context(repo, space)
        request = {"managed_world_id": "elderwyld", "campaign_id": "longmont-c2", "run_id": run_id,
            "expected_run_revision": data.run.revision,
            "candidate_sha256": hashlib.sha256(data.candidate_bytes).hexdigest(),
            "source_admission_run_id": admitted["run_id"],
            "expected_parent_revision_id": context["revision_id"],
            "expected_source_authority_epoch": context["source_epoch"],
            "selections": [{"kind": "node", "record_id": node["node_id"], "action": "create",
                "facts": [{"field": field, "metadata": metadata} for field in ("label", "node_type")]}]}
        request["selections"].append({
            "kind": "placement", "record_id": proposal["candidate_node_id"], "action": "create",
            "metadata": metadata | {
                "claim_mode": "dungeonbuddy.claim:observed_event",
                "temporal_scope": {
                    "kind": "domain_ref", "schema_term": "dungeonbuddy.time:fictional_anchor_v1",
                    "payload": {"start": {"session": 8}},
                },
            },
        })
        before_prepare = repo.get_head(space)
        prepared_reply = fresh.post("/api/live/extract-promote/native-prepare", json=request)
        if prep_state:
            assert prepared_reply.status_code == 409, prepared_reply.text
            assert prepared_reply.json()["detail"]["code"] == "placement_requires_played_event"
            assert repo.get_head(space) == before_prepare
            return
        assert prepared_reply.status_code == 200, prepared_reply.text
        assert repo.get_head(space) == before_prepare
        prepared = prepared_reply.json()
        assert prepared["publication"] == "not_performed"
        assert repo.get_publication_receipt(space, prepared["envelope"]["prepared_change_id"]) is None
        assert prepared["envelope"]["review"]["run_id"] == run_id
        packet = {key: prepared[key] for key in ("envelope", "prepared", "token")}
        committed_reply = fresh.post("/api/live/extract-promote/native-confirm", json=packet)
        assert committed_reply.status_code == 200, committed_reply.text
        result = committed_reply.json()["result"]
        committed_head = repo.get_head(space)
        assert fresh.post("/api/live/extract-promote/native-confirm", json=packet).json()["result"] == result
        assert repo.get_head(space) == committed_head

    # Independent repository and APP readers bind actual committed values and source.
    reader = PostgresNativeSourceEvidenceRepository(PostgresDatabase(native_core_dsn))
    receipt = reader.get_publication_receipt(space, packet["envelope"]["prepared_change_id"])
    assert receipt.status == "published"
    assert receipt.published_revision_id == result["child_revision_id"]
    assert receipt.expected_parent_revision_id == before_prepare.head_revision_id
    child = reader.get_revision(space, result["child_revision_id"])
    assert reader.get_head(space).head_revision_id == child.revision.revision_id
    event_rows = [row for row in child.graph_payload["assertions"]
                  if row["subject_entity_id"] != campaign_object]
    assert {row["predicate"] for row in event_rows} == {
        "dnd5e:name", "dnd5e:classification", "dungeonbuddy.custom:on_timeline"}
    placement, = [row for row in event_rows if row["predicate"] == "dungeonbuddy.custom:on_timeline"]
    assert placement["value"] == {"kind": "entity_ref", "entity_id": campaign_object}
    assert placement["metadata"]["temporal_scope"]["payload"] == {"start": {"session": 8}}
    values = {row["predicate"]: row["value"] for row in event_rows}
    assert values["dnd5e:name"] == {"kind": "literal", "value": node["label"]}
    assert values["dnd5e:classification"] == {"kind": "term_ref", "term": "dungeonbuddy:event"}
    for row in event_rows:
        assert row["metadata"]["evidence_ref_ids"] == [evidence_id]
        assert row["metadata"]["scope"] == [
            {"axis": "dungeonbuddy.scope:campaign", "value": "longmont-c2"}]
    _, access = native.access_context(reader, space)
    opened = open_admitted_native_text(access, evidence_id)
    assert opened.status == "available"
    assert opened.source_artifact_id == admitted["source_artifact_id"]
    assert opened.source_revision_id == admitted["source_revision_id"]
    assert opened.body_sha256 == source.content_sha256
    assert opened.body_text.encode() == data.source_bytes
    assert (opened.span_start_byte, opened.span_end_byte) == (support_start, support_end)
    assert opened.span_sha256 == hashlib.sha256(reviewed_text).hexdigest()
    assert opened.body_text.encode()[opened.span_start_byte:opened.span_end_byte] == reviewed_text
    reopened = load_reviewable_extraction_data(root, run_id)
    assert (reopened.source_bytes, reopened.candidate_bytes, reopened.span_bytes) == frozen
    # The standard pytest report retains the exact join after fixture teardown.
    from fastapi.encoders import jsonable_encoder
    record_property("isolated_ingestion_publication_proof", json.dumps({
        "scope": "Structural fixture proof; no live model or semantic-quality claim",
        "run_id": run_id, "profile_id": data.run.profile_id,
        "source_artifact_id": source.source_artifact_id,
        "source_revision_id": str(source.source_revision_id),
        "source_sha256": source.content_sha256,
        "candidate_sha256": request["candidate_sha256"],
        "span_index_sha256": hashlib.sha256(data.span_bytes).hexdigest(),
        "reviewed_request": prepared["envelope"]["review"],
        "publication_receipt": jsonable_encoder(receipt),
        "fresh_assertions": child.graph_payload["assertions"],
        "fresh_source_evidence_id": evidence_id,
        "fresh_source_span": {"start_byte": opened.span_start_byte,
            "end_byte": opened.span_end_byte, "sha256": opened.span_sha256},
        "idempotent_confirmation_verified": True,
        "APP_source_candidate_and_span_bytes_unchanged": True,
    }, sort_keys=True))


@pytest.mark.parametrize("planning", [False, True])
def test_ordinary_process_proposes_event_placement_from_saved_recap(client_env, monkeypatch, planning):
    import graph_memory.extraction.graph_preview_runner as producer

    client, root = client_env
    extract = producer.extract_category_candidate_graph

    def extract_event(*args, **kwargs):
        result = extract(*args, **kwargs)
        node = result.candidate_graph["nodes"][0]
        node.update(label="The keeper scouts the road", node_type="event")
        if planning:
            node["semantic_state"].update(canon_state="planning_scaffold", authority_state="gm_prep")
        return result

    monkeypatch.setattr(producer, "extract_category_candidate_graph", extract_event)
    request = process_body(session=29)
    response = client.post("/api/live/recap-ingest", json=request)
    assert response.status_code == 200, response.text
    graph = response.json()["ingest_report"]["graph_preview"]
    data = load_reviewable_extraction_data(root, graph["extraction_run_id"])
    node, = json.loads(data.candidate_bytes)["nodes"]
    expected = {
        "candidate_node_id": node["node_id"],
        "status": "needs_review",
        "campaign_id": "longmont-c2",
        "start": {"session": 29},
        "source_span_ids": [node["evidence_refs"][0]["source_span_ref_id"]],
    }
    if planning:
        expected = {"candidate_node_id": node["node_id"], "status": "held", "reason": "not_played_history"}
    assert graph["event_placement_proposals"] == [expected]
    repeated = client.post("/api/live/recap-ingest", json=request)
    assert repeated.status_code == 200, repeated.text
    reused = repeated.json()["ingest_report"]["graph_preview"]
    assert reused["extraction_run_id"] == graph["extraction_run_id"]
    assert reused["event_placement_proposals"] == graph["event_placement_proposals"]
