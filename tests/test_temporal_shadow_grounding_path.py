"""Tests for TL01 shared source-phrase grounding-path diagnostic."""

from __future__ import annotations

import copy
import json
import subprocess
import sys
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
_SRC = REPO_ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from graph_memory.kernel.contribution_models import GraphContribution  # noqa: E402
from graph_memory.kernel.contributions import explicit_assertion_evidence_ref_ids  # noqa: E402
from graph_memory.temporal_shadow_extraction import (  # noqa: E402
    FakeTemporalShadowExtractionClient,
    TL01C_PACKET_VERSION,
    TemporalShadowExtractionError,
    build_assertion_evidence_packets,
    compute_prompt_sha256,
    load_temporal_shadow_extraction_case,
    render_temporal_shadow_user_content_v2,
    resolve_prompt_spec,
)
from evals.graph_memory_layer import temporal_shadow_grounding_path as grounding  # noqa: E402
from tests.test_temporal_shadow_extraction_tl01g import (  # noqa: E402
    FROZEN_TL01F_PROMPT_SHA256,
    FROZEN_TL01G_PROMPT_SHA256,
    LAST_RETIRED_ADVERSARIAL_VERSION,
    LAST_RETIRED_HOLDOUT_VERSION,
    _discover_cohorts_above_retired_cutoff,
)

FIXTURE = REPO_ROOT / "evals/graph_memory_layer/examples/temporal_shadow_grounding_smoke_v1"
CONTROL_CASE = FIXTURE / "temporal-case-tl01f.json"
CANDIDATE_CASE = FIXTURE / "temporal-case-tl01g.json"
FAKE_OUTPUT_PATH = FIXTURE / "fake-model-output.json"
EXPECTED_PHRASE = "the brass moth struck the north bell exactly twice"

FROZEN_PROMPT_SHA256S = {
    "tl01f-v1": FROZEN_TL01F_PROMPT_SHA256,
    "tl01g-v1": FROZEN_TL01G_PROMPT_SHA256,
}


def _load_fake_output() -> dict[str, Any]:
    return json.loads(FAKE_OUTPUT_PATH.read_text(encoding="utf-8"))


def _load_contribution(case_path: Path) -> GraphContribution:
    case = load_temporal_shadow_extraction_case(case_path, repo_root=REPO_ROOT)
    base_path = REPO_ROOT / case.base_contribution_path
    return GraphContribution.model_validate(json.loads(base_path.read_text(encoding="utf-8")))


def test_fixture_inventory_one_assertion_one_owned_ref_unique_ascii_phrase() -> None:
    contribution = _load_contribution(CONTROL_CASE)
    case = load_temporal_shadow_extraction_case(CONTROL_CASE, repo_root=REPO_ROOT)
    assert len(case.selected_assertion_ids) == 1
    assertion = contribution.candidate_assertions[0]
    owned = explicit_assertion_evidence_ref_ids(assertion)
    assert len(owned) == 1
    source = (FIXTURE / "source.md").read_text(encoding="utf-8")
    assert EXPECTED_PHRASE in source
    assert source.count(EXPECTED_PHRASE) == 1
    assert EXPECTED_PHRASE.isascii()


def test_paired_cases_differ_only_by_frozen_prompt_identity() -> None:
    control, candidate = grounding.validate_paired_cases(
        CONTROL_CASE, CANDIDATE_CASE, repo_root=REPO_ROOT
    )
    assert control.prompt_version == "tl01f-v1"
    assert candidate.prompt_version == "tl01g-v1"
    assert grounding._case_pair_fields(control) == grounding._case_pair_fields(candidate)


def test_paired_validation_fails_before_delegate_on_other_diffs(tmp_path: Path) -> None:
    bad = json.loads(CANDIDATE_CASE.read_text(encoding="utf-8"))
    bad["snippet_max_chars"] = 1999
    bad_path = tmp_path / "bad-case.json"
    bad_path.write_text(json.dumps(bad, indent=2) + "\n", encoding="utf-8")
    with pytest.raises(TemporalShadowExtractionError) as exc:
        grounding.validate_paired_cases(CONTROL_CASE, bad_path, repo_root=REPO_ROOT)
    assert exc.value.code == "invalid_case"


def test_frozen_prompt_hashes_match_known_sha256() -> None:
    for version, expected in FROZEN_PROMPT_SHA256S.items():
        assert compute_prompt_sha256(version) == expected


def test_packet_contains_phrase_and_renderer_preserves_decoded_phrase() -> None:
    contribution = _load_contribution(CONTROL_CASE)
    case = load_temporal_shadow_extraction_case(CONTROL_CASE, repo_root=REPO_ROOT)
    spec = resolve_prompt_spec(case.prompt_version)
    packets = build_assertion_evidence_packets(
        contribution,
        case,
        repo_root=REPO_ROOT,
        packet_version=spec.packet_version,
    )
    assertion_id = case.selected_assertion_ids[0]
    owned = list(explicit_assertion_evidence_ref_ids(contribution.candidate_assertions[0]))
    assert grounding.packet_contains_phrase(
        packets,
        assertion_id=assertion_id,
        evidence_ref_ids=owned,
        expected_phrase=EXPECTED_PHRASE,
    )
    rendered = render_temporal_shadow_user_content_v2(packets, case.selected_assertion_ids)
    decoded = json.loads(rendered)
    snippet = decoded["assertion_packets"][0]["evidence_snippets"][0]["preview_snippet"]
    assert EXPECTED_PHRASE in snippet


def test_fake_control_and_candidate_reach_evaluable_with_metrics(tmp_path: Path) -> None:
    fake = _load_fake_output()
    result = grounding.run_paired_grounding_path_diagnostic(
        control_case_path=CONTROL_CASE,
        candidate_case_path=CANDIDATE_CASE,
        output_dir=tmp_path / "paired",
        mode="deterministic",
        phase="initial",
        model_id="fake-model",
        fake_output=fake,
        repo_root=REPO_ROOT,
        overwrite=True,
    )
    assert result.control.lane_result == "EVALUABLE"
    assert result.candidate.lane_result == "EVALUABLE"
    assert result.control.comparison_metrics_present is True
    assert result.candidate.comparison_metrics_present is True
    assert result.provider_calls == 0


@pytest.mark.parametrize(
    ("mutator", "expected_lane"),
    [
        (
            lambda batch: batch["annotations"][0].update({"source_phrase": "paraphrased phrase"}),
            "PROVIDER_PHRASE_FIDELITY_BLOCKED",
        ),
        (
            lambda batch: batch["annotations"][0].update(
                {"evidence_ref_ids": ["evidence:foreign:not-owned"]}
            ),
            "EVIDENCE_OWNERSHIP_MISMATCH",
        ),
        (
            lambda batch: batch["annotations"][0].update({"evidence_ref_ids": []}),
            "EVIDENCE_OWNERSHIP_MISMATCH",
        ),
        (
            lambda batch: batch["annotations"][0].update({"interpretation_status": "not_a_status"}),
            "TRANSPORT_REJECTED",
        ),
    ],
)
def test_injected_failures_match_production_lane_results(
    tmp_path: Path,
    mutator: Any,
    expected_lane: str,
) -> None:
    fake = copy.deepcopy(_load_fake_output())
    mutator(fake)
    result = grounding.run_paired_grounding_path_diagnostic(
        control_case_path=CONTROL_CASE,
        candidate_case_path=CANDIDATE_CASE,
        output_dir=tmp_path / "fail",
        mode="deterministic",
        phase="initial",
        model_id="fake-model",
        fake_output=fake,
        repo_root=REPO_ROOT,
        overwrite=True,
    )
    assert result.control.lane_result == expected_lane


def test_foreign_evidence_yields_evidence_ownership_mismatch(tmp_path: Path) -> None:
    fake = copy.deepcopy(_load_fake_output())
    fake["annotations"][0]["evidence_ref_ids"] = ["evidence:foreign:not-owned"]
    result = grounding.run_lane_diagnostic(
        lane="control",
        case_path=CONTROL_CASE,
        output_dir=tmp_path / "foreign",
        mode="deterministic",
        phase="initial",
        model_id="fake-model",
        client=FakeTemporalShadowExtractionClient(fake),
        repo_root=REPO_ROOT,
        overwrite=True,
    )
    assert result.lane_result == "EVIDENCE_OWNERSHIP_MISMATCH"


def test_missing_metrics_not_presented_as_zero(tmp_path: Path) -> None:
    class NoComparisonClient(FakeTemporalShadowExtractionClient):
        def extract_annotations(self, *, instructions: str, user_content: str, model_id: str):
            batch, meta = super().extract_annotations(
                instructions=instructions,
                user_content=user_content,
                model_id=model_id,
            )
            return batch, meta

    fake = _load_fake_output()
    result = grounding.run_lane_diagnostic(
        lane="control",
        case_path=CONTROL_CASE,
        output_dir=tmp_path / "lane",
        mode="deterministic",
        phase="initial",
        model_id="fake-model",
        client=NoComparisonClient(fake),
        repo_root=REPO_ROOT,
        overwrite=True,
    )
    assert result.comparison_metrics_present is True
    assert result.comparison_metrics is not None
    assert result.comparison_metrics.get("exact_match_count") == 1

    broken = grounding.LaneDiagnostic(
        lane="control",
        case_id="x",
        case_digest="y",
        prompt_version="tl01f-v1",
        prompt_sha256="z",
        packet_version=TL01C_PACKET_VERSION,
        renderer_identity=grounding.RENDERER_IDENTITY,
        model_id="fake",
        assertion_id="assertion:a",
        evidence_ref_ids=["evidence:a"],
        resolved_span_digest="deadbeef",
        expected_phrase=EXPECTED_PHRASE,
        packet_phrase_present=True,
        renderer_phrase_present=True,
        transport_accepted=True,
        returned_evidence_ref_ids=["evidence:a"],
        returned_source_phrase=EXPECTED_PHRASE,
        owned_evidence_check="owned_match",
        phrase_match=True,
        phrase_match_evidence_ref_id="evidence:a",
        phrase_match_offset=0,
        production_error_code=None,
        production_diagnostics=None,
        overlay_id="temporal-overlay:x",
        comparison_metrics_present=False,
        comparison_metrics=None,
        provider_response_id="fake",
        lane_result="COMPARISON_METRICS_UNOBSERVED",
        run_mode="deterministic",
        phase="initial",
        repository_sha="unknown",
    )
    trace = broken.to_trace_dict()
    assert trace["comparison_metrics_present"] is False
    assert trace["comparison_metrics"] is None


def test_deterministic_mode_zero_live_delegate_calls(tmp_path: Path) -> None:
    live_spy = FakeTemporalShadowExtractionClient(_load_fake_output())

    class GuardClient(FakeTemporalShadowExtractionClient):
        def extract_annotations(self, *, instructions: str, user_content: str, model_id: str):
            raise AssertionError("live delegate must not be called in deterministic mode")

    result = grounding.run_paired_grounding_path_diagnostic(
        control_case_path=CONTROL_CASE,
        candidate_case_path=CANDIDATE_CASE,
        output_dir=tmp_path / "det",
        mode="deterministic",
        phase="initial",
        model_id="fake-model",
        fake_output=_load_fake_output(),
        repo_root=REPO_ROOT,
        overwrite=True,
    )
    assert result.provider_calls == 0
    _ = live_spy


def test_paired_live_workflow_spy_delegate_exactly_two_calls(tmp_path: Path) -> None:
    calls: list[str] = []

    class SpyClient(FakeTemporalShadowExtractionClient):
        def extract_annotations(self, *, instructions: str, user_content: str, model_id: str):
            calls.append(model_id)
            return super().extract_annotations(
                instructions=instructions,
                user_content=user_content,
                model_id=model_id,
            )

    ledger = grounding.ProviderCallLedger(phase="initial")
    client = SpyClient(_load_fake_output())
    grounding.run_lane_diagnostic(
        lane="control",
        case_path=CONTROL_CASE,
        output_dir=tmp_path / "live-control",
        mode="live",
        phase="initial",
        model_id=grounding.LIVE_MODEL_ID,
        client=client,
        repo_root=REPO_ROOT,
        ledger=ledger,
        overwrite=True,
    )
    grounding.run_lane_diagnostic(
        lane="candidate",
        case_path=CANDIDATE_CASE,
        output_dir=tmp_path / "live-candidate",
        mode="live",
        phase="initial",
        model_id=grounding.LIVE_MODEL_ID,
        client=client,
        repo_root=REPO_ROOT,
        ledger=ledger,
        overwrite=True,
    )
    assert len(calls) == 2
    assert ledger.calls == 2


def test_trace_artifacts_omit_forbidden_fields(tmp_path: Path) -> None:
    fake = _load_fake_output()
    out = tmp_path / "trace"
    grounding.run_paired_grounding_path_diagnostic(
        control_case_path=CONTROL_CASE,
        candidate_case_path=CANDIDATE_CASE,
        output_dir=out,
        mode="deterministic",
        phase="initial",
        model_id="fake-model",
        fake_output=fake,
        repo_root=REPO_ROOT,
        overwrite=True,
    )
    for name in ("paired-summary.json", "control-trace.json", "candidate-trace.json"):
        text = (out / name).read_text(encoding="utf-8")
        for forbidden in grounding.FORBIDDEN_TRACE_SUBSTRINGS:
            assert forbidden not in text


def test_smoke_fixture_not_discovered_by_holdout_or_adversarial_cutoff() -> None:
    examples = REPO_ROOT / "evals/graph_memory_layer/examples"
    holdout = _discover_cohorts_above_retired_cutoff(
        prefix="temporal_shadow_holdout_v",
        last_retired_version=LAST_RETIRED_HOLDOUT_VERSION,
        examples_root=examples,
    )
    adversarial = _discover_cohorts_above_retired_cutoff(
        prefix="temporal_shadow_adversarial_v",
        last_retired_version=LAST_RETIRED_ADVERSARIAL_VERSION,
        examples_root=examples,
    )
    discovered = {p.name for p in holdout + adversarial}
    assert "temporal_shadow_grounding_smoke_v1" not in discovered


def test_live_mode_fails_closed_without_opt_in() -> None:
    with patch.dict("os.environ", {}, clear=True):
        with pytest.raises(TemporalShadowExtractionError) as exc:
            grounding.run_paired_grounding_path_diagnostic(
                control_case_path=CONTROL_CASE,
                candidate_case_path=CANDIDATE_CASE,
                output_dir=REPO_ROOT / "out/test-live-guard",
                mode="live",
                phase="initial",
                model_id=grounding.LIVE_MODEL_ID,
                fake_output=None,
                repo_root=REPO_ROOT,
                overwrite=True,
            )
    assert "DMB_RUN_LIVE_TL01_GROUNDING_SMOKE" in str(exc.value)


def test_recording_wrapper_does_not_mutate_request_or_response() -> None:
    fake = _load_fake_output()
    delegate = FakeTemporalShadowExtractionClient(fake)
    recording = grounding.RecordingTemporalShadowClient(delegate)
    instructions = "system"
    user_content = '{"assertion_packets":[]}'
    before_batch = copy.deepcopy(fake)
    raw, meta = recording.extract_annotations(
        instructions=instructions,
        user_content=user_content,
        model_id="fake-model",
    )
    assert recording.last_instructions == instructions
    assert recording.last_user_content == user_content
    assert raw == before_batch
    assert meta.response_id == "fake-response"


def test_cli_deterministic_invocation(tmp_path: Path) -> None:
    out = tmp_path / "cli-out"
    proc = subprocess.run(
        [
            "uv",
            "run",
            "python",
            "evals/graph_memory_layer/temporal_shadow_grounding_path.py",
            "--control-case",
            str(CONTROL_CASE),
            "--candidate-case",
            str(CANDIDATE_CASE),
            "--fake-output",
            str(FAKE_OUTPUT_PATH),
            "--model-id",
            "gpt-5.4-mini",
            "--mode",
            "deterministic",
            "--phase",
            "initial",
            "--output-dir",
            str(out),
            "--overwrite",
        ],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    assert "control:   EVALUABLE" in proc.stdout
    assert "candidate: EVALUABLE" in proc.stdout
    assert "provider calls: 0" in proc.stdout
    assert "overall: UNRESOLVED_DIAGNOSTIC_GAP" in proc.stdout


def test_empty_evidence_refs_are_ownership_mismatch_not_validator_defect(
    tmp_path: Path,
) -> None:
    """Absent returned refs must not fall back to owned refs (§3 / §6.7)."""
    fake = copy.deepcopy(_load_fake_output())
    fake["annotations"][0]["evidence_ref_ids"] = []
    # Exact phrase still present — old fallback would mislabel as validator defect.
    assert EXPECTED_PHRASE in fake["annotations"][0]["source_phrase"]
    result = grounding.run_lane_diagnostic(
        lane="control",
        case_path=CONTROL_CASE,
        output_dir=tmp_path / "empty-refs",
        mode="deterministic",
        phase="initial",
        model_id="fake-model",
        client=FakeTemporalShadowExtractionClient(fake),
        repo_root=REPO_ROOT,
        overwrite=True,
    )
    assert result.lane_result == "EVIDENCE_OWNERSHIP_MISMATCH"
    assert result.returned_evidence_ref_ids == []
    assert result.owned_evidence_check == "foreign_or_missing"
    assert result.phrase_match is False


def test_empty_evidence_refs_with_paraphrase_still_ownership_mismatch(
    tmp_path: Path,
) -> None:
    fake = copy.deepcopy(_load_fake_output())
    fake["annotations"][0]["evidence_ref_ids"] = []
    fake["annotations"][0]["source_phrase"] = "paraphrased moth struck something"
    result = grounding.run_lane_diagnostic(
        lane="control",
        case_path=CONTROL_CASE,
        output_dir=tmp_path / "empty-paraphrase",
        mode="deterministic",
        phase="initial",
        model_id="fake-model",
        client=FakeTemporalShadowExtractionClient(fake),
        repo_root=REPO_ROOT,
        overwrite=True,
    )
    assert result.lane_result == "EVIDENCE_OWNERSHIP_MISMATCH"


def test_overall_conclusion_requires_both_deterministic_and_live_evaluable() -> None:
    # Bare enums must never unlock READY — only evidence-bound combiners can.
    assert (
        grounding.compute_overall_conclusion(
            live_control="EVALUABLE",
            live_candidate="EVALUABLE",
        )
        == "UNRESOLVED_DIAGNOSTIC_GAP"
    )
    assert (
        grounding.compute_overall_conclusion(
            deterministic_control="EVALUABLE",
            deterministic_candidate="EVALUABLE",
        )
        == "UNRESOLVED_DIAGNOSTIC_GAP"
    )
    assert (
        grounding.compute_overall_conclusion(
            deterministic_control="EVALUABLE",
            deterministic_candidate="EVALUABLE",
            live_control="EVALUABLE",
            live_candidate="EVALUABLE",
        )
        == "UNRESOLVED_DIAGNOSTIC_GAP"
    )


def test_overall_conclusion_provider_execution_is_unresolved_gap() -> None:
    assert (
        grounding.compute_overall_conclusion(
            deterministic_control="EVALUABLE",
            deterministic_candidate="EVALUABLE",
            live_control="EVALUABLE",
            live_candidate="PROVIDER_EXECUTION_FAILED",
        )
        == "UNRESOLVED_DIAGNOSTIC_GAP"
    )


def test_overall_conclusion_phrase_fidelity_requires_deterministic_proof() -> None:
    # Live-only phrase failure cannot claim PROVIDER_PHRASE_FIDELITY_BLOCKED.
    assert (
        grounding.compute_overall_conclusion(
            live_control="EVALUABLE",
            live_candidate="PROVIDER_PHRASE_FIDELITY_BLOCKED",
        )
        == "UNRESOLVED_DIAGNOSTIC_GAP"
    )
    # Both live phrase-fidelity failures, after deterministic EVALUABLE → blocked.
    assert (
        grounding.compute_overall_conclusion(
            deterministic_control="EVALUABLE",
            deterministic_candidate="EVALUABLE",
            live_control="PROVIDER_PHRASE_FIDELITY_BLOCKED",
            live_candidate="PROVIDER_PHRASE_FIDELITY_BLOCKED",
        )
        == "PROVIDER_PHRASE_FIDELITY_BLOCKED"
    )
    # One live phrase-fidelity failure is enough once deterministic proof exists.
    assert (
        grounding.compute_overall_conclusion(
            deterministic_control="EVALUABLE",
            deterministic_candidate="EVALUABLE",
            live_control="EVALUABLE",
            live_candidate="PROVIDER_PHRASE_FIDELITY_BLOCKED",
        )
        == "PROVIDER_PHRASE_FIDELITY_BLOCKED"
    )


def _minimal_lane(
    *,
    lane: str,
    run_mode: str,
    prompt_version: str,
    case_digest: str,
    repository_sha: str,
    model_id: str,
    provider_response_id: str | None,
    lane_result: str = "EVALUABLE",
    assertion_id: str = "assertion:shared",
    evidence_ref_ids: list[str] | None = None,
    expected_phrase: str = EXPECTED_PHRASE,
    resolved_span_digest: str = "spandigest",
    prompt_sha256: str | None = None,
) -> grounding.LaneDiagnostic:
    owned = evidence_ref_ids or ["evidence:shared"]
    if prompt_sha256 is None:
        if prompt_version == grounding.FROZEN_CONTROL_PROMPT_VERSION:
            prompt_sha256 = grounding.FROZEN_CONTROL_PROMPT_SHA256
        elif prompt_version == grounding.FROZEN_CANDIDATE_PROMPT_VERSION:
            prompt_sha256 = grounding.FROZEN_CANDIDATE_PROMPT_SHA256
        else:
            prompt_sha256 = "deadbeef"
    return grounding.LaneDiagnostic(
        lane=lane,  # type: ignore[arg-type]
        case_id=f"case-{lane}",
        case_digest=case_digest,
        prompt_version=prompt_version,
        prompt_sha256=prompt_sha256,
        packet_version=TL01C_PACKET_VERSION,
        renderer_identity=grounding.RENDERER_IDENTITY,
        model_id=model_id,
        assertion_id=assertion_id,
        evidence_ref_ids=owned,
        resolved_span_digest=resolved_span_digest,
        expected_phrase=expected_phrase,
        packet_phrase_present=True,
        renderer_phrase_present=True,
        transport_accepted=True,
        returned_evidence_ref_ids=list(owned),
        returned_source_phrase=expected_phrase,
        owned_evidence_check="owned_match",
        phrase_match=True,
        phrase_match_evidence_ref_id=owned[0],
        phrase_match_offset=0,
        production_error_code=None,
        production_diagnostics=None,
        overlay_id="temporal-overlay:x",
        comparison_metrics_present=True,
        comparison_metrics={"exact_match_count": 1},
        provider_response_id=provider_response_id,
        lane_result=lane_result,  # type: ignore[arg-type]
        run_mode=run_mode,  # type: ignore[arg-type]
        phase="initial",
        repository_sha=repository_sha,
    )


def test_combine_paired_ready_requires_shared_identity_and_live_provenance() -> None:
    clean_sha = "a" * 40
    det = grounding.PairedDiagnosticResult(
        control=_minimal_lane(
            lane="control",
            run_mode="deterministic",
            prompt_version=grounding.FROZEN_CONTROL_PROMPT_VERSION,
            case_digest="digest-control",
            repository_sha=clean_sha,
            model_id="fake-model",
            provider_response_id="fake",
        ),
        candidate=_minimal_lane(
            lane="candidate",
            run_mode="deterministic",
            prompt_version=grounding.FROZEN_CANDIDATE_PROMPT_VERSION,
            case_digest="digest-candidate",
            repository_sha=clean_sha,
            model_id="fake-model",
            provider_response_id="fake",
        ),
        provider_calls=0,
        overall_conclusion="UNRESOLVED_DIAGNOSTIC_GAP",
        live_attempted=False,
    )
    live = grounding.PairedDiagnosticResult(
        control=_minimal_lane(
            lane="control",
            run_mode="live",
            prompt_version=grounding.FROZEN_CONTROL_PROMPT_VERSION,
            case_digest="digest-control",
            repository_sha=clean_sha,
            model_id=grounding.LIVE_MODEL_ID,
            provider_response_id="resp_control",
        ),
        candidate=_minimal_lane(
            lane="candidate",
            run_mode="live",
            prompt_version=grounding.FROZEN_CANDIDATE_PROMPT_VERSION,
            case_digest="digest-candidate",
            repository_sha=clean_sha,
            model_id=grounding.LIVE_MODEL_ID,
            provider_response_id="resp_candidate",
        ),
        provider_calls=2,
        overall_conclusion="UNRESOLVED_DIAGNOSTIC_GAP",
        live_attempted=True,
    )
    assert (
        grounding.combine_paired_diagnostic_conclusions(
            deterministic=det, live=live
        )
        == "GROUNDING_PATH_READY"
    )

    broken = grounding.PairedDiagnosticResult(
        control=live.control,
        candidate=_minimal_lane(
            lane="candidate",
            run_mode="live",
            prompt_version=grounding.FROZEN_CANDIDATE_PROMPT_VERSION,
            case_digest="digest-candidate",
            repository_sha=clean_sha,
            model_id=grounding.LIVE_MODEL_ID,
            provider_response_id="resp_candidate",
            assertion_id="assertion:other",
        ),
        provider_calls=2,
        overall_conclusion="UNRESOLVED_DIAGNOSTIC_GAP",
        live_attempted=True,
    )
    assert (
        grounding.combine_paired_diagnostic_conclusions(
            deterministic=det, live=broken
        )
        == "UNRESOLVED_DIAGNOSTIC_GAP"
    )


def test_combine_rejects_unfrozen_prompt_hash_even_when_versions_match() -> None:
    clean_sha = "b" * 40
    det = grounding.PairedDiagnosticResult(
        control=_minimal_lane(
            lane="control",
            run_mode="deterministic",
            prompt_version=grounding.FROZEN_CONTROL_PROMPT_VERSION,
            case_digest="digest-control",
            repository_sha=clean_sha,
            model_id="fake-model",
            provider_response_id="fake",
            prompt_sha256="deadbeef" * 8,
        ),
        candidate=_minimal_lane(
            lane="candidate",
            run_mode="deterministic",
            prompt_version=grounding.FROZEN_CANDIDATE_PROMPT_VERSION,
            case_digest="digest-candidate",
            repository_sha=clean_sha,
            model_id="fake-model",
            provider_response_id="fake",
        ),
        provider_calls=0,
        overall_conclusion="UNRESOLVED_DIAGNOSTIC_GAP",
        live_attempted=False,
    )
    live = grounding.PairedDiagnosticResult(
        control=_minimal_lane(
            lane="control",
            run_mode="live",
            prompt_version=grounding.FROZEN_CONTROL_PROMPT_VERSION,
            case_digest="digest-control",
            repository_sha=clean_sha,
            model_id=grounding.LIVE_MODEL_ID,
            provider_response_id="resp_control",
            prompt_sha256="deadbeef" * 8,
        ),
        candidate=_minimal_lane(
            lane="candidate",
            run_mode="live",
            prompt_version=grounding.FROZEN_CANDIDATE_PROMPT_VERSION,
            case_digest="digest-candidate",
            repository_sha=clean_sha,
            model_id=grounding.LIVE_MODEL_ID,
            provider_response_id="resp_candidate",
        ),
        provider_calls=2,
        overall_conclusion="UNRESOLVED_DIAGNOSTIC_GAP",
        live_attempted=True,
    )
    assert (
        grounding.combine_paired_diagnostic_conclusions(
            deterministic=det, live=live
        )
        == "UNRESOLVED_DIAGNOSTIC_GAP"
    )


def test_combine_rejects_mismatched_implementation_sha() -> None:
    det = grounding.PairedDiagnosticResult(
        control=_minimal_lane(
            lane="control",
            run_mode="deterministic",
            prompt_version=grounding.FROZEN_CONTROL_PROMPT_VERSION,
            case_digest="digest-control",
            repository_sha="c" * 40,
            model_id="fake-model",
            provider_response_id="fake",
        ),
        candidate=_minimal_lane(
            lane="candidate",
            run_mode="deterministic",
            prompt_version=grounding.FROZEN_CANDIDATE_PROMPT_VERSION,
            case_digest="digest-candidate",
            repository_sha="c" * 40,
            model_id="fake-model",
            provider_response_id="fake",
        ),
        provider_calls=0,
        overall_conclusion="UNRESOLVED_DIAGNOSTIC_GAP",
        live_attempted=False,
    )
    live = grounding.PairedDiagnosticResult(
        control=_minimal_lane(
            lane="control",
            run_mode="live",
            prompt_version=grounding.FROZEN_CONTROL_PROMPT_VERSION,
            case_digest="digest-control",
            repository_sha="d" * 40,
            model_id=grounding.LIVE_MODEL_ID,
            provider_response_id="resp_control",
        ),
        candidate=_minimal_lane(
            lane="candidate",
            run_mode="live",
            prompt_version=grounding.FROZEN_CANDIDATE_PROMPT_VERSION,
            case_digest="digest-candidate",
            repository_sha="d" * 40,
            model_id=grounding.LIVE_MODEL_ID,
            provider_response_id="resp_candidate",
        ),
        provider_calls=2,
        overall_conclusion="UNRESOLVED_DIAGNOSTIC_GAP",
        live_attempted=True,
    )
    assert (
        grounding.combine_paired_diagnostic_conclusions(
            deterministic=det, live=live
        )
        == "UNRESOLVED_DIAGNOSTIC_GAP"
    )


def test_combine_rejects_evaluable_with_contradictory_failure_fields() -> None:
    clean_sha = "e" * 40
    bad_control = _minimal_lane(
        lane="control",
        run_mode="deterministic",
        prompt_version=grounding.FROZEN_CONTROL_PROMPT_VERSION,
        case_digest="digest-control",
        repository_sha=clean_sha,
        model_id="fake-model",
        provider_response_id="fake",
    )
    bad_control.transport_accepted = False
    bad_control.owned_evidence_check = "phrase_not_in_owned_snippet"
    bad_control.phrase_match = False
    bad_control.production_error_code = "grounding_failure"
    bad_control.overlay_id = None
    det = grounding.PairedDiagnosticResult(
        control=bad_control,
        candidate=_minimal_lane(
            lane="candidate",
            run_mode="deterministic",
            prompt_version=grounding.FROZEN_CANDIDATE_PROMPT_VERSION,
            case_digest="digest-candidate",
            repository_sha=clean_sha,
            model_id="fake-model",
            provider_response_id="fake",
        ),
        provider_calls=0,
        overall_conclusion="UNRESOLVED_DIAGNOSTIC_GAP",
        live_attempted=False,
    )
    live = grounding.PairedDiagnosticResult(
        control=_minimal_lane(
            lane="control",
            run_mode="live",
            prompt_version=grounding.FROZEN_CONTROL_PROMPT_VERSION,
            case_digest="digest-control",
            repository_sha=clean_sha,
            model_id=grounding.LIVE_MODEL_ID,
            provider_response_id="resp_control",
        ),
        candidate=_minimal_lane(
            lane="candidate",
            run_mode="live",
            prompt_version=grounding.FROZEN_CANDIDATE_PROMPT_VERSION,
            case_digest="digest-candidate",
            repository_sha=clean_sha,
            model_id=grounding.LIVE_MODEL_ID,
            provider_response_id="resp_candidate",
        ),
        provider_calls=2,
        overall_conclusion="UNRESOLVED_DIAGNOSTIC_GAP",
        live_attempted=True,
    )
    assert (
        grounding.combine_paired_diagnostic_conclusions(
            deterministic=det, live=live
        )
        == "UNRESOLVED_DIAGNOSTIC_GAP"
    )


def test_combine_paired_summary_rejects_literal_evaluable_without_identity() -> None:
    summary = {
        "run_mode": "deterministic",
        "provider_calls": 0,
        "control": {"lane_result": "EVALUABLE"},
        "candidate": {"lane_result": "EVALUABLE"},
    }
    live = {
        "run_mode": "live",
        "provider_calls": 2,
        "control": {"lane_result": "EVALUABLE"},
        "candidate": {"lane_result": "EVALUABLE"},
    }
    assert (
        grounding.combine_paired_summary_conclusions(
            deterministic_summary=summary,
            live_summary=live,
        )
        == "UNRESOLVED_DIAGNOSTIC_GAP"
    )


def test_combine_post_fix_summaries_at_shared_clean_sha() -> None:
    det_path = (
        REPO_ROOT
        / "out/evals/temporal_shadow_grounding_path/deterministic-post-fix/paired-summary.json"
    )
    live_path = (
        REPO_ROOT
        / "out/evals/temporal_shadow_grounding_path/live-post-fix/paired-summary.json"
    )
    if not det_path.is_file() or not live_path.is_file():
        pytest.skip("author-local post-fix paired summaries not present")
    det = json.loads(det_path.read_text(encoding="utf-8"))
    live = json.loads(live_path.read_text(encoding="utf-8"))
    assert (
        grounding.combine_paired_summary_conclusions(
            deterministic_summary=det,
            live_summary=live,
        )
        == "GROUNDING_PATH_READY"
    )


def test_failed_provider_attempts_are_charged_to_budget() -> None:
    class FailingDelegate:
        def extract_annotations(self, *, instructions: str, user_content: str, model_id: str):
            raise TemporalShadowExtractionError(
                "provider refused",
                code="provider_refusal",
                provider_response_id="resp_failed_attempt",
            )

    ledger = grounding.ProviderCallLedger(phase="initial")
    recording = grounding.RecordingTemporalShadowClient(
        FailingDelegate(),  # type: ignore[arg-type]
        ledger=ledger,
        record_provider_calls=True,
    )
    with pytest.raises(TemporalShadowExtractionError) as exc:
        recording.extract_annotations(
            instructions="x",
            user_content="y",
            model_id=grounding.LIVE_MODEL_ID,
        )
    assert exc.value.code == "provider_refusal"
    assert ledger.calls == 1
    assert ledger.response_ids == ["resp_failed_attempt"]
    assert recording.call_count == 1


def test_alternate_budget_ledger_path_rejected(tmp_path: Path) -> None:
    with patch.dict("os.environ", {grounding.LIVE_OPT_IN_ENV: "1"}):
        with pytest.raises(TemporalShadowExtractionError) as exc:
            grounding.run_paired_grounding_path_diagnostic(
                control_case_path=CONTROL_CASE,
                candidate_case_path=CANDIDATE_CASE,
                output_dir=tmp_path / "blocked-alt",
                mode="live",
                phase="post_fix",
                model_id=grounding.LIVE_MODEL_ID,
                fake_output=None,
                repo_root=REPO_ROOT,
                overwrite=True,
                budget_ledger_path=tmp_path / "fresh-zero.json",
            )
    assert "Alternate provider budget ledger path rejected" in str(exc.value)


def test_missing_budget_ledger_fails_closed(tmp_path: Path) -> None:
    missing = tmp_path / "missing-ledger.json"
    with pytest.raises(TemporalShadowExtractionError) as exc:
        grounding.load_provider_budget_ledger(missing)
    assert "missing" in str(exc.value).lower()


def test_budget_ledger_reconciles_total_against_entries(tmp_path: Path) -> None:
    path = tmp_path / "bad-ledger.json"
    path.write_text(
        json.dumps(
            {
                "schema": grounding.BUDGET_LEDGER_SCHEMA,
                "max_total_provider_calls": 4,
                "total_calls": 0,
                "response_ids": [],
                "entries": [
                    {
                        "phase": "initial",
                        "repository_sha": "a" * 40,
                        "calls": 2,
                        "response_ids": ["r1", "r2"],
                    }
                ],
            }
        )
        + "\n",
        encoding="utf-8",
    )
    with pytest.raises(TemporalShadowExtractionError) as exc:
        grounding.load_provider_budget_ledger(path)
    assert "reconcile" in str(exc.value).lower()


def test_budget_ledger_accepts_fewer_response_ids_than_calls(tmp_path: Path) -> None:
    path = tmp_path / "partial-ids-ledger.json"
    path.write_text(
        json.dumps(
            {
                "schema": grounding.BUDGET_LEDGER_SCHEMA,
                "max_total_provider_calls": 4,
                "total_calls": 2,
                "response_ids": ["r1"],
                "entries": [
                    {
                        "phase": "initial",
                        "repository_sha": "a" * 40,
                        "calls": 2,
                        "response_ids": ["r1"],
                    }
                ],
            }
        )
        + "\n",
        encoding="utf-8",
    )
    ledger = grounding.load_provider_budget_ledger(path)
    assert ledger.total_calls == 2
    assert ledger.response_ids == ["r1"]

    empty_ids_path = tmp_path / "empty-ids-ledger.json"
    empty_ids_path.write_text(
        json.dumps(
            {
                "schema": grounding.BUDGET_LEDGER_SCHEMA,
                "max_total_provider_calls": 4,
                "total_calls": 2,
                "response_ids": [],
                "entries": [
                    {
                        "phase": "initial",
                        "repository_sha": "a" * 40,
                        "calls": 2,
                        "response_ids": [],
                    }
                ],
            }
        )
        + "\n",
        encoding="utf-8",
    )
    empty_ledger = grounding.load_provider_budget_ledger(empty_ids_path)
    assert empty_ledger.total_calls == 2
    assert empty_ledger.response_ids == []


def test_budget_ledger_rejects_more_response_ids_than_calls(tmp_path: Path) -> None:
    path = tmp_path / "too-many-ids.json"
    path.write_text(
        json.dumps(
            {
                "schema": grounding.BUDGET_LEDGER_SCHEMA,
                "max_total_provider_calls": 4,
                "total_calls": 1,
                "response_ids": ["r1", "r2"],
                "entries": [
                    {
                        "phase": "initial",
                        "repository_sha": "a" * 40,
                        "calls": 1,
                        "response_ids": ["r1", "r2"],
                    }
                ],
            }
        )
        + "\n",
        encoding="utf-8",
    )
    with pytest.raises(TemporalShadowExtractionError) as exc:
        grounding.load_provider_budget_ledger(path)
    assert "more response_ids than calls" in str(exc.value).lower()


def test_record_provider_budget_entry_rejects_more_ids_than_calls(
    tmp_path: Path,
) -> None:
    path = tmp_path / "fresh-ledger.json"
    path.write_text(
        json.dumps(
            {
                "schema": grounding.BUDGET_LEDGER_SCHEMA,
                "max_total_provider_calls": 4,
                "total_calls": 0,
                "response_ids": [],
                "entries": [],
            }
        )
        + "\n",
        encoding="utf-8",
    )
    ledger = grounding.load_provider_budget_ledger(path)
    with pytest.raises(TemporalShadowExtractionError) as exc:
        grounding.record_provider_budget_entry(
            ledger,
            phase="initial",
            repository_sha="a" * 40,
            calls=1,
            response_ids=["r1", "r2"],
        )
    assert "more response_ids than calls" in str(exc.value).lower()


def test_persistent_ledger_survives_provider_failure_without_response_id(
    tmp_path: Path,
) -> None:
    ledger_path = tmp_path / "provider-budget-ledger.json"
    ledger_path.write_text(
        json.dumps(
            {
                "schema": grounding.BUDGET_LEDGER_SCHEMA,
                "max_total_provider_calls": 4,
                "total_calls": 0,
                "response_ids": [],
                "entries": [],
            }
        )
        + "\n",
        encoding="utf-8",
    )
    out = tmp_path / "live-out"

    class ProviderErrorNoResponseId:
        def extract_annotations(
            self, *, instructions: str, user_content: str, model_id: str
        ):
            raise TemporalShadowExtractionError(
                "simulated network failure",
                code="provider_error",
            )

    with patch.dict("os.environ", {grounding.LIVE_OPT_IN_ENV: "1"}):
        with (
            patch.object(
                grounding,
                "canonical_budget_ledger_path",
                return_value=ledger_path,
            ),
            patch.object(
                grounding,
                "OpenAITemporalShadowExtractionClient",
                return_value=ProviderErrorNoResponseId(),
            ),
        ):
            result = grounding.run_paired_grounding_path_diagnostic(
                control_case_path=CONTROL_CASE,
                candidate_case_path=CANDIDATE_CASE,
                output_dir=out,
                mode="live",
                phase="initial",
                model_id=grounding.LIVE_MODEL_ID,
                fake_output=None,
                repo_root=REPO_ROOT,
                overwrite=True,
            )

    assert result.control.lane_result == "PROVIDER_EXECUTION_FAILED"
    assert result.candidate.lane_result == "PROVIDER_EXECUTION_FAILED"
    assert result.provider_calls == 2
    assert result.overall_conclusion == "UNRESOLVED_DIAGNOSTIC_GAP"

    summary_path = out / "paired-summary.json"
    assert summary_path.is_file()
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assert summary["budget_total_calls"] == 2
    assert summary["budget_remaining"] == 2
    assert summary["provider_response_ids"] == []

    assert (out / "control-trace.json").is_file()
    assert (out / "candidate-trace.json").is_file()

    reloaded = grounding.load_provider_budget_ledger(ledger_path)
    assert reloaded.total_calls == 2
    assert len(reloaded.response_ids) <= reloaded.total_calls
    assert reloaded.response_ids == []


def test_persistent_budget_ledger_blocks_fifth_live_invocation(tmp_path: Path) -> None:
    with patch.dict("os.environ", {grounding.LIVE_OPT_IN_ENV: "1"}):
        with pytest.raises(TemporalShadowExtractionError) as exc:
            grounding.run_paired_grounding_path_diagnostic(
                control_case_path=CONTROL_CASE,
                candidate_case_path=CANDIDATE_CASE,
                output_dir=tmp_path / "blocked",
                mode="live",
                phase="post_fix",
                model_id=grounding.LIVE_MODEL_ID,
                fake_output=None,
                repo_root=REPO_ROOT,
                overwrite=True,
                budget_ledger_path=grounding.canonical_budget_ledger_path(REPO_ROOT),
            )
    assert "budget" in str(exc.value).lower() or "exhausted" in str(exc.value).lower()


def test_fixture_budget_ledger_is_exhausted_at_four() -> None:
    ledger_path = grounding.canonical_budget_ledger_path(REPO_ROOT)
    ledger = grounding.load_provider_budget_ledger(ledger_path)
    assert ledger.total_calls == 4
    assert ledger.remaining == 0
    with pytest.raises(TemporalShadowExtractionError):
        grounding.assert_provider_budget_available(ledger, calls_needed=1)


def test_resolve_live_budget_defaults_to_canonical() -> None:
    canonical = grounding.canonical_budget_ledger_path(REPO_ROOT)
    assert (
        grounding.resolve_live_budget_ledger_path(
            repo_root=REPO_ROOT, requested=None
        )
        == canonical
    )
    assert (
        grounding.resolve_live_budget_ledger_path(
            repo_root=REPO_ROOT, requested=canonical
        )
        == canonical
    )


def test_transport_accepted_false_for_invalid_model_output_and_provider_errors() -> None:
    invalid = TemporalShadowExtractionError(
        "bad transport",
        code="invalid_model_output",
    )
    assert (
        grounding.transport_accepted_for_error(
            invalid, succeeded=False, raw_batch={"annotations": []}
        )
        is False
    )
    provider = TemporalShadowExtractionError(
        "network",
        code="provider_error",
    )
    assert (
        grounding.transport_accepted_for_error(
            provider, succeeded=False, raw_batch=None
        )
        is False
    )
    grounding_err = TemporalShadowExtractionError(
        "phrase miss",
        code="grounding_failure",
    )
    assert (
        grounding.transport_accepted_for_error(
            grounding_err,
            succeeded=False,
            raw_batch={"annotations": []},
        )
        is True
    )


def test_transport_rejected_lane_records_transport_accepted_false(
    tmp_path: Path,
) -> None:
    fake = copy.deepcopy(_load_fake_output())
    fake["annotations"][0]["interpretation_status"] = "not_a_status"
    result = grounding.run_lane_diagnostic(
        lane="control",
        case_path=CONTROL_CASE,
        output_dir=tmp_path / "transport",
        mode="deterministic",
        phase="initial",
        model_id="fake-model",
        client=FakeTemporalShadowExtractionClient(fake),
        repo_root=REPO_ROOT,
        overwrite=True,
    )
    assert result.lane_result == "TRANSPORT_REJECTED"
    assert result.transport_accepted is False


@pytest.mark.parametrize(
    "mutator",
    [
        lambda batch: batch.update({"annotations": "not-a-list"}),
        lambda batch: batch.update({"annotations": ["not-an-object"]}),
        lambda batch: batch["annotations"][0].update({"evidence_ref_ids": 7}),
    ],
)
def test_malformed_raw_batch_observation_yields_transport_rejected(
    tmp_path: Path,
    mutator: Any,
) -> None:
    fake = copy.deepcopy(_load_fake_output())
    mutator(fake)
    result = grounding.run_lane_diagnostic(
        lane="control",
        case_path=CONTROL_CASE,
        output_dir=tmp_path / "malformed",
        mode="deterministic",
        phase="initial",
        model_id="fake-model",
        client=FakeTemporalShadowExtractionClient(fake),
        repo_root=REPO_ROOT,
        overwrite=True,
    )
    assert result.lane_result == "TRANSPORT_REJECTED"
    assert result.transport_accepted is False


def test_annotation_from_raw_batch_shape_guards() -> None:
    assertion_id = "assertion:x"
    phrase, refs, ok = grounding._annotation_from_raw_batch(
        {"annotations": [{"base_assertion_id": assertion_id, "evidence_ref_ids": 7}]},
        assertion_id=assertion_id,
    )
    assert ok is False
    assert phrase is None and refs is None
    phrase, refs, ok = grounding._annotation_from_raw_batch(
        {"annotations": "nope"},
        assertion_id=assertion_id,
    )
    assert ok is False
    phrase, refs, ok = grounding._annotation_from_raw_batch(
        {"annotations": [42]},
        assertion_id=assertion_id,
    )
    assert ok is False


def test_deterministic_paired_overall_is_not_grounding_path_ready(tmp_path: Path) -> None:
    result = grounding.run_paired_grounding_path_diagnostic(
        control_case_path=CONTROL_CASE,
        candidate_case_path=CANDIDATE_CASE,
        output_dir=tmp_path / "det-overall",
        mode="deterministic",
        phase="initial",
        model_id="fake-model",
        fake_output=_load_fake_output(),
        repo_root=REPO_ROOT,
        overwrite=True,
    )
    assert result.control.lane_result == "EVALUABLE"
    assert result.candidate.lane_result == "EVALUABLE"
    assert result.overall_conclusion == "UNRESOLVED_DIAGNOSTIC_GAP"
