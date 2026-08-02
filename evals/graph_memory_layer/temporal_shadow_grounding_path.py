"""Paired TL01 shared source-phrase grounding-path diagnostic runner."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
_SRC = _REPO_ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from graph_memory.kernel.contribution_models import GraphContribution  # noqa: E402
from graph_memory.kernel.contributions import explicit_assertion_evidence_ref_ids  # noqa: E402
from graph_memory.temporal_shadow_extraction import (  # noqa: E402
    FakeTemporalShadowExtractionClient,
    OpenAITemporalShadowExtractionClient,
    ProviderMeta,
    TL01C_PACKET_VERSION,
    TemporalShadowExtractionClient,
    TemporalShadowExtractionError,
    build_assertion_evidence_packets,
    compute_prompt_sha256,
    load_bound_gold_overlay,
    load_temporal_shadow_extraction_case,
    resolve_prompt_spec,
    run_temporal_shadow_extraction,
)

LaneName = Literal["control", "candidate"]
RunMode = Literal["deterministic", "live"]
RunPhase = Literal["initial", "post_fix"]

LIVE_OPT_IN_ENV = "DMB_RUN_LIVE_TL01_GROUNDING_SMOKE"
LIVE_MODEL_ID = "gpt-5.4-mini"
RENDERER_IDENTITY = "render_temporal_shadow_user_content_v2"
FROZEN_CONTROL_PROMPT_VERSION = "tl01f-v1"
FROZEN_CANDIDATE_PROMPT_VERSION = "tl01g-v1"
FROZEN_CONTROL_PROMPT_SHA256 = (
    "7a9d27c3a9980893f18757d7a5fe0612cf67f9aad8dfd2ccb20f9e3c667b7143"
)
FROZEN_CANDIDATE_PROMPT_SHA256 = (
    "3af1e470e304008d2490ba73e1a53628519c211bb54e17a10cd4c694beae9013"
)
SMOKE_FIXTURE_RELATIVE = Path(
    "evals/graph_memory_layer/examples/temporal_shadow_grounding_smoke_v1"
)

LaneResult = Literal[
    "EVALUABLE",
    "PACKET_MISSING_PHRASE",
    "RENDERER_MISSING_PHRASE",
    "PROVIDER_EXECUTION_FAILED",
    "PROVIDER_PHRASE_FIDELITY_BLOCKED",
    "TRANSPORT_REJECTED",
    "EVIDENCE_OWNERSHIP_MISMATCH",
    "GROUNDING_VALIDATOR_DEFECT",
    "OVERLAY_ASSEMBLY_FAILED",
    "COMPARISON_METRICS_UNOBSERVED",
    "UNRESOLVED_DIAGNOSTIC_GAP",
]

OverallConclusion = Literal[
    "GROUNDING_PATH_READY",
    "LOCAL_REPAIR_REQUIRED",
    "PROVIDER_PHRASE_FIDELITY_BLOCKED",
    "UNRESOLVED_DIAGNOSTIC_GAP",
]

FORBIDDEN_TRACE_SUBSTRINGS = (
    "OPENAI_API_KEY",
    "sk-",
    "/home/",
    "/Users/",
    "TL01F_PROPOSITION_TYPE_TEMPORAL_LANE_INSTRUCTIONS",
    "TL01G_RESOLUTION_PROOF_ABSTENTION_INSTRUCTIONS",
)

PHASE_CALL_BUDGET = 2
MAX_TOTAL_PROVIDER_CALLS = 4
BUDGET_LEDGER_SCHEMA = "tl01_grounding_path_budget_v1"
DEFAULT_BUDGET_LEDGER_NAME = "provider-budget-ledger.json"


def _normalize_phrase(text: str) -> str:
    return " ".join(text.split())


def _bounded_text(text: str | None, *, limit: int = 200) -> str | None:
    if text is None:
        return None
    if len(text) <= limit:
        return text
    return text[: limit - 3] + "..."


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _repository_sha(*, repo_root: Path) -> str:
    try:
        sha = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        dirty = subprocess.run(
            ["git", "status", "--porcelain"],
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


def _load_contribution(case_path: Path, *, repo_root: Path) -> GraphContribution:
    case = load_temporal_shadow_extraction_case(case_path, repo_root=repo_root)
    base_path = repo_root / case.base_contribution_path
    return GraphContribution.model_validate(json.loads(base_path.read_text(encoding="utf-8")))


def _case_pair_fields(case: Any) -> dict[str, Any]:
    payload = case.model_dump(by_alias=True)
    for key in ("case_id", "prompt_version"):
        payload.pop(key, None)
    return payload


def validate_paired_cases(
    control_case_path: Path,
    candidate_case_path: Path,
    *,
    repo_root: Path,
) -> tuple[Any, Any]:
    control = load_temporal_shadow_extraction_case(control_case_path, repo_root=repo_root)
    candidate = load_temporal_shadow_extraction_case(
        candidate_case_path, repo_root=repo_root
    )
    if control.prompt_version == candidate.prompt_version:
        raise TemporalShadowExtractionError(
            "Control and candidate must use different frozen prompt identities",
            code="invalid_case",
            diagnostics=[
                f"control={control.prompt_version!r}",
                f"candidate={candidate.prompt_version!r}",
            ],
        )
    if _case_pair_fields(control) != _case_pair_fields(candidate):
        raise TemporalShadowExtractionError(
            "Paired cases differ outside allowed prompt identity fields",
            code="invalid_case",
            diagnostics=["only prompt_version and case_id may differ"],
        )
    return control, candidate


def expected_phrase_from_fixture(
    *,
    contribution: GraphContribution,
    case: Any,
    repo_root: Path,
) -> tuple[str, str, list[str]]:
    assertion_id = case.selected_assertion_ids[0]
    assertion = next(
        a for a in contribution.candidate_assertions if a.assertion_id == assertion_id
    )
    owned = list(explicit_assertion_evidence_ref_ids(assertion))
    gold = load_bound_gold_overlay(case, contribution, repo_root=repo_root)
    gold_ann = next(a for a in gold.annotations if a.base_assertion_id == assertion_id)
    phrase = gold_ann.source_phrase or ""
    if not phrase.strip():
        raise TemporalShadowExtractionError(
            "Fixture gold overlay missing source_phrase for selected assertion",
            code="invalid_case",
            affected_assertion_id=assertion_id,
        )
    return phrase, assertion_id, owned


def packet_contains_phrase(
    packets: dict[str, dict[str, Any]],
    *,
    assertion_id: str,
    evidence_ref_ids: list[str],
    expected_phrase: str,
) -> bool:
    snippets = packets[assertion_id]["evidence_snippets"]
    normalized_expected = _normalize_phrase(expected_phrase)
    for evidence_id in evidence_ref_ids:
        snippet = next(
            s["preview_snippet"] for s in snippets if s["evidence_ref_id"] == evidence_id
        )
        if normalized_expected in _normalize_phrase(snippet):
            return True
    return False


def decoded_renderer_contains_phrase(user_content: str, expected_phrase: str) -> bool:
    payload = json.loads(user_content)
    normalized_expected = _normalize_phrase(expected_phrase)
    for packet in payload.get("assertion_packets", []):
        for snippet in packet.get("evidence_snippets", []):
            preview = snippet.get("preview_snippet")
            if isinstance(preview, str) and normalized_expected in _normalize_phrase(preview):
                return True
    return False


def _resolved_span_digest(
    packets: dict[str, dict[str, Any]], *, assertion_id: str, evidence_ref_id: str
) -> str:
    snippets = packets[assertion_id]["evidence_snippets"]
    snippet = next(
        s["preview_snippet"] for s in snippets if s["evidence_ref_id"] == evidence_ref_id
    )
    return hashlib.sha256(_normalize_phrase(snippet).encode("utf-8")).hexdigest()


def _phrase_match_in_owned_snippet(
    *,
    returned_phrase: str | None,
    evidence_ref_ids: list[str],
    packets: dict[str, dict[str, Any]],
    assertion_id: str,
) -> tuple[bool, str | None, int | None]:
    if returned_phrase is None:
        return False, None, None
    normalized_phrase = _normalize_phrase(returned_phrase)
    if not normalized_phrase:
        return False, None, None
    snippets = packets[assertion_id]["evidence_snippets"]
    for evidence_id in evidence_ref_ids:
        match = next(
            (s for s in snippets if s["evidence_ref_id"] == evidence_id),
            None,
        )
        if match is None:
            continue
        snippet = match["preview_snippet"]
        normalized_snippet = _normalize_phrase(snippet)
        offset = normalized_snippet.find(normalized_phrase)
        if offset >= 0:
            return True, evidence_id, offset
    return False, None, None


@dataclass
class ProviderCallLedger:
    phase: RunPhase
    calls: int = 0
    response_ids: list[str] = field(default_factory=list)

    def record_attempt(self, response_id: str | None = None) -> None:
        """Charge one provider attempt, including refusals/errors/exceptions."""
        self.calls += 1
        if response_id:
            self.response_ids.append(response_id)

    def record(self, meta: ProviderMeta) -> None:
        self.record_attempt(meta.response_id)

    def assert_budget(self) -> None:
        if self.calls > PHASE_CALL_BUDGET:
            raise TemporalShadowExtractionError(
                f"Provider call budget exceeded for phase {self.phase!r}",
                code="invalid_case",
                diagnostics=[f"calls={self.calls}", f"budget={PHASE_CALL_BUDGET}"],
            )


class RecordingTemporalShadowClient:
    """Observe request/response boundary without mutating values."""

    def __init__(
        self,
        delegate: TemporalShadowExtractionClient,
        *,
        ledger: ProviderCallLedger | None = None,
        record_provider_calls: bool = False,
    ) -> None:
        self._delegate = delegate
        self.ledger = ledger
        self.record_provider_calls = record_provider_calls
        self.last_instructions: str | None = None
        self.last_user_content: str | None = None
        self.last_raw_batch: dict[str, Any] | None = None
        self.last_provider_meta: ProviderMeta | None = None
        self.call_count = 0

    def extract_annotations(
        self,
        *,
        instructions: str,
        user_content: str,
        model_id: str,
    ) -> tuple[dict[str, Any], ProviderMeta]:
        self.last_instructions = instructions
        self.last_user_content = user_content
        # Charge the attempt before delegation so refusals/errors still consume budget.
        if self.ledger is not None and self.record_provider_calls:
            self.ledger.record_attempt(None)
        try:
            raw_batch, meta = self._delegate.extract_annotations(
                instructions=instructions,
                user_content=user_content,
                model_id=model_id,
            )
        except TemporalShadowExtractionError as exc:
            self.call_count += 1
            if (
                self.ledger is not None
                and self.record_provider_calls
                and exc.provider_response_id
            ):
                self.ledger.response_ids.append(exc.provider_response_id)
            raise
        except Exception:
            self.call_count += 1
            raise
        self.last_raw_batch = raw_batch
        self.last_provider_meta = meta
        self.call_count += 1
        if self.ledger is not None and self.record_provider_calls and meta.response_id:
            self.ledger.response_ids.append(meta.response_id)
        return raw_batch, meta


def _annotation_from_raw_batch(
    raw_batch: dict[str, Any] | None,
    *,
    assertion_id: str,
) -> tuple[str | None, list[str] | None, bool]:
    """Observe (source_phrase, evidence_ref_ids, well_formed) without trusting shape.

    Raw provider output is untrusted. Malformed annotations / evidence_ref_ids must
    not raise; callers treat well_formed=False as transport observation failure.
    """
    if raw_batch is None:
        return None, None, True
    if not isinstance(raw_batch, dict):
        return None, None, False
    if "annotations" not in raw_batch:
        return None, None, True
    annotations = raw_batch.get("annotations")
    if not isinstance(annotations, list):
        return None, None, False
    for item in annotations:
        if not isinstance(item, dict):
            return None, None, False
        if item.get("base_assertion_id") != assertion_id:
            continue
        phrase_raw = item.get("source_phrase")
        if phrase_raw is not None and not isinstance(phrase_raw, str):
            return None, None, False
        phrase = phrase_raw if isinstance(phrase_raw, str) else None
        if "evidence_ref_ids" not in item:
            return phrase, None, True
        refs_raw = item.get("evidence_ref_ids")
        if refs_raw is None:
            return phrase, None, True
        if not isinstance(refs_raw, list):
            return None, None, False
        if not all(isinstance(ref, str) for ref in refs_raw):
            return None, None, False
        return phrase, list(refs_raw), True
    return None, None, True


def classify_lane_result(
    *,
    packet_phrase_present: bool,
    renderer_phrase_present: bool,
    run_mode: RunMode,
    error: TemporalShadowExtractionError | None,
    raw_batch: dict[str, Any] | None,
    packets: dict[str, dict[str, Any]],
    assertion_id: str,
    owned_evidence_ref_ids: list[str],
    comparison_metrics_present: bool,
    succeeded: bool,
    raw_batch_well_formed: bool = True,
) -> LaneResult:
    if not packet_phrase_present:
        return "PACKET_MISSING_PHRASE"
    if not renderer_phrase_present:
        return "RENDERER_MISSING_PHRASE"
    if not raw_batch_well_formed:
        return "TRANSPORT_REJECTED"
    if error is not None:
        if error.code in {"provider_refusal", "provider_incomplete", "provider_error"}:
            return "PROVIDER_EXECUTION_FAILED"
        if error.code == "invalid_model_output":
            return "TRANSPORT_REJECTED"
        if error.code == "overlay_assembly_failed":
            return "OVERLAY_ASSEMBLY_FAILED"
        if error.code == "grounding_failure":
            returned_phrase, returned_refs, well_formed = _annotation_from_raw_batch(
                raw_batch, assertion_id=assertion_id
            )
            if not well_formed:
                return "TRANSPORT_REJECTED"
            # Absent refs (missing key, null, or empty list) are ownership failures.
            # Never fall back to the assertion's owned refs for phrase matching.
            if returned_refs is None or len(returned_refs) == 0:
                return "EVIDENCE_OWNERSHIP_MISMATCH"
            if error.foreign_evidence_attempts > 0:
                return "EVIDENCE_OWNERSHIP_MISMATCH"
            owned = set(owned_evidence_ref_ids)
            if not set(returned_refs).issubset(owned):
                return "EVIDENCE_OWNERSHIP_MISMATCH"
            present, _, _ = _phrase_match_in_owned_snippet(
                returned_phrase=returned_phrase,
                evidence_ref_ids=returned_refs,
                packets=packets,
                assertion_id=assertion_id,
            )
            if present:
                return "GROUNDING_VALIDATOR_DEFECT"
            if run_mode == "live" or raw_batch is not None:
                return "PROVIDER_PHRASE_FIDELITY_BLOCKED"
            return "UNRESOLVED_DIAGNOSTIC_GAP"
        return "UNRESOLVED_DIAGNOSTIC_GAP"
    if succeeded and not comparison_metrics_present:
        return "COMPARISON_METRICS_UNOBSERVED"
    if succeeded:
        return "EVALUABLE"
    return "UNRESOLVED_DIAGNOSTIC_GAP"


_LOCAL_REPAIR_LANE_RESULTS: frozenset[LaneResult] = frozenset(
    {
        "PACKET_MISSING_PHRASE",
        "RENDERER_MISSING_PHRASE",
        "GROUNDING_VALIDATOR_DEFECT",
        "OVERLAY_ASSEMBLY_FAILED",
        "COMPARISON_METRICS_UNOBSERVED",
    }
)


def compute_overall_conclusion(
    *,
    deterministic_control: LaneResult | None = None,
    deterministic_candidate: LaneResult | None = None,
    live_control: LaneResult | None = None,
    live_candidate: LaneResult | None = None,
) -> OverallConclusion:
    """Lane-result triage only. Never returns GROUNDING_PATH_READY.

    Readiness requires evidence-bound combination via
    ``combine_paired_diagnostic_conclusions`` (or summary traces), which verifies
    shared fixture/identity fields before READY.
    """
    det_lanes = (deterministic_control, deterministic_candidate)
    live_lanes = (live_control, live_candidate)
    det_complete = all(lane is not None for lane in det_lanes)
    live_complete = all(lane is not None for lane in live_lanes)
    both_det_evaluable = det_complete and all(lane == "EVALUABLE" for lane in det_lanes)

    observed = [lane for lane in (*det_lanes, *live_lanes) if lane is not None]
    if any(lane in _LOCAL_REPAIR_LANE_RESULTS for lane in observed):
        return "LOCAL_REPAIR_REQUIRED"

    if both_det_evaluable and live_complete:
        if any(lane == "PROVIDER_EXECUTION_FAILED" for lane in live_lanes):
            return "UNRESOLVED_DIAGNOSTIC_GAP"
        if any(lane == "PROVIDER_PHRASE_FIDELITY_BLOCKED" for lane in live_lanes):
            return "PROVIDER_PHRASE_FIDELITY_BLOCKED"

    return "UNRESOLVED_DIAGNOSTIC_GAP"


def _fixture_identity_key(lane: LaneDiagnostic) -> tuple[Any, ...]:
    return (
        lane.assertion_id,
        tuple(lane.evidence_ref_ids),
        lane.expected_phrase,
        lane.resolved_span_digest,
        lane.packet_version,
        lane.renderer_identity,
    )


def _trace_fixture_identity_key(trace: dict[str, Any]) -> tuple[Any, ...] | None:
    try:
        return (
            trace["assertion_id"],
            tuple(trace["evidence_ref_ids"]),
            trace["expected_phrase"],
            trace["resolved_span_digest"],
            trace["packet_version"],
            trace["renderer_identity"],
        )
    except (KeyError, TypeError):
        return None


def _is_clean_commit_sha(value: str | None) -> bool:
    if not isinstance(value, str) or not value:
        return False
    if "+" in value or value == "unknown":
        return False
    return len(value) == 40 and all(c in "0123456789abcdef" for c in value)


def _frozen_prompt_errors(
    *,
    control_version: str | None,
    control_sha: str | None,
    candidate_version: str | None,
    candidate_sha: str | None,
) -> list[str]:
    errors: list[str] = []
    if control_version != FROZEN_CONTROL_PROMPT_VERSION:
        errors.append(
            f"control prompt_version must be {FROZEN_CONTROL_PROMPT_VERSION!r}"
        )
    if candidate_version != FROZEN_CANDIDATE_PROMPT_VERSION:
        errors.append(
            f"candidate prompt_version must be {FROZEN_CANDIDATE_PROMPT_VERSION!r}"
        )
    if control_sha != FROZEN_CONTROL_PROMPT_SHA256:
        errors.append("control prompt_sha256 must match frozen tl01f-v1 hash")
    if candidate_sha != FROZEN_CANDIDATE_PROMPT_SHA256:
        errors.append("candidate prompt_sha256 must match frozen tl01g-v1 hash")
    if control_version == FROZEN_CONTROL_PROMPT_VERSION:
        if compute_prompt_sha256(FROZEN_CONTROL_PROMPT_VERSION) != control_sha:
            errors.append("control prompt_sha256 does not match compute_prompt_sha256")
    if candidate_version == FROZEN_CANDIDATE_PROMPT_VERSION:
        if compute_prompt_sha256(FROZEN_CANDIDATE_PROMPT_VERSION) != candidate_sha:
            errors.append("candidate prompt_sha256 does not match compute_prompt_sha256")
    return errors


def _evaluable_success_field_errors_from_mapping(trace: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if trace.get("lane_result") != "EVALUABLE":
        return errors
    if trace.get("transport_accepted") is not True:
        errors.append("EVALUABLE requires transport_accepted=True")
    if trace.get("owned_evidence_check") != "owned_match":
        errors.append("EVALUABLE requires owned_evidence_check='owned_match'")
    if trace.get("phrase_match") is not True:
        errors.append("EVALUABLE requires phrase_match=True")
    returned_refs = trace.get("returned_evidence_ref_ids")
    owned_refs = trace.get("evidence_ref_ids")
    if not isinstance(returned_refs, list) or not returned_refs:
        errors.append("EVALUABLE requires non-empty returned_evidence_ref_ids")
    elif not all(isinstance(ref, str) for ref in returned_refs):
        errors.append("EVALUABLE returned_evidence_ref_ids must be strings")
    elif not isinstance(owned_refs, list) or not set(returned_refs).issubset(set(owned_refs)):
        errors.append("EVALUABLE returned refs must be owned by the assertion")
    if trace.get("production_error_code") is not None:
        errors.append("EVALUABLE requires production_error_code=None")
    if not isinstance(trace.get("overlay_id"), str) or not trace.get("overlay_id"):
        errors.append("EVALUABLE requires a non-empty overlay_id")
    if trace.get("comparison_metrics_present") is not True:
        errors.append("EVALUABLE requires comparison_metrics_present=True")
    if trace.get("packet_version") != TL01C_PACKET_VERSION:
        errors.append(f"packet_version must be {TL01C_PACKET_VERSION!r}")
    if trace.get("renderer_identity") != RENDERER_IDENTITY:
        errors.append(f"renderer_identity must be {RENDERER_IDENTITY!r}")
    return errors


def _evaluable_success_field_errors(lane: LaneDiagnostic) -> list[str]:
    return _evaluable_success_field_errors_from_mapping(lane.to_trace_dict())


def _paired_identity_mismatches(
    deterministic: PairedDiagnosticResult,
    live: PairedDiagnosticResult,
) -> list[str]:
    errors: list[str] = []
    lanes = (
        deterministic.control,
        deterministic.candidate,
        live.control,
        live.candidate,
    )
    identities = {_fixture_identity_key(lane) for lane in lanes}
    if len(identities) != 1:
        errors.append("fixture identity mismatch across deterministic/live lanes")

    if deterministic.control.lane != "control" or live.control.lane != "control":
        errors.append("control lane identity must be 'control'")
    if deterministic.candidate.lane != "candidate" or live.candidate.lane != "candidate":
        errors.append("candidate lane identity must be 'candidate'")
    if (
        deterministic.control.run_mode != "deterministic"
        or deterministic.candidate.run_mode != "deterministic"
    ):
        errors.append("deterministic pair run_mode must be 'deterministic'")
    if live.control.run_mode != "live" or live.candidate.run_mode != "live":
        errors.append("live pair run_mode must be 'live'")

    errors.extend(
        _frozen_prompt_errors(
            control_version=deterministic.control.prompt_version,
            control_sha=deterministic.control.prompt_sha256,
            candidate_version=deterministic.candidate.prompt_version,
            candidate_sha=deterministic.candidate.prompt_sha256,
        )
    )
    errors.extend(
        _frozen_prompt_errors(
            control_version=live.control.prompt_version,
            control_sha=live.control.prompt_sha256,
            candidate_version=live.candidate.prompt_version,
            candidate_sha=live.candidate.prompt_sha256,
        )
    )

    if deterministic.control.case_digest != live.control.case_digest:
        errors.append("control case_digest mismatch across modes")
    if deterministic.candidate.case_digest != live.candidate.case_digest:
        errors.append("candidate case_digest mismatch across modes")

    for lane in lanes:
        if lane.packet_version != TL01C_PACKET_VERSION:
            errors.append(f"{lane.run_mode}/{lane.lane} packet_version mismatch")
        if lane.renderer_identity != RENDERER_IDENTITY:
            errors.append(f"{lane.run_mode}/{lane.lane} renderer_identity mismatch")

    if live.control.model_id != LIVE_MODEL_ID or live.candidate.model_id != LIVE_MODEL_ID:
        errors.append(f"live model_id must be {LIVE_MODEL_ID!r}")

    implementation_shas = {
        deterministic.control.repository_sha,
        deterministic.candidate.repository_sha,
        live.control.repository_sha,
        live.candidate.repository_sha,
    }
    if len(implementation_shas) != 1:
        errors.append(
            "deterministic and live evidence must share one clean implementation SHA"
        )
    shared_sha = next(iter(implementation_shas))
    if not _is_clean_commit_sha(shared_sha):
        errors.append("shared implementation SHA must be a clean full commit SHA")

    if live.provider_calls < 2:
        errors.append("live provider_calls must be at least 2")
    if not live.control.provider_response_id or not live.candidate.provider_response_id:
        errors.append("live lanes require provider_response_id")

    for lane in lanes:
        errors.extend(_evaluable_success_field_errors(lane))
    return errors


def combine_paired_diagnostic_conclusions(
    *,
    deterministic: PairedDiagnosticResult,
    live: PairedDiagnosticResult,
) -> OverallConclusion:
    """Evidence-bound overall conclusion from actual paired diagnostic objects."""
    if deterministic.live_attempted or deterministic.control.run_mode != "deterministic":
        return "UNRESOLVED_DIAGNOSTIC_GAP"
    if not live.live_attempted or live.control.run_mode != "live":
        return "UNRESOLVED_DIAGNOSTIC_GAP"

    triage = compute_overall_conclusion(
        deterministic_control=deterministic.control.lane_result,
        deterministic_candidate=deterministic.candidate.lane_result,
        live_control=live.control.lane_result,
        live_candidate=live.candidate.lane_result,
    )
    both_evaluable = (
        deterministic.control.lane_result == "EVALUABLE"
        and deterministic.candidate.lane_result == "EVALUABLE"
        and live.control.lane_result == "EVALUABLE"
        and live.candidate.lane_result == "EVALUABLE"
    )
    if not both_evaluable:
        return triage

    mismatches = _paired_identity_mismatches(deterministic, live)
    if mismatches:
        return "UNRESOLVED_DIAGNOSTIC_GAP"
    return "GROUNDING_PATH_READY"


def _summary_pair_contract_errors(
    *,
    deterministic_summary: dict[str, Any],
    live_summary: dict[str, Any],
    det_control: dict[str, Any],
    det_candidate: dict[str, Any],
    live_control: dict[str, Any],
    live_candidate: dict[str, Any],
) -> list[str]:
    errors: list[str] = []
    if det_control.get("lane") != "control" or live_control.get("lane") != "control":
        errors.append("control lane identity must be 'control'")
    if det_candidate.get("lane") != "candidate" or live_candidate.get("lane") != "candidate":
        errors.append("candidate lane identity must be 'candidate'")
    if det_control.get("run_mode") != "deterministic" or det_candidate.get("run_mode") != "deterministic":
        errors.append("deterministic traces require run_mode='deterministic'")
    if live_control.get("run_mode") != "live" or live_candidate.get("run_mode") != "live":
        errors.append("live traces require run_mode='live'")

    errors.extend(
        _frozen_prompt_errors(
            control_version=det_control.get("prompt_version"),
            control_sha=det_control.get("prompt_sha256"),
            candidate_version=det_candidate.get("prompt_version"),
            candidate_sha=det_candidate.get("prompt_sha256"),
        )
    )
    errors.extend(
        _frozen_prompt_errors(
            control_version=live_control.get("prompt_version"),
            control_sha=live_control.get("prompt_sha256"),
            candidate_version=live_candidate.get("prompt_version"),
            candidate_sha=live_candidate.get("prompt_sha256"),
        )
    )

    identities = [
        _trace_fixture_identity_key(trace)
        for trace in (det_control, det_candidate, live_control, live_candidate)
    ]
    if any(identity is None for identity in identities) or len(set(identities)) != 1:
        errors.append("fixture identity mismatch across deterministic/live traces")
    if det_control.get("case_digest") != live_control.get("case_digest"):
        errors.append("control case_digest mismatch across modes")
    if det_candidate.get("case_digest") != live_candidate.get("case_digest"):
        errors.append("candidate case_digest mismatch across modes")
    if live_control.get("model_id") != LIVE_MODEL_ID or live_candidate.get("model_id") != LIVE_MODEL_ID:
        errors.append(f"live model_id must be {LIVE_MODEL_ID!r}")

    implementation_shas = {
        det_control.get("repository_sha"),
        det_candidate.get("repository_sha"),
        live_control.get("repository_sha"),
        live_candidate.get("repository_sha"),
        deterministic_summary.get("repository_sha"),
        live_summary.get("repository_sha"),
    }
    if len(implementation_shas) != 1:
        errors.append(
            "deterministic and live evidence must share one clean implementation SHA"
        )
    shared_sha = next(iter(implementation_shas))
    if not _is_clean_commit_sha(shared_sha if isinstance(shared_sha, str) else None):
        errors.append("shared implementation SHA must be a clean full commit SHA")

    if int(live_summary.get("provider_calls") or 0) < 2:
        errors.append("live provider_calls must be at least 2")
    if not live_control.get("provider_response_id") or not live_candidate.get(
        "provider_response_id"
    ):
        errors.append("live lanes require provider_response_id")

    for trace in (det_control, det_candidate, live_control, live_candidate):
        errors.extend(_evaluable_success_field_errors_from_mapping(trace))
    return errors


def combine_paired_summary_conclusions(
    *,
    deterministic_summary: dict[str, Any],
    live_summary: dict[str, Any],
) -> OverallConclusion:
    """Evidence-bound conclusion from saved paired-summary.json traces."""
    if deterministic_summary.get("run_mode") != "deterministic":
        return "UNRESOLVED_DIAGNOSTIC_GAP"
    if live_summary.get("run_mode") != "live":
        return "UNRESOLVED_DIAGNOSTIC_GAP"

    det_control = deterministic_summary.get("control")
    det_candidate = deterministic_summary.get("candidate")
    live_control = live_summary.get("control")
    live_candidate = live_summary.get("candidate")
    if not all(
        isinstance(trace, dict)
        for trace in (det_control, det_candidate, live_control, live_candidate)
    ):
        return "UNRESOLVED_DIAGNOSTIC_GAP"

    triage = compute_overall_conclusion(
        deterministic_control=det_control.get("lane_result"),
        deterministic_candidate=det_candidate.get("lane_result"),
        live_control=live_control.get("lane_result"),
        live_candidate=live_candidate.get("lane_result"),
    )
    both_evaluable = all(
        trace.get("lane_result") == "EVALUABLE"
        for trace in (det_control, det_candidate, live_control, live_candidate)
    )
    if not both_evaluable:
        return triage

    if _summary_pair_contract_errors(
        deterministic_summary=deterministic_summary,
        live_summary=live_summary,
        det_control=det_control,
        det_candidate=det_candidate,
        live_control=live_control,
        live_candidate=live_candidate,
    ):
        return "UNRESOLVED_DIAGNOSTIC_GAP"
    return "GROUNDING_PATH_READY"


@dataclass
class ProviderBudgetLedger:
    path: Path
    total_calls: int
    response_ids: list[str]
    entries: list[dict[str, Any]]

    @property
    def remaining(self) -> int:
        return max(0, MAX_TOTAL_PROVIDER_CALLS - self.total_calls)


def canonical_budget_ledger_path(repo_root: Path) -> Path:
    return (repo_root / SMOKE_FIXTURE_RELATIVE / DEFAULT_BUDGET_LEDGER_NAME).resolve()


def resolve_live_budget_ledger_path(
    *,
    repo_root: Path,
    requested: Path | None,
) -> Path:
    """Live mode may use only the canonical fixture ledger path."""
    canonical = canonical_budget_ledger_path(repo_root)
    if requested is None:
        return canonical
    try:
        resolved = requested.resolve()
    except OSError as exc:
        raise TemporalShadowExtractionError(
            "Unable to resolve budget ledger path",
            code="invalid_case",
            diagnostics=[str(requested)],
        ) from exc
    if resolved != canonical:
        raise TemporalShadowExtractionError(
            "Alternate provider budget ledger path rejected",
            code="invalid_case",
            diagnostics=[
                f"requested={str(resolved)}",
                f"canonical={str(canonical)}",
                "live mode requires the canonical smoke fixture ledger",
            ],
        )
    return canonical


def load_provider_budget_ledger(path: Path) -> ProviderBudgetLedger:
    if not path.is_file():
        raise TemporalShadowExtractionError(
            "Provider budget ledger is missing",
            code="invalid_case",
            diagnostics=[f"path={str(path)}"],
        )
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TemporalShadowExtractionError(
            "Provider budget ledger must be a JSON object",
            code="invalid_case",
        )
    if payload.get("schema") != BUDGET_LEDGER_SCHEMA:
        raise TemporalShadowExtractionError(
            "Provider budget ledger schema mismatch",
            code="invalid_case",
            diagnostics=[f"expected={BUDGET_LEDGER_SCHEMA!r}"],
        )
    entries = [
        item for item in (payload.get("entries") or []) if isinstance(item, dict)
    ]
    entry_calls = 0
    entry_response_ids: list[str] = []
    for entry in entries:
        calls = entry.get("calls")
        if not isinstance(calls, int) or calls < 0:
            raise TemporalShadowExtractionError(
                "Provider budget ledger entry has invalid calls",
                code="invalid_case",
            )
        entry_calls += calls
        refs = entry.get("response_ids") or []
        if not isinstance(refs, list) or not all(isinstance(item, str) for item in refs):
            raise TemporalShadowExtractionError(
                "Provider budget ledger entry response_ids must be strings",
                code="invalid_case",
            )
        if len(refs) > calls:
            raise TemporalShadowExtractionError(
                "Provider budget ledger entry has more response_ids than calls",
                code="invalid_case",
                diagnostics=[f"calls={calls}", f"response_ids={len(refs)}"],
            )
        entry_response_ids.extend(refs)

    declared_total = payload.get("total_calls")
    if not isinstance(declared_total, int):
        raise TemporalShadowExtractionError(
            "Provider budget ledger total_calls must be an int",
            code="invalid_case",
        )
    if declared_total != entry_calls:
        raise TemporalShadowExtractionError(
            "Provider budget ledger total_calls does not reconcile to entries",
            code="invalid_case",
            diagnostics=[
                f"total_calls={declared_total}",
                f"entry_sum={entry_calls}",
            ],
        )
    declared_ids = payload.get("response_ids") or []
    if not isinstance(declared_ids, list) or not all(
        isinstance(item, str) for item in declared_ids
    ):
        raise TemporalShadowExtractionError(
            "Provider budget ledger response_ids must be a string list",
            code="invalid_case",
        )
    if declared_ids != entry_response_ids:
        raise TemporalShadowExtractionError(
            "Provider budget ledger response_ids do not reconcile to entries",
            code="invalid_case",
        )
    if declared_total > MAX_TOTAL_PROVIDER_CALLS:
        raise TemporalShadowExtractionError(
            "Provider budget ledger exceeds maximum total provider calls",
            code="invalid_case",
            diagnostics=[
                f"total_calls={declared_total}",
                f"max={MAX_TOTAL_PROVIDER_CALLS}",
            ],
        )
    return ProviderBudgetLedger(
        path=path,
        total_calls=declared_total,
        response_ids=list(declared_ids),
        entries=entries,
    )


def save_provider_budget_ledger(ledger: ProviderBudgetLedger) -> None:
    payload = {
        "schema": BUDGET_LEDGER_SCHEMA,
        "max_total_provider_calls": MAX_TOTAL_PROVIDER_CALLS,
        "total_calls": ledger.total_calls,
        "response_ids": list(ledger.response_ids),
        "entries": list(ledger.entries),
    }
    ledger.path.parent.mkdir(parents=True, exist_ok=True)
    ledger.path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def assert_provider_budget_available(
    ledger: ProviderBudgetLedger, *, calls_needed: int
) -> None:
    if calls_needed < 0:
        raise TemporalShadowExtractionError(
            "Provider budget reservation must be non-negative",
            code="invalid_case",
        )
    if ledger.total_calls + calls_needed > MAX_TOTAL_PROVIDER_CALLS:
        raise TemporalShadowExtractionError(
            "Global provider call budget exhausted or insufficient remaining",
            code="invalid_case",
            diagnostics=[
                f"total_calls={ledger.total_calls}",
                f"calls_needed={calls_needed}",
                f"max={MAX_TOTAL_PROVIDER_CALLS}",
                f"ledger={str(ledger.path)}",
            ],
        )


def record_provider_budget_entry(
    ledger: ProviderBudgetLedger,
    *,
    phase: RunPhase,
    repository_sha: str,
    calls: int,
    response_ids: list[str],
    note: str | None = None,
) -> ProviderBudgetLedger:
    """Persist one budget entry. Response IDs are optional per charged attempt."""
    if len(response_ids) > calls:
        raise TemporalShadowExtractionError(
            "Provider budget entry has more response_ids than calls",
            code="invalid_case",
            diagnostics=[f"calls={calls}", f"response_ids={len(response_ids)}"],
        )
    assert_provider_budget_available(ledger, calls_needed=calls)
    entry: dict[str, Any] = {
        "phase": phase,
        "repository_sha": repository_sha,
        "calls": calls,
        "response_ids": list(response_ids),
    }
    if note:
        entry["note"] = note
    updated = ProviderBudgetLedger(
        path=ledger.path,
        total_calls=ledger.total_calls + calls,
        response_ids=[*ledger.response_ids, *response_ids],
        entries=[*ledger.entries, entry],
    )
    save_provider_budget_ledger(updated)
    return updated


def transport_accepted_for_error(
    error: TemporalShadowExtractionError | None,
    *,
    succeeded: bool,
    raw_batch: dict[str, Any] | None,
) -> bool | None:
    """Whether transport validation accepted a usable raw batch.

    Must not report True beside TRANSPORT_REJECTED or provider execution failure.
    """
    if succeeded:
        return True
    if error is None:
        return None if raw_batch is None else True
    if error.code in {"provider_refusal", "provider_incomplete", "provider_error"}:
        return False
    if error.code == "invalid_model_output":
        return False
    if raw_batch is not None:
        return True
    return False


@dataclass
class LaneDiagnostic:
    lane: LaneName
    case_id: str
    case_digest: str
    prompt_version: str
    prompt_sha256: str
    packet_version: str
    renderer_identity: str
    model_id: str
    assertion_id: str
    evidence_ref_ids: list[str]
    resolved_span_digest: str
    expected_phrase: str
    packet_phrase_present: bool
    renderer_phrase_present: bool
    transport_accepted: bool | None
    returned_evidence_ref_ids: list[str] | None
    returned_source_phrase: str | None
    owned_evidence_check: str | None
    phrase_match: bool | None
    phrase_match_evidence_ref_id: str | None
    phrase_match_offset: int | None
    production_error_code: str | None
    production_diagnostics: list[str] | None
    overlay_id: str | None
    comparison_metrics_present: bool
    comparison_metrics: dict[str, Any] | None
    provider_response_id: str | None
    lane_result: LaneResult
    run_mode: RunMode
    phase: RunPhase
    repository_sha: str

    def to_trace_dict(self) -> dict[str, Any]:
        return {
            "repository_sha": self.repository_sha,
            "run_mode": self.run_mode,
            "phase": self.phase,
            "lane": self.lane,
            "case_id": self.case_id,
            "case_digest": self.case_digest,
            "prompt_version": self.prompt_version,
            "prompt_sha256": self.prompt_sha256,
            "packet_version": self.packet_version,
            "renderer_identity": self.renderer_identity,
            "model_id": self.model_id,
            "provider_response_id": self.provider_response_id,
            "assertion_id": self.assertion_id,
            "evidence_ref_ids": self.evidence_ref_ids,
            "resolved_span_digest": self.resolved_span_digest,
            "expected_phrase": _bounded_text(self.expected_phrase),
            "packet_phrase_present": self.packet_phrase_present,
            "renderer_phrase_present": self.renderer_phrase_present,
            "transport_accepted": self.transport_accepted,
            "returned_evidence_ref_ids": self.returned_evidence_ref_ids,
            "returned_source_phrase": _bounded_text(self.returned_source_phrase),
            "owned_evidence_check": self.owned_evidence_check,
            "phrase_match": self.phrase_match,
            "phrase_match_evidence_ref_id": self.phrase_match_evidence_ref_id,
            "phrase_match_offset": self.phrase_match_offset,
            "production_error_code": self.production_error_code,
            "production_diagnostics": self.production_diagnostics,
            "overlay_id": self.overlay_id,
            "comparison_metrics_present": self.comparison_metrics_present,
            "comparison_metrics": self.comparison_metrics,
            "lane_result": self.lane_result,
        }


def run_lane_diagnostic(
    *,
    lane: LaneName,
    case_path: Path,
    output_dir: Path,
    mode: RunMode,
    phase: RunPhase,
    model_id: str,
    client: TemporalShadowExtractionClient,
    repo_root: Path,
    ledger: ProviderCallLedger | None = None,
    overwrite: bool = False,
) -> LaneDiagnostic:
    case = load_temporal_shadow_extraction_case(case_path, repo_root=repo_root)
    contribution = _load_contribution(case_path, repo_root=repo_root)
    spec = resolve_prompt_spec(case.prompt_version)
    packets = build_assertion_evidence_packets(
        contribution,
        case,
        repo_root=repo_root,
        packet_version=spec.packet_version,
    )
    expected_phrase, assertion_id, owned_refs = expected_phrase_from_fixture(
        contribution=contribution,
        case=case,
        repo_root=repo_root,
    )
    packet_present = packet_contains_phrase(
        packets,
        assertion_id=assertion_id,
        evidence_ref_ids=owned_refs,
        expected_phrase=expected_phrase,
    )
    user_content = spec.render_user_content(packets, case.selected_assertion_ids)
    renderer_present = decoded_renderer_contains_phrase(user_content, expected_phrase)
    span_digest = _resolved_span_digest(
        packets, assertion_id=assertion_id, evidence_ref_id=owned_refs[0]
    )

    recording = RecordingTemporalShadowClient(
        client, ledger=ledger, record_provider_calls=(mode == "live")
    )
    lane_out = output_dir / lane
    error: TemporalShadowExtractionError | None = None
    succeeded = False
    overlay_id: str | None = None
    comparison_metrics: dict[str, Any] | None = None
    comparison_metrics_present = False
    transport_accepted: bool | None = None
    returned_phrase: str | None = None
    returned_refs: list[str] | None = None
    phrase_match: bool | None = None
    phrase_match_ref: str | None = None
    phrase_match_offset: int | None = None
    owned_check: str | None = None
    provider_response_id: str | None = None

    if packet_present and renderer_present:
        try:
            run = run_temporal_shadow_extraction(
                case_path,
                lane_out,
                client=recording,
                model_id=model_id,
                repo_root=repo_root,
                overwrite=overwrite,
            )
            succeeded = True
            overlay_id = run.overlay_id
            provider_response_id = run.provider_response_id or None
            transport_accepted = True
            comparison_path = lane_out / "comparison.json"
            if comparison_path.is_file():
                comparison_payload = json.loads(comparison_path.read_text(encoding="utf-8"))
                metrics = comparison_payload.get("metrics")
                if isinstance(metrics, dict):
                    comparison_metrics = {
                        k: metrics[k]
                        for k in sorted(metrics)
                        if isinstance(metrics[k], (int, float, bool))
                    }
                    comparison_metrics_present = True
        except TemporalShadowExtractionError as exc:
            error = exc
            provider_response_id = exc.provider_response_id or (
                recording.last_provider_meta.response_id
                if recording.last_provider_meta is not None
                else None
            )
            transport_accepted = transport_accepted_for_error(
                exc,
                succeeded=False,
                raw_batch=recording.last_raw_batch,
            )
    else:
        transport_accepted = None

    raw_batch = recording.last_raw_batch
    returned_phrase, returned_refs, raw_well_formed = _annotation_from_raw_batch(
        raw_batch, assertion_id=assertion_id
    )
    if not raw_well_formed:
        transport_accepted = False
        returned_phrase = None
        returned_refs = None
        phrase_match = None
        phrase_match_ref = None
        phrase_match_offset = None
        owned_check = "malformed_raw_batch"
        if error is None or error.code != "invalid_model_output":
            error = TemporalShadowExtractionError(
                "Diagnostic observed malformed provider raw batch",
                code="invalid_model_output",
                provider_response_id=provider_response_id,
            )
            succeeded = False
            comparison_metrics_present = False
            comparison_metrics = None
            overlay_id = None
    elif raw_batch is not None:
        if returned_refs is None or len(returned_refs) == 0:
            phrase_match = False
            phrase_match_ref = None
            phrase_match_offset = None
            owned_check = "foreign_or_missing"
        else:
            phrase_match, phrase_match_ref, phrase_match_offset = (
                _phrase_match_in_owned_snippet(
                    returned_phrase=returned_phrase,
                    evidence_ref_ids=returned_refs,
                    packets=packets,
                    assertion_id=assertion_id,
                )
            )
            if error is not None and error.foreign_evidence_attempts > 0:
                owned_check = "foreign_or_missing"
            elif not set(returned_refs).issubset(set(owned_refs)):
                owned_check = "foreign_or_missing"
            elif phrase_match:
                owned_check = "owned_match"
            elif returned_phrase is not None:
                owned_check = "phrase_not_in_owned_snippet"
            else:
                owned_check = "missing_returned_phrase"

    lane_result = classify_lane_result(
        packet_phrase_present=packet_present,
        renderer_phrase_present=renderer_present,
        run_mode=mode,
        error=error,
        raw_batch=raw_batch if raw_well_formed else None,
        packets=packets,
        assertion_id=assertion_id,
        owned_evidence_ref_ids=owned_refs,
        comparison_metrics_present=comparison_metrics_present,
        succeeded=succeeded,
        raw_batch_well_formed=raw_well_formed,
    )

    diagnostic = LaneDiagnostic(
        lane=lane,
        case_id=case.case_id,
        case_digest=_file_sha256(case_path),
        prompt_version=case.prompt_version,
        prompt_sha256=compute_prompt_sha256(case.prompt_version),
        packet_version=spec.packet_version,
        renderer_identity=RENDERER_IDENTITY,
        model_id=model_id,
        assertion_id=assertion_id,
        evidence_ref_ids=owned_refs,
        resolved_span_digest=span_digest,
        expected_phrase=expected_phrase,
        packet_phrase_present=packet_present,
        renderer_phrase_present=renderer_present,
        transport_accepted=transport_accepted,
        returned_evidence_ref_ids=returned_refs,
        returned_source_phrase=returned_phrase,
        owned_evidence_check=owned_check,
        phrase_match=phrase_match,
        phrase_match_evidence_ref_id=phrase_match_ref,
        phrase_match_offset=phrase_match_offset,
        production_error_code=error.code if error is not None else None,
        production_diagnostics=(error.diagnostics[:8] if error is not None else None),
        overlay_id=overlay_id,
        comparison_metrics_present=comparison_metrics_present,
        comparison_metrics=comparison_metrics,
        provider_response_id=provider_response_id,
        lane_result=lane_result,
        run_mode=mode,
        phase=phase,
        repository_sha=_repository_sha(repo_root=repo_root),
    )
    return diagnostic


def write_trace_artifact(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    for forbidden in FORBIDDEN_TRACE_SUBSTRINGS:
        if forbidden in serialized:
            raise TemporalShadowExtractionError(
                f"Trace artifact contains forbidden content: {forbidden!r}",
                code="invalid_case",
            )
    path.write_text(serialized, encoding="utf-8")


@dataclass
class PairedDiagnosticResult:
    control: LaneDiagnostic
    candidate: LaneDiagnostic
    provider_calls: int
    overall_conclusion: OverallConclusion
    live_attempted: bool


def run_paired_grounding_path_diagnostic(
    *,
    control_case_path: Path,
    candidate_case_path: Path,
    output_dir: Path,
    mode: RunMode,
    phase: RunPhase,
    model_id: str,
    fake_output: dict[str, Any] | None,
    repo_root: Path,
    overwrite: bool = False,
    budget_ledger_path: Path | None = None,
) -> PairedDiagnosticResult:
    validate_paired_cases(control_case_path, candidate_case_path, repo_root=repo_root)

    live_attempted = False
    persistent_budget: ProviderBudgetLedger | None = None
    if mode == "live":
        if os.environ.get(LIVE_OPT_IN_ENV) != "1":
            raise TemporalShadowExtractionError(
                f"Live mode requires {LIVE_OPT_IN_ENV}=1",
                code="invalid_case",
            )
        if model_id != LIVE_MODEL_ID:
            raise TemporalShadowExtractionError(
                f"Live smoke requires model_id={LIVE_MODEL_ID!r}",
                code="invalid_case",
                diagnostics=[f"got={model_id!r}"],
            )
        if budget_ledger_path is None:
            budget_ledger_path = canonical_budget_ledger_path(repo_root)
        budget_ledger_path = resolve_live_budget_ledger_path(
            repo_root=repo_root,
            requested=budget_ledger_path,
        )
        persistent_budget = load_provider_budget_ledger(budget_ledger_path)
        assert_provider_budget_available(
            persistent_budget, calls_needed=PHASE_CALL_BUDGET
        )
        delegate: TemporalShadowExtractionClient = OpenAITemporalShadowExtractionClient()
        live_attempted = True
    else:
        if fake_output is None:
            raise TemporalShadowExtractionError(
                "Deterministic mode requires fake_output",
                code="invalid_case",
            )
        delegate = FakeTemporalShadowExtractionClient(fake_output)

    ledger = ProviderCallLedger(phase=phase)
    try:
        control = run_lane_diagnostic(
            lane="control",
            case_path=control_case_path,
            output_dir=output_dir,
            mode=mode,
            phase=phase,
            model_id=model_id,
            client=delegate,
            repo_root=repo_root,
            ledger=ledger,
            overwrite=overwrite,
        )
        ledger.assert_budget()
        candidate = run_lane_diagnostic(
            lane="candidate",
            case_path=candidate_case_path,
            output_dir=output_dir,
            mode=mode,
            phase=phase,
            model_id=model_id,
            client=delegate,
            repo_root=repo_root,
            ledger=ledger,
            overwrite=overwrite,
        )
        ledger.assert_budget()
    finally:
        if persistent_budget is not None and ledger.calls > 0:
            record_provider_budget_entry(
                persistent_budget,
                phase=phase,
                repository_sha=_repository_sha(repo_root=repo_root),
                calls=ledger.calls,
                response_ids=list(ledger.response_ids),
            )

    if ledger.calls > MAX_TOTAL_PROVIDER_CALLS:
        raise TemporalShadowExtractionError(
            "Global provider call budget exceeded",
            code="invalid_case",
            diagnostics=[f"calls={ledger.calls}", f"max={MAX_TOTAL_PROVIDER_CALLS}"],
        )

    # Single-mode invocations cannot claim GROUNDING_PATH_READY; that requires
    # evidence-bound combination of deterministic + live PairedDiagnosticResult.
    if mode == "deterministic":
        overall = compute_overall_conclusion(
            deterministic_control=control.lane_result,
            deterministic_candidate=candidate.lane_result,
        )
    else:
        overall = compute_overall_conclusion(
            live_control=control.lane_result,
            live_candidate=candidate.lane_result,
        )

    summary = {
        "repository_sha": _repository_sha(repo_root=repo_root),
        "run_mode": mode,
        "phase": phase,
        "provider_calls": ledger.calls,
        "provider_response_ids": ledger.response_ids,
        "overall_conclusion": overall,
        "control": control.to_trace_dict(),
        "candidate": candidate.to_trace_dict(),
    }
    if persistent_budget is not None:
        refreshed = load_provider_budget_ledger(persistent_budget.path)
        summary["budget_ledger_path"] = str(persistent_budget.path)
        summary["budget_total_calls"] = refreshed.total_calls
        summary["budget_max_total_calls"] = MAX_TOTAL_PROVIDER_CALLS
        summary["budget_remaining"] = refreshed.remaining
    write_trace_artifact(output_dir / "paired-summary.json", summary)
    write_trace_artifact(output_dir / "control-trace.json", control.to_trace_dict())
    write_trace_artifact(output_dir / "candidate-trace.json", candidate.to_trace_dict())

    return PairedDiagnosticResult(
        control=control,
        candidate=candidate,
        provider_calls=ledger.calls,
        overall_conclusion=overall,
        live_attempted=live_attempted,
    )


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--control-case", type=Path, required=True)
    parser.add_argument("--candidate-case", type=Path, required=True)
    parser.add_argument("--fake-output", type=Path, default=None)
    parser.add_argument("--model-id", default=LIVE_MODEL_ID)
    parser.add_argument(
        "--mode",
        choices=("deterministic", "live"),
        default="deterministic",
    )
    parser.add_argument(
        "--phase",
        choices=("initial", "post_fix"),
        default="initial",
    )
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument(
        "--budget-ledger",
        type=Path,
        default=None,
        help=(
            "Must be the canonical smoke fixture provider-budget-ledger.json "
            "(alternate paths are rejected)"
        ),
    )
    parser.add_argument(
        "--combine-with-deterministic-summary",
        type=Path,
        default=None,
        help="Optional deterministic paired-summary.json to evidence-bind overall READY",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    fake_output: dict[str, Any] | None = None
    if args.mode == "deterministic":
        if args.fake_output is None:
            print("deterministic mode requires --fake-output", file=sys.stderr)
            return 2
        fake_output = json.loads(args.fake_output.read_text(encoding="utf-8"))

    budget_ledger = args.budget_ledger
    if args.mode == "live":
        budget_ledger = resolve_live_budget_ledger_path(
            repo_root=_REPO_ROOT,
            requested=budget_ledger,
        )

    result = run_paired_grounding_path_diagnostic(
        control_case_path=args.control_case,
        candidate_case_path=args.candidate_case,
        output_dir=args.output_dir,
        mode=args.mode,
        phase=args.phase,
        model_id=args.model_id,
        fake_output=fake_output,
        repo_root=_REPO_ROOT,
        overwrite=args.overwrite,
        budget_ledger_path=budget_ledger,
    )
    print(f"control:   {result.control.lane_result}")
    print(f"candidate: {result.candidate.lane_result}")
    print(f"provider calls: {result.provider_calls}")
    print(
        "comparison metrics present: "
        f"{result.control.comparison_metrics_present} / "
        f"{result.candidate.comparison_metrics_present}"
    )
    overall = result.overall_conclusion
    if args.combine_with_deterministic_summary is not None:
        det_summary = json.loads(
            args.combine_with_deterministic_summary.read_text(encoding="utf-8")
        )
        live_summary = json.loads(
            (args.output_dir / "paired-summary.json").read_text(encoding="utf-8")
        )
        overall = combine_paired_summary_conclusions(
            deterministic_summary=det_summary,
            live_summary=live_summary,
        )
        print(f"combined overall: {overall}")
    else:
        print(f"overall: {overall}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
