from __future__ import annotations

import json
from pathlib import Path

from evals.sentence_routing_retrieval_falsification.cohort_l3_question_deep_dive_canvas_emit import DEFAULT_INPUT, emit

_REPO_ROOT = Path(__file__).resolve().parents[1]


def test_emit_writes_canvas_with_markers() -> None:
    assert emit() == 0
    p = _REPO_ROOT / 'canvases/cohort-l3-ab-question-deep-dive.canvas.tsx'
    text = p.read_text(encoding='utf-8')
    assert 'BEGIN GENERATED COHORT_L3_QUESTION_DEEP_DIVE' in text
    assert 'END GENERATED COHORT_L3_QUESTION_DEEP_DIVE' in text
    assert 'question_count' in text
    assert 'Required must-hit tokens:' in text
    assert 'Matched must-hit tokens:' in text
    assert 'Missing must-hit tokens:' in text
    assert 'Swapped out vs legacy-only reference:' in text
    assert '<h3>Baseline</h3>' not in text
    assert 'Default (equivalence-augmented ranking)' in text


def test_artifact_schema_exists() -> None:
    p = _REPO_ROOT / 'evals/sentence_routing_retrieval_falsification/artifacts/baselines/cohort_l3_ab_question_delta_c1s1_to_c1s3_v1.json'
    data = json.loads(p.read_text(encoding='utf-8'))
    assert data['schema_id'] == 'dmb_breadcrumb_query_cohort_l3_question_delta_v1'


def test_emit_supports_custom_input_output(tmp_path: Path) -> None:
    out = tmp_path / "custom.canvas.tsx"
    assert emit(input_path=DEFAULT_INPUT, output_path=out) == 0
    text = out.read_text(encoding="utf-8")
    assert "BEGIN GENERATED COHORT_L3_QUESTION_DEEP_DIVE" in text
    assert "question_count" in text
