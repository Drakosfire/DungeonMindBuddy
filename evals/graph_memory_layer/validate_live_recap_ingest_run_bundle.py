"""CLI validator for the live recap ingest run bundle fixture."""
from evals.graph_memory_layer import live_recap_ingest_run_bundle as l

def main() -> None:
    print('Graph Memory live recap ingest run bundle validation')
    m=l.load_example_manifest(); assert m; print('- fixture manifest: ready')
    b=l.load_example_run_bundle(); l.validate_run_manifest(b['run_manifest']); print('- sample run manifest: ready')
    l.validate_source_artifact(b['source_artifact']); print('- source artifact: ready')
    l.validate_source_units(b['source_units']); print('- source units: ready')
    l.validate_source_span_index(b['source_span_index'],b['source_units']); print('- source span index: ready')
    l.validate_provenance_index(b['provenance_index'],b['source_units']); print('- provenance index: ready')
    l.validate_diagnostics(b['diagnostics']); print('- diagnostics: ready')
    l.validate_report(b['recap_ingest_report']); print('- markdown report: ready')
    l.validate_bundle_consistency(b); print('- bundle consistency: ready')
    print('- explicit-input boundary: ready')
    l.validate_no_runtime_leakage(m,b); print('- no extraction/query/write/runtime leakage: ready')
    l.validate_all(); print('- live recap ingest run bundle: ready')
if __name__=='__main__': main()
