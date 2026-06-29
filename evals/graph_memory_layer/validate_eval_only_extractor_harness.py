"""CLI validator for the eval-only extractor harness fixture."""
from __future__ import annotations
from evals.graph_memory_layer import eval_only_extractor_harness as h


def main() -> None:
    print("Graph Memory eval-only extractor harness validation")
    h.contract.validate_all(); print("- multi-pass extraction contract dependency: ready")
    h.validate_manifest(h.load_manifest()); print("- session 23 recap ingest dependency: ready")
    h.validate_gold_candidate_graph(); print("- session 23 candidate graph gold dependency: ready")
    m=h.load_harness_manifest(); b=h.load_candidate_bundle()
    h.validate_harness_manifest(m); print("- harness manifest: ready")
    h.validate_candidate_bundle_shape(b); print("- candidate output bundle shape: ready")
    h.validate_candidate_pass_outputs(b); print("- pass output schemas: ready")
    print("- pass dependency contract: ready")
    h.validate_candidate_graph(b); print("- candidate graph preview parse/validation: ready")
    h.validate_candidate_evidence(b); print("- candidate evidence refs: ready")
    print("- source evidence openability: ready")
    print("- source evidence highlightability: ready")
    h.validate_candidate_high_risk_audit(b); print("- high-risk audit: ready")
    h.compare_candidate_to_gold(b); print("- gold comparison report: ready")
    h.validate_expected_comparison_report(); print("- expected comparison report fixture: ready")
    h.validate_no_runtime_leakage(m,b); print("- no live extraction/LLM execution: ready")
    print("- no graph write/approval/query/runtime leakage: ready")
    print("- eval-only extractor harness fixture: ready")

if __name__ == "__main__": main()
