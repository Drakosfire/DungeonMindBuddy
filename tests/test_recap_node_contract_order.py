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


def _record_final_dispatch(monkeypatch, *, profile=RECAP_EXTRACTION_PROFILE, finalize=True):
    from src.graph_memory.extraction import category_candidate_graph_extractor as owner

    calls = {}
    original_builder = owner.build_node_pass_prompt

    def with_context(*args, **kwargs):
        prompt, diagnostics = original_builder(*args, **kwargs)
        # Exercise the final dispatch seam, including context inserted at the
        # real source boundary and hints appended after the full template.
        prompt = prompt.replace('\n\n## Source Packet\n\n',
                                '\n\nSynthetic vocabulary context\n\n## Source Packet\n\n', 1)
        return prompt + '\nSynthetic appended identity hint\n', diagnostics

    monkeypatch.setattr(owner, 'build_node_pass_prompt', with_context)
    if not finalize:
        monkeypatch.setattr(owner, 'finalize_node_contract_order', lambda prompt, **kwargs: prompt)

    class Client:
        def run_pass(self, pass_name, *, user_content, instructions, **kwargs):
            calls[pass_name] = (user_content, instructions)
            key = 'observation_edges' if pass_name == 'edge_pass' else (
                'observation_beats' if pass_name == 'beat_pass' else 'observation_nodes')
            return {'parsed': {key: []}, 'usage': {}, 'cost_usd': 0.0,
                    'elapsed_ms': 0, 'response_id': 'synthetic-' + pass_name}

    index = {'schema': 'dmb_source_span_index_v0', 'version': '0.1',
             'campaign_id': 'synthetic', 'session_id': 'session-1',
             'source_artifact_id': 'artifact:synthetic', 'source_ref_id': 'artifact:synthetic:text',
             'spans': [{'span_id': 'span-1', 'source_span_ref_id': 'span-1',
                        'source_artifact_id': 'artifact:synthetic', 'kind': 'paragraph',
                        'text': 'SOURCE_SENTINEL has uncertain meaning.'}]}
    owner.extract_category_candidate_graph(owner.CategoryGraphExtractionOptions(
        campaign_id='synthetic', session_id='session-1', session_number=1,
        source_span_index=index, profile=profile), client=Client())
    return calls


def test_final_dispatch_moves_all_five_contracts_after_every_context(monkeypatch):
    calls = _record_final_dispatch(monkeypatch)
    templates = render_category_pass_prompts([])
    for spec in RECAP_EXTRACTION_PROFILE.node_passes:
        prompt, system = calls[spec.pass_id]
        template = templates[spec.pass_id + '.md']
        start = template.index('## Task\n\n')
        end = template.index('\n\n## Source Packet\n\n', start)
        contract = template[start:end]
        assert prompt.endswith(contract)
        assert prompt.count(contract) == 1
        assert prompt.index('SOURCE_SENTINEL') < prompt.index('Synthetic appended identity hint') < prompt.index(contract)
        assert prompt.count('Synthetic vocabulary context') == 1
        assert prompt.startswith(template[:start])
        assert system == 'Category-decomposed graph memory extraction.'


def test_beat_and_edge_final_dispatch_are_byte_identical_to_unmoved_control(monkeypatch):
    with monkeypatch.context() as patch:
        moved = _record_final_dispatch(patch)
    with monkeypatch.context() as patch:
        original = _record_final_dispatch(patch, finalize=False)
    for name in ('beat_pass', 'edge_pass'):
        assert moved[name] == original[name]


def test_worldbuilding_final_dispatch_is_byte_identical_to_unmoved_control(monkeypatch):
    with monkeypatch.context() as patch:
        moved = _record_final_dispatch(patch, profile=WORLDBUILDING_PLUMBING_PROFILE)
    with monkeypatch.context() as patch:
        original = _record_final_dispatch(patch, profile=WORLDBUILDING_PLUMBING_PROFILE, finalize=False)
    assert moved == original
