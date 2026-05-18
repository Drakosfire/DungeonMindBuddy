from evals.c1s4_preplanning_vertical_slice.context_classification import (
    is_allowed_retrieval_corpus_path,
    infer_planner_lane,
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
        'snippet': 'Pippa, Bubbles, Grishna',
    }
    assert is_navigation_only_context(item) is True
    assert is_context_compatible_with_required_lane(item, 'character_party_behavior') is False


def test_npc_hub_content_is_character_compatible():
    item = {
        'source_path': 'corpus/eldyrwild-markdown/Longmont Campaign/Campaign 1/NPCs/bubbles_the_float_goat/README.md',
        'subject_class': 'npc',
        'section_heading': 'Summary',
        'snippet': 'Bubbles was rescued from floodwaters',
    }
    assert is_context_compatible_with_required_lane(item, 'character_party_behavior') is True
