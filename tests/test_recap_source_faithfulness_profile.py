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


def test_collective_scene_scope_guidance_reaches_only_recap_collective_prompt() -> None:
    """Exercise prompt ownership; actual model scope preservation is separate."""
    from src.graph_memory.extraction.extraction_profile import get_extraction_profile
    from src.graph_memory.extraction.worldbuilding_extraction_profile import (
        WORLDBUILDING_PROFILE,
    )

    rows = [
        {
            "source_span_ref_id": "span-observatory",
            "line_start": 1,
            "line_end": 1,
            "text": "Keepers at the observatory greeted the visitors.",
        },
        {
            "source_span_ref_id": "span-quarry",
            "line_start": 2,
            "line_end": 2,
            "text": "Elsewhere, keepers at a quarry restrained a messenger.",
        },
        {
            "source_span_ref_id": "span-continuity",
            "line_start": 3,
            "line_end": 3,
            "text": "The same observatory keepers later guided the visitors across the terrace.",
        },
    ]
    rule = "Repeated role labels in different scenes do not establish one continuing group"
    for profile in (
        RECAP_EXTRACTION_PROFILE,
        get_extraction_profile("recap_category_encounter_job_preview", "2.0"),
    ):
        prompts = render_category_pass_prompts(rows, profile=profile)
        collective = prompts["collective_pass.md"]
        assert collective.count(rule) == 1
        assert "a specifically scoped group" in collective
        assert "Preserve continuity when the source supports" in collective
        assert all(row["text"] in collective for row in rows)
        assert "anchor_quotes" in collective
        assert all(rule not in value for key, value in prompts.items()
                   if key != "collective_pass.md")
    for profile in (WORLDBUILDING_PROFILE, WORLDBUILDING_PLUMBING_PROFILE):
        prompts = render_category_pass_prompts(rows, profile=profile)
        assert all(rule not in value for value in prompts.values())


def test_source_form_authority_reaches_every_recap_claim_bearing_pass() -> None:
    """Verify instruction delivery; source authority in model output is assessed separately."""
    from src.graph_memory.extraction.category_candidate_graph_extractor import (
        render_encounter_job_pass_prompt,
    )
    from src.graph_memory.extraction.extraction_profile import get_extraction_profile
    from src.graph_memory.extraction.worldbuilding_extraction_profile import (
        WORLDBUILDING_PROFILE,
    )

    rows = [
        {
            "source_span_ref_id": "span-handout",
            "line_start": 1,
            "line_end": 1,
            "text": "(The GM gave the players a printed constellation chart.)",
        },
        {
            "source_span_ref_id": "span-rhetoric",
            "line_start": 2,
            "line_end": 2,
            "text": "Can the envoy pull another victory out of her hat?",
        },
        {
            "source_span_ref_id": "span-world-object",
            "line_start": 3,
            "line_end": 3,
            "text": "(The envoy put a brass compass into her satchel.)",
        },
    ]
    rule = "Distinguish in-world assertions from table presentation and rhetorical language"
    for profile in (
        RECAP_EXTRACTION_PROFILE,
        get_extraction_profile("recap_category_encounter_job_preview", "2.0"),
    ):
        prompts = render_category_pass_prompts(rows, profile=profile)
        if profile.encounter_job_pass is not None:
            prompts["encounter_job_pass.md"] = render_encounter_job_pass_prompt(
                rows, nodes=[], beats=[], instruction=profile.encounter_job_pass.instruction,
            )
        for name, prompt in prompts.items():
            assert prompt.count(rule) == 1, name
            assert "does not establish a physical object" in prompt
            assert "Preserve supported table observations as such" in prompt
            assert "Parentheses alone do not determine authority" in prompt
            assert all(row["text"] in prompt for row in rows)
            assert "anchor_quotes" in prompt
    for profile in (WORLDBUILDING_PROFILE, WORLDBUILDING_PLUMBING_PROFILE):
        prompts = render_category_pass_prompts(rows, profile=profile)
        assert all(rule not in prompt for prompt in prompts.values())


def test_node_description_coverage_changes_only_existing_recap_node_prompts() -> None:
    """Check actual prompt delivery/scope; this does not prove model compliance."""
    import hashlib
    import json
    from pathlib import Path

    from src.graph_memory.extraction.category_candidate_graph_extractor import (
        render_encounter_job_pass_prompt,
    )
    from src.graph_memory.extraction.extraction_profile import get_extraction_profile
    from src.graph_memory.extraction.recap_extraction_profile import (
        _NODE_DESCRIPTION_COVERAGE,
    )
    from src.graph_memory.extraction.worldbuilding_extraction_profile import (
        WORLDBUILDING_PROFILE,
    )

    fixture = json.loads((Path(__file__).parent / "fixtures" /
                          "recap_prompt_scope_before_description_coverage.json").read_text())
    eligible = {"actor_pass.md", "location_pass.md", "collective_pass.md",
                "object_pass.md", "thread_pass.md"}
    for profile in (
        RECAP_EXTRACTION_PROFILE,
        get_extraction_profile("recap_category_encounter_job_preview", "2.0"),
        WORLDBUILDING_PROFILE,
        WORLDBUILDING_PLUMBING_PROFILE,
    ):
        prompts = render_category_pass_prompts(fixture["source_rows"], profile=profile)
        if profile.encounter_job_pass is not None:
            prompts["encounter_job_pass.md"] = render_encounter_job_pass_prompt(
                fixture["source_rows"], nodes=[], beats=[],
                instruction=profile.encounter_job_pass.instruction,
            )
        before = fixture["rendered_prompt_sha256"][profile.qualified_id]
        assert set(prompts) == set(before)
        for name, prompt in prompts.items():
            changes = profile.admitted_source_domains == frozenset({"recap"}) and name in eligible
            assert prompt.count(_NODE_DESCRIPTION_COVERAGE) == int(changes), (profile.qualified_id, name)
            # All other content remains byte-identical to the independently
            # captured pre-change renderer output, including source/evidence rules.
            unchanged = prompt.replace(_NODE_DESCRIPTION_COVERAGE + "\n\n", "") if changes else prompt
            assert hashlib.sha256(unchanged.encode()).hexdigest() == before[name], (profile.qualified_id, name)


def test_description_chronology_changes_only_existing_recap_node_prompts() -> None:
    """Verify actual instruction delivery/scope, not model chronology compliance."""
    import hashlib
    import json
    from pathlib import Path

    from src.graph_memory.extraction.category_candidate_graph_extractor import (
        render_encounter_job_pass_prompt,
    )
    from src.graph_memory.extraction.extraction_profile import get_extraction_profile
    from src.graph_memory.extraction.recap_extraction_profile import (
        _NODE_DESCRIPTION_CHRONOLOGY,
    )
    from src.graph_memory.extraction.worldbuilding_extraction_profile import (
        WORLDBUILDING_PROFILE,
    )

    fixture = json.loads((Path(__file__).parent / "fixtures" /
                          "recap_prompt_scope_before_description_chronology.json").read_text())
    eligible = {"actor_pass.md", "location_pass.md", "collective_pass.md",
                "object_pass.md", "thread_pass.md"}
    for profile in (
        RECAP_EXTRACTION_PROFILE,
        get_extraction_profile("recap_category_encounter_job_preview", "2.0"),
        WORLDBUILDING_PROFILE,
        WORLDBUILDING_PLUMBING_PROFILE,
    ):
        prompts = render_category_pass_prompts(fixture["source_rows"], profile=profile)
        if profile.encounter_job_pass is not None:
            prompts["encounter_job_pass.md"] = render_encounter_job_pass_prompt(
                fixture["source_rows"], nodes=[], beats=[],
                instruction=profile.encounter_job_pass.instruction,
            )
        before = fixture["rendered_prompt_sha256"][profile.qualified_id]
        assert set(prompts) == set(before)
        for name, prompt in prompts.items():
            changes = profile.admitted_source_domains == frozenset({"recap"}) and name in eligible
            assert prompt.count(_NODE_DESCRIPTION_CHRONOLOGY) == int(changes), (profile.qualified_id, name)
            assert all(row["text"] in prompt for row in fixture["source_rows"])
            # Removing exactly the new paragraph must recover the unmodified
            # base, including existing coverage, time, scope and evidence rules.
            unchanged = prompt.replace(" " + _NODE_DESCRIPTION_CHRONOLOGY, "", 1) if changes else prompt
            assert hashlib.sha256(unchanged.encode()).hexdigest() == before[name], (profile.qualified_id, name)
