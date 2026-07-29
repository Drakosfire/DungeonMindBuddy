"""Typed temporal envelope and legacy temporal_scope interpretation (TL00).

Authority: interpret ``GraphContributionAssertion.temporal_scope`` without
mutating the durable assertion or changing assertion identity.

Transaction / revision time is intentionally outside this envelope — graph
revision and contribution metadata already own when DungeonBuddy recorded or
changed an interpretation.
"""

from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    field_validator,
    model_validator,
)

TEMPORAL_ENVELOPE_SCHEMA = "dmb_temporal_envelope_v1"

TemporalPointKind = Literal[
    "unknown",
    "session",
    "campaign_date",
    "relative",
    "textual",
]

TemporalCertainty = Literal[
    "explicit",
    "inferred",
    "approximate",
    "unknown",
]

TemporalRelation = Literal[
    "before",
    "after",
    "during",
    "at",
]

TemporalScopeFormat = Literal[
    "none",
    "legacy_session_observation",
    "legacy_unresolved",
    "temporal_envelope_v1",
]

_OPTIONAL_POINT_STRING_FIELDS = (
    "campaign_id",
    "session_id",
    "calendar_id",
    "value",
    "anchor_ref",
    "raw_expression",
)


class TemporalScopeValidationError(ValueError):
    """Stable typed failure for malformed schema-tagged TemporalEnvelopeV1."""

    def __init__(self, message: str, *, diagnostics: list[str] | None = None) -> None:
        super().__init__(message)
        self.diagnostics = list(diagnostics or [message])


class _TemporalModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        strict=True,
        populate_by_name=True,
    )


def _reject_blank_optional_string(value: str | None) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise TypeError("optional temporal string fields must be str or null")
    stripped = value.strip()
    if not stripped:
        raise ValueError("blank temporal string fields are forbidden")
    return stripped


class TemporalPointV1(_TemporalModel):
    """Constrained point/anchor that preserves exact and incomplete fictional time."""

    kind: TemporalPointKind
    campaign_id: str | None = None
    session_id: str | None = None
    calendar_id: str | None = None
    value: str | None = None
    relation: TemporalRelation | None = None
    anchor_ref: str | None = None
    raw_expression: str | None = None
    certainty: TemporalCertainty

    @field_validator(*_OPTIONAL_POINT_STRING_FIELDS, mode="before")
    @classmethod
    def _no_blank_strings(cls, value: Any) -> Any:
        if value is None:
            return None
        return _reject_blank_optional_string(value if isinstance(value, str) else value)

    @model_validator(mode="after")
    def _validate_kind_requirements(self) -> TemporalPointV1:
        kind = self.kind
        if kind == "session":
            if self.session_id is None:
                raise ValueError('kind="session" requires session_id')
        elif kind == "campaign_date":
            if self.value is None:
                raise ValueError('kind="campaign_date" requires value')
        elif kind == "relative":
            has_structured = self.relation is not None and self.anchor_ref is not None
            has_raw = self.raw_expression is not None
            if not has_structured and not has_raw:
                raise ValueError(
                    'kind="relative" requires relation+anchor_ref or raw_expression'
                )
        elif kind == "textual":
            if self.raw_expression is None:
                raise ValueError('kind="textual" requires raw_expression')
        elif kind == "unknown":
            if self.session_id is not None or self.value is not None:
                raise ValueError(
                    'kind="unknown" must not invent session_id or campaign_date value'
                )
            if self.calendar_id is not None:
                raise ValueError('kind="unknown" must not invent calendar_id')
        return self


class TemporalIntervalV1(_TemporalModel):
    """Valid-time or occurrence interval without cross-system ordering checks."""

    start: TemporalPointV1 | None = None
    end: TemporalPointV1 | None = None
    raw_expression: str | None = None

    @field_validator("raw_expression", mode="before")
    @classmethod
    def _no_blank_raw(cls, value: Any) -> Any:
        if value is None:
            return None
        return _reject_blank_optional_string(value if isinstance(value, str) else value)

    @model_validator(mode="after")
    def _require_at_least_one_anchor(self) -> TemporalIntervalV1:
        if self.start is None and self.end is None and self.raw_expression is None:
            raise ValueError(
                "TemporalIntervalV1 requires at least one of start, end, raw_expression"
            )
        return self


class TemporalPointExtentV1(_TemporalModel):
    kind: Literal["point"] = "point"
    point: TemporalPointV1


class TemporalIntervalExtentV1(_TemporalModel):
    kind: Literal["interval"] = "interval"
    start: TemporalPointV1 | None = None
    end: TemporalPointV1 | None = None
    raw_expression: str | None = None

    @field_validator("raw_expression", mode="before")
    @classmethod
    def _no_blank_raw(cls, value: Any) -> Any:
        if value is None:
            return None
        return _reject_blank_optional_string(value if isinstance(value, str) else value)

    @model_validator(mode="after")
    def _require_at_least_one_anchor(self) -> TemporalIntervalExtentV1:
        if self.start is None and self.end is None and self.raw_expression is None:
            raise ValueError(
                "interval extent requires at least one of start, end, raw_expression"
            )
        return self


TemporalExtentV1 = Annotated[
    TemporalPointExtentV1 | TemporalIntervalExtentV1,
    Field(discriminator="kind"),
]


class TemporalEnvelopeV1(_TemporalModel):
    """Canonical typed temporal carrier for Graph V1 assertions (TL00).

    Distinguishes source_time (provenance), occurrence_time (when fiction
    happened), and valid_time (when a state/relationship was true). Does not
    include transaction/revision time.
    """

    schema_: Literal["dmb_temporal_envelope_v1"] = Field(
        default=TEMPORAL_ENVELOPE_SCHEMA,
        alias="schema",
    )
    source_time: TemporalPointV1 | None = None
    occurrence_time: TemporalExtentV1 | None = None
    valid_time: TemporalIntervalV1 | None = None

    @model_validator(mode="after")
    def _require_at_least_one_lane(self) -> TemporalEnvelopeV1:
        if (
            self.source_time is None
            and self.occurrence_time is None
            and self.valid_time is None
        ):
            raise ValueError(
                "TemporalEnvelopeV1 requires at least one of "
                "source_time, occurrence_time, valid_time"
            )
        return self


class TemporalScopeInterpretationV1(_TemporalModel):
    format: TemporalScopeFormat
    envelope: TemporalEnvelopeV1 | None = None
    unresolved_legacy_fields: dict[str, Any] = Field(default_factory=dict)
    diagnostics: list[str] = Field(default_factory=list)


def _session_source_point(session_id: str) -> TemporalPointV1:
    return TemporalPointV1(
        kind="session",
        session_id=session_id,
        certainty="explicit",
    )


def _legacy_session_envelope(session_id: str) -> TemporalEnvelopeV1:
    return TemporalEnvelopeV1(
        schema_=TEMPORAL_ENVELOPE_SCHEMA,
        source_time=_session_source_point(session_id),
        occurrence_time=None,
        valid_time=None,
    )


def _parse_envelope_v1(payload: dict[str, Any]) -> TemporalEnvelopeV1:
    try:
        return TemporalEnvelopeV1.model_validate(payload)
    except ValidationError as exc:
        diagnostics = [f"{'.'.join(str(p) for p in err['loc'])}: {err['msg']}" for err in exc.errors()]
        raise TemporalScopeValidationError(
            "Malformed dmb_temporal_envelope_v1 payload",
            diagnostics=diagnostics or [str(exc)],
        ) from exc
    except (TypeError, ValueError) as exc:
        raise TemporalScopeValidationError(
            "Malformed dmb_temporal_envelope_v1 payload",
            diagnostics=[str(exc)],
        ) from exc


def interpret_temporal_scope(
    temporal_scope: dict[str, Any] | None,
) -> TemporalScopeInterpretationV1:
    """Canonical typed interpretation of a durable temporal_scope dict.

    Does not mutate the input. Never infers occurrence_time or valid_time from
    a legacy session observation stamp.
    """
    if temporal_scope is None:
        return TemporalScopeInterpretationV1(
            format="none",
            envelope=None,
            unresolved_legacy_fields={},
            diagnostics=[],
        )

    if not isinstance(temporal_scope, dict):
        raise TypeError("temporal_scope must be a dict or None")

    raw = dict(temporal_scope)
    schema_tag = raw.get("schema")

    if schema_tag == TEMPORAL_ENVELOPE_SCHEMA:
        envelope = _parse_envelope_v1(raw)
        return TemporalScopeInterpretationV1(
            format="temporal_envelope_v1",
            envelope=envelope,
            unresolved_legacy_fields={},
            diagnostics=[],
        )

    if schema_tag is not None:
        # Explicit but unrecognized schema tag — preserve, do not claim V1.
        return TemporalScopeInterpretationV1(
            format="legacy_unresolved",
            envelope=None,
            unresolved_legacy_fields=raw,
            diagnostics=[
                f"unrecognized temporal schema tag {schema_tag!r}; "
                "preserved as unresolved legacy"
            ],
        )

    keys = set(raw.keys())
    session_id = raw.get("session_id")
    if keys == {"session_id"} and isinstance(session_id, str) and session_id.strip():
        return TemporalScopeInterpretationV1(
            format="legacy_session_observation",
            envelope=_legacy_session_envelope(session_id.strip()),
            unresolved_legacy_fields={},
            diagnostics=[],
        )

    if (
        "session_id" in raw
        and isinstance(session_id, str)
        and session_id.strip()
        and keys - {"session_id"}
    ):
        unresolved = {key: value for key, value in raw.items() if key != "session_id"}
        return TemporalScopeInterpretationV1(
            format="legacy_unresolved",
            envelope=_legacy_session_envelope(session_id.strip()),
            unresolved_legacy_fields=unresolved,
            diagnostics=[
                "legacy temporal_scope contains session_id plus unresolved "
                f"qualifiers: {sorted(unresolved.keys())!r}"
            ],
        )

    return TemporalScopeInterpretationV1(
        format="legacy_unresolved",
        envelope=None,
        unresolved_legacy_fields=raw,
        diagnostics=["unrecognized legacy temporal_scope shape; preserved unresolved"],
    )


def serialize_temporal_envelope(envelope: TemporalEnvelopeV1) -> dict[str, Any]:
    """Emit a deterministic JSON-compatible V1 envelope dict.

    Serialization rule: the three top-level temporal lanes retain explicit
    nulls (matches the canonical envelope shape). Nested models omit None
    fields. Never emits legacy ``{"session_id": ...}`` shorthand.
    """
    def _dump_point(point: TemporalPointV1) -> dict[str, Any]:
        return point.model_dump(mode="json", exclude_none=True)

    def _dump_interval(interval: TemporalIntervalV1) -> dict[str, Any]:
        payload: dict[str, Any] = {}
        if interval.start is not None:
            payload["start"] = _dump_point(interval.start)
        if interval.end is not None:
            payload["end"] = _dump_point(interval.end)
        if interval.raw_expression is not None:
            payload["raw_expression"] = interval.raw_expression
        return payload

    def _dump_extent(extent: TemporalExtentV1) -> dict[str, Any]:
        if isinstance(extent, TemporalPointExtentV1):
            return {"kind": "point", "point": _dump_point(extent.point)}
        payload: dict[str, Any] = {"kind": "interval"}
        if extent.start is not None:
            payload["start"] = _dump_point(extent.start)
        if extent.end is not None:
            payload["end"] = _dump_point(extent.end)
        if extent.raw_expression is not None:
            payload["raw_expression"] = extent.raw_expression
        return payload

    return {
        "schema": TEMPORAL_ENVELOPE_SCHEMA,
        "source_time": (
            _dump_point(envelope.source_time) if envelope.source_time is not None else None
        ),
        "occurrence_time": (
            _dump_extent(envelope.occurrence_time)
            if envelope.occurrence_time is not None
            else None
        ),
        "valid_time": (
            _dump_interval(envelope.valid_time) if envelope.valid_time is not None else None
        ),
    }


def temporal_source_payload(
    temporal_scope: dict[str, Any] | None,
) -> dict[str, Any] | None:
    """Return provenance-facing source_time only (never occurrence/valid)."""
    interpretation = interpret_temporal_scope(temporal_scope)
    if interpretation.envelope is None or interpretation.envelope.source_time is None:
        return None
    return {
        "source_time": serialize_temporal_envelope(interpretation.envelope)["source_time"]
    }


def temporal_core_semantic_payload(
    temporal_scope: dict[str, Any] | None,
) -> dict[str, Any] | None:
    """Return correction-sensitive temporal payload for projection fingerprints.

    For V1 envelopes: occurrence_time and valid_time only (source_time excluded).
    For legacy dictionaries: remove top-level session_id; preserve every other
    legacy field exactly; return None when nothing remains.
    """
    if temporal_scope is None:
        return None

    if not isinstance(temporal_scope, dict):
        raise TypeError("temporal_scope must be a dict or None")

    raw = dict(temporal_scope)
    if raw.get("schema") == TEMPORAL_ENVELOPE_SCHEMA:
        # Strict parse — malformed V1 must not silently participate as legacy.
        envelope = _parse_envelope_v1(raw)
        serialized = serialize_temporal_envelope(envelope)
        payload: dict[str, Any] = {}
        if serialized["occurrence_time"] is not None:
            payload["occurrence_time"] = serialized["occurrence_time"]
        if serialized["valid_time"] is not None:
            payload["valid_time"] = serialized["valid_time"]
        return payload or None

    # Legacy (including unrecognized schema tags): strip observation session only.
    remaining = {key: value for key, value in raw.items() if key != "session_id"}
    return remaining or None


__all__ = [
    "TEMPORAL_ENVELOPE_SCHEMA",
    "TemporalCertainty",
    "TemporalEnvelopeV1",
    "TemporalExtentV1",
    "TemporalIntervalExtentV1",
    "TemporalIntervalV1",
    "TemporalPointExtentV1",
    "TemporalPointKind",
    "TemporalPointV1",
    "TemporalRelation",
    "TemporalScopeFormat",
    "TemporalScopeInterpretationV1",
    "TemporalScopeValidationError",
    "interpret_temporal_scope",
    "serialize_temporal_envelope",
    "temporal_core_semantic_payload",
    "temporal_source_payload",
]
