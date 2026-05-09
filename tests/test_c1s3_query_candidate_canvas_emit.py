from __future__ import annotations

from pathlib import Path

from evals.sentence_routing_retrieval_falsification.c1s3_query_candidate_canvas_emit import (
    BLOCK_BEGIN,
    BLOCK_END,
    refresh_c1s3_candidate_canvases,
)


def test_c1s3_candidate_canvas_refresh(tmp_path: Path) -> None:
    canvas = tmp_path / "c.canvas.tsx"
    canvas.write_text(
        f"head\n{BLOCK_BEGIN}\nconst x = {{}} as const;\n{BLOCK_END}\ntail\n",
        encoding="utf-8",
    )
    doc = {
        "schema": "dmb_breadcrumb_query_candidates_v1",
        "generated_at_utc": "t",
        "source_breadcrumb_path": "p",
        "campaign_id": "longmont-c1",
        "session_number": 3,
        "candidates": [
            {
                "candidate_id": "c1s3_cand_x",
                "category": "core_recall",
                "question": "Q?",
                "expected_answer_draft": "A.",
                "must_hit_tokens_draft": ["a"],
                "supporting_unit_ids": ["u-L0008-01"],
                "supporting_route_substrings": ["Campaign 1/NPCs/pippa"],
                "supporting_evidence_snippets": ["snip"],
                "notes": "n",
                "review_status": "pending",
            }
        ],
    }
    summary = refresh_c1s3_candidate_canvases(candidates_doc=doc, canvas_paths=[canvas])
    assert not summary["errors"]
    assert summary["updated"]
    text = canvas.read_text(encoding="utf-8")
    assert "c1s3CandidateCanvasGenerated" in text
    assert "c1s3_cand_x" in text
