"""Losslessness of display, including structure, quoting and citation handles."""
from copy import deepcopy
import json

import pytest

from application_state.agent_conversation.native_evidence_presentation import (
    flat_native_evidence,
    restore_flat_native_evidence,
)


@pytest.mark.parametrize("value", [None, False, 0, 1.25, "_", "a\tb\nc\u2028d", [], {},
    {"0": [None, {"a/b~c": "quote\""}], "empty": []}])
def test_flatten_preserves_every_value_type_container_and_handle(value):
    frame = {"user_question": "Question", "input_status": "partial",
        "native_body_evidence": {"excerpts": [{"excerpt_handle": "body0", "text": "exact\nquote"}]},
        "native_assertions": {"status": "complete", "universal_absence_claimed": False,
            "assertions": [{"assertion_handle": "assertion0", "assertion": {"value": value}},
                {"assertion_handle": "assertion1", "different": {"0": False}}],
            "qualifications": {"qualification0": {"nested": [value], "scope": "campaign"}}}}
    original = deepcopy(frame)
    text, proof = flat_native_evidence(frame)
    assert restore_flat_native_evidence(text, proof) == original
    assert json.dumps(restore_flat_native_evidence(text, proof)) == json.dumps(original)
    assert frame == original
    assert flat_native_evidence(frame) == (text, proof)
    for handle in ["assertion0", "assertion1", "qualification0", "body0"]:
        assert handle in text


def test_flatten_handles_empty_tables_and_preserves_state():
    frame = {"native_assertions": {"assertions": [], "qualifications": {}, "state": None}}
    text, proof = flat_native_evidence(frame)
    assert restore_flat_native_evidence(text, proof) == frame
    assert json.dumps(restore_flat_native_evidence(text, proof)) == json.dumps(frame)


def test_readback_detects_changed_cells():
    frame = {"native_assertions": {"assertions": [{"assertion_handle": "a", "fact": "original"}], "qualifications": {}}}
    text, proof = flat_native_evidence(frame)
    assert restore_flat_native_evidence(text.replace('"original"', '"changed"'), proof) != frame
