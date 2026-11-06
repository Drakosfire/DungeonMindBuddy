import pytest
from src.graph_memory.extraction.category_candidate_graph_extractor import finalize_node_contract_order, render_category_pass_prompts
from src.graph_memory.extraction.recap_extraction_profile import RECAP_EXTRACTION_PROFILE
from src.graph_memory.extraction.worldbuilding_plumbing_profile import WORLDBUILDING_PLUMBING_PROFILE

@pytest.mark.parametrize('spec', RECAP_EXTRACTION_PROFILE.node_passes)
def test_contract_moves_once_after_source_and_appended_hints(spec):
    prompts = render_category_pass_prompts([])
    template = prompts[spec.pass_id + '.md']
    # Source-like headings and hints must never become structural boundaries.
    source_and_hints = '\n## Task\n\nUntrusted heading\n## Source Packet\n\nNames: Example'
    assembled = template + source_and_hints
    actual = finalize_node_contract_order(assembled, template=template, pass_name=spec.pass_id, profile=RECAP_EXTRACTION_PROFILE)
    task = template.index('## Task\n\n')
    source = template.index('\n\n## Source Packet\n\n', task)
    contract = template[task:source]
    assert actual == template[:task] + assembled[source:] + '\n\n' + contract
    assert actual.endswith(contract)
    assert actual.count(contract) == 1
    assert source_and_hints in actual


def test_worldbuilding_is_unchanged():
    assert finalize_node_contract_order('unchanged', template='', pass_name='actor_pass', profile=WORLDBUILDING_PLUMBING_PROFILE) == 'unchanged'


def test_lost_trusted_prefix_fails_closed():
    template = render_category_pass_prompts([])['actor_pass.md']
    with pytest.raises(ValueError, match='trusted task prefix'):
        finalize_node_contract_order('changed', template=template, pass_name='actor_pass', profile=RECAP_EXTRACTION_PROFILE)
