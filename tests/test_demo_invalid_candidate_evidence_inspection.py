"""An invalid quote is inspectable, but never becomes publication evidence."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from apps.live_control_server.services import candidate_graph_admission, extract_promote, graph_run_registry


def _fixture(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    *,
    false_quote: bool = True,
) -> str:
    source = tmp_path / "source.md"
    source.write_text("Torbin, who bought the strange seed, repaired the roof.\n")
    candidate = tmp_path / "candidate.json"
    candidate.write_text(json.dumps({"campaign_id": "demo", "session_id": None}))
    artifact_id = "artifact:worldbuilding:demo:r1:abc"
    span_id = f"{artifact_id}:span:abc:1-1"

    refs = [
        SimpleNamespace(
            source_artifact_id=artifact_id,
            source_span_ref_id=span_id,
            anchor_quotes=["Torbin, who bought the strange seed"]
            + (["Torbin bought the strange seed"] if false_quote else []),
        )
    ]
    typed = SimpleNamespace(
        nodes=[SimpleNamespace(node_id="torbin", label="Torbin", description="Villager", evidence_refs=refs)],
        edges=[],
    )
    resolved = SimpleNamespace(
        run_id="run-demo",
        status="reviewable",
        normalized_recap_path=source,
        candidate_graph_path=candidate,
        source_artifact_id=artifact_id,
        source_revision_id="sha256:abc",
        campaign_id="demo",
        session_id=None,
        source_domain="worldbuilding",
        world_id="demo",
        diagnostics=[],
    )
    span_index = SimpleNamespace(
        spans=[SimpleNamespace(source_span_id=span_id, start_line=1, end_line=1)]
    )
    capability = SimpleNamespace(
        world_id="demo",
        world_state="uninitialized",
        eligible=True,
        reason=None,
    )
    monkeypatch.setattr(candidate_graph_admission, "validate_candidate_document_integrity", lambda _: typed)
    monkeypatch.setattr(extract_promote, "resolve_promotable_ingest_run", lambda *_args, **_kwargs: resolved)
    monkeypatch.setattr(extract_promote, "_load_frozen_span_index_for_resolved_run", lambda _: span_index)
    monkeypatch.setattr(extract_promote, "resolve_first_world_capability", lambda **_kwargs: capability)
    monkeypatch.setattr(
        graph_run_registry, "get_extraction_run",
        lambda *_args, **_kwargs: SimpleNamespace(lineage={}),
    )
    return span_id


def test_exact_run_review_keeps_false_quote_but_blocks_publication(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _fixture(monkeypatch, tmp_path)

    review = extract_promote.get_exact_run_review_package("run-demo")

    assert review.run_id == "run-demo"
    assert review.inspection_status == "invalid_evidence"
    assert review.invalid_evidence_count == 1
    assert [item.assertion_id for item in review.assertions] == ["torbin"]
    evidence = review.assertions[0].evidence[0]
    assert evidence.anchor_quotes == [
        "Torbin, who bought the strange seed",
        "Torbin bought the strange seed",
    ]
    assert evidence.invalid_anchor_quotes == ["Torbin bought the strange seed"]
    assert review.promotable is False
    assert review.first_world_publish_eligible is False
    assert "publication is blocked" in (review.first_world_publish_reason or "")


def test_strict_publication_validation_still_rejects_false_quote(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    span_id = _fixture(monkeypatch, tmp_path)
    with pytest.raises(extract_promote.ExtractPromoteError) as exc_info:
        extract_promote._assert_and_project_candidate_evidence(
            candidate_payload={"campaign_id": "demo", "session_id": None},
            source_prose="Torbin, who bought the strange seed, repaired the roof.\n",
            source_artifact_id="artifact:worldbuilding:demo:r1:abc",
            span_index=SimpleNamespace(
                spans=[SimpleNamespace(source_span_id=span_id, start_line=1, end_line=1)]
            ),
        )
    assert exc_info.value.code == "run_not_promotable"
    assert any(item.code == "false_anchor_quote" for item in exc_info.value.diagnostics)


def test_literal_candidate_retains_publication_capability(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _fixture(monkeypatch, tmp_path, false_quote=False)
    review = extract_promote.get_exact_run_review_package("run-demo")
    assert review.inspection_status == "ready"
    assert review.invalid_evidence_count == 0
    assert review.assertions[0].evidence[0].invalid_anchor_quotes == []
    assert review.first_world_publish_eligible is True


def test_unknown_span_remains_hard_failure(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _fixture(monkeypatch, tmp_path)
    monkeypatch.setattr(
        extract_promote,
        "_load_frozen_span_index_for_resolved_run",
        lambda _: SimpleNamespace(spans=[]),
    )
    with pytest.raises(extract_promote.ExtractPromoteError) as exc_info:
        extract_promote.get_exact_run_review_package("run-demo")
    assert exc_info.value.code == "run_not_promotable"
    assert exc_info.value.inspection_status == "blocked"
