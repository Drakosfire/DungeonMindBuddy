from __future__ import annotations

from evals.graph_memory_layer.session_22_candidate_graph_gold_fixture import *


def esc(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def main() -> None:
    preview = parse_gold_candidate_graph()
    refs = collect_gold_evidence_refs(preview)
    resolved = resolve_gold_evidence_refs()
    print("# Session 22 Candidate Graph Gold Fixture Report\n")
    print("## Summary\n\n| Metric | Count |\n|---|---:|")
    rows = [
        ("Nodes", len(preview.nodes)),
        ("Edges", len(preview.edges)),
        ("Session beats", len(preview.beats)),
        ("Proposed writes", len(preview.proposed_writes)),
        ("Ignored items", len(preview.ignored_items)),
        ("Deferred items", len(preview.deferred_items)),
        ("Evidence refs", len(refs)),
        ("Resolved evidence refs", len(resolved)),
        ("Mystery/thread nodes", sum(node.node_type in {"thread", "mystery"} for node in preview.nodes)),
    ]
    for key, value in rows:
        print(f"| {key} | {value} |")
    print("\n## Session Outline\n\n| Order | Beat | Summary | Evidence |\n|---:|---|---|---:|")
    for beat in sorted(preview.beats, key=lambda item: item.order):
        print(f"| {beat.order} | {esc(beat.title)} | {esc(beat.summary)} | {len(beat.evidence_refs)} |")
    print("\n## Nodes\n\n| ID | Label | Type | Importance | Confidence | Evidence |\n|---|---|---|---|---|---:|")
    for node in preview.nodes:
        print(f"| {node.node_id} | {esc(node.label)} | {node.node_type} | {node.importance} | {node.confidence} | {len(node.evidence_refs)} |")
    labels = {node.node_id: node.label for node in preview.nodes}
    print("\n## Edges\n\n| ID | From | Label | To | Type | Confidence | Evidence |\n|---|---|---|---|---|---|---:|")
    for edge in preview.edges:
        print(f"| {edge.edge_id} | {esc(labels[edge.from_node_id])} | {esc(edge.label)} | {esc(labels[edge.to_node_id])} | {edge.relationship_type} | {edge.confidence} | {len(edge.evidence_refs)} |")
    print("\n## Proposed Writes\n\n| ID | Type | Target | Status | Reason |\n|---|---|---|---|---|")
    for write in preview.proposed_writes:
        print(f"| {write.write_id} | {write.write_type} | {write.target_id} | {write.status} | {esc(write.reason)} |")
    print("\n## Deferred Items\n\n| ID | Label | Reason | Suggested Next Step | Evidence |\n|---|---|---|---|---:|")
    for item in preview.deferred_items:
        print(f"| {item.item_id} | {esc(item.label)} | {esc(item.reason)} | {esc(item.suggested_next_step)} | {len(item.evidence_refs)} |")
    print("\n## Evidence Preview\n\n| Anchor | Label | Snippet |\n|---|---|---|")
    seen: set[str] = set()
    for item in resolved:
        if item.source_anchor_id in seen:
            continue
        seen.add(str(item.source_anchor_id))
        print(f"| {item.source_anchor_id} | {esc(item.label)} | {esc(item.preview_snippet)} |")
    print("\n## Boundary Statement\n")
    print(
        "This is a hand-authored Session 22 Candidate Graph Preview gold fixture.\n"
        "It is not extractor output.\n"
        "It does not call an LLM.\n"
        "It does not run the live planner.\n"
        "It does not write graph memory.\n"
        "It does not approve writes.\n"
        "It does not execute graph queries.\n"
        "It does not scan or mutate corpus files.\n"
        "It does not connect `/plan`.\n"
        "It does not connect Agent Interaction.\n"
        "It does not promote facts or canon.\n"
        "It does not change runtime behavior."
    )


if __name__ == "__main__":
    main()
