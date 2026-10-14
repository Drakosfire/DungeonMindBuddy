import pytest

from src.graph_memory.extraction.category_candidate_graph_extractor import (
    _empty_party_context,
    _normalize_evidence_refs,
    _source_packet_md,
    render_category_pass_prompts,
)
from src.graph_memory.extraction.worldbuilding_gazetteer_profile import (
    GAZETTEER_PROFILE,
)


@pytest.mark.parametrize(
    "unit,expected",
    [
        ("span:canonical", "### span:canonical / lines 4-5"),
        ("unit:distinct", "### span:canonical / unit:distinct / lines 4-5"),
        (None, "### span:canonical / lines 4-5"),
    ],
)
def test_source_packet_retains_canonical_evidence_without_duplicate_unit(
    unit, expected
):
    row = {
        "source_span_ref_id": "span:canonical",
        "line_start": 4,
        "line_end": 5,
        "text": "Exact source\n  with indentation.",
    }
    if unit is not None:
        row["source_unit_id"] = unit
    packet = _source_packet_md([row])
    assert packet == expected + "\n\n```text\nExact source\n  with indentation.\n```"
    prompts = render_category_pass_prompts(
        [row], party_ctx=_empty_party_context("world"), profile=GAZETTEER_PROFILE
    )
    for prompt in prompts.values():
        assert packet in prompt
    refs = _normalize_evidence_refs(
        [{"source_span_ref_id": "span:canonical", "anchor_quotes": ["Exact source"]}],
        allowed_span_refs={"span:canonical"},
    )
    assert refs[0]["source_span_ref_id"] == "span:canonical"
    assert refs[0]["anchor_quotes"] == ["Exact source"]
