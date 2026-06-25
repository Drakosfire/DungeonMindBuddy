"""Concise report CLI for the graph memory query vocabulary fixture."""
from __future__ import annotations
from evals.graph_memory_layer import query_vocabulary_fixture as q

def main() -> None:
    f=q.load_query_vocabulary_fixture()
    print("Graph Memory Query Vocabulary Fixture v0")
    print(f"Fixture: {q.QUERY_VOCABULARY_FIXTURE_PATH}")
    print(f"Report: {q.QUERY_VOCABULARY_REPORT_PATH}")
    print(f"Safe query examples: {len(f['safe_queries'])}")
    print(f"Unsafe query examples: {len(f['unsafe_queries'])}")
    print(f"Deferred query examples: {len(f['deferred_queries'])}")
    print(f"Agent Interaction readiness: {f['agent_interaction_readiness']['status']}")
    print("Boundary: static vocabulary only; no query execution")
if __name__ == "__main__": main()
