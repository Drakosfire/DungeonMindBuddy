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


_PREVIOUS_AUTHORITY_PARAGRAPH = (
    "Distinguish in-world assertions from table presentation and rhetorical language. "
    "A table handout or figurative mention does not establish a physical object, "
    "character attribute, possession, or in-world event. Preserve supported table "
    "observations as such without promoting them into world facts. Parentheses "
    "alone do not determine authority: retain explicitly narrated in-world "
    "objects and actions even when parenthetical."
)


_PRIOR_EPISTEMIC_SENTENCE = (
    "An uncertain actor attribution stays uncertain in every prose mention of that action. "
)
_EPISTEMIC_CLARIFICATION = (
    "Attribution alone does not preserve uncertainty. Keep an actor "
    "or outcome tentative whenever the source is tentative, including in "
    "descriptions framed as reports or recollections. Do not hedge a confident "
    "source statement merely because it is attributed. "
)


def _restore_prior_authority_paragraph_for_historical_fixture(prompt):
    from src.graph_memory.extraction.recap_extraction_profile import _RECAP_SOURCE_FAITHFULNESS
    paragraph = _RECAP_SOURCE_FAITHFULNESS[_RECAP_SOURCE_FAITHFULNESS.index("Distinguish in-world assertions"):]
    assert prompt.count(paragraph) <= 1
    # Historical hashes predate both bounded source-policy changes. Restore
    # exactly their old text without changing those retained historical fixtures.
    return prompt.replace(paragraph, _PREVIOUS_AUTHORITY_PARAGRAPH).replace(
        _EPISTEMIC_CLARIFICATION, _PRIOR_EPISTEMIC_SENTENCE,
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
    assert prompt_markdown(capabilities=RECAP_EXTRACTION_PROFILE.edge_pass.predicate_capabilities) in edge
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
        selected_guidance = recap_predicate_meaning_guidance(capabilities=profile.edge_pass.predicate_capabilities)
        assert selected_guidance in prompts["edge_pass.md"]
        assert all(selected_guidance not in prompt for key, prompt in prompts.items() if key != "edge_pass.md")
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
    rule = "Distinguish in-world assertions, attributed evaluations and comparisons"
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
            for contract in (
                "actions, affected objects, and outcomes explicitly in the description",
                "Retain explicit source-supported before/after relationships in descriptions",
                "without relying on paragraph, node, or list position",
                "Do not impose order on concurrent or unresolved actions",
                "Do not leave a material detail only in an evidence quote, beat summary, or relationship label",
                "Preserve source ambiguity rather than filling missing details by inference",
            ):
                assert prompt.count(contract) == int(changes), (profile.qualified_id, name)
            # All other content remains byte-identical to the independently
            # captured pre-change renderer output, including source/evidence rules.
            unchanged = prompt.replace(_NODE_DESCRIPTION_COVERAGE + "\n\n", "") if changes else prompt
            if profile.edge_pass.predicate_capabilities and name in {"thread_pass.md", "edge_pass.md"}:
                # The exact-main precedence fixture below owns these two newly
                # changed prompts; retain this older coverage baseline elsewhere.
                continue
            assert hashlib.sha256(_restore_prior_authority_paragraph_for_historical_fixture(unchanged).encode()).hexdigest() == before[name], (profile.qualified_id, name)



def test_ordered_occurrence_kinds_change_only_recap_thread_instruction() -> None:
    """Exercise real rendering and schema scope, not a claim of model compliance."""
    import hashlib
    import json
    from pathlib import Path

    from src.graph_memory.extraction.category_candidate_graph_extractor import render_encounter_job_pass_prompt
    from src.graph_memory.extraction.category_candidate_graph_schema import schema_for_pass_spec
    from src.graph_memory.extraction.extraction_profile import get_extraction_profile
    from src.graph_memory.extraction.worldbuilding_extraction_profile import WORLDBUILDING_PROFILE

    fixture = json.loads((Path(__file__).parent / "fixtures" /
                          "recap_prompt_scope_before_occurrence_kinds.json").read_text())
    for profile in (RECAP_EXTRACTION_PROFILE,
                    get_extraction_profile("recap_category_encounter_job_preview", "2.0"),
                    WORLDBUILDING_PROFILE, WORLDBUILDING_PLUMBING_PROFILE):
        prompts = render_category_pass_prompts(fixture["source_rows"], profile=profile)
        if profile.encounter_job_pass:
            prompts["encounter_job_pass.md"] = render_encounter_job_pass_prompt(
                fixture["source_rows"], nodes=[], beats=[], instruction=profile.encounter_job_pass.instruction)
        before = fixture["rendered_prompt_sha256"][profile.qualified_id]
        assert set(prompts) == set(before)
        for name, prompt in prompts.items():
            changed = profile.admitted_source_domains == frozenset({"recap"}) and name == "thread_pass.md"
            assert (hashlib.sha256(_restore_prior_authority_paragraph_for_historical_fixture(prompt).encode()).hexdigest() != before[name]) == changed
            for rule in (
                "emit an event candidate rather than only a clue for what was learned",
                "preserve uncertainty about whether an action occurred",
                "rather than duplicating it as both event and clue solely for categorization",
            ):
                assert prompt.count(rule) == int(changed), (profile.qualified_id, name)
            assert all(row["text"] in prompt for row in fixture["source_rows"])
        for spec in filter(None, [*profile.node_passes, profile.beat_pass,
                                  profile.encounter_job_pass, profile.edge_pass]):
            digest = hashlib.sha256(json.dumps(schema_for_pass_spec(spec), sort_keys=True).encode()).hexdigest()
            assert digest == fixture["schema_sha256"][profile.qualified_id][spec.pass_id]


def test_explicit_passage_transitions_change_only_recap_thread_prompt() -> None:
    """Verify exact delivery/scope, not whether a model follows the instruction."""
    import hashlib
    import json
    from pathlib import Path

    from src.graph_memory.extraction.category_candidate_graph_extractor import render_encounter_job_pass_prompt
    from src.graph_memory.extraction.category_candidate_graph_schema import schema_for_pass_spec
    from src.graph_memory.extraction.extraction_profile import get_extraction_profile
    from src.graph_memory.extraction.recap_extraction_profile import _EXPLICIT_PASSAGE_TRANSITIONS
    from src.graph_memory.extraction.worldbuilding_extraction_profile import WORLDBUILDING_PROFILE

    fixture = json.loads((Path(__file__).parent / "fixtures" /
                          "recap_prompt_scope_before_explicit_transitions.json").read_text())
    assert fixture["base"] == "1b505aa74718d28ec5443f98a59e5ea4af181478"
    for profile in (RECAP_EXTRACTION_PROFILE,
                    get_extraction_profile("recap_category_encounter_job_preview", "2.0"),
                    WORLDBUILDING_PROFILE, WORLDBUILDING_PLUMBING_PROFILE):
        prompts = render_category_pass_prompts(fixture["source_rows"], profile=profile)
        if profile.encounter_job_pass:
            prompts["encounter_job_pass.md"] = render_encounter_job_pass_prompt(
                fixture["source_rows"], nodes=[], beats=[], instruction=profile.encounter_job_pass.instruction)
        before = fixture["rendered_prompt_sha256"][profile.qualified_id]
        assert set(prompts) == set(before)
        for name, prompt in prompts.items():
            changes = profile.admitted_source_domains == frozenset({"recap"}) and name == "thread_pass.md"
            assert prompt.count(_EXPLICIT_PASSAGE_TRANSITIONS) == int(changes)
            unchanged = prompt.replace(_EXPLICIT_PASSAGE_TRANSITIONS, "") if changes else prompt
            assert hashlib.sha256(_restore_prior_authority_paragraph_for_historical_fixture(unchanged).encode()).hexdigest() == before[name], (profile.qualified_id, name)
        for spec in filter(None, [*profile.node_passes, profile.beat_pass,
                                  profile.encounter_job_pass, profile.edge_pass]):
            digest = hashlib.sha256(json.dumps(schema_for_pass_spec(spec), sort_keys=True).encode()).hexdigest()
            assert digest == fixture["schema_sha256"][profile.qualified_id][spec.pass_id]


def test_cross_passage_transition_guards_and_source_frames_reach_thread_prompt() -> None:
    """Positive and misleading cues remain source, alongside explicit guard rules."""
    rows = [
        {"source_span_ref_id": "span-completed", "line_start": 1, "line_end": 1,
         "text": "The envoy signed the accord."},
        {"source_span_ref_id": "span-transition", "line_start": 3, "line_end": 3,
         "text": "Next, the envoy entered the market."},
        {"source_span_ref_id": "span-adjacency", "line_start": 5, "line_end": 5,
         "text": "The lighthouse was green. The orchard was quiet."},
        {"source_span_ref_id": "span-future", "line_start": 7, "line_end": 7,
         "text": "She planned to depart next week; no departure was reported."},
        {"source_span_ref_id": "span-topic", "line_start": 9, "line_end": 9,
         "text": "Next topic: the two guards. He waited beside the next door."},
        {"source_span_ref_id": "span-flashback", "line_start": 11, "line_end": 11,
         "text": "The story next returns to last winter; no time passes at the gate."},
        {"source_span_ref_id": "span-ambiguous", "line_start": 13, "line_end": 13,
         "text": "Two couriers delivered different parcels. After that one left; which was unclear."},
        {"source_span_ref_id": "span-unordered", "line_start": 15, "line_end": 15,
         "text": "Both the repair and the inspection preceded departure; their mutual order is unknown."},
        {"source_span_ref_id": "span-concurrent", "line_start": 17, "line_end": 17,
         "text": "Meanwhile the courier waited; the other courier's timing was unknown."},
    ]
    prompt = render_category_pass_prompts(rows, profile=RECAP_EXTRACTION_PROFILE)["thread_pass.md"]
    for row in rows:
        assert row["text"] in prompt
        assert row["source_span_ref_id"] in prompt
    for rule in (
        "Resolve references to earlier and later occurrences using the surrounding source context",
        "state the directed before/after relationship in an occurrence description with both occurrences named",
        "attach evidence_refs covering the earlier occurrence, the later occurrence, and the source connective",
        "One paragraph is sufficient when it supplies all three",
        "otherwise cite each needed paragraph on that claim itself",
        "check every ordering clause in its description against its own references",
        "evidence on another node cannot close a missing witness",
        "Do not derive time from passage adjacency alone",
        "the antecedent is ambiguous",
        "the transition changes topic rather than event time",
        "an action remains merely proposed",
        "turn narrative presentation or a flashback into fictional elapsed time",
        "Preserve concurrency, future modality and unresolved order",
    ):
        assert prompt.count(rule) == 1


def test_direct_order_changes_only_opted_in_thread_edge_prompts_and_edge_schema():
    import hashlib
    import json
    from pathlib import Path
    from src.graph_memory.extraction.category_candidate_graph_schema import schema_for_pass_spec
    from src.graph_memory.extraction.category_candidate_graph_extractor import render_encounter_job_pass_prompt
    from src.graph_memory.extraction.extraction_profile import get_extraction_profile
    from src.graph_memory.extraction.worldbuilding_extraction_profile import WORLDBUILDING_PROFILE
    from src.graph_memory.extraction.recap_extraction_profile import (
        _NODE_DESCRIPTION_COVERAGE, _SOURCE_ORDER_OCCURRENCES, _SOURCE_ORDER_EDGES,
    )
    fixture = json.loads((Path(__file__).parent / "fixtures" / "recap_prompt_scope_before_direct_precedence.json").read_text())
    for profile in (RECAP_EXTRACTION_PROFILE,
                    get_extraction_profile("recap_category_encounter_job_preview", "2.0"),
                    WORLDBUILDING_PROFILE, WORLDBUILDING_PLUMBING_PROFILE):
        prompts = render_category_pass_prompts(fixture["source_rows"], profile=profile)
        if profile.encounter_job_pass:
            prompts["encounter_job_pass.md"] = render_encounter_job_pass_prompt(
                fixture["source_rows"], nodes=[], beats=[], instruction=profile.encounter_job_pass.instruction)
        opted_in = bool(profile.edge_pass.predicate_capabilities)
        before = fixture["rendered_prompt_sha256"][profile.qualified_id]
        assert set(prompts) == set(before)
        for name, prompt in prompts.items():
            changed = opted_in and name in {"thread_pass.md", "edge_pass.md"}
            # This fixture predates the separately verified description refinement.
            # Remove only that appended delta; preserve the original coverage rule
            # and every ordering/source/schema instruction under comparison.
            refinement = _NODE_DESCRIPTION_COVERAGE.partition(
                "source-faithfulness requirements."
            )[2]
            assert refinement
            ordering_prompt = prompt.replace(refinement, "")
            assert (hashlib.sha256(_restore_prior_authority_paragraph_for_historical_fixture(ordering_prompt).encode()).hexdigest() != before[name]) == changed
            assert prompt.count(_SOURCE_ORDER_OCCURRENCES) == int(opted_in and name == "thread_pass.md")
            assert prompt.count(_SOURCE_ORDER_EDGES) == int(opted_in and name == "edge_pass.md")
            assert ("`precedes`" in prompt) == (opted_in and name == "edge_pass.md")
        specs = [*profile.node_passes, profile.beat_pass, profile.encounter_job_pass, profile.edge_pass]
        for spec in filter(None, specs):
            digest = hashlib.sha256(json.dumps(schema_for_pass_spec(spec), sort_keys=True).encode()).hexdigest()
            assert (digest != fixture["schema_sha256"][profile.qualified_id][spec.pass_id]) == (opted_in and spec.kind == "edge")


def test_transition_antecedent_clause_replaces_parent_without_other_contract_changes() -> None:
    """Exact parent restoration proves delivery/scope, not semantic compliance."""
    import hashlib
    import json
    from pathlib import Path
    from src.graph_memory.extraction.category_candidate_graph_extractor import render_encounter_job_pass_prompt
    from src.graph_memory.extraction.category_candidate_graph_schema import schema_for_pass_spec
    from src.graph_memory.extraction.extraction_profile import get_extraction_profile
    from src.graph_memory.extraction.recap_extraction_profile import _EXPLICIT_PASSAGE_TRANSITIONS
    from src.graph_memory.extraction.worldbuilding_extraction_profile import WORLDBUILDING_PROFILE

    fixture = json.loads((Path(__file__).parent / "fixtures" /
                          "recap_prompt_scope_before_transition_antecedents.json").read_text())
    assert fixture["base"] == "9d089b0f25bffdd4f38191bd9b1271231ded7a26"
    for profile in (RECAP_EXTRACTION_PROFILE,
                    get_extraction_profile("recap_category_encounter_job_preview", "2.0"),
                    WORLDBUILDING_PROFILE, WORLDBUILDING_PLUMBING_PROFILE):
        prompts = render_category_pass_prompts(fixture["source_rows"], profile=profile)
        if profile.encounter_job_pass:
            prompts["encounter_job_pass.md"] = render_encounter_job_pass_prompt(
                fixture["source_rows"], nodes=[], beats=[], instruction=profile.encounter_job_pass.instruction)
        before = fixture["rendered_prompt_sha256"][profile.qualified_id]
        assert set(prompts) == set(before)
        for name, prompt in prompts.items():
            changed = profile.admitted_source_domains == frozenset({"recap"}) and name == "thread_pass.md"
            assert prompt.count(_EXPLICIT_PASSAGE_TRANSITIONS) == int(changed)
            assert fixture["previous_clause"] not in prompt
            restored = prompt.replace(_EXPLICIT_PASSAGE_TRANSITIONS, fixture["previous_clause"]) if changed else prompt
            assert hashlib.sha256(_restore_prior_authority_paragraph_for_historical_fixture(restored).encode()).hexdigest() == before[name]
            assert (hashlib.sha256(_restore_prior_authority_paragraph_for_historical_fixture(prompt).encode()).hexdigest() != before[name]) == changed
            for row in fixture["source_rows"]:
                assert row["text"] in prompt and row["source_span_ref_id"] in prompt
        for spec in filter(None, [*profile.node_passes, profile.beat_pass,
                                  profile.encounter_job_pass, profile.edge_pass]):
            digest = hashlib.sha256(json.dumps(schema_for_pass_spec(spec), sort_keys=True).encode()).hexdigest()
            assert digest == fixture["schema_sha256"][profile.qualified_id][spec.pass_id]


def test_attributed_observations_and_unresolved_presentation_reach_recap_prompts_only():
    """Source/policy delivery is not a claim of semantic model compliance."""
    from src.graph_memory.extraction.extraction_profile import get_extraction_profile
    from src.graph_memory.extraction.worldbuilding_extraction_profile import WORLDBUILDING_PROFILE
    from src.graph_memory.extraction.source_sentence_evidence import compile_source_sentence_packet
    texts = [
        "The narrator compared the envoy to a fox.",
        "The captain boasted that the scout was invincible.",
        "Could the envoy fly over the gate?",
        "(The GM handed the players a printed chart.)",
        "(The scout carried a brass chart in her satchel.)",
        "(A chart card appeared, with no explanation of its presentation.)",
        "The table prop and the scout's chart were separately described.",
    ]
    source = "\n".join(texts)
    rows = [{"source_span_ref_id": f"span:{i}", "line_start": i, "line_end": i, "text": text}
            for i, text in enumerate(texts, 1)]
    packet = compile_source_sentence_packet(source, rows)
    for profile in (RECAP_EXTRACTION_PROFILE, get_extraction_profile("recap_category_encounter_job_preview", "2.0")):
        prompts = render_category_pass_prompts(rows, profile=profile, node_source_packet=packet)
        for prompt in prompts.values():
            assert "as attributed observations" in prompt
            assert "not objective properties" in prompt
            assert "A rhetorical question is not its answer" in prompt
            assert "preserve that uncertainty rather than forcing a category" in prompt
            assert "Do not invent a world object" in prompt
            assert all(text in prompt for text in texts)
        object_prompt = prompts["object_pass.md"]
        assert "ignored_items" in object_prompt and "deferred_items" in object_prompt
    for profile in (WORLDBUILDING_PROFILE, WORLDBUILDING_PLUMBING_PROFILE):
        prompts = render_category_pass_prompts(rows, profile=profile)
        assert all("as attributed observations" not in p for p in prompts.values())


def test_policy_rewrite_changes_only_shared_authority_paragraph(monkeypatch):
    from dataclasses import replace
    from src.graph_memory.extraction import recap_extraction_profile as module
    from src.graph_memory.extraction.category_candidate_graph_schema import schema_for_pass_spec
    old_paragraph = _PREVIOUS_AUTHORITY_PARAGRAPH
    current = module._RECAP_SOURCE_FAITHFULNESS
    start = current.index("Distinguish in-world assertions")
    old_policy = current[:start] + old_paragraph
    monkeypatch.setattr(module, "_RECAP_SOURCE_FAITHFULNESS", old_policy)
    prior = module._build_recap_profile(profile_id=module.RECAP_PROFILE_ID,
        profile_version=module.RECAP_PROFILE_VERSION, enable_encounter_job_pass=False,
        enable_encounter_job_edge_guidance=False, enable_dynamic_node_vocabulary_packet=False)
    current_specs = [*RECAP_EXTRACTION_PROFILE.node_passes, RECAP_EXTRACTION_PROFILE.beat_pass, RECAP_EXTRACTION_PROFILE.edge_pass]
    prior_specs = [*prior.node_passes, prior.beat_pass, prior.edge_pass]
    for new, old in zip(current_specs, prior_specs):
        assert new.instruction.count(current) == 1
        assert replace(new, instruction=new.instruction.replace(current, old_policy)) == old
        assert schema_for_pass_spec(new) == schema_for_pass_spec(old)


def test_epistemic_policy_reaches_rendered_recaps_without_changing_source_or_schema():
    from dataclasses import replace
    from src.graph_memory.extraction.category_candidate_graph_schema import category_pass_text_format_for_spec
    from src.graph_memory.extraction.extraction_profile import get_extraction_profile

    # Contrast inputs are source distinctions, not a claim that a fake model
    # passed semantic evaluation. Actual model compliance needs fresh captures.
    contrasts = [
        ('Ari recalled: I think Bo opened the hatch.', 'tentative actor'),
        ('The witness reported that Bo opened the hatch.', 'confident attributed actor'),
        ('The fragments might be copper.', 'tentative outcome'),
        ('Ari remembers the fragments were copper.', 'confident recollected outcome'),
        ('Someone apparently held the rope; who did so is unclear.', 'unresolved actor'),
        ('Perhaps Bo held the rope. Ari definitely closed the hatch.', 'local qualifier scope'),
    ]
    rows = [{'source_span_ref_id': f'epistemic-{i}', 'line_start': i + 1,
             'line_end': i + 1, 'text': text} for i, (text, _) in enumerate(contrasts)]
    for profile in (RECAP_EXTRACTION_PROFILE, get_extraction_profile('recap_category_encounter_job_preview', '2.0')):
        def prior(spec):
            return replace(spec, instruction=spec.instruction.replace(_EPISTEMIC_CLARIFICATION, _PRIOR_EPISTEMIC_SENTENCE)) if spec else None
        predecessor = replace(profile, node_passes=tuple(prior(spec) for spec in profile.node_passes),
                              beat_pass=prior(profile.beat_pass), edge_pass=prior(profile.edge_pass),
                              encounter_job_pass=prior(profile.encounter_job_pass))
        current_prompts = render_category_pass_prompts(rows, profile=profile)
        prior_prompts = render_category_pass_prompts(rows, profile=predecessor)
        assert current_prompts.keys() == prior_prompts.keys()
        for name, prompt in current_prompts.items():
            assert prompt.count(_EPISTEMIC_CLARIFICATION) == 1, name
            assert prompt.replace(_EPISTEMIC_CLARIFICATION, _PRIOR_EPISTEMIC_SENTENCE) == prior_prompts[name]
            for text, distinction in contrasts:
                assert text in prompt, distinction
        current_specs = [*profile.node_passes, profile.beat_pass, profile.edge_pass, profile.encounter_job_pass]
        previous_specs = [*predecessor.node_passes, predecessor.beat_pass, predecessor.edge_pass, predecessor.encounter_job_pass]
        for current, previous in zip(current_specs, previous_specs, strict=True):
            if current:
                assert category_pass_text_format_for_spec(current) == category_pass_text_format_for_spec(previous)
    assert all(_EPISTEMIC_CLARIFICATION not in prompt for prompt in
               render_category_pass_prompts(rows, profile=WORLDBUILDING_PLUMBING_PROFILE).values())
