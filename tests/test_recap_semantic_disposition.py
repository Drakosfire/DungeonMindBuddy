"""A corrected recap child needs exact semantic acceptance beyond evidence validity."""

from __future__ import annotations

import asyncio
import json
import hashlib
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest
from pydantic import ValidationError

from application_state.ingest.service import RecapSemanticBasisV1
from apps.live_control_server.models.extract_promote import (
    ExtractPromoteConfirmRequest,
    ExtractPromotePrepareRequest,
    RecapSemanticDecisionRequest,
    RecapSemanticDecisionResponse,
)
from apps.live_control_server.routes import extract_promote as extract_promote_routes
from apps.live_control_server.services.agent_graph_auth import (
    NativeGraphPrincipal,
    native_graph_gm_dependency,
)
from apps.live_control_server.services import (
    candidate_graph_admission,
    extract_promote,
    graph_run_registry,
)
from apps.live_control_server.services.recap_semantic_disposition import (
    DERIVATION,
    EFFECT_KEY,
    accepted_effect_binding,
    assert_current_effect_binding,
    assess_recap_semantics,
)
from graph_memory.extract_promote_proposal import compute_proposal_digest
from graph_memory.extract_promote_ops import ExtractPromotePrepareResult
from graph_memory.ingestion.extraction_run import (
    ExtractionRun,
    ExtractionRunComponentKind,
    ExtractionRunComponentRef,
    ExtractionRunStatus,
)


def _component(
    kind: ExtractionRunComponentKind, uri: str, sha: str
) -> ExtractionRunComponentRef:
    return ExtractionRunComponentRef(kind=kind, uri=uri, sha256=sha, exists=True)


def _runs() -> tuple[ExtractionRun, ExtractionRun]:
    parent = ExtractionRun(
        run_id="parent",
        source_artifact_id="artifact:recap:c:s:source",
        source_domain="recap",
        status=ExtractionRunStatus.REVIEWABLE,
        campaign_id="c",
        session_id="s",
        profile_id="recap_category_v1@1.0",
        components={
            "source_artifact": _component(
                ExtractionRunComponentKind.SOURCE_ARTIFACT, "source.md", "a" * 64
            ),
            "source_span_index": _component(
                ExtractionRunComponentKind.SOURCE_SPAN_INDEX, "spans.json", "b" * 64
            ),
            "candidate_graph": _component(
                ExtractionRunComponentKind.CANDIDATE_GRAPH, "parent.json", "c" * 64
            ),
        },
    )
    child = parent.model_copy(
        deep=True,
        update={
            "run_id": "child",
            "revision": 6,
            "components": {
                **parent.components,
                "candidate_graph": _component(
                    ExtractionRunComponentKind.CANDIDATE_GRAPH,
                    "child.json",
                    "d" * 64,
                ),
            },
            "lineage": {
                "derivation": DERIVATION,
                "parent_run_id": parent.run_id,
                "parent_candidate_sha256": "c" * 64,
                "correction_digest": "e" * 64,
            },
        },
    )
    return parent, child


def _assessment(parent: ExtractionRun, child: ExtractionRun):
    return assess_recap_semantics(child, parent=parent, source_revision_id="a" * 64)


def test_marked_child_is_held_until_exact_basis_is_accepted() -> None:
    parent, child = _runs()
    held = _assessment(parent, child)
    assert held.marked and not held.accepted and held.basis_sha256
    assert RecapSemanticBasisV1.model_validate(held.basis).digest() == held.basis_sha256
    child.lineage["semantic_disposition"] = {
        "version": 1,
        "state": "accepted",
        "basis_sha256": held.basis_sha256,
        "review_decision_ref": "review:1",
        "reviewer_id": "local_operator",
        "decided_at": "2026-10-06T00:00:00Z",
    }
    accepted = _assessment(parent, child)
    assert accepted.accepted
    binding = accepted_effect_binding(child, accepted)
    assert binding["run_id"] == "child"
    assert binding["run_revision"] == 6
    assert binding["candidate_sha256"] == "d" * 64
    assert binding["profile_version"] == "1.0"
    assert binding["basis_sha256"] == held.basis_sha256
    assert accepted.basis and accepted.basis["profile_version"] == "1.0"
    package = extract_promote._bind_recap_semantic_effect(
        {"effect": {"world_id": "w"}, "proposal_digest": "old"}, child, accepted
    )
    assert package["effect"][EFFECT_KEY] == binding
    assert package["proposal_digest"] == compute_proposal_digest(package["effect"])
    assert_current_effect_binding(child, accepted, binding)
    with pytest.raises(ValueError):
        assert_current_effect_binding(child, accepted, None)
    with pytest.raises(ValueError):
        assert_current_effect_binding(child, accepted, {**binding, "run_revision": 5})
    child.revision += 1
    with pytest.raises(ValueError):
        assert_current_effect_binding(child, accepted, binding)


def test_basis_rejects_drift_and_malformed_disposition() -> None:
    parent, child = _runs()
    basis = _assessment(parent, child).basis_sha256
    assert basis
    child.lineage["semantic_disposition"] = {
        "version": 1,
        "state": "accepted",
        "basis_sha256": basis,
        "review_decision_ref": "review:1",
        "reviewer_id": "local_operator",
        "decided_at": "2026-10-06T00:00:00Z",
    }
    assert _assessment(parent, child).accepted
    for change in (
        {"candidate_graph": "f" * 64},
        {"source_artifact": "f" * 64},
        {"source_span_index": "f" * 64},
    ):
        altered = child.model_copy(deep=True)
        for kind, sha in change.items():
            altered.components[kind].sha256 = sha
        assert not _assessment(parent, altered).accepted
    for field, value in (
        ("campaign_id", "other"),
        ("session_id", "other"),
        ("profile_id", "other"),
        ("profile_id", "recap_category_v1@2.0"),
        ("status", ExtractionRunStatus.REJECTED),
        ("source_domain", "worldbuilding"),
        ("source_artifact_id", "other"),
    ):
        altered = child.model_copy(deep=True, update={field: value})
        assert not _assessment(parent, altered).accepted
    for mutation in (
        {"version": True},
        {"version": 2},
        {"state": "held"},
        {"basis_sha256": "f" * 64},
        {"reviewer_id": ""},
    ):
        altered = child.model_copy(deep=True)
        altered.lineage["semantic_disposition"].update(mutation)
        assert not _assessment(parent, altered).accepted
    altered = child.model_copy(deep=True)
    altered.lineage["parent_candidate_sha256"] = "f" * 64
    assert not _assessment(parent, altered).accepted
    assert not assess_recap_semantics(
        child, parent=parent, source_revision_id="f" * 64
    ).accepted
    wrong_parent = parent.model_copy(deep=True, update={"status": ExtractionRunStatus.DRAFT})
    assert not _assessment(wrong_parent, child).accepted
    wrong_parent = parent.model_copy(deep=True, update={"profile_id": "unknown_profile@1.0"})
    wrong_child = child.model_copy(deep=True, update={"profile_id": "unknown_profile@1.0"})
    assert not _assessment(wrong_parent, wrong_child).accepted


def test_unmarked_recap_and_worldbuilding_do_not_gain_this_gate() -> None:
    parent, child = _runs()
    child.lineage["derivation"] = "operator_literal_evidence_correction_v1"
    assert _assessment(parent, child).accepted
    assert not _assessment(parent, child).marked


def test_held_prepare_rejects_before_candidate_admission(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    parent, child = _runs()
    resolved = SimpleNamespace(
        run_id=child.run_id,
        source_revision_id="a" * 64,
        source_span_index_path=Path("spans.json"),
    )
    monkeypatch.setattr(
        extract_promote, "resolve_promotable_ingest_run", lambda *_a, **_k: resolved
    )
    monkeypatch.setattr(
        graph_run_registry,
        "get_extraction_run",
        lambda _root, run_id: {"parent": parent, "child": child}[run_id],
    )
    monkeypatch.setattr(
        candidate_graph_admission,
        "prepare_candidate_graph_admission",
        lambda **_kwargs: pytest.fail("held child reached candidate admission"),
    )
    with pytest.raises(extract_promote.ExtractPromoteError) as error:
        extract_promote.prepare(ExtractPromotePrepareRequest(run_id="child"))
    assert error.value.code == "recap_semantic_hold"
    assert error.value.status_code == 409


def test_accepted_prepare_seals_exact_semantic_binding(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    parent, child = _runs()
    basis_sha = _assessment(parent, child).basis_sha256
    child.lineage["semantic_disposition"] = {
        "version": 1, "state": "accepted", "basis_sha256": basis_sha,
        "review_decision_ref": "review:accept", "reviewer_id": "local_operator",
        "decided_at": "2026-10-06T00:00:00Z", "from_revision": 5,
    }
    candidate = tmp_path / "candidate.json"
    candidate.write_text(json.dumps({"campaign_id": "c", "session_id": "s"}))
    resolved = SimpleNamespace(
        run_id="child", source_revision_id="a" * 64,
        source_span_index_path=tmp_path / "spans.json",
        candidate_graph_path=candidate, campaign_id="c", session_id="s",
        source_artifact_id=child.source_artifact_id,
        sealed_source_uri="repo://source.md", extraction_profile="recap_category_v1@1.0",
        registry_context_graph_path=None, diagnostics=[], source_domain="recap",
    )
    monkeypatch.setattr(extract_promote, "resolve_promotable_ingest_run", lambda *_a, **_k: resolved)
    monkeypatch.setattr(graph_run_registry, "get_extraction_run", lambda _root, run_id: {"parent": parent, "child": child}[run_id])
    monkeypatch.setattr(extract_promote, "assert_sealed_source_uri_allowed", lambda _uri: None)
    monkeypatch.setattr(extract_promote, "_require_canonical_source_artifact", lambda _id: object())
    from apps.live_control_server import config
    from apps.live_control_server.integrations.dungeonmind import world_graph_writes

    monkeypatch.setattr(config, "world_graph_authority_mode", lambda: config.WORLD_GRAPH_AUTHORITY_DUNGEONMIND)
    monkeypatch.setattr(world_graph_writes, "load_production_mutation_context", lambda _id: object())
    monkeypatch.setattr(
        candidate_graph_admission, "prepare_candidate_graph_admission",
        lambda **_kwargs: ExtractPromotePrepareResult(
            review_package={"effect": {"world_id": "w"}, "proposal_digest": "old"},
            proposal_id="proposal", proposal_digest="old", parent_revision_id="parent-rev",
            world_id="w", accepted_proposals_count=0, unresolved_mentions_count=0,
            rejected_assertions_count=0,
        ),
    )

    def seal(package, _context):
        assert package["effect"][EFFECT_KEY] == accepted_effect_binding(child, _assessment(parent, child))
        return package

    monkeypatch.setattr(world_graph_writes, "bind_identity_ledger_to_package", seal)
    response = extract_promote.prepare(ExtractPromotePrepareRequest(run_id="child"))
    assert response.review_package["effect"][EFFECT_KEY]["run_revision"] == 6
    assert response.proposal_digest == compute_proposal_digest(response.review_package["effect"])


def test_held_review_package_remains_readable(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    parent, child = _runs()
    source = tmp_path / "source.md"
    source.write_text("Mira found the silver key.\n", encoding="utf-8")
    candidate = tmp_path / "candidate.json"
    candidate.write_text(json.dumps({"campaign_id": "c", "session_id": "s"}))
    span_id = f"{child.source_artifact_id}:span:abc:1-1"
    resolved = SimpleNamespace(
        run_id="child",
        status="reviewable",
        normalized_recap_path=source,
        candidate_graph_path=candidate,
        source_artifact_id=child.source_artifact_id,
        source_revision_id="a" * 64,
        campaign_id="c",
        session_id="s",
        source_domain="recap",
        world_id="w",
        diagnostics=[],
        source_span_index_path=Path("spans.json"),
    )
    typed = SimpleNamespace(
        nodes=[
            SimpleNamespace(
                node_id="mira",
                label="Mira",
                description="Found a key",
                evidence_refs=[
                    SimpleNamespace(
                        source_artifact_id=child.source_artifact_id,
                        source_span_ref_id=span_id,
                        anchor_quotes=["Mira found the silver key"],
                    )
                ],
            )
        ],
        edges=[],
    )
    monkeypatch.setattr(
        extract_promote, "resolve_promotable_ingest_run", lambda *_a, **_k: resolved
    )
    monkeypatch.setattr(
        extract_promote,
        "_load_frozen_span_index_for_resolved_run",
        lambda *_a: SimpleNamespace(
            spans=[SimpleNamespace(source_span_id=span_id, start_line=1, end_line=1)]
        ),
    )
    monkeypatch.setattr(
        extract_promote,
        "resolve_first_world_capability",
        lambda **_k: SimpleNamespace(
            world_id="w", world_state="initialized", eligible=True, reason=None
        ),
    )
    monkeypatch.setattr(
        candidate_graph_admission,
        "validate_candidate_document_integrity",
        lambda _payload: typed,
    )
    monkeypatch.setattr(
        graph_run_registry,
        "get_extraction_run",
        lambda _root, run_id: {"parent": parent, "child": child}[run_id],
    )
    review = extract_promote.get_exact_run_review_package("child")
    assert review.inspection_status == "ready"
    assert review.invalid_evidence_count == 0
    assert review.derived_from_run_id == "parent"
    assert review.semantic_disposition["state"] == "held"
    assert review.promotable is False
    assert "semantic review" in review.promotable_reason

    from apps.live_control_server.integrations.dungeonmind import world_graph_writes

    monkeypatch.setattr(
        world_graph_writes, "confirm_extract_promote_via_dungeonmind",
        lambda *_a, **_k: pytest.fail("review projection reached World writer"),
    )
    from application_state.ingest import service as ingest_service
    from apps.live_control_server.services import source_artifact_registry

    monkeypatch.setattr(graph_run_registry, "get_reviewable_extraction_run", lambda _root, _id: child)
    monkeypatch.setattr(
        source_artifact_registry, "get_source_artifact",
        lambda _root, _id: SimpleNamespace(content_sha256="a" * 64),
    )

    def record_rejection(run_id, *, expected_revision, basis, decision):
        assert run_id == "child" and expected_revision == 6
        assert decision.state == "rejected"
        child.lineage["semantic_disposition"] = {
            "version": 1, "state": decision.state,
            "basis_sha256": basis.digest(),
            "review_decision_ref": decision.review_decision_ref,
            "reviewer_id": decision.reviewer_id,
            "decided_at": "2026-10-06T00:00:00Z", "from_revision": expected_revision,
        }
        child.revision += 1
        return child

    monkeypatch.setattr(ingest_service, "record_recap_semantic_disposition", record_rejection)
    receipt = extract_promote.decide_recap_semantic_disposition(
        "child",
        RecapSemanticDecisionRequest(
            expected_revision=6, candidate_sha256="d" * 64,
            decision="rejected", review_decision_ref="review:reject",
        ),
        reviewer_id="local_operator",
    )
    assert receipt.state == "rejected" and receipt.revision == 7
    rejected = extract_promote.get_exact_run_review_package("child")
    assert rejected.semantic_disposition["state"] == "rejected"
    assert rejected.semantic_disposition["reason"] == rejected.promotable_reason
    assert "rejected by semantic review" in rejected.promotable_reason
    assert rejected.promotable is False
    assert rejected.first_world_publish_eligible is False
    with pytest.raises(extract_promote.ExtractPromoteError) as error:
        extract_promote.prepare(ExtractPromotePrepareRequest(run_id="child"))
    assert error.value.code == "recap_semantic_hold"
    assert "rejected" in str(error.value)
    child.lineage["semantic_disposition"]["basis_sha256"] = "f" * 64
    malformed = extract_promote.get_exact_run_review_package("child")
    assert malformed.semantic_disposition["state"] == "held"
    assert malformed.promotable is False


@pytest.mark.parametrize(
    "case", ["missing_binding", "forged_binding", "held_disposition", "rejected_disposition", "revision_drift", "status_drift", "domain_drift"]
)
def test_confirm_never_reaches_world_writer_for_held_or_changed_child(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, case: str
) -> None:
    parent, child = _runs()
    held = _assessment(parent, child)
    child.lineage["semantic_disposition"] = {
        "version": 1, "state": "accepted", "basis_sha256": held.basis_sha256,
        "review_decision_ref": "review:1", "reviewer_id": "local_operator",
        "decided_at": "2026-10-06T00:00:00Z", "from_revision": 5,
    }
    accepted = _assessment(parent, child)
    binding = accepted_effect_binding(child, accepted)
    if case == "forged_binding":
        binding["basis_sha256"] = "f" * 64
    candidate = tmp_path / "child.json"
    candidate.write_text("{}")
    resolved = SimpleNamespace(
        run_id=child.run_id, source_revision_id="a" * 64,
        source_span_index_path=tmp_path / "spans.json",
        candidate_graph_path=candidate,
    )
    if case == "status_drift":
        child.status = ExtractionRunStatus.REJECTED
    if case == "held_disposition":
        child.lineage["semantic_disposition"]["state"] = "held"
    if case == "rejected_disposition":
        child.lineage["semantic_disposition"]["state"] = "rejected"
    if case == "revision_drift":
        child.revision += 1
    if case == "domain_drift":
        child.source_domain = "worldbuilding"
        child.session_id = None
    monkeypatch.setattr(extract_promote, "_candidate_owner_for_locator", lambda _loc: child)
    monkeypatch.setattr(extract_promote, "resolve_promotable_ingest_run", lambda *_a, **_k: resolved)
    monkeypatch.setattr(graph_run_registry, "get_extraction_run", lambda _root, run_id: {"parent": parent, "child": child}[run_id])
    from apps.live_control_server import config
    from apps.live_control_server.integrations.dungeonmind import world_graph_writes

    monkeypatch.setattr(config, "world_graph_authority_mode", lambda: config.WORLD_GRAPH_AUTHORITY_DUNGEONMIND)
    monkeypatch.setattr(
        candidate_graph_admission, "confirm_candidate_graph_admission",
        lambda **kwargs: kwargs["governed_confirm"](),
    )
    monkeypatch.setattr(
        world_graph_writes, "confirm_extract_promote_via_dungeonmind",
        lambda *_a, **_k: pytest.fail("semantic gate reached World writer"),
    )
    binding = binding if case != "missing_binding" else None
    request = ExtractPromoteConfirmRequest(
        review_package={
            "effect": {"candidate_admission": {"candidate_locator": str(candidate)},
                       **({EFFECT_KEY: binding} if binding else {})},
        },
        assertion_ids=["mira"],
    )
    with pytest.raises(extract_promote.ExtractPromoteError) as error:
        extract_promote.confirm(request)
    assert error.value.status_code == 409


def test_exact_accepted_child_reaches_governed_writer_once(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    parent, child = _runs()
    basis_sha = _assessment(parent, child).basis_sha256
    child.lineage["semantic_disposition"] = {
        "version": 1, "state": "accepted", "basis_sha256": basis_sha,
        "review_decision_ref": "review:accept", "reviewer_id": "local_operator",
        "decided_at": "2026-10-06T00:00:00Z", "from_revision": 5,
    }
    accepted = _assessment(parent, child)
    candidate = tmp_path / "child.json"
    candidate.write_text("{}")
    resolved = SimpleNamespace(
        run_id=child.run_id, source_revision_id="a" * 64,
        source_span_index_path=tmp_path / "spans.json", candidate_graph_path=candidate,
    )
    monkeypatch.setattr(extract_promote, "_candidate_owner_for_locator", lambda _loc: child)
    monkeypatch.setattr(extract_promote, "resolve_promotable_ingest_run", lambda *_a, **_k: resolved)
    monkeypatch.setattr(graph_run_registry, "get_extraction_run", lambda _root, run_id: {"parent": parent, "child": child}[run_id])
    from apps.live_control_server import config
    from apps.live_control_server.integrations.dungeonmind import world_graph_writes

    monkeypatch.setattr(config, "world_graph_authority_mode", lambda: config.WORLD_GRAPH_AUTHORITY_DUNGEONMIND)
    monkeypatch.setattr(candidate_graph_admission, "confirm_candidate_graph_admission", lambda **kwargs: kwargs["governed_confirm"]())
    calls = []
    monkeypatch.setattr(world_graph_writes, "confirm_extract_promote_via_dungeonmind", lambda *_a, **_k: calls.append("write") or {"ok": True})
    monkeypatch.setattr(extract_promote, "_build_confirm_receipt", lambda **_kwargs: "receipt")
    request = ExtractPromoteConfirmRequest(
        review_package={"effect": {
            "candidate_admission": {"candidate_locator": str(candidate)},
            EFFECT_KEY: accepted_effect_binding(child, accepted),
        }},
        assertion_ids=["mira"],
    )
    assert extract_promote.confirm(request) == "receipt"
    assert calls == ["write"]


def test_confirm_candidate_owner_uses_exact_uri_and_bytes_not_path_identity(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from application_state.ingest import service as ingest_service

    parent, child = _runs()
    candidate = tmp_path / "out" / "candidate.json"
    candidate.parent.mkdir()
    candidate.write_bytes(b'{"nodes":[]}')
    digest = hashlib.sha256(candidate.read_bytes()).hexdigest()
    child.components["candidate_graph"].sha256 = digest
    seen = []

    def lookup(*, uri, sha256):
        seen.append((uri, sha256))
        return ingest_service.CandidateRunLookup(
            "unique", child
        ) if uri == "repo://out/candidate.json" and sha256 == digest else ingest_service.CandidateRunLookup("not_found")

    monkeypatch.setattr(extract_promote, "repo_root", lambda: tmp_path)
    monkeypatch.setattr(ingest_service, "lookup_extraction_run_by_candidate_component", lookup)
    assert extract_promote._candidate_owner_for_locator(str(candidate)).run_id == child.run_id
    assert seen == [("out/candidate.json", digest), ("repo://out/candidate.json", digest)]
    assert parent.run_id != child.run_id
    unmatched = tmp_path / "out" / "graph_memory" / "derived_candidates" / "child" / "candidate_graph.json"
    unmatched.parent.mkdir(parents=True)
    unmatched.write_text("{}")
    with pytest.raises(extract_promote.ExtractPromoteError) as error:
        extract_promote._candidate_owner_for_locator(str(unmatched))
    assert error.value.code == "candidate_binding_invalid"


def test_semantic_decision_route_requires_gm_and_owns_reviewer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    route = next(
        route for route in extract_promote_routes.router.routes
        if route.path.endswith("/semantic-disposition")
    )
    assert any(
        dependency.call is native_graph_gm_dependency
        for dependency in route.dependant.dependencies
    )
    with pytest.raises(ValidationError):
        RecapSemanticDecisionRequest.model_validate({
            "expectedRevision": 6, "candidateSha256": "d" * 64,
            "decision": "accepted", "reviewDecisionRef": "review:1",
            "reviewerId": "forged",
        })
    seen = []

    def decide(run_id, request, *, reviewer_id):
        seen.append((run_id, request.decision, reviewer_id))
        return RecapSemanticDecisionResponse(
            run_id=run_id, revision=7, candidate_sha256=request.candidate_sha256,
            state=request.decision, basis_sha256="a" * 64,
            review_decision_ref=request.review_decision_ref,
            reviewer_id=reviewer_id, decided_at="2026-10-06T00:00:00Z",
        )

    monkeypatch.setattr(extract_promote_routes, "decide_recap_semantic_disposition", decide)
    valid = extract_promote_routes.post_recap_semantic_disposition(
        SimpleNamespace(query_params={}),
        "child",
        RecapSemanticDecisionRequest(
            expected_revision=6, candidate_sha256="d" * 64,
            decision="accepted", review_decision_ref="review:1",
        ),
        principal=NativeGraphPrincipal(
            subject="server_operator", role="gm", auth_method="local_session"
        ),
    )
    assert seen == [("child", "accepted", "server_operator")]
    assert valid["reviewerId"] == "server_operator"


def test_semantic_decision_http_auth_csrf_body_and_principal(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Exercise actual ASGI routing and Depends with an inert decision seam."""
    import fastapi.dependencies.utils as dependency_utils
    import fastapi.routing as fastapi_routing
    from apps.live_control_server.main import create_app
    from apps.live_control_server.services.agent_graph_auth import (
        authenticate_native_graph_principal,
    )

    # This test host cannot execute even a minimal synchronous FastAPI route
    # through AnyIO's worker pool. Keep full ASGI/Depends dispatch and execute
    # synchronous callables inline; the decision seam remains synthetic.
    async def inline_sync(function, *args, **kwargs):
        return function(*args, **kwargs)

    monkeypatch.setattr(fastapi_routing, "run_in_threadpool", inline_sync)
    monkeypatch.setattr(dependency_utils, "run_in_threadpool", inline_sync)
    monkeypatch.setenv("DMB_AGENT_GRAPH_AUTH_MODE", "local_operator")
    monkeypatch.setenv("DMB_AGENT_GRAPH_AUTH_ENVIRONMENT", "development")
    monkeypatch.setenv("DMB_AGENT_GRAPH_LOCAL_OPERATOR_TOKEN", "synthetic-local-operator-capability-32-characters")
    monkeypatch.setenv("DMB_AGENT_GRAPH_LOCAL_UI_ORIGIN", "http://127.0.0.1:5202")
    monkeypatch.setenv("DMB_AGENT_GRAPH_LOCAL_API_HOST", "127.0.0.1:8000")
    monkeypatch.setenv("DMB_AGENT_GRAPH_SESSION_STORE", str(tmp_path / "private" / "sessions.json"))
    calls = []

    def decide(run_id, request, *, reviewer_id):
        calls.append((run_id, reviewer_id, request.decision))
        return RecapSemanticDecisionResponse(
            run_id=run_id, revision=7, candidate_sha256=request.candidate_sha256,
            state=request.decision, basis_sha256="a" * 64,
            review_decision_ref=request.review_decision_ref,
            reviewer_id=reviewer_id, decided_at="2026-10-06T00:00:00Z",
        )

    monkeypatch.setattr(extract_promote_routes, "decide_recap_semantic_disposition", decide)
    app = create_app()
    url = "/api/live/extract-promote/runs/child/semantic-disposition"
    body = {
        "expectedRevision": 6, "candidateSha256": "d" * 64,
        "decision": "accepted", "reviewDecisionRef": "review:accept",
    }
    async def exercise() -> None:
        transport = httpx.ASGITransport(app=app, client=("127.0.0.1", 50000))
        async with httpx.AsyncClient(transport=transport, base_url="http://127.0.0.1:8000") as client:
            no_auth = await client.post(url, json=body)
            assert no_auth.status_code == 401
            assert no_auth.json()["detail"]["code"] == "graph_auth_required"
            assert calls == []

            app.dependency_overrides[authenticate_native_graph_principal] = lambda: NativeGraphPrincipal(
                subject="player", role="player", auth_method="local_operator"
            )
            player = await client.post(url, json=body)
            assert player.status_code == 403
            assert player.json()["detail"]["code"] == "graph_gm_required"
            assert calls == []
            app.dependency_overrides.clear()

            boot = await client.post(
                "/api/live/agent/local-session",
                headers={"Origin": "http://127.0.0.1:5202", "Sec-Fetch-Site": "same-origin"},
            )
            assert boot.status_code == 200, boot.text
            csrf = boot.json()["csrf_token"]
            no_csrf = await client.post(url, json=body, headers={"Origin": "http://127.0.0.1:5202"})
            assert no_csrf.status_code == 403
            assert no_csrf.json()["detail"]["code"] == "graph_auth_csrf_rejected"
            assert calls == []

            headers = {"Origin": "http://127.0.0.1:5202", "X-DMB-Graph-CSRF": csrf}
            forged = await client.post(url, json={**body, "reviewerId": "forged"}, headers=headers)
            assert forged.status_code == 422
            assert calls == []
            accepted = await client.post(url, json=body, headers=headers)
            assert accepted.status_code == 200, accepted.text
            assert accepted.json()["reviewerId"] == "local_operator"
            assert calls == [("child", "local_operator", "accepted")]

    asyncio.run(exercise())


def test_decision_service_uses_canonical_basis_and_appstate_cas(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from application_state.ingest import service as ingest_service
    from apps.live_control_server.services import source_artifact_registry

    parent, child = _runs()
    held = _assessment(parent, child)
    child.lineage["semantic_disposition"] = {
        "version": 1, "state": "held", "basis_sha256": held.basis_sha256,
    }
    monkeypatch.setattr(graph_run_registry, "get_reviewable_extraction_run", lambda _root, _id: child)
    monkeypatch.setattr(graph_run_registry, "get_extraction_run", lambda _root, _id: parent)
    monkeypatch.setattr(source_artifact_registry, "get_source_artifact", lambda _root, _id: SimpleNamespace(content_sha256="a" * 64))
    calls = []

    def record(run_id, *, expected_revision, basis, decision):
        calls.append((run_id, expected_revision, basis.digest(), decision.reviewer_id))
        decided = child.model_copy(deep=True, update={"revision": child.revision + 1})
        decided.lineage["semantic_disposition"] = {
            "version": 1, "state": decision.state,
            "basis_sha256": basis.digest(),
            "review_decision_ref": decision.review_decision_ref,
            "reviewer_id": decision.reviewer_id,
            "decided_at": "2026-10-06T00:00:00Z", "from_revision": expected_revision,
        }
        return decided

    monkeypatch.setattr(ingest_service, "record_recap_semantic_disposition", record)
    response = extract_promote.decide_recap_semantic_disposition(
        "child",
        RecapSemanticDecisionRequest(
            expected_revision=6, candidate_sha256="d" * 64,
            decision="accepted", review_decision_ref="review:accept",
        ),
        reviewer_id="server_operator",
    )
    assert calls == [("child", 6, held.basis_sha256, "server_operator")]
    assert response.state == "accepted" and response.revision == 7
