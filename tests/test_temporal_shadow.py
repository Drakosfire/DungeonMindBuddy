"""Tests for TL01 temporal annotation overlay and shadow preview."""

from __future__ import annotations

import json
from typing import Any

import pytest
from pydantic import ValidationError

from graph_memory.kernel.contributions import (
    build_assertion,
    compute_assertion_id,
    compute_contribution_source_payload_sha256,
    create_graph_contribution,
)
from graph_memory.kernel.temporal import (
    TEMPORAL_ENVELOPE_SCHEMA,
    TemporalEnvelopeV1,
    TemporalIntervalV1,
    TemporalPointExtentV1,
    TemporalPointV1,
    serialize_temporal_envelope,
)
from graph_memory.temporal_shadow import (
    TEMPORAL_SHADOW_PREVIEW_SCHEMA,
    TemporalAnnotationOverlayV1,
    TemporalAssertionAnnotationV1,
    TemporalOverlayProducerV1,
    TemporalShadowBuildError,
    build_temporal_shadow_preview,
    compute_temporal_overlay_id,
    derive_assertion_source_time,
    load_temporal_annotation_overlay,
)
from graph_memory.temporal_shadow_cli import main as shadow_cli_main

FIXTURE_PRODUCER = TemporalOverlayProducerV1(
    kind="fixture",
    name="tl01-tests",
    version="1",
)
EVIDENCE_A = "evidence:test:chunk-a"
EVIDENCE_B = "evidence:test:chunk-b"
CAMPAIGN = "longmont-c2"


def _evidence_value(*, session_id: str | None = None, evidence_ref_id: str = EVIDENCE_A) -> dict[str, Any]:
    entry: dict[str, Any] = {"evidence_ref_id": evidence_ref_id}
    if session_id is not None:
        entry["session_id"] = session_id
    return {"evidence": [entry]}


def _candidate_assertion(
    *,
    temporal_scope: dict[str, Any] | None = None,
    session_id: str | None = "session-12",
    extra_evidence: list[dict[str, Any]] | None = None,
    evidence_ref_ids: list[str] | None = None,
    assertion_kind: str = "node",
    subject_node_id: str = "npc:test",
) -> Any:
    value = _evidence_value(session_id=session_id)
    if extra_evidence:
        value["evidence"] = [*value["evidence"], *extra_evidence]
    refs = list(evidence_ref_ids or [EVIDENCE_A])
    if extra_evidence:
        for item in extra_evidence:
            ref = item.get("evidence_ref_id")
            if isinstance(ref, str) and ref not in refs:
                refs.append(ref)
    return build_assertion(
        assertion_kind=assertion_kind,
        acceptance_state="candidate",
        subject_node_id=subject_node_id,
        label="Test NPC",
        campaign_scope=CAMPAIGN,
        value=value,
        evidence_ref_ids=refs,
        temporal_scope=temporal_scope,
    )


def _contribution(*assertions: Any) -> Any:
    return create_graph_contribution(
        world_id="eldyrwild",
        source_kind="source_extraction",
        campaign_scope=CAMPAIGN,
        candidate_assertions=list(assertions),
    )


def _session_point(session_id: str) -> TemporalPointV1:
    return TemporalPointV1(kind="session", session_id=session_id, certainty="explicit")


def _point_extent(session_id: str) -> TemporalPointExtentV1:
    return TemporalPointExtentV1(kind="point", point=_session_point(session_id))


def _resolved_annotation(
    assertion: Any,
    *,
    annotation_id: str = "ann-1",
    occurrence_time: TemporalPointExtentV1 | None = None,
    valid_time: TemporalIntervalV1 | None = None,
    evidence_ref_ids: list[str] | None = None,
) -> TemporalAssertionAnnotationV1:
    return TemporalAssertionAnnotationV1(
        annotation_id=annotation_id,
        base_assertion_id=assertion.assertion_id,
        interpretation_status="resolved",
        occurrence_time=occurrence_time,
        valid_time=valid_time,
        evidence_ref_ids=list(evidence_ref_ids or [EVIDENCE_A]),
    )


def _build_overlay(
    contribution: Any,
    annotations: list[TemporalAssertionAnnotationV1],
    *,
    producer: TemporalOverlayProducerV1 = FIXTURE_PRODUCER,
) -> TemporalAnnotationOverlayV1:
    digest = compute_contribution_source_payload_sha256(contribution)
    overlay_id = compute_temporal_overlay_id(
        base_contribution_id=contribution.contribution_id,
        base_contribution_source_payload_sha256=digest,
        producer=producer,
        annotations=annotations,
    )
    return TemporalAnnotationOverlayV1(
        overlay_id=overlay_id,
        base_contribution_id=contribution.contribution_id,
        base_contribution_source_payload_sha256=digest,
        producer=producer,
        annotations=annotations,
    )


def _expect_build_error(
    contribution: Any,
    overlay: TemporalAnnotationOverlayV1 | dict[str, Any],
    *,
    code: str,
) -> None:
    with pytest.raises(TemporalShadowBuildError) as exc_info:
        build_temporal_shadow_preview(contribution, overlay)
    assert exc_info.value.code == code


# ---------------------------------------------------------------------------
# Overlay contract
# ---------------------------------------------------------------------------


def test_overlay_rejects_extra_fields() -> None:
    contribution = _contribution(_candidate_assertion(temporal_scope={"session_id": "session-12"}))
    assertion = contribution.candidate_assertions[0]
    overlay = _build_overlay(
        contribution,
        [_resolved_annotation(assertion, occurrence_time=_point_extent("session-20"))],
    )
    payload = overlay.model_dump(mode="json", by_alias=True)
    payload["unexpected"] = True
    with pytest.raises(TemporalShadowBuildError) as exc_info:
        load_temporal_annotation_overlay(payload)
    assert exc_info.value.code == "invalid_temporal_annotation"


def test_overlay_id_deterministic_and_order_invariant() -> None:
    contribution = _contribution(
        _candidate_assertion(temporal_scope={"session_id": "session-12"}, subject_node_id="npc:a"),
        _candidate_assertion(temporal_scope={"session_id": "session-12"}, subject_node_id="npc:b"),
    )
    a0, a1 = contribution.candidate_assertions
    ann0 = _resolved_annotation(a0, annotation_id="ann-a", occurrence_time=_point_extent("session-5"))
    ann1 = _resolved_annotation(a1, annotation_id="ann-b", occurrence_time=_point_extent("session-6"))
    digest = compute_contribution_source_payload_sha256(contribution)
    id_forward = compute_temporal_overlay_id(
        base_contribution_id=contribution.contribution_id,
        base_contribution_source_payload_sha256=digest,
        producer=FIXTURE_PRODUCER,
        annotations=[ann0, ann1],
    )
    id_reverse = compute_temporal_overlay_id(
        base_contribution_id=contribution.contribution_id,
        base_contribution_source_payload_sha256=digest,
        producer=FIXTURE_PRODUCER,
        annotations=[ann1, ann0],
    )
    assert id_forward == id_reverse
    assert id_forward.startswith("temporal-overlay:")


def test_overlay_rejects_stale_overlay_id() -> None:
    contribution = _contribution(_candidate_assertion(temporal_scope={"session_id": "session-12"}))
    assertion = contribution.candidate_assertions[0]
    overlay = _build_overlay(
        contribution,
        [_resolved_annotation(assertion, occurrence_time=_point_extent("session-20"))],
    )
    payload = overlay.model_dump(mode="json", by_alias=True)
    payload["overlay_id"] = "temporal-overlay:deadbeefdeadbeef"
    with pytest.raises(TemporalShadowBuildError) as exc_info:
        load_temporal_annotation_overlay(payload)
    assert exc_info.value.code in ("invalid_overlay_id", "invalid_temporal_annotation")
    joined = " ".join(exc_info.value.diagnostics)
    assert "invalid_overlay_id" in joined or "does not match canonical" in joined


def test_load_revalidates_model_instance_with_stale_overlay_id() -> None:
    contribution = _contribution(_candidate_assertion(temporal_scope={"session_id": "session-12"}))
    assertion = contribution.candidate_assertions[0]
    overlay = _build_overlay(
        contribution,
        [_resolved_annotation(assertion, occurrence_time=_point_extent("session-20"))],
    )
    mutated = overlay.model_copy(update={"overlay_id": "temporal-overlay:deadbeefdeadbeef"})
    with pytest.raises(TemporalShadowBuildError) as exc_info:
        load_temporal_annotation_overlay(mutated)
    assert exc_info.value.code == "invalid_overlay_id"
    with pytest.raises(TemporalShadowBuildError) as build_exc:
        build_temporal_shadow_preview(contribution, mutated)
    assert build_exc.value.code == "invalid_overlay_id"


def test_load_revalidates_model_instance_with_mutated_annotation() -> None:
    contribution = _contribution(_candidate_assertion(temporal_scope={"session_id": "session-12"}))
    assertion = contribution.candidate_assertions[0]
    overlay = _build_overlay(
        contribution,
        [_resolved_annotation(assertion, occurrence_time=_point_extent("session-20"))],
    )
    mutated_annotation = overlay.annotations[0].model_copy(
        update={
            "interpretation_status": "ambiguous",
            "occurrence_time": None,
            "source_phrase": None,
            "diagnostics": [],
        }
    )
    mutated = overlay.model_copy(update={"annotations": [mutated_annotation]})
    with pytest.raises(TemporalShadowBuildError) as exc_info:
        load_temporal_annotation_overlay(mutated)
    assert exc_info.value.code == "invalid_temporal_annotation"


def test_overlay_rejects_duplicate_assertion_targets() -> None:
    contribution = _contribution(_candidate_assertion(temporal_scope={"session_id": "session-12"}))
    assertion = contribution.candidate_assertions[0]
    ann_a = _resolved_annotation(assertion, annotation_id="ann-a", occurrence_time=_point_extent("session-5"))
    ann_b = _resolved_annotation(assertion, annotation_id="ann-b", occurrence_time=_point_extent("session-6"))
    digest = compute_contribution_source_payload_sha256(contribution)
    with pytest.raises(TemporalShadowBuildError) as exc_info:
        load_temporal_annotation_overlay(
            {
                "schema": "dmb_temporal_annotation_overlay_v1",
                "overlay_id": "temporal-overlay:placeholder",
                "base_contribution_id": contribution.contribution_id,
                "base_contribution_source_payload_sha256": digest,
                "producer": FIXTURE_PRODUCER.model_dump(),
                "annotations": [
                    ann_a.model_dump(mode="json"),
                    ann_b.model_dump(mode="json"),
                ],
            }
        )
    assert exc_info.value.code == "invalid_temporal_annotation"


def test_overlay_rejects_invalid_producer_kind() -> None:
    with pytest.raises(ValidationError):
        TemporalOverlayProducerV1(kind="llm_extraction", name="x", version="1")  # type: ignore[arg-type]


def test_annotation_resolved_requires_semantic_time() -> None:
    contribution = _contribution(_candidate_assertion(temporal_scope={"session_id": "session-12"}))
    assertion = contribution.candidate_assertions[0]
    with pytest.raises(ValidationError):
        TemporalAssertionAnnotationV1(
            annotation_id="ann-1",
            base_assertion_id=assertion.assertion_id,
            interpretation_status="resolved",
            evidence_ref_ids=[EVIDENCE_A],
        )


def test_annotation_ambiguous_rejects_normalized_time_and_requires_metadata() -> None:
    contribution = _contribution(_candidate_assertion(temporal_scope={"session_id": "session-12"}))
    assertion = contribution.candidate_assertions[0]
    with pytest.raises(ValidationError):
        TemporalAssertionAnnotationV1(
            annotation_id="ann-1",
            base_assertion_id=assertion.assertion_id,
            interpretation_status="ambiguous",
            occurrence_time=_point_extent("session-5"),
            evidence_ref_ids=[EVIDENCE_A],
            source_phrase="maybe later",
            diagnostics=["unclear wording"],
        )
    with pytest.raises(ValidationError):
        TemporalAssertionAnnotationV1(
            annotation_id="ann-2",
            base_assertion_id=assertion.assertion_id,
            interpretation_status="ambiguous",
            evidence_ref_ids=[EVIDENCE_A],
            source_phrase="maybe later",
        )


def test_annotation_ambiguous_rejects_blank_diagnostics() -> None:
    contribution = _contribution(_candidate_assertion(temporal_scope={"session_id": "session-12"}))
    assertion = contribution.candidate_assertions[0]
    with pytest.raises(ValidationError):
        TemporalAssertionAnnotationV1(
            annotation_id="ann-blank-diag",
            base_assertion_id=assertion.assertion_id,
            interpretation_status="ambiguous",
            evidence_ref_ids=[EVIDENCE_A],
            source_phrase="long ago",
            diagnostics=["   "],
        )


def test_annotation_unresolved_rejects_blank_diagnostics_without_phrase() -> None:
    contribution = _contribution(_candidate_assertion(temporal_scope={"session_id": "session-12"}))
    assertion = contribution.candidate_assertions[0]
    with pytest.raises(ValidationError):
        TemporalAssertionAnnotationV1(
            annotation_id="ann-unresolved-blank",
            base_assertion_id=assertion.assertion_id,
            interpretation_status="unresolved",
            evidence_ref_ids=[EVIDENCE_A],
            diagnostics=[" "],
        )


def test_annotation_unresolved_and_not_applicable_reject_normalized_time() -> None:
    contribution = _contribution(_candidate_assertion(temporal_scope={"session_id": "session-12"}))
    assertion = contribution.candidate_assertions[0]
    for status in ("unresolved", "not_applicable"):
        with pytest.raises(ValidationError):
            TemporalAssertionAnnotationV1(
                annotation_id=f"ann-{status}",
                base_assertion_id=assertion.assertion_id,
                interpretation_status=status,  # type: ignore[arg-type]
                valid_time=TemporalIntervalV1(start=_session_point("session-1")),
                evidence_ref_ids=[EVIDENCE_A],
                source_phrase="text",
                diagnostics=["x"],
            )


# ---------------------------------------------------------------------------
# Base binding
# ---------------------------------------------------------------------------


def test_base_contribution_id_mismatch() -> None:
    contribution = _contribution(_candidate_assertion(temporal_scope={"session_id": "session-12"}))
    assertion = contribution.candidate_assertions[0]
    annotations = [
        _resolved_annotation(assertion, occurrence_time=_point_extent("session-20"))
    ]
    digest = compute_contribution_source_payload_sha256(contribution)
    wrong_id = "contribution:wrong"
    overlay = TemporalAnnotationOverlayV1(
        overlay_id=compute_temporal_overlay_id(
            base_contribution_id=wrong_id,
            base_contribution_source_payload_sha256=digest,
            producer=FIXTURE_PRODUCER,
            annotations=annotations,
        ),
        base_contribution_id=wrong_id,
        base_contribution_source_payload_sha256=digest,
        producer=FIXTURE_PRODUCER,
        annotations=annotations,
    )
    _expect_build_error(contribution, overlay, code="base_contribution_id_mismatch")


def test_base_contribution_digest_mismatch() -> None:
    contribution = _contribution(_candidate_assertion(temporal_scope={"session_id": "session-12"}))
    assertion = contribution.candidate_assertions[0]
    annotations = [
        _resolved_annotation(assertion, occurrence_time=_point_extent("session-20"))
    ]
    wrong_digest = "0" * 64
    overlay = TemporalAnnotationOverlayV1(
        overlay_id=compute_temporal_overlay_id(
            base_contribution_id=contribution.contribution_id,
            base_contribution_source_payload_sha256=wrong_digest,
            producer=FIXTURE_PRODUCER,
            annotations=annotations,
        ),
        base_contribution_id=contribution.contribution_id,
        base_contribution_source_payload_sha256=wrong_digest,
        producer=FIXTURE_PRODUCER,
        annotations=annotations,
    )
    _expect_build_error(contribution, overlay, code="base_contribution_digest_mismatch")


def test_invalid_base_contribution_with_accepted_assertions() -> None:
    node = _candidate_assertion(temporal_scope={"session_id": "session-12"})
    contribution = create_graph_contribution(
        world_id="eldyrwild",
        source_kind="source_extraction",
        campaign_scope=CAMPAIGN,
        accepted_assertions=[node],
    )
    overlay = _build_overlay(contribution, [])
    _expect_build_error(contribution, overlay, code="invalid_base_contribution")


def test_invalid_base_contribution_with_rejected_assertions() -> None:
    node = _candidate_assertion(temporal_scope={"session_id": "session-12"})
    contribution = create_graph_contribution(
        world_id="eldyrwild",
        source_kind="source_extraction",
        campaign_scope=CAMPAIGN,
        candidate_assertions=[node],
        rejected_assertions=[node],
    )
    overlay = _build_overlay(contribution, [])
    _expect_build_error(contribution, overlay, code="invalid_base_contribution")


def test_invalid_base_contribution_non_candidate_acceptance_state() -> None:
    node = build_assertion(
        assertion_kind="node",
        acceptance_state="accepted",
        subject_node_id="npc:test",
        label="Test",
        campaign_scope=CAMPAIGN,
        value=_evidence_value(session_id="session-12"),
        evidence_ref_ids=[EVIDENCE_A],
        temporal_scope={"session_id": "session-12"},
    )
    contribution = create_graph_contribution(
        world_id="eldyrwild",
        source_kind="source_extraction",
        campaign_scope=CAMPAIGN,
        candidate_assertions=[node],
    )
    overlay = _build_overlay(contribution, [])
    _expect_build_error(contribution, overlay, code="invalid_base_contribution")


def test_invalid_base_rejects_duplicate_candidate_assertion_ids() -> None:
    """Semantically identical rows with different evidence can share an ID."""
    first = _candidate_assertion(
        temporal_scope={"session_id": "session-12"},
        evidence_ref_ids=[EVIDENCE_A],
        session_id="session-12",
    )
    second = _candidate_assertion(
        temporal_scope={"session_id": "session-12"},
        evidence_ref_ids=[EVIDENCE_B],
        session_id="session-12",
    )
    second = second.model_copy(
        update={
            "evidence_ref_ids": [EVIDENCE_B],
            "value": _evidence_value(session_id="session-12", evidence_ref_id=EVIDENCE_B),
        }
    )
    assert first.assertion_id == second.assertion_id
    assert first.evidence_ref_ids != second.evidence_ref_ids
    contribution = create_graph_contribution(
        world_id="eldyrwild",
        source_kind="source_extraction",
        campaign_scope=CAMPAIGN,
        candidate_assertions=[first, second],
    )
    # Re-assert after contribution rewrite that IDs remain duplicated.
    assert (
        contribution.candidate_assertions[0].assertion_id
        == contribution.candidate_assertions[1].assertion_id
    )
    overlay = _build_overlay(contribution, [])
    _expect_build_error(contribution, overlay, code="invalid_base_contribution")


def test_invalid_base_rejects_noncanonical_assertion_id() -> None:
    node = _candidate_assertion(temporal_scope={"session_id": "session-12"})
    malformed = node.model_copy(update={"assertion_id": "assertion:not-canonical"})
    contribution = create_graph_contribution(
        world_id="eldyrwild",
        source_kind="source_extraction",
        campaign_scope=CAMPAIGN,
        candidate_assertions=[malformed],
    )
    # create_graph_contribution may canonicalize — force non-canonical after create.
    contribution = contribution.model_copy(
        update={
            "candidate_assertions": [
                contribution.candidate_assertions[0].model_copy(
                    update={"assertion_id": "assertion:not-canonical"}
                )
            ]
        }
    )
    canonical = compute_assertion_id(
        assertion_kind=contribution.candidate_assertions[0].assertion_kind,
        subject_node_id=contribution.candidate_assertions[0].subject_node_id,
        target_node_id=contribution.candidate_assertions[0].target_node_id,
        predicate=contribution.candidate_assertions[0].predicate,
        label=contribution.candidate_assertions[0].label,
        value=contribution.candidate_assertions[0].value,
        campaign_scope=contribution.candidate_assertions[0].campaign_scope,
        temporal_scope=contribution.candidate_assertions[0].temporal_scope,
        epistemic_kind=contribution.candidate_assertions[0].epistemic_kind,
        visibility=contribution.candidate_assertions[0].visibility,
    )
    assert contribution.candidate_assertions[0].assertion_id != canonical
    overlay = _build_overlay(contribution, [])
    _expect_build_error(contribution, overlay, code="invalid_base_contribution")


def test_base_contribution_unchanged_after_successful_build() -> None:
    contribution = _contribution(_candidate_assertion(temporal_scope={"session_id": "session-12"}))
    before = contribution.model_dump(mode="json")
    assertion = contribution.candidate_assertions[0]
    overlay = _build_overlay(
        contribution,
        [_resolved_annotation(assertion, occurrence_time=_point_extent("session-20"))],
    )
    build_temporal_shadow_preview(contribution, overlay)
    assert contribution.model_dump(mode="json") == before


def test_annotation_target_not_found() -> None:
    contribution = _contribution(_candidate_assertion(temporal_scope={"session_id": "session-12"}))
    overlay = _build_overlay(
        contribution,
        [
            TemporalAssertionAnnotationV1(
                annotation_id="ann-missing",
                base_assertion_id="assertion:does-not-exist",
                interpretation_status="not_applicable",
                evidence_ref_ids=[EVIDENCE_A],
                source_phrase="n/a",
            )
        ],
    )
    _expect_build_error(contribution, overlay, code="annotation_target_not_found")


# ---------------------------------------------------------------------------
# Evidence
# ---------------------------------------------------------------------------


def test_annotation_rejects_empty_evidence_ref_ids() -> None:
    contribution = _contribution(_candidate_assertion(temporal_scope={"session_id": "session-12"}))
    assertion = contribution.candidate_assertions[0]
    with pytest.raises(ValidationError):
        TemporalAssertionAnnotationV1(
            annotation_id="ann-1",
            base_assertion_id=assertion.assertion_id,
            interpretation_status="not_applicable",
            evidence_ref_ids=[],
            source_phrase="n/a",
        )


def test_annotation_evidence_subset_succeeds() -> None:
    contribution = _contribution(
        _candidate_assertion(
            temporal_scope={"session_id": "session-12"},
            extra_evidence=[{"evidence_ref_id": EVIDENCE_B, "session_id": "session-12"}],
            evidence_ref_ids=[EVIDENCE_A, EVIDENCE_B],
        )
    )
    assertion = contribution.candidate_assertions[0]
    overlay = _build_overlay(
        contribution,
        [
            TemporalAssertionAnnotationV1(
                annotation_id="ann-subset",
                base_assertion_id=assertion.assertion_id,
                interpretation_status="not_applicable",
                evidence_ref_ids=[EVIDENCE_B],
                source_phrase="source-only re-attestation",
            )
        ],
    )
    preview = build_temporal_shadow_preview(contribution, overlay)
    assert preview.verdict == "complete"
    row = preview.rows[0]
    assert row.annotation_evidence_ref_ids == [EVIDENCE_B]


def test_annotation_foreign_evidence_not_owned() -> None:
    contribution = _contribution(_candidate_assertion(temporal_scope={"session_id": "session-12"}))
    assertion = contribution.candidate_assertions[0]
    overlay = _build_overlay(
        contribution,
        [
            TemporalAssertionAnnotationV1(
                annotation_id="ann-foreign",
                base_assertion_id=assertion.assertion_id,
                interpretation_status="not_applicable",
                evidence_ref_ids=["evidence:foreign:attack"],
                source_phrase="n/a",
            )
        ],
    )
    _expect_build_error(contribution, overlay, code="annotation_evidence_not_owned")


# ---------------------------------------------------------------------------
# Source-time derivation
# ---------------------------------------------------------------------------


def test_legacy_session_scope_derives_source_time_without_occurrence() -> None:
    contribution = _contribution(_candidate_assertion(temporal_scope={"session_id": "session-12"}))
    assertion = contribution.candidate_assertions[0]
    source, derivation, _ = derive_assertion_source_time(assertion)
    assert derivation == "legacy_session_scope"
    assert source is not None
    assert source.session_id == "session-12"
    preview = build_temporal_shadow_preview(contribution, _build_overlay(contribution, []))
    row = preview.rows[0]
    assert row.source_time_derivation == "legacy_session_scope"
    assert row.shadow_temporal_scope is not None
    assert row.shadow_temporal_scope.get("occurrence_time") is None


def test_evidence_session_derivation_when_temporal_scope_none() -> None:
    contribution = _contribution(_candidate_assertion(temporal_scope=None, session_id="session-9"))
    assertion = contribution.candidate_assertions[0]
    source, derivation, _ = derive_assertion_source_time(assertion)
    assert derivation == "evidence_session"
    assert source is not None
    assert source.session_id == "session-9"
    preview = build_temporal_shadow_preview(contribution, _build_overlay(contribution, []))
    row = preview.rows[0]
    assert row.shadow_temporal_scope is not None
    assert row.shadow_temporal_scope.get("occurrence_time") is None


def test_no_session_evidence_yields_none_source_time() -> None:
    node = build_assertion(
        assertion_kind="node",
        acceptance_state="candidate",
        subject_node_id="npc:test",
        label="Test",
        campaign_scope=CAMPAIGN,
        value={"kind": "npc"},
        evidence_ref_ids=[EVIDENCE_A],
        temporal_scope=None,
    )
    contribution = _contribution(node)
    assertion = contribution.candidate_assertions[0]
    source, derivation, _ = derive_assertion_source_time(assertion)
    assert derivation == "none"
    assert source is None
    preview = build_temporal_shadow_preview(contribution, _build_overlay(contribution, []))
    assert preview.rows[0].shadow_temporal_scope is None


def test_multiple_evidence_sessions_raises_multiple_source_sessions() -> None:
    node = _candidate_assertion(
        temporal_scope=None,
        extra_evidence=[
            {"evidence_ref_id": EVIDENCE_B, "session_id": "session-2"},
        ],
        evidence_ref_ids=[EVIDENCE_A, EVIDENCE_B],
        session_id="session-1",
    )
    contribution = _contribution(node)
    assertion = contribution.candidate_assertions[0]
    with pytest.raises(TemporalShadowBuildError) as exc_info:
        derive_assertion_source_time(assertion)
    assert exc_info.value.code == "multiple_source_sessions"


def test_existing_v1_source_time_conflicts_with_evidence_session() -> None:
    envelope = serialize_temporal_envelope(
        TemporalEnvelopeV1(
            schema_=TEMPORAL_ENVELOPE_SCHEMA,
            source_time=_session_point("session-12"),
            occurrence_time=None,
            valid_time=None,
        )
    )
    node = _candidate_assertion(temporal_scope=envelope, session_id="session-99")
    contribution = _contribution(node)
    assertion = contribution.candidate_assertions[0]
    with pytest.raises(TemporalShadowBuildError) as exc_info:
        derive_assertion_source_time(assertion)
    assert exc_info.value.code == "source_time_conflict"


def test_source_time_never_auto_creates_occurrence_regression() -> None:
    contribution = _contribution(_candidate_assertion(temporal_scope={"session_id": "session-12"}))
    preview = build_temporal_shadow_preview(contribution, _build_overlay(contribution, []))
    scope = preview.rows[0].shadow_temporal_scope
    assert scope is not None
    assert scope["source_time"]["session_id"] == "session-12"
    assert scope.get("occurrence_time") is None


def test_explicit_occurrence_matching_source_session_when_resolved() -> None:
    contribution = _contribution(_candidate_assertion(temporal_scope={"session_id": "session-12"}))
    assertion = contribution.candidate_assertions[0]
    overlay = _build_overlay(
        contribution,
        [
            _resolved_annotation(
                assertion,
                occurrence_time=_point_extent("session-12"),
            )
        ],
    )
    preview = build_temporal_shadow_preview(contribution, overlay)
    scope = preview.rows[0].shadow_temporal_scope
    assert scope is not None
    assert scope["occurrence_time"]["point"]["session_id"] == "session-12"
    assert scope["source_time"]["session_id"] == "session-12"


# ---------------------------------------------------------------------------
# Composition / identity
# ---------------------------------------------------------------------------


def test_none_temporal_scope_plus_occurrence_annotation_changes_identity_and_core() -> None:
    contribution = _contribution(_candidate_assertion(temporal_scope=None, session_id="session-12"))
    assertion = contribution.candidate_assertions[0]
    overlay = _build_overlay(
        contribution,
        [_resolved_annotation(assertion, occurrence_time=_point_extent("session-20"))],
    )
    preview = build_temporal_shadow_preview(contribution, overlay)
    row = preview.rows[0]
    assert row.identity_changed is True
    assert row.core_temporal_changed is True


def test_legacy_session_plus_occurrence_changes_provenance_and_semantics() -> None:
    contribution = _contribution(_candidate_assertion(temporal_scope={"session_id": "session-12"}))
    assertion = contribution.candidate_assertions[0]
    overlay = _build_overlay(
        contribution,
        [_resolved_annotation(assertion, occurrence_time=_point_extent("session-20"))],
    )
    preview = build_temporal_shadow_preview(contribution, overlay)
    row = preview.rows[0]
    assert row.identity_changed is True
    assert row.core_temporal_changed is True
    assert row.shadow_temporal_scope is not None
    assert row.shadow_temporal_scope["source_time"]["session_id"] == "session-12"
    assert row.shadow_temporal_scope["occurrence_time"]["point"]["session_id"] == "session-20"


def test_provenance_only_legacy_to_v1_source_normalization() -> None:
    contribution = _contribution(_candidate_assertion(temporal_scope={"session_id": "session-12"}))
    preview = build_temporal_shadow_preview(contribution, _build_overlay(contribution, []))
    row = preview.rows[0]
    assert row.identity_changed is True
    assert row.core_temporal_changed is False


def test_valid_time_annotation_changes_identity_and_core() -> None:
    contribution = _contribution(_candidate_assertion(temporal_scope=None, session_id="session-12"))
    assertion = contribution.candidate_assertions[0]
    overlay = _build_overlay(
        contribution,
        [
            _resolved_annotation(
                assertion,
                valid_time=TemporalIntervalV1(start=_session_point("session-13")),
            )
        ],
    )
    preview = build_temporal_shadow_preview(contribution, overlay)
    row = preview.rows[0]
    assert row.identity_changed is True
    assert row.core_temporal_changed is True


def test_no_temporal_info_preserves_assertion_id() -> None:
    node = build_assertion(
        assertion_kind="node",
        acceptance_state="candidate",
        subject_node_id="npc:static",
        label="Static",
        campaign_scope=CAMPAIGN,
        value={"kind": "npc"},
        evidence_ref_ids=[EVIDENCE_A],
        temporal_scope=None,
    )
    contribution = _contribution(node)
    preview = build_temporal_shadow_preview(contribution, _build_overlay(contribution, []))
    row = preview.rows[0]
    assert row.shadow_assertion_id == row.base_assertion_id
    assert row.identity_changed is False


def test_extraction_metadata_does_not_change_shadow_assertion_id() -> None:
    contribution = _contribution(_candidate_assertion(temporal_scope={"session_id": "session-12"}))
    assertion = contribution.candidate_assertions[0]
    base_overlay = _build_overlay(
        contribution,
        [
            TemporalAssertionAnnotationV1(
                annotation_id="ann-meta-a",
                base_assertion_id=assertion.assertion_id,
                interpretation_status="ambiguous",
                evidence_ref_ids=[EVIDENCE_A],
                source_phrase="phrase one",
                extraction_confidence="high",
                diagnostics=["d1"],
            )
        ],
    )
    alt_producer = TemporalOverlayProducerV1(kind="fixture", name="other-producer", version="1")
    alt_overlay = _build_overlay(
        contribution,
        [
            TemporalAssertionAnnotationV1(
                annotation_id="ann-meta-b",
                base_assertion_id=assertion.assertion_id,
                interpretation_status="ambiguous",
                evidence_ref_ids=[EVIDENCE_A],
                source_phrase="phrase two",
                extraction_confidence="low",
                diagnostics=["d2", "d3"],
            )
        ],
        producer=alt_producer,
    )
    assert base_overlay.overlay_id != alt_overlay.overlay_id
    preview_a = build_temporal_shadow_preview(contribution, base_overlay)
    preview_b = build_temporal_shadow_preview(contribution, alt_overlay)
    assert preview_a.rows[0].shadow_assertion_id == preview_b.rows[0].shadow_assertion_id


def test_unresolved_legacy_temporal_scope_skipped_partial_verdict() -> None:
    contribution = _contribution(
        _candidate_assertion(temporal_scope={"session_id": "session-12", "as_of": "T1"})
    )
    preview = build_temporal_shadow_preview(contribution, _build_overlay(contribution, []))
    assert preview.verdict == "partial"
    row = preview.rows[0]
    assert row.status == "skipped"
    assert row.source_time_derivation == "skipped"
    assert "skipped_existing_unresolved_temporal_scope" in row.diagnostics


def test_unknown_schema_tag_skipped_partial_verdict() -> None:
    contribution = _contribution(
        _candidate_assertion(
            temporal_scope={"schema": "dmb_future_temporal_v9", "session_id": "session-12"}
        )
    )
    preview = build_temporal_shadow_preview(contribution, _build_overlay(contribution, []))
    assert preview.verdict == "partial"
    assert preview.rows[0].status == "skipped"
    assert "skipped_unrecognized_temporal_schema" in preview.rows[0].diagnostics


def test_matching_existing_v1_semantic_preserved() -> None:
    occurrence = _point_extent("session-20")
    envelope = serialize_temporal_envelope(
        TemporalEnvelopeV1(
            schema_=TEMPORAL_ENVELOPE_SCHEMA,
            source_time=_session_point("session-12"),
            occurrence_time=occurrence,
            valid_time=None,
        )
    )
    contribution = _contribution(_candidate_assertion(temporal_scope=envelope))
    assertion = contribution.candidate_assertions[0]
    overlay = _build_overlay(
        contribution,
        [_resolved_annotation(assertion, occurrence_time=occurrence)],
    )
    preview = build_temporal_shadow_preview(contribution, overlay)
    row = preview.rows[0]
    assert row.core_temporal_changed is False


def test_conflicting_existing_v1_occurrence_fails() -> None:
    envelope = serialize_temporal_envelope(
        TemporalEnvelopeV1(
            schema_=TEMPORAL_ENVELOPE_SCHEMA,
            source_time=_session_point("session-12"),
            occurrence_time=_point_extent("session-20"),
            valid_time=None,
        )
    )
    contribution = _contribution(_candidate_assertion(temporal_scope=envelope))
    assertion = contribution.candidate_assertions[0]
    overlay = _build_overlay(
        contribution,
        [_resolved_annotation(assertion, occurrence_time=_point_extent("session-99"))],
    )
    _expect_build_error(contribution, overlay, code="conflicting_existing_occurrence_time")


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------


def test_preview_dump_deterministic_for_same_inputs() -> None:
    contribution = _contribution(
        _candidate_assertion(temporal_scope={"session_id": "session-12"}, subject_node_id="npc:a"),
        _candidate_assertion(temporal_scope=None, session_id="session-9", subject_node_id="npc:b"),
    )
    a0, a1 = contribution.candidate_assertions
    overlay = _build_overlay(
        contribution,
        [
            _resolved_annotation(a0, annotation_id="ann-a", occurrence_time=_point_extent("session-5")),
            TemporalAssertionAnnotationV1(
                annotation_id="ann-b",
                base_assertion_id=a1.assertion_id,
                interpretation_status="not_applicable",
                evidence_ref_ids=[EVIDENCE_A],
                source_phrase="n/a",
            ),
        ],
    )
    first = build_temporal_shadow_preview(contribution, overlay).model_dump(mode="json", by_alias=True)
    second = build_temporal_shadow_preview(contribution, overlay).model_dump(mode="json", by_alias=True)
    assert first == second


def test_row_order_follows_base_assertion_order_not_annotation_order() -> None:
    contribution = _contribution(
        _candidate_assertion(temporal_scope={"session_id": "session-12"}, subject_node_id="npc:first"),
        _candidate_assertion(temporal_scope={"session_id": "session-12"}, subject_node_id="npc:second"),
    )
    first, second = contribution.candidate_assertions
    overlay = _build_overlay(
        contribution,
        [
            _resolved_annotation(second, annotation_id="ann-second", occurrence_time=_point_extent("session-2")),
            _resolved_annotation(first, annotation_id="ann-first", occurrence_time=_point_extent("session-1")),
        ],
    )
    preview = build_temporal_shadow_preview(contribution, overlay)
    assert [row.base_assertion_id for row in preview.rows] == [
        first.assertion_id,
        second.assertion_id,
    ]


# ---------------------------------------------------------------------------
# Adversarial scenarios A–G
# ---------------------------------------------------------------------------


def test_scenario_a_source_only_re_attestation_not_applicable() -> None:
    contribution = _contribution(_candidate_assertion(temporal_scope={"session_id": "session-12"}))
    assertion = contribution.candidate_assertions[0]
    overlay = _build_overlay(
        contribution,
        [
            TemporalAssertionAnnotationV1(
                annotation_id="ann-a",
                base_assertion_id=assertion.assertion_id,
                interpretation_status="not_applicable",
                evidence_ref_ids=[EVIDENCE_A],
                source_phrase="no fictional event time",
            )
        ],
    )
    preview = build_temporal_shadow_preview(contribution, overlay)
    row = preview.rows[0]
    assert row.interpretation_status == "not_applicable"
    assert row.shadow_temporal_scope is not None
    assert row.shadow_temporal_scope.get("occurrence_time") is None


def test_scenario_b_explicit_event_occurrence() -> None:
    contribution = _contribution(
        _candidate_assertion(temporal_scope={"session_id": "session-20"}, session_id="session-20")
    )
    assertion = contribution.candidate_assertions[0]
    overlay = _build_overlay(
        contribution,
        [_resolved_annotation(assertion, occurrence_time=_point_extent("session-12"))],
    )
    preview = build_temporal_shadow_preview(contribution, overlay)
    scope = preview.rows[0].shadow_temporal_scope
    assert scope is not None
    assert scope["occurrence_time"]["point"]["session_id"] == "session-12"


def test_scenario_c_persistent_valid_time_start() -> None:
    contribution = _contribution(_candidate_assertion(temporal_scope=None, session_id="session-12"))
    assertion = contribution.candidate_assertions[0]
    overlay = _build_overlay(
        contribution,
        [
            _resolved_annotation(
                assertion,
                valid_time=TemporalIntervalV1(start=_session_point("session-13")),
            )
        ],
    )
    preview = build_temporal_shadow_preview(contribution, overlay)
    scope = preview.rows[0].shadow_temporal_scope
    assert scope is not None
    assert scope["valid_time"]["start"]["session_id"] == "session-13"


def test_scenario_d_relative_historical_occurrence() -> None:
    relative_point = TemporalPointV1(
        kind="relative",
        relation="before",
        anchor_ref="event:festival-of-expansion",
        raw_expression="twenty years before the campaign",
        certainty="approximate",
    )
    contribution = _contribution(_candidate_assertion(temporal_scope=None, session_id="session-12"))
    assertion = contribution.candidate_assertions[0]
    overlay = _build_overlay(
        contribution,
        [
            _resolved_annotation(
                assertion,
                occurrence_time=TemporalPointExtentV1(kind="point", point=relative_point),
            )
        ],
    )
    preview = build_temporal_shadow_preview(contribution, overlay)
    occ = preview.rows[0].shadow_temporal_scope["occurrence_time"]["point"]
    assert occ["kind"] == "relative"
    assert occ["anchor_ref"] == "event:festival-of-expansion"


def test_scenario_e_ambiguous_language_no_normalized_time() -> None:
    contribution = _contribution(_candidate_assertion(temporal_scope={"session_id": "session-12"}))
    assertion = contribution.candidate_assertions[0]
    overlay = _build_overlay(
        contribution,
        [
            TemporalAssertionAnnotationV1(
                annotation_id="ann-e",
                base_assertion_id=assertion.assertion_id,
                interpretation_status="ambiguous",
                evidence_ref_ids=[EVIDENCE_A],
                source_phrase="sometime after the siege",
                diagnostics=["multiple plausible readings"],
            )
        ],
    )
    preview = build_temporal_shadow_preview(contribution, overlay)
    row = preview.rows[0]
    assert row.interpretation_status == "ambiguous"
    assert row.shadow_temporal_scope is not None
    assert row.shadow_temporal_scope.get("occurrence_time") is None


def test_scenario_f_same_source_and_occurrence_when_explicitly_annotated() -> None:
    contribution = _contribution(_candidate_assertion(temporal_scope={"session_id": "session-12"}))
    assertion = contribution.candidate_assertions[0]
    overlay = _build_overlay(
        contribution,
        [_resolved_annotation(assertion, occurrence_time=_point_extent("session-12"))],
    )
    preview = build_temporal_shadow_preview(contribution, overlay)
    scope = preview.rows[0].shadow_temporal_scope
    assert scope["source_time"]["session_id"] == "session-12"
    assert scope["occurrence_time"]["point"]["session_id"] == "session-12"


def test_scenario_g_foreign_evidence_attack_fails() -> None:
    contribution = _contribution(_candidate_assertion(temporal_scope={"session_id": "session-12"}))
    assertion = contribution.candidate_assertions[0]
    overlay = _build_overlay(
        contribution,
        [
            TemporalAssertionAnnotationV1(
                annotation_id="ann-g",
                base_assertion_id=assertion.assertion_id,
                interpretation_status="resolved",
                occurrence_time=_point_extent("session-20"),
                evidence_ref_ids=["evidence:stolen:ref"],
            )
        ],
    )
    _expect_build_error(contribution, overlay, code="annotation_evidence_not_owned")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _write_contribution(path: Any, contribution: Any) -> None:
    path.write_text(
        json.dumps(contribution.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _write_overlay(path: Any, overlay: TemporalAnnotationOverlayV1) -> None:
    path.write_text(
        json.dumps(overlay.model_dump(mode="json", by_alias=True), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def test_cli_writes_preview_with_expected_schema(tmp_path: Any) -> None:
    contribution = _contribution(_candidate_assertion(temporal_scope={"session_id": "session-12"}))
    assertion = contribution.candidate_assertions[0]
    overlay = _build_overlay(
        contribution,
        [_resolved_annotation(assertion, occurrence_time=_point_extent("session-20"))],
    )
    contrib_path = tmp_path / "contribution.json"
    overlay_path = tmp_path / "overlay.json"
    out_path = tmp_path / "preview.json"
    _write_contribution(contrib_path, contribution)
    _write_overlay(overlay_path, overlay)
    code = shadow_cli_main(
        [
            "--contribution",
            str(contrib_path),
            "--overlay",
            str(overlay_path),
            "--output",
            str(out_path),
        ]
    )
    assert code == 0
    payload = json.loads(out_path.read_text(encoding="utf-8"))
    assert payload["schema"] == TEMPORAL_SHADOW_PREVIEW_SCHEMA


def test_cli_invalid_overlay_exits_nonzero(tmp_path: Any) -> None:
    contribution = _contribution(_candidate_assertion(temporal_scope={"session_id": "session-12"}))
    contrib_path = tmp_path / "contribution.json"
    overlay_path = tmp_path / "overlay.json"
    out_path = tmp_path / "preview.json"
    _write_contribution(contrib_path, contribution)
    overlay_path.write_text('{"schema":"dmb_temporal_annotation_overlay_v1"}\n', encoding="utf-8")
    code = shadow_cli_main(
        [
            "--contribution",
            str(contrib_path),
            "--overlay",
            str(overlay_path),
            "--output",
            str(out_path),
        ]
    )
    assert code == 1
    assert not out_path.exists()


def test_cli_existing_output_requires_overwrite(tmp_path: Any) -> None:
    contribution = _contribution(_candidate_assertion(temporal_scope={"session_id": "session-12"}))
    assertion = contribution.candidate_assertions[0]
    overlay = _build_overlay(
        contribution,
        [_resolved_annotation(assertion, occurrence_time=_point_extent("session-20"))],
    )
    contrib_path = tmp_path / "contribution.json"
    overlay_path = tmp_path / "overlay.json"
    out_path = tmp_path / "preview.json"
    _write_contribution(contrib_path, contribution)
    _write_overlay(overlay_path, overlay)
    out_path.write_text("{}\n", encoding="utf-8")
    blocked = shadow_cli_main(
        [
            "--contribution",
            str(contrib_path),
            "--overlay",
            str(overlay_path),
            "--output",
            str(out_path),
        ]
    )
    assert blocked == 1
    allowed = shadow_cli_main(
        [
            "--contribution",
            str(contrib_path),
            "--overlay",
            str(overlay_path),
            "--output",
            str(out_path),
            "--overwrite",
        ]
    )
    assert allowed == 0
    payload = json.loads(out_path.read_text(encoding="utf-8"))
    assert payload["schema"] == TEMPORAL_SHADOW_PREVIEW_SCHEMA


def test_shadow_assertion_id_matches_compute_assertion_id_for_shadow_scope() -> None:
    contribution = _contribution(_candidate_assertion(temporal_scope={"session_id": "session-12"}))
    assertion = contribution.candidate_assertions[0]
    overlay = _build_overlay(
        contribution,
        [_resolved_annotation(assertion, occurrence_time=_point_extent("session-20"))],
    )
    preview = build_temporal_shadow_preview(contribution, overlay)
    row = preview.rows[0]
    expected = compute_assertion_id(
        assertion_kind=assertion.assertion_kind,
        subject_node_id=assertion.subject_node_id,
        target_node_id=assertion.target_node_id,
        predicate=assertion.predicate,
        label=assertion.label,
        value=assertion.value,
        campaign_scope=assertion.campaign_scope,
        temporal_scope=row.shadow_temporal_scope,
        epistemic_kind=assertion.epistemic_kind,
        visibility=assertion.visibility,
    )
    assert row.shadow_assertion_id == expected
