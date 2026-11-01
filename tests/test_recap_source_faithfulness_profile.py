from __future__ import annotations

from src.graph_memory.extraction.category_candidate_graph_extractor import (
    render_category_pass_prompts,
)
from src.graph_memory.extraction.recap_extraction_profile import (
    RECAP_EXTRACTION_PROFILE,
)
from src.graph_memory.extraction.worldbuilding_plumbing_profile import (
    WORLDBUILDING_PLUMBING_PROFILE,
)


SYNTHETIC_SOURCE_ROWS = [
    {
        "source_span_ref_id": "span-intent",
        "line_start": 1,
        "line_end": 1,
        "text": (
            "Ephanna planned to use Eldritch Blast to rescue the children, "
            "but she did not cast it."
        ),
    },
    {
        "source_span_ref_id": "span-names",
        "line_start": 2,
        "line_end": 2,
        "text": "The team visited Lysandro's house while Lysandra spoke at the gate.",
    },
    {
        "source_span_ref_id": "span-group",
        "line_start": 3,
        "line_end": 3,
        "text": "The children gathered outside town and asked the guards for help.",
    },
    {
        "source_span_ref_id": "span-places",
        "line_start": 4,
        "line_end": 4,
        "text": "Fellinor's house and warehouse stand at Edge.",
    },
    {
        "source_span_ref_id": "span-plural",
        "line_start": 5,
        "line_end": 5,
        "text": "The monsters attacked the town; guards drove some attackers away.",
    },
]

# These are expected source distinctions, not assertions about model output.
SYNTHETIC_SOURCE_GOLD = {
    "intent": {
        "span": "span-intent",
        "pass": "beat_pass.md",
        "rule": "An intended action is not a completed action",
        "source_witnesses": ("planned", "did not cast it"),
        "distinction": "planned rescue is not a completed cast",
    },
    "identity": {
        "span": "span-names",
        "pass": "actor_pass.md",
        "rule": "Keep similarly named people and creatures as separate candidates",
        "source_witnesses": ("Lysandro's house", "Lysandra spoke"),
        "distinction": "Lysandro and Lysandra remain distinct without source identity evidence",
    },
    "population": {
        "span": "span-group",
        "pass": "collective_pass.md",
        "rule": "Include source-mentioned informal populations",
        "source_witnesses": ("The children gathered", "asked the guards for help"),
        "distinction": "children remain available as a meaningful source-mentioned group",
    },
    "places": {
        "span": "span-places",
        "pass": "location_pass.md",
        "rule": "extract them separately instead of combining them",
        "source_witnesses": ("house and warehouse", "at Edge"),
        "distinction": "house and warehouse are not collapsed into one place label",
    },
    "referent": {
        "span": "span-plural",
        "pass": "edge_pass.md",
        "rule": "Keep broad plural references broad",
        "source_witnesses": ("The monsters attacked", "some attackers"),
        "distinction": "the broad monsters/attackers are not silently mapped to a narrower subgroup",
    },
}




def test_recap_prompt_builder_carries_source_faithfulness_by_pass() -> None:
    prompts = render_category_pass_prompts(
        SYNTHETIC_SOURCE_ROWS,
        profile=RECAP_EXTRACTION_PROFILE,
    )

    assert {case["pass"] for case in SYNTHETIC_SOURCE_GOLD.values()} <= prompts.keys()

    rows_by_span = {row["source_span_ref_id"]: row for row in SYNTHETIC_SOURCE_ROWS}
    for case in SYNTHETIC_SOURCE_GOLD.values():
        prompt = prompts[case["pass"]]
        source_text = rows_by_span[case["span"]]["text"]
        assert case["rule"] in prompt, case["pass"]
        assert source_text in prompt, case["span"]
        assert all(
            witness in source_text for witness in case["source_witnesses"]
        ), case["distinction"]

    assert "topic proximity" in prompts["actor_pass.md"]
    assert "attribution and uncertainty" in prompts["beat_pass.md"]
    assert "relationship itself" in prompts["edge_pass.md"]

    # Exercise the prompt-construction boundary with all five synthetic cases,
    # and retain the existing evidence contract on claim-bearing passes.
    for source in SYNTHETIC_SOURCE_ROWS:
        assert source["text"] in prompts["beat_pass.md"]
        assert source["text"] in prompts["edge_pass.md"]
    assert "anchor_quotes" in prompts["beat_pass.md"]
    assert "anchor_quotes" in prompts["edge_pass.md"]
    assert "Return JSON with key `observation_edges`" in prompts["edge_pass.md"]


def test_recap_only_guidance_does_not_leak_into_worldbuilding_profile() -> None:
    prompts = render_category_pass_prompts(
        SYNTHETIC_SOURCE_ROWS,
        profile=WORLDBUILDING_PLUMBING_PROFILE,
    )

    compiled = "\n".join(prompts.values())
    assert "An intended action is not a completed action" not in compiled
    assert "Keep broad plural references broad" not in compiled
