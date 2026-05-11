from __future__ import annotations

import json
from pathlib import Path

from evals.sentence_routing_retrieval_falsification.cohort_l3_alias_saturation_canvas_emit import build_payload, emit

_REPO_ROOT = Path(__file__).resolve().parents[1]
_INPUT_TIGHT = _REPO_ROOT / "evals/sentence_routing_retrieval_falsification/artifacts/baselines/cohort_l3_ab_question_delta_c1s1_to_c1s3_v1.json"
_INPUT_NATURAL = _REPO_ROOT / "evals/sentence_routing_retrieval_falsification/artifacts/baselines/cohort_l3_ab_question_delta_natural_v1.json"


def test_build_payload_schema_and_threshold_order() -> None:
    payload = build_payload([_INPUT_TIGHT, _INPUT_NATURAL])
    assert payload["schema_id"] == "dmb_cohort_l3_alias_saturation_v1"
    assert payload["inputs"] == [
        "evals/sentence_routing_retrieval_falsification/artifacts/baselines/cohort_l3_ab_question_delta_c1s1_to_c1s3_v1.json",
        "evals/sentence_routing_retrieval_falsification/artifacts/baselines/cohort_l3_ab_question_delta_natural_v1.json",
    ]
    rows = payload["rows"]
    assert payload["question_count"] == len(rows)
    thresholds = [t["threshold_alias_count"] for t in payload["threshold_scan"]]
    assert thresholds == list(range(max(r["alias_count"] for r in rows) + 1))


def test_emit_writes_markers_and_json_block(tmp_path: Path) -> None:
    out = tmp_path / "alias.canvas.tsx"
    assert emit(input_paths=[_INPUT_TIGHT, _INPUT_NATURAL], output_path=out) == 0
    text = out.read_text(encoding="utf-8")
    assert "BEGIN GENERATED COHORT_L3_ALIAS_SATURATION" in text
    assert "END GENERATED COHORT_L3_ALIAS_SATURATION" in text
    assert "dmb_cohort_l3_alias_saturation_v1" in text
    assert "Promotion gate candidate" in text


def test_contested_slot_fields_present() -> None:
    payload = build_payload([_INPUT_TIGHT, _INPUT_NATURAL])
    row = payload["rows"][0]
    assert "contested_slot_unit_in" in row
    assert "contested_slot_unit_out" in row
    assert "alias_tokens_added" in row
    assert isinstance(row["alias_count"], int)
