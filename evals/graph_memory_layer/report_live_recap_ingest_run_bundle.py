"""Report CLI for the live recap ingest sample run bundle."""
from evals.graph_memory_layer import live_recap_ingest_run_bundle as l

def main() -> None:
    b=l.load_example_run_bundle(); m=b['run_manifest']; d=b['diagnostics']
    print('Live Recap Ingest Run Bundle v0')
    print(f"Sample run: {m['run_id']}")
    print(f"Campaign: {m['campaign_id']}")
    print(f"Session: {m['session_id']}")
    print(f"Source units: {len(b['source_units']['units'])}")
    print(f"Source span refs: {d['counts']['source_span_refs']}")
    print(f"Warnings: {d['counts']['warnings']}")
    print(f"Hard failures: {d['counts']['hard_failures']}")
    print('Boundary: explicit input only; no LLM, extraction, graph writes, query execution, /plan, Agent Interaction, corpus scan/mutation, or runtime behavior')
    print(f"Report: {l.SESSION_23_SAMPLE_DIR}/recap_ingest_report.md")
if __name__=='__main__': main()
