import copy
from dataclasses import asdict

import pytest

from graph_memory.anchor_quotes import find_anchor_quote_matches
from ingestion_evaluation.evidence import inspect_quotes
from ingestion_evaluation.runner import digest


def receipt(source, quote):
    index = {'spans': [{'source_span_id': 's1', 'start_line': 1, 'end_line': 1}],
             'content_sha256': digest(source.encode())}
    ref = {'source_span_ref_id': 's1', 'anchor_quotes': [quote],
           'anchor_quote_matches': [asdict(m) for m in find_anchor_quote_matches(source, [quote])]}
    return {'nodes': [{'evidence_refs': [ref]}]}, index


@pytest.mark.parametrize(('source', 'quote'), [
    ('They heard footsteps.', 'They heard footsteps.'),
    ('They heard footsteps.', 'they heard footsteps.'),
    ('They  heard footsteps.', 'They heard footsteps.'),
    ('Mira’s lantern—still burning.', "Mira's lantern-still burning."),
])
def test_real_owner_receipts_preserve_source_bytes_under_allowed_normalization(source, quote):
    graph, index = receipt(source, quote)
    original = copy.deepcopy(graph)
    result = inspect_quotes(graph, index, source, {}, set())
    assert not result['issues']
    assert result['quote_strings'] == result['occurrence_matches'] == 1
    assert graph == original  # Auditing never repairs the authored anchor.
    assert len(result['normalized_quote_differences']) == int(source != quote)
    if source != quote:
        assert result['normalized_quote_differences'] == [
            {'selector': '/nodes/0', 'authored_quote': quote, 'source_text': source}]


@pytest.mark.parametrize('mutation', [
    {'char_start': -1}, {'char_start': True}, {'char_start': 1},
    {'char_end': 100}, {'match_text': 'they heard footsteps.'},
])
def test_normalization_cannot_hide_forged_raw_coordinates_or_source_text(mutation):
    source = 'They heard footsteps.'
    graph, index = receipt(source, 'they heard footsteps.')
    graph['nodes'][0]['evidence_refs'][0]['anchor_quote_matches'][0].update(mutation)
    result = inspect_quotes(graph, index, source, {}, set())
    assert any(issue['reason'] == 'coordinate_mismatch' for issue in result['issues'])


def test_receipt_for_other_words_does_not_establish_an_authored_quote():
    source = 'They heard footsteps.'
    graph, index = receipt(source, source)
    ref = graph['nodes'][0]['evidence_refs'][0]
    ref['anchor_quotes'] = ['They heard music.']
    ref['anchor_quote_matches'][0]['quote'] = 'They heard music.'
    result = inspect_quotes(graph, index, source, {}, set())
    assert any(issue['reason'] == 'anchor_normalization_mismatch' for issue in result['issues'])


def test_authored_quote_requires_a_receipt_in_its_actual_source_frame():
    source = 'They heard footsteps.'
    graph, index = receipt(source, source)
    ref = graph['nodes'][0]['evidence_refs'][0]
    ref['anchor_quote_matches'] = []
    assert inspect_quotes(graph, index, source, {}, set())['issues']
    graph, index = receipt(source, source)
    graph['nodes'][0]['evidence_refs'][0]['source_span_ref_id'] = 'not-the-cited-frame'
    assert inspect_quotes(graph, index, source, {}, set())['issues']


def test_receipt_for_an_unadvertised_quote_is_not_evidence_for_another_quote():
    source = 'They heard footsteps.'
    graph, index = receipt(source, source)
    graph['nodes'][0]['evidence_refs'][0]['anchor_quotes'] = ['footsteps.']
    result = inspect_quotes(graph, index, source, {}, set())
    assert any(issue['reason'] == 'unadvertised_quote_receipt' for issue in result['issues'])


@pytest.mark.parametrize('quote', ['They heard footsteps.', 'they heard footsteps.'])
def test_normalized_anchors_do_not_relax_exact_unique_canonical_rebinding(quote):
    first = 'They heard footsteps.'
    source = first + '\n\nAnother observation.'
    graph, index = receipt(first, quote)
    index['spans'].append({'source_span_id': 's2', 'start_line': 3, 'end_line': 3})
    index['content_sha256'] = digest(source.encode())
    diagnostics = {
        'compact_evidence_context': {'entries': [
            {'source_span_ref_id': sid, 'text': text, 'text_sha256': digest(text.encode())}
            for sid, text in [('s1', first), ('s2', 'Another observation.')]]},
        'canonical_quote_bindings': [{'quote': quote, 'canonical_span_ref_id': 's1',
                                      'nominated_span_ref_id': 's2',
                                      'source_sha256': index['content_sha256'], 'pass_name': 'synthetic'}],
    }
    result = inspect_quotes(graph, index, source, diagnostics, {'synthetic'})
    canonical_issues = [i for i in result['issues'] if i['reason'] == 'canonical_binding_unproven']
    assert bool(canonical_issues) == (quote != first)
    if quote == first:
        diagnostics['compact_evidence_context']['entries'][1]['text'] = first
        diagnostics['compact_evidence_context']['entries'][1]['text_sha256'] = digest(first.encode())
        # A forged raw frame is still rejected independently of its supplied hash.
        assert inspect_quotes(graph, index, source, diagnostics, {'synthetic'})['issues']
