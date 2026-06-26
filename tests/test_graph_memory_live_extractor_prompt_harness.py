from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from evals.graph_memory_layer import live_extractor_prompt_harness as h
from evals.graph_memory_layer.live_vs_gold_compare import compare_live_to_gold
from evals.graph_memory_layer.reconcile_live_candidate import ENVELOPE_SCHEMA, validate_live_candidate_output


def _semantic_state() -> dict[str, str]:
    return {
        "canon_state": "candidate_extraction",
        "lifecycle_state": "candidate",
        "evidence_role": "source_evidence",
        "authority_state": "system_derived",
        "visibility_state": "gm_private",
    }


def _diagnostics() -> dict[str, object]:
    return {
        "preview_only": True,
        "extraction_performed": False,
        "llm_used": False,
        "runtime_connected": False,
        "plan_connected": False,
        "agent_interaction_connected": False,
        "corpus_scanned": False,
        "corpus_mutated": False,
        "facts_promoted": False,
        "canon_promoted": False,
        "unresolved_evidence_refs": 0,
        "missing_evidence_objects": 0,
        "warning_count": 0,
    }


def _minimal_envelope(spref: str = "spref:session-23:p001") -> dict:
    ev = [{"source_span_ref_id": spref}]
    return {
        "schema": ENVELOPE_SCHEMA,
        "version": "0.1",
        "candidate_graph": {
            "schema": "dmb_candidate_graph_preview_v0",
            "version": "0.1",
            "preview_id": "candidate-preview:test",
            "campaign_id": "longmont-c2",
            "session_id": "session-23",
            "source_artifact_ids": ["source-artifact:session-23-normalized-recap"],
            "status": "preview",
            "nodes": [
                {
                    "node_id": "node:test-party",
                    "label": "Test party",
                    "node_type": "group",
                    "description": "Test group node.",
                    "importance": "medium",
                    "semantic_state": _semantic_state(),
                    "evidence_refs": ev,
                    "proposed_action": "create",
                    "confidence": "medium",
                }
            ],
            "edges": [],
            "beats": [
                {
                    "beat_id": "beat:test-1",
                    "order": 1,
                    "title": "Test beat",
                    "summary": "Test summary.",
                    "involved_node_ids": ["node:test-party"],
                    "evidence_refs": ev,
                    "proposed_action": "create",
                }
            ],
            "proposed_writes": [],
            "ignored_items": [],
            "deferred_items": [],
            "diagnostics": _diagnostics(),
        },
        "review_sidecar": {"high_risk_claims": [], "notes": []},
    }


def test_prompt_manifest_validates():
    h.validate_prompt_manifest(h.load_manifest())
    h.validate_prompt_packet_manifest(h.load_sample_packet_manifest())


def test_one_two_three_shot_render_deterministically():
    v = h.verify_run_bundle_and_source(Path(h.SESSION_23_RUN_BUNDLE), Path(h.SESSION_23_SOURCE_RECAP))
    one = h.render_prompts("one_shot", v)
    two = h.render_prompts("two_shot", v)
    three = h.render_prompts("three_shot", v)
    assert one == h.render_prompts("one_shot", v)
    assert two == h.render_prompts("two_shot", v)
    assert three == h.render_prompts("three_shot", v)
    joined = "\n".join([*one.values(), *two.values(), *three.values()])
    for needle in [
        "source_span_ref_id",
        "Do not resolve cliffhangers",
        "Named-in-span-A",
        "review_sidecar",
        "dmb_candidate_graph_preview_v0",
        "Forbidden: approve memory",
        "relationship_type",
        "observation_edges",
        "Assembly Pass",
    ]:
        assert needle in joined


def test_source_recap_identity_rejections(tmp_path):
    source = Path(h.SESSION_23_SOURCE_RECAP)
    bad = tmp_path / "bad.md"
    bad.write_text(source.read_text().replace("Mireward", "MirewardX", 1))
    with pytest.raises(h.HarnessValidationError, match="source_recap_sha256_mismatch"):
        h.verify_run_bundle_and_source(Path(h.SESSION_23_RUN_BUNDLE), bad)
    short = tmp_path / "short.md"
    short.write_text("\n".join(source.read_text().splitlines()[:-1]))
    with pytest.raises(h.HarnessValidationError, match="source_recap_sha256_mismatch|source_recap_line_count_mismatch"):
        h.verify_run_bundle_and_source(Path(h.SESSION_23_RUN_BUNDLE), short)
    with pytest.raises(h.HarnessValidationError, match="source_recap_missing"):
        h.validate_source_recap_path(tmp_path / "missing.md")
    d = tmp_path / "dir"
    d.mkdir()
    with pytest.raises(h.HarnessValidationError, match="source_recap_is_directory"):
        h.validate_source_recap_path(d)
    with pytest.raises(h.HarnessValidationError, match="source_recap_is_glob"):
        h.validate_source_recap_path(Path("*.md"))


def test_output_guards_and_cli_render(tmp_path):
    root = h.repo_root()
    with pytest.raises(h.HarnessValidationError, match="output_outside_allowed_run_dir"):
        h.validate_output_path(tmp_path / "out")
    with pytest.raises(h.HarnessValidationError, match="output_outside_allowed_run_dir"):
        h.validate_output_path(Path(h.RUNS_DIR), allow_overwrite=True)
    out = Path(h.RUNS_DIR) / "pytest_one_shot"
    res = subprocess.run(
        [
            sys.executable,
            "-m",
            "evals.graph_memory_layer.render_live_extractor_prompt_harness",
            "--mode",
            "one_shot",
            "--run-bundle",
            h.SESSION_23_RUN_BUNDLE,
            "--source-recap",
            h.SESSION_23_SOURCE_RECAP,
            "--out",
            str(out),
            "--allow-overwrite",
        ],
        cwd=root,
        text=True,
        capture_output=True,
        check=True,
    )
    assert res.returncode == 0
    target = root / out
    assert (target / "prompt_packet_manifest.json").exists()
    assert (target / "source_packet_summary.json").exists()
    prompt = (target / "one_shot_prompt.md").read_text()
    assert "spref:session-23:p001" in prompt and "dmb_live_extractor_candidate_envelope_v0" in prompt


def test_candidate_output_validator_rejects_promoted_output():
    envelope = _minimal_envelope()
    envelope["candidate_graph"]["proposed_writes"] = [
        {
            "write_id": "write:test",
            "write_type": "create_node",
            "target_id": "node:test-party",
            "label": "bad",
            "reason": "approved_memory",
            "evidence_refs": [{"source_span_ref_id": "spref:session-23:p001"}],
            "status": "pending",
        }
    ]
    with pytest.raises(h.HarnessValidationError, match="forbidden_candidate_output"):
        h.validate_candidate_output(envelope, {"spref:session-23:p001"})


def test_candidate_output_validator_requires_evidence_refs():
    allowed = {"spref:session-23:p001"}
    envelope = _minimal_envelope()
    envelope["candidate_graph"]["nodes"][0]["evidence_refs"] = []
    with pytest.raises(h.HarnessValidationError, match="canonical_ir_issues|missing_evidence"):
        h.validate_candidate_output(envelope, allowed)


def test_candidate_output_validator_rejects_unknown_evidence_refs():
    envelope = _minimal_envelope("spref:session-23:missing")
    with pytest.raises(h.HarnessValidationError, match="unknown_source_span_ref"):
        h.validate_candidate_output(envelope, {"spref:session-23:p001"})


def test_candidate_output_validator_accepts_canonical_envelope():
    envelope = _minimal_envelope()
    report = h.validate_candidate_output(envelope, {"spref:session-23:p001"})
    assert report["canonical_ir_valid"]
    assert report["evidence_ref_count"] >= 2


def test_reconcile_and_live_vs_gold_on_gold_subset():
    envelope = _minimal_envelope()
    report = validate_live_candidate_output(
        envelope,
        run_bundle=Path(h.SESSION_23_RUN_BUNDLE),
        allowed_span_refs={"spref:session-23:p001"},
    )
    comparison = compare_live_to_gold(report["reconciled_candidate_graph"])
    assert comparison["comparison_mode"] == "live_fuzzy_vs_gold"
    assert "node_recall" in comparison["scores"]


def test_validation_and_report_clis():
    root = h.repo_root()
    for mod in [
        "evals.graph_memory_layer.validate_live_extractor_prompt_harness",
        "evals.graph_memory_layer.report_live_extractor_prompt_harness",
    ]:
        res = subprocess.run([sys.executable, "-m", mod], cwd=root, text=True, capture_output=True, check=True)
        assert res.returncode == 0
