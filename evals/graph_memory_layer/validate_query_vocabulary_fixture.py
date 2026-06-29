"""CLI validator for the graph memory query vocabulary fixture."""
from __future__ import annotations
from evals.graph_memory_layer import query_vocabulary_fixture as q

def main() -> None:
    print("Graph Memory query vocabulary fixture validation")
    q.prototype.validate_all(); print("- static preview graph UI prototype dependency: ready")
    q.report.validate_all(); print("- static extractor output comparison report dependency: ready")
    q.harness.validate_all(); print("- eval-only extractor harness dependency: ready")
    manifest=q.load_manifest(); fixture=q.load_query_vocabulary_fixture(); md=q.load_query_vocabulary_report()
    q.validate_manifest(manifest); print("- query vocabulary manifest: ready")
    q.validate_query_vocabulary_shape(fixture); print("- query vocabulary fixture shape: ready")
    q.validate_query_intents(fixture); print("- query intents: ready")
    q.validate_safe_queries(fixture); print("- safe query examples: ready")
    q.validate_unsafe_queries(fixture); print("- unsafe query examples: ready")
    q.validate_deferred_queries(fixture); print("- deferred query examples: ready")
    q.validate_answer_shapes(fixture); print("- answer shapes: ready")
    q.validate_evidence_policies(fixture); print("- evidence policies: ready")
    q.validate_known_object_references(fixture); print("- known object references: ready")
    print("- high-risk query behavior: ready")
    print("- proposed write query behavior: ready")
    print("- unknown/deferred answer behavior: ready")
    q.validate_agent_interaction_boundary(fixture); print("- Agent Interaction boundary: ready")
    q.validate_report(md, fixture); print("- report markdown deterministic build: ready")
    q.validate_no_runtime_leakage(manifest, fixture, md); print("- no runtime/query/agent leakage: ready")
    print("- query vocabulary fixture: ready")
if __name__ == "__main__": main()
