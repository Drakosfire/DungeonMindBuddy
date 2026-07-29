"""Tests for TL01B temporal shadow extraction."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from graph_memory.kernel.temporal import TEMPORAL_ENVELOPE_SCHEMA
from graph_memory.temporal_shadow_extraction import (
    FakeTemporalShadowExtractionClient,
    TemporalShadowExtractionError,
    build_assertion_evidence_packets,
    compare_temporal_overlays,
    ground_and_convert_model_batch,
    load_temporal_shadow_extraction_case,
    run_temporal_shadow_extraction,
)
from graph_memory.temporal_shadow_extraction_cli import main as extraction_cli_main
from graph_memory.temporal_shadow_extraction_schema import (
    temporal_model_annotation_batch_text_format,
)
from graph_memory.temporal_shadow import load_temporal_annotation_overlay

REPO_ROOT = Path(__file__).resolve().parents[1]
CASE_PATH = (
    REPO_ROOT
    / "evals/graph_memory_layer/examples/temporal_shadow_cohort/temporal-case.json"
)


def _session_point(session_id: str) -> dict[str, Any]:
    return {
        "kind": "session",
        "session_id": session_id,
        "campaign_id": "longmont-c2",
        "calendar_id": None,
        "value": None,
        "relation": None,
        "anchor_ref": None,
        "raw_expression": None,
        "certainty": "explicit",
    }


def _occurrence_point(session_id: str) -> dict[str, Any]:
    return {
        "kind": "point",
        "point": _session_point(session_id),
        "start": None,
        "end": None,
        "raw_expression": None,
    }


def _valid_start(session_id: str) -> dict[str, Any]:
    return {
        "start": _session_point(session_id),
        "end": None,
        "raw_expression": None,
    }


def _load_case_bundle() -> tuple[Any, Any, Any, dict[str, Any]]:
    case = load_temporal_shadow_extraction_case(CASE_PATH, repo_root=REPO_ROOT)
    base_path = REPO_ROOT / case.base_contribution_path
    from graph_memory.kernel.contribution_models import GraphContribution

    contribution = GraphContribution.model_validate(
        json.loads(base_path.read_text(encoding="utf-8"))
    )
    gold = load_temporal_annotation_overlay(
        json.loads((REPO_ROOT / case.gold_overlay_path).read_text(encoding="utf-8"))
    )
    packets = build_assertion_evidence_packets(contribution, case, repo_root=REPO_ROOT)
    return case, contribution, gold, packets


def _gold_to_model_batch(gold: Any) -> dict[str, Any]:
    annotations: list[dict[str, Any]] = []
    for ann in gold.annotations:
        occurrence = None
        valid = None
        if ann.occurrence_time is not None:
            point = ann.occurrence_time.point.session_id  # type: ignore[union-attr]
            occurrence = _occurrence_point(point)
        if ann.valid_time is not None and ann.valid_time.start is not None:
            valid = _valid_start(ann.valid_time.start.session_id)  # type: ignore[union-attr]
        annotations.append(
            {
                "base_assertion_id": ann.base_assertion_id,
                "interpretation_status": ann.interpretation_status,
                "occurrence_time": occurrence,
                "valid_time": valid,
                "evidence_ref_ids": list(ann.evidence_ref_ids),
                "source_phrase": ann.source_phrase,
                "extraction_confidence": ann.extraction_confidence,
                "diagnostics": list(ann.diagnostics),
            }
        )
    return {"schema": "dmb_temporal_model_annotation_batch_v1", "annotations": annotations}


def test_responses_format_is_strict_json_schema() -> None:
    fmt = temporal_model_annotation_batch_text_format()
    assert fmt["format"]["type"] == "json_schema"
    assert fmt["format"]["strict"] is True


def test_load_sealed_case_and_packets() -> None:
    case, contribution, _gold, packets = _load_case_bundle()
    assert len(case.selected_assertion_ids) == 6
    assert len(packets) == 6
    assert contribution.candidate_assertions


def test_grounding_rejects_target_set_mismatch() -> None:
    case, contribution, _gold, packets = _load_case_bundle()
    batch = _gold_to_model_batch(_gold)
    batch["annotations"] = batch["annotations"][:-1]
    with pytest.raises(TemporalShadowExtractionError) as exc:
        ground_and_convert_model_batch(
            raw_batch=batch,
            contribution=contribution,
            case=case,
            packets=packets,
        )
    assert exc.value.code == "target_set_mismatch"


def test_fake_client_happy_path_matches_gold(tmp_path: Path) -> None:
    case, _contribution, gold, _packets = _load_case_bundle()
    batch = _gold_to_model_batch(gold)
    client = FakeTemporalShadowExtractionClient(batch)
    run = run_temporal_shadow_extraction(
        CASE_PATH,
        tmp_path / "run",
        client=client,
        model_id="fake-model",
        repo_root=REPO_ROOT,
    )
    assert run.comparison_verdict == "pass"
    comparison = json.loads((tmp_path / "run/comparison.json").read_text())
    assert comparison["metrics"]["exact_match_count"] == 6


def test_negative_provenance_does_not_infer_occurrence_in_preview(tmp_path: Path) -> None:
    case, contribution, gold, packets = _load_case_bundle()
    batch = _gold_to_model_batch(gold)
    road_id = next(
        a.assertion_id
        for a in contribution.candidate_assertions
        if a.label == "Road observation"
    )
    for item in batch["annotations"]:
        if item["base_assertion_id"] == road_id:
            assert item["interpretation_status"] == "not_applicable"
            assert item["occurrence_time"] is None

    client = FakeTemporalShadowExtractionClient(batch)
    run_temporal_shadow_extraction(
        CASE_PATH,
        tmp_path / "neg",
        client=client,
        model_id="fake-model",
        repo_root=REPO_ROOT,
    )
    preview = json.loads((tmp_path / "neg/preview.json").read_text())
    row = next(r for r in preview["rows"] if r["base_assertion_id"] == road_id)
    scope = row.get("shadow_temporal_scope") or {}
    assert scope.get("schema") == TEMPORAL_ENVELOPE_SCHEMA
    assert scope.get("occurrence_time") is None
    assert scope.get("valid_time") is None


def test_compare_detects_status_mismatch() -> None:
    _case, _contribution, gold, _packets = _load_case_bundle()
    predicted = load_temporal_annotation_overlay(
        json.loads(json.dumps(gold.model_dump(by_alias=True)))
    )
    first = predicted.annotations[0]
    mutated = predicted.model_copy(
        update={
            "annotations": [
                first.model_copy(update={"interpretation_status": "unresolved"}),
                *predicted.annotations[1:],
            ]
        }
    )
    with pytest.raises(Exception):
        load_temporal_annotation_overlay(mutated.model_dump(by_alias=True))

    # Build a fresh predicted overlay with same IDs but different status via gold copy hack
    pred_payload = json.loads(json.dumps(gold.model_dump(by_alias=True)))
    pred_payload["annotations"][0]["interpretation_status"] = "unresolved"
    pred_payload["annotations"][0]["occurrence_time"] = None
    pred_payload["annotations"][0]["valid_time"] = None
    pred_payload["annotations"][0]["diagnostics"] = ["cannot ground"]
    pred_payload["annotations"][0]["source_phrase"] = pred_payload["annotations"][0][
        "source_phrase"
    ]
    from graph_memory.temporal_shadow_extraction import compute_temporal_annotation_id

    ann0 = pred_payload["annotations"][0]
    ann0["annotation_id"] = compute_temporal_annotation_id(
        base_assertion_id=ann0["base_assertion_id"],
        interpretation_status=ann0["interpretation_status"],
        occurrence_time=None,
        valid_time=None,
        evidence_ref_ids=ann0["evidence_ref_ids"],
        source_phrase=ann0["source_phrase"],
        extraction_confidence=ann0["extraction_confidence"],
        diagnostics=ann0["diagnostics"],
    )
    from graph_memory.temporal_shadow import (
        TemporalAssertionAnnotationV1,
        TemporalOverlayProducerV1,
        compute_temporal_overlay_id,
    )

    anns = [TemporalAssertionAnnotationV1.model_validate(a) for a in pred_payload["annotations"]]
    producer = TemporalOverlayProducerV1(kind="model_shadow", name="test", version="1")
    pred_payload["overlay_id"] = compute_temporal_overlay_id(
        base_contribution_id=pred_payload["base_contribution_id"],
        base_contribution_source_payload_sha256=pred_payload[
            "base_contribution_source_payload_sha256"
        ],
        producer=producer,
        annotations=anns,
    )
    pred_payload["producer"] = producer.model_dump()
    predicted_overlay = load_temporal_annotation_overlay(pred_payload)
    comparison = compare_temporal_overlays(predicted_overlay, gold)
    assert comparison.verdict in {"partial", "fail"}
    assert (
        comparison.metrics.status_mismatch_count
        + comparison.metrics.safe_under_resolution_count
        + comparison.metrics.unsafe_over_resolution_count
    ) >= 1
    assert comparison.evaluation_verdict in {
        "SAFE_FOR_NEXT_EXPERIMENT",
        "ITERATE_PROMPT",
        "BLOCKED_BY_EVIDENCE",
        "BLOCKED_BY_CONTRACT",
        "PROVIDER_FAILURE",
    }


def test_cli_smoke(tmp_path: Path) -> None:
    case, _c, gold, _p = _load_case_bundle()
    batch = _gold_to_model_batch(gold)

    class _InjectingFake(FakeTemporalShadowExtractionClient):
        pass

    # Patch run to use fake via env not available — call run directly in prior tests.
    out = tmp_path / "cli-out"
    # CLI uses real OpenAI; run module with monkeypatch
    import graph_memory.temporal_shadow_extraction as mod

    original = mod.OpenAITemporalShadowExtractionClient

    class _CliFake(FakeTemporalShadowExtractionClient):
        def __init__(self) -> None:
            super().__init__(batch)

    mod.OpenAITemporalShadowExtractionClient = _CliFake  # type: ignore[misc]
    try:
        rc = extraction_cli_main(
            ["--case", str(CASE_PATH), "--output-dir", str(out), "--overwrite"]
        )
    finally:
        mod.OpenAITemporalShadowExtractionClient = original  # type: ignore[misc]
    assert rc == 0
    assert (out / "run-manifest.json").is_file()


def test_digest_mismatch_on_case(tmp_path: Path) -> None:
    case = load_temporal_shadow_extraction_case(CASE_PATH, repo_root=REPO_ROOT)
    bad = json.loads(CASE_PATH.read_text())
    bad["base_contribution_sha256"] = "0" * 64
    bad_path = tmp_path / "bad-case.json"
    bad_path.write_text(json.dumps(bad))
    with pytest.raises(TemporalShadowExtractionError) as exc:
        load_temporal_shadow_extraction_case(bad_path, repo_root=REPO_ROOT)
    assert exc.value.code == "digest_mismatch"
