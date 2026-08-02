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
