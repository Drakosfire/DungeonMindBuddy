"""Unit tests for edge core semantic fingerprint session-stamp handling."""

from __future__ import annotations

import pytest

import graph_memory.kernel as kernel
from graph_memory.kernel.temporal import (
    TEMPORAL_ENVELOPE_SCHEMA,
    TemporalEnvelopeV1,
    TemporalIntervalV1,
    TemporalPointExtentV1,
    TemporalPointV1,
    serialize_temporal_envelope,
)
from graph_memory.kernel.world_projection import (
    WorldGraphProjectionError,
    _assert_active_edge_assertions_agree,
    _edge_core_semantic_fingerprint,
)

EDGE_ID = "edge:party:member_of:location:mireward"
SOURCE_NODE_ID = "pc:caelynn"
TARGET_NODE_ID = "location:mireward"


def _edge_assertion(
    *,
    session_ids: list[str] | None = None,
    temporal_scope: dict | None = None,
    contribution_id: str = "contribution:test-edge-fingerprint",
) -> kernel.GraphContributionAssertion:
    value: dict = {
        "edge_id": EDGE_ID,
        "direction": "outbound",
        "source_domains": ["recap"],
    }
    if session_ids is not None:
        value["session_ids"] = session_ids
    return kernel.build_assertion(
        assertion_kind="edge",
        acceptance_state="accepted",
        contribution_id=contribution_id,
        subject_node_id=SOURCE_NODE_ID,
        target_node_id=TARGET_NODE_ID,
        predicate="member_of",
        label="member of",
        campaign_scope="longmont-c2",
        source_artifact_id="artifact:recap:longmont-c2:session-22",
        value=value,
        temporal_scope=temporal_scope,
    )


def _session_point(session_id: str) -> TemporalPointV1:
    return TemporalPointV1(
        kind="session",
        session_id=session_id,
        certainty="explicit",
    )


def test_edge_fingerprint_ignores_value_session_ids_and_temporal_session_id() -> None:
    first = _edge_assertion(
        session_ids=["session-1"],
        temporal_scope={"session_id": "session-1"},
    )
    second = _edge_assertion(
        session_ids=["session-2", "session-3"],
        temporal_scope={"session_id": "session-2"},
    )
    assert _edge_core_semantic_fingerprint(first) == _edge_core_semantic_fingerprint(second)
    _assert_active_edge_assertions_agree([first, second], graph_object_id=EDGE_ID)


def test_edge_fingerprint_disagrees_on_other_temporal_scope_fields() -> None:
    first = _edge_assertion(
        temporal_scope={"session_id": "session-1", "as_of": "T1"},
    )
    second = _edge_assertion(
        temporal_scope={"session_id": "session-2", "as_of": "T2"},
    )
    assert _edge_core_semantic_fingerprint(first) != _edge_core_semantic_fingerprint(second)
    with pytest.raises(WorldGraphProjectionError, match="Active edge assertions disagree"):
        _assert_active_edge_assertions_agree([first, second], graph_object_id=EDGE_ID)


def test_edge_fingerprint_ignores_v1_source_time_only() -> None:
    first = _edge_assertion(
        temporal_scope=serialize_temporal_envelope(
            TemporalEnvelopeV1(
                schema=TEMPORAL_ENVELOPE_SCHEMA,
                source_time=_session_point("session-1"),
            )
        )
    )
    second = _edge_assertion(
        temporal_scope=serialize_temporal_envelope(
            TemporalEnvelopeV1(
                schema=TEMPORAL_ENVELOPE_SCHEMA,
                source_time=_session_point("session-2"),
            )
        )
    )
    assert _edge_core_semantic_fingerprint(first) == _edge_core_semantic_fingerprint(second)
    _assert_active_edge_assertions_agree([first, second], graph_object_id=EDGE_ID)


def test_edge_fingerprint_disagrees_on_v1_occurrence_time() -> None:
    first = _edge_assertion(
        temporal_scope=serialize_temporal_envelope(
            TemporalEnvelopeV1(
                schema=TEMPORAL_ENVELOPE_SCHEMA,
                occurrence_time=TemporalPointExtentV1(
                    kind="point",
                    point=_session_point("session-1"),
                ),
            )
        )
    )
    second = _edge_assertion(
        temporal_scope=serialize_temporal_envelope(
            TemporalEnvelopeV1(
                schema=TEMPORAL_ENVELOPE_SCHEMA,
                occurrence_time=TemporalPointExtentV1(
                    kind="point",
                    point=_session_point("session-2"),
                ),
            )
        )
    )
    assert _edge_core_semantic_fingerprint(first) != _edge_core_semantic_fingerprint(second)
    with pytest.raises(WorldGraphProjectionError, match="Active edge assertions disagree"):
        _assert_active_edge_assertions_agree([first, second], graph_object_id=EDGE_ID)


def test_edge_fingerprint_disagrees_on_v1_valid_time() -> None:
    first = _edge_assertion(
        temporal_scope=serialize_temporal_envelope(
            TemporalEnvelopeV1(
                schema=TEMPORAL_ENVELOPE_SCHEMA,
                valid_time=TemporalIntervalV1(start=_session_point("session-1")),
            )
        )
    )
    second = _edge_assertion(
        temporal_scope=serialize_temporal_envelope(
            TemporalEnvelopeV1(
                schema=TEMPORAL_ENVELOPE_SCHEMA,
                valid_time=TemporalIntervalV1(start=_session_point("session-2")),
            )
        )
    )
    assert _edge_core_semantic_fingerprint(first) != _edge_core_semantic_fingerprint(second)
    with pytest.raises(WorldGraphProjectionError, match="Active edge assertions disagree"):
        _assert_active_edge_assertions_agree([first, second], graph_object_id=EDGE_ID)
