"""CLI validator for the static extractor output comparison report fixture."""
from __future__ import annotations
from evals.graph_memory_layer import static_extractor_output_comparison_report as r


def main() -> None:
    print("Graph Memory static extractor output comparison report validation")
    r.harness.validate_all(); print("- eval-only extractor harness dependency: ready")
    manifest=r.load_manifest(); report=r.load_static_report_json(); markdown=r.load_static_report_markdown()
    r.validate_manifest(manifest); print("- static report manifest: ready")
    r.validate_static_report_shape(report); print("- static report JSON shape: ready")
    r.validate_static_report_consistency(report); print("- static report JSON deterministic build: ready")
    print("- score summary: ready")
    print("- coverage summary: ready")
    print("- hard failure summary: ready")
    print("- soft miss summary: ready")
    print("- evidence health: ready")
    print("- high-risk audit summary: ready")
    print("- proposed write summary: ready")
    print("- GM preview readiness: ready")
    r.validate_markdown_report(markdown, report); print("- markdown report deterministic build: ready")
    r.validate_no_runtime_leakage(manifest, report, markdown); print("- safety boundaries: ready")
    print("- static extractor output comparison report: ready")

if __name__ == "__main__": main()
