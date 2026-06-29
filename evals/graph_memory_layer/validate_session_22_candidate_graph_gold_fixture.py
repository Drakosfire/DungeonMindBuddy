from __future__ import annotations

import json

from evals.graph_memory_layer.session_22_candidate_graph_gold_fixture import *
from evals.graph_memory_layer.session_22_recap_ingest_fixture import load_manifest, validate_manifest
from src.graph_memory.candidate_graph_preview import COMMITTED_ACTIONS


def _assert(condition: bool, message: object) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> None:
    print("Graph Memory Session 22 candidate graph gold fixture validation")
    validate_manifest(load_manifest())
    print("- session 22 recap ingest dependency: ready")
    manifest = load_gold_manifest()
    validate_gold_manifest(manifest)
    print("- gold manifest: ready")
    preview = parse_gold_candidate_graph()
    report = validate_gold_candidate_graph()
    _assert(not report.issues, report.issues)
    _assert(preview.schema == CANDIDATE_GRAPH_PREVIEW_SCHEMA and preview.version == CANDIDATE_GRAPH_PREVIEW_VERSION, "schema/version")
    print("- candidate graph schema/version: ready")
    _assert(preview.status == "preview" and preview.campaign_id == "longmont-c2" and preview.session_id == "session-22", "status/session")
    print("- preview status: ready")
    _assert(SOURCE_ARTIFACT_ID in preview.source_artifact_ids, "source artifact")
    _assert(len(preview.nodes) >= 25 and len(preview.edges) >= 16 and len(preview.beats) >= 9 and len(preview.proposed_writes) >= 10, "counts")
    print("- graph shape counts: ready")
    _assert(sum(node.node_type in {"thread", "mystery"} and node.node_id.startswith("node:") for node in preview.nodes) >= 4, "mystery/thread nodes")
    print("- unresolved thread nodes: ready")
    node_ids = {node.node_id for node in preview.nodes}
    _assert(all(edge.from_node_id in node_ids and edge.to_node_id in node_ids for edge in preview.edges), "edge endpoints")
    print("- edges: ready")
    _assert(all(node_id in node_ids for beat in preview.beats for node_id in beat.involved_node_ids + beat.unresolved_thread_node_ids), "beat nodes")
    print("- session beats: ready")
    targets = node_ids | {edge.edge_id for edge in preview.edges} | {beat.beat_id for beat in preview.beats} | {item.item_id for item in preview.ignored_items} | {item.item_id for item in preview.deferred_items}
    _assert(all(write.target_id in targets and write.status == "pending" for write in preview.proposed_writes), "writes")
    print("- proposed writes: ready")
    _assert(all(getattr(obj, "semantic_state", None).lifecycle_state != "promoted" for obj in list(preview.nodes) + list(preview.edges)), "promoted lifecycle")
    _assert(all(getattr(obj, "proposed_action", "create") not in COMMITTED_ACTIONS for obj in list(preview.nodes) + list(preview.edges) + list(preview.beats)), "committed action")
    print("- semantic states: ready")
    refs = collect_gold_evidence_refs(preview)
    anchors = valid_source_anchor_ids()
    _assert(all(refs), "refs")
    _assert(all(ref.source_anchor_id in anchors for ref in refs), "unknown anchors")
    validate_high_risk_evidence_audit(preview)
    print("- evidence refs: ready")
    resolved = resolve_gold_evidence_refs()
    _assert(len(resolved) == len(refs), "resolved count")
    _assert(all(not item.warnings for item in resolved), "resolver warnings")
    _assert(all(item.can_open_source and item.can_highlight_span for item in resolved), "open/highlight")
    _assert(all(item.preview_snippet.strip() and not item.preview_snippet.strip().startswith("#") for item in resolved), "heading only")
    print("- source evidence resolvability: ready")
    graph_text = json.dumps(load_gold_candidate_graph_dict())
    _assert(load_source_text() not in graph_text, "source leakage")
    diagnostics = preview.diagnostics
    _assert(diagnostics.preview_only and not any([diagnostics.extraction_performed, diagnostics.llm_used, diagnostics.runtime_connected, diagnostics.plan_connected, diagnostics.agent_interaction_connected, diagnostics.corpus_scanned, diagnostics.corpus_mutated, diagnostics.facts_promoted, diagnostics.canon_promoted]), "dangerous diagnostics")
    print("- no graph write/approval: ready")
    forbidden = ("llm_response", "extraction_output", "runtime_payload", "adapter_payload", "plan_payload", "agent_interaction_payload", "query_execution", "corpus_mutation", "graph_write_result", "canon_promotion", "fact_promotion")
    _assert(not any(key in graph_text for key in forbidden), "forbidden payload")
    print("- no extraction/LLM output: ready")
    print("- session 22 candidate graph gold fixture: ready")


if __name__ == "__main__":
    main()
