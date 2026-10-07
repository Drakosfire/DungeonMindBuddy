"""A corrected recap child needs exact semantic acceptance beyond evidence validity."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from apps.live_control_server.models.extract_promote import ExtractPromotePrepareRequest
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
