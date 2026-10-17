"""Exact model-readable navigation encoding, with no evidence promotion."""

from copy import deepcopy
import pytest
from apps.live_control_server.services.build_initial_packet_codec import (
    CODEC,
    INTERPRETATION,
    encode,
    decode,
)


def packet():
    support = {
        "source": "source:unchanged",
        "passage": "A reported belief, not a confirmed event. " * 12,
    }
    return {
        "candidates": [
            {"id": "node:unknown", "selected": False, "nullable": None},
            {"id": "node:second", "selected": False},
        ],
        "claimLedger": [
            {
                "claim_id": f"claim:{i}",
                "support": support,
                "epistemic_kind": "belief",
                "visibility": "gm",
                "campaign_scope": ["longmont-c2"],
                "temporal_scope": {"session": 22},
                "evidence_ref_ids": [],
            }
            for i in range(24)
        ],
        "intentHint": None,
        "availableExpansions": ["sources", "neighborhood"],
    }


def test_exact_deterministic_qualified_roundtrip_and_absence():
    original = packet()
    snapshot = deepcopy(original)
    compact = encode(original)
    assert encode(original) == compact
    assert decode(compact) == original == snapshot
    result = decode(compact)
    assert result["candidates"][0]["nullable"] is None
    assert "nullable" not in result["candidates"][1]
    assert result["claimLedger"][0]["epistemic_kind"] == "belief"
    assert result["claimLedger"][0]["evidence_ref_ids"] == []
    assert result["candidates"][0]["id"] == "node:unknown"


@pytest.mark.parametrize(
    "mutation",
    ["version", "extra", "reference", "duplicate", "presence", "width", "unused"],
)
def test_malformed_codec_refused(mutation):
    value = encode(packet())
    table = value["tables"]["claimLedger"]
    if mutation == "version":
        value["schema"] = "unknown"
    elif mutation == "extra":
        value["extra"] = True
    elif mutation == "reference":
        table["references"][0][2] = 999
    elif mutation == "duplicate":
        table["references"].append(deepcopy(table["references"][0]))
    elif mutation == "presence":
        table["presence"][0] = "2" * len(table["columns"])
    elif mutation == "width":
        table["rows"][0].pop()
    else:
        value["shared_values"].append("unused")
    with pytest.raises(ValueError):
        decode(value)


def test_bounded_reference_expansion():
    value = dict(
        schema=CODEC,
        interpretation=INTERPRETATION,
        packet_fields={},
        field_order=["claimLedger"],
        shared_values=["x" * 6000],
        tables={
            "claimLedger": dict(
                columns=["value"],
                rows=[[None] for _ in range(64)],
                presence=["1"] * 64,
                references=[[i, 0, 0] for i in range(64)],
            )
        },
    )
    with pytest.raises(ValueError, match="expansion"):
        decode(value)


@pytest.mark.parametrize("invalid", [float("nan"), float("inf"), set(), {1: "key"}])
def test_non_json_input_refused(invalid):
    with pytest.raises(ValueError):
        encode({"extra": invalid})


def test_deep_input_refused_before_recursive_encoding():
    value = None
    for _ in range(40):
        value = [value]
    with pytest.raises(ValueError, match="depth"):
        encode({"extra": value})


def test_decoded_shared_values_do_not_share_mutable_authority():
    compact = encode(packet())
    snapshot = deepcopy(compact)
    output = decode(compact)
    output["claimLedger"][0]["support"]["source"] = "changed"
    assert output["claimLedger"][1]["support"]["source"] == "source:unchanged"
    assert compact == snapshot


def test_irreducible_packet_still_hits_unchanged_question_limit():
    import json
    from apps.live_control_server.services.build_jev_dispatch import validate_body

    state = {"initialClaimPacket": encode({"claimLedger": [{"text": "x" * 40000}]})}
    body = {
        "model": "jev-1.14.0",
        "state": state,
        "questions": {"yes": {"type": "noul", "instructions": "Is there support?"}},
    }
    with pytest.raises(ValueError, match="per-question context"):
        validate_body(json.dumps(body), state)
