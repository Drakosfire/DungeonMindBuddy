"""Lossless exposure, malformed encodings and exact host shape preservation."""

from copy import deepcopy
import json

import pytest

from apps.live_control_server.services.build_jev_assessment_codec import (
    CODEC,
    encode,
    decode,
    _pack,
    _unpack,
)


def state():
    return {
        "interaction": {
            "history": [{"question": "earlier", "answer": "unchanged " * 300}]
        },
        "interpretation": "Reference data.",
        "decision": {
            "phase": "assess",
            "state": {
                "scope": {"world": "synthetic"},
                "rules": "Do not invent.",
                "evidence": [
                    {
                        "id": "a",
                        "subject": "🐐",
                        "source_class": "native",
                        "epistemic_kind": "belief",
                        "temporal_scope": None,
                        "observation": ["one", 1],
                        "opened": ["p2"],
                    },
                    {
                        "id": "b",
                        "subject": "saved",
                        "source_class": "saved",
                        "epistemic_kind": "authored",
                        "text": [1],
                    },
                    {
                        "id": "c",
                        "subject": "🐐",
                        "source_class": "native",
                        "epistemic_kind": "belief",
                        "temporal_scope": "past",
                        "observation": ["two"],
                        "opened": ["p1", "p2"],
                    },
                ],
                "passages": {
                    "p1": "café 中文 🐐\nexact " * 50,
                    "p2": "中文 🐐\nexact " * 3,
                },
            },
        },
        "observation_qualifications": {
            "a": {"visibility": "gm", "campaign_scope": None},
            "c": {"visibility": "gm"},
        },
    }


def test_mixed_units_exact_roundtrip_history_order_null_and_passages():
    original = state()
    before = deepcopy(original)
    compact = encode(original)
    assert compact["assessment_codec"] == CODEC
    assert decode(compact) == original == before
    assert compact["interaction"] == original["interaction"]
    assert [row["id"] for row in decode(compact)["decision"]["state"]["evidence"]] == [
        "a",
        "b",
        "c",
    ]
    compact["interaction"]["history"].clear()
    assert original == before


@pytest.mark.parametrize("phase", ["select", "navigate", "coverage"])
def test_other_phases_keep_exact_wire_shape(phase):
    original = state()
    original["decision"]["phase"] = phase
    assert encode(original) == original
    assert "assessment_codec" not in encode(original)


@pytest.mark.parametrize(
    "records",
    [
        [],
        [{"x": True}, {"x": 1}],
        [{"x": None}, {}],
        [{"x": ""}, {"x": []}],
        [{"x": 1}, {"y": 2}, {"x": 3}],
    ],
)
def test_group_roundtrip_is_type_exact(records):
    assert json.dumps(_unpack(_pack(records))) == json.dumps(records)


@pytest.mark.parametrize(
    "mutation",
    [
        "tag",
        "phase",
        "columns",
        "collision",
        "length",
        "duplicate_position",
        "boolean_position",
        "gap",
        "extra",
        "grammar",
        "qualification_id",
        "handle",
    ],
)
def test_malformed_encodings_fail_closed(mutation):
    compact = encode(state())
    group = compact["decision"]["state"]["evidence"][0]
    if mutation == "tag":
        compact["assessment_codec"] = "other"
    elif mutation == "phase":
        compact["decision"]["phase"] = "navigate"
    elif mutation == "columns":
        group["columns"].append(group["columns"][0])
    elif mutation == "collision":
        group["constants"][group["columns"][0]] = "wrong"
    elif mutation == "length":
        group["rows"][0].append("wrong")
    elif mutation == "duplicate_position":
        group["positions"][1] = group["positions"][0]
    elif mutation == "boolean_position":
        group["positions"][0] = False
    elif mutation == "gap":
        group["positions"][0] = 99
    elif mutation == "extra":
        group["extra"] = True
    elif mutation == "grammar":
        compact["interpretation"] = "wrong"
    elif mutation == "qualification_id":
        compact["observation_qualifications"] = _pack([{"id": "a"}, {"id": "a"}])
    elif mutation == "handle":
        compact["decision"]["state"]["passages"] = {"p1": 1}
    with pytest.raises((ValueError, KeyError, TypeError)):
        decode(compact)
