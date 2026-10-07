"""Recap quote correction creates an immutable child held for semantic review."""

from __future__ import annotations

import asyncio
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest

from application_state.ingest.service import RecapSemanticBasisV1
from apps.live_control_server.models.extract_promote import (
    ExactRunEvidenceCorrectionRequest,
    ExactRunEvidenceQuoteCorrection,
    RecapEvidenceCorrectionResponse,
)
from apps.live_control_server.services import exact_run_evidence_correction as correction
from apps.live_control_server.services import graph_run_registry
from apps.live_control_server.services import source_artifact_registry
from apps.live_control_server.services.graph_run_registry import GraphRunRegistryError
from apps.live_control_server.services.recap_semantic_disposition import assess_recap_semantics
from graph_memory.ingestion.extraction_run import (
    ExtractionRun,
    ExtractionRunComponentKind,
    ExtractionRunComponentRef,
    ExtractionRunStatus,
)


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _fixture(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, *, two_invalid: bool = False):
    source = tmp_path / "source.md"
    source_bytes = b"Mira found the silver key under the old bridge.\n"
    source.write_bytes(source_bytes)
    span_file = tmp_path / "spans.json"
    span_file.write_text('{"spans":[]}', encoding="utf-8")
    artifact_id = "artifact:recap:c:s:source"
    span_id = f"{artifact_id}:span:abc:1-1"
    payload = {
        "schema": "dmb_candidate_graph_preview_v0", "version": "0.1",
        "preview_id": "preview:recap-test",
        "campaign_id": "c", "session_id": "s",
        "source_artifact_ids": [artifact_id], "status": "preview",
        "nodes": [{
            "node_id": "mira", "node_type": "character", "label": "Mira",
            "description": "Found a key", "importance": "medium",
            "semantic_state": {
                "canon_state": "played_canon", "lifecycle_state": "candidate",
                "evidence_role": "source_evidence", "authority_state": "system_derived",
                "visibility_state": "gm_private",
            },
            "proposed_action": "create", "confidence": "medium",
            "evidence_refs": [{
                "source_ref_id": "ref:mira",
                "source_artifact_id": artifact_id,
                "source_span_ref_id": span_id,
                "can_open_source": True, "can_highlight_span": True,
                "anchor_quotes": ["Mira acquired a key"]
                + (["beneath the river"] if two_invalid else []),
            }],
        }],
        "edges": [], "beats": [], "proposed_writes": [],
        "ignored_items": [], "deferred_items": [],
        "diagnostics": {
            "preview_only": True, "extraction_performed": False, "llm_used": False,
            "runtime_connected": False, "plan_connected": False,
            "agent_interaction_connected": False, "corpus_scanned": False,
            "corpus_mutated": False, "facts_promoted": False, "canon_promoted": False,
            "unresolved_evidence_refs": 0, "missing_evidence_objects": 0,
            "warning_count": 0,
        },
    }
    parent_path = tmp_path / "parent.json"
    parent_bytes = json.dumps(payload).encode()
    parent_path.write_bytes(parent_bytes)
    source_sha = _sha(source_bytes)
    components = {
        "source_artifact": ExtractionRunComponentRef(
            kind=ExtractionRunComponentKind.SOURCE_ARTIFACT,
            uri="source.md", sha256=source_sha, exists=True,
        ),
        "source_span_index": ExtractionRunComponentRef(
            kind=ExtractionRunComponentKind.SOURCE_SPAN_INDEX,
            uri="spans.json", sha256=_sha(span_file.read_bytes()), exists=True,
        ),
        "candidate_graph": ExtractionRunComponentRef(
            kind=ExtractionRunComponentKind.CANDIDATE_GRAPH,
            uri="parent.json", sha256=_sha(parent_bytes), exists=True,
        ),
    }
    parent = ExtractionRun(
        run_id="parent", source_artifact_id=artifact_id, source_domain="recap",
        campaign_id="c", session_id="s", profile_id="recap_category_v1@1.0",
        status=ExtractionRunStatus.REVIEWABLE, components=components,
    )
    resolved = SimpleNamespace(
        run_id="parent", candidate_graph_path=parent_path,
        normalized_recap_path=source, source_artifact_id=artifact_id,
        source_revision_id=source_sha, source_span_index_path=span_file,
        campaign_id="c", session_id="s", source_domain="recap",
        extraction_profile="recap_category_v1@1.0",
    )
    span_index = SimpleNamespace(spans=[
        SimpleNamespace(source_span_id=span_id, start_line=1, end_line=1),
    ])
    children: dict[str, ExtractionRun] = {}

    def get_run(_repo, run_id):
        if run_id == "parent":
            return parent
        if run_id in children:
            return children[run_id]
        raise GraphRunRegistryError("missing", status_code=404)

    def create_run(_repo, **kwargs):
        run = ExtractionRun(**kwargs)
        children[run.run_id] = run
        return run

    def update_run(_repo, run_id, *, status, expected_revision):
        run = children[run_id]
        assert run.revision == expected_revision
        updated = run.model_copy(update={"status": status, "revision": run.revision + 1})
        children[run_id] = updated
        return updated

    def resolve(run_id, **_kwargs):
        if run_id == "parent":
            return resolved
        child = children[run_id]
        candidate = tmp_path / child.components["candidate_graph"].uri
        assert child.status == ExtractionRunStatus.REVIEWABLE
        assert _sha(candidate.read_bytes()) == child.components["candidate_graph"].sha256
        return SimpleNamespace(run_id=run_id)

    monkeypatch.setattr(correction, "repo_root", lambda: tmp_path)
    monkeypatch.setattr(correction, "resolve_promotable_ingest_run", resolve)
    monkeypatch.setattr(correction, "get_extraction_run", get_run)
    monkeypatch.setattr(correction, "create_extraction_run", create_run)
    monkeypatch.setattr(correction, "update_extraction_run_status", update_run)
    monkeypatch.setattr(correction, "_load_frozen_span_index_for_resolved_run", lambda _resolved: span_index)
    return parent, parent_bytes, source_bytes, span_file.read_bytes(), span_id, children


def _request(sha: str, span_id: str, replacement: str = "found the silver key"):
    return ExactRunEvidenceCorrectionRequest(
        parent_run_id="parent", parent_candidate_sha256=sha,
        corrections=[ExactRunEvidenceQuoteCorrection(
            assertion_id="mira", evidence_index=0, source_span_ref_id=span_id,
            quote_index=0, original_quote="Mira acquired a key",
            replacement_quote=replacement,
        )],
    )


def test_recap_child_is_held_exact_idempotent_and_parent_frozen(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    parent, parent_bytes, source_bytes, span_bytes, span_id, children = _fixture(monkeypatch, tmp_path)
    from apps.live_control_server.integrations.dungeonmind import world_graph_writes

    monkeypatch.setattr(
        world_graph_writes, "confirm_extract_promote_via_dungeonmind",
        lambda *_a, **_k: pytest.fail("correction reached World writer"),
    )
    response = correction.correct_recap_run_evidence(_request(_sha(parent_bytes), span_id))
    repeated = correction.correct_recap_run_evidence(_request(_sha(parent_bytes), span_id))
    assert response == repeated
    assert response.semantic_state == "held" and len(children) == 1
    child = children[response.run_id]
    assert child.status == ExtractionRunStatus.REVIEWABLE
    assert child.lineage["derivation"] == "operator_recap_literal_evidence_correction_v1"
    assert child.components["source_artifact"] == parent.components["source_artifact"]
    assert child.components["source_span_index"] == parent.components["source_span_index"]
    assert child.components["candidate_graph"] != parent.components["candidate_graph"]
    assert parent.status == ExtractionRunStatus.REVIEWABLE
    assert (tmp_path / "parent.json").read_bytes() == parent_bytes
    assert (tmp_path / "source.md").read_bytes() == source_bytes
    assert (tmp_path / "spans.json").read_bytes() == span_bytes
    child_payload = json.loads((tmp_path / child.components["candidate_graph"].uri).read_text())
    expected = json.loads(parent_bytes)
    expected["nodes"][0]["evidence_refs"][0]["anchor_quotes"][0] = "found the silver key"
    assert child_payload == expected
    assessment = assess_recap_semantics(child, parent=parent, source_revision_id=_sha(source_bytes))
    assert assessment.marked and not assessment.accepted
    assert assessment.basis_sha256 == response.semantic_basis_sha256
    assert RecapSemanticBasisV1.model_validate(assessment.basis).digest() == response.semantic_basis_sha256
    assert child.lineage["semantic_disposition"] == {
        "version": 1, "state": "held", "basis_sha256": response.semantic_basis_sha256,
    }


@pytest.mark.parametrize("replacement", ["Mira acquired a key", "elsewhere"])
def test_recap_nonliteral_or_unchanged_replacement_creates_no_child(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, replacement: str
) -> None:
    _, parent_bytes, _, _, span_id, children = _fixture(monkeypatch, tmp_path)
    with pytest.raises(correction.ExtractPromoteError):
        correction.correct_recap_run_evidence(_request(_sha(parent_bytes), span_id, replacement))
    assert not children


def test_recap_partial_stale_and_wrong_profile_fail_closed(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    parent, parent_bytes, _, _, span_id, children = _fixture(monkeypatch, tmp_path, two_invalid=True)
    with pytest.raises(correction.ExtractPromoteError):
        correction.correct_recap_run_evidence(_request(_sha(parent_bytes), span_id))
    with pytest.raises(correction.ExtractPromoteError):
        correction.correct_recap_run_evidence(_request("0" * 64, span_id))
    stale_quote = _request(_sha(parent_bytes), span_id)
    stale_quote.corrections[0].original_quote = "different original"
    with pytest.raises(correction.ExtractPromoteError, match="stale"):
        correction.correct_recap_run_evidence(stale_quote)
    stale_span = _request(_sha(parent_bytes), span_id)
    stale_span.corrections[0].source_span_ref_id = "other:span"
    with pytest.raises(correction.ExtractPromoteError, match="source span"):
        correction.correct_recap_run_evidence(stale_span)
    parent.profile_id = "other@1.0"
    with pytest.raises(correction.ExtractPromoteError):
        correction.correct_recap_run_evidence(_request(_sha(parent_bytes), span_id))
    assert not children


def test_recap_existing_child_identity_conflict_does_not_reseal(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _, parent_bytes, _, _, span_id, children = _fixture(monkeypatch, tmp_path)
    response = correction.correct_recap_run_evidence(_request(_sha(parent_bytes), span_id))
    child = children[response.run_id]
    child.lineage["semantic_disposition"]["state"] = "accepted"
    with pytest.raises(correction.ExtractPromoteError, match="semantic decision conflicts"):
        correction.correct_recap_run_evidence(_request(_sha(parent_bytes), span_id))


@pytest.mark.parametrize("state", ["accepted", "rejected"])
def test_recap_retry_reports_current_review_decision_without_reset(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, state: str
) -> None:
    _, parent_bytes, _, _, span_id, children = _fixture(monkeypatch, tmp_path)
    request = _request(_sha(parent_bytes), span_id)
    first = correction.correct_recap_run_evidence(request)
    child = children[first.run_id]
    child.lineage["semantic_disposition"] = {
        "version": 1, "state": state,
        "basis_sha256": first.semantic_basis_sha256,
        "review_decision_ref": "review:1", "reviewer_id": "local_operator",
        "decided_at": "2026-10-06T00:00:00Z", "from_revision": child.revision,
    }
    child.revision += 1
    revision = child.revision
    candidate = tmp_path / child.components["candidate_graph"].uri
    before = candidate.read_bytes()
    repeated = correction.correct_recap_run_evidence(request)
    assert repeated.run_id == first.run_id
    assert repeated.semantic_state == state
    assert repeated.semantic_basis_sha256 == first.semantic_basis_sha256
    assert children[first.run_id].revision == revision
    assert children[first.run_id].lineage["semantic_disposition"]["state"] == state
    assert candidate.read_bytes() == before


def test_recap_duplicate_target_and_tampered_sealed_bytes_fail(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _, parent_bytes, _, _, span_id, children = _fixture(monkeypatch, tmp_path)
    request = _request(_sha(parent_bytes), span_id)
    request.corrections.append(request.corrections[0])
    with pytest.raises(correction.ExtractPromoteError, match="duplicate correction target"):
        correction.correct_recap_run_evidence(request)
    assert not children
    request.corrections.pop()
    first = correction.correct_recap_run_evidence(request)
    candidate = tmp_path / children[first.run_id].components["candidate_graph"].uri
    candidate.write_text("{}")
    with pytest.raises(correction.ExtractPromoteError, match="changed after seal"):
        correction.correct_recap_run_evidence(request)


def test_recap_child_round_trips_real_disposable_run_registry(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, application_state_dsn: str
) -> None:
    assert application_state_dsn
    source_text = "Mira found the silver key under the old bridge.\n"
    artifact = source_artifact_registry.create_recap_source_artifact(
        tmp_path, campaign_id="c", session_id="s", recap_text=source_text
    )
    span_path = source_artifact_registry.source_span_index_path(
        tmp_path, artifact.source_artifact_id
    )
    span = source_artifact_registry.load_source_span_index(
        tmp_path, artifact.source_artifact_id
    ).spans[0]
    payload = {
        "schema": "dmb_candidate_graph_preview_v0", "version": "0.1",
        "preview_id": "preview:recap-registry-test", "campaign_id": "c", "session_id": "s",
        "source_artifact_ids": [artifact.source_artifact_id], "status": "preview",
        "nodes": [{
            "node_id": "mira", "node_type": "character", "label": "Mira",
            "description": "Found a key", "importance": "medium",
            "semantic_state": {
                "canon_state": "played_canon", "lifecycle_state": "candidate",
                "evidence_role": "source_evidence", "authority_state": "system_derived",
                "visibility_state": "gm_private",
            },
            "proposed_action": "create", "confidence": "medium",
            "evidence_refs": [{
                "source_ref_id": "ref:mira", "source_artifact_id": artifact.source_artifact_id,
                "source_span_ref_id": span.source_span_id,
                "can_open_source": True, "can_highlight_span": True,
                "anchor_quotes": ["Mira acquired a key"],
            }],
        }],
        "edges": [], "beats": [], "proposed_writes": [],
        "ignored_items": [], "deferred_items": [],
        "diagnostics": {
            "preview_only": True, "extraction_performed": False, "llm_used": False,
            "runtime_connected": False, "plan_connected": False,
            "agent_interaction_connected": False, "corpus_scanned": False,
            "corpus_mutated": False, "facts_promoted": False, "canon_promoted": False,
            "unresolved_evidence_refs": 0, "missing_evidence_objects": 0,
            "warning_count": 0,
        },
    }
    parent_path = tmp_path / "parent.json"
    parent_path.write_text(json.dumps(payload), encoding="utf-8")
    parent_bytes = parent_path.read_bytes()
    components = {
        "source_artifact": ExtractionRunComponentRef(
            kind=ExtractionRunComponentKind.SOURCE_ARTIFACT,
            uri=artifact.uri, sha256=artifact.content_sha256, exists=True,
        ),
        "source_span_index": ExtractionRunComponentRef(
            kind=ExtractionRunComponentKind.SOURCE_SPAN_INDEX,
            uri=f"repo://{span_path.relative_to(tmp_path).as_posix()}",
            sha256=_sha(span_path.read_bytes()), exists=True,
        ),
        "candidate_graph": ExtractionRunComponentRef(
            kind=ExtractionRunComponentKind.CANDIDATE_GRAPH,
            uri="repo://parent.json", sha256=_sha(parent_bytes), exists=True,
        ),
    }
    parent = graph_run_registry.create_extraction_run(
        tmp_path, source_artifact_id=artifact.source_artifact_id,
        source_domain="recap", campaign_id="c", session_id="s",
        profile_id="recap_category_v1@1.0", components=components,
    )
    for status in (
        ExtractionRunStatus.PREPARED, ExtractionRunStatus.EXTRACTED,
        ExtractionRunStatus.VALIDATED, ExtractionRunStatus.REVIEWABLE,
    ):
        parent = graph_run_registry.update_extraction_run_status(
            tmp_path, parent.run_id, status=status, expected_revision=parent.revision
        )
    monkeypatch.setattr(correction, "repo_root", lambda: tmp_path)
    from apps.live_control_server.services import extract_promote

    monkeypatch.setattr(extract_promote, "repo_root", lambda: tmp_path)
    request = ExactRunEvidenceCorrectionRequest(
        parent_run_id=parent.run_id, parent_candidate_sha256=_sha(parent_bytes),
        corrections=[ExactRunEvidenceQuoteCorrection(
            assertion_id="mira", evidence_index=0, source_span_ref_id=span.source_span_id,
            quote_index=0, original_quote="Mira acquired a key",
            replacement_quote="found the silver key",
        )],
    )
    resolved = correction.resolve_promotable_ingest_run(parent.run_id, root=tmp_path)
    assert resolved.source_revision_id.removeprefix("sha256:") == artifact.content_sha256
    assert parent.components["candidate_graph"].sha256 == _sha(parent_bytes)
    response = correction.correct_recap_run_evidence(request)
    child = graph_run_registry.get_reviewable_extraction_run(tmp_path, response.run_id)
    assert child.lineage["semantic_disposition"] == {
        "version": 1, "state": "held", "basis_sha256": response.semantic_basis_sha256,
    }
    assert child.components["source_artifact"] == parent.components["source_artifact"]
    assert child.components["source_span_index"] == parent.components["source_span_index"]
    assert correction.correct_recap_run_evidence(request) == response
    assert parent_path.read_bytes() == parent_bytes
    assert graph_run_registry.get_extraction_run(tmp_path, parent.run_id).status == ExtractionRunStatus.REVIEWABLE


def test_recap_route_requires_gm_and_preserves_private_quote_draft(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    import fastapi.dependencies.utils as dependency_utils
    import fastapi.routing as fastapi_routing
    from apps.live_control_server.main import create_app
    from apps.live_control_server.routes import extract_promote as routes
    from apps.live_control_server.services.agent_graph_auth import (
        NativeGraphPrincipal, authenticate_native_graph_principal,
    )

    async def inline_sync(function, *args, **kwargs):
        return function(*args, **kwargs)

    monkeypatch.setattr(fastapi_routing, "run_in_threadpool", inline_sync)
    monkeypatch.setattr(dependency_utils, "run_in_threadpool", inline_sync)
    monkeypatch.setenv("DMB_AGENT_GRAPH_AUTH_MODE", "local_operator")
    monkeypatch.setenv("DMB_AGENT_GRAPH_AUTH_ENVIRONMENT", "development")
    token = "synthetic-local-operator-capability-32-characters"
    monkeypatch.setenv("DMB_AGENT_GRAPH_LOCAL_OPERATOR_TOKEN", token)
    seen = []

    def correct(request):
        seen.append(request.parent_run_id)
        return RecapEvidenceCorrectionResponse(
            run_id="child", parent_run_id="parent",
            parent_candidate_sha256="a" * 64, candidate_sha256="b" * 64,
            correction_digest="c" * 64, semantic_state="held",
            semantic_basis_sha256="d" * 64,
        )

    monkeypatch.setattr(routes, "correct_recap_run_evidence", correct)
    app = create_app()
    draft = tmp_path / "quote-draft.json"
    draft.write_text('{"replacement":"found the silver key"}')
    draft.chmod(0o600)
    before = draft.read_bytes()
    body = _request("a" * 64, "span:1").model_dump(mode="json", by_alias=True)
    url = "/api/live/extract-promote/runs/parent/recap-evidence-corrections"

    async def exercise():
        transport = httpx.ASGITransport(app=app, client=("127.0.0.1", 50000))
        async with httpx.AsyncClient(transport=transport, base_url="http://127.0.0.1:8000") as client:
            assert (await client.post(url, json=body)).status_code == 401
            app.dependency_overrides[authenticate_native_graph_principal] = lambda: NativeGraphPrincipal(
                subject="player", role="player", auth_method="local_operator"
            )
            assert (await client.post(url, json=body)).status_code == 403
            app.dependency_overrides.clear()
            headers = {"Authorization": f"Bearer {token}"}
            assert (await client.post(url, json={**body, "parentRunId": "other"}, headers=headers)).status_code == 422
            accepted = await client.post(url, json=body, headers=headers)
            assert accepted.status_code == 200, accepted.text
            assert accepted.json()["semanticState"] == "held"

    asyncio.run(exercise())
    assert seen == ["parent"]
    assert draft.read_bytes() == before and draft.stat().st_mode & 0o777 == 0o600
