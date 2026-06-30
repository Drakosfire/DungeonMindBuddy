from __future__ import annotations

import json

from evals.graph_memory_layer.mirathorn_city_world_doc_fixture import load_manifest, validate_manifest, load_source_doc
from evals.graph_memory_layer.mirathorn_city_candidate_graph_gold_fixture import *
from src.graph_memory.candidate_graph_preview import COMMITTED_ACTIONS


def _assert(c, msg):
    if not c:
        raise AssertionError(msg)


def main() -> None:
    print("Graph Memory Mirathorn city candidate graph gold fixture validation")
    validate_manifest(load_manifest())
    print("- mirathorn city world doc dependency: ready")
    m = load_gold_manifest()
    validate_gold_manifest(m)
    print("- gold manifest: ready")
    p = parse_gold_candidate_graph()
    r = validate_gold_candidate_graph()
    _assert(not r.issues, r.issues)
    _assert(p.schema == CANDIDATE_GRAPH_PREVIEW_SCHEMA and p.version == CANDIDATE_GRAPH_PREVIEW_VERSION, "schema/version")
    print("- candidate graph schema/version: ready")
    _assert(p.status == "preview" and p.campaign_id is None and p.session_id is None, "status/session")
    print("- preview status: ready")
    _assert("source-artifact:mirathorn-city-world-doc" in p.source_artifact_ids, "source artifact")
    _assert(
        len(p.nodes) >= 26
        and len(p.edges) >= 24
        and len(p.beats) == 0
        and len(p.proposed_writes) >= 2
        and len(p.ignored_items) >= 1
        and len(p.deferred_items) >= 3,
        "counts",
    )
    print("- graph shape counts: ready")
    labels = " ".join(n.label for n in p.nodes).lower()
    for term in [
        "mirathorn",
        "the elderwyld",
        "lundayell",
        "stormspire",
        "shepherd's flock",
        "wizard's tower brewing co",
        "elara swiftwind",
        "tinkerbright",
        "nameless goddess",
    ]:
        _assert(term in labels or term in json.dumps(load_gold_candidate_graph_dict()).lower(), term)
    print("- named nodes: ready")
    node_ids = {n.node_id for n in p.nodes}
    _assert(all(e.from_node_id in node_ids and e.to_node_id in node_ids for e in p.edges), "edge endpoints")
    print("- edges: ready")
    targets = node_ids | {e.edge_id for e in p.edges} | {i.item_id for i in p.ignored_items} | {d.item_id for d in p.deferred_items}
    _assert(all(w.target_id in targets and w.status == "pending" for w in p.proposed_writes), "writes")
    print("- proposed writes: ready")
    print("- ignored items: ready")
    print("- deferred items: ready")
    _assert(all(getattr(o, "semantic_state", None).lifecycle_state != "promoted" for o in list(p.nodes) + list(p.edges)), "promoted lifecycle")
    _assert(
        all(getattr(o, "proposed_action", "create") not in COMMITTED_ACTIONS for o in list(p.nodes) + list(p.edges) + list(p.beats)),
        "committed action",
    )
    print("- semantic states: ready")
    print("- graph integrity: ready")
    refs = collect_gold_evidence_refs(p)
    anchors = valid_source_anchor_ids()
    _assert(all(refs), "refs")
    _assert(all(r.source_anchor_id in anchors for r in refs), "unknown anchors")
    validate_high_risk_evidence_audit(p)
    print("- evidence refs: ready")
    resolved = resolve_gold_evidence_refs()
    _assert(all(not x.warnings for x in resolved), "resolver warnings")
    _assert(len(resolved) == len(refs), "resolved count")
    _assert(all(x.can_open_source for x in resolved), "open")
    print("- source evidence openability: ready")
    _assert(all(x.can_highlight_span for x in resolved), "highlight")
    print("- source evidence highlightability: ready")
    _assert(all(x.preview_snippet.strip() and not x.preview_snippet.strip().startswith("#") for x in resolved), "heading only")
    print("- no heading-only evidence refs: ready")
    graph_text = json.dumps(load_gold_candidate_graph_dict())
    _assert(load_source_doc() not in graph_text, "source leakage")
    print("- no full source leakage: ready")
    d = p.diagnostics
    _assert(
        d.preview_only
        and not any(
            [
                d.extraction_performed,
                d.llm_used,
                d.runtime_connected,
                d.plan_connected,
                d.agent_interaction_connected,
                d.corpus_scanned,
                d.corpus_mutated,
                d.facts_promoted,
                d.canon_promoted,
            ]
        ),
        "dangerous diagnostics",
    )
    print("- no graph write/approval: ready")
    forbidden = (
        "llm_response",
        "extraction_output",
        "runtime_payload",
        "adapter_payload",
        "plan_payload",
        "agent_interaction_payload",
        "query_execution",
        "corpus_mutation",
        "graph_write_result",
        "canon_promotion",
        "fact_promotion",
    )
    _assert(not any(k in graph_text for k in forbidden), "forbidden payload")
    print("- no extraction/LLM output: ready")
    print("- no adapter/plan/agent/runtime leakage: ready")
    print("- mirathorn city candidate graph gold fixture: ready")


if __name__ == "__main__":
    main()
