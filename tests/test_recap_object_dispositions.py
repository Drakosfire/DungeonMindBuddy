"""Object source-authority decisions survive the ordinary pass contract."""
import copy
import json
from dataclasses import replace

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
        assert result[key][0]['item_id'] == 'recap-model-disposition:' + json.dumps(
            ['object_pass', payload[key][0]['item_id']], separators=(',', ':'),
        )
        assert result[key][0]['reason'] == payload[key][0]['reason']
        assert result[key][0]['evidence_refs'] == evidence
    assert result['deferred_items'][0]['suggested_next_step'] == payload['deferred_items'][0]['suggested_next_step']


@pytest.mark.parametrize('bad_id', [None, '', '  ', 7])
def test_recap_disposition_missing_identity_is_not_repaired(bad_id):
    with pytest.raises(ValueError, match='missing disposition ID'):
        consolidate_category_outputs({'object_pass': {'deferred_items': [
            {'item_id': bad_id, 'label': 'Uncertain object', 'reason': 'Unresolved'},
        ]}}, campaign_id='synthetic', session=1)


@pytest.mark.parametrize('collections', [
    ('deferred_items', 'deferred_items'),
    ('ignored_items', 'ignored_items'),
    ('ignored_items', 'deferred_items'),
])
def test_recap_same_pass_duplicate_dispositions_stay_invalid(collections):
    payload = {}
    for collection, item_id in zip(collections, ['D001', ' D001 ']):
        payload.setdefault(collection, []).append({'item_id': item_id})
    with pytest.raises(ValueError, match='duplicate disposition ID'):
        consolidate_category_outputs({'object_pass': payload}, campaign_id='synthetic', session=1)


def test_recap_cross_pass_disposition_identity_is_repeatable_and_lossless():
    outputs = {name: {'deferred_items': [{
        'item_id': 'D001', 'label': name, 'reason': 'Unresolved',
        'evidence_refs': [], 'suggested_next_step': 'Ask the author',
    }]} for name in ('object_pass', 'thread_pass')}
    before = copy.deepcopy(outputs)
    first = consolidate_category_outputs(outputs, campaign_id='synthetic', session=1)
    second = consolidate_category_outputs(outputs, campaign_id='synthetic', session=1)
    assert outputs == before
    assert first['deferred_items'] == second['deferred_items']
    assert len({item['item_id'] for item in first['deferred_items']}) == 2
    for item in first['deferred_items']:
        assert item['reason'] == 'Unresolved'
        assert item['suggested_next_step'] == 'Ask the author'


def test_nonrecap_disposition_ids_keep_existing_contract():
    profile = replace(RECAP_EXTRACTION_PROFILE, admitted_source_domains=frozenset({'worldbuilding'}))
    result = consolidate_category_outputs(
        {'object_pass': {'deferred_items': [{'item_id': 'D001', 'label': 'Unknown'}]}},
        campaign_id='synthetic', session=1, profile=profile,
    )
    assert result['deferred_items'][0]['item_id'] == 'D001'
