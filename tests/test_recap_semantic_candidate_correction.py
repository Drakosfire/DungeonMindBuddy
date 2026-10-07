"""A bounded candidate edit makes a new held recap child, never a World write."""

from __future__ import annotations

import asyncio
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
import httpx
from fastapi import FastAPI

from application_state.ingest.service import RecapSemanticBasisV2
from apps.live_control_server.models.extract_promote import (
    RecapCandidateCorrectionRequest,
    RecapNodeDescriptionReplacement,
)
from apps.live_control_server.services import recap_semantic_candidate_correction as service
from apps.live_control_server.services import extract_promote, graph_run_registry
from apps.live_control_server.models.extract_promote import ExtractPromotePrepareRequest
from apps.live_control_server.services.recap_semantic_disposition import (
    EFFECT_KEY, accepted_effect_binding,
)
from apps.live_control_server.routes import extract_promote as routes
from apps.live_control_server.services.agent_graph_auth import NativeGraphPrincipal, native_graph_gm_dependency
from apps.live_control_server.services.graph_run_registry import GraphRunRegistryError
from apps.live_control_server.services.recap_semantic_disposition import assess_recap_semantics
from graph_memory.ingestion.extraction_run import (
    ExtractionRun,
    ExtractionRunComponentKind,
    ExtractionRunComponentRef,
    ExtractionRunStatus,
)


def _sha(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _fixture(monkeypatch: pytest.MonkeyPatch, root: Path):
    source = root / "source.md"
    source.write_text("Mira found the key under the bridge.\n", encoding="utf-8")
    spans = root / "spans.json"
    spans.write_text('{"spans":[]}', encoding="utf-8")
    artifact_id = "artifact:recap:c:s:source"
    span_id = f"{artifact_id}:span:abc:1-1"
    node = {
        "node_id": "mira", "node_type": "character", "label": "Mira",
        "description": "Mira carried an uncertain object.", "importance": "medium",
        "semantic_state": {
            "canon_state": "played_canon", "lifecycle_state": "candidate",
            "evidence_role": "source_evidence", "authority_state": "system_derived",
            "visibility_state": "gm_private",
        },
        "proposed_action": "create", "confidence": "medium",
        "evidence_refs": [{
            "source_ref_id": "ref:mira", "source_artifact_id": artifact_id,
            "source_span_ref_id": span_id, "can_open_source": True,
            "can_highlight_span": True,
            "anchor_quotes": ["Mira found the key under the bridge."],
        }],
    }
    payload = {
        "schema": "dmb_candidate_graph_preview_v0", "version": "0.1",
        "preview_id": "preview:recap-semantic-test", "campaign_id": "c",
        "session_id": "s", "source_artifact_ids": [artifact_id],
        "status": "preview", "nodes": [node], "edges": [], "beats": [],
        "proposed_writes": [], "ignored_items": [], "deferred_items": [],
        "diagnostics": {
            "preview_only": True, "extraction_performed": False,
            "llm_used": False, "runtime_connected": False,
            "plan_connected": False, "agent_interaction_connected": False,
            "corpus_scanned": False, "corpus_mutated": False,
            "facts_promoted": False, "canon_promoted": False,
            "unresolved_evidence_refs": 0, "missing_evidence_objects": 0,
            "warning_count": 0,
        },
    }
    parent_file = root / "parent.json"
    parent_bytes = json.dumps(payload).encode()
    parent_file.write_bytes(parent_bytes)
    components = {
        kind.value: ExtractionRunComponentRef(
            kind=kind, uri=uri, sha256=_sha((root / uri).read_bytes()), exists=True,
        )
        for kind, uri in (
            (ExtractionRunComponentKind.SOURCE_ARTIFACT, "source.md"),
            (ExtractionRunComponentKind.SOURCE_SPAN_INDEX, "spans.json"),
            (ExtractionRunComponentKind.CANDIDATE_GRAPH, "parent.json"),
        )
    }
    parent = ExtractionRun(
        run_id="parent", source_artifact_id=artifact_id,
        source_domain="recap", campaign_id="c", session_id="s",
        profile_id=service.PROFILE, status=ExtractionRunStatus.REVIEWABLE,
        components=components,
    )
    runs = {"parent": parent}

    def resolve(run_id, **_kwargs):
        run = runs[run_id]
        return SimpleNamespace(
            run_id=run_id, source_domain="recap", extraction_profile=service.PROFILE,
            campaign_id="c", session_id="s", source_artifact_id=artifact_id,
            candidate_graph_path=root / run.components["candidate_graph"].uri,
            normalized_recap_path=source, source_span_index_path=spans,
            source_revision_id=_sha(source.read_bytes()),
        )

    def get_run(_root, run_id):
        try:
            return runs[run_id]
        except KeyError as exc:
            raise GraphRunRegistryError("missing", status_code=404) from exc

    def create_run(_root, **kwargs):
        run = ExtractionRun(**kwargs)
        runs[run.run_id] = run
        return run

    def update_run(_root, run_id, *, status, expected_revision):
        run = runs[run_id]
        assert run.revision == expected_revision
        updated = run.model_copy(update={"status": status, "revision": expected_revision + 1})
        runs[run_id] = updated
        return updated

    monkeypatch.setattr(service, "repo_root", lambda: root)
    monkeypatch.setattr(service, "resolve_promotable_ingest_run", resolve)
    monkeypatch.setattr(service, "get_extraction_run", get_run)
    monkeypatch.setattr(service, "create_extraction_run", create_run)
    monkeypatch.setattr(service, "update_extraction_run_status", update_run)
    monkeypatch.setattr(
        service, "_load_frozen_span_index_for_resolved_run",
        lambda _resolved: SimpleNamespace(spans=[SimpleNamespace(
            source_span_id=span_id, start_line=1, end_line=1,
        )]),
    )
    return parent, parent_bytes, runs


def _request(parent_bytes: bytes) -> RecapCandidateCorrectionRequest:
    return RecapCandidateCorrectionRequest(
        parent_run_id="parent", parent_candidate_sha256=_sha(parent_bytes),
        node_description_replacements=[RecapNodeDescriptionReplacement(
            node_id="mira", original_description="Mira carried an uncertain object.",
            replacement_description="Mira found the key under the bridge.",
        )],
    )


def test_immutable_child_replays_and_stays_held(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    parent, parent_bytes, runs = _fixture(monkeypatch, tmp_path)
    response = service.correct_recap_candidate(_request(parent_bytes))
    assert service.correct_recap_candidate(_request(parent_bytes)) == response
    assert parent_bytes == (tmp_path / "parent.json").read_bytes()
    child = runs[response.run_id]
    assert child.status == ExtractionRunStatus.REVIEWABLE
    assert child.lineage["semantic_disposition"]["state"] == "held"
    assert service.verify_child_replay(child, parent, tmp_path)
    assessment = assess_recap_semantics(
        child, parent=parent, source_revision_id=_sha((tmp_path / "source.md").read_bytes()),
        root=tmp_path,
    )
    assert assessment.marked and not assessment.accepted
    assert assessment.basis_sha256 == response.semantic_basis_sha256
    assert RecapSemanticBasisV2.model_validate(assessment.basis).digest() == response.semantic_basis_sha256
    candidate = json.loads((tmp_path / child.components["candidate_graph"].uri).read_text())
    assert candidate["nodes"][0]["description"] == "Mira found the key under the bridge."
    assert candidate["nodes"][0]["evidence_refs"] == json.loads(parent_bytes)["nodes"][0]["evidence_refs"]
    candidate["nodes"][0]["label"] = "forged"
    (tmp_path / child.components["candidate_graph"].uri).write_text(json.dumps(candidate))
    assert not service.verify_child_replay(child, parent, tmp_path)
    assert not assess_recap_semantics(
        child, parent=parent, source_revision_id=_sha((tmp_path / "source.md").read_bytes()),
        root=tmp_path,
    ).accepted
    candidate_path = tmp_path / child.components["candidate_graph"].uri
    candidate_path.write_bytes(service._canonical_bytes(service.replay_candidate(json.loads(parent_bytes), child.lineage["semantic_candidate_manifest"])))
    (tmp_path / "spans.json").write_text('{"spans":[],"tampered":true}')
    assert not service.verify_child_replay(child, parent, tmp_path)


def test_replay_refuses_stale_description_and_edge_dependency() -> None:
    parent = {
        "nodes": [{"node_id": "n", "description": "old"}],
        "edges": [{"edge_id": "e"}],
        "proposed_writes": [{"target_id": "e"}],
    }
    manifest = {
        "schema": service.MANIFEST_SCHEMA,
        "node_description_replacements": [{
            "node_id": "n", "original_description": "wrong",
            "replacement_description": "new",
        }],
        "omitted_edge_ids": [],
    }
    with pytest.raises(ValueError, match="stale"):
        service.replay_candidate(parent, manifest)
    manifest["node_description_replacements"] = []
    manifest["omitted_edge_ids"] = ["e"]
    with pytest.raises(ValueError, match="dependent"):
        service.replay_candidate(parent, manifest)
    parent["proposed_writes"] = []
    assert service.replay_candidate(parent, manifest)["edges"] == []
    assert parent["edges"] == [{"edge_id": "e"}]


def test_request_enforces_one_plus_one_bounded_shape() -> None:
    with pytest.raises(ValueError):
        RecapCandidateCorrectionRequest(parent_run_id="p", parent_candidate_sha256="a" * 64)
    with pytest.raises(ValueError):
        RecapCandidateCorrectionRequest(
            parent_run_id="p", parent_candidate_sha256="a" * 64,
            omitted_edge_ids=["e1", "e2"],
        )


def test_http_route_creates_held_child_and_rejects_wrong_path(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    parent, parent_bytes, runs = _fixture(monkeypatch, tmp_path)
    route = next(route for route in routes.router.routes if route.path.endswith("/recap-candidate-corrections"))
    assert any(dependency.call is native_graph_gm_dependency for dependency in route.dependant.dependencies)
    import fastapi.dependencies.utils as dependency_utils
    import fastapi.routing as fastapi_routing

    async def inline_sync(function, *args, **kwargs):
        return function(*args, **kwargs)

    monkeypatch.setattr(fastapi_routing, "run_in_threadpool", inline_sync)
    monkeypatch.setattr(dependency_utils, "run_in_threadpool", inline_sync)
    app = FastAPI()
    app.include_router(routes.router)
    app.dependency_overrides[native_graph_gm_dependency] = lambda: NativeGraphPrincipal(
        subject="test_gm", role="gm", auth_method="local_session",
    )
    body = _request(parent_bytes).model_dump(mode="json", by_alias=True)
    url = "/api/live/extract-promote/runs/parent/recap-candidate-corrections"

    async def exercise():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            mismatch = await client.post(url, json={**body, "parentRunId": "other"})
            assert mismatch.status_code == 422
            unknown = await client.post(url, json={**body, "arbitraryPatch": {"x": 1}})
            assert unknown.status_code == 422
            created = await client.post(url, json=body)
            assert created.status_code == 200, created.text
            assert created.json()["semanticState"] == "held"
            assert created.json()["runId"] in runs

    asyncio.run(exercise())
    assert parent_bytes == (tmp_path / parent.components["candidate_graph"].uri).read_bytes()


def test_v2_hold_and_confirm_binding_guard_world_writer(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    parent, parent_bytes, runs = _fixture(monkeypatch, tmp_path)
    response = service.correct_recap_candidate(_request(parent_bytes))
    child = runs[response.run_id]
    monkeypatch.setattr(extract_promote, "repo_root", lambda: tmp_path)
    monkeypatch.setattr(extract_promote, "resolve_promotable_ingest_run", service.resolve_promotable_ingest_run)
    monkeypatch.setattr(graph_run_registry, "get_extraction_run", lambda _root, run_id: runs[run_id])
    monkeypatch.setattr(extract_promote, "_candidate_owner_for_locator", lambda _loc: runs[response.run_id])
    with pytest.raises(extract_promote.ExtractPromoteError, match="semantic review") as held:
        extract_promote.prepare(ExtractPromotePrepareRequest(run_id=child.run_id))
    assert held.value.code == "recap_semantic_hold"
    source_sha = _sha((tmp_path / "source.md").read_bytes())
    child.lineage["semantic_disposition"] = {
        "version": 1, "state": "rejected", "basis_sha256": response.semantic_basis_sha256,
        "review_decision_ref": "review:reject", "reviewer_id": "gm",
        "decided_at": "2026-10-06T00:00:00Z", "from_revision": child.revision,
    }
    child.revision += 1
    with pytest.raises(extract_promote.ExtractPromoteError) as rejected:
        extract_promote.prepare(ExtractPromotePrepareRequest(run_id=child.run_id))
    assert rejected.value.code == "recap_semantic_hold"
    child.lineage["semantic_disposition"]["state"] = "accepted"
    assessment = assess_recap_semantics(
        child, parent=parent, source_revision_id=source_sha, root=tmp_path,
    )
    assert assessment.accepted
    binding = accepted_effect_binding(child, assessment)
    locator = str(tmp_path / child.components["candidate_graph"].uri)
    extract_promote._assert_recap_semantics_at_confirm(locator, {"effect": {EFFECT_KEY: binding}})
    with pytest.raises(extract_promote.ExtractPromoteError):
        extract_promote._assert_recap_semantics_at_confirm(locator, {"effect": {EFFECT_KEY: {**binding, "manifest_sha256": "f" * 64}}})
    candidate = tmp_path / child.components["candidate_graph"].uri
    candidate.write_bytes(candidate.read_bytes() + b" ")
    with pytest.raises(extract_promote.ExtractPromoteError) as drifted:
        extract_promote._assert_recap_semantics_at_confirm(locator, {"effect": {EFFECT_KEY: binding}})
    assert drifted.value.code == "recap_semantic_hold"
