from __future__ import annotations

import sys

from evals.graph_memory_layer.validate_source_span_resolver_fixture import build_registries, load_fixture
from src.graph_memory.source_span import analyze_evidence_resolution, resolve_many_source_span_refs


def _cell(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\n", "<br>")


def main() -> int:
    fixture = load_fixture()
    text_artifacts, structured_artifacts, refs = build_registries(fixture)
    resolved = resolve_many_source_span_refs(refs, text_artifacts=text_artifacts, structured_artifacts=structured_artifacts)
    report = analyze_evidence_resolution(refs, resolved)
    print("# Source Span Evidence Resolver Report\n")
    print("## Summary\n")
    print("| Metric | Count |\n|---|---:|")
    rows = [("Source span refs", report.total_refs), ("Resolved refs", report.resolved_refs), ("Unresolved refs", report.unresolved_refs), ("Highlightable refs", report.highlightable_refs), ("Text span refs", report.text_span_refs), ("Structured refs", report.structured_refs), ("Issues", len(report.issues))]
    for label, count in rows:
        print(f"| {label} | {count} |")
    print("\n## Resolved Evidence\n")
    print("| Source Ref | Artifact | Kind | Evidence Role | Can Open | Can Highlight | Snippet |\n|---|---|---|---|---|---|---|")
    for item in resolved:
        print(f"| {_cell(item.source_ref_id)} | {_cell(item.source_artifact_id)} | {_cell(item.artifact_kind)} | {_cell(item.evidence_role)} | {item.can_open_source} | {item.can_highlight_span} | {_cell(item.preview_snippet)} |")
    print("\n## Issues\n")
    print("| Severity | Code | Source Ref | Message |\n|---|---|---|---|")
    for issue in report.issues:
        print(f"| {_cell(issue.severity)} | {_cell(issue.code)} | {_cell(issue.source_ref_id or '')} | {_cell(issue.message)} |")
    print("\n## Boundary Statement\n")
    print("This is a source-span evidence resolver fixture only.")
    print("It does not extract entities.")
    print("It does not infer relationships.")
    print("It does not promote facts or canon.")
    print("It does not connect `/plan`.")
    print("It does not connect Agent Interaction.")
    print("It does not read runtime corpus files.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
