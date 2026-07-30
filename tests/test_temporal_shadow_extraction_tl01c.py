"""TL01C registry, packet V2, and cohort separation tests."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from graph_memory.temporal_shadow_extraction import (
    FakeTemporalShadowExtractionClient,
    TL01B_BASELINE_INSTRUCTIONS,
    TL01B_PACKET_VERSION,
    TL01C_PACKET_VERSION,
    TL01C_SOURCE_AWARE_INSTRUCTIONS,
    baseline_prompt_fingerprint,
    build_assertion_evidence_packets,
    load_temporal_shadow_extraction_case,
    resolve_prompt_spec,
    run_temporal_shadow_extraction,
)
from graph_memory.temporal_shadow_extraction_schema import TEMPORAL_SHADOW_PROMPT_VERSION

REPO_ROOT = Path(__file__).resolve().parents[1]
DEV_CASE = (
    REPO_ROOT
    / "evals/graph_memory_layer/examples/temporal_shadow_cohort/temporal-case.json"
)
DEV_TL01C_CASE = (
    REPO_ROOT
    / "evals/graph_memory_layer/examples/temporal_shadow_cohort/temporal-case-tl01c.json"
)
HOLDOUT_CASE = (
    REPO_ROOT
    / "evals/graph_memory_layer/examples/temporal_shadow_holdout/temporal-case.json"
)

FORBIDDEN_SYNTHETIC_TERMS = (
    "Stafl",
    "Caelynn",
    "Lysandra",
    "Maelthor",
    "Hybrid",
    "Copper and Quartz",
)


def _load_contribution(case_path: Path):
    case = load_temporal_shadow_extraction_case(case_path, repo_root=REPO_ROOT)
    from graph_memory.kernel.contribution_models import GraphContribution

    base_path = REPO_ROOT / case.base_contribution_path
    return case, GraphContribution.model_validate(
        json.loads(base_path.read_text(encoding="utf-8"))
    )


def test_baseline_instructions_fingerprint_stable() -> None:
    fingerprint = baseline_prompt_fingerprint()
    expected = hashlib.sha256(TL01B_BASELINE_INSTRUCTIONS.encode("utf-8")).hexdigest()
    assert fingerprint["prompt_version"] == TEMPORAL_SHADOW_PROMPT_VERSION
    assert fingerprint["instructions_sha256"] == expected
    assert fingerprint["packet_version"] == TL01B_PACKET_VERSION


def test_v1_packet_lacks_source_context_v2_includes_provenance_only() -> None:
    case, contribution = _load_contribution(DEV_TL01C_CASE)
    v1_packets = build_assertion_evidence_packets(
        contribution,
        case,
        repo_root=REPO_ROOT,
        packet_version=TL01B_PACKET_VERSION,
    )
    v2_packets = build_assertion_evidence_packets(
        contribution,
        case,
        repo_root=REPO_ROOT,
        packet_version=TL01C_PACKET_VERSION,
    )
    assertion_id = case.selected_assertion_ids[0]
    assert "source_context" not in v1_packets[assertion_id]
    source_context = v2_packets[assertion_id]["source_context"]
    assert source_context["semantic_authority"] == "provenance_only"
    assert "derivation" in source_context
    assert "source_time" in source_context


def test_unknown_prompt_version_fails_before_provider(tmp_path: Path) -> None:
    case_payload = json.loads(DEV_CASE.read_text(encoding="utf-8"))
    case_payload["prompt_version"] = "tl01z-v9"
    bad_case = tmp_path / "bad-case.json"
    bad_case.write_text(json.dumps(case_payload), encoding="utf-8")

    class ExplodingClient(FakeTemporalShadowExtractionClient):
        def extract_annotations(self, **kwargs):  # type: ignore[no-untyped-def]
            raise AssertionError("provider must not be called")

    with pytest.raises(Exception) as exc:
        run_temporal_shadow_extraction(
            bad_case,
            tmp_path / "run",
            client=ExplodingClient({"schema": "dmb_temporal_model_annotation_batch_v1", "annotations": []}),
            model_id="fake-model",
            repo_root=REPO_ROOT,
        )
    assert "unsupported_prompt_version" in str(exc.value) or getattr(exc.value, "code", "") == "unsupported_prompt_version"


def test_tl01c_instructions_contain_required_distinction_phrases() -> None:
    text = TL01C_SOURCE_AWARE_INSTRUCTIONS
    required_groups = [
        ("occurrence", "valid_time"),
        ("provenance_only",),
        ("not_applicable",),
        ("ambiguous",),
    ]
    for group in required_groups:
        assert all(term in text for term in group)
    assert "re-attestation" in text or "again travels" in text
    assert "password" in text or "Veyra" in text
    assert "three winters" in text


def test_tl01c_synthetic_examples_exclude_sealed_cohort_terms() -> None:
    text = TL01C_SOURCE_AWARE_INSTRUCTIONS
    for term in FORBIDDEN_SYNTHETIC_TERMS:
        assert term not in text


def test_development_and_holdout_assertion_ids_do_not_overlap() -> None:
    dev = load_temporal_shadow_extraction_case(DEV_CASE, repo_root=REPO_ROOT)
    holdout = load_temporal_shadow_extraction_case(HOLDOUT_CASE, repo_root=REPO_ROOT)
    dev_ids = set(dev.selected_assertion_ids)
    holdout_ids = set(holdout.selected_assertion_ids)
    assert dev_ids.isdisjoint(holdout_ids)


def test_development_and_holdout_evidence_ids_do_not_overlap() -> None:
    dev = load_temporal_shadow_extraction_case(DEV_CASE, repo_root=REPO_ROOT)
    holdout = load_temporal_shadow_extraction_case(HOLDOUT_CASE, repo_root=REPO_ROOT)
    dev_evidence = {entry.evidence_ref_id for entry in dev.evidence_registry}
    holdout_evidence = {entry.evidence_ref_id for entry in holdout.evidence_registry}
    assert dev_evidence.isdisjoint(holdout_evidence)


def test_resolve_prompt_spec_tl01c_packet_version() -> None:
    spec = resolve_prompt_spec("tl01c-v1")
    assert spec.version == "tl01c-v1"
    assert spec.packet_version == TL01C_PACKET_VERSION
