from __future__ import annotations

from evals.sentence_routing_retrieval_falsification import benchmark_review_canvas_template as brc


def test_generated_block_wraps_payload_with_markers() -> None:
    block = brc.generated_block(
        begin="// BEGIN GENERATED TEST",
        end="// END GENERATED TEST",
        const_name="testGenerated",
        payload={"question_count": 3},
    )
    assert block.startswith("// BEGIN GENERATED TEST\n")
    assert block.endswith("// END GENERATED TEST")
    assert '"question_count": 3' in block
    assert "const testGenerated =" in block


def test_missed_detail_rows_include_route_and_gate_axes() -> None:
    rows = brc.missed_detail_rows(
        violations=["missing_expected_route_hit"],
        arm={
            "context_must_hits_missing": ["Wolf"],
            "expected_route_substring_breakdown": [{"substring": "Bonogo", "matched": False}],
        },
    )
    assert ["gate violation", "missing_expected_route_hit"] in rows
    assert ["must_hit keyword", "Wolf"] in rows
    assert ["expected corpus route", "Bonogo"] in rows
