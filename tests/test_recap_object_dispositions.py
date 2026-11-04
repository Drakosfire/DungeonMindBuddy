"""Object source-authority decisions survive the ordinary pass contract."""
import pytest
from jsonschema import Draft202012Validator

from src.graph_memory.extraction.category_candidate_graph_extractor import (
    consolidate_category_outputs,
    render_category_pass_prompts,
)
from src.graph_memory.extraction.category_candidate_graph_schema import (
    category_pass_text_format_for_spec,
)
from src.graph_memory.extraction.extraction_profile import get_extraction_profile
from src.graph_memory.extraction.recap_extraction_profile import RECAP_EXTRACTION_PROFILE


@pytest.mark.parametrize('profile', [
    RECAP_EXTRACTION_PROFILE,
    get_extraction_profile('recap_category_encounter_job_preview', '2.0'),
])
def test_object_decisions_have_schema_prompt_and_retained_evidence(profile):
    spec = next(s for s in profile.node_passes if s.pass_id == 'object_pass')
    evidence = [{'source_span_ref_id': 'span-1', 'anchor_quotes': ['table diagram']}]
    payload = {
        'observation_nodes': [{
            'node_id': 'item:letter', 'label': 'Sealed letter', 'node_type': 'item',
            'description': 'A physical letter', 'importance': 'medium',
            'evidence_refs': [],
        }],
        'ignored_items': [{
            'item_id': 'ignored:diagram', 'label': 'Diagram',
            'reason': 'Explicit table illustration', 'evidence_refs': evidence,
            'suggested_next_step': None,
        }],
        'deferred_items': [{
            'item_id': 'deferred:token', 'label': 'Token',
            'reason': 'World status unclear', 'evidence_refs': evidence,
            'suggested_next_step': 'Clarify whether the token exists in world',
        }],
    }
    Draft202012Validator(category_pass_text_format_for_spec(spec)['format']['schema']).validate(payload)
    prompts = render_category_pass_prompts([], profile=profile)
    prompt = next(value for key, value in prompts.items() if 'object_pass' in key)
    assert '`ignored_items`' in prompt and '`deferred_items`' in prompt
    result = consolidate_category_outputs(
        {'object_pass': payload}, campaign_id='synthetic', session=1, profile=profile,
    )
    assert [n['node_id'] for n in result['nodes']] == ['item:letter']
    for key in ('ignored_items', 'deferred_items'):
        assert result[key][0]['item_id'] == payload[key][0]['item_id']
        assert result[key][0]['reason'] == payload[key][0]['reason']
        assert result[key][0]['evidence_refs'] == evidence
    assert result['deferred_items'][0]['suggested_next_step'] == payload['deferred_items'][0]['suggested_next_step']
