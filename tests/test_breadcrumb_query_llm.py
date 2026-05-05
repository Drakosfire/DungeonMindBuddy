from __future__ import annotations

from evals.sentence_routing_retrieval_falsification import breadcrumb_query_llm as bql


def test_query_llm_system_prompt_prefers_coverage_over_brevity() -> None:
    sys = bql._SYSTEM
    assert "Prefer coverage over brevity" in sys
    assert "named entities" in sys
    assert "locations" in sys
    assert "numbers" in sys
    assert "6–14 sentences" in sys


def test_format_synthesis_user_message_includes_question_and_hit_context() -> None:
    msg = bql.format_synthesis_user_message(question="Who fought?", hit_context="Unit A text.")
    assert msg.startswith("Question:\nWho fought?")
    assert "### Retrieved excerpts and routes" in msg
    assert "Unit A text." in msg
