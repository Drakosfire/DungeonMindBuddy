"""Complete initial records confer authority; discovery remains non-authoritative."""
import json
from uuid import uuid4

import pytest

from apps.live_control_server.services.graph_tool_presentation import GraphToolPresentation
from tests.test_graph_tool_transport import ARGS, SCOPE
from tests.test_graph_tool_presentation import detail_pages

TOOL = "expand_graph_retrieval"


def packet(size=80, missing=False):
    return {"schema": "fixture", "outcome": "enough",
        "reviewedSourceObservations": [
            {"assertionId": "small", "text": "x" * size, "evidenceRefIds": ["e:one", "e:two"],
             "epistemicKind": "belief", "temporalScope": {"kind": "past"}, "reviewId": "review:1"},
            {"assertionId": "large", "text": "unrelated" * 5000, "evidenceRefIds": ["e:two"]}],
        "sourceAnchors": [{"anchorId": "a:one", "evidenceRefId": "e:one"}] + ([] if missing else [
            {"anchorId": "a:two", "evidenceRefId": "e:two"}]),
        "nodes": [{"nodeId": "node:one", "label": "one"}]}


def present(value):
    parent = GraphToolPresentation(SCOPE)
    first = parent.present(TOOL, ARGS, json.dumps(value, ensure_ascii=False), uuid4())
    return parent, first, json.loads(first)


def test_mixed_initial_records_preserve_qualifications_and_complete_anchor_closure():
    value = packet()
    parent, first, initial = present(value)
    assert len(first.encode()) <= 8000
    assert initial["completeRecordCounts"] == {"included": 1, "omitted": 1}
    assert initial["records"][0]["value"] == value["reviewedSourceObservations"][0]
    exposure, = parent.inclusion(TOOL, [first])
    assert exposure.assertion_ids == {"small"}
    assert exposure.evidence_ref_ids == {"e:one", "e:two"}
    assert not exposure.complete
    assert any(row["assertionId"] == "large" for row in initial["view"]["reviewedSourceObservations"])
    # A future request must not inherit the records from an earlier envelope.
    later = detail_pages(parent, first)[-1]
    assert "small" not in parent.inclusion(TOOL, [later])[0].assertion_ids
    changed = json.loads(first)
    changed["records"][0]["value"].pop("epistemicKind")
    with pytest.raises(ValueError, match="Unknown"):
        parent.inclusion(TOOL, [json.dumps(changed)])
    with pytest.raises(ValueError, match="Unknown"):
        GraphToolPresentation(SCOPE).inclusion(TOOL, [first])


def test_missing_anchor_never_partially_admits_a_claim():
    parent, first, initial = present(packet(missing=True))
    assert initial["records"] == []
    assert not parent.inclusion(TOOL, [first])[0].assertion_ids


def test_packing_boundary_is_deterministic_and_never_clips_record():
    low, high = 1, 9000
    while low + 1 < high:
        middle = (low + high) // 2
        _, _, initial = present(packet(size=middle))
        if initial["completeRecordCounts"]["included"]:
            low = middle
        else:
            high = middle
    parent, first, initial = present(packet(size=low))
    assert len(first.encode()) <= 8000
    assert initial["records"][0]["value"]["text"] == "x" * low
    assert parent.inclusion(TOOL, [first])[0].assertion_ids == {"small"}
    other_parent, other, other_initial = present(packet(size=high))
    assert other_initial["completeRecordCounts"]["included"] == 0
    assert not other_parent.inclusion(TOOL, [other])[0].assertion_ids
    # Tokens vary per cache; deterministic content/packing does not.
    _, _, again = present(packet(size=low))
    assert initial["records"] == again["records"]
    assert initial["completeRecordCounts"] == again["completeRecordCounts"]
