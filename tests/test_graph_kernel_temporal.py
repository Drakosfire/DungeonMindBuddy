"""Unit tests for TemporalEnvelopeV1 and legacy temporal_scope interpretation (TL00)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

import graph_memory.kernel as kernel
from graph_memory.kernel.temporal import (
    TEMPORAL_ENVELOPE_SCHEMA,
    TemporalEnvelopeV1,
    TemporalIntervalExtentV1,
    TemporalIntervalV1,
    TemporalPointExtentV1,
    TemporalPointV1,
    TemporalScopeValidationError,
    interpret_temporal_scope,
    serialize_temporal_envelope,
    temporal_core_semantic_payload,
    temporal_source_payload,
)
from graph_memory.kernel.world_projection import (
    WorldGraphProjectionError,
    _edge_core_semantic_fingerprint,
    _node_core_semantic_fingerprint,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
BUNDLE_CONTRIBUTION = (
    REPO_ROOT
    / "graph_data/approved_contribution_bundles/eldyrwild-longmont-c2-initial-v1"
    / "contributions/004-session-22-mireward-road.json"
)

GOLDEN_EVENT_ASSERTION_ID = "assertion:c940738e1fe6fc8a"


def _session_point(session_id: str) -> TemporalPointV1:
    return TemporalPointV1(
        kind="session",
        session_id=session_id,
        certainty="explicit",
    )


def _source_only_envelope(session_id: str) -> TemporalEnvelopeV1:
    return TemporalEnvelopeV1(
        schema=TEMPORAL_ENVELOPE_SCHEMA,
        source_time=_session_point(session_id),
        occurrence_time=None,
        valid_time=None,
    )


def _occurrence_envelope(session_id: str) -> TemporalEnvelopeV1:
    return TemporalEnvelopeV1(
        schema=TEMPORAL_ENVELOPE_SCHEMA,
        source_time=None,
        occurrence_time=TemporalPointExtentV1(
            kind="point",
            point=_session_point(session_id),
        ),
        valid_time=None,
    )


def _valid_time_envelope(session_id: str) -> TemporalEnvelopeV1:
    return TemporalEnvelopeV1(
        schema=TEMPORAL_ENVELOPE_SCHEMA,
        source_time=None,
        occurrence_time=None,
        valid_time=TemporalIntervalV1(start=_session_point(session_id)),
    )


def _edge_assertion(
    *,
    temporal_scope: dict | None,
    contribution_id: str = "contribution:test-temporal",
) -> kernel.GraphContributionAssertion:
    return kernel.build_assertion(
        assertion_kind="edge",
        acceptance_state="accepted",
        contribution_id=contribution_id,
        subject_node_id="pc:caelynn",
        target_node_id="location:mireward",
        predicate="member_of",
        label="member of",
        campaign_scope="longmont-c2",
        value={
            "edge_id": "edge:pc:caelynn:member_of:location:mireward",
            "direction": "outbound",
        },
        temporal_scope=temporal_scope,
    )


def _node_assertion(
    *,
    temporal_scope: dict | None,
    contribution_id: str = "contribution:test-temporal-node",
) -> kernel.GraphContributionAssertion:
    return kernel.build_assertion(
        assertion_kind="node",
        acceptance_state="accepted",
        contribution_id=contribution_id,
        subject_node_id="location:mireward",
        label="Mireward",
        campaign_scope="longmont-c2",
        value={"kind": "location", "role": "town", "aliases": ["Mireward"]},
        temporal_scope=temporal_scope,
    )


# ---------------------------------------------------------------------------
# Typed model validation
# ---------------------------------------------------------------------------


def test_session_point_validation() -> None:
    point = TemporalPointV1(
        kind="session",
        session_id="session-12",
        certainty="explicit",
    )
    assert point.session_id == "session-12"
    with pytest.raises(ValidationError):
        TemporalPointV1(kind="session", certainty="explicit")


def test_campaign_date_point_validation() -> None:
    point = TemporalPointV1(
        kind="campaign_date",
        value="204-Firstfrost-3",
        calendar_id="eldyrwild-common",
        certainty="approximate",
    )
    assert point.value == "204-Firstfrost-3"
    with pytest.raises(ValidationError):
        TemporalPointV1(kind="campaign_date", certainty="explicit")


def test_relative_point_validation() -> None:
    structured = TemporalPointV1(
        kind="relative",
        relation="before",
        anchor_ref="event:festival-of-expansion",
        certainty="inferred",
    )
    textual = TemporalPointV1(
        kind="relative",
        raw_expression="three nights later",
        certainty="approximate",
    )
    assert structured.anchor_ref == "event:festival-of-expansion"
    assert textual.raw_expression == "three nights later"
    with pytest.raises(ValidationError):
        TemporalPointV1(kind="relative", certainty="unknown")


def test_textual_and_unknown_point_validation() -> None:
    textual = TemporalPointV1(
        kind="textual",
        raw_expression="during her childhood",
        certainty="unknown",
    )
    unknown = TemporalPointV1(
        kind="unknown",
        raw_expression="long ago",
        certainty="unknown",
    )
    assert textual.raw_expression == "during her childhood"
    assert unknown.kind == "unknown"
    with pytest.raises(ValidationError):
        TemporalPointV1(kind="textual", certainty="explicit")
    with pytest.raises(ValidationError):
        TemporalPointV1(
            kind="unknown",
            session_id="session-1",
            certainty="unknown",
        )


def test_cross_kind_fields_rejected() -> None:
    """Point kinds must not accept contradictory cross-kind fields."""
    with pytest.raises(ValidationError):
        TemporalPointV1(
            kind="session",
            session_id="session-1",
            value="204-Firstfrost-3",
            certainty="explicit",
        )
    with pytest.raises(ValidationError):
        TemporalPointV1(
            kind="session",
            session_id="session-1",
            calendar_id="eldyrwild-common",
            certainty="explicit",
        )
    with pytest.raises(ValidationError):
        TemporalPointV1(
            kind="session",
            session_id="session-1",
            relation="during",
            certainty="explicit",
        )
    with pytest.raises(ValidationError):
        TemporalPointV1(
            kind="campaign_date",
            value="204-Firstfrost-3",
            session_id="session-1",
            certainty="explicit",
        )
    with pytest.raises(ValidationError):
        TemporalPointV1(
            kind="textual",
            raw_expression="during her childhood",
            session_id="session-1",
            certainty="unknown",
        )
    with pytest.raises(ValidationError):
        TemporalPointV1(
            kind="textual",
            raw_expression="during her childhood",
            value="204-Firstfrost-3",
            certainty="unknown",
        )
    with pytest.raises(ValidationError):
        TemporalPointV1(
            kind="unknown",
            relation="before",
            anchor_ref="event:x",
            certainty="unknown",
        )
    with pytest.raises(ValidationError):
        TemporalPointV1(
            kind="relative",
            relation="before",
            anchor_ref="event:x",
            session_id="session-1",
            certainty="inferred",
        )


def test_interval_validation() -> None:
    interval = TemporalIntervalV1(
        start=_session_point("session-13"),
        end=None,
        raw_expression=None,
    )
    assert interval.start is not None
    with pytest.raises(ValidationError):
        TemporalIntervalV1()


def test_blank_identifiers_rejected() -> None:
    with pytest.raises(ValidationError):
        TemporalPointV1(
            kind="session",
            session_id="   ",
            certainty="explicit",
        )
    with pytest.raises(ValidationError):
        TemporalPointV1(
            kind="textual",
            raw_expression="",
            certainty="explicit",
        )


def test_extra_fields_rejected() -> None:
    with pytest.raises(ValidationError):
        TemporalPointV1.model_validate(
            {
                "kind": "session",
                "session_id": "session-1",
                "certainty": "explicit",
                "unexpected": True,
            }
        )
    with pytest.raises(ValidationError):
        TemporalEnvelopeV1.model_validate(
            {
                "schema": TEMPORAL_ENVELOPE_SCHEMA,
                "source_time": {
                    "kind": "session",
                    "session_id": "session-1",
                    "certainty": "explicit",
                },
                "occurrence_time": None,
                "valid_time": None,
                "transaction_time": "now",
            }
        )


def test_envelope_requires_at_least_one_lane() -> None:
    with pytest.raises(ValidationError):
        TemporalEnvelopeV1(
            schema=TEMPORAL_ENVELOPE_SCHEMA,
            source_time=None,
            occurrence_time=None,
            valid_time=None,
        )


def test_deterministic_serialization_and_round_trip() -> None:
    envelope = TemporalEnvelopeV1(
        schema=TEMPORAL_ENVELOPE_SCHEMA,
        source_time=_session_point("session-12"),
        occurrence_time=TemporalIntervalExtentV1(
            kind="interval",
            start=_session_point("session-10"),
            end=_session_point("session-12"),
            raw_expression="throughout the siege",
        ),
        valid_time=TemporalIntervalV1(
            start=_session_point("session-13"),
        ),
    )
    first = serialize_temporal_envelope(envelope)
    second = serialize_temporal_envelope(envelope)
    assert first == second
    assert first["schema"] == TEMPORAL_ENVELOPE_SCHEMA
    assert first["source_time"] is not None
    assert first["occurrence_time"] is not None
    assert first["valid_time"] is not None
    assert "session_id" not in first  # never legacy shorthand
    round_trip = TemporalEnvelopeV1.model_validate(first)
    assert serialize_temporal_envelope(round_trip) == first


# ---------------------------------------------------------------------------
# Compatibility interpretation
# ---------------------------------------------------------------------------


def test_interpret_none() -> None:
    result = interpret_temporal_scope(None)
    assert result.format == "none"
    assert result.envelope is None
    assert result.unresolved_legacy_fields == {}


def test_interpret_legacy_session_only_maps_to_source_time() -> None:
    result = interpret_temporal_scope({"session_id": "session-12"})
    assert result.format == "legacy_session_observation"
    assert result.envelope is not None
    assert result.envelope.source_time is not None
    assert result.envelope.source_time.kind == "session"
    assert result.envelope.source_time.session_id == "session-12"
    assert result.envelope.occurrence_time is None
    assert result.envelope.valid_time is None
    assert result.unresolved_legacy_fields == {}


def test_interpret_legacy_session_plus_as_of_preserves_unresolved() -> None:
    result = interpret_temporal_scope({"session_id": "session-12", "as_of": "T1"})
    assert result.format == "legacy_unresolved"
    assert result.envelope is not None
    assert result.envelope.source_time is not None
    assert result.envelope.source_time.session_id == "session-12"
    assert result.envelope.occurrence_time is None
    assert result.unresolved_legacy_fields == {"as_of": "T1"}
    assert result.diagnostics


def test_interpret_unknown_legacy_shape_preserved() -> None:
    raw = {"era": "Age of Ash", "note": "unnormalized"}
    result = interpret_temporal_scope(raw)
    assert result.format == "legacy_unresolved"
    assert result.envelope is None
    assert result.unresolved_legacy_fields == raw
    assert result.diagnostics


def test_malformed_schema_tagged_v1_raises_typed_error() -> None:
    with pytest.raises(TemporalScopeValidationError) as exc_info:
        interpret_temporal_scope(
            {
                "schema": TEMPORAL_ENVELOPE_SCHEMA,
                "source_time": None,
                "occurrence_time": None,
                "valid_time": None,
            }
        )
    assert exc_info.value.diagnostics
    with pytest.raises(TemporalScopeValidationError):
        interpret_temporal_scope(
            {
                "schema": TEMPORAL_ENVELOPE_SCHEMA,
                "source_time": {"kind": "session", "certainty": "explicit"},
                "occurrence_time": None,
                "valid_time": None,
            }
        )


def test_legacy_session_does_not_populate_occurrence_time() -> None:
    result = interpret_temporal_scope({"session_id": "session-20"})
    assert result.envelope is not None
    assert result.envelope.occurrence_time is None
    assert result.envelope.valid_time is None
    source = temporal_source_payload({"session_id": "session-20"})
    assert source is not None
    assert "source_time" in source
    assert temporal_core_semantic_payload({"session_id": "session-20"}) is None


def test_source_time_does_not_populate_valid_time() -> None:
    envelope = _source_only_envelope("session-12")
    serialized = serialize_temporal_envelope(envelope)
    assert serialized["valid_time"] is None
    assert serialized["occurrence_time"] is None
    core = temporal_core_semantic_payload(serialized)
    assert core is None
    source = temporal_source_payload(serialized)
    assert source == {"source_time": serialized["source_time"]}


# ---------------------------------------------------------------------------
# Semantic fingerprints
# ---------------------------------------------------------------------------


def test_legacy_source_sessions_agree_on_core_fingerprints() -> None:
    first = _edge_assertion(temporal_scope={"session_id": "session-1"})
    second = _edge_assertion(temporal_scope={"session_id": "session-2"})
    assert _edge_core_semantic_fingerprint(first) == _edge_core_semantic_fingerprint(
        second
    )
    node_a = _node_assertion(temporal_scope={"session_id": "session-1"})
    node_b = _node_assertion(temporal_scope={"session_id": "session-2"})
    assert _node_core_semantic_fingerprint(node_a) == _node_core_semantic_fingerprint(
        node_b
    )


def test_v1_source_sessions_agree_on_core_fingerprints() -> None:
    first = _edge_assertion(
        temporal_scope=serialize_temporal_envelope(_source_only_envelope("session-1"))
    )
    second = _edge_assertion(
        temporal_scope=serialize_temporal_envelope(_source_only_envelope("session-2"))
    )
    assert _edge_core_semantic_fingerprint(first) == _edge_core_semantic_fingerprint(
        second
    )


def test_v1_occurrence_sessions_disagree_on_core_fingerprints() -> None:
    first = _edge_assertion(
        temporal_scope=serialize_temporal_envelope(_occurrence_envelope("session-1"))
    )
    second = _edge_assertion(
        temporal_scope=serialize_temporal_envelope(_occurrence_envelope("session-2"))
    )
    assert _edge_core_semantic_fingerprint(first) != _edge_core_semantic_fingerprint(
        second
    )


def test_v1_valid_time_sessions_disagree_on_core_fingerprints() -> None:
    first = _edge_assertion(
        temporal_scope=serialize_temporal_envelope(_valid_time_envelope("session-1"))
    )
    second = _edge_assertion(
        temporal_scope=serialize_temporal_envelope(_valid_time_envelope("session-2"))
    )
    assert _edge_core_semantic_fingerprint(first) != _edge_core_semantic_fingerprint(
        second
    )


def test_legacy_as_of_remains_correction_sensitive() -> None:
    first = _edge_assertion(
        temporal_scope={"session_id": "session-1", "as_of": "T1"}
    )
    second = _edge_assertion(
        temporal_scope={"session_id": "session-2", "as_of": "T2"}
    )
    assert _edge_core_semantic_fingerprint(first) != _edge_core_semantic_fingerprint(
        second
    )
    assert temporal_core_semantic_payload(
        {"session_id": "session-1", "as_of": "T1"}
    ) == {"as_of": "T1"}


def test_unknown_schema_keeps_session_id_correction_sensitive() -> None:
    """Explicit unrecognized schema tags must not receive the observation strip."""
    first_payload = {
        "schema": "dmb_temporal_envelope_v2",
        "session_id": "session-1",
        "occurrence": "A",
    }
    second_payload = {
        "schema": "dmb_temporal_envelope_v2",
        "session_id": "session-2",
        "occurrence": "A",
    }
    assert temporal_core_semantic_payload(first_payload) == first_payload
    assert temporal_core_semantic_payload(second_payload) == second_payload
    first = _edge_assertion(temporal_scope=first_payload)
    second = _edge_assertion(temporal_scope=second_payload)
    assert _edge_core_semantic_fingerprint(first) != _edge_core_semantic_fingerprint(
        second
    )


def test_malformed_v1_fingerprint_raises_projection_integrity_409() -> None:
    malformed = {
        "schema": TEMPORAL_ENVELOPE_SCHEMA,
        "source_time": None,
        "occurrence_time": None,
        "valid_time": None,
    }
    with pytest.raises(TemporalScopeValidationError):
        temporal_core_semantic_payload(malformed)

    edge = _edge_assertion(temporal_scope=malformed)
    with pytest.raises(WorldGraphProjectionError) as exc_info:
        _edge_core_semantic_fingerprint(edge)
    assert exc_info.value.code == "projection_integrity_error"
    assert exc_info.value.status_code == 409
    assert any(
        d.code == "malformed_temporal_envelope" for d in exc_info.value.diagnostics
    )

    node = _node_assertion(temporal_scope=malformed)
    with pytest.raises(WorldGraphProjectionError) as node_exc:
        _node_core_semantic_fingerprint(node)
    assert node_exc.value.code == "projection_integrity_error"
    assert node_exc.value.status_code == 409


# ---------------------------------------------------------------------------
# Assertion identity compatibility
# ---------------------------------------------------------------------------


def test_golden_legacy_assertion_id_unchanged() -> None:
    payload = json.loads(BUNDLE_CONTRIBUTION.read_text(encoding="utf-8"))
    assertion = next(
        item
        for item in payload["accepted_assertions"]
        if item["assertion_id"] == GOLDEN_EVENT_ASSERTION_ID
    )
    assert assertion["temporal_scope"] == {"session_id": "session-22"}
    computed = kernel.compute_assertion_id(
        assertion_kind=assertion["assertion_kind"],
        subject_node_id=assertion["subject_node_id"],
        target_node_id=assertion["target_node_id"],
        predicate=assertion["predicate"],
        label=assertion["label"],
        value=assertion["value"],
        campaign_scope=assertion["campaign_scope"],
        temporal_scope=assertion["temporal_scope"],
        epistemic_kind=assertion["epistemic_kind"],
        visibility=assertion["visibility"],
    )
    assert computed == GOLDEN_EVENT_ASSERTION_ID
    assert computed == assertion["assertion_id"]


def test_legacy_contribution_round_trip_preserves_temporal_scope_and_id() -> None:
    payload = json.loads(BUNDLE_CONTRIBUTION.read_text(encoding="utf-8"))
    contribution = kernel.GraphContribution.model_validate(payload)
    dumped = contribution.model_dump(mode="json")
    event = next(
        item
        for item in dumped["accepted_assertions"]
        if item["assertion_id"] == GOLDEN_EVENT_ASSERTION_ID
    )
    assert event["temporal_scope"] == {"session_id": "session-22"}
    assert event["assertion_id"] == GOLDEN_EVENT_ASSERTION_ID
    reloaded = kernel.GraphContribution.model_validate(dumped)
    reloaded_event = next(
        item
        for item in reloaded.accepted_assertions
        if item.assertion_id == GOLDEN_EVENT_ASSERTION_ID
    )
    assert reloaded_event.temporal_scope == {"session_id": "session-22"}


def test_v1_occurrence_envelope_changes_assertion_identity() -> None:
    base = dict(
        assertion_kind="edge",
        subject_node_id="pc:baergrom",
        target_node_id="pc:caelynn",
        predicate="serves",
        label="serves",
        value={"direction": "outbound"},
        campaign_scope="longmont-c2",
        temporal_scope=None,
        epistemic_kind="fact",
        visibility="gm",
    )
    without_time = kernel.compute_assertion_id(**base)
    with_occurrence = kernel.compute_assertion_id(
        **{
            **base,
            "temporal_scope": serialize_temporal_envelope(
                _occurrence_envelope("session-12")
            ),
        }
    )
    with_other_occurrence = kernel.compute_assertion_id(
        **{
            **base,
            "temporal_scope": serialize_temporal_envelope(
                _occurrence_envelope("session-20")
            ),
        }
    )
    assert without_time != with_occurrence
    assert with_occurrence != with_other_occurrence


def test_absence_of_time_remains_valid() -> None:
    assertion = _edge_assertion(temporal_scope=None)
    assert assertion.temporal_scope is None
    assert interpret_temporal_scope(None).format == "none"
    assert temporal_core_semantic_payload(None) is None


def test_kernel_exports_temporal_apis() -> None:
    for name in (
        "TemporalEnvelopeV1",
        "interpret_temporal_scope",
        "serialize_temporal_envelope",
        "temporal_core_semantic_payload",
        "temporal_source_payload",
        "TemporalScopeValidationError",
        "TEMPORAL_ENVELOPE_SCHEMA",
    ):
        assert name in kernel.__all__
        assert hasattr(kernel, name)
