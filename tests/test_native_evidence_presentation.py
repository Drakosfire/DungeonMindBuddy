"""Losslessness of display, including structure, quoting and citation handles."""
from copy import deepcopy
from hashlib import sha256
import json

import pytest

from application_state.agent_conversation.native_evidence_presentation import (
    flat_native_evidence,
    restore_flat_native_evidence,
    reviewed_qualification_frame,
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


def test_shared_qualifications_merge_only_byte_identical_values_and_keep_interleaved_order():
    same = {"scope": "session", "uncertain": True, "text": "reported, not verified\nquote\t_"}
    frame = {"native_assertions": {"assertions": [
        {"assertion_handle": "a0", "assertion": {"qualification": "q3", "literal": "exact quote"}}],
        "qualifications": {"q0": same, "q1": {**same, "uncertain": False}, "q2": deepcopy(same),
                           "q3": {"text": same["text"], "uncertain": True, "scope": "session"},
                           "q4": {**same, "text": same["text"] + " "}}}}
    original = deepcopy(frame)
    text, proof = flat_native_evidence(frame)
    assert len(proof["tables"][1]["layouts"]) == 4
    assert '["q0","q2"]' in text
    assert ["qualification_handles"] in proof["tables"][1]["columns"]
    assert ["qualification_handles", 0] not in proof["tables"][1]["columns"]
    restored = restore_flat_native_evidence(text, proof)
    assert json.dumps(restored) == json.dumps(original)
    assert frame == original
    restored["native_assertions"]["qualifications"]["q0"]["scope"] = "changed"
    assert restored["native_assertions"]["qualifications"]["q2"]["scope"] == "session"
    with pytest.raises(ValueError, match="Duplicate shared"):
        restore_flat_native_evidence(text.replace('["q0","q2"]', '["q0","q0"]'), proof)
    with pytest.raises(ValueError, match="handles differ"):
        restore_flat_native_evidence(text.replace('["q0","q2"]', '["q0","unknown"]'), proof)


def test_historical_flat_proof_is_not_a_competing_runtime_reader():
    with pytest.raises(ValueError, match="pinned renderer"):
        restore_flat_native_evidence("historical artifact", {"tables": []})


@pytest.mark.parametrize("bad", [None, "binding", "pending", "incomplete", "duplicate", "reconstruction", "digest", "erasure"])
def test_reviewed_qualification_separation_preserves_every_other_value(bad):
    frame = {"native_assertions": {"assertions": [{"assertion_handle": "a0", "literal": "audit-id is an exact quote"}],
        "qualifications": {"q0": {"standing": "provisional", "domain_metadata": [
            {"world_context": {"source_qualification": "A report. audit-id Not omniscient.", "other": "audit-id"}}]}}},
        "native_body_evidence": {"text": "audit-id"}, "user_question": "audit-id?"}
    original = deepcopy(frame)
    compact = lambda x: json.dumps(x, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
    parts = [{"role": "meaning", "text": "A report. "}, {"role": "host_audit", "text": "audit-id "},
             {"role": "meaning", "text": "Not omniscient."}]
    record = {"qualification_handle": "q0", "domain_index": 0,
              "original_sha256": sha256("A report. audit-id Not omniscient.".encode()).hexdigest(), "parts": parts}
    review = {"schema": "dmb_reviewed_qualification_parts_v1", "reviewer": "Independent reviewer",
              "source_frame_sha256": sha256(compact(frame).encode()).hexdigest(), "records": [record]}
    if bad == "binding": review["source_frame_sha256"] = "wrong"
    elif bad == "pending": parts[0]["role"] = "pending"
    elif bad == "incomplete": review["records"] = []
    elif bad == "duplicate": review["records"].append(deepcopy(record))
    elif bad == "reconstruction": parts[0]["text"] = "Other meaning"
    elif bad == "digest": record["original_sha256"] = "wrong"
    elif bad == "erasure":
        for part in parts: part["role"] = "host_audit"
    if bad:
        with pytest.raises(ValueError): reviewed_qualification_frame(frame, review)
    else:
        result, proof = reviewed_qualification_frame(frame, review)
        expected = deepcopy(frame)
        expected["native_assertions"]["qualifications"]["q0"]["domain_metadata"][0]["world_context"]["source_qualification"] = "A report. Not omniscient."
        assert result == expected
        assert proof["original_frame_sha256"] != proof["presented_frame_sha256"]
    assert frame == original
