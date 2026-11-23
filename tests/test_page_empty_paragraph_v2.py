from hashlib import sha256

import pytest
from pydantic import ValidationError

from application_state.content.page_presentation import PagePresentation, UNSET, candidate
from application_state.errors import ApplicationStateValidationError


def fixture():
    source = 'First.\n\nSecond.\n'
    raw = source.encode()
    digest = lambda b: sha256(b).hexdigest()
    data = {'schema_version': 'dmb_page_presentation_v2', 'markdown_sha256': digest(raw), 'items': [
        {'kind': 'empty_paragraph', 'id': 'leading'},
        {'kind': 'block', 'id': 'first', 'byte_start': 0, 'byte_end': 8, 'sha256': digest(raw[:8])},
        {'kind': 'empty_paragraph', 'id': 'middle'},
        {'kind': 'block', 'id': 'second', 'byte_start': 8, 'byte_end': len(raw), 'sha256': digest(raw[8:])},
        {'kind': 'empty_paragraph', 'id': 'trailing'},
    ]}
    return source, data


def test_v2_accepts_ordered_empty_blocks_without_changing_source_binding():
    source, data = fixture()
    result = PagePresentation.model_validate(data).checked(source)
    assert [item.id for item in result.items] == ['leading', 'first', 'middle', 'second', 'trailing']
    with pytest.raises(ApplicationStateValidationError):
        result.checked(source + 'changed')


def test_empty_blocks_require_v2_and_unique_ids():
    source, data = fixture()
    with pytest.raises(ApplicationStateValidationError):
        PagePresentation.model_validate({**data, 'schema_version': 'dmb_page_presentation_v1'}).checked(source)
    data['items'][-1]['id'] = 'leading'
    with pytest.raises(ApplicationStateValidationError):
        PagePresentation.model_validate(data).checked(source)


def test_old_writers_cannot_remove_or_downgrade_v2():
    source, data = fixture()
    current = PagePresentation.model_validate(data).checked(source)
    for old_value in (None, UNSET):
        with pytest.raises(ApplicationStateValidationError):
            candidate(old_value, source, current)
    v1 = {**data, 'schema_version': 'dmb_page_presentation_v1', 'items': [item for item in data['items'] if item['kind'] == 'block']}
    with pytest.raises(ApplicationStateValidationError):
        candidate(v1, source, current)


def test_v2_refuses_unknown_and_nested_empty_items():
    source, data = fixture()
    with pytest.raises(ValidationError):
        PagePresentation.model_validate({**data, 'items': [{'kind': 'empty_paragraph', 'id': 'x', 'text': 'hidden'}]})
    row = {'kind': 'row', 'id': 'r', 'slots': [{'id': 's', 'width': 12, 'blocks': [{'kind': 'empty_paragraph', 'id': 'x'}]}]}
    with pytest.raises(ValidationError):
        PagePresentation.model_validate({**data, 'items': [row]})
