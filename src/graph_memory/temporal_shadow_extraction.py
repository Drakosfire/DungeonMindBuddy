"""Evidence-bound model shadow temporal extraction (TL01B)."""

from __future__ import annotations

import hashlib
import json
import os
import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, Protocol

from openai import OpenAI
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from src.bootstrap_env import load_dungeonmindbuddy_dotenv
from src.llm.api_client import DungeonMindApiClient
from graph_memory.extraction.category_candidate_graph_extractor import (
    resolve_category_graph_model,
)
from graph_memory.kernel.contribution_models import (
    GraphContribution,
    GraphContributionAssertion,
)
from graph_memory.kernel.contributions import (
    compute_assertion_id,
    compute_contribution_source_payload_sha256,
    explicit_assertion_evidence_ref_ids,
    semantic_assertion_value,
)
from graph_memory.kernel.temporal import (
    TemporalExtentV1,
    TemporalIntervalExtentV1,
    TemporalIntervalV1,
    TemporalPointExtentV1,
    TemporalPointV1,
)
from graph_memory.source_span import (
    SourceArtifactText,
    SourceSpanRef,
    analyze_evidence_resolution,
    resolve_many_source_span_refs,
    source_span_ref_from_dict,
)
from graph_memory.temporal_shadow import (
    TEMPORAL_ANNOTATION_OVERLAY_SCHEMA,
    TemporalAnnotationOverlayV1,
    TemporalAssertionAnnotationV1,
    TemporalOverlayProducerV1,
    TemporalShadowBuildError,
    TemporalShadowPreviewV1,
    build_temporal_shadow_preview,
    compute_temporal_overlay_id,
    derive_assertion_source_time,
    load_temporal_annotation_overlay,
)
from graph_memory.temporal_shadow_extraction_schema import (
    TEMPORAL_MODEL_ANNOTATION_BATCH_SCHEMA,
    TEMPORAL_SHADOW_COMPARISON_SCHEMA,
    TEMPORAL_SHADOW_EXTRACTION_CASE_SCHEMA,
    TEMPORAL_SHADOW_EXTRACTION_RUN_SCHEMA,
    TEMPORAL_SHADOW_PROMPT_VERSION,
    TemporalModelAnnotationBatchTransportV1,
    TemporalModelAnnotationTransportV1,
    temporal_model_annotation_batch_text_format,
)

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class TemporalShadowExtractionError(Exception):
    def __init__(
        self,
        message: str,
        *,
        code: str,
        diagnostics: list[str] | None = None,
        affected_assertion_id: str | None = None,
        provider_response_id: str | None = None,
        foreign_evidence_attempts: int = 0,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.diagnostics = list(diagnostics or [message])
        self.affected_assertion_id = affected_assertion_id
        self.provider_response_id = provider_response_id
        self.foreign_evidence_attempts = int(foreign_evidence_attempts)


class _CaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, populate_by_name=True)


class EvidenceRegistryEntryV1(_CaseModel):
    evidence_ref_id: str
    source_artifact_id: str
    source_artifact_path: str
    content_sha256: str
    source_ref_id: str
    start_line: int
    end_line: int
    label: str | None = None
    artifact_kind: str = "markdown_recap"
    evidence_role: str = "observation"
    visibility_state: str = "player_safe"

    @field_validator("content_sha256", mode="after")
    @classmethod
    def _sha(cls, value: str) -> str:
        if not _SHA256_RE.match(value):
            raise ValueError("content_sha256 must be lowercase hex sha256")
        return value


class TemporalShadowExtractionCaseV1(_CaseModel):
    schema_: Literal["dmb_temporal_shadow_extraction_case_v1"] = Field(
        default=TEMPORAL_SHADOW_EXTRACTION_CASE_SCHEMA,
        alias="schema",
    )
    case_id: str
    base_contribution_path: str
    base_contribution_sha256: str
    gold_overlay_path: str
    gold_overlay_sha256: str
    selected_assertion_ids: list[str]
    evidence_registry: list[EvidenceRegistryEntryV1]
    snippet_max_chars: int = 2000
    prompt_version: str = TEMPORAL_SHADOW_PROMPT_VERSION

    @field_validator("selected_assertion_ids", mode="after")
    @classmethod
    def _selected_unique_nonempty(cls, value: list[str]) -> list[str]:
        if not value:
            raise ValueError("selected_assertion_ids must be non-empty")
        if len(set(value)) != len(value):
            raise ValueError("selected_assertion_ids must be unique")
        return value

    @field_validator("base_contribution_sha256", "gold_overlay_sha256", mode="after")
    @classmethod
    def _sha_fields(cls, value: str) -> str:
        if not _SHA256_RE.match(value):
            raise ValueError("digest fields must be lowercase hex sha256")
        return value


ComparisonVerdict = Literal["pass", "partial", "fail"]
EvaluationVerdict = Literal[
    "SAFE_FOR_NEXT_EXPERIMENT",
    "ITERATE_PROMPT",
    "BLOCKED_BY_EVIDENCE",
    "BLOCKED_BY_CONTRACT",
    "PROVIDER_FAILURE",
]
ComparisonClassification = Literal[
    "exact_match",
    "safe_under_resolution",
    "unsafe_over_resolution",
    "wrong_temporal_lane",
    "status_mismatch",
    "semantic_mismatch",
    "wrong_temporal_value",
    "missing_prediction",
    "extra_prediction",
]


class TemporalShadowComparisonRowV1(_CaseModel):
    base_assertion_id: str
    classification: ComparisonClassification
    gold_interpretation_status: str | None = None
    predicted_interpretation_status: str | None = None
    diagnostics: list[str] = Field(default_factory=list)


class TemporalShadowComparisonMetricsV1(_CaseModel):
    total_gold_annotations: int
    exact_match_count: int
    exact_semantic_match_count: int = 0
    resolved_exact_match_count: int = 0
    safe_under_resolution_count: int = 0
    unsafe_over_resolution_count: int = 0
    wrong_temporal_lane_count: int = 0
    status_mismatch_count: int
    semantic_mismatch_count: int
    missing_prediction_count: int
    extra_prediction_count: int
    # Safety
    source_to_occurrence_false_positives: int = 0
    source_to_valid_time_false_positives: int = 0
    unsupported_resolved_annotations: int = 0
    foreign_evidence_attempts: int = 0
    ungrounded_source_phrases: int = 0
    invalid_temporal_payloads: int = 0
    # Evidence selection (owned evidence; not ownership violations)
    evidence_selection_mismatch_count: int = 0
    # Quality
    status_accuracy: float = 0.0
    ambiguous_or_unresolved_count: int = 0
    not_applicable_accuracy: float = 0.0


class TemporalShadowComparisonV1(_CaseModel):
    schema_: Literal["dmb_temporal_shadow_comparison_v1"] = Field(
        default=TEMPORAL_SHADOW_COMPARISON_SCHEMA,
        alias="schema",
    )
    verdict: ComparisonVerdict
    evaluation_verdict: EvaluationVerdict
    metrics: TemporalShadowComparisonMetricsV1
    rows: list[TemporalShadowComparisonRowV1] = Field(default_factory=list)


class TemporalShadowSourceArtifactDigestV1(_CaseModel):
    source_artifact_id: str
    content_sha256: str


class TemporalShadowExtractionRunV1(_CaseModel):
    schema_: Literal["dmb_temporal_shadow_extraction_run_v1"] = Field(
        default=TEMPORAL_SHADOW_EXTRACTION_RUN_SCHEMA,
        alias="schema",
    )
    run_id: str
    case_id: str
    case_digest: str
    repository_sha: str
    overlay_id: str
    base_contribution_id: str
    base_contribution_source_payload_sha256: str
    selected_assertion_ids: list[str]
    source_artifacts: list[TemporalShadowSourceArtifactDigestV1]
    comparison_verdict: ComparisonVerdict
    evaluation_verdict: EvaluationVerdict
    preview_verdict: str
    model_id: str
    prompt_version: str
    executed_prompt_version: str
    provider_response_id: str
    input_tokens: int
    output_tokens: int
    elapsed_ms: float


TEMPORAL_SHADOW_FAILURE_MANIFEST_SCHEMA = "dmb_temporal_shadow_extraction_failure_v1"


class TemporalShadowExtractionFailureV1(_CaseModel):
    schema_: Literal["dmb_temporal_shadow_extraction_failure_v1"] = Field(
        default=TEMPORAL_SHADOW_FAILURE_MANIFEST_SCHEMA,
        alias="schema",
    )
    case_id: str
    case_digest: str
    base_contribution_id: str
    base_contribution_source_payload_sha256: str
    model_id: str
    executed_prompt_version: str
    failure_code: str
    diagnostics: list[str] = Field(default_factory=list)
    provider_response_id: str | None = None
    affected_assertion_id: str | None = None
    foreign_evidence_attempts: int = 0


@dataclass(frozen=True)
class ProviderMeta:
    response_id: str
    model_id: str
    input_tokens: int
    output_tokens: int
    elapsed_ms: float


def _canonical_json(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _resolve_repo_relative(path_str: str, *, repo_root: Path) -> Path:
    raw = path_str.strip()
    if not raw:
        raise TemporalShadowExtractionError("empty path", code="path_escape")
    if raw.startswith("/") or raw.startswith("\\"):
        raise TemporalShadowExtractionError(
            f"absolute paths forbidden: {raw!r}",
            code="path_escape",
        )
    parts = Path(raw).parts
    if ".." in parts:
        raise TemporalShadowExtractionError(
            f"path traversal forbidden: {raw!r}",
            code="path_escape",
        )
    resolved = (repo_root / raw).resolve()
    try:
        resolved.relative_to(repo_root.resolve())
    except ValueError as exc:
        raise TemporalShadowExtractionError(
            f"path escapes repo root: {raw!r}",
            code="path_escape",
        ) from exc
    return resolved


def _validate_candidate_only_base(contribution: GraphContribution) -> None:
    if contribution.status != "active":
        raise TemporalShadowExtractionError(
            f"Base contribution status must be 'active', got {contribution.status!r}",
            code="invalid_case",
        )
    if not contribution.candidate_assertions:
        raise TemporalShadowExtractionError(
            "Base contribution must contain non-empty candidate_assertions",
            code="invalid_case",
        )
    if contribution.accepted_assertions or contribution.rejected_assertions:
        raise TemporalShadowExtractionError(
            "Base contribution must be candidate-only",
            code="invalid_case",
        )
    seen: set[str] = set()
    for assertion in contribution.candidate_assertions:
        if assertion.acceptance_state != "candidate":
            raise TemporalShadowExtractionError(
                "Every candidate assertion must have acceptance_state='candidate'",
                code="invalid_case",
                affected_assertion_id=assertion.assertion_id,
            )
        if assertion.assertion_id in seen:
            raise TemporalShadowExtractionError(
                "Duplicate candidate assertion_id values",
                code="invalid_case",
                affected_assertion_id=assertion.assertion_id,
            )
        seen.add(assertion.assertion_id)
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
            raise TemporalShadowExtractionError(
                "Candidate assertion_id is not canonical",
                code="invalid_case",
                affected_assertion_id=assertion.assertion_id,
                diagnostics=[f"canonical={canonical_id!r}"],
            )


def load_temporal_shadow_extraction_case(
    path: Path | str,
    *,
    repo_root: Path,
) -> TemporalShadowExtractionCaseV1:
    case_path = Path(path)
    try:
        payload = json.loads(case_path.read_text(encoding="utf-8"))
        case = TemporalShadowExtractionCaseV1.model_validate(payload)
    except (OSError, json.JSONDecodeError, ValidationError) as exc:
        raise TemporalShadowExtractionError(
            "Invalid temporal shadow extraction case",
            code="invalid_case",
            diagnostics=[str(exc)],
        ) from exc

    base_path = _resolve_repo_relative(case.base_contribution_path, repo_root=repo_root)
    if not base_path.is_file():
        raise TemporalShadowExtractionError(
            f"Missing base contribution: {case.base_contribution_path}",
            code="invalid_case",
        )
    actual_base_sha = _file_sha256(base_path)
    if actual_base_sha != case.base_contribution_sha256:
        raise TemporalShadowExtractionError(
            "base_contribution_sha256 mismatch",
            code="digest_mismatch",
            diagnostics=[
                f"expected={case.base_contribution_sha256!r}",
                f"actual={actual_base_sha!r}",
            ],
        )

    try:
        contribution_payload = json.loads(base_path.read_text(encoding="utf-8"))
        contribution = GraphContribution.model_validate(contribution_payload)
    except (ValidationError, json.JSONDecodeError) as exc:
        raise TemporalShadowExtractionError(
            "Invalid base GraphContribution",
            code="invalid_case",
            diagnostics=[str(exc)],
        ) from exc
    _validate_candidate_only_base(contribution)

    base_by_id = {a.assertion_id: a for a in contribution.candidate_assertions}
    for assertion_id in case.selected_assertion_ids:
        if assertion_id not in base_by_id:
            raise TemporalShadowExtractionError(
                f"selected_assertion_id not in base contribution: {assertion_id!r}",
                code="selected_assertion_invalid",
                affected_assertion_id=assertion_id,
            )

    registry_ids = {entry.evidence_ref_id for entry in case.evidence_registry}
    if len(registry_ids) != len(case.evidence_registry):
        seen: set[str] = set()
        dupes: list[str] = []
        for entry in case.evidence_registry:
            if entry.evidence_ref_id in seen:
                dupes.append(entry.evidence_ref_id)
            seen.add(entry.evidence_ref_id)
        raise TemporalShadowExtractionError(
            "Duplicate evidence_ref_id in evidence registry",
            code="invalid_case",
            diagnostics=[f"duplicates={sorted(set(dupes))!r}"],
        )

    artifact_defs: dict[str, tuple[str, str, str, str, str, str, str | None]] = {}
    for entry in case.evidence_registry:
        fingerprint = (
            entry.source_artifact_path,
            entry.content_sha256,
            entry.source_ref_id,
            entry.artifact_kind,
            entry.evidence_role,
            entry.visibility_state,
            entry.label,
        )
        prior = artifact_defs.get(entry.source_artifact_id)
        if prior is not None and prior != fingerprint:
            raise TemporalShadowExtractionError(
                "Conflicting source artifact definitions for same source_artifact_id",
                code="invalid_case",
                diagnostics=[
                    f"source_artifact_id={entry.source_artifact_id!r}",
                    f"prior={prior!r}",
                    f"current={fingerprint!r}",
                ],
            )
        artifact_defs[entry.source_artifact_id] = fingerprint

    for assertion_id in case.selected_assertion_ids:
        assertion = base_by_id[assertion_id]
        owned = set(explicit_assertion_evidence_ref_ids(assertion))
        missing = owned - registry_ids
        if missing:
            raise TemporalShadowExtractionError(
                "Evidence registry missing owned evidence for selected assertion",
                code="invalid_case",
                affected_assertion_id=assertion_id,
                diagnostics=[f"missing={sorted(missing)!r}"],
            )

    for entry in case.evidence_registry:
        artifact_path = _resolve_repo_relative(
            entry.source_artifact_path, repo_root=repo_root
        )
        if not artifact_path.is_file():
            raise TemporalShadowExtractionError(
                f"Missing source artifact: {entry.source_artifact_path}",
                code="invalid_case",
            )
        actual_artifact_sha = _file_sha256(artifact_path)
        if actual_artifact_sha != entry.content_sha256:
            raise TemporalShadowExtractionError(
                "source artifact content_sha256 mismatch",
                code="digest_mismatch",
                diagnostics=[
                    f"path={entry.source_artifact_path!r}",
                    f"expected={entry.content_sha256!r}",
                    f"actual={actual_artifact_sha!r}",
                ],
            )

    gold_path = _resolve_repo_relative(case.gold_overlay_path, repo_root=repo_root)
    if not gold_path.is_file():
        raise TemporalShadowExtractionError(
            f"Missing gold overlay: {case.gold_overlay_path}",
            code="invalid_case",
        )
    actual_gold_sha = _file_sha256(gold_path)
    if actual_gold_sha != case.gold_overlay_sha256:
        raise TemporalShadowExtractionError(
            "gold_overlay_sha256 mismatch",
            code="digest_mismatch",
            diagnostics=[
                f"expected={case.gold_overlay_sha256!r}",
                f"actual={actual_gold_sha!r}",
            ],
        )

    resolve_prompt_instructions(case.prompt_version)
    load_bound_gold_overlay(case, contribution, repo_root=repo_root)
    return case


def resolve_prompt_instructions(prompt_version: str) -> tuple[str, str]:
    """Return (instructions, executed_prompt_version) or fail closed."""
    if prompt_version != TEMPORAL_SHADOW_PROMPT_VERSION:
        raise TemporalShadowExtractionError(
            f"Unsupported prompt_version: {prompt_version!r}",
            code="unsupported_prompt_version",
            diagnostics=[
                f"supported={TEMPORAL_SHADOW_PROMPT_VERSION!r}",
                f"declared={prompt_version!r}",
            ],
        )
    return TEMPORAL_SHADOW_SYSTEM_INSTRUCTIONS, TEMPORAL_SHADOW_PROMPT_VERSION


def load_bound_gold_overlay(
    case: TemporalShadowExtractionCaseV1,
    contribution: GraphContribution,
    *,
    repo_root: Path,
) -> TemporalAnnotationOverlayV1:
    gold_path = _resolve_repo_relative(case.gold_overlay_path, repo_root=repo_root)
    try:
        gold = load_temporal_annotation_overlay(
            json.loads(gold_path.read_text(encoding="utf-8"))
        )
    except TemporalShadowBuildError as exc:
        raise TemporalShadowExtractionError(
            f"Invalid gold overlay: {exc}",
            code="invalid_gold_overlay",
            diagnostics=list(exc.diagnostics),
        ) from exc

    if gold.producer.kind != "human_gold":
        raise TemporalShadowExtractionError(
            'Gold overlay producer.kind must be "human_gold"',
            code="invalid_gold_overlay",
            diagnostics=[f"producer.kind={gold.producer.kind!r}"],
        )

    if gold.base_contribution_id != contribution.contribution_id:
        raise TemporalShadowExtractionError(
            "Gold overlay base_contribution_id mismatch",
            code="invalid_gold_overlay",
            diagnostics=[
                f"expected={contribution.contribution_id!r}",
                f"actual={gold.base_contribution_id!r}",
            ],
        )

    expected_digest = compute_contribution_source_payload_sha256(contribution)
    if gold.base_contribution_source_payload_sha256 != expected_digest:
        raise TemporalShadowExtractionError(
            "Gold overlay source-payload digest mismatch",
            code="invalid_gold_overlay",
            diagnostics=[
                f"expected={expected_digest!r}",
                f"actual={gold.base_contribution_source_payload_sha256!r}",
            ],
        )

    gold_targets = [ann.base_assertion_id for ann in gold.annotations]
    if len(gold_targets) != len(set(gold_targets)):
        raise TemporalShadowExtractionError(
            "Gold overlay has duplicate assertion targets",
            code="invalid_gold_overlay",
        )
    if set(gold_targets) != set(case.selected_assertion_ids):
        raise TemporalShadowExtractionError(
            "Gold overlay targets must exactly equal selected_assertion_ids",
            code="invalid_gold_overlay",
            diagnostics=[
                f"expected={sorted(case.selected_assertion_ids)!r}",
                f"actual={sorted(gold_targets)!r}",
            ],
        )
    return gold


def _load_contribution_for_case(
    case: TemporalShadowExtractionCaseV1, *, repo_root: Path
) -> GraphContribution:
    base_path = _resolve_repo_relative(case.base_contribution_path, repo_root=repo_root)
    payload = json.loads(base_path.read_text(encoding="utf-8"))
    contribution = GraphContribution.model_validate(payload)
    _validate_candidate_only_base(contribution)
    return contribution


def _load_text_artifacts(
    case: TemporalShadowExtractionCaseV1, *, repo_root: Path
) -> dict[str, SourceArtifactText]:
    artifacts: dict[str, SourceArtifactText] = {}
    for entry in case.evidence_registry:
        if entry.source_artifact_id in artifacts:
            continue
        path = _resolve_repo_relative(entry.source_artifact_path, repo_root=repo_root)
        text = path.read_text(encoding="utf-8")
        artifacts[entry.source_artifact_id] = SourceArtifactText(
            source_artifact_id=entry.source_artifact_id,
            source_ref_id=entry.source_ref_id,
            artifact_kind=entry.artifact_kind,
            label=entry.label or entry.source_artifact_path,
            text=text,
            evidence_role=entry.evidence_role,
            visibility_state=entry.visibility_state,
        )
    return artifacts


def build_assertion_evidence_packets(
    contribution: GraphContribution,
    case: TemporalShadowExtractionCaseV1,
    *,
    repo_root: Path,
) -> dict[str, dict[str, Any]]:
    base_by_id = {a.assertion_id: a for a in contribution.candidate_assertions}
    registry_by_evidence = {e.evidence_ref_id: e for e in case.evidence_registry}
    text_artifacts = _load_text_artifacts(case, repo_root=repo_root)
    packets: dict[str, dict[str, Any]] = {}

    for assertion_id in case.selected_assertion_ids:
        assertion = base_by_id[assertion_id]
        owned = explicit_assertion_evidence_ref_ids(assertion)
        refs: list[SourceSpanRef] = []
        for evidence_id in owned:
            entry = registry_by_evidence.get(evidence_id)
            if entry is None:
                raise TemporalShadowExtractionError(
                    f"Missing evidence registry entry for {evidence_id!r}",
                    code="evidence_unresolved",
                    affected_assertion_id=assertion_id,
                )
            refs.append(
                SourceSpanRef(
                    source_ref_id=entry.source_ref_id,
                    source_artifact_id=entry.source_artifact_id,
                    start_line=entry.start_line,
                    end_line=entry.end_line,
                    label=entry.label,
                    artifact_kind=entry.artifact_kind,
                    evidence_role=entry.evidence_role,
                    visibility_state=entry.visibility_state,
                )
            )

        resolved = resolve_many_source_span_refs(
            refs,
            text_artifacts=text_artifacts,
            snippet_max_chars=case.snippet_max_chars,
        )
        report = analyze_evidence_resolution(refs, resolved)
        blockers = [
            issue
            for issue in report.issues
            if issue.severity in {"error", "blocker"}
        ]
        if blockers:
            raise TemporalShadowExtractionError(
                "Evidence resolution blockers",
                code="evidence_unresolved",
                affected_assertion_id=assertion_id,
                diagnostics=[issue.message for issue in blockers],
            )

        snippets: list[dict[str, Any]] = []
        for evidence_id, resolved_item in zip(owned, resolved, strict=True):
            if not resolved_item.preview_snippet.strip():
                raise TemporalShadowExtractionError(
                    f"Empty snippet for evidence {evidence_id!r}",
                    code="evidence_unresolved",
                    affected_assertion_id=assertion_id,
                )
            snippets.append(
                {
                    "evidence_ref_id": evidence_id,
                    "preview_snippet": resolved_item.preview_snippet,
                    "start_line": resolved_item.start_line,
                    "end_line": resolved_item.end_line,
                }
            )

        packets[assertion_id] = {
            "base_assertion_id": assertion_id,
            "assertion_kind": assertion.assertion_kind,
            "subject_node_id": assertion.subject_node_id,
            "target_node_id": assertion.target_node_id,
            "predicate": assertion.predicate,
            "label": assertion.label,
            "semantic_value": semantic_assertion_value(assertion.value),
            "campaign_scope": assertion.campaign_scope,
            "temporal_scope": assertion.temporal_scope,
            "evidence_snippets": snippets,
        }
    return packets


TEMPORAL_SHADOW_SYSTEM_INSTRUCTIONS = """You annotate temporal interpretation for candidate graph assertions using ONLY the supplied evidence snippets.

Rules (fail closed):
- source_time / recap session is NOT occurrence_time. Never set occurrence_time or valid_time merely because the evidence comes from a session recap or legacy temporal_scope.session_id.
- occurrence_time is when the described fiction event happened; valid_time is when a persistent state holds.
- Use interpretation_status=resolved only when you supply occurrence_time and/or valid_time grounded in the snippet text.
- Use not_applicable when fiction-time does not apply to the assertion (scene framing, structural edges, observation-only scope).
- Use ambiguous when multiple distinct fiction-time readings are plausible; include source_phrase and diagnostics.
- Use unresolved when fiction-time may apply but cannot be grounded; include source_phrase and/or diagnostics.
- evidence_ref_ids must be subsets of the packet's owned evidence only.
- source_phrase must be a verbatim substring of a cited snippet (whitespace may differ).
- Return one annotation per requested base_assertion_id, no extras, no omissions.

Temporal point kind-exclusive fields (all other point fields MUST be JSON null):
- kind=session → require session_id; optional campaign_id, raw_expression; forbid value, calendar_id, relation, anchor_ref
- kind=campaign_date → require value; optional calendar_id, campaign_id, raw_expression; forbid session_id, relation, anchor_ref
- kind=relative → require relation+anchor_ref OR raw_expression; optional campaign_id; forbid session_id, value, calendar_id
- kind=textual → require raw_expression; optional campaign_id; forbid session_id, value, calendar_id, relation, anchor_ref
- kind=unknown → optional raw_expression, campaign_id; forbid session_id, value, calendar_id, relation, anchor_ref
"""


def render_temporal_shadow_user_content(
    packets: dict[str, dict[str, Any]],
    selected_ids: list[str],
) -> str:
    ordered = [packets[assertion_id] for assertion_id in selected_ids]
    payload = {
        "schema": TEMPORAL_MODEL_ANNOTATION_BATCH_SCHEMA,
        "selected_assertion_ids": list(selected_ids),
        "assertion_packets": ordered,
    }
    return json.dumps(payload, indent=2, ensure_ascii=True)


class TemporalShadowExtractionClient(Protocol):
    def extract_annotations(
        self,
        *,
        instructions: str,
        user_content: str,
        model_id: str,
    ) -> tuple[dict[str, Any], ProviderMeta]: ...


def _usage_from_response(response: Any) -> tuple[int, int]:
    usage = getattr(response, "usage", None)
    if usage is None:
        return 0, 0
    return (
        int(getattr(usage, "input_tokens", 0) or 0),
        int(getattr(usage, "output_tokens", 0) or 0),
    )


class OpenAITemporalShadowExtractionClient:
    def extract_annotations(
        self,
        *,
        instructions: str,
        user_content: str,
        model_id: str,
    ) -> tuple[dict[str, Any], ProviderMeta]:
        load_dungeonmindbuddy_dotenv()
        raw_client = OpenAI()
        api_client = DungeonMindApiClient.wrap(raw_client)
        text_format = temporal_model_annotation_batch_text_format()
        try:
            call = api_client.responses_create(
                action="temporal_shadow.extract_annotations",
                model=model_id,
                instructions=instructions,
                input=[{"type": "message", "role": "user", "content": user_content}],
                text=text_format,
            )
        except Exception as exc:
            raise TemporalShadowExtractionError(
                f"OpenAI responses.create failed: {exc}",
                code="provider_error",
            ) from exc
        response = call.response
        elapsed_ms = call.elapsed_ms
        response_id = str(getattr(response, "id", "") or "") or None
        refusal = getattr(response, "refusal", None)
        if refusal:
            raise TemporalShadowExtractionError(
                f"model refused: {refusal}",
                code="provider_refusal",
                provider_response_id=response_id,
            )
        if getattr(response, "status", None) == "incomplete":
            raw = getattr(response, "output_text", None) or response.model_dump_json()
            raise TemporalShadowExtractionError(
                "model response incomplete",
                code="provider_incomplete",
                diagnostics=[str(raw)[:2000]],
                provider_response_id=response_id,
            )
        raw_text = (getattr(response, "output_text", None) or "").strip()
        if not raw_text:
            raise TemporalShadowExtractionError(
                "model response missing output_text",
                code="provider_error",
                provider_response_id=response_id,
            )
        try:
            parsed = json.loads(raw_text)
        except json.JSONDecodeError as exc:
            raise TemporalShadowExtractionError(
                f"invalid model JSON: {exc.msg}",
                code="invalid_model_output",
                diagnostics=[raw_text[:2000]],
            ) from exc

        input_tokens, output_tokens = _usage_from_response(response)
        meta = ProviderMeta(
            response_id=str(getattr(response, "id", "") or ""),
            model_id=model_id,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            elapsed_ms=elapsed_ms,
        )
        return parsed, meta


class FakeTemporalShadowExtractionClient:
    def __init__(self, batch: dict[str, Any]) -> None:
        self._batch = batch

    def extract_annotations(
        self,
        *,
        instructions: str,
        user_content: str,
        model_id: str,
    ) -> tuple[dict[str, Any], ProviderMeta]:
        _ = (instructions, user_content)
        meta = ProviderMeta(
            response_id="fake-response",
            model_id=model_id,
            input_tokens=0,
            output_tokens=0,
            elapsed_ms=0.0,
        )
        return dict(self._batch), meta


def _normalize_ws(text: str) -> str:
    return " ".join(text.split())


def compute_temporal_annotation_id(
    *,
    case_id: str,
    model_id: str,
    prompt_version: str,
    base_assertion_id: str,
    interpretation_status: str,
    occurrence_time: TemporalExtentV1 | None,
    valid_time: TemporalIntervalV1 | None,
    evidence_ref_ids: list[str],
    source_phrase: str | None,
    extraction_confidence: str,
    diagnostics: list[str],
) -> str:
    from graph_memory.temporal_shadow import _extent_dump, _interval_dump

    payload = {
        "base_assertion_id": base_assertion_id,
        "case_id": case_id,
        "diagnostics": list(diagnostics),
        "evidence_ref_ids": sorted(evidence_ref_ids),
        "extraction_confidence": extraction_confidence,
        "interpretation_status": interpretation_status,
        "model_id": model_id,
        "occurrence_time": (
            _extent_dump(occurrence_time) if occurrence_time is not None else None
        ),
        "prompt_version": prompt_version,
        "source_phrase": source_phrase,
        "valid_time": _interval_dump(valid_time) if valid_time is not None else None,
    }
    digest = hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()[:16]
    return f"temporal-annotation:{digest}"


def compute_temporal_shadow_run_id(
    *,
    case_id: str,
    case_digest: str,
    model_id: str,
    prompt_version: str,
    validated_model_output: dict[str, Any],
) -> str:
    payload = {
        "case_digest": case_digest,
        "case_id": case_id,
        "model_id": model_id,
        "prompt_version": prompt_version,
        "validated_model_output": validated_model_output,
    }
    digest = hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()[:16]
    return f"temporal-shadow-run:{digest}"


def _transport_to_annotation(
    item: TemporalModelAnnotationTransportV1,
    *,
    case_id: str,
    model_id: str,
    prompt_version: str,
) -> TemporalAssertionAnnotationV1:
    occurrence = (
        item.occurrence_time.to_temporal_extent_v1()
        if item.occurrence_time is not None
        else None
    )
    valid = item.valid_time.to_temporal_interval_v1() if item.valid_time is not None else None
    annotation_id = compute_temporal_annotation_id(
        case_id=case_id,
        model_id=model_id,
        prompt_version=prompt_version,
        base_assertion_id=item.base_assertion_id,
        interpretation_status=item.interpretation_status,
        occurrence_time=occurrence,
        valid_time=valid,
        evidence_ref_ids=item.evidence_ref_ids,
        source_phrase=item.source_phrase,
        extraction_confidence=item.extraction_confidence,
        diagnostics=item.diagnostics,
    )
    return TemporalAssertionAnnotationV1(
        annotation_id=annotation_id,
        base_assertion_id=item.base_assertion_id,
        interpretation_status=item.interpretation_status,
        occurrence_time=occurrence,
        valid_time=valid,
        evidence_ref_ids=list(item.evidence_ref_ids),
        source_phrase=item.source_phrase,
        extraction_confidence=item.extraction_confidence,
        diagnostics=list(item.diagnostics),
    )


def _require_grounded_source_phrase(
    *,
    item: TemporalModelAnnotationTransportV1,
    packets: dict[str, dict[str, Any]],
    required: bool,
) -> None:
    phrase = item.source_phrase
    if phrase is None:
        if required:
            raise TemporalShadowExtractionError(
                "resolved annotation requires nonblank source_phrase",
                code="grounding_failure",
                affected_assertion_id=item.base_assertion_id,
            )
        return
    if not phrase.strip():
        raise TemporalShadowExtractionError(
            "source_phrase must be nonblank when supplied",
            code="grounding_failure",
            affected_assertion_id=item.base_assertion_id,
        )
    normalized_phrase = _normalize_ws(phrase)
    if not normalized_phrase:
        raise TemporalShadowExtractionError(
            "source_phrase must be nonblank when supplied",
            code="grounding_failure",
            affected_assertion_id=item.base_assertion_id,
        )
    found = False
    for evidence_id in item.evidence_ref_ids:
        snippet_entries = packets[item.base_assertion_id]["evidence_snippets"]
        text = next(
            s["preview_snippet"]
            for s in snippet_entries
            if s["evidence_ref_id"] == evidence_id
        )
        if normalized_phrase in _normalize_ws(text):
            found = True
            break
    if not found:
        raise TemporalShadowExtractionError(
            "source_phrase not found verbatim in cited snippets",
            code="grounding_failure",
            affected_assertion_id=item.base_assertion_id,
            diagnostics=[f"source_phrase={phrase!r}"],
        )


def ground_and_convert_model_batch(
    *,
    raw_batch: dict[str, Any],
    contribution: GraphContribution,
    case: TemporalShadowExtractionCaseV1,
    packets: dict[str, dict[str, Any]],
    model_id: str,
    prompt_version: str,
) -> list[TemporalAssertionAnnotationV1]:
    try:
        batch = TemporalModelAnnotationBatchTransportV1.model_validate(raw_batch)
    except ValidationError as exc:
        raise TemporalShadowExtractionError(
            "Model batch failed transport validation",
            code="invalid_model_output",
            diagnostics=[str(exc)],
        ) from exc

    predicted_ids = [item.base_assertion_id for item in batch.annotations]
    if len(predicted_ids) != len(set(predicted_ids)):
        raise TemporalShadowExtractionError(
            "Model batch contains duplicate assertion targets",
            code="target_set_mismatch",
            diagnostics=[f"ids={predicted_ids!r}"],
        )
    expected_ids = set(case.selected_assertion_ids)
    if set(predicted_ids) != expected_ids:
        raise TemporalShadowExtractionError(
            "Model batch target set mismatch",
            code="target_set_mismatch",
            diagnostics=[
                f"expected={sorted(expected_ids)!r}",
                f"actual={sorted(set(predicted_ids))!r}",
            ],
        )

    base_by_id = {a.assertion_id: a for a in contribution.candidate_assertions}
    annotations: list[TemporalAssertionAnnotationV1] = []

    foreign_attempts = 0
    first_foreign_assertion: str | None = None
    foreign_diagnostics: list[str] = []
    for item in batch.annotations:
        assertion = base_by_id[item.base_assertion_id]
        owned = set(explicit_assertion_evidence_ref_ids(assertion))
        packet_snippets = packets[item.base_assertion_id]["evidence_snippets"]
        packet_ids = {entry["evidence_ref_id"] for entry in packet_snippets}
        for evidence_id in item.evidence_ref_ids:
            if evidence_id not in owned or evidence_id not in packet_ids:
                foreign_attempts += 1
                if first_foreign_assertion is None:
                    first_foreign_assertion = item.base_assertion_id
                foreign_diagnostics.append(
                    f"assertion={item.base_assertion_id!r} evidence_ref_id={evidence_id!r}"
                )

    if foreign_attempts:
        raise TemporalShadowExtractionError(
            "Annotation cites evidence not owned by assertion or missing from packet",
            code="grounding_failure",
            affected_assertion_id=first_foreign_assertion,
            foreign_evidence_attempts=foreign_attempts,
            diagnostics=_bounded_diagnostics(foreign_diagnostics),
        )

    for item in batch.annotations:
        if item.interpretation_status == "resolved":
            _require_grounded_source_phrase(
                item=item, packets=packets, required=True
            )
        else:
            if item.interpretation_status == "not_applicable":
                cleaned = [d.strip() for d in item.diagnostics if isinstance(d, str)]
                if not any(cleaned):
                    raise TemporalShadowExtractionError(
                        "not_applicable annotation requires a nonblank explanation",
                        code="grounding_failure",
                        affected_assertion_id=item.base_assertion_id,
                    )
            _require_grounded_source_phrase(
                item=item, packets=packets, required=False
            )

        try:
            annotations.append(
                _transport_to_annotation(
                    item,
                    case_id=case.case_id,
                    model_id=model_id,
                    prompt_version=prompt_version,
                )
            )
        except (ValidationError, ValueError, TypeError) as exc:
            raise TemporalShadowExtractionError(
                "Model temporal payload failed TL00 validation",
                code="invalid_model_output",
                affected_assertion_id=item.base_assertion_id,
                diagnostics=[str(exc)],
            ) from exc

    return annotations


def assemble_temporal_overlay(
    *,
    contribution: GraphContribution,
    annotations: list[TemporalAssertionAnnotationV1],
    prompt_version: str,
) -> TemporalAnnotationOverlayV1:
    digest = compute_contribution_source_payload_sha256(contribution)
    producer = TemporalOverlayProducerV1(
        kind="model_shadow",
        name="temporal-shadow-extractor",
        version=prompt_version,
    )
    overlay_id = compute_temporal_overlay_id(
        base_contribution_id=contribution.contribution_id,
        base_contribution_source_payload_sha256=digest,
        producer=producer,
        annotations=annotations,
    )
    try:
        return TemporalAnnotationOverlayV1(
            overlay_id=overlay_id,
            base_contribution_id=contribution.contribution_id,
            base_contribution_source_payload_sha256=digest,
            producer=producer,
            annotations=annotations,
        )
    except ValidationError as exc:
        raise TemporalShadowExtractionError(
            "Overlay assembly failed validation",
            code="overlay_assembly_failed",
            diagnostics=[str(exc)],
        ) from exc


def _annotation_semantic_payload(annotation: TemporalAssertionAnnotationV1) -> dict[str, Any]:
    from graph_memory.temporal_shadow import _extent_dump, _interval_dump

    return {
        "evidence_ref_ids": sorted(annotation.evidence_ref_ids),
        "interpretation_status": annotation.interpretation_status,
        "occurrence_time": (
            _extent_dump(annotation.occurrence_time)
            if annotation.occurrence_time is not None
            else None
        ),
        "valid_time": (
            _interval_dump(annotation.valid_time)
            if annotation.valid_time is not None
            else None
        ),
    }


def _lane_signature(annotation: TemporalAssertionAnnotationV1) -> tuple[bool, bool]:
    return (
        annotation.occurrence_time is not None,
        annotation.valid_time is not None,
    )


def _point_canonical(point: TemporalPointV1) -> dict[str, Any]:
    return point.model_dump(mode="json", exclude_none=True)


def _extent_contains_exact_point(
    extent: TemporalExtentV1 | None, point: TemporalPointV1
) -> bool:
    if extent is None:
        return False
    target = _point_canonical(point)
    if isinstance(extent, TemporalPointExtentV1):
        return _point_canonical(extent.point) == target
    if isinstance(extent, TemporalIntervalExtentV1):
        for boundary in (extent.start, extent.end):
            if boundary is not None and _point_canonical(boundary) == target:
                return True
    return False


def _interval_contains_exact_point(
    interval: TemporalIntervalV1 | None, point: TemporalPointV1
) -> bool:
    if interval is None:
        return False
    target = _point_canonical(point)
    for boundary in (interval.start, interval.end):
        if boundary is not None and _point_canonical(boundary) == target:
            return True
    return False


def _derive_comparison_source_time(
    contribution: GraphContribution,
    assertion_id: str,
) -> TemporalPointV1 | None:
    matches = [
        assertion
        for assertion in contribution.candidate_assertions
        if assertion.assertion_id == assertion_id
    ]
    if not matches:
        raise TemporalShadowExtractionError(
            "Comparison target missing from base contribution",
            code="comparison_source_time_failure",
            affected_assertion_id=assertion_id,
        )
    if len(matches) > 1:
        raise TemporalShadowExtractionError(
            "Duplicate assertion_id in base contribution",
            code="comparison_source_time_failure",
            affected_assertion_id=assertion_id,
        )
    try:
        source, derivation, diagnostics = derive_assertion_source_time(matches[0])
    except TemporalShadowBuildError as exc:
        raise TemporalShadowExtractionError(
            "Cannot safely derive source time for comparison",
            code="comparison_source_time_failure",
            affected_assertion_id=assertion_id,
            diagnostics=list(exc.diagnostics) or [str(exc)],
        ) from exc
    if derivation == "skipped":
        raise TemporalShadowExtractionError(
            "Source-time derivation skipped; cannot measure source leakage",
            code="comparison_source_time_failure",
            affected_assertion_id=assertion_id,
            diagnostics=list(diagnostics),
        )
    return source


def _build_assertion_source_time_map(
    contribution: GraphContribution,
    assertion_ids: set[str],
) -> dict[str, TemporalPointV1 | None]:
    return {
        assertion_id: _derive_comparison_source_time(contribution, assertion_id)
        for assertion_id in assertion_ids
    }


def compare_temporal_overlays(
    predicted: TemporalAnnotationOverlayV1,
    gold: TemporalAnnotationOverlayV1,
    *,
    base_contribution: GraphContribution | None = None,
    assertion_source_times: Mapping[str, TemporalPointV1 | None] | None = None,
) -> TemporalShadowComparisonV1:
    """Compare predicted vs gold using semantic temporal equality.

    Source-leakage metrics require either ``base_contribution`` (preferred) or
    an immutable ``assertion_source_times`` map derived via TL01
    ``derive_assertion_source_time``. Do not invent source time from gold,
    filenames, or model output.
    """
    if assertion_source_times is None:
        if base_contribution is None:
            raise TemporalShadowExtractionError(
                "compare_temporal_overlays requires base_contribution or assertion_source_times",
                code="comparison_source_time_failure",
            )
        all_ids_for_source = {
            item.base_assertion_id for item in gold.annotations
        } | {item.base_assertion_id for item in predicted.annotations}
        source_times = _build_assertion_source_time_map(
            base_contribution, all_ids_for_source
        )
    else:
        source_times = dict(assertion_source_times)

    gold_by_id = {item.base_assertion_id: item for item in gold.annotations}
    predicted_by_id = {item.base_assertion_id: item for item in predicted.annotations}
    all_ids = sorted(set(gold_by_id) | set(predicted_by_id))

    rows: list[TemporalShadowComparisonRowV1] = []
    exact = status_mismatch = semantic_mismatch = missing = extra = 0
    safe_under = unsafe_over = wrong_lane = 0
    resolved_exact = 0
    status_matches = 0
    comparable_status = 0
    source_to_occ_fp = source_to_valid_fp = unsupported_resolved = 0
    evidence_selection_mismatch = 0
    ambiguous_or_unresolved = 0
    not_applicable_gold = 0
    not_applicable_correct = 0
    conservative_statuses = {"ambiguous", "unresolved"}
    non_resolved_gold = {"ambiguous", "unresolved", "not_applicable"}

    for assertion_id in all_ids:
        gold_ann = gold_by_id.get(assertion_id)
        pred_ann = predicted_by_id.get(assertion_id)
        if gold_ann is None:
            extra += 1
            rows.append(
                TemporalShadowComparisonRowV1(
                    base_assertion_id=assertion_id,
                    classification="extra_prediction",
                    predicted_interpretation_status=pred_ann.interpretation_status
                    if pred_ann
                    else None,
                    diagnostics=["predicted annotation without gold target"],
                )
            )
            continue
        if gold_ann.interpretation_status in conservative_statuses:
            ambiguous_or_unresolved += 1
        if gold_ann.interpretation_status == "not_applicable":
            not_applicable_gold += 1
        if pred_ann is None:
            missing += 1
            comparable_status += 1
            rows.append(
                TemporalShadowComparisonRowV1(
                    base_assertion_id=assertion_id,
                    classification="missing_prediction",
                    gold_interpretation_status=gold_ann.interpretation_status,
                    diagnostics=["gold annotation missing from prediction"],
                )
            )
            continue

        comparable_status += 1
        if gold_ann.interpretation_status == pred_ann.interpretation_status:
            status_matches += 1

        if sorted(gold_ann.evidence_ref_ids) != sorted(pred_ann.evidence_ref_ids):
            evidence_selection_mismatch += 1

        if assertion_id not in source_times:
            raise TemporalShadowExtractionError(
                "Missing derived source time for comparison target",
                code="comparison_source_time_failure",
                affected_assertion_id=assertion_id,
            )
        source = source_times[assertion_id]
        if source is not None:
            if _extent_contains_exact_point(pred_ann.occurrence_time, source):
                if not _extent_contains_exact_point(gold_ann.occurrence_time, source):
                    source_to_occ_fp += 1
            if _interval_contains_exact_point(pred_ann.valid_time, source):
                if not _interval_contains_exact_point(gold_ann.valid_time, source):
                    source_to_valid_fp += 1

        if gold_ann.interpretation_status != pred_ann.interpretation_status:
            if (
                gold_ann.interpretation_status in non_resolved_gold
                and pred_ann.interpretation_status == "resolved"
            ):
                unsafe_over += 1
                unsupported_resolved += 1
                classification: ComparisonClassification = "unsafe_over_resolution"
            elif (
                gold_ann.interpretation_status == "resolved"
                and pred_ann.interpretation_status in conservative_statuses
            ):
                safe_under += 1
                classification = "safe_under_resolution"
            else:
                status_mismatch += 1
                classification = "status_mismatch"
            rows.append(
                TemporalShadowComparisonRowV1(
                    base_assertion_id=assertion_id,
                    classification=classification,
                    gold_interpretation_status=gold_ann.interpretation_status,
                    predicted_interpretation_status=pred_ann.interpretation_status,
                )
            )
            continue
        gold_semantic = _annotation_semantic_payload(gold_ann)
        pred_semantic = _annotation_semantic_payload(pred_ann)
        if gold_semantic != pred_semantic:
            if _lane_signature(gold_ann) != _lane_signature(pred_ann):
                wrong_lane += 1
                semantic_mismatch += 1
                rows.append(
                    TemporalShadowComparisonRowV1(
                        base_assertion_id=assertion_id,
                        classification="wrong_temporal_lane",
                        gold_interpretation_status=gold_ann.interpretation_status,
                        predicted_interpretation_status=pred_ann.interpretation_status,
                        diagnostics=["occurrence/valid-time lane presence differs"],
                    )
                )
            else:
                semantic_mismatch += 1
                rows.append(
                    TemporalShadowComparisonRowV1(
                        base_assertion_id=assertion_id,
                        classification="wrong_temporal_value",
                        gold_interpretation_status=gold_ann.interpretation_status,
                        predicted_interpretation_status=pred_ann.interpretation_status,
                        diagnostics=["semantic temporal payload differs"],
                    )
                )
            continue
        exact += 1
        if gold_ann.interpretation_status == "resolved":
            resolved_exact += 1
        if gold_ann.interpretation_status == "not_applicable":
            not_applicable_correct += 1
        rows.append(
            TemporalShadowComparisonRowV1(
                base_assertion_id=assertion_id,
                classification="exact_match",
                gold_interpretation_status=gold_ann.interpretation_status,
                predicted_interpretation_status=pred_ann.interpretation_status,
            )
        )

    status_accuracy = (
        float(status_matches) / float(comparable_status) if comparable_status else 0.0
    )
    not_applicable_accuracy = (
        float(not_applicable_correct) / float(not_applicable_gold)
        if not_applicable_gold
        else 0.0
    )

    metrics = TemporalShadowComparisonMetricsV1(
        total_gold_annotations=len(gold.annotations),
        exact_match_count=exact,
        exact_semantic_match_count=exact,
        resolved_exact_match_count=resolved_exact,
        safe_under_resolution_count=safe_under,
        unsafe_over_resolution_count=unsafe_over,
        wrong_temporal_lane_count=wrong_lane,
        status_mismatch_count=status_mismatch,
        semantic_mismatch_count=semantic_mismatch,
        missing_prediction_count=missing,
        extra_prediction_count=extra,
        source_to_occurrence_false_positives=source_to_occ_fp,
        source_to_valid_time_false_positives=source_to_valid_fp,
        unsupported_resolved_annotations=unsupported_resolved,
        # Successful comparisons only reach here after grounding; foreign
        # evidence is a fail-closed precondition, always zero on success.
        foreign_evidence_attempts=0,
        ungrounded_source_phrases=0,
        invalid_temporal_payloads=0,
        evidence_selection_mismatch_count=evidence_selection_mismatch,
        status_accuracy=status_accuracy,
        ambiguous_or_unresolved_count=ambiguous_or_unresolved,
        not_applicable_accuracy=not_applicable_accuracy,
    )
    if missing or extra or unsafe_over:
        verdict: ComparisonVerdict = "fail"
    elif status_mismatch or semantic_mismatch or safe_under:
        verdict = "partial"
    else:
        verdict = "pass"

    if unsafe_over or missing or extra:
        evaluation_verdict: EvaluationVerdict = "ITERATE_PROMPT"
    elif exact == len(gold.annotations) and exact > 0:
        evaluation_verdict = "SAFE_FOR_NEXT_EXPERIMENT"
    else:
        evaluation_verdict = "ITERATE_PROMPT"

    return TemporalShadowComparisonV1(
        verdict=verdict,
        evaluation_verdict=evaluation_verdict,
        metrics=metrics,
        rows=rows,
    )


def _repository_sha(*, repo_root: Path) -> str:
    import subprocess

    try:
        completed = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_root,
            check=True,
            capture_output=True,
            text=True,
        )
        sha = completed.stdout.strip() or "unknown"
        # Ignore untracked files and node_modules noise; only tracked
        # project dirtiness marks +dirty on the recorded SHA.
        dirty = subprocess.run(
            [
                "git",
                "status",
                "--porcelain",
                "-uno",
                "--",
                ".",
                ":(exclude)node_modules",
                ":(exclude)node_modules/**",
            ],
            cwd=repo_root,
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return "unknown"
    if dirty.stdout.strip():
        return f"{sha}+dirty"
    return sha


def _bounded_diagnostics(diagnostics: list[str], *, limit: int = 8) -> list[str]:
    bounded: list[str] = []
    for item in diagnostics[:limit]:
        text = item if len(item) <= 500 else item[:497] + "..."
        bounded.append(text)
    return bounded


def _staging_dir(out: Path) -> Path:
    import tempfile

    out.parent.mkdir(parents=True, exist_ok=True)
    return Path(
        tempfile.mkdtemp(prefix=f".{out.name}.staging-", dir=str(out.parent))
    )


def _publish_run_directory(staging: Path, out: Path) -> None:
    import shutil

    backup: Path | None = None
    try:
        if out.exists():
            backup = out.with_name(f".{out.name}.bak-{os.getpid()}")
            if backup.exists():
                shutil.rmtree(backup)
            out.rename(backup)
        staging.rename(out)
    except Exception:
        if backup is not None and backup.exists() and not out.exists():
            backup.rename(out)
        if staging.exists():
            shutil.rmtree(staging, ignore_errors=True)
        raise
    if backup is not None and backup.exists():
        shutil.rmtree(backup, ignore_errors=True)


def _write_provider_failure_manifest(
    *,
    out: Path,
    case: TemporalShadowExtractionCaseV1,
    contribution: GraphContribution,
    case_digest: str,
    model_id: str,
    executed_prompt_version: str,
    error: TemporalShadowExtractionError,
    provider_response_id: str | None = None,
) -> TemporalShadowExtractionFailureV1:
    failure = TemporalShadowExtractionFailureV1(
        case_id=case.case_id,
        case_digest=case_digest,
        base_contribution_id=contribution.contribution_id,
        base_contribution_source_payload_sha256=compute_contribution_source_payload_sha256(
            contribution
        ),
        model_id=model_id,
        executed_prompt_version=executed_prompt_version,
        failure_code=error.code,
        diagnostics=_bounded_diagnostics(list(error.diagnostics)),
        provider_response_id=provider_response_id,
        affected_assertion_id=error.affected_assertion_id,
        foreign_evidence_attempts=error.foreign_evidence_attempts,
    )
    (out / "failure-manifest.json").write_text(
        json.dumps(failure.model_dump(by_alias=True), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return failure


def _source_artifact_digests(
    case: TemporalShadowExtractionCaseV1,
) -> list[TemporalShadowSourceArtifactDigestV1]:
    seen: dict[str, str] = {}
    for entry in case.evidence_registry:
        prior = seen.get(entry.source_artifact_id)
        if prior is None:
            seen[entry.source_artifact_id] = entry.content_sha256
        elif prior != entry.content_sha256:
            raise TemporalShadowExtractionError(
                "Conflicting source artifact digests in case registry",
                code="invalid_case",
                diagnostics=[f"source_artifact_id={entry.source_artifact_id!r}"],
            )
    return [
        TemporalShadowSourceArtifactDigestV1(
            source_artifact_id=artifact_id,
            content_sha256=digest,
        )
        for artifact_id, digest in sorted(seen.items())
    ]


def run_temporal_shadow_extraction(
    case_path: Path | str,
    output_dir: Path | str,
    *,
    client: TemporalShadowExtractionClient | None = None,
    model_id: str | None = None,
    overwrite: bool = False,
    repo_root: Path | None = None,
) -> TemporalShadowExtractionRunV1:
    root = repo_root or Path(__file__).resolve().parents[2]
    out = Path(output_dir)
    if out.exists() and any(out.iterdir()) and not overwrite:
        raise TemporalShadowExtractionError(
            f"Output directory is non-empty (use overwrite=True): {out}",
            code="invalid_case",
        )

    staging = _staging_dir(out)
    published = False
    try:
        case = load_temporal_shadow_extraction_case(case_path, repo_root=root)
        contribution = _load_contribution_for_case(case, repo_root=root)
        packets = build_assertion_evidence_packets(contribution, case, repo_root=root)
        resolved_model = resolve_category_graph_model(model_id)
        instructions, executed_prompt_version = resolve_prompt_instructions(
            case.prompt_version
        )
        active_client = client or OpenAITemporalShadowExtractionClient()
        case_digest = _file_sha256(Path(case_path))
        base_digest = compute_contribution_source_payload_sha256(contribution)

        user_content = render_temporal_shadow_user_content(
            packets, case.selected_assertion_ids
        )
        try:
            raw_batch, provider_meta = active_client.extract_annotations(
                instructions=instructions,
                user_content=user_content,
                model_id=resolved_model,
            )
        except TemporalShadowExtractionError as exc:
            if exc.code in {"provider_refusal", "provider_incomplete", "provider_error"}:
                _write_provider_failure_manifest(
                    out=staging,
                    case=case,
                    contribution=contribution,
                    case_digest=case_digest,
                    model_id=resolved_model,
                    executed_prompt_version=executed_prompt_version,
                    error=exc,
                    provider_response_id=exc.provider_response_id,
                )
                _publish_run_directory(staging, out)
                published = True
            raise

        try:
            annotations = ground_and_convert_model_batch(
                raw_batch=raw_batch,
                contribution=contribution,
                case=case,
                packets=packets,
                model_id=resolved_model,
                prompt_version=executed_prompt_version,
            )
        except TemporalShadowExtractionError as exc:
            if exc.code == "grounding_failure":
                _write_provider_failure_manifest(
                    out=staging,
                    case=case,
                    contribution=contribution,
                    case_digest=case_digest,
                    model_id=resolved_model,
                    executed_prompt_version=executed_prompt_version,
                    error=exc,
                    provider_response_id=provider_meta.response_id,
                )
                _publish_run_directory(staging, out)
                published = True
            raise
        overlay = assemble_temporal_overlay(
            contribution=contribution,
            annotations=annotations,
            prompt_version=executed_prompt_version,
        )
        parsed_overlay = load_temporal_annotation_overlay(
            overlay.model_dump(by_alias=True)
        )
        try:
            preview = build_temporal_shadow_preview(contribution, parsed_overlay)
        except TemporalShadowBuildError as exc:
            raise TemporalShadowExtractionError(
                str(exc),
                code="overlay_assembly_failed",
                affected_assertion_id=exc.affected_assertion_id,
                diagnostics=list(exc.diagnostics),
            ) from exc

        gold_overlay = load_bound_gold_overlay(case, contribution, repo_root=root)
        comparison = compare_temporal_overlays(
            parsed_overlay,
            gold_overlay,
            base_contribution=contribution,
        )

        run_id = compute_temporal_shadow_run_id(
            case_id=case.case_id,
            case_digest=case_digest,
            model_id=resolved_model,
            prompt_version=executed_prompt_version,
            validated_model_output=raw_batch,
        )
        run = TemporalShadowExtractionRunV1(
            run_id=run_id,
            case_id=case.case_id,
            case_digest=case_digest,
            repository_sha=_repository_sha(repo_root=root),
            overlay_id=parsed_overlay.overlay_id,
            base_contribution_id=contribution.contribution_id,
            base_contribution_source_payload_sha256=base_digest,
            selected_assertion_ids=list(case.selected_assertion_ids),
            source_artifacts=_source_artifact_digests(case),
            comparison_verdict=comparison.verdict,
            evaluation_verdict=comparison.evaluation_verdict,
            preview_verdict=preview.verdict,
            model_id=resolved_model,
            prompt_version=executed_prompt_version,
            executed_prompt_version=executed_prompt_version,
            provider_response_id=provider_meta.response_id,
            input_tokens=provider_meta.input_tokens,
            output_tokens=provider_meta.output_tokens,
            elapsed_ms=provider_meta.elapsed_ms,
        )

        # Write payload artifacts first; run-manifest last, then publish atomically.
        (staging / "model-output.json").write_text(
            json.dumps(raw_batch, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        (staging / "overlay.json").write_text(
            json.dumps(
                parsed_overlay.model_dump(by_alias=True), indent=2, sort_keys=True
            )
            + "\n",
            encoding="utf-8",
        )
        (staging / "preview.json").write_text(
            json.dumps(preview.model_dump(by_alias=True), indent=2, sort_keys=True)
            + "\n",
            encoding="utf-8",
        )
        (staging / "comparison.json").write_text(
            json.dumps(comparison.model_dump(by_alias=True), indent=2, sort_keys=True)
            + "\n",
            encoding="utf-8",
        )
        (staging / "provider-metadata.json").write_text(
            json.dumps(
                {
                    "response_id": provider_meta.response_id,
                    "model_id": provider_meta.model_id,
                    "input_tokens": provider_meta.input_tokens,
                    "output_tokens": provider_meta.output_tokens,
                    "elapsed_ms": provider_meta.elapsed_ms,
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        (staging / "run-manifest.json").write_text(
            json.dumps(run.model_dump(by_alias=True), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        _publish_run_directory(staging, out)
        published = True
        return run
    finally:
        if not published and staging.exists():
            import shutil

            shutil.rmtree(staging, ignore_errors=True)


__all__ = [
    "FakeTemporalShadowExtractionClient",
    "OpenAITemporalShadowExtractionClient",
    "ProviderMeta",
    "TemporalShadowComparisonV1",
    "TemporalShadowExtractionCaseV1",
    "TemporalShadowExtractionClient",
    "TemporalShadowExtractionError",
    "TemporalShadowExtractionFailureV1",
    "TemporalShadowExtractionRunV1",
    "TEMPORAL_SHADOW_SYSTEM_INSTRUCTIONS",
    "assemble_temporal_overlay",
    "build_assertion_evidence_packets",
    "compare_temporal_overlays",
    "compute_temporal_annotation_id",
    "compute_temporal_shadow_run_id",
    "ground_and_convert_model_batch",
    "load_bound_gold_overlay",
    "load_temporal_shadow_extraction_case",
    "render_temporal_shadow_user_content",
    "resolve_prompt_instructions",
    "run_temporal_shadow_extraction",
]
