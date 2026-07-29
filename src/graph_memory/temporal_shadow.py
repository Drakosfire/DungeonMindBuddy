"""Temporal annotation overlay and deterministic shadow preview (TL01).

Non-authoritative evaluation seam: overlays and shadow previews never write
GraphContribution records, never merge, and never publish graph revisions.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    field_validator,
    model_validator,
)
from pydantic_core import PydanticSerializationError

from graph_memory.kernel.contribution_models import (
    GraphContribution,
    GraphContributionAssertion,
)
from graph_memory.kernel.contributions import (
    compute_assertion_id,
    compute_contribution_source_payload_sha256,
    explicit_assertion_evidence_ref_ids,
)
from graph_memory.kernel.temporal import (
    TEMPORAL_ENVELOPE_SCHEMA,
    TemporalEnvelopeV1,
    TemporalExtentV1,
    TemporalIntervalV1,
    TemporalPointExtentV1,
    TemporalPointV1,
    TemporalScopeValidationError,
    interpret_temporal_scope,
    serialize_temporal_envelope,
    temporal_core_semantic_payload,
)

TEMPORAL_ANNOTATION_OVERLAY_SCHEMA = "dmb_temporal_annotation_overlay_v1"
TEMPORAL_SHADOW_PREVIEW_SCHEMA = "dmb_temporal_shadow_preview_v1"

OverlayProducerKind = Literal["human_gold", "fixture", "model_shadow"]
InterpretationStatus = Literal[
    "resolved",
    "ambiguous",
    "unresolved",
    "not_applicable",
]
ShadowVerdict = Literal["complete", "partial", "failed"]
ShadowRowStatus = Literal["ok", "skipped", "error"]
ExtractionConfidence = Literal["high", "medium", "low", "unknown"]
SourceTimeDerivation = Literal[
    "legacy_session_scope",
    "existing_v1_source_time",
    "evidence_session",
    "none",
    "skipped",
]


class TemporalShadowBuildError(Exception):
    """Stable typed failure for overlay binding / shadow composition."""

    def __init__(
        self,
        message: str,
        *,
        code: str,
        affected_assertion_id: str | None = None,
        diagnostics: list[str] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.affected_assertion_id = affected_assertion_id
        self.diagnostics = list(diagnostics or [message])


class _ShadowModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        strict=True,
        populate_by_name=True,
    )


def _reject_blank(value: str) -> str:
    if not isinstance(value, str):
        raise TypeError("expected string")
    stripped = value.strip()
    if not stripped:
        raise ValueError("blank strings are forbidden")
    return stripped


class TemporalOverlayProducerV1(_ShadowModel):
    kind: OverlayProducerKind
    name: str
    version: str

    @field_validator("name", "version", mode="before")
    @classmethod
    def _no_blank(cls, value: Any) -> Any:
        if value is None:
            raise ValueError("producer fields are required")
        return _reject_blank(value if isinstance(value, str) else value)


class TemporalAssertionAnnotationV1(_ShadowModel):
    annotation_id: str
    base_assertion_id: str
    interpretation_status: InterpretationStatus
    occurrence_time: TemporalExtentV1 | None = None
    valid_time: TemporalIntervalV1 | None = None
    evidence_ref_ids: list[str] = Field(default_factory=list)
    source_phrase: str | None = None
    extraction_confidence: ExtractionConfidence = "unknown"
    diagnostics: list[str] = Field(default_factory=list)

    @field_validator("annotation_id", "base_assertion_id", mode="before")
    @classmethod
    def _ids_nonblank(cls, value: Any) -> Any:
        return _reject_blank(value if isinstance(value, str) else value)

    @field_validator("source_phrase", mode="before")
    @classmethod
    def _phrase_not_blank(cls, value: Any) -> Any:
        if value is None:
            return None
        return _reject_blank(value if isinstance(value, str) else value)

    @field_validator("evidence_ref_ids", mode="after")
    @classmethod
    def _evidence_nonempty_and_unique(cls, value: list[str]) -> list[str]:
        cleaned = [_reject_blank(item) for item in value]
        if not cleaned:
            raise ValueError("annotations require at least one evidence_ref_id")
        if len(set(cleaned)) != len(cleaned):
            raise ValueError("annotation evidence_ref_ids must be unique")
        return cleaned

    @field_validator("diagnostics", mode="after")
    @classmethod
    def _diagnostics_trimmed_nonblank(cls, value: list[str]) -> list[str]:
        cleaned: list[str] = []
        for item in value:
            if not isinstance(item, str):
                raise TypeError("diagnostics entries must be strings")
            stripped = item.strip()
            if not stripped:
                raise ValueError("diagnostics entries must be non-blank after trim")
            cleaned.append(stripped)
        return cleaned

    @model_validator(mode="after")
    def _status_constraints(self) -> TemporalAssertionAnnotationV1:
        status = self.interpretation_status
        has_semantic = self.occurrence_time is not None or self.valid_time is not None
        if status == "resolved":
            if not has_semantic:
                raise ValueError(
                    'interpretation_status="resolved" requires occurrence_time '
                    "and/or valid_time"
                )
        elif status in {"ambiguous", "unresolved", "not_applicable"}:
            if has_semantic:
                raise ValueError(
                    f"interpretation_status={status!r} must not include "
                    "occurrence_time or valid_time"
                )
            if status == "ambiguous":
                if self.source_phrase is None:
                    raise ValueError(
                        'interpretation_status="ambiguous" requires source_phrase'
                    )
                if not self.diagnostics:
                    raise ValueError(
                        'interpretation_status="ambiguous" requires diagnostics'
                    )
            elif status == "unresolved":
                if self.source_phrase is None and not self.diagnostics:
                    raise ValueError(
                        'interpretation_status="unresolved" requires source_phrase '
                        "or diagnostics"
                    )
        return self


class TemporalAnnotationOverlayV1(_ShadowModel):
    schema_: Literal["dmb_temporal_annotation_overlay_v1"] = Field(
        default=TEMPORAL_ANNOTATION_OVERLAY_SCHEMA,
        alias="schema",
    )
    overlay_id: str
    base_contribution_id: str
    base_contribution_source_payload_sha256: str
    producer: TemporalOverlayProducerV1
    annotations: list[TemporalAssertionAnnotationV1] = Field(default_factory=list)

    @field_validator(
        "overlay_id",
        "base_contribution_id",
        "base_contribution_source_payload_sha256",
        mode="before",
    )
    @classmethod
    def _required_ids(cls, value: Any) -> Any:
        return _reject_blank(value if isinstance(value, str) else value)

    @model_validator(mode="after")
    def _validate_overlay_identity(self) -> TemporalAnnotationOverlayV1:
        seen_targets: set[str] = set()
        seen_annotation_ids: set[str] = set()
        for annotation in self.annotations:
            if annotation.base_assertion_id in seen_targets:
                raise ValueError(
                    "duplicate annotation target "
                    f"{annotation.base_assertion_id!r}"
                )
            seen_targets.add(annotation.base_assertion_id)
            if annotation.annotation_id in seen_annotation_ids:
                raise ValueError(
                    f"duplicate annotation_id {annotation.annotation_id!r}"
                )
            seen_annotation_ids.add(annotation.annotation_id)

        expected = compute_temporal_overlay_id(
            base_contribution_id=self.base_contribution_id,
            base_contribution_source_payload_sha256=(
                self.base_contribution_source_payload_sha256
            ),
            producer=self.producer,
            annotations=self.annotations,
        )
        if self.overlay_id != expected:
            raise ValueError(
                f"invalid_overlay_id: supplied {self.overlay_id!r} "
                f"does not match canonical {expected!r}"
            )
        return self


class TemporalShadowSummaryV1(_ShadowModel):
    total_candidate_assertions: int
    annotated_assertions: int
    resolved_annotations: int
    ambiguous_annotations: int
    unresolved_annotations: int
    not_applicable_annotations: int
    unannotated_assertions: int
    source_time_derived: int
    identity_changed_count: int
    core_temporal_changed_count: int
    unchanged_count: int
    skipped_count: int
    error_count: int


class TemporalShadowRowV1(_ShadowModel):
    base_assertion_id: str
    shadow_assertion_id: str | None
    assertion_kind: str
    subject_node_id: str | None
    target_node_id: str | None
    predicate: str | None
    label: str | None
    interpretation_status: InterpretationStatus | None
    annotation_id: str | None
    annotation_evidence_ref_ids: list[str] = Field(default_factory=list)
    source_time_derivation: SourceTimeDerivation
    base_temporal_scope: dict[str, Any] | None
    shadow_temporal_scope: dict[str, Any] | None
    identity_changed: bool
    base_core_temporal_payload: dict[str, Any] | None
    shadow_core_temporal_payload: dict[str, Any] | None
    core_temporal_changed: bool
    status: ShadowRowStatus
    diagnostics: list[str] = Field(default_factory=list)


class TemporalShadowPreviewV1(_ShadowModel):
    schema_: Literal["dmb_temporal_shadow_preview_v1"] = Field(
        default=TEMPORAL_SHADOW_PREVIEW_SCHEMA,
        alias="schema",
    )
    overlay_id: str
    base_contribution_id: str
    base_contribution_source_payload_sha256: str
    verdict: ShadowVerdict
    summary: TemporalShadowSummaryV1
    rows: list[TemporalShadowRowV1] = Field(default_factory=list)


def _canonical_json(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _extent_dump(extent: TemporalExtentV1) -> dict[str, Any]:
    if isinstance(extent, TemporalPointExtentV1):
        return {
            "kind": "point",
            "point": extent.point.model_dump(mode="json", exclude_none=True),
        }
    payload: dict[str, Any] = {"kind": "interval"}
    if extent.start is not None:
        payload["start"] = extent.start.model_dump(mode="json", exclude_none=True)
    if extent.end is not None:
        payload["end"] = extent.end.model_dump(mode="json", exclude_none=True)
    if extent.raw_expression is not None:
        payload["raw_expression"] = extent.raw_expression
    return payload


def _interval_dump(interval: TemporalIntervalV1) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    if interval.start is not None:
        payload["start"] = interval.start.model_dump(mode="json", exclude_none=True)
    if interval.end is not None:
        payload["end"] = interval.end.model_dump(mode="json", exclude_none=True)
    if interval.raw_expression is not None:
        payload["raw_expression"] = interval.raw_expression
    return payload


def _annotation_canonical_payload(
    annotation: TemporalAssertionAnnotationV1,
) -> dict[str, Any]:
    return {
        "annotation_id": annotation.annotation_id,
        "base_assertion_id": annotation.base_assertion_id,
        "diagnostics": list(annotation.diagnostics),
        "evidence_ref_ids": list(annotation.evidence_ref_ids),
        "extraction_confidence": annotation.extraction_confidence,
        "interpretation_status": annotation.interpretation_status,
        "occurrence_time": (
            _extent_dump(annotation.occurrence_time)
            if annotation.occurrence_time is not None
            else None
        ),
        "source_phrase": annotation.source_phrase,
        "valid_time": (
            _interval_dump(annotation.valid_time)
            if annotation.valid_time is not None
            else None
        ),
    }


def compute_temporal_overlay_id(
    *,
    base_contribution_id: str,
    base_contribution_source_payload_sha256: str,
    producer: TemporalOverlayProducerV1,
    annotations: list[TemporalAssertionAnnotationV1],
) -> str:
    """Deterministic overlay ID from canonical overlay content (no path/time)."""
    ordered = sorted(annotations, key=lambda item: item.base_assertion_id)
    payload = {
        "annotations": [_annotation_canonical_payload(item) for item in ordered],
        "base_contribution_id": base_contribution_id,
        "base_contribution_source_payload_sha256": (
            base_contribution_source_payload_sha256
        ),
        "producer": {
            "kind": producer.kind,
            "name": producer.name,
            "version": producer.version,
        },
        "schema": TEMPORAL_ANNOTATION_OVERLAY_SCHEMA,
    }
    digest = hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()[:16]
    return f"temporal-overlay:{digest}"


def load_temporal_annotation_overlay(
    payload: dict[str, Any] | TemporalAnnotationOverlayV1,
) -> TemporalAnnotationOverlayV1:
    """Parse and revalidate a TemporalAnnotationOverlayV1 payload.

    Always re-runs model validation — including when the caller already holds a
    ``TemporalAnnotationOverlayV1`` instance — so mutated models or
    ``model_copy(update=...)`` results cannot bypass overlay-ID, duplicate-
    target, evidence, or status checks.

    Instance serialization and validation failures both surface as
    ``TemporalShadowBuildError`` (never raw Pydantic serialization exceptions).
    """
    try:
        if isinstance(payload, TemporalAnnotationOverlayV1):
            payload = payload.model_dump(mode="json", by_alias=True)
        return TemporalAnnotationOverlayV1.model_validate(payload)
    except PydanticSerializationError as exc:
        raise TemporalShadowBuildError(
            "Invalid temporal annotation overlay",
            code="invalid_temporal_annotation",
            diagnostics=[f"overlay serialization failed: {exc}"],
        ) from exc
    except ValidationError as exc:
        diagnostics = [
            f"{'.'.join(str(p) for p in err['loc'])}: {err['msg']}"
            for err in exc.errors()
        ]
        joined = " ".join(diagnostics)
        code = (
            "invalid_overlay_id"
            if "invalid_overlay_id" in joined
            else "invalid_temporal_annotation"
        )
        raise TemporalShadowBuildError(
            "Invalid temporal annotation overlay",
            code=code,
            diagnostics=diagnostics or [str(exc)],
        ) from exc
    except (TypeError, ValueError) as exc:
        message = str(exc)
        code = (
            "invalid_overlay_id"
            if "invalid_overlay_id" in message
            else "invalid_temporal_annotation"
        )
        raise TemporalShadowBuildError(
            message,
            code=code,
            diagnostics=[message],
        ) from exc


def _collect_evidence_session_ids(
    assertion: GraphContributionAssertion,
) -> list[str]:
    """Collect unique non-blank session_id values from embedded provenance."""
    sessions: list[str] = []
    seen: set[str] = set()
    value = dict(assertion.value or {})

    def _add(raw: Any) -> None:
        if not isinstance(raw, str):
            return
        cleaned = raw.strip()
        if not cleaned or cleaned in seen:
            return
        seen.add(cleaned)
        sessions.append(cleaned)

    for entry in value.get("evidence") or []:
        if isinstance(entry, dict):
            _add(entry.get("session_id"))
    for entry in value.get("source_artifacts") or []:
        if isinstance(entry, dict):
            _add(entry.get("session_id"))
    return sessions


def derive_assertion_source_time(
    assertion: GraphContributionAssertion,
) -> tuple[TemporalPointV1 | None, SourceTimeDerivation, list[str]]:
    """Derive V1 source_time without inventing occurrence/valid time."""
    diagnostics: list[str] = []
    evidence_sessions = _collect_evidence_session_ids(assertion)
    campaign_id = assertion.campaign_scope

    try:
        interpretation = interpret_temporal_scope(assertion.temporal_scope)
    except TemporalScopeValidationError as exc:
        raise TemporalShadowBuildError(
            "Malformed durable temporal_scope on base assertion",
            code="invalid_temporal_annotation",
            affected_assertion_id=assertion.assertion_id,
            diagnostics=list(exc.diagnostics),
        ) from exc

    if interpretation.format == "legacy_unresolved" and interpretation.envelope is None:
        schema_tag = None
        if isinstance(assertion.temporal_scope, dict):
            schema_tag = assertion.temporal_scope.get("schema")
        if schema_tag is not None and schema_tag != TEMPORAL_ENVELOPE_SCHEMA:
            return None, "skipped", [
                "skipped_unrecognized_temporal_schema",
                *interpretation.diagnostics,
            ]
        return None, "skipped", [
            "skipped_existing_unresolved_temporal_scope",
            *interpretation.diagnostics,
        ]

    if interpretation.format == "legacy_unresolved" and interpretation.envelope is not None:
        return None, "skipped", [
            "skipped_existing_unresolved_temporal_scope",
            *interpretation.diagnostics,
        ]

    if interpretation.format == "temporal_envelope_v1":
        assert interpretation.envelope is not None
        existing_source = interpretation.envelope.source_time
        if existing_source is not None:
            if len(evidence_sessions) > 1:
                raise TemporalShadowBuildError(
                    "Multiple evidence sessions while existing V1 source_time present",
                    code="multiple_source_sessions",
                    affected_assertion_id=assertion.assertion_id,
                    diagnostics=[f"evidence_sessions={evidence_sessions!r}"],
                )
            if (
                len(evidence_sessions) == 1
                and existing_source.kind == "session"
                and existing_source.session_id is not None
                and existing_source.session_id != evidence_sessions[0]
            ):
                raise TemporalShadowBuildError(
                    "Existing source_time disagrees with evidence session",
                    code="source_time_conflict",
                    affected_assertion_id=assertion.assertion_id,
                    diagnostics=[
                        f"source_session={existing_source.session_id!r}",
                        f"evidence_session={evidence_sessions[0]!r}",
                    ],
                )
            return existing_source, "existing_v1_source_time", diagnostics

    if interpretation.format == "legacy_session_observation":
        assert interpretation.envelope is not None
        assert interpretation.envelope.source_time is not None
        source = interpretation.envelope.source_time
        if len(evidence_sessions) > 1:
            raise TemporalShadowBuildError(
                "Multiple evidence sessions for legacy session temporal_scope",
                code="multiple_source_sessions",
                affected_assertion_id=assertion.assertion_id,
                diagnostics=[f"evidence_sessions={evidence_sessions!r}"],
            )
        if (
            len(evidence_sessions) == 1
            and source.session_id is not None
            and source.session_id != evidence_sessions[0]
        ):
            raise TemporalShadowBuildError(
                "Legacy temporal_scope session disagrees with evidence session",
                code="source_time_conflict",
                affected_assertion_id=assertion.assertion_id,
                diagnostics=[
                    f"scope_session={source.session_id!r}",
                    f"evidence_session={evidence_sessions[0]!r}",
                ],
            )
        if campaign_id and source.campaign_id is None:
            source = TemporalPointV1(
                kind="session",
                session_id=source.session_id,
                campaign_id=campaign_id,
                certainty=source.certainty,
            )
        return source, "legacy_session_scope", diagnostics

    if len(evidence_sessions) > 1:
        raise TemporalShadowBuildError(
            "Multiple evidence sessions with no existing source_time",
            code="multiple_source_sessions",
            affected_assertion_id=assertion.assertion_id,
            diagnostics=[f"evidence_sessions={evidence_sessions!r}"],
        )
    if len(evidence_sessions) == 1:
        return (
            TemporalPointV1(
                kind="session",
                session_id=evidence_sessions[0],
                campaign_id=campaign_id,
                certainty="explicit",
            ),
            "evidence_session",
            diagnostics,
        )
    return None, "none", diagnostics


def _semantic_equal(left: Any, right: Any) -> bool:
    return _canonical_json(left) == _canonical_json(right)


def _compose_shadow_temporal_scope(
    assertion: GraphContributionAssertion,
    *,
    source_time: TemporalPointV1 | None,
    annotation: TemporalAssertionAnnotationV1 | None,
) -> dict[str, Any] | None:
    occurrence: TemporalExtentV1 | None = None
    valid: TemporalIntervalV1 | None = None

    interpretation = interpret_temporal_scope(assertion.temporal_scope)
    if interpretation.format == "temporal_envelope_v1" and interpretation.envelope is not None:
        existing = interpretation.envelope
        occurrence = existing.occurrence_time
        valid = existing.valid_time
        if annotation is not None and annotation.interpretation_status == "resolved":
            if annotation.occurrence_time is not None:
                if occurrence is not None and not _semantic_equal(
                    _extent_dump(occurrence),
                    _extent_dump(annotation.occurrence_time),
                ):
                    raise TemporalShadowBuildError(
                        "Annotation occurrence_time conflicts with existing V1 envelope",
                        code="conflicting_existing_occurrence_time",
                        affected_assertion_id=assertion.assertion_id,
                    )
                occurrence = annotation.occurrence_time
            if annotation.valid_time is not None:
                if valid is not None and not _semantic_equal(
                    _interval_dump(valid),
                    _interval_dump(annotation.valid_time),
                ):
                    raise TemporalShadowBuildError(
                        "Annotation valid_time conflicts with existing V1 envelope",
                        code="conflicting_existing_valid_time",
                        affected_assertion_id=assertion.assertion_id,
                    )
                valid = annotation.valid_time
    elif annotation is not None and annotation.interpretation_status == "resolved":
        occurrence = annotation.occurrence_time
        valid = annotation.valid_time

    if source_time is None and occurrence is None and valid is None:
        return None

    envelope = TemporalEnvelopeV1(
        schema_=TEMPORAL_ENVELOPE_SCHEMA,
        source_time=source_time,
        occurrence_time=occurrence,
        valid_time=valid,
    )
    return serialize_temporal_envelope(envelope)


def _validate_candidate_only_base(contribution: GraphContribution) -> None:
    if contribution.status != "active":
        raise TemporalShadowBuildError(
            f"Base contribution status must be 'active', got {contribution.status!r}",
            code="invalid_base_contribution",
        )
    if not contribution.candidate_assertions:
        raise TemporalShadowBuildError(
            "Base contribution must contain non-empty candidate_assertions",
            code="invalid_base_contribution",
        )
    if contribution.accepted_assertions:
        raise TemporalShadowBuildError(
            "Base contribution must not contain accepted_assertions",
            code="invalid_base_contribution",
        )
    if contribution.rejected_assertions:
        raise TemporalShadowBuildError(
            "Base contribution must not contain rejected_assertions",
            code="invalid_base_contribution",
        )

    seen_assertion_ids: set[str] = set()
    for assertion in contribution.candidate_assertions:
        if assertion.acceptance_state != "candidate":
            raise TemporalShadowBuildError(
                "Every candidate assertion must have acceptance_state='candidate'",
                code="invalid_base_contribution",
                affected_assertion_id=assertion.assertion_id,
                diagnostics=[f"acceptance_state={assertion.acceptance_state!r}"],
            )
        if assertion.assertion_id in seen_assertion_ids:
            raise TemporalShadowBuildError(
                "Base contribution contains duplicate candidate assertion_id values",
                code="invalid_base_contribution",
                affected_assertion_id=assertion.assertion_id,
                diagnostics=[
                    "assertion targeting requires unique candidate assertion_id values"
                ],
            )
        seen_assertion_ids.add(assertion.assertion_id)

        canonical_id = compute_assertion_id(
            assertion_kind=assertion.assertion_kind,
            subject_node_id=assertion.subject_node_id,
            target_node_id=assertion.target_node_id,
            predicate=assertion.predicate,
            label=assertion.label,
            value=assertion.value,
            campaign_scope=assertion.campaign_scope,
            temporal_scope=assertion.temporal_scope,
            epistemic_kind=assertion.epistemic_kind,
            visibility=assertion.visibility,
        )
        if assertion.assertion_id != canonical_id:
            raise TemporalShadowBuildError(
                "Candidate assertion_id is not canonical for its semantic content",
                code="invalid_base_contribution",
                affected_assertion_id=assertion.assertion_id,
                diagnostics=[f"canonical_assertion_id={canonical_id!r}"],
            )


def _bind_overlay(
    contribution: GraphContribution,
    overlay: TemporalAnnotationOverlayV1,
) -> None:
    if overlay.base_contribution_id != contribution.contribution_id:
        raise TemporalShadowBuildError(
            "Overlay base_contribution_id does not match contribution",
            code="base_contribution_id_mismatch",
            diagnostics=[
                f"overlay={overlay.base_contribution_id!r}",
                f"contribution={contribution.contribution_id!r}",
            ],
        )
    actual_digest = compute_contribution_source_payload_sha256(contribution)
    if overlay.base_contribution_source_payload_sha256 != actual_digest:
        raise TemporalShadowBuildError(
            "Overlay base_contribution_source_payload_sha256 does not match",
            code="base_contribution_digest_mismatch",
            diagnostics=[
                f"overlay={overlay.base_contribution_source_payload_sha256!r}",
                f"actual={actual_digest!r}",
            ],
        )


def _verify_annotation_evidence(
    assertion: GraphContributionAssertion,
    annotation: TemporalAssertionAnnotationV1,
) -> None:
    owned = set(explicit_assertion_evidence_ref_ids(assertion))
    for evidence_id in annotation.evidence_ref_ids:
        if evidence_id not in owned:
            raise TemporalShadowBuildError(
                "Annotation cites evidence not owned by the target assertion",
                code="annotation_evidence_not_owned",
                affected_assertion_id=assertion.assertion_id,
                diagnostics=[
                    f"evidence_ref_id={evidence_id!r}",
                    f"owned={sorted(owned)!r}",
                ],
            )


def build_temporal_shadow_preview(
    contribution: GraphContribution,
    overlay: TemporalAnnotationOverlayV1 | dict[str, Any],
) -> TemporalShadowPreviewV1:
    """Build a deterministic non-authoritative temporal shadow preview.

    The base ``contribution`` is never mutated. Failed binding / composition
    raises ``TemporalShadowBuildError``. Successful builds return
    ``verdict`` of ``complete`` or ``partial``.
    """
    _validate_candidate_only_base(contribution)
    parsed_overlay = load_temporal_annotation_overlay(overlay)
    _bind_overlay(contribution, parsed_overlay)

    base_by_id = {
        assertion.assertion_id: assertion
        for assertion in contribution.candidate_assertions
    }

    annotations_by_target = {
        item.base_assertion_id: item for item in parsed_overlay.annotations
    }
    missing_targets = sorted(set(annotations_by_target) - set(base_by_id))
    if missing_targets:
        raise TemporalShadowBuildError(
            "Annotation targets assertion missing from base contribution",
            code="annotation_target_not_found",
            affected_assertion_id=missing_targets[0],
            diagnostics=[f"missing={missing_targets!r}"],
        )

    rows: list[TemporalShadowRowV1] = []
    skipped_count = 0
    error_count = 0
    source_time_derived = 0
    identity_changed_count = 0
    core_temporal_changed_count = 0
    unchanged_count = 0
    status_counts = {
        "resolved": 0,
        "ambiguous": 0,
        "unresolved": 0,
        "not_applicable": 0,
    }

    for assertion in contribution.candidate_assertions:
        annotation = annotations_by_target.get(assertion.assertion_id)
        if annotation is not None:
            _verify_annotation_evidence(assertion, annotation)
            status_counts[annotation.interpretation_status] += 1

        source_time, derivation, derive_diagnostics = derive_assertion_source_time(
            assertion
        )
        row_diagnostics = list(derive_diagnostics)
        if derivation == "skipped":
            skipped_count += 1
            rows.append(
                TemporalShadowRowV1(
                    base_assertion_id=assertion.assertion_id,
                    shadow_assertion_id=None,
                    assertion_kind=assertion.assertion_kind,
                    subject_node_id=assertion.subject_node_id,
                    target_node_id=assertion.target_node_id,
                    predicate=assertion.predicate,
                    label=assertion.label,
                    interpretation_status=(
                        annotation.interpretation_status if annotation else None
                    ),
                    annotation_id=annotation.annotation_id if annotation else None,
                    annotation_evidence_ref_ids=(
                        list(annotation.evidence_ref_ids) if annotation else []
                    ),
                    source_time_derivation="skipped",
                    base_temporal_scope=(
                        dict(assertion.temporal_scope)
                        if assertion.temporal_scope is not None
                        else None
                    ),
                    shadow_temporal_scope=None,
                    identity_changed=False,
                    base_core_temporal_payload=temporal_core_semantic_payload(
                        assertion.temporal_scope
                    ),
                    shadow_core_temporal_payload=None,
                    core_temporal_changed=False,
                    status="skipped",
                    diagnostics=row_diagnostics,
                )
            )
            continue

        if derivation in {"legacy_session_scope", "evidence_session"}:
            source_time_derived += 1

        if annotation is not None and annotation.interpretation_status != "resolved":
            if annotation.source_phrase is not None:
                row_diagnostics.append(
                    "source_phrase_preserved_outside_temporal_scope="
                    f"{annotation.source_phrase!r}"
                )
            row_diagnostics.extend(annotation.diagnostics)

        shadow_scope = _compose_shadow_temporal_scope(
            assertion,
            source_time=source_time,
            annotation=annotation,
        )
        shadow_id = compute_assertion_id(
            assertion_kind=assertion.assertion_kind,
            subject_node_id=assertion.subject_node_id,
            target_node_id=assertion.target_node_id,
            predicate=assertion.predicate,
            label=assertion.label,
            value=assertion.value,
            campaign_scope=assertion.campaign_scope,
            temporal_scope=shadow_scope,
            epistemic_kind=assertion.epistemic_kind,
            visibility=assertion.visibility,
        )
        base_core = temporal_core_semantic_payload(assertion.temporal_scope)
        shadow_core = temporal_core_semantic_payload(shadow_scope)
        identity_changed = shadow_id != assertion.assertion_id
        core_changed = not _semantic_equal(base_core, shadow_core)
        if identity_changed:
            identity_changed_count += 1
        if core_changed:
            core_temporal_changed_count += 1
        if not identity_changed and not core_changed:
            unchanged_count += 1

        rows.append(
            TemporalShadowRowV1(
                base_assertion_id=assertion.assertion_id,
                shadow_assertion_id=shadow_id,
                assertion_kind=assertion.assertion_kind,
                subject_node_id=assertion.subject_node_id,
                target_node_id=assertion.target_node_id,
                predicate=assertion.predicate,
                label=assertion.label,
                interpretation_status=(
                    annotation.interpretation_status if annotation else None
                ),
                annotation_id=annotation.annotation_id if annotation else None,
                annotation_evidence_ref_ids=(
                    list(annotation.evidence_ref_ids) if annotation else []
                ),
                source_time_derivation=derivation,
                base_temporal_scope=(
                    dict(assertion.temporal_scope)
                    if assertion.temporal_scope is not None
                    else None
                ),
                shadow_temporal_scope=shadow_scope,
                identity_changed=identity_changed,
                base_core_temporal_payload=base_core,
                shadow_core_temporal_payload=shadow_core,
                core_temporal_changed=core_changed,
                status="ok",
                diagnostics=row_diagnostics,
            )
        )

    annotated = len(parsed_overlay.annotations)
    total = len(contribution.candidate_assertions)
    summary = TemporalShadowSummaryV1(
        total_candidate_assertions=total,
        annotated_assertions=annotated,
        resolved_annotations=status_counts["resolved"],
        ambiguous_annotations=status_counts["ambiguous"],
        unresolved_annotations=status_counts["unresolved"],
        not_applicable_annotations=status_counts["not_applicable"],
        unannotated_assertions=total - annotated,
        source_time_derived=source_time_derived,
        identity_changed_count=identity_changed_count,
        core_temporal_changed_count=core_temporal_changed_count,
        unchanged_count=unchanged_count,
        skipped_count=skipped_count,
        error_count=error_count,
    )
    verdict: ShadowVerdict = "partial" if skipped_count else "complete"
    return TemporalShadowPreviewV1(
        schema_=TEMPORAL_SHADOW_PREVIEW_SCHEMA,
        overlay_id=parsed_overlay.overlay_id,
        base_contribution_id=contribution.contribution_id,
        base_contribution_source_payload_sha256=(
            parsed_overlay.base_contribution_source_payload_sha256
        ),
        verdict=verdict,
        summary=summary,
        rows=rows,
    )


__all__ = [
    "TEMPORAL_ANNOTATION_OVERLAY_SCHEMA",
    "TEMPORAL_SHADOW_PREVIEW_SCHEMA",
    "TemporalAnnotationOverlayV1",
    "TemporalAssertionAnnotationV1",
    "TemporalOverlayProducerV1",
    "TemporalShadowBuildError",
    "TemporalShadowPreviewV1",
    "TemporalShadowRowV1",
    "TemporalShadowSummaryV1",
    "build_temporal_shadow_preview",
    "compute_temporal_overlay_id",
    "derive_assertion_source_time",
    "load_temporal_annotation_overlay",
]
