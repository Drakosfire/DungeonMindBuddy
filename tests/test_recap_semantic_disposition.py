"""A corrected recap child needs exact semantic acceptance beyond evidence validity."""

from __future__ import annotations

import json
import hashlib
from pathlib import Path
from types import SimpleNamespace

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


@pytest.mark.parametrize("case", ["missing_binding", "status_drift", "domain_drift"])
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
    candidate = tmp_path / "child.json"
    candidate.write_text("{}")
    resolved = SimpleNamespace(
        run_id=child.run_id, source_revision_id="a" * 64,
        source_span_index_path=tmp_path / "spans.json",
        candidate_graph_path=candidate,
    )
    if case == "status_drift":
        child.status = ExtractionRunStatus.REJECTED
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
    binding = accepted_effect_binding(child, accepted) if case != "missing_binding" else None
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
