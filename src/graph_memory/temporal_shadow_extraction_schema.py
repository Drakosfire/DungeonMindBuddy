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
TEMPORAL_PROMPT_CALIBRATION_SCHEMA = "dmb_temporal_prompt_calibration_v1"

CalibrationDecision = Literal[
    "PROMPT_READY_FOR_BROADER_SHADOW",
    "ITERATE_PROMPT",
    "BLOCKED_BY_INPUT_REPRESENTATION",
    "BLOCKED_BY_EVIDENCE",
    "BLOCKED_BY_CONTRACT",
    "PROVIDER_FAILURE",
]

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


class CalibrationMetricDistributionV1(_TransportModel):
    min: float
    median: float
    max: float


class CalibrationAssertionStabilityV1(_TransportModel):
    base_assertion_id: str
    classification_counts: dict[str, int] = Field(default_factory=dict)
    status_counts: dict[str, int] = Field(default_factory=dict)
    occurrence_normalized_counts: dict[str, int] = Field(default_factory=dict)
    valid_time_normalized_counts: dict[str, int] = Field(default_factory=dict)
    failure_counts: dict[str, int] = Field(default_factory=dict)


class CalibrationRunRecordV1(_TransportModel):
    """Per-repetition audit row — durable enough to regenerate report slices."""

    prompt_lane: Literal["baseline", "candidate"]
    cohort: Literal["development", "holdout", "adversarial"]
    repetition: int
    succeeded: bool
    case_id: str | None = None
    model_id: str | None = None
    prompt_version: str | None = None
    repository_sha: str | None = None
    run_id: str | None = None
    provider_response_id: str | None = None
    failure_code: str | None = None
    affected_assertion_id: str | None = None
    failure_diagnostics: list[str] = Field(default_factory=list)
    foreign_evidence_attempts: int | None = None
    exact_match_count: int | None = None
    resolved_exact_match_count: int | None = None
    exact_occurrence_match_count: int | None = None
    exact_valid_time_match_count: int | None = None
    status_accuracy: float | None = None
    not_applicable_accuracy: float | None = None
    unsafe_over_resolution_count: int | None = None
    source_to_occurrence_false_positives: int | None = None
    source_to_valid_time_false_positives: int | None = None
    evidence_selection_mismatch_count: int | None = None
    manifest_consistent: bool = True
    manifest_diagnostics: list[str] = Field(default_factory=list)


class CalibrationCohortAggregateV1(_TransportModel):
    prompt_lane: Literal["baseline", "candidate"]
    cohort: Literal["development", "holdout", "adversarial"]
    case_id: str | None = None
    run_count: int = 0
    success_count: int = 0
    failure_count: int = 0
    exact_match: CalibrationMetricDistributionV1 | None = None
    resolved_exact_match: CalibrationMetricDistributionV1 | None = None
    exact_occurrence_match: CalibrationMetricDistributionV1 | None = None
    exact_valid_time_match: CalibrationMetricDistributionV1 | None = None
    min_status_accuracy: float = 0.0
    min_not_applicable_accuracy: float = 0.0
    total_unsafe_over_resolution: int = 0
    total_source_to_occurrence_false_positives: int = 0
    total_source_to_valid_time_false_positives: int = 0
    total_source_leakage_false_positives: int = 0
    total_evidence_selection_mismatches: int = 0
    total_evidence_or_case_failures: int = 0
    total_provider_failures: int = 0
    total_grounding_failures: int = 0
    total_model_output_failures: int = 0
    total_invalid_payloads: int = 0
    total_wrong_temporal_value: int = 0
    total_wrong_temporal_lane: int = 0
    total_status_mismatch: int = 0
    min_exact_match_ratio: float = 0.0
    min_resolved_exact_ratio: float = 0.0
    assertion_stability: list[CalibrationAssertionStabilityV1] = Field(
        default_factory=list
    )
    run_records: list[CalibrationRunRecordV1] = Field(default_factory=list)
    manifest_consistency_ok: bool = True
    manifest_diagnostics: list[str] = Field(default_factory=list)


class TemporalPromptCalibrationMetricsSliceV1(_TransportModel):
    """Per-prompt-lane rollup across cohorts."""

    prompt_lane: Literal["baseline", "candidate"]
    prompt_version: str
    prompt_sha256: str
    case_ids: list[str] = Field(default_factory=list)
    pass_count: int = 0
    partial_count: int = 0
    fail_count: int = 0
    blocked_count: int = 0
    cohort_aggregates: list[CalibrationCohortAggregateV1] = Field(default_factory=list)


CalibrationExperimentRole = Literal["observed_regression", "promotion"]


class CalibrationRunMatrixEntryV1(_TransportModel):
    """One lane/cohort/case identity participating in a calibration aggregate."""

    prompt_lane: Literal["baseline", "candidate"]
    cohort: Literal["development", "holdout", "adversarial"]
    case_id: str


class TemporalPromptCalibrationAggregateV1(_TransportModel):
    """Cross-case prompt calibration aggregate for TL01C."""

    schema_: Literal["dmb_temporal_prompt_calibration_v1"] = Field(
        default=TEMPORAL_PROMPT_CALIBRATION_SCHEMA,
        alias="schema",
    )
    calibration_id: str
    repository_sha: str
    aggregate_build_sha: str
    provider_run_repository_shas: list[str] = Field(default_factory=list)
    holdout_case_sha256: str
    holdout_base_sha256: str
    holdout_gold_sha256: str
    holdout_seal_commit_sha: str
    adversarial_case_sha256: str | None = None
    adversarial_base_sha256: str | None = None
    adversarial_gold_sha256: str | None = None
    adversarial_seal_commit_sha: str | None = None
    seals_verified: bool = False
    baseline_prompt_version: str | None = None
    candidate_prompt_version: str | None = None
    candidate_prompt_sha256: str
    baseline_prompt_sha256: str
    model_id: str
    repetitions: int
    # Optional for frozen pre-TL01D aggregates; new runner always populates these.
    experiment_role: CalibrationExperimentRole | None = None
    run_matrix: list[CalibrationRunMatrixEntryV1] = Field(default_factory=list)
    control_adversarial_enabled: bool = False
    control_adversarial_case_id: str | None = None
    slices: list[TemporalPromptCalibrationMetricsSliceV1] = Field(default_factory=list)
    decision: CalibrationDecision = "ITERATE_PROMPT"
    diagnostics: list[str] = Field(default_factory=list)


__all__ = [
    "CalibrationAssertionStabilityV1",
    "CalibrationCohortAggregateV1",
    "CalibrationDecision",
    "CalibrationExperimentRole",
    "CalibrationMetricDistributionV1",
    "CalibrationRunMatrixEntryV1",
    "CalibrationRunRecordV1",
    "TEMPORAL_MODEL_ANNOTATION_BATCH_SCHEMA",
    "TEMPORAL_PROMPT_CALIBRATION_SCHEMA",
    "TEMPORAL_SHADOW_COMPARISON_SCHEMA",
    "TEMPORAL_SHADOW_EXTRACTION_CASE_SCHEMA",
    "TEMPORAL_SHADOW_EXTRACTION_RUN_SCHEMA",
    "TEMPORAL_SHADOW_PROMPT_VERSION",
    "OccurrenceExtentTransportV1",
    "TemporalModelAnnotationBatchTransportV1",
    "TemporalModelAnnotationTransportV1",
    "TemporalPointTransportV1",
    "TemporalPromptCalibrationAggregateV1",
    "TemporalPromptCalibrationMetricsSliceV1",
    "ValidTimeTransportV1",
    "temporal_model_annotation_batch_json_schema",
    "temporal_model_annotation_batch_text_format",
]
