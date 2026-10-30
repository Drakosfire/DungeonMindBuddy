"""Actual held-child service persistence in a uniquely named disposable APP DB."""
from __future__ import annotations

import copy
import json
import os
import subprocess
import sys
import time
from contextlib import contextmanager
from urllib.parse import urlsplit, urlunsplit
from uuid import NAMESPACE_URL, uuid4, uuid5

import psycopg
from psycopg import sql
import pytest

from application_state.cli import upgrade_to_head
from application_state.config import APPLICATION_STATE_DSN_ENV
from application_state.errors import ApplicationStateConflictError
from application_state.ingest import service as ingest
from apps.live_control_server.models.extract_promote import (
    RecapCandidateCorrectionRequestV8, RecapCandidateCorrectionRequestV9, RecapCandidateCorrectionRequestV10,
    RecapCandidateCorrectionRequestV11, RecapCandidateCorrectionResponseV10,
    RecapCandidateCorrectionResponseV11,
    RecapNodeDescriptionReplacement,
)
from apps.live_control_server.services import graph_run_registry as registry
from apps.live_control_server.services import recap_semantic_candidate_correction as correction
from apps.live_control_server.services.recap_semantic_disposition import assess_recap_semantics
from graph_memory.ingestion.extraction_run import ExtractionRun, ExtractionRunStatus
from tests.test_recap_semantic_candidate_correction import (
    _actor_recovery_request, _append_fixture, _append_request,
)


def _component_path(root, run, component):
    return root / run.components[component].uri.removeprefix("repo://")


@pytest.fixture
def disposable_append_app(monkeypatch):
    admin = os.environ.get("DMB_RAKE_PG_ADMIN_DSN")
    if not admin:
        pytest.fail("DMB_RAKE_PG_ADMIN_DSN must designate disposable PostgreSQL administration")
    name = "dungeonbuddy_app_state_test_rake_append_" + uuid4().hex[:12]
    parts = urlsplit(admin)
    dsn = urlunsplit((parts.scheme, parts.netloc, "/" + name, parts.query, parts.fragment))
    try:
        with psycopg.connect(admin, autocommit=True) as conn:
            conn.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
    except psycopg.Error as exc:
        pytest.fail("disposable database creation failed: " + type(exc).__name__)
    try:
        monkeypatch.setenv(APPLICATION_STATE_DSN_ENV, dsn)
        upgrade_to_head()  # Uses the checked-in Alembic head, including future compatible migrations.
        yield name
    finally:
        with psycopg.connect(admin, autocommit=True) as conn:
            conn.execute(
                "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                "WHERE datname = %s AND pid <> pg_backend_pid()",
                (name,),
            )
            conn.execute(sql.SQL("DROP DATABASE {}").format(sql.Identifier(name)))


def test_append_durable_child_fresh_read_retry_and_pc_proof(disposable_append_app, monkeypatch, tmp_path):
    original_get = registry.get_extraction_run
    original_create = registry.create_extraction_run
    original_update = registry.update_extraction_run_status
    original_resolve = correction.resolve_promotable_ingest_run
    original_span_loader = correction._load_frozen_span_index_for_resolved_run
    from application_state.source import service as source_service
    original_persist_source_markdown = source_service.persist_source_markdown
    original_descriptors = source_service.get_source_input_descriptors
    original_source_body = source_service.get_source_markdown
    from application_state.ingest import components as output_store
    original_persist_output = output_store.persist_component_payload
    original_review_data = registry.load_reviewable_extraction_data
    parent_fixture, _, _, pc_body, _, fixture_index = _append_fixture(monkeypatch, tmp_path)
    monkeypatch.setattr(output_store, "persist_component_payload", original_persist_output)
    monkeypatch.setattr(registry, "load_reviewable_extraction_data", original_review_data)
    monkeypatch.setattr(source_service, "persist_source_markdown", original_persist_source_markdown)
    monkeypatch.setattr(source_service, "get_source_input_descriptors", original_descriptors)
    monkeypatch.setattr(source_service, "get_source_markdown", original_source_body)
    monkeypatch.setattr(correction, "get_extraction_run", original_get)
    monkeypatch.setattr(correction, "create_extraction_run", original_create)
    monkeypatch.setattr(correction, "update_extraction_run_status", original_update)
    monkeypatch.setattr(correction, "resolve_promotable_ingest_run", original_resolve)
    monkeypatch.setattr(correction, "_load_frozen_span_index_for_resolved_run", original_span_loader)
    from apps.live_control_server.services import extract_promote
    monkeypatch.setattr(extract_promote, "_artifact_root", lambda: tmp_path)
    from apps.live_control_server.services.source_artifact_registry import (
        create_recap_source_artifact,
        source_span_index_path,
    )
    from graph_memory.ingestion.extraction_run import (
        ExtractionRunComponentKind,
        ExtractionRunComponentRef,
    )
    from graph_memory.source_span import document_source_ref_id

    source_bytes = (
        b"Lysandro found the key under the bridge while Mira watched.\n\n"
        b"Mira rescued a traveler.\n\n"
        b"Mira felt frightened.\n"
    )
    (tmp_path / "source.md").write_bytes(source_bytes)
    artifact = create_recap_source_artifact(
        tmp_path, world_id="invented-world", campaign_id="c", session_id="session-28",
        recap_text=source_bytes.decode("utf-8"),
    )
    span_path = source_span_index_path(tmp_path, artifact.source_artifact_id)
    span_bytes = span_path.read_bytes()
    index = json.loads(span_bytes)
    span_by_line = {
        line: span["source_span_id"]
        for span in index["spans"]
        for line in range(span["start_line"], span["end_line"] + 1)
    }
    fixture_span_line = {
        span["source_span_id"]: span["start_line"] for span in fixture_index["spans"]
    }
    payload = json.loads((tmp_path / "parent.json").read_bytes())
    source_ref_id = document_source_ref_id(artifact.source_artifact_id)
    for record in [*payload["nodes"], *payload["edges"]]:
        for evidence in record.get("evidence_refs", []):
            line = fixture_span_line[evidence["source_span_ref_id"]]
            evidence["source_artifact_id"] = artifact.source_artifact_id
            evidence["source_ref_id"] = source_ref_id
            evidence["source_span_ref_id"] = span_by_line[line]
            if line == 1:
                evidence["anchor_quotes"] = [source_bytes.decode("utf-8").splitlines()[0]]
    payload["source_artifact_ids"] = [artifact.source_artifact_id]
    payload["campaign_id"] = artifact.campaign_id
    payload["session_id"] = artifact.session_id
    candidate_bytes = correction._canonical_bytes(payload)
    run_dir = tmp_path / "out/graph_memory/ingest_runs/parent"
    run_dir.mkdir(parents=True)
    source_snapshot = run_dir / "source.md"
    candidate_path = run_dir / "candidate_graph.json"
    source_snapshot.write_bytes(source_bytes)
    candidate_path.write_bytes(candidate_bytes)
    components = {
        ExtractionRunComponentKind.SOURCE_ARTIFACT.value: ExtractionRunComponentRef(
            kind=ExtractionRunComponentKind.SOURCE_ARTIFACT,
            uri="repo://out/graph_memory/ingest_runs/parent/source.md",
            sha256=correction._sha(source_bytes), exists=True,
        ),
        ExtractionRunComponentKind.SOURCE_SPAN_INDEX.value: ExtractionRunComponentRef(
            kind=ExtractionRunComponentKind.SOURCE_SPAN_INDEX,
            uri=artifact.lineage["source_span_index_uri"],
            sha256=correction._sha(span_bytes), exists=True,
        ),
        ExtractionRunComponentKind.CANDIDATE_GRAPH.value: ExtractionRunComponentRef(
            kind=ExtractionRunComponentKind.CANDIDATE_GRAPH,
            uri="repo://out/graph_memory/ingest_runs/parent/candidate_graph.json",
            sha256=correction._sha(candidate_bytes), exists=True,
        ),
    }
    world_context = {
        "schema": "dm_world_campaign_ingest_context_v1",
        "managed_world_id": "managed-invented",
        "native_world_id": "invented-world",
        "binding_version": 1,
        "campaign_id": "c",
        "head_revision_id": "rev:head",
        "graph_schema": "world_graph_v1",
        "graph_payload_sha256": "a" * 64,
    }
    parent = original_create(
        tmp_path, run_id="parent", source_artifact_id=artifact.source_artifact_id,
        source_domain="recap", campaign_id=artifact.campaign_id,
        session_id=artifact.session_id, profile_id=correction.PROFILE,
        components=components, status=ExtractionRunStatus.DRAFT,
        lineage={"world_campaign_ingest_context": world_context},
    )
    for state in correction._LIFECYCLE[1:]:
        parent = original_update(
            tmp_path, parent.run_id, status=state, expected_revision=parent.revision,
        )
    raw = candidate_bytes
    pc_body.update(
        parent_run_id=parent.run_id,
        expected_parent_revision=parent.revision,
        parent_candidate_sha256=correction._sha(raw),
        source_revision_sha256=artifact.content_sha256,
        span_index_sha256=correction._sha(span_bytes),
        registry_path="corpus/invented/_party_registry.json",
    )
    pc_body["attachments"][0]["source_span_ref_id"] = span_by_line[1]
    pc_body["attachments"][0]["anchor_quote"] = source_bytes.decode("utf-8").splitlines()[0]
    pc_body["world_id"] = "invented-world"
    pc_body["expected_head_revision_id"] = "rev:head"
    pc_body["registry_sha256"] = correction._sha(
        (tmp_path / "corpus/invented/_party_registry.json").read_bytes()
    )
    monkeypatch.setattr(correction, "get_extraction_run", original_get)
    monkeypatch.setattr(correction, "create_extraction_run", original_create)
    monkeypatch.setattr(correction, "update_extraction_run_status", original_update)
    assert parent.status == ExtractionRunStatus.REVIEWABLE
    derived_root = tmp_path / "out/graph_memory/derived_candidates"
    packages_before = (
        {path.name for path in derived_root.iterdir() if path.is_dir()}
        if derived_root.exists() else set()
    )

    # The frozen run-local source is byte-authoritative. Even line-ending drift
    # must be rejected before a child row or package is created.
    source_snapshot.write_bytes(source_bytes.replace(b"\n", b"\r\n"))
    with pytest.raises(correction.ExtractPromoteError):
        correction.correct_recap_candidate(RecapCandidateCorrectionRequestV9.model_validate(pc_body))
    assert [run.run_id for run in ingest.list_extraction_runs()] == [parent.run_id]
    assert (
        {path.name for path in derived_root.iterdir() if path.is_dir()}
        if derived_root.exists() else set()
    ) == packages_before
    source_snapshot.write_bytes(source_bytes)

    # create_extraction_run persists the canonical source authority before it
    # inserts the child row. Simulate a process failure after that durable,
    # idempotent source write and prove the exact retry can continue cleanly.
    persisted_then_interrupted = False

    def persist_source_then_interrupt(**kwargs):
        nonlocal persisted_then_interrupted
        result = original_persist_source_markdown(**kwargs)
        if not persisted_then_interrupted:
            persisted_then_interrupted = True
            raise RuntimeError("injected interruption after source authority persistence")
        return result

    monkeypatch.setattr(source_service, "persist_source_markdown", persist_source_then_interrupt)
    with pytest.raises(RuntimeError, match="after source authority persistence"):
        correction.correct_recap_candidate(RecapCandidateCorrectionRequestV9.model_validate(pc_body))
    assert persisted_then_interrupted
    assert [run.run_id for run in ingest.list_extraction_runs()] == [parent.run_id]
    durable_source = source_service.get_source_markdown(
        source_artifact_id=artifact.source_artifact_id,
        content_sha256=artifact.content_sha256,
    )
    assert durable_source is not None
    assert durable_source.markdown.encode("utf-8") == source_bytes
    # No deterministic child package was published before the failed row claim.
    packages_after = (
        {path.name for path in derived_root.iterdir() if path.is_dir()}
        if derived_root.exists() else set()
    )
    assert packages_after == packages_before
    already_durable = original_persist_source_markdown(
        source_artifact_id=artifact.source_artifact_id,
        source_domain="recap", campaign_id=artifact.campaign_id,
        session_id=artifact.session_id, world_id=artifact.world_id,
        markdown=source_bytes.decode("utf-8"), content_sha256=artifact.content_sha256,
        lineage={"adopted_from_uri": artifact.uri},
    )
    assert already_durable.source_artifact_id == artifact.source_artifact_id
    with pytest.raises(ApplicationStateConflictError):
        original_persist_source_markdown(
            source_artifact_id=artifact.source_artifact_id,
            source_domain="recap", campaign_id="foreign-campaign",
            session_id=artifact.session_id, world_id=artifact.world_id,
            markdown=source_bytes.decode("utf-8"), content_sha256=artifact.content_sha256,
            lineage={"adopted_from_uri": artifact.uri},
        )
    monkeypatch.setattr(source_service, "persist_source_markdown", original_persist_source_markdown)
    pc_response = correction.correct_recap_candidate(RecapCandidateCorrectionRequestV9.model_validate(pc_body))
    pc_parent = original_get(tmp_path, pc_response.run_id)
    pc_path = _component_path(tmp_path, pc_parent, "candidate_graph")
    pc_bytes = pc_path.read_bytes()
    payload = json.loads(pc_bytes)
    def append_request(run, graph, *, kind="node", identifier="mira", line=2):
        collection, key = ("nodes", "node_id") if kind == "node" else ("edges", "edge_id")
        record = next(value for value in graph[collection] if value[key] == identifier)
        source_line = line * 2 - 1
        quote = source_bytes.decode("utf-8").splitlines()[source_line - 1]
        return {
            "schema": "dmb_recap_candidate_correction_request_v10",
            "parent_run_id": run.run_id,
            "expected_parent_revision": run.revision,
            "parent_candidate_sha256": run.components["candidate_graph"].sha256.removeprefix("sha256:"),
            "source_revision_sha256": artifact.content_sha256,
            "span_index_sha256": correction._sha(span_bytes),
            "profile_id": correction.PROFILE,
            "evidence_appends": [{
                "record_kind": kind,
                "record_id": identifier,
                "expected_evidence_refs_sha256": correction._sha(
                    correction._canonical_bytes(record["evidence_refs"])
                ),
                "source_span_ref_id": span_by_line[source_line],
                "anchor_quotes": [quote],
            }],
        }

    body = append_request(pc_parent, payload)
    second = append_request(pc_parent, payload, kind="edge", identifier="edge-bridge", line=3)
    body["evidence_appends"].extend(second["evidence_appends"])

    worker_code = """
import json,sys,time
from pathlib import Path
from apps.live_control_server.models.extract_promote import RecapCandidateCorrectionRequestV10
from apps.live_control_server.services import extract_promote
import apps.live_control_server.services.recap_semantic_candidate_correction as correction
from graph_memory import party_context
root=Path(sys.argv[1]);body=json.loads(Path(sys.argv[2]).read_text())
correction.repo_root=lambda:root
extract_promote._artifact_root=lambda:root
party_context.CAMPAIGN_CORPUS['c']=(Path('corpus'),'invented')
ready=Path(sys.argv[3]);release=Path(sys.argv[4]);ready.write_text('ready')
deadline=time.monotonic()+20
while not release.exists():
    if time.monotonic() > deadline: raise RuntimeError('concurrency barrier timed out')
    time.sleep(0.01)
result=correction.correct_recap_candidate(RecapCandidateCorrectionRequestV10.model_validate(body))
print(json.dumps(result.model_dump(mode='json',by_alias=True)))
"""
    barrier = tmp_path / "concurrent-identical-request"
    barrier.mkdir()
    request_path = barrier / "request.json"
    release_path = barrier / "release"
    request_path.write_text(json.dumps(body))
    workers = [
        subprocess.Popen(
            [sys.executable, "-c", worker_code, str(tmp_path), str(request_path),
             str(barrier / f"ready-{index}"), str(release_path)],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        )
        for index in range(2)
    ]
    try:
        deadline = time.monotonic() + 20
        while not all((barrier / f"ready-{index}").exists() for index in range(2)):
            if time.monotonic() > deadline:
                pytest.fail("both independent correction processes did not reach the barrier")
            time.sleep(0.01)
        release_path.write_text("go")
        outputs = [worker.communicate(timeout=30) for worker in workers]
    finally:
        for worker in workers:
            if worker.poll() is None:
                worker.kill()
                worker.communicate()
    assert all(worker.returncode == 0 for worker in workers), [output[1] for output in outputs]
    responses = [json.loads(output[0]) for output in outputs]
    assert responses[0] == responses[1]
    response = RecapCandidateCorrectionResponseV10.model_validate(responses[0])
    child = original_get(tmp_path, response.run_id)
    actual = json.loads(_component_path(tmp_path, child, "candidate_graph").read_bytes())
    for group in ("nodes", "edges"):
        assert actual[group][0]["evidence_refs"][:-1] == payload[group][0]["evidence_refs"]
    assert actual["nodes"][0]["corpus_ref"] == payload["nodes"][0]["corpus_ref"]
    assert pc_path.read_bytes() == pc_bytes
    assert _component_path(tmp_path, parent, "candidate_graph").read_bytes() == raw
    assert (tmp_path / "source.md").read_bytes() == source_bytes
    assert span_path.read_bytes() == span_bytes
    assert child.lineage["semantic_disposition"]["state"] == "held"
    assert len(ingest.list_extraction_runs()) == 3
    fresh_code = """
import json,sys
from pathlib import Path
from application_state.ingest.service import get_extraction_run
from apps.live_control_server.services.recap_semantic_candidate_correction import inherited_pc_reference_proof,verify_child_replay
import apps.live_control_server.services.recap_semantic_candidate_correction as correction
from graph_memory import party_context
from apps.live_control_server.services.recap_semantic_disposition import assess_recap_semantics
root=Path(sys.argv[1]);correction.repo_root=lambda: root
party_context.CAMPAIGN_CORPUS['c']=(Path('corpus'),'invented')
child=get_extraction_run(sys.argv[2]);parent=get_extraction_run(sys.argv[3])
assert verify_child_replay(child,parent,root)
proof=inherited_pc_reference_proof(child,root)
assert proof==child.lineage['inherited_pc_proof'] and proof['rows'][0]['origin_run_id']==parent.run_id
assessment=assess_recap_semantics(child,parent=parent,source_revision_id=sys.argv[4],root=root)
assert assessment.marked and not assessment.accepted and assessment.basis['schema']=='dmb_recap_semantic_basis_v12'
print(json.dumps({'revision':child.revision,'state':child.lineage['semantic_disposition']['state'],'proof_origin':proof['rows'][0]['origin_run_id']}))
"""
    output = subprocess.check_output([sys.executable, "-c", fresh_code, str(tmp_path), child.run_id,
                                      pc_parent.run_id, body["source_revision_sha256"]], text=True)
    assert json.loads(output)["state"] == "held"
    assessment = assess_recap_semantics(child, parent=pc_parent, source_revision_id=body["source_revision_sha256"], root=tmp_path)
    basis = ingest.RecapSemanticBasisV12.model_validate(assessment.basis, strict=True)
    # The actual APP CAS must reject a forged inherited proof, leaving the held child untouched.
    forged_operation = basis.operation_basis.model_copy(
        update={"inherited_pc_proof_sha256": "0" * 64},
    )
    forged = basis.model_copy(update={"operation_basis": forged_operation})
    with pytest.raises(ApplicationStateConflictError):
        ingest.record_recap_semantic_disposition(child.run_id, expected_revision=child.revision, basis=forged,
            decision=ingest.RecapSemanticDispositionCommandV1(state="accepted", reviewer_id="synthetic-reviewer", review_decision_ref="synthetic:reject-forged-proof"))
    for fault in ("parent", "source", "quote", "unknown", "existing", "preimage"):
        bad = copy.deepcopy(body)
        if fault == "parent":
            bad["expected_parent_revision"] += 1
        elif fault == "source":
            bad["source_revision_sha256"] = "0" * 64
        elif fault == "quote":
            bad["evidence_appends"][0]["anchor_quotes"] = ["forged quote"]
        elif fault == "unknown":
            bad["evidence_appends"][0]["record_id"] = "unknown"
        elif fault == "existing":
            bad["evidence_appends"][0].update(source_span_ref_id=index["spans"][0]["source_span_id"], anchor_quotes=["Mira found the key under the bridge."])
        else:
            bad["evidence_appends"][0]["expected_evidence_refs_sha256"] = "0" * 64
        with pytest.raises(correction.ExtractPromoteError):
            correction.correct_recap_candidate(RecapCandidateCorrectionRequestV10.model_validate(bad))
        assert len(ingest.list_extraction_runs()) == 3
    assert original_get(tmp_path, child.run_id).revision == child.revision
    assert original_get(tmp_path, child.run_id).lineage["semantic_disposition"]["state"] == "held"

    # Historical legacy rows are checked against their deterministic old ID
    # before the new V11 child can be claimed. Use a canonical-source parent so
    # the old (source-URI-preserving) child can be genuinely REVIEWABLE.
    legacy_parent_dir = tmp_path / "out/graph_memory/ingest_runs/legacy-parent"
    legacy_parent_dir.mkdir(parents=True)
    legacy_parent_candidate = legacy_parent_dir / "candidate_graph.json"
    legacy_parent_candidate.write_bytes(raw)
    legacy_parent_components = dict(components)
    legacy_parent_components["source_artifact"] = components["source_artifact"].model_copy(
        update={"uri": artifact.uri, "sha256": artifact.content_sha256},
    )
    legacy_parent_components["candidate_graph"] = components["candidate_graph"].model_copy(
        update={
            "uri": "repo://out/graph_memory/ingest_runs/legacy-parent/candidate_graph.json",
            "sha256": correction._sha(raw),
        },
    )
    legacy_parent = original_create(
        tmp_path, run_id="legacy-parent", source_artifact_id=artifact.source_artifact_id,
        source_domain="recap", campaign_id=artifact.campaign_id,
        session_id=artifact.session_id, profile_id=correction.PROFILE,
        components=legacy_parent_components, status=ExtractionRunStatus.DRAFT,
        lineage={"world_campaign_ingest_context": world_context},
    )
    for state in correction._LIFECYCLE[1:]:
        legacy_parent = original_update(
            tmp_path, legacy_parent.run_id, status=state,
            expected_revision=legacy_parent.revision,
        )

    def seed_legacy_v9(body, state):
        request = RecapCandidateCorrectionRequestV9.model_validate(body)
        manifest = request.model_dump(
            mode="json", exclude={"schema_", "parent_run_id", "parent_candidate_sha256"},
        )
        manifest["schema"] = correction.MANIFEST_SCHEMA_V9
        manifest["attachments"].sort(key=lambda item: item["node_id"])
        manifest_sha = correction._sha(correction._canonical_bytes(manifest))
        legacy_id = str(uuid5(
            NAMESPACE_URL,
            f"dmb:{correction.DERIVATION_V9}:{legacy_parent.run_id}:"
            f"{correction._sha(raw)}:{manifest_sha}",
        ))
        relative_candidate = (
            f"out/graph_memory/derived_candidates/{legacy_id}/candidate_graph.json"
        )
        candidate = correction.replay_candidate(
            json.loads(raw), manifest, source_bytes=source_bytes, span_bytes=span_bytes,
        )
        candidate_bytes = correction._canonical_bytes(candidate)
        directory = tmp_path / "out/graph_memory/derived_candidates" / legacy_id
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "candidate_graph.json").write_bytes(candidate_bytes)
        if state == "orphan":
            return legacy_id

        lineage = {
            "derivation": correction.DERIVATION_V9,
            "parent_run_id": legacy_parent.run_id,
            "parent_candidate_sha256": correction._sha(raw),
            "manifest_sha256": manifest_sha,
            "semantic_candidate_manifest": manifest,
            "world_campaign_ingest_context": world_context,
        }
        legacy_components = dict(legacy_parent.components)
        legacy_components["candidate_graph"] = legacy_components["candidate_graph"].model_copy(
            update={"uri": relative_candidate, "sha256": correction._sha(candidate_bytes)},
        )
        provisional = ExtractionRun(
            run_id=legacy_id, source_artifact_id=artifact.source_artifact_id,
            source_domain="recap", campaign_id=artifact.campaign_id,
            session_id=artifact.session_id, profile_id=correction.PROFILE,
            status=ExtractionRunStatus.REVIEWABLE, components=legacy_components,
            lineage=copy.deepcopy(lineage),
        )
        if state != "mismatched":
            assessment = assess_recap_semantics(
                provisional, parent=legacy_parent,
                source_revision_id=artifact.content_sha256, root=tmp_path,
            )
            assert assessment.basis_sha256 is not None
            lineage["semantic_disposition"] = {
                "version": 1, "state": "held",
                "basis_sha256": assessment.basis_sha256,
            }
        else:
            lineage["manifest_sha256"] = "0" * 64
        legacy = original_create(
            tmp_path, run_id=legacy_id, source_artifact_id=artifact.source_artifact_id,
            source_domain="recap", campaign_id=artifact.campaign_id,
            session_id=artifact.session_id, profile_id=correction.PROFILE,
            components=legacy_components, status=ExtractionRunStatus.DRAFT,
            lineage=lineage,
        )
        if state in {"exact", "mismatched"}:
            for next_state in correction._LIFECYCLE[1:]:
                legacy = original_update(
                    tmp_path, legacy.run_id, status=next_state,
                    expected_revision=legacy.revision,
                )
        return legacy_id

    for state in ("exact", "stranded_draft", "mismatched", "orphan"):
        request_body = {
            **pc_body,
            "parent_run_id": legacy_parent.run_id,
            "expected_parent_revision": legacy_parent.revision,
            "review_decision_ref": f"synthetic:legacy-{state}",
        }
        legacy_id = seed_legacy_v9(request_body, state)
        row_ids_before = {run.run_id for run in ingest.list_extraction_runs()}
        if state == "exact":
            reused = correction.correct_recap_candidate(
                RecapCandidateCorrectionRequestV9.model_validate(request_body),
            )
            assert reused.run_id == legacy_id
        else:
            with pytest.raises(correction.ExtractPromoteError, match=legacy_id):
                correction.correct_recap_candidate(
                    RecapCandidateCorrectionRequestV9.model_validate(request_body),
                )
        row_ids_after = {run.run_id for run in ingest.list_extraction_runs()}
        assert row_ids_after == row_ids_before
        assert not (tmp_path / "out/graph_memory/derived_candidates" / legacy_id / "source.md").exists()

    # Kill the lock owner after its DRAFT row claim. The kernel must release
    # flock, and the next exact process must resume the registered row without
    # adopting or deleting a stale temporary file left by its predecessor.
    crash_body = _append_request(pc_parent, payload, index, identifier="bridge", line=2)
    before_crash_rows = {run.run_id for run in ingest.list_extraction_runs()}
    crash_worker = """
import json,os,sys
from pathlib import Path
from apps.live_control_server.models.extract_promote import RecapCandidateCorrectionRequestV10
from apps.live_control_server.services import extract_promote
import apps.live_control_server.services.recap_semantic_candidate_correction as correction
from graph_memory import party_context
root=Path(sys.argv[1]); body=json.loads(Path(sys.argv[2]).read_text())
correction.repo_root=lambda:root
extract_promote._artifact_root=lambda:root
party_context.CAMPAIGN_CORPUS['c']=(Path('corpus'),'invented')
def die_after_draft(root, child_id, *, source_bytes, candidate_bytes, allow_existing):
    staging=root/'out/graph_memory/derived_candidates/.staging'
    staging.mkdir(parents=True,exist_ok=True)
    (staging/f'{child_id}.prior-owner.tmp').write_bytes(b'preserve crashed owner staging bytes')
    os._exit(77)
correction._publish_child_package_files=die_after_draft
correction.correct_recap_candidate(RecapCandidateCorrectionRequestV10.model_validate(body))
raise RuntimeError('injected crash point was not reached')
"""
    crash_request_path = tmp_path / "crashed-owner-request.json"
    crash_request_path.write_text(json.dumps(crash_body))
    crashed = subprocess.run(
        [sys.executable, "-c", crash_worker, str(tmp_path), str(crash_request_path)],
        capture_output=True, text=True, timeout=30,
    )
    assert crashed.returncode == 77, crashed.stderr
    after_crash_rows = {run.run_id for run in ingest.list_extraction_runs()}
    assert len(after_crash_rows - before_crash_rows) == 1
    stranded_id = (after_crash_rows - before_crash_rows).pop()
    stranded = original_get(tmp_path, stranded_id)
    assert stranded.status == ExtractionRunStatus.DRAFT
    assert not (tmp_path / "out/graph_memory/derived_candidates" / stranded_id).exists()
    abandoned_staging = (
        tmp_path / "out/graph_memory/derived_candidates/.staging"
        / f"{stranded_id}.prior-owner.tmp"
    )
    assert abandoned_staging.read_bytes() == b"preserve crashed owner staging bytes"
    recovered = correction.correct_recap_candidate(
        RecapCandidateCorrectionRequestV10.model_validate(crash_body),
    )
    assert recovered.run_id == stranded_id
    assert original_get(tmp_path, stranded_id).status == ExtractionRunStatus.REVIEWABLE
    assert abandoned_staging.read_bytes() == b"preserve crashed owner staging bytes"

    # V11 keeps the same durable child/retry boundary while adding one source-
    # supported local actor and a bounded endpoint correction.
    actor_parent = original_get(tmp_path, pc_parent.run_id)
    actor_parent_payload = json.loads(_component_path(
        tmp_path, actor_parent, "candidate_graph",
    ).read_bytes())
    actor_source_text = source_bytes.decode("utf-8")
    actor_body = _actor_recovery_request(
        actor_parent, actor_parent_payload, index, actor_source_text,
    )
    actor_request = RecapCandidateCorrectionRequestV11.model_validate(
        actor_body, strict=True,
    )
    actor_response = correction.correct_recap_candidate(actor_request)
    assert isinstance(actor_response, RecapCandidateCorrectionResponseV11)
    assert (actor_response.introduced_actor_count, actor_response.retargeted_edge_count,
            actor_response.omitted_edge_count) == (1, 1, 0)
    actor_child = original_get(tmp_path, actor_response.run_id)
    actor_payload = json.loads(_component_path(
        tmp_path, actor_child, "candidate_graph",
    ).read_bytes())
    actor_node = actor_payload["nodes"][-1]
    assert actor_node["label"] == "Lysandro" and actor_node["corpus_ref"] is None
    assert actor_payload["edges"][0]["from_node_id"] == actor_node["node_id"]
    assert actor_payload["edges"][0]["evidence_refs"] == actor_parent_payload["edges"][0]["evidence_refs"]
    assert correction.verify_child_replay(actor_child, actor_parent, tmp_path)
    assert correction.correct_recap_candidate(actor_request).model_dump(
        mode="json", by_alias=True,
    ) == actor_response.model_dump(mode="json", by_alias=True)
    actor_assessment = assess_recap_semantics(
        actor_child, parent=actor_parent,
        source_revision_id=actor_body["source_revision_sha256"], root=tmp_path,
    )
    actor_basis = ingest.RecapSemanticBasisV12.model_validate(
        actor_assessment.basis, strict=True,
    )
    assert actor_basis.request_version == 11
    assert actor_basis.operation_basis.schema_ == "dmb_recap_semantic_basis_v13"
    monkeypatch.setattr(extract_promote, "resolve_promotable_ingest_run", original_resolve)
    actor_package = extract_promote.get_exact_run_review_package(actor_child.run_id)
    assert any(assertion.label == "Lysandro" for assertion in actor_package.assertions)
    assert actor_package.inherited_pc_references is not None
    assert actor_package.inherited_pc_references.rows[0].origin_run_id == actor_parent.run_id

    fresh_actor_code = """
import json,sys
from pathlib import Path
from application_state.ingest.service import get_extraction_run
from apps.live_control_server.services.recap_semantic_candidate_correction import verify_child_replay
import apps.live_control_server.services.recap_semantic_candidate_correction as correction
from graph_memory import party_context
root=Path(sys.argv[1]); correction.repo_root=lambda:root
party_context.CAMPAIGN_CORPUS['c']=(Path('corpus'),'invented')
child=get_extraction_run(sys.argv[2]); parent=get_extraction_run(sys.argv[3])
assert verify_child_replay(child,parent,root)
candidate=json.loads((root/child.components['candidate_graph'].uri.removeprefix('repo://')).read_bytes())
assert candidate['nodes'][-1]['label']=='Lysandro'
print(json.dumps({'run_id':child.run_id,'status':child.status.value,'actor':candidate['nodes'][-1]['label']}))
"""
    fresh_actor = subprocess.check_output(
        [sys.executable, "-c", fresh_actor_code, str(tmp_path), actor_child.run_id,
         actor_parent.run_id], text=True,
    )
    assert json.loads(fresh_actor)["actor"] == "Lysandro"

    # A distinct omission-only request gives the crash-resume test its own
    # deterministic child identity while preserving the successful retarget.
    crash_actor_body = _actor_recovery_request(
        actor_parent, actor_parent_payload, index, actor_source_text, action="omit",
    )
    crash_actor_path = tmp_path / "actor-recovery-crash-request.json"
    crash_actor_path.write_text(json.dumps(crash_actor_body))
    before_actor_crash = {run.run_id for run in ingest.list_extraction_runs()}
    crash_actor_worker = """
import json,os,sys
from pathlib import Path
from apps.live_control_server.models.extract_promote import RecapCandidateCorrectionRequestV11
from apps.live_control_server.services import extract_promote
import apps.live_control_server.services.recap_semantic_candidate_correction as correction
from graph_memory import party_context
root=Path(sys.argv[1]); body=json.loads(Path(sys.argv[2]).read_text())
correction.repo_root=lambda:root; extract_promote._artifact_root=lambda:root
party_context.CAMPAIGN_CORPUS['c']=(Path('corpus'),'invented')
def die_after_draft(root, child_id, *, source_bytes, candidate_bytes, allow_existing):
    staging=root/'out/graph_memory/derived_candidates/.staging'
    staging.mkdir(parents=True,exist_ok=True)
    (staging/f'{child_id}.actor-recovery.tmp').write_bytes(b'preserve actor recovery staging')
    os._exit(78)
correction._publish_child_package_files=die_after_draft
correction.correct_recap_candidate(RecapCandidateCorrectionRequestV11.model_validate(body))
raise RuntimeError('injected actor recovery crash point was not reached')
"""
    crashed_actor = subprocess.run(
        [sys.executable, "-c", crash_actor_worker, str(tmp_path), str(crash_actor_path)],
        capture_output=True, text=True, timeout=30,
    )
    assert crashed_actor.returncode == 78, crashed_actor.stderr
    new_actor_rows = {run.run_id for run in ingest.list_extraction_runs()} - before_actor_crash
    assert len(new_actor_rows) == 1
    stranded_actor_id = next(iter(new_actor_rows))
    stranded_actor = original_get(tmp_path, stranded_actor_id)
    assert stranded_actor.status == ExtractionRunStatus.DRAFT
    recovered_actor = correction.correct_recap_candidate(
        RecapCandidateCorrectionRequestV11.model_validate(crash_actor_body, strict=True),
    )
    assert recovered_actor.run_id == stranded_actor_id
    assert original_get(tmp_path, stranded_actor_id).status == ExtractionRunStatus.REVIEWABLE
    assert correction.verify_child_replay(
        original_get(tmp_path, stranded_actor_id), actor_parent, tmp_path,
    )


def test_production_source_snapshot_correction_and_locked_parent_authority(
    disposable_append_app, monkeypatch, tmp_path,
):
    """Exercise producer-owned snapshots, a real held correction, and stale parent rejection."""
    from apps.live_control_server.services import extract_promote
    from apps.live_control_server.services.source_artifact_registry import (
        create_recap_source_artifact,
    )
    from src.graph_memory import party_context
    from graph_memory.ingestion.extraction_run import ExtractionRunStatus
    from src.graph_memory.extraction.category_candidate_graph_extractor import (
        FixtureCategoryGraphPassClient,
    )
    from src.graph_memory.extraction.graph_preview_runner import (
        ProductionExtractionRequest,
        run_production_extraction,
    )
    from src.graph_memory.extraction.recap_extraction_profile import (
        RECAP_PROFILE_ID,
        RECAP_PROFILE_VERSION,
    )
    from apps.live_control_server.services.graph_preview_runner import (
        _normalized_from_registered,
    )

    monkeypatch.setattr(correction, "repo_root", lambda: tmp_path)
    monkeypatch.setattr(extract_promote, "_artifact_root", lambda: tmp_path)
    empty_corpus = tmp_path / "empty-synthetic-corpus"
    empty_corpus.mkdir()
    campaign_id = "synthetic-campaign"
    world_id = "synthetic-world"
    session_id = "session-1"
    monkeypatch.setitem(
        party_context.CAMPAIGN_CORPUS, campaign_id, (empty_corpus, "Synthetic"),
    )

    source_text = (
        "Mira crossed the painted bridge. The brass key remained hidden. "
        "Lysandro found the key under the bridge, and Mira confirmed he waits at the guard headquarters.\n"
    )
    artifact = create_recap_source_artifact(
        tmp_path,
        world_id=world_id,
        campaign_id=campaign_id,
        session_id=session_id,
        recap_text=source_text,
    )
    source = _normalized_from_registered(tmp_path, artifact.source_artifact_id)
    span_id = source.source_span_index["spans"][0]["source_span_id"]
    fixture_client = FixtureCategoryGraphPassClient({
        "actor_pass": {"observation_nodes": [{
            "node_id": "mira",
            "label": "Mira Vale",
            "node_type": "character",
            "description": "Mira crossed the painted bridge.",
            "importance": "medium",
            "evidence_refs": [{
                "source_span_ref_id": span_id,
                "anchor_quotes": ["Mira crossed the painted bridge."],
            }],
        }]},
        "location_pass": {"observation_nodes": [{
            "node_id": "guard-hq",
            "label": "Guard Headquarters",
            "node_type": "location",
            "description": "The guard headquarters mentioned in the recap.",
            "importance": "medium",
            "evidence_refs": [{
                "source_span_ref_id": span_id,
                "anchor_quotes": ["guard headquarters"],
            }],
        }]},
        "collective_pass": {"observation_nodes": []},
        "object_pass": {"observation_nodes": []},
        "thread_pass": {"observation_nodes": [], "ignored_items": [], "deferred_items": []},
        "beat_pass": {"observation_beats": []},
        "edge_pass": {"observation_edges": [{
            "edge_id": "edge-lysandro-headquarters",
            "from_node_id": "mira",
            "to_node_id": "guard-hq",
            "relationship_type": "located_in",
            "predicate_family": "spatial",
            "label": "Lysandro waits at the guard headquarters.",
            "evidence_refs": [{
                "source_span_ref_id": span_id,
                "anchor_quotes": ["Mira confirmed he waits at the guard headquarters."],
            }],
        }]},
    })

    def produce_parent():
        produced = run_production_extraction(ProductionExtractionRequest(
            repo_root=tmp_path,
            source=source,
            profile_id=RECAP_PROFILE_ID,
            profile_version=RECAP_PROFILE_VERSION,
            model_id="fixture-no-provider",
            allow_llm=False,
            category_client=fixture_client,
            initial_lineage={
                "native_world_id": world_id,
                "campaign_id": campaign_id,
            },
        ))
        assert produced.failure_kind is None, produced.diagnostics
        assert produced.run.status == ExtractionRunStatus.REVIEWABLE
        return ingest.get_extraction_run(produced.run.run_id)

    def correction_request(parent, replacement):
        candidate_path = _component_path(tmp_path, parent, "candidate_graph")
        candidate_bytes = candidate_path.read_bytes()
        candidate = json.loads(candidate_bytes)
        node = next(record for record in candidate["nodes"] if record["node_id"] == "mira")
        return RecapCandidateCorrectionRequestV8.model_validate({
            "schema": "dmb_recap_candidate_correction_request_v8",
            "parent_run_id": parent.run_id,
            "parent_candidate_sha256": correction._sha(candidate_bytes),
            "expected_parent_revision": parent.revision,
            "source_revision_sha256": artifact.content_sha256,
            "span_index_sha256": parent.components["source_span_index"].sha256.removeprefix("sha256:"),
            "profile_id": parent.profile_id,
            "node_description_replacements": [RecapNodeDescriptionReplacement(
                node_id=node["node_id"],
                original_description=node["description"],
                replacement_description=replacement,
            ).model_dump(mode="json")],
        })

    # The actual producer writes and registers its source.md and span index.
    parent = produce_parent()
    source_path = _component_path(tmp_path, parent, "source_artifact")
    span_path = _component_path(tmp_path, parent, "source_span_index")
    candidate_path = _component_path(tmp_path, parent, "candidate_graph")
    parent_source_bytes = source_path.read_bytes()
    parent_span_bytes = span_path.read_bytes()
    parent_candidate_bytes = candidate_path.read_bytes()
    assert parent_source_bytes == source.source_text.encode("utf-8")
    assert json.loads(parent_span_bytes)["source_artifact_id"] == artifact.source_artifact_id

    request = correction_request(parent, "Mira deliberately crossed the painted bridge.")
    response = correction.correct_recap_candidate(request)
    assert response.semantic_state == "held"
    fresh_child = ingest.get_extraction_run(response.run_id)
    assert fresh_child.status == ExtractionRunStatus.REVIEWABLE
    assert correction.verify_child_replay(fresh_child, parent, tmp_path)
    assessment = assess_recap_semantics(
        fresh_child,
        parent=parent,
        source_revision_id=artifact.content_sha256,
        root=tmp_path,
    )
    assert assessment.marked and not assessment.accepted
    assert assessment.basis is not None
    assert assessment.basis["schema"] == "dmb_recap_semantic_basis_v12"
    basis = fresh_child.lineage["semantic_source_binding_basis_v12"]
    assert basis["source_artifact_id"] == artifact.source_artifact_id
    assert basis["source_revision_sha256"] == artifact.content_sha256
    assert _component_path(tmp_path, fresh_child, "source_artifact").read_bytes() == parent_source_bytes
    assert _component_path(tmp_path, parent, "source_artifact").read_bytes() == parent_source_bytes
    assert _component_path(tmp_path, parent, "source_span_index").read_bytes() == parent_span_bytes
    assert _component_path(tmp_path, parent, "candidate_graph").read_bytes() == parent_candidate_bytes
    retry = correction.correct_recap_candidate(request)
    assert retry.run_id == fresh_child.run_id
    assert ingest.get_extraction_run(fresh_child.run_id).revision == fresh_child.revision

    # Join the actual producer output to V11 recovery: extraction intentionally
    # omits Lysandro and misbinds the located_in assertion to Mira. The source-
    # supported child adds only Lysandro and retargets only that declared edge.
    production_candidate = json.loads(parent_candidate_bytes)
    actor_request_body = _actor_recovery_request(
        parent, production_candidate, source.source_span_index, source_text,
        edge_id="edge-lysandro-headquarters",
    )
    actor_request = RecapCandidateCorrectionRequestV11.model_validate(
        actor_request_body, strict=True,
    )
    actor_result = correction.correct_recap_candidate(actor_request)
    assert actor_result.semantic_state == "held"
    actor_child = ingest.get_extraction_run(actor_result.run_id)
    actor_candidate_bytes = _component_path(
        tmp_path, actor_child, "candidate_graph",
    ).read_bytes()
    actor_candidate = json.loads(actor_candidate_bytes)
    actor_node = actor_candidate["nodes"][-1]
    assert actor_node["label"] == "Lysandro"
    assert actor_node["corpus_ref"] is None
    assert actor_candidate["nodes"] == production_candidate["nodes"] + [actor_node]
    expected_edges = copy.deepcopy(production_candidate["edges"])
    expected_edge = next(
        edge for edge in expected_edges
        if edge["edge_id"] == "edge-lysandro-headquarters"
    )
    expected_edge["from_node_id"] = actor_node["node_id"]
    actual_edge = next(
        edge for edge in actor_candidate["edges"]
        if edge["edge_id"] == "edge-lysandro-headquarters"
    )
    assert actor_candidate["edges"] == expected_edges
    assert actual_edge["evidence_refs"] == next(
        edge["evidence_refs"] for edge in production_candidate["edges"]
        if edge["edge_id"] == "edge-lysandro-headquarters"
    )
    for key in ("beats", "proposed_writes", "ignored_items", "deferred_items"):
        assert actor_candidate.get(key, []) == production_candidate.get(key, [])
    assert _component_path(tmp_path, actor_child, "source_artifact").read_bytes() == parent_source_bytes
    assert source_path.read_bytes() == parent_source_bytes
    assert span_path.read_bytes() == parent_span_bytes
    assert candidate_path.read_bytes() == parent_candidate_bytes
    actor_assessment = assess_recap_semantics(
        actor_child, parent=parent,
        source_revision_id=artifact.content_sha256, root=tmp_path,
    )
    assert actor_assessment.marked and not actor_assessment.accepted
    actor_basis = ingest.RecapSemanticBasisV12.model_validate(
        actor_assessment.basis, strict=True,
    )
    assert actor_basis.request_version == 11
    assert actor_basis.operation_basis.schema_ == "dmb_recap_semantic_basis_v13"
    assert correction.verify_child_replay(actor_child, parent, tmp_path)
    actor_retry = correction.correct_recap_candidate(actor_request)
    assert actor_retry.run_id == actor_child.run_id
    assert ingest.get_extraction_run(actor_child.run_id).revision == actor_child.revision
    fresh_actor_code = """
import json,sys
from pathlib import Path
from application_state.ingest.service import RecapSemanticBasisV12, get_extraction_run
from apps.live_control_server.services.recap_semantic_candidate_correction import verify_child_replay
from apps.live_control_server.services.recap_semantic_disposition import assess_recap_semantics
import apps.live_control_server.services.recap_semantic_candidate_correction as correction
from graph_memory import party_context
root=Path(sys.argv[1]); correction.repo_root=lambda:root
party_context.CAMPAIGN_CORPUS['synthetic-campaign']=(root/'empty-synthetic-corpus','Synthetic')
child=get_extraction_run(sys.argv[2]); parent=get_extraction_run(sys.argv[3])
assert verify_child_replay(child,parent,root)
assessment=assess_recap_semantics(child,parent=parent,source_revision_id=sys.argv[4],root=root)
assert assessment.marked and not assessment.accepted
basis=RecapSemanticBasisV12.model_validate(assessment.basis,strict=True)
assert basis.operation_basis.schema_=='dmb_recap_semantic_basis_v13'
candidate=json.loads((root/child.components['candidate_graph'].uri.removeprefix('repo://')).read_bytes())
print(json.dumps({'actor':candidate['nodes'][-1]['label'],'held':child.lineage['semantic_disposition']['state']}))
"""
    fresh_actor = subprocess.check_output(
        [sys.executable, "-c", fresh_actor_code, str(tmp_path), actor_child.run_id,
         parent.run_id, artifact.content_sha256], text=True,
    )
    assert json.loads(fresh_actor) == {"actor": "Lysandro", "held": "held"}

    # Omission is a separate held child from the same real producer result.
    # Its contextual actor quote is in the pinned source span but absent from
    # the old edge's evidence quotes; it validates the operator's explanation
    # without silently appending or rewriting evidence on the withdrawn edge.
    production_edge = next(
        edge for edge in production_candidate["edges"]
        if edge["edge_id"] == "edge-lysandro-headquarters"
    )
    original_quotes = [
        quote
        for evidence_ref in production_edge["evidence_refs"]
        for quote in evidence_ref["anchor_quotes"]
    ]
    omission_body = _actor_recovery_request(
        parent, production_candidate, source.source_span_index, source_text,
        action="omit", edge_id="edge-lysandro-headquarters",
    )
    validation_quotes = omission_body["affected_edges"][0]["actor_anchor_quotes"]
    assert validation_quotes[0] in source_text
    assert validation_quotes[0] not in original_quotes
    assert all("Lysandro" not in quote for quote in original_quotes)
    omission_request = RecapCandidateCorrectionRequestV11.model_validate(
        omission_body, strict=True,
    )
    omission_response = correction.correct_recap_candidate(omission_request)
    assert omission_response.semantic_state == "held"
    assert (omission_response.introduced_actor_count,
            omission_response.retargeted_edge_count,
            omission_response.omitted_edge_count) == (1, 0, 1)
    omission_child = ingest.get_extraction_run(omission_response.run_id)
    omission_candidate = json.loads(_component_path(
        tmp_path, omission_child, "candidate_graph",
    ).read_bytes())
    omission_actor = omission_candidate["nodes"][-1]
    assert omission_actor["label"] == "Lysandro"
    assert omission_candidate["nodes"] == production_candidate["nodes"] + [omission_actor]
    assert omission_candidate["edges"] == [
        edge for edge in production_candidate["edges"]
        if edge["edge_id"] != "edge-lysandro-headquarters"
    ]
    for key in ("beats", "proposed_writes", "ignored_items", "deferred_items"):
        assert omission_candidate.get(key, []) == production_candidate.get(key, [])
    omission_assessment = assess_recap_semantics(
        omission_child, parent=parent,
        source_revision_id=artifact.content_sha256, root=tmp_path,
    )
    assert omission_assessment.marked and not omission_assessment.accepted
    omission_basis = ingest.RecapSemanticBasisV12.model_validate(
        omission_assessment.basis, strict=True,
    )
    assert omission_basis.request_version == 11
    assert omission_basis.operation_basis.schema_ == "dmb_recap_semantic_basis_v13"
    assert correction.verify_child_replay(omission_child, parent, tmp_path)
    omission_retry = correction.correct_recap_candidate(omission_request)
    assert omission_retry.run_id == omission_child.run_id
    assert ingest.get_extraction_run(omission_child.run_id).revision == omission_child.revision
    fresh_omission = subprocess.check_output(
        [sys.executable, "-c", fresh_actor_code, str(tmp_path), omission_child.run_id,
         parent.run_id, artifact.content_sha256], text=True,
    )
    assert json.loads(fresh_omission) == {"actor": "Lysandro", "held": "held"}
    assert source_path.read_bytes() == parent_source_bytes
    assert span_path.read_bytes() == parent_span_bytes
    assert candidate_path.read_bytes() == parent_candidate_bytes

    original_lock = correction._source_binding_child_lock
    package_root = tmp_path / "out" / "graph_memory" / "derived_candidates"

    def package_names():
        return {
            path.name for path in package_root.iterdir()
            if path.is_dir() and path.name not in {".locks", ".staging"}
        } if package_root.exists() else set()

    def reject_transition(parent, status):
        request = correction_request(
            parent,
            f"Synthetic stale-lock correction: {status.value}.",
        )
        packages_before = package_names()
        rows_before = {run.run_id for run in ingest.list_extraction_runs()}

        @contextmanager
        def transition_after_lock(root, child_id):
            with original_lock(root, child_id):
                if status == ExtractionRunStatus.SUPERSEDED:
                    registry.supersede_extraction_run(
                        root, parent.run_id, expected_revision=parent.revision,
                    )
                else:
                    registry.update_extraction_run_status(
                        root, parent.run_id, status=status,
                        expected_revision=parent.revision,
                    )
                yield

        monkeypatch.setattr(correction, "_source_binding_child_lock", transition_after_lock)
        with pytest.raises(correction.ExtractPromoteError, match="parent run authority changed"):
            correction.correct_recap_candidate(request)
        monkeypatch.setattr(correction, "_source_binding_child_lock", original_lock)

        rows_after = {run.run_id for run in ingest.list_extraction_runs()}
        new_rows = rows_after - rows_before
        assert package_names() == packages_before
        assert ingest.get_extraction_run(parent.run_id).status == status
        if status == ExtractionRunStatus.SUPERSEDED:
            assert len(new_rows) == 1
            successor = ingest.get_extraction_run(next(iter(new_rows)))
            assert successor.supersedes_run_id == parent.run_id
        else:
            assert not new_rows

    rejected_parent = produce_parent()
    reject_transition(rejected_parent, ExtractionRunStatus.REJECTED)
    superseded_parent = produce_parent()
    reject_transition(superseded_parent, ExtractionRunStatus.SUPERSEDED)
