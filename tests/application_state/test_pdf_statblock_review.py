from uuid import uuid4

import pytest

from application_state.errors import ApplicationStateConflictError
from application_state.pdf_statblock_review import read_review, save_review


def test_review_keeps_regions_through_edits_and_rejects_stale_writes(application_state_dsn):
    key = {"world_id": "elderwyld", "review_id": uuid4()}
    regions = [{"source_revision_id": "srev:fixture", "page": 1}]
    initial = {"identity": {"name": "Meat Mind"}}
    edited = {"identity": {"name": "Meat Mind revised"}}

    first = save_review(**key, expected_revision=0, definition=initial, regions=regions)
    assert read_review(**key) == first
    assert read_review(**(key | {"world_id": "other-world"})) is None

    with pytest.raises(ApplicationStateConflictError):
        save_review(**key, expected_revision=1, definition=edited, regions=[regions[0] | {"page": 2}])

    second = save_review(**key, expected_revision=1, definition=edited, regions=regions)
    assert second == {"revision": 2, "definition": edited, "regions": regions}
    with pytest.raises(ApplicationStateConflictError):
        save_review(**key, expected_revision=1, definition=initial, regions=regions)
    assert read_review(**key) == second
