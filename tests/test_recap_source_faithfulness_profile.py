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


def test_recap_edge_prompt_requires_full_directed_tuple_support() -> None:
    prompts = render_category_pass_prompts(
        SYNTHETIC_SOURCE_ROWS, profile=RECAP_EXTRACTION_PROFILE,
    )
    edge = prompts["edge_pass.md"]
    assert "from_node_id → relationship_type → to_node_id" in edge
    assert "direction" in edge
    assert "label does not qualify" in edge
    assert "no catalog predicate faithfully expresses" in edge
    assert "Keep broad plural references broad" in edge
    assert edge.count("from_node_id → relationship_type → to_node_id") == 1


def test_recap_edge_contract_preserves_catalog_schema_and_profile_boundary() -> None:
    from src.graph_memory.predicate_catalog import prompt_markdown

    prompts = render_category_pass_prompts(
        SYNTHETIC_SOURCE_ROWS, profile=RECAP_EXTRACTION_PROFILE,
    )
    edge = prompts["edge_pass.md"]
    assert prompt_markdown() in edge
    assert "Use exact `node_id` values" in edge
    assert "Return JSON with key `observation_edges`" in edge
    for row in SYNTHETIC_SOURCE_ROWS:
        assert row["text"] in edge
    worldbuilding = render_category_pass_prompts(
        SYNTHETIC_SOURCE_ROWS, profile=WORLDBUILDING_PLUMBING_PROFILE,
    )["edge_pass.md"]
    assert "from_node_id → relationship_type → to_node_id" not in worldbuilding
    assert "label does not qualify" not in worldbuilding
    assert "no catalog predicate faithfully expresses" not in worldbuilding


def test_common_faithfulness_reaches_every_ordinary_recap_pass_once() -> None:
    prompts = render_category_pass_prompts(
        SYNTHETIC_SOURCE_ROWS, profile=RECAP_EXTRACTION_PROFILE,
    )
    common = "Preserve the source's modality, attribution, time, and scope."
    for name, prompt in prompts.items():
        assert prompt.count(common) == 1, name
        assert "anchor_quotes" in prompt, name
        for row in SYNTHETIC_SOURCE_ROWS:
            assert row["text"] in prompt, name
    assert "Extract notable items" in prompts["object_pass.md"]
    assert "Extract mysteries, clues" in prompts["thread_pass.md"]
    worldbuilding = render_category_pass_prompts(
        SYNTHETIC_SOURCE_ROWS, profile=WORLDBUILDING_PLUMBING_PROFILE,
    )
    assert all(common not in prompt for prompt in worldbuilding.values())


def test_repeated_prose_claims_receive_field_local_qualification_instructions() -> None:
    """Prove prompt delivery, not model compliance with source distinctions."""
    from src.graph_memory.extraction.extraction_profile import get_extraction_profile
    from src.graph_memory.extraction.category_candidate_graph_extractor import (
        render_encounter_job_pass_prompt,
    )

    rows = [
        {
            "source_span_ref_id": "span-belief",
            "line_start": 1,
            "line_end": 1,
            "text": "Nara said the lantern was cursed. It hung in the guild hall.",
        },
        {
            "source_span_ref_id": "span-uncertain-actor",
            "line_start": 2,
            "line_end": 2,
            "text": "Bryn may have calmed the mule's owner; the narrator was unsure.",
        },
    ]
    rule = "Keep attribution and uncertainty in each prose assertion"
    profiles = (
        RECAP_EXTRACTION_PROFILE,
        get_extraction_profile("recap_category_encounter_job_preview", "2.0"),
    )
    for profile in profiles:
        prompts = render_category_pass_prompts(rows, profile=profile)
        if profile.encounter_job_pass is not None:
            # This pass is rendered separately in the ordinary extraction loop.
            prompts["encounter_job_pass.md"] = render_encounter_job_pass_prompt(
                rows, nodes=[], beats=[], instruction=profile.encounter_job_pass.instruction,
            )
        for name, prompt in prompts.items():
            assert prompt.count(rule) == 1, (profile.qualified_id, name)
            assert "adjectives" in prompt
            assert "another entity's description" in prompt
            assert "an evidence quote or another node" in prompt
            for row in rows:
                assert row["text"] in prompt
            assert "anchor_quotes" in prompt
        # Qualified wording cannot rescue a stronger edge predicate.
        assert "a promise or intention is not a completed action" in prompts["edge_pass.md"]
        assert "If no catalog predicate" in prompts["edge_pass.md"]

    worldbuilding = render_category_pass_prompts(rows, profile=WORLDBUILDING_PLUMBING_PROFILE)
    assert all(rule not in prompt for prompt in worldbuilding.values())


def test_meanings_reach_only_recap_edge_prompt():
    from src.graph_memory.predicate_catalog import recap_predicate_meaning_guidance
    from src.graph_memory.extraction.worldbuilding_extraction_profile import WORLDBUILDING_PROFILE
    from src.graph_memory.extraction.extraction_profile import get_extraction_profile

    guidance = recap_predicate_meaning_guidance()
    for profile in (RECAP_EXTRACTION_PROFILE, get_extraction_profile(
        "recap_category_encounter_job_preview", "2.0"
    )):
        prompts = render_category_pass_prompts(SYNTHETIC_SOURCE_ROWS, profile=profile)
        assert guidance in prompts["edge_pass.md"]
        assert all(guidance not in prompt for key, prompt in prompts.items() if key != "edge_pass.md")
    for profile in (WORLDBUILDING_PROFILE, WORLDBUILDING_PLUMBING_PROFILE):
        prompts = render_category_pass_prompts(SYNTHETIC_SOURCE_ROWS, profile=profile)
        assert all(guidance not in prompt for prompt in prompts.values())
