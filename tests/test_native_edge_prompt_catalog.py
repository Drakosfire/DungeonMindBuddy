from apps.live_control_server.integrations.dungeonmind.assertion_qualification import (
    CURRENT_V5_TARGET, edge_endpoint_kind_admission_reason,
)
from src.graph_memory.extraction.native_edge_prompt_catalog import (
    native_edge_prompt_rules, native_edge_prompt_markdown,
)
from src.graph_memory.extraction.category_candidate_graph_extractor import (
    render_category_pass_prompts, _empty_party_context,
)


def test_every_advertised_tuple_passes_native_qualification():
    rules = native_edge_prompt_rules()
    assert rules and len({r.predicate for r in rules}) == len(rules)
    vocabulary = CURRENT_V5_TARGET.world_object_loader()
    for rule in rules:
        for source in rule.subject_kinds:
            for target in rule.object_kinds:
                assert edge_endpoint_kind_admission_reason(
                    buddy_predicate=rule.predicate, from_buddy_kind=source,
                    to_buddy_kind=target, vocabulary=vocabulary,
                ) is None, (rule.predicate, source, target)


def test_reverse_belongs_to_mapping_keeps_subject_direction():
    rule = next(r for r in native_edge_prompt_rules() if r.predicate == 'belongs_to')
    assert 'item' in rule.subject_kinds and 'pc' in rule.object_kinds
    assert edge_endpoint_kind_admission_reason(
        buddy_predicate='belongs_to', from_buddy_kind='item', to_buddy_kind='pc',
    ) is None


def test_actual_edge_prompt_does_not_recommend_unmapped_predicates():
    prompts = render_category_pass_prompts([], party_ctx=_empty_party_context('synthetic'))
    edge = prompts['edge_pass.md']
    for unsupported in ['besieges', 'reports_threat_in', 'part_of_group', 'governs', 'reports_to']:
        assert unsupported not in edge
    assert native_edge_prompt_markdown() in edge
    assert 'Use exact `node_id` values' in edge
    assert 'descriptive, source-backed label' in edge
    assert 'Defer unsupported relationships' in edge
    assert 'Source Packet' in edge
