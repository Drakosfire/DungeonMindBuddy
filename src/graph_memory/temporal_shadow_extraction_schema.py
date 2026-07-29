"""JSON Schema and transport models for TL01B temporal shadow extraction."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from graph_memory.kernel.temporal import (
    TemporalExtentV1,
    TemporalIntervalV1,
    TemporalPointExtentV1,
    TemporalPointV1,
    TemporalRelation,
)

TEMPORAL_SHADOW_EXTRACTION_CASE_SCHEMA = "dmb_temporal_shadow_extraction_case_v1"
TEMPORAL_MODEL_ANNOTATION_BATCH_SCHEMA = "dmb_temporal_model_annotation_batch_v1"
TEMPORAL_SHADOW_COMPARISON_SCHEMA = "dmb_temporal_shadow_comparison_v1"
TEMPORAL_SHADOW_EXTRACTION_RUN_SCHEMA = "dmb_temporal_shadow_extraction_run_v1"
TEMPORAL_SHADOW_PROMPT_VERSION = "tl01b-v1"

InterpretationStatusTransport = Literal[
    "resolved",
    "ambiguous",
    "unresolved",
    "not_applicable",
]
ExtractionConfidenceTransport = Literal["high", "medium", "low", "unknown"]
TemporalPointKindTransport = Literal[
    "session",
    "campaign_date",
    "relative",
    "textual",
    "unknown",
]
TemporalCertaintyTransport = Literal[
    "explicit",
    "inferred",
    "approximate",
    "unknown",
]
TemporalRelationTransport = Literal["before", "after", "during", "at"]


def _nullable_string() -> dict[str, Any]:
    return {"type": ["string", "null"]}


def _temporal_point_transport_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "kind": {
                "type": "string",
                "enum": list(TemporalPointKindTransport.__args__),  # type: ignore[attr-defined]
            },
            "session_id": _nullable_string(),
            "campaign_id": _nullable_string(),
            "calendar_id": _nullable_string(),
            "value": _nullable_string(),
            "relation": {
                "type": ["string", "null"],
                "enum": [*(TemporalRelationTransport.__args__), None],  # type: ignore[attr-defined]
            },
            "anchor_ref": _nullable_string(),
            "raw_expression": _nullable_string(),
            "certainty": {
                "type": "string",
                "enum": list(TemporalCertaintyTransport.__args__),  # type: ignore[attr-defined]
            },
        },
        "required": [
            "kind",
            "session_id",
            "campaign_id",
            "calendar_id",
            "value",
            "relation",
            "anchor_ref",
            "raw_expression",
            "certainty",
        ],
    }


def _nullable_point_schema() -> dict[str, Any]:
    point = _temporal_point_transport_schema()
    return {
        "type": ["object", "null"],
        "additionalProperties": False,
        "properties": point["properties"],
        "required": point["required"],
    }


def _occurrence_extent_transport_schema() -> dict[str, Any]:
    nullable_point = _nullable_point_schema()
    return {
        "type": ["object", "null"],
        "additionalProperties": False,
        "properties": {
            "kind": {"type": "string", "enum": ["point", "interval"]},
            "point": nullable_point,
            "start": nullable_point,
            "end": nullable_point,
            "raw_expression": _nullable_string(),
        },
        "required": ["kind", "point", "start", "end", "raw_expression"],
    }


def _valid_time_transport_schema() -> dict[str, Any]:
    nullable_point = _nullable_point_schema()
    return {
        "type": ["object", "null"],
        "additionalProperties": False,
        "properties": {
            "start": nullable_point,
            "end": nullable_point,
            "raw_expression": _nullable_string(),
        },
        "required": ["start", "end", "raw_expression"],
    }


def _model_annotation_transport_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "base_assertion_id": {"type": "string", "minLength": 1},
            "interpretation_status": {
                "type": "string",
                "enum": list(InterpretationStatusTransport.__args__),  # type: ignore[attr-defined]
            },
            "occurrence_time": _occurrence_extent_transport_schema(),
            "valid_time": _valid_time_transport_schema(),
            "evidence_ref_ids": {
                "type": "array",
                "items": {"type": "string", "minLength": 1},
            },
            "source_phrase": _nullable_string(),
            "extraction_confidence": {
                "type": "string",
                "enum": list(ExtractionConfidenceTransport.__args__),  # type: ignore[attr-defined]
            },
            "diagnostics": {
                "type": "array",
                "items": {"type": "string"},
            },
        },
        "required": [
            "base_assertion_id",
            "interpretation_status",
            "occurrence_time",
            "valid_time",
            "evidence_ref_ids",
            "source_phrase",
            "extraction_confidence",
            "diagnostics",
        ],
    }


def temporal_model_annotation_batch_json_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "schema": {
                "type": "string",
                "enum": [TEMPORAL_MODEL_ANNOTATION_BATCH_SCHEMA],
            },
            "annotations": {
                "type": "array",
                "items": _model_annotation_transport_schema(),
            },
        },
        "required": ["schema", "annotations"],
    }


def temporal_model_annotation_batch_text_format(*, strict: bool = True) -> dict[str, Any]:
    return {
        "format": {
            "type": "json_schema",
            "name": TEMPORAL_MODEL_ANNOTATION_BATCH_SCHEMA,
            "strict": strict,
            "schema": temporal_model_annotation_batch_json_schema(),
        }
    }


class _TransportModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, populate_by_name=True)


class TemporalPointTransportV1(_TransportModel):
    kind: TemporalPointKindTransport
    session_id: str | None = None
    campaign_id: str | None = None
    calendar_id: str | None = None
    value: str | None = None
    relation: TemporalRelationTransport | None = None
    anchor_ref: str | None = None
    raw_expression: str | None = None
    certainty: TemporalCertaintyTransport

    def to_temporal_point_v1(self) -> TemporalPointV1:
        return TemporalPointV1(
            kind=self.kind,  # type: ignore[arg-type]
            session_id=self.session_id,
            campaign_id=self.campaign_id,
            calendar_id=self.calendar_id,
            value=self.value,
            relation=self.relation,
            anchor_ref=self.anchor_ref,
            raw_expression=self.raw_expression,
            certainty=self.certainty,
        )


class OccurrenceExtentTransportV1(_TransportModel):
    kind: Literal["point", "interval"]
    point: TemporalPointTransportV1 | None = None
    start: TemporalPointTransportV1 | None = None
    end: TemporalPointTransportV1 | None = None
    raw_expression: str | None = None

    def to_temporal_extent_v1(self) -> TemporalExtentV1:
        if self.kind == "point":
            if self.point is None:
                raise ValueError('occurrence kind="point" requires point')
            return TemporalPointExtentV1(
                kind="point",
                point=self.point.to_temporal_point_v1(),
            )
        from graph_memory.kernel.temporal import TemporalIntervalExtentV1

        return TemporalIntervalExtentV1(
            kind="interval",
            start=self.start.to_temporal_point_v1() if self.start else None,
            end=self.end.to_temporal_point_v1() if self.end else None,
            raw_expression=self.raw_expression,
        )


class ValidTimeTransportV1(_TransportModel):
    start: TemporalPointTransportV1 | None = None
    end: TemporalPointTransportV1 | None = None
    raw_expression: str | None = None

    def to_temporal_interval_v1(self) -> TemporalIntervalV1:
        return TemporalIntervalV1(
            start=self.start.to_temporal_point_v1() if self.start else None,
            end=self.end.to_temporal_point_v1() if self.end else None,
            raw_expression=self.raw_expression,
        )


class TemporalModelAnnotationTransportV1(_TransportModel):
    base_assertion_id: str
    interpretation_status: InterpretationStatusTransport
    occurrence_time: OccurrenceExtentTransportV1 | None = None
    valid_time: ValidTimeTransportV1 | None = None
    evidence_ref_ids: list[str] = Field(default_factory=list)
    source_phrase: str | None = None
    extraction_confidence: ExtractionConfidenceTransport = "unknown"
    diagnostics: list[str] = Field(default_factory=list)


class TemporalModelAnnotationBatchTransportV1(_TransportModel):
    schema_: Literal["dmb_temporal_model_annotation_batch_v1"] = Field(
        default=TEMPORAL_MODEL_ANNOTATION_BATCH_SCHEMA,
        alias="schema",
    )
    annotations: list[TemporalModelAnnotationTransportV1] = Field(default_factory=list)

    @field_validator("annotations", mode="after")
    @classmethod
    def _non_empty(cls, value: list[TemporalModelAnnotationTransportV1]) -> list:
        if not value:
            raise ValueError("annotations must be non-empty")
        return value


__all__ = [
    "TEMPORAL_MODEL_ANNOTATION_BATCH_SCHEMA",
    "TEMPORAL_SHADOW_COMPARISON_SCHEMA",
    "TEMPORAL_SHADOW_EXTRACTION_CASE_SCHEMA",
    "TEMPORAL_SHADOW_EXTRACTION_RUN_SCHEMA",
    "TEMPORAL_SHADOW_PROMPT_VERSION",
    "OccurrenceExtentTransportV1",
    "TemporalModelAnnotationBatchTransportV1",
    "TemporalModelAnnotationTransportV1",
    "TemporalPointTransportV1",
    "ValidTimeTransportV1",
    "temporal_model_annotation_batch_json_schema",
    "temporal_model_annotation_batch_text_format",
]
