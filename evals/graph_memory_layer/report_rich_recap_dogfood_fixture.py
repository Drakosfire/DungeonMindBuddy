from __future__ import annotations

from evals.graph_memory_layer.rich_recap_dogfood import build_rich_recap_materializer_inputs, build_rich_recap_source_span_registries, load_rich_recap_requirements
from src.graph_memory.recap_ingestion_materialize import materialize_recap_ingestion_source_artifacts
from src.graph_memory.source_span import resolve_many_source_span_refs


def main() -> int:
    inputs = build_rich_recap_materializer_inputs()
    materialization = materialize_recap_ingestion_source_artifacts(inputs)
    requirements = load_rich_recap_requirements()
    declared = requirements["declared_contents"]
    minimums = requirements["minimum_requirements"]
    text_artifacts, structured_artifacts, refs = build_rich_recap_source_span_registries()
    resolved = resolve_many_source_span_refs(refs, text_artifacts=text_artifacts, structured_artifacts=structured_artifacts)
    print("# Rich Recap Dogfood Fixture Report\n")
    print("## Summary\n")
    print("| Metric | Count |\n|---|---:|")
    rows = [("Artifact inputs", len(inputs)), ("Source artifacts", len(materialization.artifacts)), ("Source anchors", len(materialization.anchors)), ("Source units", len(materialization.units)), ("Source span refs", len(refs)), ("Resolved span refs", sum(1 for r in resolved if r.can_open_source)), ("Text span refs", sum(1 for r in refs if r.start_line is not None)), ("Structured refs", sum(1 for r in refs if r.structured_path)), ("Declared named entities", len(declared["named_entities"])), ("Declared locations", len(declared["locations"])), ("Declared session beats", len(declared["session_beats"])), ("Declared unresolved threads", len(declared["unresolved_threads"])), ("Declared ignored/not-promoted details", len(declared["ignored_or_not_promoted_details"])), ("Declared deferred/uncertain details", len(declared["deferred_or_uncertain_details"]))]
    for k, v in rows: print(f"| {k} | {v} |")
    print("\n## Declared Richness\n")
    print("| Category | Count | Minimum |\n|---|---:|---:|")
    for key, minimum in minimums.items():
        declared_key = "unnamed_important_concepts" if key == "unnamed_important_relationship_opportunities" else key
        values = declared.get(declared_key, [])
        print(f"| {key} | {len(values)} | {minimum} |")
    print("\n## Source Span Coverage\n")
    print("| Ref | Artifact | Label | Evidence Role | Can Open | Can Highlight |\n|---|---|---|---|---|---|")
    for item in resolved:
        print(f"| {item.source_ref_id} | {item.source_artifact_id} | {item.label} | {item.evidence_role} | {item.can_open_source} | {item.can_highlight_span} |")
    print("\n## Boundary Statement\n")
    print("This is a rich recap source fixture only.")
    print("It does not extract entities.")
    print("It does not infer relationships.")
    print("It does not produce a candidate graph preview.")
    print("It does not produce a hand-authored gold graph.")
    print("It does not write graph memory.")
    print("It does not approve writes.")
    print("It does not promote facts or canon.")
    print("It does not connect `/plan`.")
    print("It does not connect Agent Interaction.")
    print("It does not change runtime behavior.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
