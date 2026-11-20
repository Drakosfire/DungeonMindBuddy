"""Source-exact definition boundaries for future independent observations."""
from copy import deepcopy

import pytest

from graph_memory.extraction.worldbuilding_source_sections import (
    SourceSectionRetentionError,
    owned_livestock_definitions,
)


def rows(*texts):
    return [dict(source_span_ref_id=f"source:one:span:{i}", line_start=i,
                 line_end=i, text=text) for i, text in enumerate(texts, 1)]


def source():
    return rows(
        "#### Fantastic Livestock for the Coast",
        "Local fishers believe these animals can sense approaching storms.",
        "#### 1. Lantern Sheep",
        "Their wool glows; the healing properties of their milk are only rumored.",
        "## Animal Products and Uses:",
        "Wool: woven into sails.",
        "#### 2. River Goats",
        "They walk on water and carry goods across rivers.",
        "## Cultural Significance:",
        "Some villages regard them as sacred.",
        "### Governance:",
        "A council governs the port.",
    )


def test_definitions_preserve_complete_qualified_text_without_neighbor_leakage():
    data = source()
    original = deepcopy(data)
    definitions = owned_livestock_definitions(data)
    assert len(definitions) == 2
    sheep, goats = definitions
    assert sheep['owner_label'] == goats['owner_label'] == 'Coast'
    assert sheep['title'] == 'Lantern Sheep'
    assert goats['title'] == 'River Goats'
    assert sheep['source_span_ref_ids'] == [f'source:one:span:{i}' for i in range(1, 7)]
    assert goats['source_span_ref_ids'] == ['source:one:span:1', 'source:one:span:2',
                                          *[f'source:one:span:{i}' for i in range(7, 11)]]
    for definition in definitions:
        selected = [row for row in data if row['source_span_ref_id'] in definition['source_span_ref_ids']]
        assert definition['description'] == '\n\n'.join(row['text'] for row in selected)
        assert 'Local fishers believe' in definition['description']
        assert 'council' not in definition['description']
    assert 'only rumored' in sheep['description']
    assert 'River Goats' not in sheep['description']
    assert 'Lantern Sheep' not in goats['description']
    assert data == original


def test_ids_are_deterministic_distinct_and_bound_to_source_and_content():
    data = source()
    first = owned_livestock_definitions(data)
    assert first == owned_livestock_definitions(deepcopy(data))
    assert len({x['definition_id'] for x in first}) == 2
    foreign = [{**row, 'source_span_ref_id': row['source_span_ref_id'].replace('one', 'two')}
               for row in data]
    assert first[0]['definition_id'] != owned_livestock_definitions(foreign)[0]['definition_id']
    changed = deepcopy(data)
    changed[3]['text'] = 'The alleged healing property is disproven.'
    assert first[0]['definition_id'] != owned_livestock_definitions(changed)[0]['definition_id']
    assert first[1]['definition_id'] == owned_livestock_definitions(changed)[1]['definition_id']


def test_multiple_source_owners_remain_separate():
    data = source() + [
        dict(source_span_ref_id=f'source:one:span:{i}', line_start=i, line_end=i, text=text)
        for i, text in enumerate([
            '#### Fantastic Livestock for the Highlands', '#### 1. Moss Deer',
            'Farmers use their shed antlers.', '### History:',
        ], 13)
    ]
    definitions = owned_livestock_definitions(data)
    assert [x['owner_label'] for x in definitions] == ['Coast', 'Coast', 'Highlands']
    assert 'Coast' not in definitions[2]['description']
    assert definitions[2]['source_span_ref_ids'] == [f'source:one:span:{i}' for i in range(13,16)]


@pytest.mark.parametrize('mutation', ['duplicate_ref', 'overlap', 'missing_number', 'unbounded', 'empty_definition'])
def test_ambiguous_or_damaged_boundaries_reject(mutation):
    data = source()
    if mutation == 'duplicate_ref':
        data[3]['source_span_ref_id'] = data[2]['source_span_ref_id']
    elif mutation == 'overlap':
        data[3]['line_start'] = data[2]['line_start']
    elif mutation == 'missing_number':
        data[6]['text'] = '#### 3. River Goats'
    elif mutation == 'unbounded':
        data = data[:10]
    else:
        data = data[:2] + [data[2]] + data[6:]
    with pytest.raises(SourceSectionRetentionError):
        owned_livestock_definitions(data)


def test_no_recognized_owned_layout_produces_no_invented_definitions():
    assert owned_livestock_definitions(rows('### Animals', 'Goats may be present.')) == []


def test_blank_numbered_definition_title_rejects_even_with_body():
    data = rows('#### Fantastic Livestock for the Coast', '#### 1.   ',
                'A source-backed body does not supply a missing name.', '### Governance:')
    with pytest.raises(SourceSectionRetentionError, match='title is empty'):
        owned_livestock_definitions(data)
