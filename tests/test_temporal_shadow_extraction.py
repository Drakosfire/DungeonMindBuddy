"""Tests for TL01B temporal shadow extraction."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from graph_memory.kernel.temporal import TEMPORAL_ENVELOPE_SCHEMA
from graph_memory.temporal_shadow_extraction import (
    FakeTemporalShadowExtractionClient,
    OpenAITemporalShadowExtractionClient,
    TemporalShadowExtractionError,
    build_assertion_evidence_packets,
    compare_temporal_overlays,
    compute_temporal_annotation_id,
    ground_and_convert_model_batch,
    load_bound_gold_overlay,
    load_temporal_shadow_extraction_case,
    resolve_prompt_instructions,
    run_temporal_shadow_extraction,
)
from graph_memory.temporal_shadow_extraction_cli import main as extraction_cli_main
from graph_memory.temporal_shadow_extraction_schema import (
    TEMPORAL_SHADOW_PROMPT_VERSION,
    temporal_model_annotation_batch_text_format,
)
from graph_memory.temporal_shadow import (
    TemporalAssertionAnnotationV1,
    TemporalOverlayProducerV1,
    compute_temporal_overlay_id,
    load_temporal_annotation_overlay,
)

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
    gold = load_bound_gold_overlay(case, contribution, repo_root=REPO_ROOT)
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


def _rebuild_overlay_from_payload(pred_payload: dict[str, Any]) -> Any:
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
    return load_temporal_annotation_overlay(pred_payload)


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
    case, contribution, gold, packets = _load_case_bundle()
    batch = _gold_to_model_batch(gold)
    batch["annotations"] = batch["annotations"][:-1]
    with pytest.raises(TemporalShadowExtractionError) as exc:
        ground_and_convert_model_batch(
            raw_batch=batch,
            contribution=contribution,
            case=case,
            packets=packets,
            model_id="fake-model",
            prompt_version=TEMPORAL_SHADOW_PROMPT_VERSION,
        )
    assert exc.value.code == "target_set_mismatch"


def test_fake_client_happy_path_matches_gold(tmp_path: Path) -> None:
    _case, _contribution, gold, _packets = _load_case_bundle()
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
    assert run.executed_prompt_version == TEMPORAL_SHADOW_PROMPT_VERSION
    comparison = json.loads((tmp_path / "run/comparison.json").read_text())
    assert comparison["metrics"]["exact_match_count"] == 6


def test_compare_ignores_metadata_differences() -> None:
    _case, _contribution, gold, _packets = _load_case_bundle()
    pred_payload = json.loads(json.dumps(gold.model_dump(by_alias=True)))
    for ann in pred_payload["annotations"]:
        ann["annotation_id"] = "temporal-annotation:deadbeefdeadbeef"
        ann["diagnostics"] = ["completely different human wording"]
        if ann.get("source_phrase"):
            ann["source_phrase"] = ann["source_phrase"]  # same semantic, keep grounded text
        ann["extraction_confidence"] = (
            "low" if ann["extraction_confidence"] != "low" else "medium"
        )
    # Recompute overlay ID for producer change while keeping semantic fields.
    producer = TemporalOverlayProducerV1(
        kind="model_shadow", name="other-producer", version="x"
    )
    anns = [TemporalAssertionAnnotationV1.model_validate(a) for a in pred_payload["annotations"]]
    # Restore valid annotation IDs that match TL01 pattern after validation.
    for idx, ann in enumerate(anns):
        rebuilt = ann.model_copy(
            update={
                "annotation_id": f"temporal-annotation:{idx:016x}",
                "diagnostics": ["completely different human wording"],
                "extraction_confidence": "low",
            }
        )
        anns[idx] = rebuilt
    pred_payload["annotations"] = [a.model_dump(by_alias=True) for a in anns]
    pred_payload["producer"] = producer.model_dump()
    pred_payload["overlay_id"] = compute_temporal_overlay_id(
        base_contribution_id=pred_payload["base_contribution_id"],
        base_contribution_source_payload_sha256=pred_payload[
            "base_contribution_source_payload_sha256"
        ],
        producer=producer,
        annotations=anns,
    )
    predicted = load_temporal_annotation_overlay(pred_payload)
    comparison = compare_temporal_overlays(predicted, gold)
    assert comparison.metrics.exact_match_count == 6
    assert comparison.verdict == "pass"
    assert comparison.evaluation_verdict == "SAFE_FOR_NEXT_EXPERIMENT"


def test_resolved_null_source_phrase_rejected() -> None:
    case, contribution, gold, packets = _load_case_bundle()
    batch = _gold_to_model_batch(gold)
    for item in batch["annotations"]:
        if item["interpretation_status"] == "resolved":
            item["source_phrase"] = None
            break
    with pytest.raises(TemporalShadowExtractionError) as exc:
        ground_and_convert_model_batch(
            raw_batch=batch,
            contribution=contribution,
            case=case,
            packets=packets,
            model_id="fake-model",
            prompt_version=TEMPORAL_SHADOW_PROMPT_VERSION,
        )
    assert exc.value.code == "grounding_failure"


def test_resolved_ungrounded_phrase_rejected() -> None:
    case, contribution, gold, packets = _load_case_bundle()
    batch = _gold_to_model_batch(gold)
    for item in batch["annotations"]:
        if item["interpretation_status"] == "resolved":
            item["source_phrase"] = "this phrase is not in any snippet"
            break
    with pytest.raises(TemporalShadowExtractionError) as exc:
        ground_and_convert_model_batch(
            raw_batch=batch,
            contribution=contribution,
            case=case,
            packets=packets,
            model_id="fake-model",
            prompt_version=TEMPORAL_SHADOW_PROMPT_VERSION,
        )
    assert exc.value.code == "grounding_failure"


def test_not_applicable_requires_nonblank_explanation() -> None:
    case, contribution, gold, packets = _load_case_bundle()
    batch = _gold_to_model_batch(gold)
    for item in batch["annotations"]:
        if item["interpretation_status"] == "not_applicable":
            item["diagnostics"] = ["   "]
            break
    with pytest.raises(TemporalShadowExtractionError) as exc:
        ground_and_convert_model_batch(
            raw_batch=batch,
            contribution=contribution,
            case=case,
            packets=packets,
            model_id="fake-model",
            prompt_version=TEMPORAL_SHADOW_PROMPT_VERSION,
        )
    assert exc.value.code == "grounding_failure"


def test_duplicate_evidence_registry_ids_rejected(tmp_path: Path) -> None:
    payload = json.loads(CASE_PATH.read_text())
    payload["evidence_registry"].append(dict(payload["evidence_registry"][0]))
    bad = tmp_path / "dup-evidence.json"
    bad.write_text(json.dumps(payload))
    with pytest.raises(TemporalShadowExtractionError) as exc:
        load_temporal_shadow_extraction_case(bad, repo_root=REPO_ROOT)
    assert exc.value.code == "invalid_case"
    assert "Duplicate evidence_ref_id" in str(exc.value)


def test_conflicting_source_artifact_definitions_rejected(tmp_path: Path) -> None:
    payload = json.loads(CASE_PATH.read_text())
    first = payload["evidence_registry"][0]
    conflict = dict(payload["evidence_registry"][1])
    conflict["source_artifact_id"] = first["source_artifact_id"]
    conflict["evidence_ref_id"] = "evidence:tl01b:conflict-artifact"
    payload["evidence_registry"].append(conflict)
    bad = tmp_path / "conflict-artifact.json"
    bad.write_text(json.dumps(payload))
    with pytest.raises(TemporalShadowExtractionError) as exc:
        load_temporal_shadow_extraction_case(bad, repo_root=REPO_ROOT)
    assert exc.value.code == "invalid_case"
    assert "Conflicting source artifact" in str(exc.value)


def test_gold_overlay_digest_mismatch(tmp_path: Path) -> None:
    payload = json.loads(CASE_PATH.read_text())
    payload["gold_overlay_sha256"] = "0" * 64
    bad = tmp_path / "bad-gold-digest.json"
    bad.write_text(json.dumps(payload))
    with pytest.raises(TemporalShadowExtractionError) as exc:
        load_temporal_shadow_extraction_case(bad, repo_root=REPO_ROOT)
    assert exc.value.code == "digest_mismatch"


def test_gold_stale_base_rejected(tmp_path: Path) -> None:
    _case, _contribution, gold, _packets = _load_case_bundle()
    gold_payload = json.loads(json.dumps(gold.model_dump(by_alias=True)))
    gold_payload["base_contribution_id"] = "contribution:stale"
    anns = [TemporalAssertionAnnotationV1.model_validate(a) for a in gold_payload["annotations"]]
    producer = TemporalOverlayProducerV1.model_validate(gold_payload["producer"])
    gold_payload["overlay_id"] = compute_temporal_overlay_id(
        base_contribution_id=gold_payload["base_contribution_id"],
        base_contribution_source_payload_sha256=gold_payload[
            "base_contribution_source_payload_sha256"
        ],
        producer=producer,
        annotations=anns,
    )
    nested = (
        REPO_ROOT
        / "evals/graph_memory_layer/examples/temporal_shadow_cohort"
        / "_tmp_stale_gold.json"
    )
    nested.write_text(json.dumps(gold_payload))
    try:
        case_payload = json.loads(CASE_PATH.read_text())
        case_payload["gold_overlay_path"] = (
            "evals/graph_memory_layer/examples/temporal_shadow_cohort/_tmp_stale_gold.json"
        )
        case_payload["gold_overlay_sha256"] = __import__("hashlib").sha256(
            nested.read_bytes()
        ).hexdigest()
        case_path = tmp_path / "case-stale.json"
        case_path.write_text(json.dumps(case_payload))
        with pytest.raises(TemporalShadowExtractionError) as exc:
            load_temporal_shadow_extraction_case(case_path, repo_root=REPO_ROOT)
        assert exc.value.code == "invalid_gold_overlay"
    finally:
        nested.unlink(missing_ok=True)


def test_gold_wrong_target_set_rejected(tmp_path: Path) -> None:
    _case, _contribution, gold, _packets = _load_case_bundle()
    gold_payload = json.loads(json.dumps(gold.model_dump(by_alias=True)))
    gold_payload["annotations"] = gold_payload["annotations"][:-1]
    anns = [TemporalAssertionAnnotationV1.model_validate(a) for a in gold_payload["annotations"]]
    producer = TemporalOverlayProducerV1.model_validate(gold_payload["producer"])
    gold_payload["overlay_id"] = compute_temporal_overlay_id(
        base_contribution_id=gold_payload["base_contribution_id"],
        base_contribution_source_payload_sha256=gold_payload[
            "base_contribution_source_payload_sha256"
        ],
        producer=producer,
        annotations=anns,
    )
    nested = (
        REPO_ROOT
        / "evals/graph_memory_layer/examples/temporal_shadow_cohort"
        / "_tmp_wrong_targets.json"
    )
    nested.write_text(json.dumps(gold_payload))
    try:
        case_payload = json.loads(CASE_PATH.read_text())
        case_payload["gold_overlay_path"] = (
            "evals/graph_memory_layer/examples/temporal_shadow_cohort/_tmp_wrong_targets.json"
        )
        case_payload["gold_overlay_sha256"] = __import__("hashlib").sha256(
            nested.read_bytes()
        ).hexdigest()
        case_path = tmp_path / "case-wrong-targets.json"
        case_path.write_text(json.dumps(case_payload))
        with pytest.raises(TemporalShadowExtractionError) as exc:
            load_temporal_shadow_extraction_case(case_path, repo_root=REPO_ROOT)
        assert exc.value.code == "invalid_gold_overlay"
    finally:
        nested.unlink(missing_ok=True)


def test_gold_non_human_producer_rejected(tmp_path: Path) -> None:
    _case, _contribution, gold, _packets = _load_case_bundle()
    gold_payload = json.loads(json.dumps(gold.model_dump(by_alias=True)))
    producer = TemporalOverlayProducerV1(
        kind="fixture", name="not-gold", version="1"
    )
    anns = [TemporalAssertionAnnotationV1.model_validate(a) for a in gold_payload["annotations"]]
    gold_payload["producer"] = producer.model_dump()
    gold_payload["overlay_id"] = compute_temporal_overlay_id(
        base_contribution_id=gold_payload["base_contribution_id"],
        base_contribution_source_payload_sha256=gold_payload[
            "base_contribution_source_payload_sha256"
        ],
        producer=producer,
        annotations=anns,
    )
    nested = (
        REPO_ROOT
        / "evals/graph_memory_layer/examples/temporal_shadow_cohort"
        / "_tmp_non_gold.json"
    )
    nested.write_text(json.dumps(gold_payload))
    try:
        case_payload = json.loads(CASE_PATH.read_text())
        case_payload["gold_overlay_path"] = (
            "evals/graph_memory_layer/examples/temporal_shadow_cohort/_tmp_non_gold.json"
        )
        case_payload["gold_overlay_sha256"] = __import__("hashlib").sha256(
            nested.read_bytes()
        ).hexdigest()
        case_path = tmp_path / "case-non-gold.json"
        case_path.write_text(json.dumps(case_payload))
        with pytest.raises(TemporalShadowExtractionError) as exc:
            load_temporal_shadow_extraction_case(case_path, repo_root=REPO_ROOT)
        assert exc.value.code == "invalid_gold_overlay"
    finally:
        nested.unlink(missing_ok=True)


def test_unsupported_prompt_version_rejected(tmp_path: Path) -> None:
    payload = json.loads(CASE_PATH.read_text())
    payload["prompt_version"] = "tl01b-v999"
    bad = tmp_path / "bad-prompt.json"
    bad.write_text(json.dumps(payload))
    with pytest.raises(TemporalShadowExtractionError) as exc:
        load_temporal_shadow_extraction_case(bad, repo_root=REPO_ROOT)
    assert exc.value.code == "unsupported_prompt_version"
    with pytest.raises(TemporalShadowExtractionError):
        resolve_prompt_instructions("tl01b-v999")


def test_partial_prior_run_requires_overwrite(tmp_path: Path) -> None:
    out = tmp_path / "partial"
    out.mkdir()
    (out / "model-output.json").write_text("{}\n")
    _case, _contribution, gold, _packets = _load_case_bundle()
    client = FakeTemporalShadowExtractionClient(_gold_to_model_batch(gold))
    with pytest.raises(TemporalShadowExtractionError) as exc:
        run_temporal_shadow_extraction(
            CASE_PATH,
            out,
            client=client,
            model_id="fake-model",
            repo_root=REPO_ROOT,
            overwrite=False,
        )
    assert "non-empty" in str(exc.value).lower()
    run = run_temporal_shadow_extraction(
        CASE_PATH,
        out,
        client=client,
        model_id="fake-model",
        repo_root=REPO_ROOT,
        overwrite=True,
    )
    assert run.comparison_verdict == "pass"


def test_openai_client_uses_dungeonmind_api_client() -> None:
    fake_response = MagicMock()
    fake_response.refusal = None
    fake_response.status = "completed"
    fake_response.output_text = json.dumps(
        {"schema": "dmb_temporal_model_annotation_batch_v1", "annotations": []}
    )
    fake_response.id = "resp_test"
    fake_response.usage = MagicMock(input_tokens=1, output_tokens=2)

    with patch(
        "graph_memory.temporal_shadow_extraction.DungeonMindApiClient"
    ) as mock_api_cls:
        mock_api = MagicMock()
        mock_api.responses_create.return_value = MagicMock(
            response=fake_response, elapsed_ms=12.5
        )
        mock_api_cls.wrap.return_value = mock_api
        with patch("graph_memory.temporal_shadow_extraction.OpenAI"):
            with patch(
                "graph_memory.temporal_shadow_extraction.load_dungeonmindbuddy_dotenv"
            ):
                client = OpenAITemporalShadowExtractionClient()
                parsed, meta = client.extract_annotations(
                    instructions="x",
                    user_content="y",
                    model_id="gpt-test",
                )
    mock_api.responses_create.assert_called_once()
    kwargs = mock_api.responses_create.call_args.kwargs
    assert kwargs["action"] == "temporal_shadow.extract_annotations"
    assert kwargs["text"]["format"]["type"] == "json_schema"
    assert kwargs["text"]["format"]["strict"] is True
    assert parsed["schema"] == "dmb_temporal_model_annotation_batch_v1"
    assert meta.elapsed_ms == 12.5


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
    pred_payload = json.loads(json.dumps(gold.model_dump(by_alias=True)))
    pred_payload["annotations"][0]["interpretation_status"] = "unresolved"
    pred_payload["annotations"][0]["occurrence_time"] = None
    pred_payload["annotations"][0]["valid_time"] = None
    pred_payload["annotations"][0]["diagnostics"] = ["cannot ground"]
    ann0 = pred_payload["annotations"][0]
    ann0["annotation_id"] = compute_temporal_annotation_id(
        case_id="test-case",
        model_id="fake-model",
        prompt_version=TEMPORAL_SHADOW_PROMPT_VERSION,
        base_assertion_id=ann0["base_assertion_id"],
        interpretation_status=ann0["interpretation_status"],
        occurrence_time=None,
        valid_time=None,
        evidence_ref_ids=ann0["evidence_ref_ids"],
        source_phrase=ann0["source_phrase"],
        extraction_confidence=ann0["extraction_confidence"],
        diagnostics=ann0["diagnostics"],
    )
    predicted_overlay = _rebuild_overlay_from_payload(pred_payload)
    comparison = compare_temporal_overlays(predicted_overlay, gold)
    assert comparison.verdict in {"partial", "fail"}
    assert (
        comparison.metrics.status_mismatch_count
        + comparison.metrics.safe_under_resolution_count
        + comparison.metrics.unsafe_over_resolution_count
    ) >= 1


def test_cli_smoke(tmp_path: Path) -> None:
    _case, _c, gold, _p = _load_case_bundle()
    batch = _gold_to_model_batch(gold)
    out = tmp_path / "cli-out"
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
    manifest = json.loads((out / "run-manifest.json").read_text())
    assert manifest["executed_prompt_version"] == TEMPORAL_SHADOW_PROMPT_VERSION


def test_digest_mismatch_on_case(tmp_path: Path) -> None:
    bad = json.loads(CASE_PATH.read_text())
    bad["base_contribution_sha256"] = "0" * 64
    bad_path = tmp_path / "bad-case.json"
    bad_path.write_text(json.dumps(bad))
    with pytest.raises(TemporalShadowExtractionError) as exc:
        load_temporal_shadow_extraction_case(bad_path, repo_root=REPO_ROOT)
    assert exc.value.code == "digest_mismatch"
