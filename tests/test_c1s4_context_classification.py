from evals.c1s4_preplanning_vertical_slice.context_classification import (
    is_allowed_retrieval_corpus_path,
    infer_planner_lane,
    is_admittable_planner_evidence,
    is_navigation_only_context,
    is_context_compatible_with_required_lane,
)


def test_retrieval_corpus_excludes_eval_docs_gold_canvas_and_artifacts():
    denied = [
        'evals/c1s4_preplanning_vertical_slice/analysis/pr49_corpus_artifact_report.md',
        'evals/c1s4_preplanning_vertical_slice/artifacts/pr53/pr53_packet_quality_summary.json',
        'Docs/Plans/some_plan.md',
        'evals/c1s4_preplanning_vertical_slice/gold/c1s4_expected_context_gold.json',
        'evals/c1s4_preplanning_vertical_slice/canvas_templates/c1s4_expected_context_benchmark.canvas.tsx',
    ]
    assert all(not is_allowed_retrieval_corpus_path(p) for p in denied)
    assert is_allowed_retrieval_corpus_path('corpus/eldyrwild-markdown/Longmont Campaign/Campaign 1/Locations/stone_bridge/README.md')
    assert is_allowed_retrieval_corpus_path(
        "Longmont Campaign/Campaign 2/Session Recaps/_normalized/Session 21 - Drake Nest Mirathorn Call.md"
    )
    assert not is_allowed_retrieval_corpus_path("README.md")
    assert not is_allowed_retrieval_corpus_path(".cursor/rules/corpus-layout-conventions.mdc")
    assert not is_allowed_retrieval_corpus_path("scripts/dev_notes.md")
    assert not is_allowed_retrieval_corpus_path("")


def test_location_hubs_classify_as_location_worldbuilding():
    item = {'source_path': 'corpus/eldyrwild-markdown/Longmont Campaign/Campaign 1/Locations/stone_bridge/README.md', 'subject_doc_kind': 'hub_index'}
    assert infer_planner_lane(item) == 'location_worldbuilding'


def test_npc_hubs_classify_as_character_party_behavior():
    item = {'source_path': 'corpus/eldyrwild-markdown/Longmont Campaign/Campaign 1/NPCs/pippa/README.md', 'subject_doc_kind': 'hub_index'}
    assert infer_planner_lane(item) == 'character_party_behavior'


def test_location_hub_npc_anchors_are_navigation_only_and_not_character_compatible():
    item = {
        'source_path': 'corpus/eldyrwild-markdown/Longmont Campaign/Campaign 1/Locations/stone_bridge/README.md',
        'subject_class': 'location',
        'section_heading': 'Campaign-canon NPCs anchored here',
        'evidence_role': 'navigation_only',
        'snippet': 'Pippa, Bubbles, Grishna',
    }
    assert is_navigation_only_context(item) is True
    assert is_context_compatible_with_required_lane(item, 'character_party_behavior') is False


def test_evidence_role_alias_is_navigation_only():
    item = {
        'source_path': 'corpus/eldyrwild-markdown/Longmont Campaign/Campaign 1/Locations/stone_bridge/README.md',
        'evidence_role': 'alias',
        'section_heading': 'Retrieval keywords',
    }
    assert is_navigation_only_context(item) is True
    assert is_admittable_planner_evidence(item) is False
    assert is_context_compatible_with_required_lane(item, 'location_worldbuilding') is False


def test_explicit_evidence_role_wins_over_heading_heuristic():
    item = {
        'source_path': 'corpus/eldyrwild-markdown/Longmont Campaign/Campaign 1/Locations/stone_bridge/README.md',
        'subject_class': 'location',
        'evidence_role': 'evidence',
        'section_heading': 'Sub-locations and scene anchors',
        'snippet': "River's Edge Pub as a key social and refuge space.",
    }
    assert is_navigation_only_context(item) is False
    assert is_admittable_planner_evidence(item) is True
    assert is_context_compatible_with_required_lane(item, 'location_worldbuilding') is True


def test_npc_hub_content_is_character_compatible():
    item = {
        'source_path': 'corpus/eldyrwild-markdown/Longmont Campaign/Campaign 1/NPCs/bubbles_the_float_goat/README.md',
        'subject_class': 'npc',
        'section_heading': 'Summary',
        'snippet': 'Bubbles was rescued from floodwaters',
    }
    assert is_context_compatible_with_required_lane(item, 'character_party_behavior') is True
